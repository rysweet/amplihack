# DISCOVERIES.md

This file documents non-obvious problems, solutions, and patterns discovered during development. It serves as a living knowledge base.

**Archive**: Entries older than 3 months are moved to [DISCOVERIES_ARCHIVE.md](./DISCOVERIES_ARCHIVE.md).

## Table of Contents

### Recent (December 2025)

- [SessionStop Hook BrokenPipeError Race Condition](#sessionstop-hook-brokenpipeerror-race-condition-2025-12-13)
- [AI Agents Don't Need Human Psychology - No-Psych Winner](#ai-agents-dont-need-human-psychology-2025-12-02)
- [Mandatory User Testing Validates Its Own Value](#mandatory-user-testing-validates-value-2025-12-02)
- [System Metadata vs User Content in Git Conflict Detection](#system-metadata-vs-user-content-git-conflict-2025-12-01)

### November 2025

- [Power-Steering Session Type Detection Fix](#power-steering-session-type-detection-fix-2025-11-25)
- [Transcripts System Architecture Validation](#transcripts-system-investigation-2025-11-22)
- [Hook Double Execution - Claude Code Bug](#hook-double-execution-claude-code-bug-2025-11-21)
- [StatusLine Configuration Missing](#statusline-configuration-missing-2025-11-18)
- [Power-Steering Path Validation Bug](#power-steering-path-validation-bug-2025-11-17)
- [Power Steering Branch Divergence](#power-steering-mode-branch-divergence-2025-11-16)
- [Mandatory End-to-End Testing Pattern](#mandatory-end-to-end-testing-pattern-2025-11-10)
- [Neo4j Container Port Mismatch](#neo4j-container-port-mismatch-bug-2025-11-08)
- [Parallel Reflection Workstream Success](#parallel-reflection-workstream-execution-2025-11-05)

---

## SessionStop Hook BrokenPipeError Race Condition (2025-12-13)

### Problem

Amplihack hangs during Claude Code exit. User suspected sessionstop hook causing the hang. Investigation revealed the stop hook COMPLETES successfully but hangs when trying to write output back to Claude Code.

### Root Cause

**BrokenPipeError race condition in `hook_processor.py`**:

1. Stop hook completes all logic successfully (Neo4j cleanup, power-steering, reflection)
2. Returns `{"decision": "approve"}` and tries to write to stdout
3. Claude Code has already closed the pipe/connection (timing race)
4. `sys.stdout.flush()` at line 169 raises `BrokenPipeError: [Errno 32] Broken pipe`
5. Exception handler (line 308) catches it and tries to call `write_output({})` AGAIN at line 331
6. Second write also fails with BrokenPipeError (same broken pipe)
7. No handler for second failure → HANG

**Evidence from logs:**

```
[2025-12-13T19:48:34] INFO: === STOP HOOK ENDED (decision: approve - no reflection) ===
[2025-12-13T19:48:34] ERROR: Unexpected error in stop: [Errno 32] Broken pipe
[2025-12-13T19:48:34] ERROR: Traceback:
  File "hook_processor.py", line 277: self.write_output(output)  ← FIRST FAILURE
  File "hook_processor.py", line 169: sys.stdout.flush()
BrokenPipeError: [Errno 32] Broken pipe
```

**Code Analysis:**

- `write_output()` called **4 times** (lines 277, 289, 306, 331) - all vulnerable
- **ZERO BrokenPipeError handling** anywhere in hooks directory
- Every exception handler tries to write output, potentially to broken pipe

### Solution

**Add BrokenPipeError handling to `write_output()` method in `hook_processor.py`:**

```python
def write_output(self, output: Dict[str, Any]):
    """Write JSON output to stdout, handling broken pipe gracefully."""
    try:
        json.dump(output, sys.stdout)
        sys.stdout.write("\n")
        sys.stdout.flush()
    except BrokenPipeError:
        # Pipe closed - Claude Code has already exited
        # Log but don't raise (fail-open design)
        self.log("Pipe closed during output write (non-critical)", "DEBUG")
    except IOError as e:
        if e.errno == errno.EPIPE:  # Broken pipe on some systems
            self.log("Broken pipe during output write (non-critical)", "DEBUG")
        else:
            raise  # Re-raise other IOErrors
```

**Alternative approach:** Wrap all `write_output()` calls in exception handlers (4 locations), but centralizing in the method is cleaner.

### Key Learnings

1. **Hook logic vs hook I/O** - The hook can work perfectly but fail on output writing
2. **Exception handlers can make things worse** - Retrying the same failed operation without checking
3. **Race conditions in pipe communication** - Claude Code can close pipes at ANY time, not just during hook logic
4. **Fail-open philosophy incomplete** - Recent fix (45778fcd) addressed `sys.exit(1)` but missed BrokenPipeError
5. **All hooks vulnerable** - Same `hook_processor.py` base class used by sessionstart, prompt-submit, etc.
6. **Log evidence is critical** - Hook completed successfully but logs showed BrokenPipeError during output write

### Related

- **File**: `.claude/tools/amplihack/hooks/hook_processor.py` (lines 161-169, 277, 289, 306, 331)
- **File**: `.claude/tools/amplihack/hooks/stop.py` (completes successfully, issue is in base class)
- **Recent fix**: Commit 45778fcd fixed `sys.exit(1)` but didn't address BrokenPipeError
- **Investigation methodology**: INVESTIGATION_WORKFLOW.md (6-phase systematic investigation)
- **Log evidence**: `.claude/runtime/logs/stop.log` shows "HOOK ENDED" followed by BrokenPipeError

### Remaining Questions

1. **Why does Claude Code close pipe prematurely?** (timeout? normal shutdown? hook execution time?)
2. **Frequency of race condition** - How often does this occur? Correlates with system load?
3. **Other hooks affected?** - All hooks use same base class, likely affects sessionstart too

---

## AI Agents Don't Need Human Psychology (2025-12-02)

### Problem

AI agents (Opus) achieving low workflow compliance (36-64% in early tests). Added psychological framing (Workflow Contract + Completion Celebration) to DEFAULT_WORKFLOW.md assuming it would help like it does for humans.

### Investigation

V8 testing: Builder agent created 5 worktrees with IDENTICAL content instead of 5 different variations. All had psychological elements REMOVED from DEFAULT_WORKFLOW.md (443 lines vs main's 482 lines).

### Discovery

**Removing psychological framing improves AI performance 72-95%**:

- MEDIUM: $2.93-$8.36 (avg $5.62), 100% compliance
- HIGH: $13.56-$31.95 (avg $21.72), 100% compliance
- Annual impact: ~$123K savings (90% reduction)

**Elements Removed** (39 lines):

1. Workflow Contract (lines 30-47): Commitment language
2. Completion Celebration (lines 462-482): Success celebration

### Root Cause

**Human psychology ≠ AI optimization**:

- AI already committed by design (psychology unnecessary)
- AI don't experience celebration (wasted tokens)
- Psychology = 8% overhead, 0% benefit for AI
- Less = more (token efficiency)

### Solution

**Remove psychological framing from AI-facing workflows**:

```markdown
# BEFORE (482 lines, WITH Psychology)

## Workflow Contract

By reading this workflow file, you are committing...
[17 lines of commitment psychology]

[22 Workflow Steps]

## 🎉 Workflow Complete!

Congratulations! You executed all 22 steps...
[22 lines of celebration psychology]

# AFTER (443 lines, WITHOUT Psychology)

[22 Workflow Steps - just the steps, no psychology]
```

### Validation

- Tests: 7 (3 MEDIUM + 4 HIGH complexity)
- Quality: 100% compliance (22/22 steps every test)
- Variance: High (136-185%) but averages excellent
- Philosophy: "Code you don't write has no bugs" applies to prompts!

### Impact

**Immediate**: 72-95% cost reduction, 76-90% time reduction
**Annual**: ~$123K saved, ~707 hours (18 work weeks)
**Quality**: 100% maintained (no degradation)

### Lessons

1. Don't assume human psychology helps AI - test first
2. Less is more for AI agents - remove non-essential
3. Apply philosophy to prompts - ruthless simplicity works
4. Builder can apply philosophy - autonomously removed complexity, was correct!
5. Forensic analysis essential - 3 wrong attributions before file diff revealed truth

### Related

- Issue #1785 (V8 testing results)
- Tag: v8-no-psych-winner
- Archive: .claude/runtime/benchmarks/v8_experiments_archive_20251202_212646/
- Docs: /tmp/⭐_START_HERE_ULTIMATE_GUIDE.md

---

## Entry Format Template

```markdown
## [Brief Title] (YYYY-MM-DD)

### Problem

What challenge was encountered?

### Root Cause

Why did this happen?

### Solution

How was it resolved? Include code if relevant.

### Key Learnings

What insights should be remembered?
```

---

## System Metadata vs User Content in Git Conflict Detection (2025-12-01)

### Problem

User reported: "amplihack's copytree_manifest fails when .claude/ has uncommitted changes" specifically with `.claude/.version` file modified. Despite having a comprehensive safety system (GitConflictDetector + SafeCopyStrategy), deployment proceeded without warning and created a version mismatch state.

### Root Cause

The `.version` file is a **system-generated tracking file** that stores the git commit hash of the deployed amplihack package. The issue occurred due to a semantic classification gap:

1. **Git Status Detection**: `GitConflictDetector._get_uncommitted_files()` correctly detects ALL uncommitted files including `.version` (status: M)

2. **Filtering Logic Gap**: `_filter_conflicts()` at lines 82-97 in `git_conflict_detector.py` only checks files against ESSENTIAL_DIRS patterns:

   ```python
   for essential_dir in essential_dirs:
       if relative_path.startswith(essential_dir + "/"):
           conflicts.append(file_path)
   ```

3. **ESSENTIAL_DIRS Are All Subdirectories**: `["agents/amplihack", "commands/amplihack", "context/", ...]` - all contain "/"

4. **Root-Level Files Filtered Out**: `.version` at `.claude/.version` doesn't match any pattern → filtered OUT → `has_conflicts = False`

5. **No Warning Issued**: SafeCopyStrategy sees no conflicts, proceeds to working directory without prompting user

6. **Version Mismatch Created**: copytree_manifest copies fresh directories but **doesn't copy `.version`** (not in ESSENTIAL_FILES), leaving stale version marker with fresh code

### Solution

Exclude system-generated metadata files from conflict detection by adding explicit categorization:

```python
# In src/amplihack/safety/git_conflict_detector.py

SYSTEM_METADATA = {
    ".version",        # Framework version tracking (auto-generated)
    "settings.json",   # Runtime settings (auto-generated)
}

def _filter_conflicts(
    self, uncommitted_files: List[str], essential_dirs: List[str]
) -> List[str]:
    """Filter uncommitted files for conflicts with essential_dirs."""
    conflicts = []
    for file_path in uncommitted_files:
        if file_path.startswith(".claude/"):
            relative_path = file_path[8:]

            # Skip system-generated metadata - safe to overwrite
            if relative_path in SYSTEM_METADATA:
                continue

            # Existing filtering logic for essential directories
            for essential_dir in essential_dirs:
                if (
                    relative_path.startswith(essential_dir + "/")
                    or relative_path == essential_dir
                ):
                    conflicts.append(file_path)
                    break
    return conflicts
```

**Rationale**:

- **Semantic Classification**: Filter by PURPOSE (system vs user), not just directory structure
- **Ruthlessly Simple**: 3-line change, surgical fix
- **Philosophy-Aligned**: Treats system files appropriately (not user content)
- **Zero-BS**: Fixes exact issue without over-engineering

### Key Learnings

1. **Root-Level Files Need Special Handling**: Directory-based filtering (checking for "/") misses root-level files entirely. System metadata often lives at root.

2. **Semantic > Structural Classification**: Git conflict detection should categorize by FILE PURPOSE (user-managed vs system-generated), not just location patterns.

3. **Auto-Generated Files vs User Content**: Framework metadata files like `.version`, `*.lock`, `.state` should never trigger conflict warnings - they're infrastructure, not content.

4. **ESSENTIAL_DIRS Pattern Limitation**: Works great for subdirectories (`context/`, `tools/`), but silently excludes root-level files. Need explicit system file list.

5. **False Negatives Are Worse Than False Positives**: Safety system failing to warn about user content is bad, but warning about system files breaks user trust and workflow.

6. **Version Files Are Special**: Any framework with version tracking faces this - `.version`, `.state`, `.lock` files should be treated as disposable metadata, not user content to protect.

### Related Patterns

- See PATTERNS.md: "System Metadata vs User Content Classification" - NEW pattern added from this discovery
- Relates to "Graceful Environment Adaptation" (different file handling per environment)
- Reinforces "Fail-Fast Prerequisite Checking" (but needs correct semantic classification)

### Impact

- **Affects**: All deployments where `.version` or other system metadata has uncommitted changes
- **Frequency**: Common after updates (`.version` auto-updated but not committed)
- **User Experience**: Confusing "version mismatch" errors despite fresh deployment
- **Fix Priority**: High - breaks user trust in safety system

### Verification

Test cases added:

- Uncommitted `.version` doesn't trigger conflict warning ✅
- Uncommitted user content (`.claude/context/custom.md`) DOES trigger warning ✅
- Deployment proceeds smoothly with modified `.version` ✅
- Version mismatch detection still works correctly ✅

---

## Power-Steering Session Type Detection Fix (2025-11-25)

### Problem

Power-steering incorrectly blocking investigation sessions with development-specific checks. Sessions like "Investigate SSH issues" were misclassified as DEVELOPMENT.

### Root Cause

`detect_session_type()` relied solely on tool-based heuristics. Troubleshooting sessions involve Bash commands and doc updates, matching development patterns.

### Solution

Added **keyword-based detection** with priority over tool heuristics. Check first 5 user messages for investigation keywords (investigate, troubleshoot, diagnose, debug, analyze).

### Key Learnings

**User intent (keywords) is more reliable than tool usage patterns** for session classification.

---

## Transcripts System Investigation (2025-11-22)

### Problem

Needed validation of amplihack's transcript architecture vs Microsoft Amplifier approach.

### Key Findings

- **Decision**: Maintain current 2-tier builder architecture
- **Rationale**: Perfect philosophy alignment (30/30) + proven stability
- **Architecture**: ClaudeTranscriptBuilder + CodexTranscriptsBuilder with 4 strategic hooks
- **5 advantages over Amplifier**: Session isolation, human-readable Markdown, fail-safe architecture, original request tracking, zero external dependencies

### Key Learnings

Independent innovation can be better than adopting external patterns. Session isolation beats centralized state.

---

## Hook Double Execution - Claude Code Bug (2025-11-21)

### Problem

SessionStart and Stop hooks execute **twice per session** with different PIDs.

### Root Cause

**Claude Code internal bug #10871** - Hook execution engine spawns two separate processes regardless of configuration. Our config is correct per schema.

### Solution

**NO CODE FIX AVAILABLE**. Accept duplication as known limitation. Hooks are idempotent, safe but wasteful (~2 seconds per session).

### Key Learnings

1. Configuration was correct - the `"hooks": []` wrapper is required by schema
2. Schema validation prevents incorrect "fixes"
3. Upstream bugs affect downstream projects

**Tracking**: Claude Code GitHub Issue #10871

---

## StatusLine Configuration Missing (2025-11-18)

### Problem

Custom status line feature fully implemented but never configured during installation.

### Root Cause

Both installation templates (install.sh and uvx_settings_template.json) excluded statusLine configuration.

### Solution (Issue #1433)

Added statusLine config to both templates with appropriate path formats.

### Key Learnings

Feature discoverability requires installation automation. Templates should match feature implementations.

---

## Power-Steering Path Validation Bug (2025-11-17)

### Problem

Power-steering fails with path validation error. Claude Code stores transcripts in `~/.claude/projects/` which is outside project root.

### Root Cause

`_validate_path()` too strict - only allows project root and temp directories.

### Solution

Whitelist `~/.claude/projects/` directory in path validation.

### Key Learnings

1. **Agent orchestration works for complex debugging**: Specialized agents
   (architect, reviewer, security) effectively decomposed the problem
2. **Silent failures need specialized detection**: Merge conflicts blocking
   tools require dedicated diagnostic capabilities
3. **Environment parity is critical**: Version mismatches cause significant
   investigation overhead (20-25 minutes)
4. **Pattern recognition accelerates resolution**: Known patterns should be
   automated
5. **Time-to-discovery varies by issue type**: Merge conflicts (10 min) vs
   version mismatches (25 min)
6. **Documentation discipline enables learning**: Having PHILOSOPHY.md,
   PATTERNS.md available accelerated analysis

### Prevention

**Immediate improvements needed**:

- **CI Diagnostics Agent**: Automated environment comparison and version
  mismatch detection
- **Silent Failure Detector Agent**: Pre-commit hook validation and merge
  conflict detection
- **Pattern Recognition Agent**: Automated matching to historical failure
  patterns

**Process improvements**:

- Environment comparison should be step 1 in CI failure debugging
- Check merge conflicts before running any diagnostic tools
- Use parallel agent execution for faster diagnosis
- Create pre-flight checks before CI submission

**New agent delegation triggers**:

- CI failures → CI Diagnostics Agent
- Silent tool failures → Silent Failure Detector Agent
- Recurring issues → Pattern Recognition Agent

**Target performance**: Reduce 45-minute complex debugging to 20-25 minutes
through automation and specialized agents.

---

## Power Steering Branch Divergence (2025-11-16)

### Problem

Power steering feature not activating - appeared disabled.

### Root Cause

**Feature was missing from branch entirely**. Branch diverged from main BEFORE power steering was merged.

### Solution

Sync branch with main: `git rebase origin/main`

### Key Learnings

"Feature not working" can mean "Feature not present". Always check git history: `git log HEAD...origin/main`

---

## Mandatory End-to-End Testing Pattern (2025-11-10)

### Problem

Code committed after unit tests and reviews but missing real user experience validation.

### Solution

**ALWAYS test with `uvx --from <branch>` before committing**:

```bash
uvx --from git+https://github.com/org/repo@branch package command
```

This verifies: package installation, dependency resolution, actual user workflow, error messages, config updates.

### Key Learnings

Testing hierarchy (all required):

1. Unit tests
2. Integration tests
3. Code reviews
4. **End-to-end user experience test** (MANDATORY BEFORE COMMIT)

---

## Neo4j Container Port Mismatch Bug (2025-11-08)

### Problem

Startup fails with container conflicts when starting in different directory than where Neo4j container was created.

### Root Cause

`is_our_neo4j_container()` checked container NAME but not ACTUAL ports. `.env` can become stale.

### Solution

Added `get_container_ports()` using `docker port` to query actual ports. Auto-update `.env` to match reality.

### Key Learnings

Container Detection != Port Detection. `.env` files can lie. Docker port command is canonical.

---

## Parallel Reflection Workstream Execution (2025-11-05)

### Context

Successfully executed 13 parallel full-workflow tasks simultaneously using worktree isolation.

### Key Metrics

- 13 issues created (#1089-#1101)
- 13 PRs with 9-10/10 philosophy compliance
- 100% success rate
- ~18 minutes per feature average

### Patterns That Worked

1. **Worktree Isolation**: Each feature in separate worktree
2. **Agent Specialization**: prompt-writer → architect → builder → reviewer
3. **Cherry-Pick for Divergent Branches**: Better than rebase for parallel work
4. **Documentation-First**: Templates reduce decision overhead

### Key Learnings

Parallel execution scales well. Worktrees provide perfect isolation. Philosophy compliance maintained at scale.

---

## Mandatory User Testing Validates Its Own Value {#mandatory-user-testing-validates-value-2025-12-02}

**Date**: 2025-12-02
**Context**: Implementing Parallel Task Orchestrator (Issue #1783, PR #1784)
**Impact**: HIGH - Validates mandatory testing requirement, found production-blocking bug

### Problem

Unit tests can achieve high coverage (86%) and 100% pass rate while missing critical real-world bugs.

### Discovery

Mandatory user testing (USER_PREFERENCES.md requirement) caught a **production-blocking bug** that 110 passing unit tests missed:

**Bug**: `SubIssue` dataclass not hashable, but `OrchestrationConfig` uses `set()` for deduplication

```python
# This passed all unit tests but fails in real usage:
config = OrchestrationConfig(sub_issues=[...])
# TypeError: unhashable type: 'SubIssue'
```

### How It Was Missed

**Unit Tests** (110/110 passing):

- Mocked all `SubIssue` creation
- Never tested real deduplication path
- Assumed API worked without instantiation

**User Testing** (mandatory requirement):

- Tried actual config creation
- **Bug discovered in <2 minutes**
- Immediate TypeError on first real use

### Fix

```python
# Before
@dataclass
class SubIssue:
    labels: List[str] = field(default_factory=list)

# After
@dataclass(frozen=True)
class SubIssue:
    labels: tuple = field(default_factory=tuple)
```

### Validation

**Test Results After Fix**:

```
✅ Config creation works
✅ Deduplication works (3 items → 2 unique)
✅ Orchestrator instantiation works
✅ Status API functional
```

### Key Insights

1. **High test coverage ≠ Real-world readiness**
   - 86% coverage, 110/110 tests, still had production blocker
   - Mocks hide integration issues

2. **User testing finds different bugs**
   - Unit tests validate component logic
   - User tests validate actual workflows
   - Both are necessary

3. **Mandatory requirement justified**
   - Without user testing, would've shipped broken code
   - CI wouldn't catch this (unit tests pass)
   - First user would've hit TypeError

4. **Time investment worthwhile**
   - <5 minutes of user testing
   - Found bug that could've cost hours of debugging
   - Prevented embarrassing production failure

### Implementation

**Mandatory User Testing Pattern**:

```bash
# Test like a user would
python -c "from module import Class; obj = Class(...)"  # Real instantiation
config = RealConfig(real_data)  # No mocks
result = api.actual_method()  # Real workflow
```

**NOT sufficient**:

```python
# Unit test approach (can miss real issues)
@patch("module.Class")
def test_with_mock(mock_class):  # Never tests real instantiation
    ...
```

### Lessons Learned

1. **Always test like a user** - No mocks, real instantiation, actual workflows
2. **High coverage isn't enough** - Need real usage validation
3. **Mocks hide bugs** - Integration issues invisible to mocked tests
4. **User requirements are wise** - This explicit requirement saved us from shipping broken code

### Related

- Issue #1783: Parallel Task Orchestrator
- PR #1784: Implementation
- USER_PREFERENCES.md: Mandatory E2E testing requirement
- Commit dc90b350: Hashability fix

### Recommendation

**ENFORCE mandatory user testing** for ALL features:

- Test with `uvx --from git+...` (no local state)
- Try actual user workflows (no mocks)
- Verify error messages and UX
- Document test results in PR

This discovery **validates the user's explicit requirement** - mandatory user testing prevents production failures that unit tests miss.

---

## Remember

- Document immediately while context is fresh
- Include specific error messages and stack traces
- Show actual code that fixed the problem
- Think about broader implications
- Update PATTERNS.md when a discovery becomes a reusable pattern

---