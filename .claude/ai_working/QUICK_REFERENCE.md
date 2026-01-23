# Blarify Prompt Integration - Quick Reference

**One-page reference for implementation**

---

## THE SOLUTION

Add blarify prompt to `ClaudeLauncher.prepare_launch()` at line 100, right after Neo4j startup.

```python
# src/amplihack/launcher/core.py:100

def prepare_launch(self) -> bool:
    # ... steps 1-3 (prerequisites, Neo4j credentials, Neo4j startup) ...

    # 4. NEW: Interactive blarify indexing prompt
    self._prompt_for_blarify_indexing()  # <-- INSERT HERE

    # ... steps 5-11 (remaining prep) ...
```

**Why here?**
- ✅ AFTER prerequisites checked (environment ready)
- ✅ BEFORE Claude starts (user can decide)
- ✅ Matches Neo4j pattern (consistent UX)

---

## FILES TO MODIFY

### 1. src/amplihack/launcher/core.py

**Add 3 methods** (around line 946):

```python
def _prompt_for_blarify_indexing(self) -> bool:
    """Prompt user for blarify indexing (first session per project).

    Returns:
        True (always - non-blocking)
    """
    # 1. Check consent cache: ~/.amplihack/.blarify_consent_<hash>
    # 2. If cached: return True
    # 3. Check blarify available: shutil.which("blarify")
    # 4. Check interactive: is_interactive_terminal()
    # 5. Display prompt with 30s timeout
    # 6. On accept/timeout: run blarify analyze
    # 7. Create consent file
    # 8. Return True (always continue)

def _is_blarify_available(self) -> bool:
    """Check if blarify in PATH."""
    import shutil
    return shutil.which("blarify") is not None

def _run_blarify_indexing(self) -> bool:
    """Run blarify analyze with 120s timeout."""
    subprocess.run(
        ["blarify", "analyze", str(project_root), "-o", str(output_file)],
        timeout=120
    )
```

**Insert call** at line 100:
```python
# 4. NEW: Interactive blarify indexing prompt
self._prompt_for_blarify_indexing()
```

---

## CONSENT FILE FORMAT

**Location**: `~/.amplihack/.blarify_consent_<project_hash>`

**Hash calculation**:
```python
import hashlib
project_hash = hashlib.md5(str(Path.cwd()).encode()).hexdigest()[:8]
```

**File contents**:
```
prompted_at: 2026-01-22T20:30:15.123456
accepted: true
project_root: /home/user/myproject
```

---

## PROMPT FORMAT

```
======================================================================
📚 Code Indexing - First Session Setup
======================================================================

Would you like to index this codebase with blarify?
This enables:
  • Code graph navigation in Claude sessions
  • Function/class relationship tracking
  • Enhanced memory-to-code linking

Indexing time: ~30 seconds for typical projects
Default: Yes (timeout: 30s)
======================================================================

Index codebase now? [Y/n]:
```

**Behavior**:
- Empty/timeout → **yes** (default)
- "y" or "yes" → **yes**
- "n" or "no" → **no**

---

## REUSABLE UTILITIES

From `src/amplihack/launcher/memory_config.py`:

```python
from .memory_config import (
    get_user_input_with_timeout,  # Cross-platform timeout (30s)
    is_interactive_terminal,       # Detects TTY
    parse_consent_response,        # Parses yes/no
)

# Example usage:
response = get_user_input_with_timeout(
    "\nIndex codebase now? [Y/n]: ",
    timeout_seconds=30,
    logger=logger
)
```

---

## ERROR HANDLING

**All errors are non-blocking** (always continue launch):

```python
# Blarify not installed
if not self._is_blarify_available():
    return True  # Skip silently

# Non-interactive mode
if not is_interactive_terminal():
    consent_file.write_text("skipped_non_interactive\n")
    return True

# Indexing fails
try:
    result = subprocess.run([...], timeout=120)
except Exception as e:
    logger.warning(f"Blarify error: {e}")
    return True  # Continue anyway

# Always return True at end
return True  # Never block launch
```

---

## TIMING

```
T+0.0s    User runs: amplihack launch
T+0.6s    Prerequisites check
T+0.7s    Neo4j credentials sync
T+0.8s    Neo4j startup dialog (may block 30s)
T+30.0s   🔵 BLARIFY PROMPT (new, 30s timeout)
T+60.0s   Blarify indexing (if accepted, 30s)
T+90.0s   Remaining prep steps
T+91.0s   Claude subprocess starts
T+92.0s   SessionStart hook
T+92.5s   Memory backend initialized
```

**First session**: +60s (30s prompt + 30s indexing)
**Subsequent sessions**: +10ms (file check only)

---

## TESTING CHECKLIST

### Unit Tests
- [ ] Consent file caching works
- [ ] Timeout defaults to yes
- [ ] Blarify unavailable → skip gracefully
- [ ] Indexing failure → continue launch
- [ ] Non-interactive mode → auto-skip

### Integration Tests
- [ ] First session shows prompt
- [ ] Second session skips prompt
- [ ] Prompt before Claude starts
- [ ] code_graph.json created

### Manual Tests
- [ ] Works on Linux (signal timeout)
- [ ] Works on Windows (threading timeout)
- [ ] Works on macOS (signal timeout)
- [ ] User can accept ("y")
- [ ] User can decline ("n")
- [ ] Timeout works (30s)

---

## OUTPUT FILES

**Consent file**:
```
~/.amplihack/.blarify_consent_a1b2c3d4
```

**Code graph JSON**:
```
<project>/.claude/runtime/code_graph.json
```

---

## IMPLEMENTATION ESTIMATE

**Total effort**: 2-3 hours

**Breakdown**:
- Add 3 methods to ClaudeLauncher: 1 hour
- Insert call in prepare_launch(): 5 minutes
- Write unit tests: 1 hour
- Integration testing: 30 minutes
- Documentation: 30 minutes

---

## DECISION RATIONALE

**Why Option B (Launcher)?**

| Criteria | Score | Reason |
|----------|-------|--------|
| Timing | 10/10 | Before Claude, after prereqs |
| UX | 10/10 | Matches Neo4j pattern |
| Risk | 9/10 | Non-blocking, proven utilities |
| Integration | 9/10 | Clean, single insertion point |
| **Total** | **9.5/10** | Clear winner |

**Why NOT Option A (Hook)?**
- ❌ Claude already started (too late)
- ❌ Hook timeout constraints (10s)
- ❌ Disruptive to user

**Why NOT Option C (CLI)?**
- ❌ Before prerequisites (too early)
- ❌ Limited infrastructure
- ❌ Awkward placement

---

## FULL CODE SAMPLE

```python
# src/amplihack/launcher/core.py (add around line 946)

def _prompt_for_blarify_indexing(self) -> bool:
    """Prompt user for blarify indexing (first session per project)."""
    import hashlib
    from datetime import datetime
    from pathlib import Path
    from .memory_config import get_user_input_with_timeout, is_interactive_terminal

    # 1. Check consent cache
    project_root = Path.cwd()
    project_hash = hashlib.md5(str(project_root).encode()).hexdigest()[:8]
    consent_file = Path.home() / ".amplihack" / f".blarify_consent_{project_hash}"

    if consent_file.exists():
        logger.debug("Blarify: consent cached")
        return True

    # 2. Check blarify available
    if not self._is_blarify_available():
        logger.debug("Blarify: not available")
        return True

    # 3. Check interactive
    if not is_interactive_terminal():
        logger.info("Blarify: non-interactive, skipping")
        consent_file.parent.mkdir(parents=True, exist_ok=True)
        consent_file.write_text(f"skipped_non_interactive: {datetime.now().isoformat()}\n")
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

    # 5. Get input with timeout
    try:
        response = get_user_input_with_timeout(
            "\nIndex codebase now? [Y/n]: ",
            timeout_seconds=30,
            logger=logger
        )
    except Exception as e:
        logger.warning(f"Input error: {e}")
        response = None

    # 6. Handle response
    accepted = False
    if response is None or response.strip().lower() in ['', 'y', 'yes']:
        accepted = True
        print("\n🔄 Running blarify indexing...")

        try:
            success = self._run_blarify_indexing()
            if success:
                print("✅ Indexing complete!\n")
            else:
                print("⚠️  Indexing failed (continuing launch)\n")
        except Exception as e:
            logger.warning(f"Indexing error: {e}")
            print(f"⚠️  Indexing error (continuing launch)\n")
    else:
        print("\n⏭️  Skipping indexing (run manually: blarify analyze)\n")

    # 7. Write consent file
    try:
        consent_file.parent.mkdir(parents=True, exist_ok=True)
        consent_data = f"prompted_at: {datetime.now().isoformat()}\n"
        consent_data += f"accepted: {accepted}\n"
        consent_file.write_text(consent_data)
    except Exception as e:
        logger.warning(f"Consent file error: {e}")

    return True  # Always continue


def _is_blarify_available(self) -> bool:
    """Check if blarify in PATH."""
    import shutil
    return shutil.which("blarify") is not None


def _run_blarify_indexing(self) -> bool:
    """Run blarify analyze."""
    import subprocess
    from pathlib import Path

    try:
        project_root = Path.cwd()
        output_file = project_root / ".claude" / "runtime" / "code_graph.json"
        output_file.parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["blarify", "analyze", str(project_root), "-o", str(output_file)],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            logger.info(f"Blarify success: {output_file}")
            return True
        else:
            logger.warning(f"Blarify failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.warning("Blarify timeout (120s)")
        return False
    except Exception as e:
        logger.warning(f"Blarify error: {e}")
        return False
```

**Then insert call at line 100**:
```python
def prepare_launch(self) -> bool:
    """Prepare environment for launching Claude."""
    # ... steps 1-3 ...

    # 4. NEW: Interactive blarify indexing prompt
    self._prompt_for_blarify_indexing()

    # ... steps 5-11 ...
```

---

## KEY REMINDERS

✅ **DO**:
- Return True always (non-blocking)
- Check consent cache first
- Use 30s timeout with default yes
- Write consent file regardless of outcome
- Log all errors as warnings (not errors)
- Reuse memory_config utilities

❌ **DON'T**:
- Return False (would block launch)
- Prompt more than once per project
- Skip consent file creation
- Use hooks (wrong timing)
- Add new dependencies
- Crash on any error

---

## REFERENCES

**Full Analysis**:
- Main report: `.claude/ai_working/cli_integration_investigation.md`
- Sequence diagrams: `.claude/ai_working/cli_initialization_sequence.md`
- Options comparison: `.claude/ai_working/blarify_prompt_integration_options.md`
- Summary: `.claude/ai_working/INVESTIGATION_SUMMARY.md`

**Code Locations**:
- Integration point: `src/amplihack/launcher/core.py:100`
- Pattern to follow: `src/amplihack/launcher/core.py:912-944` (Neo4j startup)
- Utilities to reuse: `src/amplihack/launcher/memory_config.py:400-617`

**Estimated time**: 2-3 hours
**Risk level**: 🟢 LOW
**Confidence**: 95%
**Status**: ✅ Ready to implement

---

*Quick reference created: 2026-01-22*
*For detailed analysis, see INVESTIGATION_SUMMARY.md*
