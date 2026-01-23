# CLI Integration Investigation - Summary Report

**Investigation**: Blarify Prompt Integration for Code Indexing
**Agent**: CLI Integration Specialist (Agent 3)
**Date**: 2026-01-22
**Status**: ✅ COMPLETE

---

## Mission Statement

Investigate the CLI startup flow to determine where to add the blarify prompt with:
- 30-second timeout
- Default "yes" behavior
- First-session per project detection
- Non-blocking execution

---

## Key Deliverables

### 1. Complete Investigation Report
**File**: `.claude/ai_working/cli_integration_investigation.md`

**Contents**:
- Full CLI initialization trace (pyproject.toml → memory backend)
- Existing consent prompt pattern analysis (memory_config.py)
- 3 integration options with detailed trade-offs
- Prompt implementation specification
- Caching strategy (per-project consent files)
- Testing strategy and risk assessment

**Key Finding**: Memory backend (Kuzu) is instantiated in SessionStart hook (AFTER Claude starts), not during CLI launch. This means blarify prompt must happen BEFORE SessionStart.

### 2. Sequence Diagrams
**File**: `.claude/ai_working/cli_initialization_sequence.md`

**Contents**:
- Complete initialization sequence (from user command to memory ready)
- Timing analysis (showing where prompt fits)
- Integration point comparison diagrams
- Blarify-to-memory data flow (future integration)
- Decision trees for architectural choices

**Key Visualization**: Shows exactly when blarify prompt should appear in the 0-62 second startup window.

### 3. Options Comparison
**File**: `.claude/ai_working/blarify_prompt_integration_options.md`

**Contents**:
- Detailed analysis of all 3 integration options
- Pros/cons with risk assessment for each
- Feature matrix and decision matrix
- Complete implementation code for Option B
- Migration paths if needed

**Key Recommendation**: Option B (Launcher Prepare) scores 9.5/10, far ahead of alternatives.

---

## Executive Summary

### The Recommendation

**Add blarify prompt to `ClaudeLauncher.prepare_launch()` as step 4, immediately after Neo4j startup.**

### Why This Works

```
Flow: pyproject.toml → cli.py → launcher.prepare_launch()
                                      ↓
                             [Prerequisites] (0.6s)
                                      ↓
                             [Neo4j Startup] (0.7s - 30s)
                                      ↓
                             [🔵 BLARIFY PROMPT] (30s - 60s)  ← INSERT HERE
                                      ↓
                             [Remaining Prep] (60s)
                                      ↓
                             [Claude Starts] (61s)
                                      ↓
                             [SessionStart Hook] (62s)
                                      ↓
                             [Memory Backend Init] (62s)
```

**Timing is perfect**:
- AFTER prerequisites checked (know environment is ready)
- BEFORE Claude starts (user can still make decisions)
- Matches Neo4j pattern (consistent UX)
- No race conditions with memory backend (it initializes later)

### What to Build

Three new methods in `ClaudeLauncher` class:

```python
def _prompt_for_blarify_indexing(self) -> bool:
    """Prompt user for blarify indexing (first session per project).

    Features:
    - Checks ~/.amplihack/.blarify_consent_<project_hash> cache
    - 30-second timeout with default "yes"
    - Runs `blarify analyze` on consent
    - Non-blocking (always returns True)
    """

def _is_blarify_available(self) -> bool:
    """Check if blarify command exists in PATH."""

def _run_blarify_indexing(self) -> bool:
    """Run blarify analyze with 120s timeout."""
```

**Insertion point**: `src/amplihack/launcher/core.py:100` (after Neo4j startup)

**Lines of code**: ~150 lines total

**Estimated effort**: 2-3 hours

---

## Investigation Findings

### 1. CLI Flow Traced

**Entry Point Chain**:
```
pyproject.toml [project.scripts]
    ↓
amplihack:main()  (src/amplihack/__init__.py:108)
    ↓
cli.py:main()  (src/amplihack/cli.py:68)
    ↓
launch_command(args)  (src/amplihack/cli.py:68)
    ↓
SessionTracker.start_session()  (src/amplihack/cli.py:108)
    ↓
_launch_command_impl(args, session_id)  (src/amplihack/cli.py:135)
    ↓
ClaudeLauncher(...)  (src/amplihack/cli.py:236)
    ↓
launcher.prepare_launch()  (src/amplihack/launcher/core.py:84)
    ↓
launcher.launch_interactive()  (src/amplihack/cli.py:249)
    ↓
subprocess.run([claude, args])  (src/amplihack/launcher/core.py)
    ↓
SessionStart hook triggered  (.claude/tools/amplihack/hooks/session_start.py:43)
    ↓
KuzuBackend instantiated  (SessionStart hook, line ~150+)
```

**Key Insight**: Memory backend creation happens in SessionStart hook, NOT during launcher preparation. This means blarify prompt must happen before the hook.

### 2. Consent Prompt Pattern Discovered

**Location**: `src/amplihack/launcher/memory_config.py:513-617`

**Pattern**:
```python
def prompt_user_consent(
    config: Dict[str, Any],
    timeout_seconds: int = 30,
    default_response: bool = True,
    logger: Optional[logging.Logger] = None
) -> bool:
    """Prompt user for consent with timeout."""

    # 1. Check if interactive terminal
    if not is_interactive_terminal():
        return default_response

    # 2. Display configuration
    print("\n" + "="*60)
    print("Configuration Update")
    # ... details ...

    # 3. Get input with timeout
    response = get_user_input_with_timeout(prompt_msg, timeout_seconds)

    # 4. Handle timeout
    if response is None:
        return default_response

    # 5. Parse response
    return parse_consent_response(response, default_response)
```

**Reusable utilities found**:
- `is_interactive_terminal()` - detects TTY
- `get_user_input_with_timeout()` - cross-platform timeout (Unix signals + Windows threading)
- `parse_consent_response()` - handles yes/no/empty responses

**Already handles**:
- CI/CD environments (non-interactive)
- Keyboard interrupts
- EOF errors
- Graceful degradation

### 3. Neo4j Startup Pattern Identified

**Location**: `src/amplihack/launcher/core.py:912-944`

**Pattern to follow**:
```python
def prepare_launch(self) -> bool:
    """Prepare environment for launching Claude."""

    # 1. Prerequisites
    if not check_prerequisites():
        return False

    # 2. Neo4j credentials
    self._check_neo4j_credentials()

    # 3. Neo4j startup (BLOCKING, interactive)
    if not self._interactive_neo4j_startup():
        return False  # User chose to exit

    # 4. 🔵 BLARIFY PROMPT GOES HERE (new)
    self._prompt_for_blarify_indexing()  # Non-blocking

    # 5-11. Remaining steps
    # ...
```

**Key takeaway**: Step 3 (Neo4j) is blocking and can return False. Step 4 (blarify) should be non-blocking and always return True.

### 4. Caching Strategy Designed

**Cache location**: `~/.amplihack/.blarify_consent_<project_hash>`

**Hash calculation**:
```python
import hashlib
from pathlib import Path

project_root = Path.cwd()
project_hash = hashlib.md5(str(project_root).encode()).hexdigest()[:8]
# Example: /home/user/myproject → "a1b2c3d4"
```

**Cache file contents**:
```
prompted_at: 2026-01-22T20:30:15.123456
accepted: true
project_root: /home/user/myproject
```

**Why this works**:
- Per-project (different projects have different hashes)
- Survives project deletion (in user home directory)
- Simple to debug (plain text file)
- No database overhead
- Easy to reset (just delete file)

---

## Option Analysis Results

### All Options Evaluated

| Option | Location | Timing | Score | Recommendation |
|--------|----------|--------|-------|----------------|
| **A** | SessionStart hook | AFTER Claude starts | 3.65/10 | ❌ Not Recommended |
| **B** | Launcher prepare | BEFORE Claude starts | 9.5/10 | ✅ STRONGLY RECOMMENDED |
| **C** | CLI pre-launch | BEFORE prerequisites | 5.15/10 | ⚠️ Not Ideal |

### Option A: SessionStart Hook (REJECTED)

**Why rejected**:
- ❌ Claude process already started (user can't back out)
- ❌ Hook has strict 10-second timeout
- ❌ Blarify indexing takes 30-60 seconds
- ❌ Disruptive user experience
- ❌ Memory backend may already be initializing

**Risk**: 🔴 HIGH

**Use case**: None - timing is fundamentally wrong

### Option B: Launcher Prepare (RECOMMENDED)

**Why recommended**:
- ✅ Perfect timing (after prerequisites, before Claude)
- ✅ Follows Neo4j pattern (step 3 → step 4)
- ✅ Full launcher infrastructure available
- ✅ Non-blocking design (failure/decline doesn't stop launch)
- ✅ Clean integration (single method addition)
- ✅ Low risk (proven patterns, graceful degradation)

**Risk**: 🟢 LOW

**Use case**: This is the solution to implement

### Option C: CLI Pre-Launch (REJECTED)

**Why rejected**:
- ❌ Too early (before prerequisites checked)
- ❌ Limited infrastructure (no launcher logger, paths, etc.)
- ❌ Awkward placement (breaks logical flow)
- ❌ No existing pattern to follow

**Risk**: 🟡 MEDIUM

**Use case**: None - suboptimal integration point

---

## Implementation Specification

### Code Location

**File**: `src/amplihack/launcher/core.py`

**Methods to add** (around line 946):
1. `_prompt_for_blarify_indexing()` - main prompt logic (~100 lines)
2. `_is_blarify_available()` - check if blarify in PATH (~5 lines)
3. `_run_blarify_indexing()` - run blarify subprocess (~30 lines)

**Modification point**: Line 100 in `prepare_launch()`

```python
# 4. NEW: Interactive blarify indexing prompt
self._prompt_for_blarify_indexing()
```

### Dependencies

**Reuse from memory_config.py**:
- `get_user_input_with_timeout()` - cross-platform timeout
- `is_interactive_terminal()` - TTY detection
- `parse_consent_response()` - yes/no parsing

**Standard library**:
- `hashlib` - MD5 for project hash
- `subprocess` - run blarify command
- `pathlib` - path manipulation
- `datetime` - timestamps

**No new dependencies required**.

### Behavior Specification

**First session in project**:
1. Calculate project hash from `Path.cwd()`
2. Check if `~/.amplihack/.blarify_consent_<hash>` exists
3. If not exists:
   - Check if blarify available (`shutil.which("blarify")`)
   - Check if interactive terminal (`sys.stdin.isatty()`)
   - Display prompt with 30s timeout
   - On accept/timeout: Run `blarify analyze <project> -o .claude/runtime/code_graph.json`
   - On decline: Skip indexing
   - Write consent file (regardless of outcome)
4. Continue launch normally (non-blocking)

**Subsequent sessions**:
1. Calculate project hash
2. Check if consent file exists
3. If exists: Skip prompt, continue launch
4. Total overhead: ~10ms (file check)

**Non-interactive mode** (CI/CD):
1. Detect non-interactive terminal
2. Auto-create consent file (skip indexing)
3. Continue launch without prompt
4. Total overhead: ~50ms (file write)

### Error Handling

**All errors are non-blocking**:

| Error Scenario | Handling | User Impact |
|---------------|----------|-------------|
| Blarify not installed | Skip prompt, log debug | None |
| Blarify hangs | 120s subprocess timeout | 2-minute delay (first session only) |
| Indexing fails | Log warning, continue | Indexing unavailable, manual retry |
| Consent file write fails | Log warning, continue | Will re-prompt next session |
| User interrupts (Ctrl+C) | Catch KeyboardInterrupt, create consent | Prompt skipped, launch continues |
| Non-interactive mode | Auto-skip, create consent | No prompt shown |

**Philosophy**: Blarify is an enhancement, never a blocker.

---

## Testing Strategy

### Unit Tests

**File**: `tests/launcher/test_blarify_prompt.py`

**Test cases**:
```python
def test_consent_file_caching():
    """Test that consent file prevents re-prompting."""
    # Given: No consent file
    # When: First session accepts
    # Then: Consent file created
    # When: Second session starts
    # Then: No prompt shown

def test_timeout_defaults_to_yes():
    """Test that timeout results in indexing."""
    # Given: User provides no input
    # When: 30s timeout expires
    # Then: Indexing proceeds (default yes)

def test_blarify_unavailable():
    """Test graceful handling when blarify not installed."""
    # Given: blarify command not in PATH
    # When: Prompt triggered
    # Then: Skip silently, no error

def test_indexing_failure_non_blocking():
    """Test that indexing failure doesn't stop launch."""
    # Given: blarify command returns error
    # When: Indexing attempted
    # Then: Warning logged, launch continues

def test_non_interactive_mode():
    """Test auto-skip in CI/CD environments."""
    # Given: Non-interactive terminal (sys.stdin.isatty() = False)
    # When: Prompt triggered
    # Then: Consent file created, no prompt shown
```

### Integration Tests

**File**: `tests/launcher/test_blarify_integration.py`

**Test cases**:
```python
def test_prompt_happens_before_claude_starts():
    """Test timing: prompt before Claude subprocess."""
    # When: Launcher starts
    # Then: Blarify prompt appears
    # Then: Claude process not yet started

def test_first_vs_subsequent_sessions():
    """Test first session prompts, subsequent skip."""
    # Given: New project
    # When: First launch
    # Then: Prompt shown
    # When: Second launch
    # Then: No prompt

def test_code_graph_json_created():
    """Test that code_graph.json is created."""
    # When: User accepts indexing
    # Then: .claude/runtime/code_graph.json exists
    # Then: File contains valid JSON
```

### Manual Testing Checklist

- [ ] First session shows prompt
- [ ] Second session skips prompt
- [ ] Timeout (30s) defaults to "yes"
- [ ] User can decline ("n")
- [ ] Blarify not installed → graceful skip
- [ ] Blarify fails → warning logged, continues
- [ ] Non-interactive mode → auto-skip
- [ ] Windows timeout works (threading)
- [ ] Linux timeout works (signals)
- [ ] macOS timeout works (signals)
- [ ] code_graph.json created in correct location
- [ ] Consent file created with correct hash

---

## Risk Assessment

### Overall Risk: 🟢 LOW

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| **Blarify hangs** | Low | Medium | 120s subprocess timeout |
| **User confusion** | Low | Low | Clear prompt messaging, matches Neo4j |
| **Performance impact** | Low | Low | Only first session, ~30s one-time cost |
| **Consent file race** | Very Low | Low | Single-user assumption, atomic file writes |
| **Cross-platform issues** | Very Low | Low | Reusing battle-tested memory_config utilities |
| **Hook conflicts** | None | N/A | Not using hooks, launcher-only |
| **Memory backend conflicts** | None | N/A | Memory init happens later, no overlap |

### Confidence Level

**Implementation confidence**: ✅ Very High (95%)

**Reasons**:
- Reusing proven patterns (Neo4j startup, memory_config timeout)
- Non-blocking design (failure never stops launch)
- Simple file-based caching (no database complexity)
- Clear integration point (step 4 in prepare_launch)
- Comprehensive error handling (all edge cases covered)

---

## Implementation Checklist

### Phase 1: Core Implementation (2-3 hours)

- [ ] **Step 1**: Add `_prompt_for_blarify_indexing()` method
  - [ ] Implement consent file checking
  - [ ] Implement blarify availability check
  - [ ] Implement interactive prompt with timeout
  - [ ] Implement consent file writing
  - [ ] Add error handling (all non-blocking)

- [ ] **Step 2**: Add `_is_blarify_available()` helper
  - [ ] Use `shutil.which("blarify")`
  - [ ] Return boolean

- [ ] **Step 3**: Add `_run_blarify_indexing()` helper
  - [ ] Build subprocess command
  - [ ] Create output directory
  - [ ] Run with 120s timeout
  - [ ] Handle all exceptions

- [ ] **Step 4**: Insert call in `prepare_launch()`
  - [ ] Add after Neo4j startup (line 100)
  - [ ] Comment: "4. NEW: Interactive blarify indexing prompt"

- [ ] **Step 5**: Write unit tests
  - [ ] Test consent caching
  - [ ] Test timeout behavior
  - [ ] Test blarify unavailable
  - [ ] Test non-interactive mode
  - [ ] Test error handling

### Phase 2: Testing & Validation (1-2 hours)

- [ ] **Step 6**: Run unit tests
  - [ ] All tests pass
  - [ ] Code coverage >90%

- [ ] **Step 7**: Integration testing
  - [ ] Test with real launcher
  - [ ] Test first session flow
  - [ ] Test subsequent session flow

- [ ] **Step 8**: Cross-platform testing
  - [ ] Test on Linux (signal timeout)
  - [ ] Test on macOS (signal timeout)
  - [ ] Test on Windows (threading timeout)

- [ ] **Step 9**: Edge case testing
  - [ ] Blarify not installed
  - [ ] Blarify indexing fails
  - [ ] User interrupts (Ctrl+C)
  - [ ] Non-interactive mode (CI/CD)

### Phase 3: Documentation (30 minutes)

- [ ] **Step 10**: Update documentation
  - [ ] Add docstrings to new methods
  - [ ] Update CHANGELOG.md
  - [ ] Update user documentation (optional)

### Phase 4: Code Review & Merge

- [ ] **Step 11**: Self-review
  - [ ] Check coding standards
  - [ ] Run linters (ruff, black)
  - [ ] Verify no breaking changes

- [ ] **Step 12**: Submit PR
  - [ ] Write clear PR description
  - [ ] Link to investigation documents
  - [ ] Request review

---

## Success Criteria

### Must Have (Phase 1)

- [x] ✅ Traced complete CLI initialization flow
- [x] ✅ Identified optimal integration point
- [x] ✅ Analyzed 3 integration options
- [x] ✅ Designed prompt specification
- [x] ✅ Designed caching strategy
- [ ] Prompt appears on first session per project
- [ ] 30-second timeout with default "yes"
- [ ] Consent cached per project (no re-prompt)
- [ ] Non-blocking (failure/decline doesn't stop launch)
- [ ] Cross-platform timeout works
- [ ] Blarify indexing runs on consent
- [ ] code_graph.json created in .claude/runtime/

### Nice to Have (Future)

- [ ] Progress bar during indexing
- [ ] Statistics display (files/functions indexed)
- [ ] Re-indexing detection (check code_graph.json age)
- [ ] Manual re-index command (`amplihack reindex`)
- [ ] Integration with Kuzu backend (import code graph)
- [ ] Incremental indexing (only changed files)

---

## Next Steps

### Immediate Actions

1. **Review investigation documents** with team
   - `.claude/ai_working/cli_integration_investigation.md` (full analysis)
   - `.claude/ai_working/cli_initialization_sequence.md` (diagrams)
   - `.claude/ai_working/blarify_prompt_integration_options.md` (options)

2. **Approve implementation plan**
   - Option B: Launcher Prepare (step 4)
   - Phase 1: Core implementation (2-3 hours)
   - Non-blocking design

3. **Assign implementation**
   - Developer: [TBD]
   - Reviewer: [TBD]
   - Target branch: feature/blarify-prompt

4. **Begin implementation**
   - Create feature branch
   - Follow implementation checklist
   - Write tests as you go

### Blocked Items

None - all dependencies resolved:
- ✅ Reusable utilities identified (memory_config.py)
- ✅ Integration point confirmed (launcher.py:100)
- ✅ Caching strategy designed (~/.amplihack/)
- ✅ Error handling specified (all non-blocking)
- ✅ Testing strategy defined (unit + integration)

---

## Appendix: File References

### Investigation Documents

1. **Main Report** (27 KB)
   - Path: `.claude/ai_working/cli_integration_investigation.md`
   - Sections: 15
   - Details: Complete flow trace, pattern analysis, options, specs

2. **Sequence Diagrams** (15 KB)
   - Path: `.claude/ai_working/cli_initialization_sequence.md`
   - Diagrams: 8
   - Details: Timing analysis, integration points, decision trees

3. **Options Analysis** (23 KB)
   - Path: `.claude/ai_working/blarify_prompt_integration_options.md`
   - Options: 3
   - Details: Pros/cons, code samples, migration paths

4. **Summary** (this file, 12 KB)
   - Path: `.claude/ai_working/INVESTIGATION_SUMMARY.md`
   - Sections: 10
   - Details: Executive summary, key findings, next steps

### Key Source Files

1. **CLI Entry**
   - `pyproject.toml:58` - Entry point definition
   - `src/amplihack/__init__.py:108-113` - Main dispatcher
   - `src/amplihack/cli.py:68-249` - CLI router

2. **Launcher** (Integration point)
   - `src/amplihack/launcher/core.py:84-134` - prepare_launch()
   - `src/amplihack/launcher/core.py:912-944` - Neo4j startup pattern
   - 🔵 **Line 100** - INSERT BLARIFY PROMPT HERE

3. **Utilities** (Reuse)
   - `src/amplihack/launcher/memory_config.py:400-510` - Timeout
   - `src/amplihack/launcher/memory_config.py:334-358` - TTY detection
   - `src/amplihack/launcher/memory_config.py:513-617` - Consent pattern

4. **Hooks** (Context only, no changes)
   - `.claude/tools/amplihack/hooks/session_start.py:37-200` - SessionStart
   - Memory backend initialized here (AFTER prompt)

5. **Memory Backend** (Context only, no changes)
   - `src/amplihack/memory/backends/kuzu_backend.py:40-100` - KuzuBackend
   - `src/amplihack/memory/__init__.py` - Exports

---

## Investigation Metrics

**Time Spent**: ~45 minutes

**Files Analyzed**: 15+

**Documentation Generated**: 4 files, ~75 KB total

**Lines of Code to Write**: ~150 lines

**Estimated Implementation Time**: 2-3 hours

**Confidence in Recommendation**: 95%

**Risk Assessment**: 🟢 LOW

**Go/No-Go Decision**: ✅ **GO** - Proceed with Option B implementation

---

## Contact & Questions

For questions about this investigation:
- Review detailed analysis: `cli_integration_investigation.md`
- View sequence diagrams: `cli_initialization_sequence.md`
- Compare all options: `blarify_prompt_integration_options.md`

For implementation questions:
- Code location: `src/amplihack/launcher/core.py:100`
- Pattern to follow: Neo4j startup (line 912-944)
- Utilities to reuse: `memory_config.py`

---

*Investigation completed: 2026-01-22*
*Status: ✅ COMPLETE - Ready for implementation*
*Next action: Team review and approval*
