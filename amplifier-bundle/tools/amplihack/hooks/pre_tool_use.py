#!/usr/bin/env python3
"""
Claude Code hook for pre tool use events.
Prevents dangerous operations like git commit --no-verify
and deletion of the current working directory.
"""

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor

CWD_DELETION_ERROR_MESSAGE = """
🚫 OPERATION BLOCKED - Working Directory Deletion Prevented

You attempted to delete a directory that contains your current working directory:
  Target: {target}
  CWD:    {cwd}

Deleting the CWD would break the current session. If you need to clean up
this directory, first change to a different working directory.

🔒 This protection cannot be disabled programmatically.
""".strip()

CWD_RENAME_ERROR_MESSAGE = """
🚫 OPERATION BLOCKED - Working Directory Rename Prevented

You attempted to move/rename a directory that contains your current working directory:
  Source: {source}
  CWD:    {cwd}

Moving or renaming the CWD would break the current session. To rename this directory:
  1. First change to a different working directory (e.g., cd ..)
  2. Then perform the rename operation
  3. Change back into the renamed directory if needed

🔒 This protection cannot be disabled programmatically.
""".strip()

# Pattern to detect recursive rm or rmdir commands.
# Catches: rm -rf, rm -r, rm -fr, rm -Rf, rm -r -f, rm --recursive, /bin/rm -rf
_RM_RECURSIVE_RE = re.compile(
    r"\brm\s+"
    r"(?:"
    r"-[a-zA-Z]*[rR][a-zA-Z]*"  # combined flags: -rf, -fr, -Rf, etc.
    r"|(?:-[a-zA-Z]+\s+)*-[rR]"  # separated flags: -f -r, -v -r, etc.
    r"|--recursive"  # long form
    r")",
)
_RMDIR_RE = re.compile(r"\brmdir(?:\s|$)")

# Pattern to detect mv commands (move/rename).
# Catches: mv, /bin/mv, /usr/bin/mv, optionally prefixed with env assignments,
# sudo (with optional flags), or command. Examples:
#   mv src dst
#   /bin/mv src dst
#   VAR=1 mv src dst
#   sudo mv src dst
#   sudo -u root /usr/bin/mv src dst
_MV_RE = re.compile(
    r"(?:^|[;&|])\s*"  # start of command or after separator
    r"(?:\w+=\S+\s+)*"  # optional env assignments
    r"(?:sudo\s+)?"  # optional sudo
    r"(?:-\w+(?:\s+\S+)?\s+)*"  # optional sudo flags (e.g., -u root)
    r"(?:command\s+)?"  # optional 'command' builtin
    r"(?:/(?:usr/)?bin/)?mv\s+"  # mv or /bin/mv or /usr/bin/mv
)

MAIN_BRANCH_ERROR_MESSAGE = """
⛔ Direct commits to '{branch}' branch are not allowed.

Please use the feature branch workflow:
  1. Create a feature branch: git checkout -b feature/your-feature-name
  2. Make your commits on the feature branch
  3. Create a Pull Request to merge into {branch}

This protection cannot be bypassed with --no-verify.
""".strip()


class PreToolUseHook(HookProcessor):
    """Hook processor for pre tool use events."""

    def __init__(self):
        super().__init__("pre_tool_use")
        self.strategy = None

    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process pre tool use event and block dangerous operations.

        Args:
            input_data: Input from Claude Code containing tool use details

        Returns:
            Dict with 'block' key set to True if operation should be blocked
        """
        tool_use = input_data.get("toolUse", {})
        tool_name = tool_use.get("name", "")
        tool_input = tool_use.get("input", {})

        if tool_name != "Bash":
            return {}

        # Detect launcher and select strategy
        self.strategy = self._select_strategy()
        if self.strategy:
            self.log(f"Using strategy: {self.strategy.__class__.__name__}")
            strategy_result = self.strategy.handle_pre_tool_use(input_data)
            if strategy_result:
                self.log("Strategy provided custom pre-tool handling")
                return strategy_result

        command = tool_input.get("command", "")

        # Check for CWD deletion before any other checks
        cwd_block = self._check_cwd_deletion(command)
        if cwd_block:
            return cwd_block

        # Check for CWD rename/move
        cwd_rename_block = self._check_cwd_rename(command)
        if cwd_rename_block:
            return cwd_rename_block

        is_git_commit = "git commit" in command
        is_git_push = "git push" in command
        has_no_verify = "--no-verify" in command
        is_git_command = is_git_commit or is_git_push

        if not is_git_command:
            return {}

        if is_git_commit:
            try:
                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    current_branch = result.stdout.strip()

                    if current_branch in ["main", "master"]:
                        self.log(
                            f"BLOCKED: Commit to {current_branch} branch detected",
                            "ERROR",
                        )

                        return {
                            "block": True,
                            "message": MAIN_BRANCH_ERROR_MESSAGE.format(branch=current_branch),
                        }
                else:
                    self.log(
                        f"Git branch detection failed (exit {result.returncode}), allowing operation",
                        "WARNING",
                    )

            except subprocess.TimeoutExpired:
                self.log(
                    "Git branch detection timed out after 5s, allowing operation",
                    "WARNING",
                )
            except FileNotFoundError:
                self.log(
                    "Git not found in PATH, allowing operation",
                    "WARNING",
                )
            except Exception as e:
                self.log(
                    f"Git branch detection failed: {e}, allowing operation",
                    "WARNING",
                )

        if has_no_verify and is_git_command:
            self.log("BLOCKED: Dangerous operation detected (--no-verify flag)", "ERROR")

            return {
                "block": True,
                "message": """
🚫 OPERATION BLOCKED

You attempted to use --no-verify which bypasses critical quality checks:
- Code formatting (ruff, prettier)
- Type checking (pyright)
- Secret detection
- Trailing whitespace fixes

This defeats the purpose of our quality gates.

✅ Instead, fix the underlying issues:
1. Run: pre-commit run --all-files
2. Fix the violations
3. Commit without --no-verify

For true emergencies, ask a human to override this protection.

🔒 This protection cannot be disabled programmatically.
""".strip(),
            }

        # Allow all other operations
        return {}

    def _check_cwd_deletion(self, command: str) -> dict[str, Any]:
        """Check if a command would delete the current working directory.

        Detects rm -r/-rf/-fr and rmdir commands targeting the CWD or a parent.
        Returns a block dict if dangerous, empty dict if safe.
        """
        # Quick check: does the command contain a recursive rm or rmdir?
        has_rm_recursive = _RM_RECURSIVE_RE.search(command)
        has_rmdir = _RMDIR_RE.search(command)

        if not has_rm_recursive and not has_rmdir:
            return {}

        try:
            cwd = Path(os.getcwd()).resolve()
        except OSError:
            self.log("CWD inaccessible, cannot check deletion safety", "WARNING")
            return {}

        # Extract path arguments from rm/rmdir commands in the full command.
        # Split on command separators (;, &&, ||) but NOT single pipe |
        segments = re.split(r";|&&|\|\|", command)

        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue

            # Check if this segment contains a dangerous rm or rmdir
            if _RM_RECURSIVE_RE.search(segment) or _RMDIR_RE.search(segment):
                # Extract the path arguments (everything after flags)
                paths = self._extract_rm_paths(segment)
                for p in paths:
                    try:
                        target = Path(p).resolve()
                    except (OSError, ValueError):
                        continue

                    # Block if CWD is equal to or a child of the target
                    try:
                        cwd.relative_to(target)
                        self.log(
                            f"BLOCKED: Directory deletion would destroy CWD. "
                            f"Target={target}, CWD={cwd}",
                            "ERROR",
                        )
                        return {
                            "block": True,
                            "message": CWD_DELETION_ERROR_MESSAGE.format(target=target, cwd=cwd),
                        }
                    except ValueError:
                        # CWD is not under target - safe
                        continue

        return {}

    def _check_cwd_rename(self, command: str) -> dict[str, Any]:
        """Check if a command would rename/move the current working directory.

        Detects mv commands where the source is the CWD or a parent of CWD.
        Returns a block dict if dangerous, empty dict if safe.
        """
        # Quick check: does the command contain an mv command?
        if not _MV_RE.search(command):
            return {}

        try:
            cwd = Path(os.getcwd()).resolve()
        except OSError:
            self.log("CWD inaccessible, cannot check rename safety", "WARNING")
            return {}

        # Extract path arguments from mv commands in the full command.
        # Split on command separators (;, &&, ||) but NOT single pipe |
        segments = re.split(r";|&&|\|\|", command)

        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue

            # Check if this segment contains an mv command
            if _MV_RE.search(segment):
                # Extract all source paths (mv supports multiple sources)
                source_paths = self._extract_mv_source_paths(segment)
                if not source_paths:
                    continue

                for source_path in source_paths:
                    # Check for glob characters - if present, be conservative
                    if any(c in source_path for c in "*?["):
                        # Extract the non-glob prefix (e.g., /tmp/par* -> /tmp/par)
                        prefix = source_path.split("*")[0].split("?")[0].split("[")[0]
                        if prefix:
                            try:
                                # Get the directory containing the glob and the basename prefix
                                prefix_path = Path(prefix)
                                glob_dir = prefix_path.parent.resolve()
                                basename_prefix = prefix_path.name  # e.g., "par" from "/tmp/par"

                                # Check if CWD's path contains a component that:
                                # 1. Is in the same directory as the glob
                                # 2. Starts with the basename prefix
                                for parent in [cwd] + list(cwd.parents):
                                    if parent.parent == glob_dir:
                                        # This CWD component is in the glob directory
                                        if parent.name.startswith(basename_prefix):
                                            # The glob could match this path component
                                            self.log(
                                                f"BLOCKED: mv with glob pattern might affect CWD. "
                                                f"Pattern={source_path}, CWD={cwd}",
                                                "ERROR",
                                            )
                                            return {
                                                "block": True,
                                                "message": CWD_RENAME_ERROR_MESSAGE.format(
                                                    source=source_path, cwd=cwd
                                                ),
                                            }
                            except (OSError, ValueError):
                                pass
                        continue

                    try:
                        source = Path(source_path).resolve()
                    except (OSError, ValueError):
                        continue

                    # Block if CWD is equal to or a child of the source
                    try:
                        cwd.relative_to(source)
                        self.log(
                            f"BLOCKED: Directory rename would invalidate CWD. "
                            f"Source={source}, CWD={cwd}",
                            "ERROR",
                        )
                        return {
                            "block": True,
                            "message": CWD_RENAME_ERROR_MESSAGE.format(source=source, cwd=cwd),
                        }
                    except ValueError:
                        # CWD is not under source - safe for this source
                        continue

        return {}

    @staticmethod
    def _extract_rm_paths(segment: str) -> list[str]:
        """Extract path arguments from an rm or rmdir command segment.

        Uses shlex.split() to handle quoted paths properly.
        Skips flags (tokens starting with -) and the command name itself.
        """
        try:
            tokens = shlex.split(segment)
        except ValueError:
            # Malformed shell syntax - fall back to simple split
            tokens = segment.split()

        paths: list[str] = []
        skip_command = True

        for token in tokens:
            # Skip tokens before the rm/rmdir command name
            if skip_command:
                if token in ("rm", "rmdir") or token.endswith("/rm") or token.endswith("/rmdir"):
                    skip_command = False
                continue

            # Skip flags
            if token.startswith("-"):
                continue

            # Everything else is a path argument
            paths.append(token)

        return paths

    @staticmethod
    def _extract_mv_source_paths(segment: str) -> list[str]:
        """Extract all source paths from an mv command segment.

        Uses shlex.split() to handle quoted paths properly.
        Supports both standard and -t/--target-directory forms:
        - mv src1 src2 dest/
        - mv -t dest/ src1 src2
        """
        try:
            tokens = shlex.split(segment)
        except ValueError:
            # Malformed shell syntax - skip
            return []

        # Find the mv command position (skip env vars, sudo, command prefix)
        mv_index = None
        for i, token in enumerate(tokens):
            if token == "mv" or token.endswith("/mv"):
                mv_index = i
                break

        if mv_index is None:
            return []

        args = tokens[mv_index + 1 :]
        non_flag_args: list[str] = []
        target_dir_mode = False
        i = 0

        while i < len(args):
            arg = args[i]
            # End of options marker
            if arg == "--":
                non_flag_args.extend(args[i + 1 :])
                break
            # Option handling
            if arg.startswith("-") and arg != "-":
                # Handle -t/--target-directory (takes next arg as target dir)
                if arg in ("-t", "--target-directory"):
                    target_dir_mode = True
                    # Skip the directory argument
                    if i + 1 < len(args):
                        i += 2
                        continue
                    return []  # Malformed
                # Handle --target-directory=DIR
                if arg.startswith("--target-directory="):
                    target_dir_mode = True
                    i += 1
                    continue
                # Other flags (skip)
                i += 1
                continue
            # Non-option argument
            non_flag_args.append(arg)
            i += 1

        if not non_flag_args:
            return []

        # If target dir specified via -t, all remaining args are sources
        if target_dir_mode:
            return non_flag_args

        # Standard form: mv src1 src2 ... dest - all but last are sources
        if len(non_flag_args) >= 2:
            return non_flag_args[:-1]

        # Single arg - treat conservatively as potential source
        return non_flag_args

    def _select_strategy(self):
        """Detect launcher and select appropriate strategy."""
        try:
            sys.path.insert(0, str(self.project_root / "src" / "amplihack"))
            from amplihack.context.adaptive.detector import LauncherDetector
            from amplihack.context.adaptive.strategies import ClaudeStrategy, CopilotStrategy

            detector = LauncherDetector(self.project_root)
            launcher_type = detector.detect()

            if launcher_type == "copilot":
                return CopilotStrategy(self.project_root, self.log)
            return ClaudeStrategy(self.project_root, self.log)

        except ImportError as e:
            self.log(f"Adaptive strategy not available: {e}", "DEBUG")
            return None


def main():
    """Entry point for the pre tool use hook."""
    hook = PreToolUseHook()
    hook.run()


if __name__ == "__main__":
    main()
