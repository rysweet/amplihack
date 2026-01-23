# Blarify Prompt Integration Options

**Purpose**: Detailed comparison of 3 integration options for blarify code indexing prompt

**Date**: 2026-01-22

---

## Option A: SessionStart Hook

### Overview

Add blarify prompt to `.claude/tools/amplihack/hooks/session_start.py` during hook processing.

### Implementation

```python
# .claude/tools/amplihack/hooks/session_start.py (lines 43-57)

class SessionStartHook(HookProcessor):
    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process session start event."""
        # Check for version mismatch FIRST
        self._check_version_mismatch()

        # NEW: Check for global hook duplication and migrate
        self._migrate_global_hooks()

        # 🔵 INSERT BLARIFY PROMPT HERE (NEW)
        if not self._prompt_for_blarify_indexing():
            # User declined or error - continue without indexing
            self.log("Blarify indexing skipped", "INFO")

        # Detect launcher and select strategy
        strategy = self._select_strategy()
        # ... rest of hook processing ...
```

### Timing

```
User → Launch → Claude Process Starts → SessionStart Hook (T+62s)
                                              ↓
                                        Blarify Prompt
                                              ↓
                                        Memory Backend Init
```

### Pros

- Hook infrastructure available (HookProcessor logging, metrics)
- Access to project context and session info
- Clean separation from CLI launcher code
- Can save metrics via `self.save_metric()`
- Existing error handling patterns

### Cons

- ❌ **TIMING: Claude process already started**
  - User already in Claude session, can't back out easily
  - Prompt appears after "Claude is loading" phase
  - Disruptive to user experience

- ❌ **Hook execution constraints**
  - Hooks have strict timeouts (10s default for SessionStart)
  - Blarify indexing can take 30-60s
  - Would need to increase hook timeout or run async

- ❌ **Memory backend may already be initialized**
  - If memory backend init happens before hook, too late
  - Race condition between hook steps

- ❌ **Error propagation unclear**
  - Hook failures are logged but don't stop Claude
  - User might not notice if indexing failed

### Code Changes Required

```python
# .claude/tools/amplihack/hooks/session_start.py

def _prompt_for_blarify_indexing(self) -> bool:
    """Prompt user for blarify code indexing (first session per project)."""
    import hashlib
    from pathlib import Path

    # Check consent cache
    project_hash = hashlib.md5(str(self.project_root).encode()).hexdigest()[:8]
    consent_file = Path.home() / ".amplihack" / f".blarify_consent_{project_hash}"

    if consent_file.exists():
        return True  # Already prompted

    # Prompt logic here (with timeout)
    # ...

    return True  # Non-blocking
```

**Lines modified**: ~50-100 lines in session_start.py

### Risk Assessment

| Risk | Likelihood | Impact | Severity |
|------|-----------|--------|----------|
| Hook timeout | High | Medium | 🔴 High |
| User confusion | High | Medium | 🔴 High |
| Race condition | Medium | Low | 🟡 Medium |
| Async complexity | Medium | High | 🟡 Medium |

**Overall Risk**: 🔴 **HIGH** - Too many unknowns, disruptive timing

### Recommendation

❌ **NOT RECOMMENDED** - Timing is fundamentally wrong for user prompts

---

## Option B: Memory Initialization in Launcher (RECOMMENDED)

### Overview

Add blarify prompt to `src/amplihack/launcher/core.py:prepare_launch()` as step 4, immediately after Neo4j startup (step 3).

### Implementation

```python
# src/amplihack/launcher/core.py (lines 84-134)

class ClaudeLauncher:
    def prepare_launch(self) -> bool:
        """Prepare environment for launching Claude."""
        # 1. Check prerequisites first - fail fast with helpful guidance
        if not check_prerequisites():
            return False

        # 2. Check and sync Neo4j credentials from existing containers
        self._check_neo4j_credentials()

        # 3. Interactive Neo4j startup (blocks until ready or user decides)
        if not self._interactive_neo4j_startup():
            # User chose to exit rather than continue without Neo4j
            return False

        # 🔵 4. NEW: Interactive blarify indexing prompt
        if not self._prompt_for_blarify_indexing():
            # Non-blocking - user declined or error, but continue launch
            pass

        # 5. Handle repository checkout if needed
        if self.checkout_repo:
            if not self._handle_repo_checkout():
                return False

        # 6-11. Remaining steps (target dir, runtime dirs, hook paths, etc.)
        # ...
```

### Timing

```
User → Launch → Prepare Phase (T+0.6s)
                    ↓
                Prerequisites (T+0.6s)
                    ↓
                Neo4j Startup (T+0.7s - T+30s)
                    ↓
                🔵 Blarify Prompt (T+30s - T+60s)
                    ↓
                Remaining Prep (T+60s)
                    ↓
                Claude Starts (T+61s)
```

### Pros

- ✅ **PERFECT TIMING: Before Claude starts**
  - User sees prompt during natural "setup" phase
  - Can make informed decision before committing to session
  - Consistent with Neo4j startup pattern

- ✅ **Infrastructure access**
  - Logger available (`self.logger`)
  - Subprocess management
  - Path resolution
  - Proxy manager if needed

- ✅ **Follows existing patterns**
  - Mirrors Neo4j startup (step 3)
  - Similar user experience flow
  - Consistent error handling

- ✅ **Non-blocking design**
  - Returns True even on failure/decline
  - Continues to next step regardless
  - User never stuck

- ✅ **Clean integration**
  - Single method addition to ClaudeLauncher
  - No hook modifications
  - Self-contained logic

### Cons

- Requires new method in ClaudeLauncher class (~100 lines)
- Adds 1-2 seconds to first-session startup (acceptable)
- Need to handle cross-platform timeout (already solved in memory_config.py)

### Code Changes Required

```python
# src/amplihack/launcher/core.py (new methods around line 946)

def _prompt_for_blarify_indexing(self) -> bool:
    """Prompt user for blarify code indexing (first session per project).

    Returns:
        True if indexing completed or user accepted (non-blocking)
        False never returned - method always succeeds
    """
    import hashlib
    from pathlib import Path
    from .memory_config import get_user_input_with_timeout, is_interactive_terminal

    # 1. Check consent cache
    project_root = Path.cwd()
    project_hash = hashlib.md5(str(project_root).encode()).hexdigest()[:8]
    consent_file = Path.home() / ".amplihack" / f".blarify_consent_{project_hash}"

    if consent_file.exists():
        return True  # Already prompted

    # 2. Check blarify availability
    if not self._is_blarify_available():
        return True  # Not an error

    # 3. Check interactive terminal
    if not is_interactive_terminal():
        # Auto-skip in non-interactive mode
        return True

    # 4. Display prompt
    print("\n" + "="*70)
    print("📚 Code Indexing - First Session Setup")
    print("="*70)
    print("\nWould you like to index this codebase with blarify?")
    print("This enables:")
    print("  • Code graph navigation in Claude sessions")
    print("  • Function/class relationship tracking")
    print("  • Enhanced memory-to-code linking")
    print("\nIndexing time: ~30 seconds for typical projects")
    print("Default: Yes (timeout: 30s)")
    print("="*70)

    # 5. Get user input with timeout
    response = get_user_input_with_timeout(
        "\nIndex codebase now? [Y/n]: ",
        timeout_seconds=30,
        logger=logger
    )

    # 6. Handle response
    if response is None or response.strip().lower() in ['', 'y', 'yes']:
        # User accepted or timeout (default yes)
        print("\n🔄 Running blarify indexing...")
        success = self._run_blarify_indexing()

        if success:
            print("✅ Indexing complete!\n")
        else:
            print("⚠️  Indexing failed (non-blocking)\n")
    else:
        print("\n⏭️  Skipping indexing (you can run manually later)\n")

    # 7. Mark as prompted
    consent_file.parent.mkdir(parents=True, exist_ok=True)
    consent_file.write_text(f"prompted_at: {datetime.now().isoformat()}\n")

    return True  # Always continue


def _is_blarify_available(self) -> bool:
    """Check if blarify command is available."""
    import shutil
    return shutil.which("blarify") is not None


def _run_blarify_indexing(self) -> bool:
    """Run blarify indexing for current project."""
    try:
        import subprocess
        from pathlib import Path

        project_root = Path.cwd()
        output_file = project_root / ".claude" / "runtime" / "code_graph.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["blarify", "analyze", str(project_root), "-o", str(output_file)],
            capture_output=True,
            text=True,
            timeout=120  # 2 minute timeout
        )

        return result.returncode == 0
    except Exception as e:
        logger.warning(f"Blarify indexing failed: {e}")
        return False
```

**Lines modified**: ~150 lines (3 new methods in ClaudeLauncher)

**Insertion point**: Line 100 in `prepare_launch()`

### Risk Assessment

| Risk | Likelihood | Impact | Severity |
|------|-----------|--------|----------|
| Blarify hangs | Low | Medium | 🟢 Low |
| User confusion | Low | Low | 🟢 Low |
| Performance impact | Low | Low | 🟢 Low |
| Integration complexity | Low | Low | 🟢 Low |
| Cross-platform issues | Very Low | Low | 🟢 Very Low |

**Overall Risk**: 🟢 **LOW** - Well-contained, proven patterns

### Recommendation

✅ **STRONGLY RECOMMENDED** - Optimal timing, clean integration, low risk

---

## Option C: CLI Command Pre-Launch

### Overview

Add blarify prompt to `src/amplihack/cli.py:_launch_command_impl()` before ClaudeLauncher is created.

### Implementation

```python
# src/amplihack/cli.py (lines 135-151)

def _launch_command_impl(
    args: argparse.Namespace,
    claude_args: list[str] | None,
    session_id: str,
    tracker: SessionTracker,
) -> int:
    """Internal implementation of launch_command with session tracking."""
    # Set environment variable for Neo4j opt-in
    if getattr(args, "use_graph_mem", False):
        os.environ["AMPLIHACK_USE_GRAPH_MEM"] = "1"
        print("Neo4j graph memory enabled")

    # 🔵 INSERT BLARIFY PROMPT HERE (NEW)
    if not _prompt_for_blarify_if_needed():
        # User declined or error - continue anyway
        pass

    # Check if Docker should be used
    use_docker = getattr(args, "docker", False) or DockerManager.should_use_docker()
    # ...
```

### Timing

```
User → Launch → _launch_command_impl (T+0.3s)
                    ↓
                🔵 Blarify Prompt (T+0.3s - T+30s)
                    ↓
                Docker Check (T+30s)
                    ↓
                ClaudeLauncher Created (T+31s)
                    ↓
                Prepare Phase (T+31s)
```

### Pros

- Very early in the flow (before launcher)
- Can check session tracker for first-session detection
- Easy to add without modifying ClaudeLauncher class
- Simple function call

### Cons

- ❌ **TOO EARLY in the flow**
  - Before `check_prerequisites()` - don't know if environment is ready
  - Before launcher infrastructure is available
  - Can't use launcher logger, subprocess management, etc.

- ❌ **Awkward placement**
  - Not grouped with other interactive prompts (Neo4j)
  - Breaks logical flow (environment setup → prompts → execution)
  - Inconsistent with existing patterns

- ❌ **Limited infrastructure**
  - No logger available (would need to create one)
  - No clear error handling pattern
  - Hard to access project context

- ❌ **Harder to test**
  - CLI function, not a class method
  - Need to mock CLI arguments
  - Less isolated than launcher method

### Code Changes Required

```python
# src/amplihack/cli.py (new function around line 250)

def _prompt_for_blarify_if_needed() -> bool:
    """Prompt user for blarify code indexing (first session per project).

    Standalone function for CLI integration.
    """
    # Similar logic to Option B, but without launcher infrastructure
    # Need to create own logger, handle paths, etc.
    # ~100 lines of code

    pass


# Modify _launch_command_impl
def _launch_command_impl(...):
    # ... existing code ...

    # Insert call
    _prompt_for_blarify_if_needed()

    # ... continue ...
```

**Lines modified**: ~120 lines (new function + 1 line insertion)

### Risk Assessment

| Risk | Likelihood | Impact | Severity |
|------|-----------|--------|----------|
| Prerequisites not checked | High | Medium | 🔴 High |
| Infrastructure missing | High | Medium | 🔴 High |
| Awkward user flow | High | Low | 🟡 Medium |
| Testing complexity | Medium | Medium | 🟡 Medium |

**Overall Risk**: 🟡 **MEDIUM** - Workable but suboptimal

### Recommendation

⚠️ **NOT IDEAL** - Too early, awkward placement, limited infrastructure

---

## Comparative Analysis

### Timing Comparison

```
Option A (SessionStart Hook):      [Prerequisites][Neo4j][Claude Start] → [Hook] → [Blarify Prompt]
                                                                                        ↑ TOO LATE

Option B (Launcher Prepare):       [Prerequisites][Neo4j] → [Blarify Prompt] → [Remaining] → [Claude Start]
                                                                  ↑ PERFECT TIMING

Option C (CLI Pre-Launch):         [Blarify Prompt] → [Prerequisites][Neo4j][Prepare] → [Claude Start]
                                         ↑ TOO EARLY
```

### Feature Matrix

| Feature | Option A | Option B | Option C |
|---------|----------|----------|----------|
| **Timing** | ❌ After Claude starts | ✅ Before Claude starts | ⚠️ Before prerequisites |
| **User Experience** | ❌ Disruptive | ✅ Smooth | ⚠️ Awkward |
| **Infrastructure** | ⚠️ Hook-specific | ✅ Full launcher access | ❌ Limited |
| **Pattern Consistency** | ⚠️ New pattern | ✅ Matches Neo4j | ❌ No precedent |
| **Error Handling** | ⚠️ Hook timeout | ✅ Non-blocking | ⚠️ Unclear |
| **Testing** | ⚠️ Hook testing | ✅ Unit testable | ⚠️ CLI testing |
| **Code Location** | Hook file | Launcher method | CLI function |
| **Lines of Code** | ~100 | ~150 | ~120 |
| **Integration Risk** | 🔴 High | 🟢 Low | 🟡 Medium |

### Decision Matrix

| Criteria | Weight | Option A Score | Option B Score | Option C Score |
|----------|--------|----------------|----------------|----------------|
| Timing correctness | 30% | 2/10 | 10/10 | 5/10 |
| User experience | 25% | 3/10 | 10/10 | 6/10 |
| Code quality | 15% | 6/10 | 9/10 | 5/10 |
| Pattern consistency | 15% | 5/10 | 10/10 | 3/10 |
| Risk level | 10% | 3/10 | 9/10 | 6/10 |
| Testing ease | 5% | 5/10 | 9/10 | 5/10 |

**Weighted Scores**:
- Option A: **3.65/10** (36.5%)
- Option B: **9.5/10** (95%)
- Option C: **5.15/10** (51.5%)

**Clear Winner**: Option B (Launcher Prepare)

---

## Implementation Roadmap

### Phase 1: Core Implementation (Option B)

**Estimated time**: 2-3 hours

**Tasks**:
1. Add `_prompt_for_blarify_indexing()` to ClaudeLauncher (1 hour)
2. Add `_is_blarify_available()` helper (15 minutes)
3. Add `_run_blarify_indexing()` helper (30 minutes)
4. Insert call in `prepare_launch()` (5 minutes)
5. Write unit tests (1 hour)

**Deliverables**:
- [ ] Core prompt functionality working
- [ ] Consent file caching implemented
- [ ] Non-blocking error handling
- [ ] Basic unit tests passing

### Phase 2: Testing & Refinement

**Estimated time**: 1-2 hours

**Tasks**:
1. Integration testing with real launcher (30 minutes)
2. Cross-platform testing (Windows, Linux, macOS) (1 hour)
3. Edge case handling (blarify not found, indexing fails, etc.) (30 minutes)
4. Documentation updates (30 minutes)

**Deliverables**:
- [ ] All tests passing on all platforms
- [ ] Edge cases handled gracefully
- [ ] User documentation updated

### Phase 3: Optional Enhancements

**Estimated time**: 4-6 hours (optional)

**Tasks**:
1. Progress bar for indexing (1 hour)
2. Statistics display (files/functions indexed) (1 hour)
3. Re-indexing detection (check code_graph.json age) (1 hour)
4. Manual re-index command (`amplihack reindex`) (2 hours)
5. Integration with Kuzu backend (import code graph) (2 hours)

**Deliverables**:
- [ ] Enhanced user feedback
- [ ] Manual control over indexing
- [ ] Memory-to-code linking

---

## Migration Path (If Needed)

If we later decide to change from Option B to another option:

### Option B → Option A (Unlikely)

**Reason to migrate**: Want to leverage hook infrastructure

**Steps**:
1. Move `_prompt_for_blarify_indexing()` to SessionStartHook class
2. Call in `process()` method instead of `prepare_launch()`
3. Adjust timeout to fit within hook constraints
4. Test hook timing

**Effort**: 1-2 hours

**Risk**: High (timing issues)

### Option B → Option C (Unlikely)

**Reason to migrate**: Want earlier timing

**Steps**:
1. Extract `_prompt_for_blarify_indexing()` to standalone function
2. Move to CLI module
3. Call in `_launch_command_impl()`
4. Remove from launcher

**Effort**: 1 hour

**Risk**: Medium (infrastructure loss)

---

## Final Recommendation

### Winner: Option B - Memory Initialization in Launcher

**Rationale**:
1. **Optimal timing**: Before Claude starts, after prerequisites checked
2. **Perfect integration**: Follows Neo4j startup pattern (step 3 → step 4)
3. **Low risk**: Non-blocking, proven patterns, full infrastructure access
4. **Best UX**: User sees prompt during natural setup phase
5. **Highest score**: 9.5/10 weighted score (95%)

**Implementation plan**: Phase 1 only (2-3 hours)

**Go/No-Go**: ✅ **GO** - Proceed with implementation

---

## Appendix: Code Snippets

### Option B: Complete Implementation

```python
# src/amplihack/launcher/core.py

def prepare_launch(self) -> bool:
    """Prepare environment for launching Claude.

    Returns:
        True if preparation successful, False otherwise.
    """
    # 1. Check prerequisites first - fail fast with helpful guidance
    if not check_prerequisites():
        return False

    # 2. Check and sync Neo4j credentials from existing containers (if any)
    self._check_neo4j_credentials()

    # 3. Interactive Neo4j startup (blocks until ready or user decides)
    if not self._interactive_neo4j_startup():
        # User chose to exit rather than continue without Neo4j
        return False

    # 4. NEW: Interactive blarify indexing prompt (non-blocking)
    self._prompt_for_blarify_indexing()

    # 5. Handle repository checkout if needed
    if self.checkout_repo:
        if not self._handle_repo_checkout():
            return False

    # 6-11. Remaining steps...
    # (existing code continues)


def _prompt_for_blarify_indexing(self) -> bool:
    """Prompt user for blarify code indexing (first session per project).

    Non-blocking: Always returns True to continue launch.
    Caches consent per project in ~/.amplihack/.blarify_consent_<hash>

    Returns:
        True (always - never blocks launch)
    """
    import hashlib
    from datetime import datetime
    from pathlib import Path

    from .memory_config import get_user_input_with_timeout, is_interactive_terminal

    # 1. Calculate project hash for consent caching
    project_root = Path.cwd()
    project_hash = hashlib.md5(str(project_root).encode()).hexdigest()[:8]
    consent_file = Path.home() / ".amplihack" / f".blarify_consent_{project_hash}"

    # 2. Check if already prompted
    if consent_file.exists():
        logger.debug("Blarify consent already given for this project")
        return True

    # 3. Check blarify availability
    if not self._is_blarify_available():
        logger.debug("Blarify not available, skipping prompt")
        return True

    # 4. Check interactive terminal
    if not is_interactive_terminal():
        logger.info("Non-interactive mode, skipping blarify prompt")
        # Auto-create consent file to avoid re-prompting in future
        consent_file.parent.mkdir(parents=True, exist_ok=True)
        consent_file.write_text(f"skipped_non_interactive: {datetime.now().isoformat()}\n")
        return True

    # 5. Display prompt
    print("\n" + "="*70)
    print("📚 Code Indexing - First Session Setup")
    print("="*70)
    print("\nWould you like to index this codebase with blarify?")
    print("This enables:")
    print("  • Code graph navigation in Claude sessions")
    print("  • Function/class relationship tracking")
    print("  • Enhanced memory-to-code linking")
    print("\nIndexing time: ~30 seconds for typical projects")
    print("Default: Yes (timeout: 30s)")
    print("="*70)

    # 6. Get user input with timeout
    try:
        response = get_user_input_with_timeout(
            "\nIndex codebase now? [Y/n]: ",
            timeout_seconds=30,
            logger=logger
        )
    except Exception as e:
        logger.warning(f"Failed to get user input: {e}")
        # Auto-accept on error
        response = None

    # 7. Handle response
    accepted = False
    if response is None or response.strip().lower() in ['', 'y', 'yes']:
        # User accepted or timeout (default yes)
        accepted = True
        print("\n🔄 Running blarify indexing...")

        try:
            success = self._run_blarify_indexing()

            if success:
                print("✅ Indexing complete!\n")
            else:
                print("⚠️  Indexing failed (non-blocking, continuing launch)\n")
        except Exception as e:
            logger.warning(f"Blarify indexing error: {e}")
            print(f"⚠️  Indexing error: {e} (continuing launch)\n")
    else:
        # User declined
        print("\n⏭️  Skipping indexing (you can run manually later with `blarify analyze`)\n")

    # 8. Mark as prompted (always, regardless of outcome)
    try:
        consent_file.parent.mkdir(parents=True, exist_ok=True)
        consent_data = f"prompted_at: {datetime.now().isoformat()}\n"
        consent_data += f"accepted: {accepted}\n"
        consent_data += f"project_root: {project_root}\n"
        consent_file.write_text(consent_data)
    except Exception as e:
        logger.warning(f"Failed to write consent file: {e}")

    return True  # Always continue


def _is_blarify_available(self) -> bool:
    """Check if blarify command is available in PATH.

    Returns:
        True if blarify found, False otherwise
    """
    import shutil
    return shutil.which("blarify") is not None


def _run_blarify_indexing(self) -> bool:
    """Run blarify indexing for current project.

    Generates code_graph.json in .claude/runtime/ directory.

    Returns:
        True if indexing successful, False otherwise
    """
    import subprocess
    from pathlib import Path

    try:
        project_root = Path.cwd()
        output_file = project_root / ".claude" / "runtime" / "code_graph.json"

        # Ensure output directory exists
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Run blarify analyze with 2-minute timeout
        result = subprocess.run(
            ["blarify", "analyze", str(project_root), "-o", str(output_file)],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            logger.info(f"Blarify indexing successful: {output_file}")
            return True
        else:
            logger.warning(f"Blarify indexing failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.warning("Blarify indexing timed out after 120s")
        return False
    except Exception as e:
        logger.warning(f"Blarify indexing error: {e}")
        return False
```

---

*Options analysis completed: 2026-01-22*
*Recommendation: Option B (Launcher Prepare)*
*Confidence: Very High (95%)*
