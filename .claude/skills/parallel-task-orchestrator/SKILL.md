# Parallel Task Orchestrator Skill

Ahoy! This skill coordinates multiple Claude Code agents workin' in parallel on independent sub-tasks from a master GitHub issue. Built fer scalin' complex features through concurrent agent execution.

## Overview

The Parallel Task Orchestrator skill deploys multiple Claude Code Task agents simultaneously to work on independent sub-issues derived from a master GitHub issue. Each agent operates in isolation with file-based coordination, ensurin' no conflicts and maximum parallelism.

**Validated at Scale**: Successfully orchestrated 5 agents producin' 4,000+ lines of code with 100% success rate during SimServ migration.

## When This Skill Activates

I load automatically when Claude Code detects:

- **Parallel Work Patterns**: Multiple independent sub-tasks in an issue
- **Scale Keywords**: "orchestrate", "coordinate agents", "parallel work", "multiple agents"
- **Issue Structure**: GitHub issue with numbered sub-tasks or checklist items
- **Explicit Request**: User mentions parallel orchestration or multi-agent coordination

**Example Triggers**:
- "Orchestrate agents to handle issue #1234"
- "Run parallel tasks from issue #567"
- "Deploy multiple agents for this feature"
- "Coordinate parallel work on sub-issues"

## How It Works

### Architecture

```
Master Issue (GitHub)
      ↓
   Parse Sub-Tasks
      ↓
  Create Sub-Issues ─→ [Agent 1] ─→ PR #1
      ↓              [Agent 2] ─→ PR #2
      ↓              [Agent 3] ─→ PR #3
      ↓              [Agent 4] ─→ PR #4
      ↓              [Agent 5] ─→ PR #5
      ↓
  Monitor Progress
      ↓
  Aggregate Results
```

### Core Components

1. **Issue Parser**: Extracts independent sub-tasks from master issue
2. **Sub-Issue Creator**: Creates trackable GitHub sub-issues
3. **Agent Deployer**: Spawns parallel Claude Code Task agents
4. **Status Monitor**: File-based coordination (`.agent_status.json`)
5. **Result Aggregator**: Combines outputs and creates summary

### Coordination Protocol

**File-Based Status** (Ruthlessly Simple):

```json
{
  "agent_id": "agent-1",
  "sub_issue": 123,
  "status": "in_progress",
  "start_time": "2025-12-01T12:00:00Z",
  "pr_number": 456,
  "completion_time": null,
  "error": null
}
```

**Status Values**:
- `pending`: Sub-issue created, agent not started
- `in_progress`: Agent workin' actively
- `completed`: PR created successfully
- `failed`: Agent encountered unrecoverable error

## Integration with Command

This skill works seamlessly with the `/amplihack:parallel-orchestrate` command:

```bash
# Skill auto-activates when command runs
/amplihack:parallel-orchestrate 1234

# Or explicitly invoke skill
Skill(parallel-task-orchestrator)
```

**Relationship**:
- **Command**: User-facing entry point, validates inputs, invokes skill
- **Skill**: Core orchestration logic, agent deployment, monitoring
- **Together**: Command handles CLI, skill handles execution

## 9-Step Workflow

### Step 1: Parse Master Issue

Extract sub-tasks from GitHub issue:

```python
# Automatic parsing of:
# - [ ] Sub-task 1: Description
# - [ ] Sub-task 2: Description
# - Numbered lists
# - Section headers with tasks
```

**Output**: List of independent sub-tasks with descriptions

### Step 2: Validate Independence

Verify sub-tasks can run in parallel:

- Check for file conflicts (different modules)
- Verify no sequential dependencies
- Confirm resource availability

**Fail-Fast**: If dependencies detected, recommend sequential workflow instead.

### Step 3: Create Sub-Issues

Generate GitHub sub-issues fer each task:

```python
# Creates issues with:
# - Title: "[Master #1234] Sub-task 1: Description"
# - Body: Full context, acceptance criteria
# - Labels: "parallel-orchestration", "sub-issue"
# - Link: References master issue
```

### Step 4: Deploy Agents

Spawn parallel Claude Code Task agents:

```python
from orchestration import OrchestratorSession, run_parallel

session = OrchestratorSession("parallel-orchestration")

agents = [
    session.create_process(
        prompt=f"Implement sub-issue #{issue.number}",
        process_id=f"agent-{i}",
        timeout=1800  # 30 minutes per agent
    )
    for i, issue in enumerate(sub_issues)
]

results = run_parallel(agents, max_workers=5)
```

### Step 5: Monitor Progress

Track agent status via file-based coordination:

```python
# Each agent writes status updates:
# .claude/runtime/parallel/{master_issue}/agent-{id}.status.json

# Monitor reads all status files
# Updates summary in real-time
```

### Step 6: Handle Partial Failures

Resilient execution continues despite individual failures:

```python
# Success criteria: >= 80% agents complete successfully
# Failed tasks: Create follow-up issues
# Timeout tasks: Marked for manual investigation
```

### Step 7: Aggregate Results

Combine agent outputs:

```python
# Collect PR numbers from successful agents
# Generate summary markdown
# Update master issue with progress
```

### Step 8: Create Summary

Generate comprehensive report:

```markdown
## Parallel Orchestration Results

**Master Issue**: #1234
**Total Sub-Tasks**: 5
**Successful**: 4
**Failed**: 1

### Completed
- [x] Sub-task 1 → PR #456
- [x] Sub-task 2 → PR #457
- [x] Sub-task 3 → PR #458
- [x] Sub-task 4 → PR #459

### Failed
- [ ] Sub-task 5: Import resolution error (Issue #460 created)
```

### Step 9: Update Master Issue

Post summary comment to master issue:

```python
# Comment includes:
# - Links to all PRs
# - Failure analysis
# - Next steps
# - Total execution time
```

## Examples

### Simple Orchestration (3 Sub-Tasks)

```bash
# Master issue #1234 has 3 independent tasks
/amplihack:parallel-orchestrate 1234

# Output:
# 🚀 Parsed 3 sub-tasks from issue #1234
# 📝 Created sub-issues: #1235, #1236, #1237
# 🤖 Deployed 3 agents
# ⏱️  Monitoring progress...
# ✅ Agent-1 completed → PR #1238
# ✅ Agent-2 completed → PR #1239
# ✅ Agent-3 completed → PR #1240
# 🎉 All agents succeeded! (Duration: 15m 32s)
```

### Complex Orchestration (10 Sub-Tasks)

```bash
# Large feature split into 10 modules
/amplihack:parallel-orchestrate 5678

# Output:
# 🚀 Parsed 10 sub-tasks from issue #5678
# 📝 Created sub-issues: #5679-#5688
# 🤖 Deployed 10 agents (max_workers=5, batched)
# ⏱️  Monitoring progress...
# [Batch 1: 5 agents]
# ✅ Agent-1 completed → PR #5689 (12m)
# ✅ Agent-2 completed → PR #5690 (15m)
# ✅ Agent-3 completed → PR #5691 (18m)
# ❌ Agent-4 failed: Import conflict
# ✅ Agent-5 completed → PR #5692 (14m)
# [Batch 2: 5 agents]
# ✅ Agent-6 completed → PR #5693 (10m)
# ✅ Agent-7 completed → PR #5694 (16m)
# ✅ Agent-8 completed → PR #5695 (13m)
# ✅ Agent-9 completed → PR #5696 (11m)
# ✅ Agent-10 completed → PR #5697 (17m)
# 🎉 9/10 agents succeeded! (Duration: 1h 8m)
# 📋 Created follow-up issue #5698 for failed task
```

### Handling Partial Failures

```bash
# 5 tasks, 1 fails midway
/amplihack:parallel-orchestrate 9000

# Output:
# 🚀 Parsed 5 sub-tasks from issue #9000
# 📝 Created sub-issues: #9001-#9005
# 🤖 Deployed 5 agents
# ⏱️  Monitoring progress...
# ✅ Agent-1 completed → PR #9006
# ✅ Agent-2 completed → PR #9007
# ❌ Agent-3 failed: Test timeout (30m)
# ✅ Agent-4 completed → PR #9008
# ✅ Agent-5 completed → PR #9009
#
# ⚠️  Partial success: 4/5 agents completed
# 📋 Created diagnostic issue #9010 for Agent-3 failure
#
# Next steps:
# 1. Review diagnostic issue #9010
# 2. Fix test timeout in sub-issue #9003
# 3. Re-run: /amplihack:parallel-orchestrate 9003 --retry
```

## Configuration Options

### Agent Limits

```python
# Set maximum concurrent agents
max_workers = 5  # Default: CPU count

# Set per-agent timeout
agent_timeout = 1800  # Default: 30 minutes

# Set retry attempts
max_retries = 1  # Default: no retries
```

### Issue Templates

```python
# Customize sub-issue template
issue_template = {
    "title": "[Master #{master}] {task_title}",
    "body": "{context}\n\n## Acceptance Criteria\n{criteria}",
    "labels": ["parallel-orchestration", "sub-issue"],
}
```

### Status Updates

```python
# Configure status update frequency
status_interval = 30  # Seconds between checks (default: 30s)

# Enable detailed logging
verbose_logging = True  # Default: False
```

## Philosophy Alignment

### Ruthless Simplicity

- **File-based coordination**: No complex message queues or databases
- **Direct subprocess spawning**: Leverages existing `orchestration` infrastructure
- **Simple status protocol**: JSON files, not distributed consensus
- **Trust in emergence**: Agents coordinate through files naturally

### Modular Design (Bricks & Studs)

**Bricks**:
- Issue Parser (independent, regeneratable)
- Agent Deployer (uses orchestration infrastructure)
- Status Monitor (file watcher)
- Result Aggregator (combiner)

**Studs**:
- `.agent_status.json` schema (public contract)
- Sub-issue template (standard format)
- Agent prompt format (consistent interface)

### Zero-BS Implementation

- No stubs: Every function works
- No mocks: Uses real GitHub API, real agents
- No dead code: All paths tested
- Real logging: Comprehensive traceability

## Benefits

### Scalability

- **10x throughput**: 5 agents complete in ~30min vs 2.5hrs sequential
- **Validated at scale**: 4,000+ lines of code produced in parallel
- **Batch support**: Handle 10+ sub-tasks efficiently

### Reliability

- **Partial failure resilience**: 80% success threshold
- **File-based coordination**: No network dependencies
- **Automatic recovery**: Failed tasks become follow-up issues
- **Timeout protection**: Runaway agents auto-terminated

### Maintainability

- **Simple coordination**: File-based, human-readable status
- **Auditable**: Complete logs per agent
- **Debuggable**: Status files persist for investigation
- **Regeneratable**: Can rebuild from specifications

## Trade-offs

### When to Use

✅ **Use Parallel Orchestration When**:
- Sub-tasks are truly independent (different modules)
- Feature naturally splits into 5+ tasks
- Tasks have similar complexity (avoid one slow blocker)
- Time savings justify orchestration overhead

❌ **Don't Use Parallel Orchestration When**:
- Tasks have sequential dependencies
- Fewer than 3 sub-tasks (overhead not worth it)
- Sub-tasks share critical files (conflict risk)
- Feature requires tight integration testing first

### Costs

- **Orchestration overhead**: ~5-10 minutes setup time
- **Resource usage**: Multiple Claude Code agents (CPU, memory)
- **Complexity**: More moving parts than sequential
- **GitHub API rate limits**: Sub-issue creation consumes quota

## Troubleshooting

### Agent Hangs

**Symptom**: Agent shows `in_progress` but no updates

**Solutions**:
1. Check agent log: `.claude/runtime/logs/{session_id}/agent-{id}.log`
2. Verify timeout set: Default 30min, increase if needed
3. Check file conflicts: Agent may be blocked on git operations

### Import Conflicts

**Symptom**: Multiple agents fail with import errors

**Solutions**:
1. Review sub-task independence validation
2. Check for shared utility modules
3. Consider sequential for shared components
4. Use git worktrees to isolate agent workspaces

### Status File Missing

**Symptom**: Monitor can't find `.agent_status.json`

**Solutions**:
1. Verify agent started successfully
2. Check log directory permissions
3. Confirm status file path: `.claude/runtime/parallel/{issue}/agent-{id}.status.json`
4. Check agent didn't crash before writing status

### PR Creation Failed

**Symptom**: Agent completes but no PR created

**Solutions**:
1. Review agent log for GitHub API errors
2. Verify branch created: `git branch -a`
3. Check GitHub token permissions
4. Manually create PR from agent's branch

## Common Pitfalls

### Pitfall 1: False Independence

**Problem**: Tasks appear independent but share critical code

**Example**:
```
Task 1: Add authentication
Task 2: Add authorization
→ Both modify user.py core functions
→ Merge conflict guaranteed
```

**Solution**: Validate independence during parsing, merge overlapping tasks

### Pitfall 2: Unbalanced Tasks

**Problem**: One task takes 3x longer than others

**Example**:
```
Task 1: Add button (5min)
Task 2: Add form (10min)
Task 3: Implement payment integration (60min)
→ Tasks 1-2 idle waiting for Task 3
```

**Solution**: Break large tasks into smaller chunks, balance complexity

### Pitfall 3: Resource Exhaustion

**Problem**: Too many concurrent agents overwhelm system

**Example**:
```
15 agents × Claude Code = 15 concurrent LLM calls
→ API rate limits hit
→ System memory exhausted
```

**Solution**: Use `max_workers` to limit concurrency, batch execution

## Best Practices

### 1. Plan Sub-Tasks Carefully

- Ensure true independence (different files/modules)
- Balance task complexity
- Define clear acceptance criteria
- Verify no shared state

### 2. Start Small

- Test with 3 agents before scaling to 10
- Validate coordination protocol works
- Verify status monitoring reliable
- Confirm PR creation successful

### 3. Monitor Actively

- Watch status updates in real-time
- Check logs if agent stalls
- Be ready to terminate runaway agents
- Collect metrics for future planning

### 4. Handle Failures Gracefully

- Expect ~10-20% failure rate on complex tasks
- Create follow-up issues automatically
- Document failure patterns
- Learn from orchestration metrics

## Integration with Existing Workflows

### With DEFAULT_WORKFLOW

Parallel orchestration happens WITHIN workflow steps:

```markdown
## Step 4: Implement Feature

**Option A: Sequential** (default)
- Implement complete feature in one session

**Option B: Parallel Orchestration** (for complex features)
- Use /amplihack:parallel-orchestrate to deploy agents
- Each agent follows DEFAULT_WORKFLOW independently
- Aggregate results before proceeding to Step 5
```

### With Document-Driven Development (DDD)

```bash
# Phase 1: Write documentation
/amplihack:ddd:2-docs

# Phase 2: Parallel implementation
/amplihack:parallel-orchestrate <issue>

# Each agent implements against docs
# Docs prevent divergence
```

### With CI/CD

```bash
# Pre-orchestration: Ensure CI green
# During orchestration: Agents create PRs
# Post-orchestration: Parallel CI runs on all PRs
# Final: Merge PRs sequentially after CI passes
```

## Metrics & Observability

### Tracked Metrics

```json
{
  "orchestration_id": "orch-1234-20251201",
  "master_issue": 1234,
  "total_sub_tasks": 5,
  "successful_agents": 4,
  "failed_agents": 1,
  "total_duration_seconds": 1832,
  "avg_agent_duration_seconds": 366,
  "prs_created": [456, 457, 458, 459],
  "follow_up_issues": [460],
  "resource_usage": {
    "max_concurrent_agents": 5,
    "peak_memory_mb": 2048,
    "total_api_calls": 47
  }
}
```

### Logs

```bash
# Orchestration session log
.claude/runtime/logs/{session_id}/session.log

# Individual agent logs
.claude/runtime/logs/{session_id}/agent-{id}.log

# Status snapshots
.claude/runtime/parallel/{issue}/agent-{id}.status.json

# Aggregated summary
.claude/runtime/parallel/{issue}/summary.md
```

## Future Enhancements

**Not Yet Implemented** (Trust in Emergence):

1. **Dynamic load balancing**: Reassign tasks from slow agents
2. **Intelligent retry**: Auto-retry failed agents with different strategies
3. **Cross-agent learning**: Share successful patterns between agents
4. **Dependency detection**: Automatically identify task dependencies from code analysis
5. **Cost optimization**: Model selection per task complexity

## References

- **Orchestration Infrastructure**: `.claude/tools/amplihack/orchestration/README.md`
- **Command Documentation**: `.claude/commands/amplihack/parallel-orchestrate.md`
- **Validation Case Study**: Issue #1783, SimServ migration (5 agents, 4,000+ LOC)
- **Philosophy**: `.claude/context/PHILOSOPHY.md` (Ruthless Simplicity, Bricks & Studs)

---

**Remember**: This skill orchestrates INDEPENDENCE, not INTEGRATION. If sub-tasks need tight coordination, use sequential workflow instead. Trust in emergence means the simplest solution (parallel files) beats complex synchronization.
