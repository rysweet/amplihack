# DISCOVERIES.md

This file documents non-obvious problems, solutions, and patterns discovered during amplihack development. Review and update this regularly, removing outdated entries or those replaced by better practices, code, or tools. Update entries where best practices have evolved.

## Cleanup Agent Gap: Root Directory Organization (2026-01-12)

### Issue

Root directory accumulated documentation files that belonged in `docs/` subdirectories. Files like `EVALUATION_SUMMARY.md` and `gh_pages_link_validation.txt` cluttered the root when they should be organized by category.

### Root Cause

1. **Cleanup agent scope limitation**: The cleanup agent focuses on code quality (dead code, complexity) but doesn't enforce documentation organization
2. **No proactive file placement checking**: No automated check for misplaced documentation in root
3. **Unclear guidelines**: File organization guidelines existed but weren't centralized or easily discoverable
4. **No prevention mechanism**: Nothing stops documentation from being created in root

### Solution

**Three-part documentation system:**

1. **File Organization Guidelines** (`docs/contributing/file-organization.md`):
   - Clear decision tree fer file placement
   - Examples of proper organization
   - Integration with cleanup agent (future)

2. **Archive Directory Structure** (`archive/legacy/README.md`):
   - Standard location fer superseded files
   - Clear policy on what goes there
   - Example: `setup.py` archived when superseded by `pyproject.toml`

3. **Moved Misplaced Files**:
   - `EVALUATION_SUMMARY.md` → `docs/memory/evaluation-summary.md`
   - `gh_pages_link_validation.txt` → `docs/testing/gh-pages-link-validation.txt`
   - `setup.py` → `archive/legacy/setup.py`

### Key Learnings

1. **Cleanup spans more than code**: File organization and documentation structure matter fer discoverability
2. **Guidelines need centralization**: Scattered advice in multiple docs isn't enforced
3. **Prevention better than cleanup**: Catch misplaced files before they be committed
4. **Archive preserves history**: Don't delete superseded files if they might have reference value

### Prevention

- Create `docs/contributing/file-organization.md` with clear guidelines (✅ done)
- Update cleanup agent to suggest documentation moves (tracked as enhancement)
- Add pre-commit hook to flag documentation files in root (future)
- Reference file organization guidelines in CONTRIBUTING.md
- Use `make check-broken-links` after movin' files to verify references

### Enhancement Opportunities

1. **Cleanup Agent Extension**: Add documentation organization to cleanup agent responsibilities
2. **Pre-commit Check**: Warn when documentation be created outside `docs/`
3. **Link Validation**: Automatically update and validate internal links when movin' files
4. **Documentation Index**: Keep `docs/index.md` automatically updated with new files

## Workflow Enforcement via CLAUDE.md (2025-11-26)

### Issue

Claude consistently ignored workflow instructions even when explicitly invoked with `/ultrathink`. Despite the command being explicitly invoked, Claude would skip workflow steps or not follow the DEFAULT_WORKFLOW.md at all.

### Root Cause

**4 levels of indirection** caused context loss:

```
/ultrathink command
  -> ultrathink-orchestrator skill
    -> default-workflow skill
      -> DEFAULT_WORKFLOW.md
```

Each layer of indirection loses context. By the time Claude reaches the actual workflow file, the instruction to follow it strictly has been diluted or lost.

### Solution

**PR #1686** eliminated the indirection by adding workflow classification directly to CLAUDE.md:

1. Added "MANDATORY: Workflow Selection" section to CLAUDE.md (lines 19-64)
2. Created Q&A_WORKFLOW.md for simple questions (enables "always use a workflow")
3. Deprecated (but kept working) the old command/skill chain
4. Removed all /ultrathink references from CLAUDE.md

### Classification Table

| Task Type     | Workflow               | When to Use                           |
| ------------- | ---------------------- | ------------------------------------- |
| Q&A           | Q&A_WORKFLOW           | Simple questions, single-turn answers |
| Investigation | INVESTIGATION_WORKFLOW | Understanding code, research          |
| Development   | DEFAULT_WORKFLOW       | Code changes, features, bugs          |

### Key Learnings

1. **Indirection kills enforcement**: Each layer between instruction and action reduces compliance
2. **Put critical instructions in CLAUDE.md**: It's always loaded, always visible
3. **Create exhaustive categories**: Q&A_WORKFLOW enables "always use a workflow" without exception
4. **Deprecate gracefully**: Keep old commands working but direct to new pattern

### Prevention

- Put mandatory behavior directly in CLAUDE.md, not in commands/skills
- Limit indirection to 1 level maximum for critical instructions
- Create a workflow for every task category to enable "no exceptions" rules
- Test workflow enforcement by starting fresh sessions

## Auto Mode SDK Integration Challenges (2025-10-25)

### Issue

Auto mode integration with Claude Code SDK had multiple failure modes including session fork crashes, missing UI flags, and test enforcement not respecting auto mode context.

### Root Cause

1. **Session management complexity**: Multiple approaches (SDK fork, environment variable export, process spawning) created confusion
2. **Flag inconsistency**: --ui flag was removed in some code paths but not others
3. **Test enforcement blindness**: Test enforcement system didn't check for auto mode before failing on missing tests
4. **PID exposure**: Security violation from exposing process IDs in auto mode output

### Solution

**Issue #1013 resolution** implemented hybrid session management:

```python
# Hybrid approach: SDK fork for subprocess + environment variable export
session_data = self._sdk.export_for_subprocess()
os.environ["CLAUDE_CODE_SESSION_ID"] = session_data["session_id"]
# Fork SDK session for subprocess
fork_output = fork_manager.create_fork(session_id)
```

**Test enforcement** updated to respect auto mode:

```python
# Check if running in auto mode before enforcing tests
if not is_auto_mode():
    enforce_test_requirements()
```

### Key Learnings

1. **Hybrid session management works best**: SDK fork for subprocess control + environment export for persistence
2. **Auto mode needs special handling**: Many validation gates should be bypassed or adapted for auto mode
3. **Security first**: Never expose process IDs or system internals in user-facing output
4. **Test with the actual SDK**: Mock testing misses critical integration issues

### Prevention

- Always check `is_auto_mode()` before enforcing validation gates
- Use hybrid session management for subprocess creation
- Never expose PIDs, absolute paths, or system internals
- Test auto mode flows with real Claude SDK, not mocks

## Azure OpenAI Proxy Port Binding Failures (2025-10-24)

### Issue

Proxy failed to start with port already in use errors, causing sessions to hang indefinitely waiting for proxy health check.

### Root Cause

1. **Port persistence**: Proxy process crashed but port remained bound to dead process
2. **No port cleanup**: No mechanism to detect and clean up stale port bindings
3. **No timeout**: Health check waited forever for proxy that would never start
4. **Silent failure**: No clear error message about what went wrong

### Solution

**Dynamic port selection** with retry:

```python
# Try binding to requested port, fall back to dynamic port if busy
for attempt in range(max_retries):
    try:
        # Try binding to check availability
        test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_socket.bind(("127.0.0.1", port))
        test_socket.close()
        return port
    except OSError:
        # Port busy, try next port
        port += 1
```

**Health check timeout**:

```python
# Don't wait forever for proxy
health_check_timeout = 30  # seconds
if not wait_for_proxy_health(timeout=health_check_timeout):
    raise ProxyStartupError("Proxy failed to start within timeout")
```

### Key Learnings

1. **Always implement timeouts**: Never wait indefinitely for external processes
2. **Dynamic port selection prevents conflicts**: Especially important for dev environments
3. **Fail fast and loud**: Clear error messages save hours of debugging
4. **Clean up process state**: Dead processes can hold resources

### Prevention

- Implement dynamic port selection for all network services
- Always set timeouts on health checks and startup waits
- Add cleanup logic for stale processes and port bindings
- Log clear error messages with actionable guidance

## Hook Execution Permissions and Path Handling (2025-10-20)

### Issue

User-provided hooks failed silently or with cryptic errors. Common failure modes:

- Hooks without execute permissions
- Relative paths in hook configuration
- Hooks timing out without clear feedback

### Root Cause

1. **No permission checking**: System didn't verify hooks were executable before attempting to run them
2. **Relative path confusion**: Hooks specified with relative paths failed when run from different directories
3. **Silent timeouts**: Hooks timing out produced no clear error message
4. **Inconsistent execution context**: Hooks ran from various working directories

### Solution

**Hook validation at installation time**:

```python
def validate_hook(hook_path: Path) -> None:
    if not hook_path.exists():
        raise HookValidationError(f"Hook does not exist: {hook_path}")
    if not os.access(hook_path, os.X_OK):
        # Try to add execute permission
        hook_path.chmod(hook_path.stat().st_mode | 0o111)
        logger.info(f"Added execute permission to hook: {hook_path}")
    # Convert to absolute path
    hook_path = hook_path.resolve()
```

**Clear timeout handling**:

```python
try:
    result = subprocess.run(
        hook_cmd,
        timeout=hook_timeout,
        capture_output=True
    )
except subprocess.TimeoutExpired:
    logger.error(
        f"Hook '{hook_name}' timed out after {hook_timeout}s. "
        f"Consider increasing timeout or optimizing hook."
    )
```

### Key Learnings

1. **Validate early**: Check prerequisites at configuration time, not execution time
2. **Absolute paths everywhere**: Resolve relative paths immediately to avoid confusion
3. **Auto-fix when possible**: Add execute permissions automatically rather than just failing
4. **Timeout feedback is critical**: Users need to know WHY their hook didn't complete

### Prevention

- Validate all hooks at installation/configuration time
- Convert relative paths to absolute immediately
- Set reasonable default timeouts (10s for most hooks)
- Provide clear, actionable error messages with timeout issues

## Worktree Management and Branch Isolation (2025-10-18)

### Issue

Multiple developers working on the same repository encountered:

- Lost work when switching branches
- Confusion about which worktree was active
- Stale worktrees cluttering filesystem
- Difficulty tracking multiple feature branches

### Root Cause

1. **Manual worktree management**: No standardized process for creating/managing worktrees
2. **No visual indication**: Hard to tell which worktree you're in
3. **No cleanup process**: Worktrees persisted after branches merged
4. **Path confusion**: Similar directory names across worktrees

### Solution

**Worktree manager agent** with standardized workflow:

```bash
# Create worktree with standard naming
git worktree add ./worktrees/feat/issue-123-feature-name -b feat/issue-123-feature-name

# Clear visual indication in prompt
export PS1="[worktree: feat/issue-123] $ "

# Cleanup merged worktrees
git worktree prune
```

**Standard worktree structure**:

```
./worktrees/
├── feat/
│   ├── issue-123-feature-name/
│   └── issue-456-other-feature/
├── fix/
│   └── issue-789-bug-fix/
└── docs/
    └── issue-101-documentation/
```

### Key Learnings

1. **Worktrees enable parallel development**: Work on multiple features without branch switching
2. **Naming consistency matters**: Standard format makes navigation easier
3. **Regular cleanup prevents clutter**: Prune merged worktrees regularly
4. **Visual indicators prevent confusion**: Show current worktree in prompt or status line

### Prevention

- Use worktree-manager agent for all worktree operations
- Follow standard naming convention: `./worktrees/{type}/issue-{num}-{desc}/`
- Prune worktrees after merging branches
- Configure shell prompt to show current worktree

## Context Preservation Across Sessions (2025-10-15)

### Issue

Long-running tasks or multi-session projects lost important context between Claude Code sessions, requiring users to re-explain decisions, constraints, and project history.

### Root Cause

1. **No session state persistence**: Each session started fresh with only basic context
2. **Decision rationale lost**: Why certain approaches were chosen wasn't captured
3. **No continuation mechanism**: Difficult to resume incomplete work from previous sessions
4. **Context spread across many files**: Important information scattered in various docs

### Solution

**Session continuation system**:

```markdown
# ai_working/session_state.md

## Current Task

[Description of what we're working on]

## Recent Decisions

- [Date] Chose approach X over Y because [rationale]
- [Date] Decided to defer Z until [condition]

## Next Steps

1. [What needs to happen next]
2. [Dependencies or blockers]

## Important Context

[Key information that must be preserved]
```

**Agent prompts reference session state**:

```
Before starting any task, read @ai_working/session_state.md to understand:
- What we're currently working on
- Recent decisions and their rationale
- What the next steps are
```

### Key Learnings

1. **Explicit state management beats implicit**: Write down decisions and context
2. **Rationale is as important as the decision**: Capture WHY, not just WHAT
3. **Next steps guide continuation**: Clear next actions enable easy resumption
4. **Centralized state prevents duplication**: Single source of truth for session context

### Prevention

- Update session_state.md after major decisions or milestone completion
- Include rationale for all non-obvious choices
- Review session_state.md at the start of each session
- Reference it in agent prompts and CLAUDE.md

## Philosophy Violations in Generated Code (2025-10-12)

### Issue

Agents frequently generated code that violated amplihack's core philosophy principles:

- Placeholder functions with TODO comments
- Overly complex abstractions for simple operations
- Generic "future-proof" code for hypothetical requirements
- Swallowed exceptions hiding real errors

### Root Cause

1. **Philosophy not enforced in agent prompts**: Agents didn't consistently reference PHILOSOPHY.md
2. **No validation gate**: Generated code not checked for philosophy compliance
3. **Patterns vs principles confusion**: Agents applied "best practices" that contradicted philosophy
4. **Cleanup agent too gentle**: Didn't aggressively remove unnecessary complexity

### Solution

**Mandatory philosophy check in workflow**:

```markdown
### Step 6: Refactor and Simplify

- [ ] **CRITICAL: Provide cleanup agent with original user requirements**
- [ ] **Always use** cleanup agent for ruthless simplification WITHIN user constraints
- [ ] Remove unnecessary abstractions (that weren't explicitly requested)
- [ ] Eliminate dead code (unless user explicitly wanted it)
- [ ] Verify no placeholders remain - no stubs, no TODOs, no swallowed exceptions
```

**Enhanced cleanup agent prompt**:

```
PHILOSOPHY ENFORCEMENT CHECKLIST:
❌ No TODO comments or placeholder functions
❌ No swallowed exceptions (bare except: pass)
❌ No unimplemented functions
❌ No overly generic abstractions
✅ Simple, direct implementations
✅ Explicit error handling
✅ Single responsibility per module
```

### Key Learnings

1. **Philosophy must be in agent context**: Reference PHILOSOPHY.md in every agent prompt
2. **Validation gates catch violations**: Check generated code before accepting it
3. **Be specific about anti-patterns**: Tell agents what NOT to do
4. **Cleanup is aggressive simplification**: Remove complexity, don't just organize it

### Prevention

- Include PHILOSOPHY.md reference in all agent prompts
- Run cleanup agent with explicit philosophy checklist
- Review generated code for common violations (TODOs, swallowed exceptions)
- Fail PR if philosophy violations detected

## Rate Limiting and Token Budget Management (2025-10-08)

### Issue

High-frequency agent operations hit Claude API rate limits, causing:

- Failed tool calls with cryptic 429 errors
- Degraded user experience with unexplained delays
- Wasted tokens on retry attempts
- Session crashes from unhandled rate limit errors

### Root Cause

1. **No rate limit awareness**: System didn't track API usage or respect limits
2. **Aggressive retry logic**: Immediate retries worsened rate limit violations
3. **No user feedback**: Rate limit errors looked like random failures
4. **Unbounded parallel requests**: Multiple agents could overwhelm API simultaneously

### Solution

**Rate limit protection system**:

```python
class RateLimitProtection:
    def __init__(self, requests_per_minute=50):
        self.rpm_limit = requests_per_minute
        self.request_times = []

    async def acquire(self):
        # Wait if we're at rate limit
        while len(self.request_times) >= self.rpm_limit:
            wait_time = 60 - (time.time() - self.request_times[0])
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            self.request_times.pop(0)

        self.request_times.append(time.time())
```

**Exponential backoff with jitter**:

```python
def exponential_backoff(attempt: int) -> float:
    base_delay = 2 ** attempt
    jitter = random.uniform(0, 0.1 * base_delay)
    return min(base_delay + jitter, 60)  # Cap at 60s
```

### Key Learnings

1. **Rate limits are real**: Respect API limits or face cascading failures
2. **Exponential backoff prevents thundering herd**: Don't retry immediately
3. **User feedback prevents confusion**: Explain why there's a delay
4. **Track usage proactively**: Don't wait for 429 to learn you're over limit

### Prevention

- Implement rate limiting for all API-heavy operations
- Use exponential backoff with jitter for retries
- Display clear messages when rate limited
- Monitor token usage to stay within budget

---

## How to Use This File

### When to Add an Entry

Add a discovery when you encounter:

- A non-obvious problem that took significant time to diagnose
- A solution that contradicts common assumptions
- A pattern that prevents an entire class of issues
- Learning that will benefit future development

### Entry Template

```markdown
## Problem Title (YYYY-MM-DD)

### Issue

[Clear description of the problem and its symptoms]

### Root Cause

[What actually caused the issue - dig deep]

### Solution

[What you implemented to fix it - include code examples]

### Key Learnings

[Principles and insights from this experience]

### Prevention

[How to avoid this problem in the future]
```

### Maintenance

- **Monthly review**: Check if discoveries are still relevant
- **Remove outdated entries**: If better solutions exist or the problem is obsolete
- **Update evolved practices**: Refine solutions as understanding improves
- **Link from docs**: Reference relevant discoveries in CLAUDE.md and AGENTS.md

### Integration

This file should be referenced by:

- **CLAUDE.md**: "Before solving complex problems, check @docs/DISCOVERIES.md"
- **AGENTS.md**: "Review @docs/DISCOVERIES.md to avoid known pitfalls"
- **New developers**: "Read DISCOVERIES.md to understand institutional knowledge"

## Checklist CLAUDE.md Breaks Sonnet 4.5 Autonomy (2025-11-30)

### Issue

Follow-up testing to #1703 Opus experiments revealed checklist approach DEGRADES Sonnet 4.5 by causing premature workflow termination.

### Testing

Ran Sonnet 4.5 on REST API Client (HIGH complexity) with:

1. Original CLAUDE.md (baseline)
2. Checklist CLAUDE.md (Approach 2 from #1703)

### Results

**Original Sonnet**: 104m, $24, 109 turns, **22/22 steps** ✅
**Checklist Sonnet**: 36m, $8, 35 turns, **8/22 steps** ❌

### Root Cause

Checklist validation gates (STOP checkpoints, pre-flight validation) trigger Sonnet to pause and ask permission: "Would ye like me to continue?" This violates autonomy guidelines and causes premature stopping.

### Key Learning

**Model-specific behavior**: Interventions designed to force Opus completion have OPPOSITE effect on Sonnet - they cause stopping instead of continuation.

### Solution

**DO NOT implement checklist approach in production** - it breaks the model that works naturally. Use Sonnet 4.5 with original CLAUDE.md for all use cases.

###Prevention

- **Test interventions across ALL target models** - what helps one can break another
- **Validation gates harmful for autonomous models** - Sonnet needs zero checkpoints
- **No universal CLAUDE.md solution** - different models need different approaches
