---
description: Meta-orchestrator that monitors health and performance of all agentic workflows in the repository
on:
  schedule:
    - cron: "0 0 * * *" # Daily at midnight UTC
  workflow_dispatch:
permissions:
  contents: read
  actions: read
  issues: write
tools:
  github:
    mode: local
    read-only: false
    toolsets: [default]
if: needs.precompute.outputs.action != 'none'
jobs:
  precompute:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      actions: read
      issues: write
    outputs:
      action: ${{ steps.precompute.outputs.action }}
      issue_number: ${{ steps.precompute.outputs.issue_number }}
      issue_title: ${{ steps.precompute.outputs.issue_title }}
      issue_body: ${{ steps.precompute.outputs.issue_body }}
      failed_workflows: ${{ steps.precompute.outputs.failed_workflows }}
    steps:
      - name: Precompute workflow health metrics
        id: precompute
        uses: actions/github-script@v7
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          script: |
            const { owner, repo } = context.repo;
            const ISSUE_TITLE = "🔧 Workflow Health Report";
            const LOOKBACK_DAYS = 7;

            function toISO(d) {
              return new Date(d).toISOString();
            }

            async function getRunCreatedAt() {
              const runId = context.runId;
              const { data } = await github.rest.actions.getWorkflowRun({
                owner,
                repo,
                run_id: runId,
              });
              return new Date(data.created_at);
            }

            const end = await getRunCreatedAt();
            const start = new Date(end.getTime() - LOOKBACK_DAYS * 24 * 60 * 60 * 1000);

            core.info(`Analysis window: ${toISO(start)} -> ${toISO(end)}`);

            // Get all workflows in the repository
            const { data: workflows } = await github.rest.actions.listRepoWorkflows({
              owner,
              repo,
              per_page: 100,
            });

            // Filter to only .md workflows (agentic workflows), exclude shared/ subdirectory
            const agenticWorkflows = workflows.workflows.filter(w =>
              w.path.startsWith('.github/workflows/') &&
              w.path.endsWith('.md') &&
              !w.path.includes('shared/')
            );

            core.info(`Found ${agenticWorkflows.length} agentic workflows to monitor`);

            // Analyze each workflow
            const workflowStats = [];

            for (const workflow of agenticWorkflows) {
              const workflowName = workflow.name || workflow.path.split('/').pop().replace('.md', '');
              core.info(`Analyzing workflow: ${workflowName}`);

              try {
                // Get workflow runs in the time window
                const { data: runs } = await github.rest.actions.listWorkflowRuns({
                  owner,
                  repo,
                  workflow_id: workflow.id,
                  per_page: 100,
                  created: `>=${toISO(start)}`,
                });

                const runsInWindow = runs.workflow_runs.filter(r =>
                  new Date(r.created_at) >= start && new Date(r.created_at) <= end
                );

                // Calculate success rate
                const totalRuns = runsInWindow.length;
                const successfulRuns = runsInWindow.filter(r => r.conclusion === 'success').length;
                const failedRuns = runsInWindow.filter(r => r.conclusion === 'failure').length;
                const cancelledRuns = runsInWindow.filter(r => r.conclusion === 'cancelled').length;
                const timedOutRuns = runsInWindow.filter(r => r.conclusion === 'timed_out').length;

                const successRate = totalRuns > 0 ? (successfulRuns / totalRuns * 100).toFixed(1) : 'N/A';

                // Calculate average duration (for completed runs)
                const completedRuns = runsInWindow.filter(r =>
                  r.conclusion && r.conclusion !== 'cancelled' && r.run_started_at
                );

                let avgDuration = 'N/A';
                if (completedRuns.length > 0) {
                  const totalDuration = completedRuns.reduce((sum, r) => {
                    const start = new Date(r.run_started_at);
                    const end = new Date(r.updated_at);
                    return sum + (end - start);
                  }, 0);
                  avgDuration = Math.round(totalDuration / completedRuns.length / 1000); // seconds
                }

                // Get most recent failure details
                const recentFailure = runsInWindow.find(r => r.conclusion === 'failure');
                let failureDetails = null;
                if (recentFailure) {
                  failureDetails = {
                    run_number: recentFailure.run_number,
                    created_at: recentFailure.created_at,
                    html_url: recentFailure.html_url,
                  };
                }

                // Determine health status
                let status = 'healthy';
                let severity = 'none';
                const issues = [];

                if (totalRuns === 0) {
                  status = 'inactive';
                  severity = 'low';
                  issues.push('No runs in past 7 days');
                } else {
                  const failureRate = (failedRuns / totalRuns * 100);

                  if (failureRate >= 50) {
                    status = 'critical';
                    severity = 'high';
                    issues.push(`High failure rate: ${failureRate.toFixed(1)}%`);
                  } else if (failureRate >= 25) {
                    status = 'degraded';
                    severity = 'medium';
                    issues.push(`Elevated failure rate: ${failureRate.toFixed(1)}%`);
                  } else if (failureRate > 0) {
                    status = 'warning';
                    severity = 'low';
                    issues.push(`Some failures: ${failureRate.toFixed(1)}%`);
                  }

                  if (timedOutRuns > 0) {
                    issues.push(`${timedOutRuns} timeout(s)`);
                  }

                  if (avgDuration !== 'N/A' && avgDuration > 1800) { // > 30 minutes
                    issues.push(`Long avg duration: ${Math.round(avgDuration / 60)}m`);
                  }
                }

                workflowStats.push({
                  name: workflowName,
                  path: workflow.path,
                  status,
                  severity,
                  issues,
                  totalRuns,
                  successfulRuns,
                  failedRuns,
                  cancelledRuns,
                  timedOutRuns,
                  successRate,
                  avgDuration,
                  failureDetails,
                });

              } catch (error) {
                core.warning(`Failed to analyze workflow ${workflowName}: ${error.message}`);
                workflowStats.push({
                  name: workflowName,
                  path: workflow.path,
                  status: 'error',
                  severity: 'medium',
                  issues: [`Analysis error: ${error.message}`],
                  totalRuns: 0,
                  successfulRuns: 0,
                  failedRuns: 0,
                  cancelledRuns: 0,
                  timedOutRuns: 0,
                  successRate: 'N/A',
                  avgDuration: 'N/A',
                  failureDetails: null,
                });
              }
            }

            // Sort by severity (critical first) then by name
            const severityOrder = { high: 0, medium: 1, low: 2, none: 3 };
            workflowStats.sort((a, b) => {
              const sevDiff = severityOrder[a.severity] - severityOrder[b.severity];
              if (sevDiff !== 0) return sevDiff;
              return a.name.localeCompare(b.name);
            });

            // Calculate overall health
            const criticalCount = workflowStats.filter(w => w.status === 'critical').length;
            const degradedCount = workflowStats.filter(w => w.status === 'degraded').length;
            const warningCount = workflowStats.filter(w => w.status === 'warning').length;
            const healthyCount = workflowStats.filter(w => w.status === 'healthy').length;
            const inactiveCount = workflowStats.filter(w => w.status === 'inactive').length;

            let overallStatus = 'Healthy';
            if (criticalCount > 0) overallStatus = 'Critical';
            else if (degradedCount > 0) overallStatus = 'Degraded';
            else if (warningCount > 0) overallStatus = 'Warning';

            // Log summary
            core.info('=== Workflow Health Summary ===');
            core.info(`Overall Status: ${overallStatus}`);
            core.info(`Critical: ${criticalCount}`);
            core.info(`Degraded: ${degradedCount}`);
            core.info(`Warning: ${warningCount}`);
            core.info(`Healthy: ${healthyCount}`);
            core.info(`Inactive: ${inactiveCount}`);

            // Detailed report
            core.info('=== Detailed Workflow Status ===');
            for (const wf of workflowStats) {
              core.info(`${wf.name}:`);
              core.info(`  Status: ${wf.status} (severity=${wf.severity})`);
              core.info(`  Runs: ${wf.totalRuns} (success=${wf.successfulRuns}, failed=${wf.failedRuns})`);
              core.info(`  Success Rate: ${wf.successRate}${typeof wf.successRate === 'string' ? '' : '%'}`);
              core.info(`  Avg Duration: ${wf.avgDuration}${typeof wf.avgDuration === 'number' ? 's' : ''}`);
              if (wf.issues.length > 0) {
                core.info(`  Issues: ${wf.issues.join(', ')}`);
              }
            }

            // Find existing health report issue
            let existingIssueNumber = "";
            try {
              const openIssues = await github.rest.issues.listForRepo({
                owner,
                repo,
                state: "open",
                per_page: 100,
              });
              const existing = (openIssues.data || []).find(i => (i.title || "") === ISSUE_TITLE);
              if (existing?.number) existingIssueNumber = String(existing.number);
            } catch (e) {
              core.warning(`Failed to find existing issue: ${e.message}`);
            }

            // Render markdown report
            function renderBody() {
              const lines = [];
              lines.push(
                `**Period:** ${toISO(start)} → ${toISO(end)} (${LOOKBACK_DAYS} days)`,
                `**Overall Status:** ${overallStatus}`,
                `**Monitored Workflows:** ${workflowStats.length}`,
                ""
              );

              // Summary statistics
              lines.push("## Summary", "");
              lines.push("| Status | Count |");
              lines.push("| --- | ---: |");
              lines.push(`| 🔴 Critical | ${criticalCount} |`);
              lines.push(`| 🟡 Degraded | ${degradedCount} |`);
              lines.push(`| ⚠️  Warning | ${warningCount} |`);
              lines.push(`| ✅ Healthy | ${healthyCount} |`);
              lines.push(`| ⚪ Inactive | ${inactiveCount} |`);
              lines.push("");

              // Workflows requiring attention
              const needsAttention = workflowStats.filter(w =>
                w.status === 'critical' || w.status === 'degraded' || w.status === 'warning'
              );

              if (needsAttention.length > 0) {
                lines.push("## Workflows Requiring Attention", "");

                for (const wf of needsAttention) {
                  const statusIcon = wf.status === 'critical' ? '🔴' :
                                    wf.status === 'degraded' ? '🟡' : '⚠️';

                  lines.push(`### ${statusIcon} ${wf.name}`);
                  lines.push("");
                  lines.push(`- **Path:** \`${wf.path}\``);
                  lines.push(`- **Status:** ${wf.status}`);
                  lines.push(`- **Total Runs:** ${wf.totalRuns}`);
                  lines.push(`- **Success Rate:** ${wf.successRate}${typeof wf.successRate === 'string' ? '' : '%'}`);
                  lines.push(`- **Average Duration:** ${wf.avgDuration}${typeof wf.avgDuration === 'number' ? 's' : ''}`);

                  if (wf.issues.length > 0) {
                    lines.push(`- **Issues:**`);
                    for (const issue of wf.issues) {
                      lines.push(`  - ${issue}`);
                    }
                  }

                  if (wf.failureDetails) {
                    lines.push(`- **Most Recent Failure:**`);
                    lines.push(`  - Run #${wf.failureDetails.run_number}`);
                    lines.push(`  - Time: ${wf.failureDetails.created_at}`);
                    lines.push(`  - [View Run](${wf.failureDetails.html_url})`);
                  }

                  lines.push("");
                }
              }

              // All workflows table
              lines.push("## All Workflows", "");
              lines.push("| Workflow | Status | Runs | Success Rate | Avg Duration |");
              lines.push("| --- | --- | ---: | ---: | ---: |");

              for (const wf of workflowStats) {
                const statusIcon = wf.status === 'critical' ? '🔴' :
                                  wf.status === 'degraded' ? '🟡' :
                                  wf.status === 'warning' ? '⚠️' :
                                  wf.status === 'healthy' ? '✅' : '⚪';

                const successRateStr = typeof wf.successRate === 'string' ?
                  wf.successRate : `${wf.successRate}%`;
                const avgDurStr = typeof wf.avgDuration === 'string' ?
                  wf.avgDuration : `${wf.avgDuration}s`;

                lines.push(`| ${wf.name} | ${statusIcon} ${wf.status} | ${wf.totalRuns} | ${successRateStr} | ${avgDurStr} |`);
              }

              lines.push("");
              lines.push("## Notes", "");
              lines.push(`- This report analyzes workflow runs from the past ${LOOKBACK_DAYS} days`);
              lines.push("- Only workflows in `.github/workflows/*.md` are monitored (excluding `shared/` subdirectory)");
              lines.push("- Success rate is calculated as successful runs / total runs");
              lines.push("- Average duration includes only completed runs (excludes cancelled runs)");
              lines.push("");
              lines.push("---");
              lines.push("*Generated by workflow-health-manager meta-orchestrator*");

              return lines.join("\n");
            }

            // Determine action
            const hasIssues = criticalCount > 0 || degradedCount > 0 || warningCount > 0;
            let action = "none";
            let issueBody = "";
            let issueNumber = "";

            if (existingIssueNumber) {
              action = "update";
              issueNumber = existingIssueNumber;
              issueBody = renderBody();
            } else if (hasIssues) {
              action = "create";
              issueBody = renderBody();
            }

            // Track failed workflows for repo-memory
            const failedWorkflows = workflowStats
              .filter(w => w.status === 'critical' || w.status === 'degraded')
              .map(w => ({
                name: w.name,
                path: w.path,
                status: w.status,
                failureRate: w.totalRuns > 0 ? ((w.failedRuns / w.totalRuns) * 100).toFixed(1) : 0,
              }));

            core.setOutput("action", action);
            core.setOutput("issue_number", issueNumber);
            core.setOutput("issue_title", ISSUE_TITLE);
            core.setOutput("issue_body", issueBody);
            core.setOutput("failed_workflows", JSON.stringify(failedWorkflows));
safe-outputs:
  create-issue:
    max: 1
    labels: [automation, workflow-health, monitoring]
  update-issue:
    max: 1
    target: "*"
    body:
  mentions:
    allowed: []
  threat-detection: false
timeout-minutes: 15
strict: true
---

# Workflow Health Manager

You are a workflow health monitoring agent responsible for maintaining the **Workflow Health Report** issue in ${{ github.repository }}.

## Your Mission

Monitor the health and performance of all agentic workflows (`.github/workflows/*.md` files, excluding `shared/` subdirectory) and maintain a single health report issue that provides visibility into workflow reliability and performance.

## Determinism Contract (MUST FOLLOW)

This workflow enforces determinism via a **precompute job**.

- Do **not** query GitHub tools for additional data.
- Use only these precomputed values:
  - `action`: `${{ needs.precompute.outputs.action }}`
  - `issue_number`: `${{ needs.precompute.outputs.issue_number }}`
  - `issue_title`: `${{ needs.precompute.outputs.issue_title }}`
  - `issue_body`: (verbatim) `${{ needs.precompute.outputs.issue_body }}`
  - `failed_workflows`: `${{ needs.precompute.outputs.failed_workflows }}`

- Emit exactly **one** safe output based on `action`:
  - `create`: create an issue with `title=issue_title` and `body=issue_body`
  - `update`: update `issue_number` with `body=issue_body`
  - `none`: emit no safe outputs

- Do not modify the precomputed markdown body.

## Report Maintenance

Maintain a **single** open issue with the exact title:

`🔧 Workflow Health Report`

### When to Create vs Update

- If an **open** issue with that exact title does **not** exist and there are workflow issues, **create** it.
- If it **does** exist, **update the existing issue body** with the latest health data.
- If all workflows are healthy and no issue exists, emit **no safe outputs**.

## Metrics Stored in Repo-Memory

After updating the health report, store the following metrics in repo-memory for trend analysis:

- Overall workflow health status (Critical/Degraded/Warning/Healthy)
- Count of workflows by status category
- List of failed/degraded workflows with failure rates
- Timestamp of the health check

Use the `failed_workflows` precomputed output for this data.

## Report Components

The precomputed report includes:

1. **Summary Statistics**: Counts by health status
2. **Workflows Requiring Attention**: Detailed breakdown of problematic workflows
3. **All Workflows Table**: Overview of all monitored workflows
4. **Notes**: Analysis methodology and definitions

## Health Status Definitions

- **Critical** (🔴): ≥50% failure rate
- **Degraded** (🟡): 25-49% failure rate
- **Warning** (⚠️): >0% failure rate but <25%
- **Healthy** (✅): 100% success rate
- **Inactive** (⚪): No runs in the past 7 days

## Your Responsibilities

1. **Issue Management**: Create or update the health report issue using precomputed data
2. **No Additional Analysis**: Use only the precomputed metrics provided
3. **Deterministic Output**: Emit the exact safe output specified by the action value
4. **Memory Storage**: Store workflow health trends in repo-memory for historical analysis

## Example Safe Output

For `action=create`:

```json
{
  "safe_output": "create-issue",
  "title": "🔧 Workflow Health Report",
  "body": "<precomputed_markdown>",
  "labels": ["automation", "workflow-health", "monitoring"]
}
```

For `action=update`:

```json
{
  "safe_output": "update-issue",
  "issue_number": "<issue_number>",
  "body": "<precomputed_markdown>"
}
```

Remember: You are a **reporting agent**, not an analysis agent. The precompute job has already performed all analysis. Your job is to faithfully render the safe outputs based on the action directive.
