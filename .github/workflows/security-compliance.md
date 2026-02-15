# Security Compliance Campaign Workflow

## YAML Configuration

```yaml
name: Security Compliance Campaign
description: Fix critical vulnerabilities before audit deadline with full tracking and reporting
timeout-minutes: 30
strict: true

on:
  workflow_dispatch:
    inputs:
      audit_date:
        description: "Audit deadline (YYYY-MM-DD)"
        required: true
      severity_threshold:
        description: "Minimum severity to fix (critical, high, medium)"
        required: false
        default: "high"
      max_issues:
        description: "Maximum vulnerabilities to process"
        required: false
        default: "500"

permissions:
  contents: read
  security-events: read

engine: copilot

safe-outputs:
  create-issue:
    expires: 2d
    max: 100
    labels: [security, campaign-tracker, cookie]
    group: true

tools:
  github:
    toolsets: [repos, search, code_security]
  repo-memory:
    branch-name: memory/campaigns
    file-glob: "memory/campaigns/security-compliance-*/**"

imports:
  - shared/mood.md
```

## Workflow Overview

This automation addresses the challenge of coordinating security remediation across the amplihack4 repository under audit deadline pressure. The framework identifies vulnerabilities through GitHub Security Advisories, creates tracked tasks, and enables progress monitoring with executive visibility.

## Core Execution Phases

**Phase 1 - Security Advisory Scanning**: Discovers vulnerabilities in amplihack4 repository dependencies using GitHub Security Advisories API, filtered by severity threshold (inputs.severity_threshold). Stores baseline metrics in repository memory at `memory/campaigns/security-compliance-{audit_date}/baseline.json`.

**Phase 2 - Issue Tracking**: Generates an epic issue for campaign oversight and individual vulnerability task issues (up to safe-outputs max: 100) with remediation guidance, CVE references, and fix instructions.

**Phase 3 - Campaign Metadata Storage**: Preserves campaign governance data in repo-memory including:

- Campaign ID and audit deadline
- Severity threshold configuration
- Approval status and compliance requirements
- Review checkpoints and escalation procedures

**Phase 4 - Remediation Automation**:

- Worker workflows process vulnerability tasks with dependency updates
- Monitor workflows track daily progress with status reports
- Completion workflows deliver final compliance reports before audit_date

## Amplihack4-Specific Adaptations

### Trigger Configuration

- `workflow_dispatch` with required `audit_date` input
- Optional `severity_threshold` (default: 'high')
- Optional `max_issues` (default: '500')

### Security Advisory Integration

Query GitHub Security Advisories for amplihack4 repository:

```
GET /repos/microsoft/amplihack4/dependabot/alerts
Filter by: severity >= {severity_threshold}, state: open
```

### Repository Memory Structure

Campaign data stored at:

```
memory/campaigns/security-compliance-{audit_date}/
├── baseline.json          # Initial vulnerability snapshot
├── metadata.json          # Campaign configuration
├── progress/              # Daily tracking updates
└── compliance-report.md   # Final audit deliverable
```

### Safe-Outputs Configuration

- Issue creation limited to 100 per workflow run
- 2-day expiration for task issues
- Auto-labeled: `security`, `campaign-tracker`, `cookie`
- Grouped to prevent flooding issue tracker

## Key Artifacts Generated

1. **Epic Issue**: Campaign status dashboard with:
   - Total vulnerabilities by severity
   - Remediation progress tracking
   - Escalation procedures
   - Days remaining until audit_date

2. **Vulnerability Task Issues**: Individual issues containing:
   - CVE reference and CVSS score
   - Affected package and version
   - Recommended fix version
   - Remediation instructions

3. **Baseline Metrics** (`baseline.json`):

   ```json
   {
     "campaign_id": "security-compliance-{audit_date}",
     "scan_date": "2026-02-15T00:00:00Z",
     "audit_deadline": "{audit_date}",
     "severity_threshold": "{severity_threshold}",
     "vulnerabilities": {
       "critical": 0,
       "high": 0,
       "medium": 0
     },
     "total_count": 0
   }
   ```

4. **Campaign Metadata** (`metadata.json`):

   ```json
   {
     "campaign_id": "security-compliance-{audit_date}",
     "created_at": "2026-02-15T00:00:00Z",
     "audit_date": "{audit_date}",
     "severity_threshold": "{severity_threshold}",
     "max_issues": "{max_issues}",
     "epic_issue_number": null,
     "status": "active",
     "governance": {
       "approval_required": true,
       "review_checkpoints": ["day_7", "day_3", "day_1"],
       "escalation_contact": "security-team@amplihack.example.com"
     }
   }
   ```

5. **Daily Progress Reports**: Stored in `progress/` directory
6. **Final Compliance Report**: Comprehensive audit deliverable

## Execution Steps

### Step 1: Initialize Campaign

```markdown
Create campaign directory structure in repo-memory:

- memory/campaigns/security-compliance-{audit_date}/
- Store input parameters in metadata.json
- Log workflow start time and configuration
```

### Step 2: Query Security Advisories

```markdown
Use GitHub code_security toolset to fetch advisories:

- GET /repos/microsoft/amplihack4/dependabot/alerts
- Filter by severity >= {severity_threshold}
- Filter by state: open
- Sort by severity (critical → high → medium)
- Limit to {max_issues} results
```

### Step 3: Generate Baseline Metrics

```markdown
Aggregate vulnerability data:

- Count by severity level (critical, high, medium)
- Calculate total vulnerability count
- Identify most critical packages
- Store in baseline.json
```

### Step 4: Create Epic Issue

```markdown
Generate campaign tracking issue with:

- Title: "Security Compliance Campaign - Audit {audit_date}"
- Body containing:
  - Campaign overview
  - Baseline metrics summary
  - Severity breakdown
  - Days remaining until audit
  - Progress tracking checklist
  - Escalation procedures
- Labels: security, campaign-tracker, epic
```

### Step 5: Create Vulnerability Task Issues

```markdown
For each vulnerability (up to safe-outputs max: 100):

- Title: "[Security] {CVE-ID}: {package_name}"
- Body containing:
  - CVE reference and CVSS score
  - Affected package and current version
  - Recommended fix version
  - Remediation steps
  - Related to epic issue #{epic_number}
- Labels: security, campaign-tracker, cookie
- Group similar vulnerabilities together
```

### Step 6: Store Campaign Metadata

```markdown
Save to repo-memory:

- Campaign configuration
- Epic issue reference
- Governance rules
- Review checkpoints
- Approval workflow requirements
```

### Step 7: Generate Initial Progress Report

```markdown
Create progress/day-0.md with:

- Campaign initialization summary
- Total issues created
- Next review checkpoint
- Recommended next actions
```

## Monitoring and Completion

### Daily Progress Tracking

Automated monitor workflow updates:

- Scan for closed vulnerability issues
- Calculate completion percentage
- Update epic issue progress
- Generate daily progress report
- Alert if behind schedule

### Audit Deadline Alerts

- 7 days before: Executive summary report
- 3 days before: Critical vulnerabilities status
- 1 day before: Final compliance checklist

### Campaign Completion

Final workflow generates:

- Comprehensive compliance report
- Remediation success metrics
- Remaining open vulnerabilities
- Recommendations for future campaigns

## Integration with Amplihack4 Ecosystem

### Philosophy Alignment

- **Ruthless Simplicity**: Single-purpose workflow for security compliance
- **Zero-BS Implementation**: Real vulnerability fixes, not stubs
- **Modular Design**: Self-contained campaign with clear boundaries

### Amplihack4 Tools Integration

- Uses `repo-memory` tool for persistent campaign state
- Leverages GitHub code_security toolset
- Compatible with existing issue management workflows

### User Preferences

- Respects verbosity preferences in progress reports
- Honors communication_style in issue templates
- Follows collaboration_style for review checkpoints

## Example Usage

```bash
# Trigger workflow via GitHub Actions UI or CLI
gh workflow run security-compliance.md \
  -f audit_date=2026-03-15 \
  -f severity_threshold=high \
  -f max_issues=500
```

## Success Criteria

- ✅ All vulnerabilities >= severity_threshold identified
- ✅ Epic issue created with campaign dashboard
- ✅ Vulnerability task issues created (up to 100)
- ✅ Baseline metrics stored in repo-memory
- ✅ Campaign metadata persisted with governance rules
- ✅ Initial progress report generated
- ✅ Monitoring workflows configured

## Notes

- Safe-outputs enforces 100 issue maximum per run
- Issues expire after 2 days if not closed
- Grouping prevents issue tracker flooding
- Campaign data persists in repo-memory for audit trail
- Workflow can be re-run to create additional batches if needed
