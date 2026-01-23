# Architecture Specification: Auto Mode Safety (Issue #1090)

## Problem Statement

When amplihack is launched via `uvx --from git+...` in a directory with uncommitted git changes, the UVX initialization copies `~/.amplihack/.claude/` directory contents and silently overwrites local uncommitted changes, causing irreversible data loss.

## Solution Overview

Implement a safety layer that:

1. Detects conflicts between files to be copied and uncommitted git changes
2. Uses fallback temporary directory when conflicts exist
3. Transforms auto mode prompts to include directory change instruction
4. Maintains transparency (no behavior change except protection)

## Architecture Design

### Philosophy Alignment

- **Ruthless Simplicity**: Three focused modules with single responsibilities
- **Zero-BS Implementation**: No stubs, complete implementations only
- **Modular Design (Bricks)**: Each module is self-contained with clear contracts
- **Regeneratable**: Can be rebuilt from this specification alone

### Module Structure

```
src/amplihack/safety/
├── __init__.py                    # Module exports
├── git_conflict_detector.py       # Brick 1: Detect conflicts
├── safe_copy_strategy.py          # Brick 2: Determine copy target
└── prompt_transformer.py          # Brick 3: Transform prompts
```

---

## Module 1: Git Conflict Detector

### Purpose

Detect if files we're about to copy conflict with uncommitted git changes.

### Contract

**Inputs:**

- `target_dir: str | Path` - Directory where we want to copy
- `essential_dirs: list[str]` - List of subdirectories to check (e.g., ["agents/amplihack", "commands/amplihack"])

**Outputs:**

- `ConflictDetectionResult` dataclass:
  - `has_conflicts: bool` - True if conflicts exist
  - `conflicting_files: list[str]` - List of conflicting file paths
  - `is_git_repo: bool` - True if target_dir is in a git repo

**Side Effects:**
None (read-only)

### Implementation Specification

```python
from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import List, Union

@dataclass
class ConflictDetectionResult:
    """Result of git conflict detection."""
    has_conflicts: bool
    conflicting_files: List[str]
    is_git_repo: bool

class GitConflictDetector:
    """Detect git conflicts for safe file copying."""

    def __init__(self, target_dir: Union[str, Path]):
        """Initialize detector.

        Args:
            target_dir: Directory to check for conflicts
        """
        self.target_dir = Path(target_dir).resolve()

    def detect_conflicts(self, essential_dirs: List[str]) -> ConflictDetectionResult:
        """Detect conflicts between essential_dirs and uncommitted changes.

        Algorithm:
        1. Check if target_dir is in a git repository
        2. If not in git repo, return no conflicts (safe to copy)
        3. Run `git status --porcelain` in target_dir
        4. Parse output for modified/added/deleted files
        5. Check if any files are under .claude/{essential_dir}/ paths
        6. Return result with conflict status and file list

        Args:
            essential_dirs: List of subdirectories under .claude/ to check
                           (e.g., ["agents/amplihack", "tools/amplihack"])

        Returns:
            ConflictDetectionResult with detection results
        """
        # Step 1: Check if in git repo
        if not self._is_git_repo():
            return ConflictDetectionResult(
                has_conflicts=False,
                conflicting_files=[],
                is_git_repo=False
            )

        # Step 2: Get uncommitted files
        uncommitted_files = self._get_uncommitted_files()

        # Step 3: Filter for conflicts with essential_dirs
        conflicting_files = self._filter_conflicts(uncommitted_files, essential_dirs)

        return ConflictDetectionResult(
            has_conflicts=len(conflicting_files) > 0,
            conflicting_files=conflicting_files,
            is_git_repo=True
        )

    def _is_git_repo(self) -> bool:
        """Check if target_dir is in a git repository.

        Returns:
            True if in git repo, False otherwise
        """
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.target_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _get_uncommitted_files(self) -> List[str]:
        """Get list of uncommitted files using git status.

        Returns:
            List of file paths with uncommitted changes
        """
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.target_dir,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return []

            # Parse git status output
            # Format: XY filename
            # X = index status, Y = worktree status
            # We care about: M (modified), A (added), D (deleted), R (renamed)
            uncommitted = []
            for line in result.stdout.splitlines():
                if len(line) < 4:
                    continue

                # Status codes at positions 0-1, space, then filename
                status = line[:2]
                filename = line[3:]

                # Check if file has uncommitted changes (index or worktree)
                if any(c in status for c in ['M', 'A', 'D', 'R']):
                    uncommitted.append(filename)

            return uncommitted

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

    def _filter_conflicts(
        self,
        uncommitted_files: List[str],
        essential_dirs: List[str]
    ) -> List[str]:
        """Filter uncommitted files for conflicts with essential_dirs.

        Args:
            uncommitted_files: List of all uncommitted file paths
            essential_dirs: List of essential directory paths under .claude/

        Returns:
            List of files that would be overwritten
        """
        conflicts = []

        for file_path in uncommitted_files:
            # Check if file is under .claude/{essential_dir}/
            if file_path.startswith('.claude/'):
                # Remove .claude/ prefix
                relative_path = file_path[8:]  # len('.claude/') = 8

                # Check if starts with any essential_dir
                for essential_dir in essential_dirs:
                    if relative_path.startswith(essential_dir + '/') or \
                       relative_path == essential_dir:
                        conflicts.append(file_path)
                        break

        return conflicts
```

### Test Requirements

1. **Test Case: Not in git repo**
   - Input: Non-git directory, essential_dirs list
   - Expected: has_conflicts=False, is_git_repo=False

2. **Test Case: Git repo with no uncommitted changes**
   - Input: Clean git repo, essential_dirs list
   - Expected: has_conflicts=False, conflicting_files=[]

3. **Test Case: Git repo with conflicts**
   - Input: Git repo with modified .claude/tools/amplihack/hooks/stop.py
   - Expected: has_conflicts=True, conflicting_files contains the file

4. **Test Case: Git repo with uncommitted changes outside .claude/**
   - Input: Git repo with modified src/main.py
   - Expected: has_conflicts=False (changes not in essential_dirs)

5. **Test Case: Git repo with changes in non-essential .claude/ subdirs**
   - Input: Git repo with modified .claude/scenarios/tool.py
   - Expected: has_conflicts=False (scenarios not in ESSENTIAL_DIRS)

---

## Module 2: Safe Copy Strategy

### Purpose

Determine where to copy files (current directory vs temporary directory) based on conflict detection.

### Contract

**Inputs:**

- `original_target: str | Path` - Original intended copy target
- `has_conflicts: bool` - Whether conflicts were detected
- `conflicting_files: list[str]` - List of conflicting files (for logging)

**Outputs:**

- `CopyStrategy` dataclass:
  - `target_dir: Path` - Where to actually copy (original or temp)
  - `used_temp: bool` - True if temp directory was used
  - `temp_dir: Path | None` - Temp directory path if created

**Side Effects:**

- Creates temporary directory if needed
- Sets environment variable `AMPLIHACK_STAGED_DIR` with target_dir

### Implementation Specification

```python
from dataclasses import dataclass
from pathlib import Path
import os
import tempfile
from typing import List, Optional, Union

@dataclass
class CopyStrategy:
    """Strategy for where to copy files."""
    target_dir: Path
    used_temp: bool
    temp_dir: Optional[Path]

class SafeCopyStrategy:
    """Determine safe copy target based on conflict detection."""

    def determine_target(
        self,
        original_target: Union[str, Path],
        has_conflicts: bool,
        conflicting_files: List[str]
    ) -> CopyStrategy:
        """Determine where to copy files based on conflict status.

        Algorithm:
        1. If no conflicts, use original_target
        2. If conflicts exist:
           a. Create temp directory with prefix "amplihack-"
           b. Log warning about conflicts and temp usage
           c. Set AMPLIHACK_STAGED_DIR env var
           d. Return temp directory as target

        Args:
            original_target: Original intended copy target
            has_conflicts: Whether conflicts were detected
            conflicting_files: List of conflicting files (for logging)

        Returns:
            CopyStrategy with target directory and metadata
        """
        original_path = Path(original_target).resolve()

        if not has_conflicts:
            # No conflicts - use original target
            return CopyStrategy(
                target_dir=original_path,
                used_temp=False,
                temp_dir=None
            )

        # Conflicts detected - use temp directory
        temp_dir = self._create_temp_directory()

        # Log warning
        self._log_conflict_warning(conflicting_files, temp_dir)

        # Set environment variable for auto mode
        os.environ["AMPLIHACK_STAGED_DIR"] = str(temp_dir)
        os.environ["AMPLIHACK_ORIGINAL_CWD"] = str(original_path)

        return CopyStrategy(
            target_dir=temp_dir,
            used_temp=True,
            temp_dir=temp_dir
        )

    def _create_temp_directory(self) -> Path:
        """Create temporary directory for staging.

        Returns:
            Path to created temp directory
        """
        temp_dir = Path(tempfile.mkdtemp(prefix="amplihack-"))

        # Create .claude subdirectory (since we'll copy into it)
        claude_dir = temp_dir / ".claude"
        claude_dir.mkdir(parents=True, exist_ok=True)

        return claude_dir

    def _log_conflict_warning(
        self,
        conflicting_files: List[str],
        temp_dir: Path
    ) -> None:
        """Log warning about conflicts and temp directory usage.

        Args:
            conflicting_files: List of conflicting files
            temp_dir: Temporary directory being used
        """
        print("\n⚠️  SAFETY WARNING: Uncommitted changes detected in .claude/")
        print("=" * 70)
        print("\nThe following files have uncommitted changes that would be overwritten:")
        for file_path in conflicting_files[:10]:  # Limit to 10 files
            print(f"  • {file_path}")
        if len(conflicting_files) > 10:
            print(f"  ... and {len(conflicting_files) - 10} more")

        print(f"\n📁 To protect your changes, .claude/ will be staged in:")
        print(f"   {temp_dir}")
        print("\n💡 Auto mode will automatically work in your original directory.")
        print("=" * 70)
        print()
```

### Test Requirements

1. **Test Case: No conflicts**
   - Input: original_target="/path/to/dir", has_conflicts=False
   - Expected: target_dir=original_target, used_temp=False

2. **Test Case: With conflicts**
   - Input: original_target="/path/to/dir", has_conflicts=True, conflicting_files=[...]
   - Expected: target_dir starts with /tmp/amplihack-, used_temp=True
   - Verify: AMPLIHACK_STAGED_DIR env var is set
   - Verify: Temp directory exists and has .claude subdirectory

3. **Test Case: Warning output**
   - Input: conflicts with specific files
   - Expected: Warning printed to stdout with file list

---

## Module 3: Prompt Transformer

### Purpose

Transform auto mode prompts to include directory change instruction when temp directory is used.

### Contract

**Inputs:**

- `original_prompt: str` - Original user prompt
- `target_directory: str | Path` - Directory to change to
- `used_temp: bool` - Whether temp directory was used

**Outputs:**

- `str` - Transformed prompt with directory change instruction

**Side Effects:**
None (pure function)

### Implementation Specification

```python
from pathlib import Path
from typing import Union
import re

class PromptTransformer:
    """Transform auto mode prompts to include directory change."""

    def transform_prompt(
        self,
        original_prompt: str,
        target_directory: Union[str, Path],
        used_temp: bool
    ) -> str:
        """Transform prompt to include directory change instruction.

        Algorithm:
        1. If not used_temp, return original prompt unchanged
        2. Find the position after slash commands (if any)
        3. Insert directory change instruction at that position
        4. Return transformed prompt

        Slash commands pattern: /command-name args
        We need to preserve slash commands but insert directory change after them.

        Example transformation:
        Input:  "/amplihack:ultrathink Fix the bug"
        Output: "/amplihack:ultrathink Change your working directory to /original/dir. Fix the bug"

        Args:
            original_prompt: Original user prompt
            target_directory: Directory to change to
            used_temp: Whether temp directory was used (safety check)

        Returns:
            Transformed prompt with directory change instruction
        """
        if not used_temp:
            return original_prompt

        target_path = Path(target_directory).resolve()

        # Find slash commands at the start
        slash_commands, remaining_prompt = self._extract_slash_commands(original_prompt)

        # Build directory change instruction
        dir_instruction = f"Change your working directory to {target_path}. "

        # Combine: slash_commands + dir_instruction + remaining_prompt
        if slash_commands:
            transformed = f"{slash_commands} {dir_instruction}{remaining_prompt}"
        else:
            transformed = f"{dir_instruction}{remaining_prompt}"

        return transformed

    def _extract_slash_commands(self, prompt: str) -> tuple[str, str]:
        """Extract slash commands from the start of the prompt.

        Slash commands:
        - Start with /
        - Continue until space followed by non-slash character
        - Can be chained: /cmd1 /cmd2 args

        Args:
            prompt: Original prompt

        Returns:
            Tuple of (slash_commands, remaining_prompt)
        """
        # Pattern: One or more slash commands at the start
        # Slash command: /word optionally followed by :word or more words
        pattern = r'^((?:/[\w:-]+(?:\s+(?=/)|(?=\s)))*)'

        match = re.match(pattern, prompt.strip())

        if match:
            slash_commands = match.group(1).strip()
            remaining = prompt[match.end():].strip()
            return slash_commands, remaining

        return "", prompt.strip()
```

### Test Requirements

1. **Test Case: No temp used**
   - Input: original_prompt="Fix the bug", used_temp=False
   - Expected: Returns original_prompt unchanged

2. **Test Case: Simple prompt with no slash commands**
   - Input: original_prompt="Fix the bug", target_directory="/home/user/project", used_temp=True
   - Expected: "Change your working directory to /home/user/project. Fix the bug"

3. **Test Case: Single slash command**
   - Input: original_prompt="/amplihack:ultrathink Fix the bug", target_directory="/home/user/project", used_temp=True
   - Expected: "/amplihack:ultrathink Change your working directory to /home/user/project. Fix the bug"

4. **Test Case: Multiple slash commands**
   - Input: original_prompt="/analyze /improve Fix stuff", target_directory="/path", used_temp=True
   - Expected: "/analyze /improve Change your working directory to /path. Fix stuff"

5. **Test Case: Slash command with colons**
   - Input: original_prompt="/amplihack:ddd:1-plan Feature X", target_directory="/path", used_temp=True
   - Expected: "/amplihack:ddd:1-plan Change your working directory to /path. Feature X"

---

## Module 4: Integration Layer

### Purpose

Integrate safety modules into existing CLI and auto mode code.

### File 1: `cli.py` Modifications

**Location:** Lines 438-467

**Current Code:**

```python
if is_uvx_deployment():
    original_cwd = os.getcwd()
    os.environ["AMPLIHACK_ORIGINAL_CWD"] = original_cwd

    temp_claude_dir = os.path.join(original_cwd, ".claude")

    # Copy .claude contents to current directory
    copied = copytree_manifest(amplihack_src, temp_claude_dir, ".claude")
```

**New Code:**

```python
if is_uvx_deployment():
    original_cwd = os.getcwd()

    # Safety: Check for git conflicts before copying
    from .safety import GitConflictDetector, SafeCopyStrategy
    from . import ESSENTIAL_DIRS

    detector = GitConflictDetector(original_cwd)
    conflict_result = detector.detect_conflicts(ESSENTIAL_DIRS)

    strategy_manager = SafeCopyStrategy()
    copy_strategy = strategy_manager.determine_target(
        original_target=os.path.join(original_cwd, ".claude"),
        has_conflicts=conflict_result.has_conflicts,
        conflicting_files=conflict_result.conflicting_files
    )

    temp_claude_dir = str(copy_strategy.target_dir)

    # Store original_cwd for auto mode (always set, regardless of conflicts)
    os.environ["AMPLIHACK_ORIGINAL_CWD"] = original_cwd

    if os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true":
        print(f"UVX mode: Staging Claude environment in: {temp_claude_dir}")
        print(f"Original working directory: {original_cwd}")
        if copy_strategy.used_temp:
            print(f"Using temp directory due to conflicts")

    # Copy .claude contents to target directory
    copied = copytree_manifest(amplihack_src, temp_claude_dir, ".claude")
```

### File 2: `auto_mode.py` Modifications

**Location:** Constructor and prompt building

**Modification 1: Constructor (after line 123)**

Add detection of staging directory:

```python
# Detect if we're using temp staging directory (safety feature)
self.staged_dir = os.environ.get("AMPLIHACK_STAGED_DIR")
self.original_cwd_from_env = os.environ.get("AMPLIHACK_ORIGINAL_CWD")
self.using_temp_staging = self.staged_dir is not None
```

**Modification 2: Prompt transformation (in \_run_sync_session and \_run_async_session)**

Before executing the first turn (clarify objective), transform the prompt:

```python
# Transform prompt if using temp staging (safety feature)
if self.using_temp_staging and self.original_cwd_from_env:
    from amplihack.safety import PromptTransformer
    transformer = PromptTransformer()
    self.prompt = transformer.transform_prompt(
        original_prompt=self.prompt,
        target_directory=self.original_cwd_from_env,
        used_temp=True
    )
    self.log(f"Transformed prompt for temp staging (target: {self.original_cwd_from_env})")
```

Insert this code at:

- Line 815 in `_run_sync_session()` (after `self.start_time = time.time()`)
- Line 984 in `_run_async_session()` (after `self.start_time = time.time()`)

### File 3: `src/amplihack/safety/__init__.py`

```python
"""Safety module for preventing data loss in auto mode."""

from .git_conflict_detector import GitConflictDetector, ConflictDetectionResult
from .safe_copy_strategy import SafeCopyStrategy, CopyStrategy
from .prompt_transformer import PromptTransformer

__all__ = [
    "GitConflictDetector",
    "ConflictDetectionResult",
    "SafeCopyStrategy",
    "CopyStrategy",
    "PromptTransformer",
]
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ UVX Launch: uvx --from git+... amplihack launch --auto -- -p X │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   cli.py L440   │
                    │ is_uvx_deploy?  │
                    └────────┬─────────┘
                             │ YES
                             ▼
                    ┌─────────────────────────────────────┐
                    │ GitConflictDetector.detect_conflicts│
                    │ Input: cwd, ESSENTIAL_DIRS          │
                    │ Output: ConflictDetectionResult     │
                    └────────┬─────────────────────────────┘
                             │
                             ▼
                    ┌─────────────────────────────────────┐
                    │ SafeCopyStrategy.determine_target   │
                    │ Input: original_target, conflicts   │
                    │ Output: CopyStrategy                │
                    │ Side Effect: Set env vars, log warn │
                    └────────┬─────────────────────────────┘
                             │
                ┌────────────┴─────────────┐
                │                          │
                ▼                          ▼
    ┌───────────────────┐     ┌──────────────────────┐
    │ No Conflicts      │     │ Conflicts Detected   │
    │ target = cwd      │     │ target = /tmp/xxx    │
    │ used_temp = False │     │ used_temp = True     │
    └────────┬──────────┘     └──────────┬───────────┘
             │                           │
             └────────────┬──────────────┘
                          │
                          ▼
                ┌──────────────────────┐
                │ copytree_manifest    │
                │ Copy to target_dir   │
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │ auto_mode.py L815+   │
                │ Check used_temp?     │
                └──────────┬───────────┘
                           │
                ┌──────────┴───────────┐
                │                      │
                ▼                      ▼
    ┌──────────────────┐   ┌─────────────────────────────┐
    │ No temp          │   │ Using temp                  │
    │ Use prompt as-is │   │ PromptTransformer.transform │
    └──────────────────┘   │ Insert dir change           │
                           └─────────────┬───────────────┘
                                         │
                                         ▼
                            ┌──────────────────────────────┐
                            │ Prompt transformed:          │
                            │ /cmd Change directory. Task  │
                            └──────────────────────────────┘
```

---

## Error Handling Strategy

### Git Command Failures

**Scenario:** Git commands timeout or fail (not installed, permission denied)

**Strategy:**

- Assume no git repo (safe default)
- Return `ConflictDetectionResult(has_conflicts=False, is_git_repo=False)`
- Continue with normal copy to current directory

**Rationale:** If we can't detect git, we assume user knows what they're doing

### Temp Directory Creation Failures

**Scenario:** Cannot create temp directory (disk full, permission denied)

**Strategy:**

- Log error message
- Fall back to original target directory
- Warn user about potential conflicts
- Exit with error code 1

**Rationale:** Better to fail explicitly than silently overwrite

### Prompt Transformation Edge Cases

**Scenario:** Malformed slash commands, unexpected prompt formats

**Strategy:**

- Regex fails to match slash commands
- Treat entire prompt as "remaining_prompt"
- Insert directory change at start
- Log warning about unexpected format

**Rationale:** Transformation should be defensive and always produce valid output

---

## Edge Cases

### Edge Case 1: .claude directory doesn't exist yet

**Scenario:** First-time user, no .claude/ directory in current directory

**Behavior:**

- GitConflictDetector checks for .claude/ files in git status
- No .claude/ files exist yet, so no conflicts
- Copy proceeds normally to current directory

**Result:** No change in behavior (transparent)

### Edge Case 2: Nested git repositories

**Scenario:** .claude/ is its own git submodule

**Behavior:**

- GitConflictDetector runs in parent directory
- Git status includes submodule changes
- If submodule has uncommitted changes, conflicts detected
- Uses temp directory (safe)

**Result:** Protects submodule changes

### Edge Case 3: User has .claude/ but not in git

**Scenario:** .claude/ exists but is gitignored or not tracked

**Behavior:**

- GitConflictDetector checks if directory is in git repo
- If .claude/ is untracked, it won't appear in git status --porcelain
- No conflicts detected
- Copy proceeds, overwriting untracked .claude/

**Result:** Acceptable (untracked files are not protected by git)

**Alternative:** Could add check for any existing .claude/ files, but this violates MANDATORY requirement "MUST detect conflicts between files amplihack will copy and uncommitted git changes" - only uncommitted changes need protection.

### Edge Case 4: Symlinks in .claude/

**Scenario:** .claude/tools/hooks is a symlink

**Behavior:**

- Git status shows changes to symlink target
- copytree_manifest follows or doesn't follow symlinks (implementation dependent)
- GitConflictDetector sees symlink path in git status

**Result:** Protected if symlink target has uncommitted changes

### Edge Case 5: Auto mode without --auto flag

**Scenario:** User launches amplihack in interactive mode with conflicts

**Behavior:**

- Conflict detection still runs
- Temp directory still used if conflicts exist
- No prompt transformation (not in auto mode)
- User works in temp directory interactively

**Result:** Still protected, but user may be confused about working directory

**Mitigation:** Log clear message about temp directory usage

---

## Risk Assessment

### Risk 1: False Positives (Detecting conflicts when none exist)

**Likelihood:** Low
**Impact:** Low (Uses temp directory unnecessarily, but functionally correct)
**Mitigation:**

- Comprehensive testing of git status parsing
- Clear logging of what conflicts were detected

### Risk 2: False Negatives (Missing real conflicts)

**Likelihood:** Low-Medium
**Impact:** HIGH (Data loss - the problem we're trying to solve)
**Mitigation:**

- Conservative conflict detection (err on side of caution)
- Comprehensive test coverage
- Manual testing with real git scenarios

### Risk 3: Prompt Transformation Breaking Slash Commands

**Likelihood:** Medium
**Impact:** Medium (Auto mode fails or behaves unexpectedly)
**Mitigation:**

- Robust regex for slash command detection
- Extensive test cases covering all slash command patterns
- Defensive fallback (insert at start if regex fails)

### Risk 4: Performance Degradation

**Likelihood:** Low
**Impact:** Low (Adds ~100-200ms for git operations)
**Mitigation:**

- Git commands have 5-10s timeouts
- Operations are simple (status check only)
- Acceptable for launch-time overhead

### Risk 5: Race Conditions

**Scenario:** User commits changes between detection and copy

**Likelihood:** Very Low
**Impact:** Low (Copy proceeds with stale detection, but git history is safe)
**Mitigation:**

- Accept this as acceptable risk
- Time window is < 1 second typically
- If user commits during launch, their changes are now in git history (protected)

---

## Testing Strategy

### Unit Tests

**Test Suite 1: GitConflictDetector**

- Location: `tests/safety/test_git_conflict_detector.py`
- Coverage: All test cases specified in Module 1
- Mock: subprocess.run for git commands
- Verify: Correct parsing of git status output

**Test Suite 2: SafeCopyStrategy**

- Location: `tests/safety/test_safe_copy_strategy.py`
- Coverage: All test cases specified in Module 2
- Verify: Temp directory creation, env vars set, logging

**Test Suite 3: PromptTransformer**

- Location: `tests/safety/test_prompt_transformer.py`
- Coverage: All test cases specified in Module 3
- Focus: Slash command regex patterns

### Integration Tests

**Test Suite 4: CLI Integration**

- Location: `tests/integration/test_automode_safety_integration.py`
- Scenarios:
  1. UVX launch with clean git repo
  2. UVX launch with uncommitted .claude/ changes
  3. UVX launch with uncommitted non-.claude/ changes
  4. UVX launch in non-git directory
- Verify end-to-end flow

### Manual Testing

**Scenario 1: Real conflict with data loss potential**

```bash
# Setup
cd /tmp/test-project
git init
mkdir -p .claude/tools/amplihack/hooks
echo "# my custom hook" > .claude/tools/amplihack/hooks/stop.py
git add .
git commit -m "Initial"

# Modify without committing
echo "# important change" >> .claude/tools/amplihack/hooks/stop.py

# Launch amplihack
uvx --from git+... amplihack launch --auto -- -p "/amplihack:ultrathink test"

# Verify:
# 1. Warning printed about conflicts
# 2. .claude/ staged in /tmp/amplihack-XXX/
# 3. Auto mode works in /tmp/test-project (original dir)
# 4. Original file still has "# important change"
```

**Scenario 2: No conflicts**

```bash
# Setup
cd /tmp/test-project
git init
git commit --allow-empty -m "Initial"

# Launch amplihack (no uncommitted changes)
uvx --from git+... amplihack launch --auto -- -p "test"

# Verify:
# 1. No warning printed
# 2. .claude/ copied to current directory
# 3. Auto mode works normally
```

---

## Success Criteria

### Functional Requirements

✓ **MUST detect conflicts** between files amplihack will copy and uncommitted git changes
✓ **MUST NOT overwrite** any files with uncommitted changes
✓ **MUST preserve** original working directory as target for auto mode operations
✓ **MUST insert** directory change instruction into auto mode prompt after slash commands
✓ **MUST maintain** explicit manifest of files that will be copied (ESSENTIAL_DIRS)
✓ **MUST work transparently** with no behavior change except protection

### Non-Functional Requirements

✓ **Performance:** Git detection adds < 500ms to launch time
✓ **Reliability:** No false negatives (missing conflicts) in testing
✓ **Clarity:** Clear logging when temp directory is used
✓ **Philosophy:** Follows ruthless simplicity, modular design, zero-BS principles

### Acceptance Test

The solution is successful if:

1. **Baseline Test:** User can launch in clean directory, no changes
2. **Protection Test:** User with uncommitted .claude/ changes is protected from data loss
3. **Transparency Test:** User without git repo sees no difference in behavior
4. **Auto Mode Test:** Auto mode works correctly in original directory even with temp staging
5. **Slash Command Test:** All slash command formats work with prompt transformation

---

## Implementation Checklist

### Phase 1: Core Modules (Builder Agent)

- [ ] Create `src/amplihack/safety/__init__.py`
- [ ] Implement `GitConflictDetector` in `git_conflict_detector.py`
- [ ] Implement `SafeCopyStrategy` in `safe_copy_strategy.py`
- [ ] Implement `PromptTransformer` in `prompt_transformer.py`

### Phase 2: Integration (Builder Agent)

- [ ] Modify `cli.py` lines 438-467
- [ ] Modify `auto_mode.py` constructor
- [ ] Modify `auto_mode.py` \_run_sync_session
- [ ] Modify `auto_mode.py` \_run_async_session

### Phase 3: Testing (Tester Agent)

- [ ] Write unit tests for GitConflictDetector
- [ ] Write unit tests for SafeCopyStrategy
- [ ] Write unit tests for PromptTransformer
- [ ] Write integration tests for CLI flow
- [ ] Perform manual testing scenarios

### Phase 4: Documentation (Builder Agent)

- [ ] Update CLAUDE.md with safety feature documentation
- [ ] Add docstrings to all new modules
- [ ] Create user-facing documentation for temp directory behavior

### Phase 5: Validation (Reviewer Agent)

- [ ] Review for philosophy compliance
- [ ] Check module boundaries
- [ ] Verify no stubs or placeholders
- [ ] Confirm all requirements met

---

## File Modifications Summary

### New Files

1. `src/amplihack/safety/__init__.py` (~20 lines)
2. `src/amplihack/safety/git_conflict_detector.py` (~150 lines)
3. `src/amplihack/safety/safe_copy_strategy.py` (~100 lines)
4. `src/amplihack/safety/prompt_transformer.py` (~80 lines)
5. `tests/safety/test_git_conflict_detector.py` (~200 lines)
6. `tests/safety/test_safe_copy_strategy.py` (~150 lines)
7. `tests/safety/test_prompt_transformer.py` (~150 lines)
8. `tests/integration/test_automode_safety_integration.py` (~200 lines)

**Total: ~1,050 lines of new code**

### Modified Files

1. `src/amplihack/cli.py` (lines 438-467, ~15 lines added)
2. `src/amplihack/launcher/auto_mode.py` (3 locations, ~20 lines added)

**Total: ~35 lines modified**

---

## Dependencies

### No New External Dependencies

All functionality uses Python standard library:

- `subprocess` - Git command execution
- `tempfile` - Temp directory creation
- `pathlib` - Path manipulation
- `re` - Regex for slash commands
- `os` - Environment variables
- `dataclasses` - Result types

### Internal Dependencies

- `amplihack.utils.is_uvx_deployment` - Already exists
- `amplihack.ESSENTIAL_DIRS` - Already exists
- `amplihack.copytree_manifest` - Already exists

---

## Rollout Strategy

### Phase 1: Development Branch

- Implement all modules
- Run unit tests
- Manual testing in development

### Phase 2: Testing Branch

- Merge to testing branch
- Run integration tests
- Manual testing in real scenarios

### Phase 3: Production

- Merge to main
- Monitor for issues in first week
- Collect user feedback

### Rollback Plan

If critical issues found:

1. Revert commits affecting cli.py and auto_mode.py
2. Safety modules remain (no harm)
3. System reverts to original behavior

---

## Future Enhancements (Out of Scope)

1. **Interactive Mode:** Ask user whether to use temp directory
2. **Git Stash Integration:** Auto-stash changes before copying
3. **Conflict Resolution UI:** Show diff and allow user to choose
4. **Per-File Granularity:** Only copy non-conflicting directories
5. **Configuration:** Allow users to disable safety checks

These are explicitly out of scope for initial implementation.

---

## Architect Notes

This architecture follows the project's core principles:

**Ruthless Simplicity:**

- Three focused modules, each < 200 lines
- Simple subprocess-based git integration
- No complex dependency injection or frameworks

**Zero-BS Implementation:**

- No stubs or placeholders in specification
- Complete algorithms provided
- All edge cases addressed

**Modular Design (Bricks):**

- Each module has single responsibility
- Clear contracts with typed inputs/outputs
- Independently testable and regeneratable

**Trust in Emergence:**

- Simple components compose to solve complex problem
- No over-engineering for future scenarios
- Focus on current requirements

This specification is complete and ready for the builder agent to implement directly.
