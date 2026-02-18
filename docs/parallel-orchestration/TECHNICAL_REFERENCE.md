# Parallel Task Orchestration - Technical Reference

Technical specification fer the Parallel Task Orchestrator, includin' API contracts, status protocol, configuration schema, and error codes.

## Status File Format

### Schema Version 1.0

**Location**: `.claude/runtime/parallel/{master_issue}/agent-{id}.status.json`

**Structure**:
```json
{
  "schema_version": "1.0",
  "agent_id": "agent-1",
  "sub_issue": 1235,
  "status": "in_progress",
  "start_time": "2025-12-01T12:00:00Z",
  "last_update": "2025-12-01T12:15:30Z",
  "completion_time": null,
  "pr_number": null,
  "branch_name": "feat/issue-1235-authentication",
  "error": null,
  "progress_percentage": 45,
  "current_stage": "implementation",
  "metadata": {
    "working_dir": "/project/worktrees/agent-1",
    "model": "claude-sonnet-4-5",
    "timeout": 1800,
    "retry_count": 0
  }
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `schema_version` | string | Yes | Status file schema version (currently "1.0") |
| `agent_id` | string | Yes | Unique agent identifier (`agent-{N}`) |
| `sub_issue` | integer | Yes | GitHub sub-issue number |
| `status` | enum | Yes | Current status (see Status Values below) |
| `start_time` | ISO8601 | Yes | Agent start timestamp (UTC) |
| `last_update` | ISO8601 | Yes | Last status update timestamp (UTC) |
| `completion_time` | ISO8601 | No | Task completion timestamp (UTC), null if not completed |
| `pr_number` | integer | No | Created PR number, null if not yet created |
| `branch_name` | string | Yes | Git branch name for this task |
| `error` | string | No | Error message if status is "failed", null otherwise |
| `progress_percentage` | integer | No | Estimated completion (0-100), null if unknown |
| `current_stage` | string | No | Human-readable current stage description |
| `metadata` | object | No | Additional agent metadata |

### Status Values

| Status | Description | Valid Transitions |
|--------|-------------|-------------------|
| `pending` | Sub-issue created, agent not started | → `in_progress` |
| `in_progress` | Agent actively working on task | → `completed`, `failed` |
| `completed` | Task completed successfully, PR created | (terminal state) |
| `failed` | Task failed with unrecoverable error | → `in_progress` (retry only) |

### Status Lifecycle

```
[pending]
   ↓ (agent starts)
[in_progress]
   ├─→ (success) [completed]
   └─→ (error) [failed]
        └─→ (retry) [in_progress]
```

### Progress Stages

Standard stages during `in_progress` status:

```
current_stage values:
- "initializing": Setting up environment
- "analyzing": Analyzing codebase
- "planning": Creating implementation plan
- "implementation": Writing code
- "testing": Running tests
- "fixing": Fixing test failures
- "documenting": Updating documentation
- "creating_pr": Creating pull request
```

### Update Frequency

Status files MUST be updated:
- On status transitions (always)
- Every 30 seconds during `in_progress` (heartbeat)
- On significant progress milestones (>= 10% change)

### Example Status Progression

**T+0s: Agent Starts**
```json
{
  "status": "in_progress",
  "start_time": "2025-12-01T12:00:00Z",
  "last_update": "2025-12-01T12:00:00Z",
  "progress_percentage": 0,
  "current_stage": "initializing"
}
```

**T+120s: Implementation Begins**
```json
{
  "status": "in_progress",
  "last_update": "2025-12-01T12:02:00Z",
  "progress_percentage": 25,
  "current_stage": "implementation"
}
```

**T+600s: Testing**
```json
{
  "status": "in_progress",
  "last_update": "2025-12-01T12:10:00Z",
  "progress_percentage": 75,
  "current_stage": "testing"
}
```

**T+900s: Completed**
```json
{
  "status": "completed",
  "last_update": "2025-12-01T12:15:00Z",
  "completion_time": "2025-12-01T12:15:00Z",
  "progress_percentage": 100,
  "current_stage": "completed",
  "pr_number": 1240,
  "branch_name": "feat/issue-1235-authentication"
}
```

## Agent Contract Specification

### Agent Responsibilities

Agents MUST:
1. Create status file immediately on start
2. Update status file every 30 seconds
3. Set progress_percentage when estimable
4. Write detailed errors to status file on failure
5. Create PR before marking status as "completed"
6. Clean up resources on exit (success or failure)

Agents SHOULD:
1. Update current_stage on major transitions
2. Log all operations to agent log file
3. Commit work incrementally
4. Run tests before creating PR
5. Include sub-issue number in PR title

Agents MUST NOT:
1. Modify files outside assigned task scope
2. Push to main/master branch directly
3. Delete or modify other agents' status files
4. Block on user input (must work autonomously)

### Agent Prompt Template

```markdown
You are Agent {agent_id} working on sub-issue #{sub_issue}.

**Master Issue**: #{master_issue}
**Sub-Task**: {task_title}
**Your Branch**: {branch_name}
**Working Directory**: {working_dir}
**Timeout**: {timeout} seconds

## Task Description
{task_description}

## Acceptance Criteria
{acceptance_criteria}

## Requirements

1. **Status Updates**: Update `.claude/runtime/parallel/{master_issue}/agent-{id}.status.json` every 30 seconds
2. **Branch**: Work on branch `{branch_name}` only
3. **PR Creation**: Create PR before marking completed
4. **Testing**: Run all tests, ensure passing
5. **Documentation**: Update relevant docs
6. **Autonomous**: Work independently, no user input

## Status File Location
{status_file_path}

## Success Criteria
- [ ] Status file created and updated regularly
- [ ] Implementation complete per acceptance criteria
- [ ] All tests passing
- [ ] PR created with proper title/description
- [ ] Status marked "completed"

Begin implementation now.
```

### Agent Environment

**Required Environment Variables**:
```bash
AGENT_ID=agent-1
MASTER_ISSUE=1234
SUB_ISSUE=1235
BRANCH_NAME=feat/issue-1235-authentication
STATUS_FILE=/path/to/.claude/runtime/parallel/1234/agent-1.status.json
WORKING_DIR=/path/to/worktree/agent-1
TIMEOUT=1800
```

**File Locations**:
```
Working Directory: {project_root}/worktrees/agent-{id}/
Status File: {project_root}/.claude/runtime/parallel/{master_issue}/agent-{id}.status.json
Log File: {project_root}/.claude/runtime/logs/{session_id}/agent-{id}.log
```

## Orchestrator API

### OrchestratorSession

```python
from orchestration import OrchestratorSession

session = OrchestratorSession(
    pattern_name: str = "parallel-orchestration",
    working_dir: Path = Path.cwd(),
    base_log_dir: Path = Path(".claude/runtime/logs"),
    model: Optional[str] = None
)

# Creates configured ClaudeProcess instance
process = session.create_process(
    prompt: str,
    process_id: Optional[str] = None,  # Auto-generated if None
    timeout: Optional[int] = None
) -> ClaudeProcess

# Logging
session.log(message: str) -> None

# Paths
session.get_session_log_path() -> Path
session.get_process_log_path(process_id: str) -> Path
```

### Parallel Execution

```python
from orchestration import run_parallel

results = run_parallel(
    processes: List[ClaudeProcess],
    max_workers: Optional[int] = None  # Defaults to CPU count
) -> List[ProcessResult]
```

**Returns**: List of ProcessResult in completion order (not input order)

**Guarantees**:
- All processes execute (no early termination)
- Exceptions caught and converted to failed ProcessResult
- Resources cleaned up for all processes
- Thread-safe execution

### ProcessResult

```python
@dataclass
class ProcessResult:
    exit_code: int       # 0 = success, -1 = timeout/fatal, >0 = error
    output: str          # Combined stdout
    stderr: str          # Stderr output
    duration: float      # Execution time (seconds)
    process_id: str      # Process identifier
```

## Sub-Issue Template

### Generated Sub-Issue Format

```markdown
**Title**: [Master #{master_issue}] {task_title}

**Body**:

**Master Issue**: #{master_issue}
**Task**: {task_title}

## Context

{task_description}

{extracted_context_from_master_issue}

## Acceptance Criteria

{acceptance_criteria}

## Implementation Notes

- **Branch**: `feat/issue-{sub_issue}-{slug}`
- **Files to Modify**: {file_list}
- **Related Issues**: #{related_issue_1}, #{related_issue_2}

## Testing Requirements

- [ ] Unit tests added/updated
- [ ] Integration tests passing
- [ ] Manual testing completed

## Documentation Requirements

- [ ] Code comments added
- [ ] API documentation updated
- [ ] User guide updated (if applicable)

## Success Criteria

Task is complete when:
1. All acceptance criteria met
2. All tests passing
3. Documentation updated
4. PR created and linked
5. CI passing

---

**Part of Parallel Orchestration**: This is a sub-task created by parallel orchestration. See master issue #{master_issue} for full context.

**Orchestration ID**: {orchestration_id}
**Agent**: agent-{agent_number}

**Labels**: `parallel-orchestration`, `sub-issue`
```

### Sub-Issue Parsing Patterns

**Checklist Format**:
```markdown
- [ ] Task 1: Description here
- [ ] Task 2: Description here
```

**Numbered List Format**:
```markdown
1. Task 1 description
2. Task 2 description
```

**Section Header Format**:
```markdown
## Task 1: Title
Description here...

## Task 2: Title
Description here...
```

### Parsing Rules

1. Extract task title from first line
2. Extract description from subsequent lines until next task
3. Infer acceptance criteria from "must", "should", "will" statements
4. Identify file mentions (paths matching `*/` patterns)
5. Skip tasks marked as completed (`[x]`)

## Configuration Schema

### Environment Variables

```bash
# Maximum concurrent agents (default: 5)
AMPLIHACK_MAX_PARALLEL_AGENTS=10

# Per-agent timeout in seconds (default: 1800 = 30min)
AMPLIHACK_AGENT_TIMEOUT=3600

# Status update interval in seconds (default: 30)
AMPLIHACK_STATUS_INTERVAL=15

# Success threshold percentage (default: 80)
AMPLIHACK_SUCCESS_THRESHOLD=90

# Verbose logging (default: false)
AMPLIHACK_PARALLEL_VERBOSE=true

# GitHub API token (required)
GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# Working directory for agents (default: ./worktrees)
AMPLIHACK_WORKTREE_DIR=/tmp/agents
```

### Configuration File

**Location**: `.claude/config/parallel-orchestration.json`

```json
{
  "version": "1.0",
  "defaults": {
    "max_workers": 5,
    "agent_timeout": 1800,
    "status_interval": 30,
    "success_threshold": 80
  },
  "issue_template": {
    "title": "[Master #{master}] {task_title}",
    "labels": ["parallel-orchestration", "sub-issue"],
    "body_template": "path/to/template.md"
  },
  "agent": {
    "model": "claude-sonnet-4-5",
    "stream_output": true,
    "log_level": "INFO"
  },
  "monitoring": {
    "status_check_interval": 30,
    "stale_threshold": 300,
    "notify_on_failure": true
  }
}
```

## Error Codes

### Command Exit Codes

| Code | Name | Description | Action |
|------|------|-------------|--------|
| 0 | SUCCESS | All agents completed successfully | Review PRs, merge |
| 1 | PARTIAL_SUCCESS | >= 80% agents completed | Review failures, retry if needed |
| 2 | MAJORITY_FAILURE | < 80% agents completed | Investigate root cause |
| 3 | PARSE_ERROR | Failed to parse master issue | Fix issue format |
| 4 | VALIDATION_ERROR | Sub-tasks not independent | Restructure or use sequential |
| 5 | GITHUB_API_ERROR | GitHub API request failed | Check token, rate limits |
| 6 | TIMEOUT_ERROR | Orchestration timeout exceeded | Increase timeout or reduce tasks |
| 7 | RESOURCE_ERROR | Insufficient system resources | Free resources or reduce max_workers |
| 8 | AGENT_SPAWN_ERROR | Failed to spawn agent processes | Check Claude Code installation |
| 9 | SYSTEM_ERROR | Unexpected system error | Check logs for details |

### Agent Error Codes

Embedded in status file `error` field:

```json
{
  "status": "failed",
  "error": "IMPORT_CONFLICT: Module 'auth.utils' not found. Dependency not available in agent workspace."
}
```

**Error Code Format**: `ERROR_TYPE: Human-readable message`

**Common Error Types**:
- `IMPORT_CONFLICT`: Import/dependency resolution failed
- `TEST_FAILURE`: Tests failed after implementation
- `TEST_TIMEOUT`: Tests exceeded timeout limit
- `BUILD_ERROR`: Build/compilation failed
- `FILE_CONFLICT`: Git merge conflict in working directory
- `API_ERROR`: GitHub API call failed
- `TIMEOUT`: Agent exceeded allotted time
- `VALIDATION_ERROR`: Output didn't meet acceptance criteria
- `RESOURCE_ERROR`: Insufficient disk/memory
- `UNKNOWN`: Unexpected error

## Monitoring Protocol

### Status Polling

Monitor polls status files every N seconds (configurable, default 30s):

```python
def monitor_agents(master_issue: int, agent_ids: List[str]) -> None:
    """Monitor agent progress via status files"""
    while any_agent_active():
        for agent_id in agent_ids:
            status = read_status_file(master_issue, agent_id)

            # Check heartbeat
            if status.last_update + STALE_THRESHOLD < now():
                warn(f"{agent_id} appears stalled")

            # Check completion
            if status.status == "completed":
                record_success(agent_id, status)
            elif status.status == "failed":
                record_failure(agent_id, status)

            # Update progress display
            update_progress_ui(agent_id, status)

        sleep(STATUS_INTERVAL)
```

### Stale Detection

Agent considered stale if:
```
current_time - status.last_update > STALE_THRESHOLD
```

Default stale threshold: 5 minutes (300 seconds)

**Actions on Stale Detection**:
1. Log warning to orchestration log
2. Check if agent process still running
3. If process dead, mark status as "failed" with TIMEOUT error
4. If process alive, wait another stale threshold period
5. If still stale after 2x threshold, forcibly terminate

### Progress Display

**Console Output Format**:
```
⏱️  Monitoring progress (5 agents)...

[12:00:00] Agent-1: Implementation (45%) ████████████░░░░░░░░░░░░░░
[12:00:00] Agent-2: Testing (75%)       ██████████████████░░░░░░░░
[12:00:00] Agent-3: ✅ Completed → PR #1240
[12:00:00] Agent-4: Creating PR (90%)   ██████████████████████░░░░
[12:00:00] Agent-5: Analyzing (20%)     █████░░░░░░░░░░░░░░░░░░░░░

Active: 4 | Completed: 1 | Failed: 0 | Duration: 12m 34s
```

## Metrics Collection

### Orchestration Metrics

**Collected Automatically**:
```json
{
  "orchestration_id": "orch-1234-20251201-120000",
  "master_issue": 1234,
  "start_time": "2025-12-01T12:00:00Z",
  "end_time": "2025-12-01T12:18:03Z",
  "duration_seconds": 1083,
  "total_sub_tasks": 5,
  "successful_agents": 4,
  "failed_agents": 1,
  "timeout_agents": 0,
  "prs_created": [1240, 1241, 1242, 1243],
  "follow_up_issues": [1246],
  "agent_durations": [765, 922, 1083, 1011, 0],
  "avg_agent_duration": 945,
  "max_agent_duration": 1083,
  "min_agent_duration": 765,
  "success_rate_percentage": 80.0,
  "speedup_ratio": 4.15,
  "estimated_sequential_time": 4500,
  "resource_usage": {
    "peak_memory_mb": 2048,
    "peak_cpu_percent": 125,
    "total_api_calls": 47,
    "total_disk_io_mb": 312
  }
}
```

**Storage Location**: `.claude/runtime/parallel/{master_issue}/metrics.json`

### Agent Metrics

**Per Agent**:
```json
{
  "agent_id": "agent-1",
  "sub_issue": 1235,
  "start_time": "2025-12-01T12:00:00Z",
  "completion_time": "2025-12-01T12:12:45Z",
  "duration_seconds": 765,
  "status": "completed",
  "pr_number": 1240,
  "lines_added": 823,
  "lines_removed": 42,
  "files_modified": 3,
  "commits": 7,
  "test_runs": 4,
  "test_passes": 35,
  "test_failures": 2,
  "retry_count": 0,
  "model": "claude-sonnet-4-5",
  "api_calls": 12,
  "tokens_used": 45231
}
```

**Storage Location**: `.claude/runtime/parallel/{master_issue}/agent-{id}.metrics.json`

## Log Format

### Orchestration Session Log

**Location**: `.claude/runtime/logs/{session_id}/session.log`

**Format**:
```
[2025-12-01 12:00:00] [INFO] Orchestration started: master_issue=1234
[2025-12-01 12:00:01] [INFO] Parsed 5 sub-tasks from issue #1234
[2025-12-01 12:00:02] [INFO] Created sub-issue #1235: Add authentication module
[2025-12-01 12:00:03] [INFO] Created sub-issue #1236: Add authorization middleware
[2025-12-01 12:00:04] [INFO] Created sub-issue #1237: Implement JWT tokens
[2025-12-01 12:00:05] [INFO] Created sub-issue #1238: Add user management API
[2025-12-01 12:00:06] [INFO] Created sub-issue #1239: Create integration tests
[2025-12-01 12:00:07] [INFO] Deploying 5 agents (max_workers=5)
[2025-12-01 12:00:08] [INFO] Agent-1 started: sub_issue=1235, timeout=1800s
[2025-12-01 12:00:09] [INFO] Agent-2 started: sub_issue=1236, timeout=1800s
[2025-12-01 12:00:10] [INFO] Agent-3 started: sub_issue=1237, timeout=1800s
[2025-12-01 12:00:11] [INFO] Agent-4 started: sub_issue=1238, timeout=1800s
[2025-12-01 12:00:12] [INFO] Agent-5 started: sub_issue=1239, timeout=1800s
[2025-12-01 12:00:13] [INFO] Monitoring progress...
[2025-12-01 12:12:45] [INFO] Agent-1 completed: pr_number=1240, duration=765s
[2025-12-01 12:15:22] [INFO] Agent-2 completed: pr_number=1241, duration=922s
[2025-12-01 12:18:03] [INFO] Agent-3 completed: pr_number=1242, duration=1083s
[2025-12-01 12:16:51] [INFO] Agent-5 completed: pr_number=1244, duration=1011s
[2025-12-01 12:30:00] [ERROR] Agent-4 failed: error=TEST_TIMEOUT, duration=1800s
[2025-12-01 12:30:01] [INFO] Created follow-up issue #1246 for Agent-4 failure
[2025-12-01 12:30:02] [INFO] Orchestration completed: success_rate=80%, duration=1803s
```

### Agent Log

**Location**: `.claude/runtime/logs/{session_id}/agent-{id}.log`

**Format**:
```
[2025-12-01 12:00:08] [INFO] Agent-1 starting: sub_issue=1235
[2025-12-01 12:00:09] [INFO] Created status file: agent-1.status.json
[2025-12-01 12:00:10] [INFO] Checked out branch: feat/issue-1235-authentication
[2025-12-01 12:00:15] [INFO] Analyzing codebase...
[2025-12-01 12:02:30] [INFO] Creating implementation plan...
[2025-12-01 12:05:00] [INFO] Implementing feature...
[2025-12-01 12:08:00] [INFO] Running tests...
[2025-12-01 12:10:00] [INFO] Tests passed: 35/35
[2025-12-01 12:11:00] [INFO] Updating documentation...
[2025-12-01 12:12:00] [INFO] Creating PR...
[2025-12-01 12:12:45] [INFO] PR created: #1240
[2025-12-01 12:12:46] [INFO] Marking status as completed
[2025-12-01 12:12:47] [INFO] Agent-1 completed successfully
```

## API Rate Limits

### GitHub API Consumption

**Per Orchestration** (N sub-tasks):
```
Sub-issue creation:    N calls
PR creation:           N calls
Status comments:       N calls
Issue linking:         N calls
Label management:      N calls

Total per orchestration: ~5N calls
```

**Rate Limits**:
- Authenticated: 5,000 requests/hour
- Max orchestrations/hour: ~1000 / N

**Example** (5 sub-tasks):
- Calls per orchestration: ~25
- Max orchestrations/hour: ~200

### Rate Limit Handling

```python
def handle_rate_limit(response):
    """Handle GitHub API rate limit"""
    if response.status_code == 403:
        reset_time = response.headers.get('X-RateLimit-Reset')
        wait_seconds = int(reset_time) - int(time.time())

        if wait_seconds > 0:
            logger.warning(f"Rate limit exceeded. Waiting {wait_seconds}s")
            time.sleep(wait_seconds + 1)
            return retry_request()

    return response
```

## Security Considerations

### Sensitive Information

**Never Log**:
- GitHub tokens
- API keys
- Passwords
- Private repository content

**Safe to Log**:
- Issue numbers
- PR numbers
- Branch names
- Public repository names
- Execution metrics

### Agent Isolation

Agents MUST be isolated:
```
✅ Separate git worktrees
✅ Separate status files
✅ Separate log files
✅ Separate environment variables
✅ Separate test databases/ports

❌ Shared working directory
❌ Shared status file
❌ Shared git branches
❌ Shared test resources
```

### GitHub Token Permissions

Required token scopes:
```
repo          (full repository access)
  - repo:status
  - repo_deployment
  - public_repo
  - repo:invite
  - security_events
workflow      (workflow management)
write:packages (package write)
```

## Extensibility

### Custom Issue Parsers

Implement `IssueParser` interface:

```python
class CustomIssueParser(IssueParser):
    def parse(self, issue_body: str) -> List[SubTask]:
        """Parse custom issue format"""
        # Your parsing logic here
        return sub_tasks
```

Register parser:
```python
from parallel_orchestrator import register_parser

register_parser("custom", CustomIssueParser())
```

### Custom Status Monitors

Implement `StatusMonitor` interface:

```python
class CustomMonitor(StatusMonitor):
    def check_status(self, agent_id: str) -> AgentStatus:
        """Custom status checking logic"""
        # Your monitoring logic here
        return status

    def update_display(self, statuses: List[AgentStatus]):
        """Custom progress display"""
        # Your display logic here
        pass
```

### Custom Result Aggregators

Implement `ResultAggregator` interface:

```python
class CustomAggregator(ResultAggregator):
    def aggregate(self, results: List[AgentResult]) -> Summary:
        """Custom aggregation logic"""
        # Your aggregation logic here
        return summary
```

## Versioning

### Schema Version

Current: `1.0`

Status file schema versioning:
```json
{
  "schema_version": "1.0",
  ...
}
```

### Backward Compatibility

Orchestrator MUST support:
- Current schema version
- One previous schema version

Forward compatibility:
- Unknown fields ignored
- Required fields validated
- Schema version checked

### Migration Path

When schema changes:
```python
def migrate_status_file(old_status: dict) -> dict:
    """Migrate old schema to new schema"""
    version = old_status.get("schema_version", "1.0")

    if version == "1.0":
        # Already current
        return old_status
    elif version == "0.9":
        # Migrate 0.9 → 1.0
        return migrate_0_9_to_1_0(old_status)
    else:
        raise ValueError(f"Unsupported schema version: {version}")
```

---

This technical reference defines the complete contract fer parallel task orchestration. All implementations MUST adhere to these specifications fer interoperability and reliability. ⚓