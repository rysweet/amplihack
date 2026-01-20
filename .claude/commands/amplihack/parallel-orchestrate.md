---
name: amplihack:parallel-orchestrate
version: 1.0.0
description: Deploy multiple Task agents in parallel for workstream orchestration
triggers:
  - "orchestrate parallel tasks"
  - "deploy parallel agents"
  - "parallel workstream"
  - "run agents in parallel"
  - "coordinate multiple agents"
invokes:
  - type: skill
    path: .claude/skills/parallel-task-orchestrator/SKILL.md
  - type: subagent
    path: .claude/agents/amplihack/specialized/worktree-manager.md
philosophy:
  - principle: Trust in Emergence
    application: Agents work independently without central coordination
  - principle: Ruthless Simplicity
    application: File-based status protocol, no complex messaging
  - principle: Modular Design
    application: Self-contained agents with clear boundaries
dependencies:
  required:
    - gh CLI (GitHub issue and PR operations)
    - git worktree support
    - .claude/tools/amplihack/orchestration/
  optional:
    - Neo4j (for advanced task dependency analysis)
examples:
  - "/amplihack:parallel-orchestrate 1783"
  - "/amplihack:parallel-orchestrate 1783 --agents 8"
  - "/amplihack:parallel-orchestrate 1783 --max-workers 5 --timeout 3600"
---

# Parallel Orchestrate Command

## Input Validation

@.claude/context/AGENT_INPUT_VALIDATION.md

Ahoy! Coordinate multiple Claude Code agents workin' in parallel on independent sub-tasks from a master GitHub issue.

## Synopsis

```bash
/amplihack:parallel-orchestrate <issue-number> [options]
```

## Description

The Parallel Task Orchestration command deploys multiple Claude Code Task agents simultaneously to work on independent sub-tasks. Each agent operates in isolation with file-based coordination, creatin' separate PRs that can be merged independently.

**Use Case**: Scale complex features by splittin' them into independent sub-tasks and parallelizin' implementation across multiple AI agents.

## Parameters

### Required

- **`<issue-number>`**: GitHub issue number containin' sub-tasks to orchestrate

### Optional

- **`--max-workers <N>`**: Maximum concurrent agents (default: 5)
- **`--timeout <seconds>`**: Per-agent timeout in seconds (default: 1800 = 30min)
- **`--retry`**: Retry failed tasks from previous orchestration
- **`--dry-run`**: Parse and validate without deploying agents
- **`--batch-size <N>`**: Process in batches of N agents (default: unlimited)

## Examples

### Basic Usage

```bash
# Orchestrate all sub-tasks from issue #1234
/amplihack:parallel-orchestrate 1234
```

**Output**:
```
🚀 Parsed 5 sub-tasks from issue #1234
📝 Created sub-issues: #1235, #1236, #1237, #1238, #1239
🤖 Deployed 5 agents (max_workers=5)
⏱️  Monitoring progress...
✅ Agent-1 completed → PR #1240 (12m 45s)
✅ Agent-2 completed → PR #1241 (15m 22s)
✅ Agent-3 completed → PR #1242 (18m 03s)
✅ Agent-4 completed → PR #1243 (14m 17s)
✅ Agent-5 completed → PR #1244 (16m 51s)
🎉 All agents succeeded! Total duration: 18m 03s
```

### Limit Concurrent Agents

```bash
# Run maximum 3 agents at once
/amplihack:parallel-orchestrate 1234 --max-workers 3
```

**Use Case**: Resource-constrained environments or API rate limits

### Custom Timeout

```bash
# Allow 60 minutes per agent (complex tasks)
/amplihack:parallel-orchestrate 1234 --timeout 3600
```

**Use Case**: Complex sub-tasks needin' more time

### Batch Processing

```bash
# Process in batches of 3 agents
/amplihack:parallel-orchestrate 1234 --batch-size 3
```

**Output**:
```
🚀 Parsed 10 sub-tasks from issue #1234
📝 Created sub-issues: #1235-#1244
🤖 Deployed 10 agents in batches (batch_size=3)

[Batch 1: Agents 1-3]
⏱️  Monitoring batch 1...
✅ Agent-1 completed → PR #1245 (10m)
✅ Agent-2 completed → PR #1246 (12m)
✅ Agent-3 completed → PR #1247 (11m)

[Batch 2: Agents 4-6]
⏱️  Monitoring batch 2...
✅ Agent-4 completed → PR #1248 (13m)
✅ Agent-5 completed → PR #1249 (9m)
✅ Agent-6 completed → PR #1250 (15m)

[Batch 3: Agents 7-9]
⏱️  Monitoring batch 3...
✅ Agent-7 completed → PR #1251 (11m)
❌ Agent-8 failed: Test timeout
✅ Agent-9 completed → PR #1252 (14m)

[Batch 4: Agent 10]
⏱️  Monitoring batch 4...
✅ Agent-10 completed → PR #1253 (10m)

🎉 9/10 agents succeeded! Total duration: 52m
📋 Created follow-up issue #1254 for Agent-8 failure
```

### Dry Run

```bash
# Validate sub-tasks without deploying agents
/amplihack:parallel-orchestrate 1234 --dry-run
```

**Output**:
```
🔍 DRY RUN MODE
🚀 Parsed 5 sub-tasks from issue #1234

Sub-tasks identified:
1. Add authentication module (estimated complexity: medium)
2. Add authorization middleware (estimated complexity: low)
3. Implement JWT tokens (estimated complexity: medium)
4. Add user management API (estimated complexity: high)
5. Create integration tests (estimated complexity: medium)

Independence validation:
✅ No file conflicts detected
✅ No sequential dependencies
⚠️  Tasks 3-4 may share user.py utilities

Estimated duration: 15-20 minutes (parallel)
Estimated PRs: 5

Recommendation: Proceed with orchestration
To run: /amplihack:parallel-orchestrate 1234
```

### Retry Failed Tasks

```bash
# Retry previously failed orchestration
/amplihack:parallel-orchestrate 1234 --retry
```

**Output**:
```
🔄 Retry mode: Loading previous orchestration state
📂 Found orchestration: orch-1234-20251201-1200
📋 Previous results: 4/5 succeeded, 1 failed

Retrying failed tasks:
- Agent-3: Import resolution error

🤖 Deployed 1 agent for retry
⏱️  Monitoring progress...
✅ Agent-3 completed → PR #1245 (10m)

🎉 Retry successful! Original orchestration now complete.
```

## Step-by-Step Workflow

### Step 1: Issue Parsing

Command parses the master GitHub issue to extract sub-tasks:

**Supported Formats**:

```markdown
<!-- GitHub issue checklist format -->
- [ ] Sub-task 1: Add authentication
- [ ] Sub-task 2: Add authorization
- [ ] Sub-task 3: Add JWT support

<!-- Numbered list format -->
1. Implement user model
2. Create user API
3. Add user tests

<!-- Section headers -->
## Sub-Tasks
### Authentication Module
Implement OAuth2 authentication...

### Authorization Middleware
Add role-based access control...
```

**Output**: List of parsed sub-tasks with titles and descriptions

### Step 2: Independence Validation

Validates sub-tasks can run in parallel:

**Checks**:
- File overlap analysis (different modules preferred)
- Dependency detection (no sequential requirements)
- Resource availability (GitHub API, system resources)

**Decision**:
- ✅ **Proceed**: Sub-tasks are independent
- ❌ **Abort**: Dependencies detected, recommend sequential workflow
- ⚠️ **Warning**: Potential conflicts identified, user confirmation required

### Step 3: Sub-Issue Creation

Creates GitHub sub-issues for each task:

**Template**:
```markdown
Title: [Master #1234] Sub-task 1: Add authentication

Body:
**Master Issue**: #1234
**Task**: Add authentication module

## Context
[Extracted from master issue]

## Acceptance Criteria
- Authentication module implemented
- Tests passing
- Documentation updated

## Notes
This is part of parallel orchestration. See master issue for context.

Labels: parallel-orchestration, sub-issue
```

**Output**: Sub-issue numbers created

### Step 4: Agent Deployment

Spawns parallel Claude Code Task agents:

**Per Agent**:
- Unique process ID: `agent-{N}`
- Dedicated log file: `.claude/runtime/logs/{session}/agent-{N}.log`
- Status file: `.claude/runtime/parallel/{issue}/agent-{N}.status.json`
- Timeout: 30 minutes (default, configurable)
- Working directory: Git worktree (isolated workspace)

**Orchestration**:
```python
from orchestration import OrchestratorSession, run_parallel

session = OrchestratorSession("parallel-orch")
agents = [session.create_process(...) for task in sub_tasks]
results = run_parallel(agents, max_workers=5)
```

### Step 5: Progress Monitoring

Real-time status tracking via file-based protocol:

**Status File** (`.agent_status.json`):
```json
{
  "agent_id": "agent-1",
  "sub_issue": 1235,
  "status": "in_progress",
  "start_time": "2025-12-01T12:00:00Z",
  "last_update": "2025-12-01T12:05:00Z",
  "pr_number": null,
  "branch": "feat/issue-1235",
  "completion_time": null,
  "error": null,
  "progress_percentage": 45
}
```

**Console Output**:
```
⏱️  Monitoring progress (updates every 30s)...
[12:00] Agent-1: Analyzing codebase (10%)
[12:02] Agent-2: Creating implementation plan (20%)
[12:05] Agent-1: Implementing feature (45%)
[12:08] Agent-3: Running tests (75%)
[12:10] Agent-2: Creating PR (90%)
[12:12] Agent-2: ✅ Completed → PR #1241
```

### Step 6: Partial Failure Handling

Resilient execution continues despite failures:

**Success Threshold**: 80% agents must complete successfully

**Failure Actions**:
1. Log detailed error to agent log file
2. Create diagnostic follow-up issue with:
   - Error details
   - Agent log excerpt
   - Suggested fixes
   - Link to original sub-issue
3. Continue monitoring remaining agents
4. Include failure in final summary

**Example Failure**:
```
❌ Agent-3 failed after 28m: Test timeout
📋 Created diagnostic issue #1246: "Agent-3 Test Timeout Investigation"
⏱️  Continuing with remaining agents...
```

### Step 7: Result Aggregation

Collects outputs from all agents:

**Success Metrics**:
- PR numbers created
- Execution duration per agent
- Total lines of code added
- Tests passing status

**Failure Metrics**:
- Error types
- Failure stage (parsing, implementation, testing, PR)
- Timeout occurrences

**Example Summary**:
```json
{
  "master_issue": 1234,
  "total_sub_tasks": 5,
  "successful": 4,
  "failed": 1,
  "prs_created": [1240, 1241, 1242, 1243],
  "follow_up_issues": [1246],
  "duration_seconds": 1083,
  "lines_of_code": 4127
}
```

### Step 8: Summary Generation

Creates markdown summary report:

```markdown
## Parallel Orchestration Results

**Master Issue**: #1234 - Add authentication system
**Orchestration ID**: orch-1234-20251201-1200
**Duration**: 18m 03s
**Success Rate**: 4/5 (80%)

### Successful Tasks

| Agent | Sub-Issue | PR | Duration | LOC |
|-------|-----------|-----|----------|-----|
| Agent-1 | #1235 | [PR #1240](link) | 12m 45s | 823 |
| Agent-2 | #1236 | [PR #1241](link) | 15m 22s | 1,045 |
| Agent-3 | #1237 | [PR #1242](link) | 18m 03s | 1,387 |
| Agent-5 | #1239 | [PR #1244](link) | 16m 51s | 872 |

**Total LOC**: 4,127 lines across 4 PRs

### Failed Tasks

| Agent | Sub-Issue | Error | Duration | Follow-Up |
|-------|-----------|-------|----------|-----------|
| Agent-4 | #1238 | Test timeout | 30m | [Issue #1246](link) |

### Next Steps

1. Review and merge successful PRs (#1240, #1241, #1242, #1244)
2. Investigate test timeout in diagnostic issue #1246
3. Fix and re-run sub-issue #1238: `/amplihack:parallel-orchestrate 1238 --retry`

### Performance Metrics

- **Parallel vs Sequential**: 18m vs ~90m estimated (5x speedup)
- **Peak Concurrency**: 5 agents
- **Average Agent Duration**: 14m 37s
- **Success Rate**: 80%

---
🤖 Generated by Parallel Task Orchestrator
📊 Full logs: `.claude/runtime/logs/orch-1234-20251201-1200/`
```

### Step 9: Master Issue Update

Posts summary comment to master issue:

**Comment Content**:
- Link to full summary
- Quick status overview
- Links to all PRs
- Next action items

**Example Comment**:
```markdown
## 🤖 Parallel Orchestration Complete

**Status**: 4/5 tasks completed successfully (80%)
**Duration**: 18 minutes
**PRs Created**: #1240, #1241, #1242, #1244

See [full summary](link) for details.

### Action Required
- [ ] Review and merge PR #1240
- [ ] Review and merge PR #1241
- [ ] Review and merge PR #1242
- [ ] Review and merge PR #1244
- [ ] Investigate test timeout in issue #1246

---
Orchestration ID: orch-1234-20251201-1200
```

## Common Scenarios

### Scenario 1: Feature Development

**Use Case**: Implement large feature split into independent modules

```bash
# Master issue: "Add e-commerce shopping cart"
# Sub-tasks:
# - Cart data model
# - Cart API endpoints
# - Cart UI components
# - Cart persistence
# - Cart tests

/amplihack:parallel-orchestrate 5000
```

**Result**: 5 agents create 5 PRs in ~20 minutes vs ~100 minutes sequential

### Scenario 2: Bug Fixes

**Use Case**: Multiple independent bugs in different modules

```bash
# Master issue: "Q4 Bug Bash Results"
# Sub-tasks:
# - Fix auth redirect bug
# - Fix payment calculation error
# - Fix email formatting
# - Fix export timeout
# - Fix search pagination

/amplihack:parallel-orchestrate 6000
```

**Result**: Parallel bug fixing across codebase

### Scenario 3: Refactoring

**Use Case**: Refactor multiple independent modules

```bash
# Master issue: "TypeScript Migration - Phase 1"
# Sub-tasks:
# - Convert utils/ to TypeScript
# - Convert models/ to TypeScript
# - Convert services/ to TypeScript
# - Convert api/ to TypeScript
# - Update build config

/amplihack:parallel-orchestrate 7000
```

**Result**: Parallel module conversions

### Scenario 4: Documentation

**Use Case**: Create comprehensive documentation for multiple components

```bash
# Master issue: "Complete API Documentation"
# Sub-tasks:
# - Document auth endpoints
# - Document user endpoints
# - Document cart endpoints
# - Document payment endpoints
# - Create API examples

/amplihack:parallel-orchestrate 8000
```

**Result**: Parallel documentation generation

## Troubleshooting

### Problem: Agents Not Starting

**Symptoms**:
- Command hangs after "🤖 Deployed N agents"
- No status updates appear

**Solutions**:
1. Check Claude Code installation: `claude --version`
2. Verify GitHub token: `gh auth status`
3. Check system resources: `top`, `free -h`
4. Review session log: `.claude/runtime/logs/{session}/session.log`

### Problem: All Agents Failing

**Symptoms**:
- Multiple agents fail with similar errors
- Quick failures (< 1 minute)

**Solutions**:
1. Check master issue format (valid sub-tasks?)
2. Verify sub-issues created: `gh issue list --label sub-issue`
3. Check agent logs for common error pattern
4. Validate issue independence (may need sequential workflow)

### Problem: Partial Progress Then Stall

**Symptoms**:
- Some agents complete, others hang indefinitely
- Status shows `in_progress` but no updates

**Solutions**:
1. Check individual agent logs
2. Verify no file conflicts: `git status` in agent workspaces
3. Check resource exhaustion: memory, disk space
4. Manually terminate hung agents: `kill -9 <pid>` (PIDs in logs)

### Problem: PRs Not Creating

**Symptoms**:
- Agents complete successfully
- Status shows `completed` but no PR number

**Solutions**:
1. Check GitHub API rate limits: `gh api rate_limit`
2. Verify branch created: `git branch -a | grep feat/issue`
3. Check GitHub token permissions (needs repo write access)
4. Manually create PR: `gh pr create --title "..." --body "..."`

### Problem: Import Conflicts

**Symptoms**:
- Multiple agents fail with import/dependency errors
- Error messages mention missing modules

**Solutions**:
1. Sub-tasks share dependencies (not truly independent)
2. Run `uv pip install` before orchestration
3. Consider sequential workflow for shared components
4. Use git worktrees to isolate agent environments

## Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success - all agents completed | Review PRs, merge when ready |
| 1 | Partial success (>= 80%) | Review failures, retry if needed |
| 2 | Majority failure (< 80%) | Investigate root cause, may need sequential |
| 3 | Parse failure | Fix master issue format |
| 4 | Validation failure | Tasks have dependencies, use sequential |
| 5 | GitHub API error | Check token, rate limits |
| 9 | System error | Check logs, system resources |

## Best Practices

### 1. Plan Sub-Tasks for Independence

✅ **Good Independence**:
```
- Add user authentication (touches auth/)
- Add payment processing (touches payment/)
- Add email notifications (touches email/)
```

❌ **Poor Independence**:
```
- Add user model (touches models/user.py)
- Add user API (touches models/user.py)
- Add user validation (touches models/user.py)
```

### 2. Balance Task Complexity

✅ **Balanced**:
```
- Add login form (10min)
- Add signup form (10min)
- Add password reset (15min)
- Add 2FA (15min)
```

❌ **Unbalanced**:
```
- Add logout button (2min)
- Implement OAuth2 provider (60min)
```

### 3. Start Small, Scale Up

**First Time**:
```bash
# Try with 3 agents
/amplihack:parallel-orchestrate 1234 --max-workers 3
```

**After Validation**:
```bash
# Scale to 5-10 agents
/amplihack:parallel-orchestrate 5678 --max-workers 10
```

### 4. Monitor Actively

```bash
# In separate terminal, watch status files
watch -n 5 'ls -lh .claude/runtime/parallel/1234/*.status.json'

# Or tail orchestration log
tail -f .claude/runtime/logs/orch-1234-*/session.log
```

## Configuration

Configuration via environment variables:

```bash
# Maximum concurrent agents (overrides --max-workers)
export AMPLIHACK_MAX_PARALLEL_AGENTS=10

# Default per-agent timeout in seconds
export AMPLIHACK_AGENT_TIMEOUT=3600

# Enable verbose logging
export AMPLIHACK_PARALLEL_VERBOSE=1

# Status update frequency (seconds)
export AMPLIHACK_STATUS_INTERVAL=15

# Success threshold percentage
export AMPLIHACK_SUCCESS_THRESHOLD=80
```

## Integration with Other Commands

### With /amplihack:analyze

```bash
# Analyze codebase first
/amplihack:analyze src/

# Then orchestrate based on analysis
/amplihack:parallel-orchestrate 1234
```

### With /amplihack:ddd Commands

```bash
# Document-driven development workflow
/amplihack:ddd:2-docs 1234  # Write docs first
/amplihack:parallel-orchestrate 1234  # Parallel implementation
/amplihack:ddd:5-finish 1234  # Final cleanup
```

### With /fix Command

```bash
# If orchestration fails with common patterns
/fix import  # Fix import errors across all agents
/amplihack:parallel-orchestrate 1234 --retry
```

## Files Created

### Status Files

```
.claude/runtime/parallel/{issue}/
├── agent-1.status.json
├── agent-2.status.json
├── agent-3.status.json
├── agent-4.status.json
├── agent-5.status.json
└── summary.md
```

### Log Files

```
.claude/runtime/logs/{session_id}/
├── session.log
├── agent-1.log
├── agent-2.log
├── agent-3.log
├── agent-4.log
└── agent-5.log
```

### Git Branches

```bash
# Each agent creates isolated branch
git branch
  feat/issue-1235-agent-1
  feat/issue-1236-agent-2
  feat/issue-1237-agent-3
  feat/issue-1238-agent-4
  feat/issue-1239-agent-5
```

## Performance Expectations

### Throughput Improvement

| Sub-Tasks | Sequential Time | Parallel Time | Speedup |
|-----------|----------------|---------------|---------|
| 3 | 45 min | 15 min | 3x |
| 5 | 75 min | 20 min | 3.75x |
| 10 | 150 min | 35 min | 4.3x |

*Assumes balanced task complexity and no failures*

### Resource Usage

| Agents | Memory (Est) | CPU (Est) | GitHub API Calls |
|--------|--------------|-----------|------------------|
| 3 | 1.5 GB | 60% | 15-20 |
| 5 | 2.5 GB | 100% | 25-30 |
| 10 | 5 GB | 200% | 50-60 |

## Validation

**Feature Validated**: Issue #1783 - SimServ Migration
- **Sub-Tasks**: 5 independent module conversions
- **Agents Deployed**: 5
- **Success Rate**: 100% (5/5)
- **Total LOC**: 4,127 lines
- **Duration**: 31 minutes (vs ~150 minutes sequential)
- **PRs Created**: 5 (all merged successfully)

## See Also

- **Skill Documentation**: `.claude/skills/parallel-task-orchestrator/SKILL.md`
- **Orchestration Infrastructure**: `.claude/tools/amplihack/orchestration/README.md`
- **DEFAULT_WORKFLOW**: Integration with standard workflow
- **Philosophy**: Ruthless Simplicity, Bricks & Studs design

---

**Remember**: Parallel orchestration be fer INDEPENDENT tasks only. If yer sub-tasks be dependin' on each other, use sequential workflow instead. The sea o' code be vast, but only parallel waters be worth sailin' with this command! ⛵