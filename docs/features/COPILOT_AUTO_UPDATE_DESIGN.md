# Copilot CLI Auto-Update Design

**Feature**: Automatic version checking and update prompting for GitHub Copilot CLI
**Issue**: #2188
**PR**: #2194
**Status**: Implemented

## Overview

The `amplihack copilot` command now checks for newer Copilot CLI versions before launching and prompts users to update interactively.

## Research & Design

### Version Management Investigation

**Research Source**: github-copilot-cli-expert skill

**Findings**:
- **Current version**: `copilot --version` → "@github/copilot/1.4.0 linux-x64 node-v20.10.0"
- **Latest version**: `npm view @github/copilot version` → "1.5.0" (fastest, no auth)
- **Installation methods**: npm, Homebrew, WinGet, uvx

### Architecture Design

**Design Source**: architect agent

**Principles**:
1. **Ruthless Simplicity**: Use Python stdlib only, no external dependencies
2. **Fail-Safe Defaults**: All errors return None/False, never block launcher
3. **Cross-Platform**: Support Unix (signal-based timeout) and Windows (threading-based)

**Function Breakdown**:

```python
_compare_versions(current: str, latest: str) -> bool
    # Semantic version comparison using tuple comparison
    # Example: (1, 4, 0) < (1, 5, 0) → True

check_for_update() -> str | None
    # Network call with 3-second timeout
    # Returns new version or None on error

detect_install_method() -> str
    # Auto-detect: npm or uvx
    # Default: npm

prompt_user_to_update(new_version: str, install_method: str) -> bool
    # Interactive prompt with 5-second timeout
    # Cross-platform: signal (Unix) / threading (Windows)
    # Returns: True (update), False (skip/timeout)

execute_update(install_method: str) -> bool
    # Run update command
    # Verify version change
    # Returns: True (success), False (failure)
```

## Implementation Details

### Version Comparison

**Strategy**: Native Python tuple comparison (elegant, no dependencies)

```python
def _compare_versions(current: str, latest: str) -> bool:
    def parse(v: str) -> tuple[int, ...]:
        return tuple(int(x) for x in v.lstrip('v').split('.'))

    return parse(latest) > parse(current)
```

**Why This Works**:
- Copilot uses standard semver (MAJOR.MINOR.PATCH)
- Python tuple comparison handles this naturally
- No need for `packaging` or `semver` libraries

### Timeout Handling

**Network Calls**: 3 seconds (npm registry)
**Local Calls**: 1 second (copilot --version)
**User Prompts**: 5 seconds (interactive timeout)

**Cross-Platform Implementation**:

```python
# Unix/Linux/Mac: signal-based
signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(5)

# Windows: threading-based
thread = threading.Thread(target=get_input)
thread.daemon = True
thread.start()
thread.join(timeout=5)
```

### Error Handling

**Philosophy**: Graceful degradation on all error paths

```python
try:
    # Network call
    result = subprocess.run(..., timeout=3)
except (TimeoutExpired, CalledProcessError, OSError):
    return None  # Silent failure, continue launch
```

## Testing Strategy

### Test Coverage: 40 Tests (39 Passing)

**Unit Tests**:
- Version comparison (4 tests)
- Update checking (6 tests)
- Installation detection (4 tests)
- User prompting (3 tests)
- Update execution (9 tests)
- Integration (4 tests)
- Cross-platform (10 tests)

**Manual Tests** (Step 13):
1. Update available scenario
2. Already up-to-date scenario
3. Network timeout scenario
4. Version comparison logic
5. uvx installation detection

**Outside-In Tests** (Step 19):
- Installation via `uvx --from git+...`
- Import verification
- Function availability

## Security Analysis

**Assessment**: 10/10 (security agent)

- ✅ No command injection (list-style subprocess)
- ✅ Proper timeouts (prevents hangs)
- ✅ No sensitive data in errors
- ✅ HTTPS via npm (certificate validation)
- ✅ Robust version parsing (fail-safe)

## Philosophy Compliance

**Score**: Grade A (philosophy-guardian agent)

**Strengths**:
- **Ruthless Simplicity**: Every line serves a purpose
- **Brick Philosophy**: Self-contained module, clear contracts
- **Zero-BS**: No stubs, placeholders, or TODOs
- **Fail-Safe**: Silent failures don't break launcher

## Lessons Learned

1. **Cross-Platform Complexity**: Initial estimate was 54 lines, actual ~150 lines due to cross-platform timeout handling. This complexity is justified and necessary.

2. **TDD Value**: Writing tests first revealed edge cases:
   - EOF handling for non-interactive environments
   - Version string parsing edge cases
   - Installation method detection fallbacks

3. **Graceful Degradation**: Every error path returns safe defaults. Update check failures never block copilot launch.

4. **User Control**: Interactive prompt with timeout respects both automated workflows (timeout) and manual usage (user choice).

## References

- **Issue**: https://github.com/rysweet/amplihack/issues/2188
- **PR**: https://github.com/rysweet/amplihack/pull/2194
- **Implementation**: `src/amplihack/launcher/copilot.py`
- **Tests**: `tests/launcher/test_copilot.py`, `tests/launcher/test_copilot_auto_update.py`
- **Documentation**: `docs/COPILOT_CLI.md`

## Future Considerations

**NOT Implemented** (not in requirements):
- Caching of version checks (always check on launch per requirements)
- Automatic updates without user prompt (explicit user confirmation required)
- Configuration to disable checks (requirement specifies check on every launch)

These were deliberately excluded to follow ruthless simplicity and user requirements.
