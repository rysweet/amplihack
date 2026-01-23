# Auto Mode Safety - Architecture Summary

## Quick Reference for Issue #1090

### Problem

UVX deployment silently overwrites uncommitted `~/.amplihack/.claude/` changes, causing data loss.

### Solution Overview

Three-module safety layer that detects conflicts, uses temp directory, and transforms prompts.

---

## Module Architecture

```
GitConflictDetector → SafeCopyStrategy → PromptTransformer
     (detect)            (decide)           (transform)
```

### Module 1: GitConflictDetector

**File:** `src/amplihack/safety/git_conflict_detector.py`
**Purpose:** Detect uncommitted changes in `~/.amplihack/.claude/` directories
**Key Method:** `detect_conflicts(essential_dirs) -> ConflictDetectionResult`
**Dependencies:** subprocess (git commands)
**Lines:** ~150

### Module 2: SafeCopyStrategy

**File:** `src/amplihack/safety/safe_copy_strategy.py`
**Purpose:** Determine copy target (current dir vs temp)
**Key Method:** `determine_target(original, has_conflicts, files) -> CopyStrategy`
**Side Effects:** Creates temp dir, sets env vars, logs warnings
**Lines:** ~100

### Module 3: PromptTransformer

**File:** `src/amplihack/safety/prompt_transformer.py`
**Purpose:** Insert directory change into auto mode prompts
**Key Method:** `transform_prompt(prompt, target_dir, used_temp) -> str`
**Key Feature:** Preserves slash commands, inserts after them
**Lines:** ~80

---

## Integration Points

### CLI Integration (cli.py, lines 438-467)

**Before:**

```python
if is_uvx_deployment():
    original_cwd = os.getcwd()
    temp_claude_dir = os.path.join(original_cwd, ".claude")
    copied = copytree_manifest(amplihack_src, temp_claude_dir, ".claude")
```

**After:**

```python
if is_uvx_deployment():
    original_cwd = os.getcwd()

    # Safety: Detect conflicts
    detector = GitConflictDetector(original_cwd)
    conflict_result = detector.detect_conflicts(ESSENTIAL_DIRS)

    # Safety: Determine target
    strategy = SafeCopyStrategy()
    copy_strategy = strategy.determine_target(
        os.path.join(original_cwd, ".claude"),
        conflict_result.has_conflicts,
        conflict_result.conflicting_files
    )

    temp_claude_dir = str(copy_strategy.target_dir)
    os.environ["AMPLIHACK_ORIGINAL_CWD"] = original_cwd

    # Copy to safe target
    copied = copytree_manifest(amplihack_src, temp_claude_dir, ".claude")
```

### Auto Mode Integration (auto_mode.py)

**Location 1: Constructor (after line 123)**

```python
# Detect temp staging
self.staged_dir = os.environ.get("AMPLIHACK_STAGED_DIR")
self.original_cwd_from_env = os.environ.get("AMPLIHACK_ORIGINAL_CWD")
self.using_temp_staging = self.staged_dir is not None
```

**Location 2: Session start (lines 815, 984)**

```python
# Transform prompt if using temp staging
if self.using_temp_staging and self.original_cwd_from_env:
    transformer = PromptTransformer()
    self.prompt = transformer.transform_prompt(
        self.prompt, self.original_cwd_from_env, True
    )
```

---

## Data Flow

```
User Launch
    ↓
CLI detects UVX → GitConflictDetector checks git status
    ↓
Has conflicts?
    ├─ NO → Copy to .claude/ (original behavior)
    └─ YES → SafeCopyStrategy creates /tmp/amplihack-XXX/
                 ↓
             Set env vars: AMPLIHACK_STAGED_DIR, AMPLIHACK_ORIGINAL_CWD
                 ↓
             Copy to temp directory
                 ↓
             AutoMode.__init__ detects temp staging
                 ↓
             PromptTransformer inserts directory change
                 ↓
             "/cmd Change to /original. Task" → Claude executes in original dir
```

---

## Key Algorithms

### Git Conflict Detection

```python
1. Run: git rev-parse --git-dir (check if git repo)
2. Run: git status --porcelain (get uncommitted files)
3. Parse output: "XY filename" → extract files with M/A/D/R status
4. Filter: Keep only files under .claude/{essential_dir}/
5. Return: conflict list
```

### Slash Command Extraction

```python
Pattern: ^((?:/[\w:-]+(?:\s+(?=/)|(?=\s)))*)
         └─ Match slash commands at start
         └─ Stop at space + non-slash character

Examples:
  "/amplihack:ultrathink Fix bug"
  → slash_commands = "/amplihack:ultrathink"
  → remaining = "Fix bug"

  "/analyze /improve Code review"
  → slash_commands = "/analyze /improve"
  → remaining = "Code review"
```

### Prompt Transformation

```python
if used_temp:
    slash_cmds, rest = extract_slash_commands(prompt)
    dir_change = f"Change your working directory to {target}. "

    if slash_cmds:
        return f"{slash_cmds} {dir_change}{rest}"
    else:
        return f"{dir_change}{rest}"
```

---

## Test Coverage

### Unit Tests (650 lines)

- `test_git_conflict_detector.py` - Git status parsing, conflict filtering
- `test_safe_copy_strategy.py` - Temp dir creation, env vars, logging
- `test_prompt_transformer.py` - Slash command regex, transformation

### Integration Tests (200 lines)

- `test_automode_safety_integration.py` - End-to-end CLI flow

### Manual Test Scenarios

1. Clean git repo (no conflicts)
2. Uncommitted .claude/ changes (conflict protection)
3. Non-git directory (transparent)
4. Various slash command formats

---

## Risk Mitigation

| Risk                                   | Likelihood | Impact | Mitigation                                  |
| -------------------------------------- | ---------- | ------ | ------------------------------------------- |
| False negatives (miss conflicts)       | Low-Medium | HIGH   | Conservative detection, comprehensive tests |
| Prompt transformation breaks           | Medium     | Medium | Robust regex, defensive fallbacks           |
| Performance overhead                   | Low        | Low    | < 500ms, acceptable for launch              |
| Race conditions (commit during launch) | Very Low   | Low    | Accept as tolerable risk                    |

---

## Success Metrics

**Functional:**

- ✓ Zero data loss in manual testing (5 scenarios)
- ✓ All slash commands work with transformation
- ✓ Transparent operation for non-git users

**Technical:**

- ✓ All unit tests pass (100% coverage of new code)
- ✓ Integration tests pass (end-to-end flow)
- ✓ Philosophy compliant (simple, modular, zero-BS)

**Performance:**

- ✓ Launch time increase < 500ms
- ✓ No impact on auto mode execution time

---

## Implementation Phases

### Phase 1: Core Modules (2-3 hours)

- [ ] GitConflictDetector
- [ ] SafeCopyStrategy
- [ ] PromptTransformer
- [ ] safety/**init**.py

### Phase 2: Integration (1 hour)

- [ ] cli.py modifications
- [ ] auto_mode.py modifications

### Phase 3: Testing (2-3 hours)

- [ ] Unit tests (3 files)
- [ ] Integration tests (1 file)
- [ ] Manual testing (5 scenarios)

### Phase 4: Documentation (30 min)

- [ ] Docstrings
- [ ] Update CLAUDE.md

**Total Estimate: 6-8 hours**

---

## Quick Start for Builder

1. **Read:** Full spec at `Specs/automode-safety-architecture.md`
2. **Create:** Safety module directory structure
3. **Implement:** Modules in order (detector → strategy → transformer)
4. **Integrate:** CLI and auto mode modifications
5. **Test:** Unit tests, then integration, then manual
6. **Verify:** Run against all test scenarios

---

## Philosophy Alignment

**Ruthless Simplicity:**

- 3 modules, ~330 lines total
- Standard library only (subprocess, tempfile, re)
- Simple subprocess git integration

**Modular Design:**

- Each module < 200 lines
- Clear contracts with typed I/O
- Independently testable

**Zero-BS:**

- No stubs in specification
- Complete algorithms provided
- All edge cases addressed

**Regeneratable:**

- Full specification provided
- Can be rebuilt from docs alone
- No hidden dependencies

---

## Files to Create

```
src/amplihack/safety/
├── __init__.py                     (~20 lines)
├── git_conflict_detector.py        (~150 lines)
├── safe_copy_strategy.py           (~100 lines)
└── prompt_transformer.py           (~80 lines)

tests/safety/
├── test_git_conflict_detector.py   (~200 lines)
├── test_safe_copy_strategy.py      (~150 lines)
└── test_prompt_transformer.py      (~150 lines)

tests/integration/
└── test_automode_safety_integration.py (~200 lines)
```

## Files to Modify

```
src/amplihack/cli.py                (~15 lines added at L438-467)
src/amplihack/launcher/auto_mode.py (~20 lines added at 3 locations)
```

**Total:** ~1,085 lines new, ~35 lines modified

---

## Key Design Decisions

### Why temp directory instead of git stash?

- Simpler (no git operations beyond detection)
- Safer (doesn't modify git state)
- More transparent (user's working tree unchanged)

### Why subprocess git instead of gitpython?

- Zero new dependencies
- Simple status check only
- Aligns with ruthless simplicity

### Why transform prompt instead of cd command?

- Works with slash commands
- Explicit in prompt (visible to Claude)
- No side effects on shell state

### Why detect in cli.py, not copytree_manifest?

- Separation of concerns
- copytree_manifest is low-level utility
- Safety is deployment concern (CLI level)

---

## References

- Full Specification: `Specs/automode-safety-architecture.md`
- Issue: #1090
- Prompt Writer: Completed requirements analysis
- Philosophy: `~/.amplihack/.claude/context/PHILOSOPHY.md`
- Patterns: `~/.amplihack/.claude/context/PATTERNS.md`
