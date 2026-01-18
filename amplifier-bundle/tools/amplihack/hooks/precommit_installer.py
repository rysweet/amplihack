#!/usr/bin/env python3
"""
Claude Code startup hook for pre-commit installation.

Philosophy:
- Automatically install pre-commit hooks when config exists
- Fail gracefully - never break session start
- Simple and focused - one responsibility
- Respect user preferences via environment variables
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor


class PrecommitInstallerHook(HookProcessor):
    """Hook processor for installing pre-commit hooks at session start.

    This hook automatically installs pre-commit hooks when:
    - A git repository is detected
    - .pre-commit-config.yaml exists
    - pre-commit is available
    - Hooks are not already installed
    - Not disabled via environment variable

    Environment Variables:
        AMPLIHACK_AUTO_PRECOMMIT: Set to "0", "false", "no", or "off" to disable
    """

    def __init__(self):
        super().__init__("precommit_installer")

    def process(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Process session start event and install pre-commit if needed.

        Args:
            input_data: Input from Claude Code

        Returns:
            Empty dict (no context to add)
        """
        try:
            # Check if disabled via environment variable
            if self._is_env_disabled():
                self.log("Pre-commit auto-install disabled via environment variable")
                self.save_metric("precommit_env_disabled", True)
                return {}

            # Check if we're in a git repo
            if not self._is_git_repo():
                self.log("Not a git repository - skipping pre-commit check")
                self.save_metric("precommit_not_git_repo", True)
                return {}

            # Check if pre-commit config exists
            config_file = self.project_root / ".pre-commit-config.yaml"
            if not config_file.exists():
                self.log("No .pre-commit-config.yaml found - skipping")
                self.save_metric("precommit_no_config", True)
                return {}

            self.log("Found pre-commit config, checking installation...")

            # Check if pre-commit is available
            precommit_info = self._is_precommit_available()
            if not precommit_info["available"]:
                self.log("⚠️ pre-commit not installed - skipping hook installation", "WARNING")
                print(
                    "\n⚠️  pre-commit is not installed but .pre-commit-config.yaml exists",
                    file=sys.stderr,
                )
                print("  Install with: pip install pre-commit\n", file=sys.stderr)
                self.save_metric("precommit_available", False)
                return {}

            # Log pre-commit version
            version = precommit_info.get("version", "unknown")
            self.log(f"pre-commit available: {version}")
            self.save_metric("precommit_available", True)
            self.save_metric("precommit_version", version)

            # Check if hooks are installed
            hooks_status = self._are_hooks_installed()
            if hooks_status["installed"]:
                self.log("✅ pre-commit hooks already installed")
                self.save_metric("precommit_already_installed", True)
                return {}

            if hooks_status.get("corrupted"):
                self.log("⚠️ Existing hook file appears corrupted, will reinstall", "WARNING")
                self.save_metric("precommit_corrupted", True)

            # Install the hooks
            self.log("Installing pre-commit hooks...")
            install_result = self._install_hooks()

            if install_result["success"]:
                self.log("✅ Successfully installed pre-commit hooks")
                print("\n✅ Installed pre-commit hooks\n", file=sys.stderr)
                self.save_metric("precommit_installed", True)
            else:
                error_msg = install_result.get("error", "Unknown error")
                self.log(f"⚠️ Failed to install pre-commit hooks: {error_msg}", "WARNING")
                print(
                    f"\n⚠️ Failed to install pre-commit hooks: {error_msg}",
                    file=sys.stderr,
                )
                print(
                    "  You may need to run 'pre-commit install' manually\n",
                    file=sys.stderr,
                )
                self.save_metric("precommit_installed", False)
                self.save_metric("precommit_install_error", error_msg)

        except Exception as e:
            # Fail gracefully - don't break session start
            self.log(f"Pre-commit check failed: {e}", "WARNING")
            self.save_metric("precommit_check_error", str(e))

        return {}

    def _is_env_disabled(self) -> bool:
        """Check if pre-commit auto-install is disabled via environment variable.

        Returns:
            True if disabled via AMPLIHACK_AUTO_PRECOMMIT environment variable

        Environment variable values that disable:
            - "0"
            - "false"
            - "no"
            - "off"
        """
        env_value = os.environ.get("AMPLIHACK_AUTO_PRECOMMIT", "").lower()
        return env_value in ("0", "false", "no", "off")

    def _is_git_repo(self) -> bool:
        """Check if current directory is a git repository.

        Returns:
            True if .git directory exists and is a directory
        """
        git_dir = self.project_root / ".git"
        return git_dir.exists() and git_dir.is_dir()

    def _is_precommit_available(self) -> dict[str, Any]:
        """Check if pre-commit command is available and get version info.

        Returns:
            Dictionary with:
                - available (bool): Whether pre-commit is available
                - version (str): Version string if available
                - error (str): Error message if not available
        """
        try:
            result = subprocess.run(
                ["pre-commit", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=self.project_root,
            )

            if result.returncode == 0:
                # Extract version from output like "pre-commit 3.5.0"
                version = result.stdout.strip()
                return {
                    "available": True,
                    "version": version,
                }
            return {
                "available": False,
                "error": f"pre-commit --version returned {result.returncode}",
            }

        except FileNotFoundError:
            return {
                "available": False,
                "error": "pre-commit command not found in PATH",
            }
        except subprocess.TimeoutExpired:
            return {
                "available": False,
                "error": "pre-commit --version timed out after 5 seconds",
            }
        except OSError as e:
            return {
                "available": False,
                "error": f"OS error checking pre-commit: {e}",
            }
        except Exception as e:
            return {
                "available": False,
                "error": f"Unexpected error checking pre-commit: {e}",
            }

    def _are_hooks_installed(self) -> dict[str, Any]:
        """Check if pre-commit hooks are already installed in .git/hooks.

        Returns:
            Dictionary with:
                - installed (bool): Whether hooks are installed
                - corrupted (bool): Whether existing hook appears corrupted
                - error (str): Error message if check failed
        """
        hook_file = self.project_root / ".git" / "hooks" / "pre-commit"

        if not hook_file.exists():
            return {"installed": False}

        # Check if it's a pre-commit managed hook
        try:
            content = hook_file.read_text()

            # Real pre-commit hooks contain specific markers:
            # 1. "#!/usr/bin/env python" or similar python shebang
            # 2. "import pre_commit" or "from pre_commit" (or with hyphen in comments)
            # 3. Or "INSTALL_PYTHON" (pre-commit marker)
            content_lower = content.lower()

            # Check for pre-commit import patterns (both _ and - versions)
            has_precommit_import = (
                "import pre_commit" in content_lower
                or "from pre_commit" in content_lower
                or "import pre-commit" in content_lower
                or "from pre-commit" in content_lower
                or "install_python" in content_lower
            )

            is_precommit_hook = has_precommit_import and "#!/usr/bin/env" in content

            if not is_precommit_hook:
                # Hook file exists but doesn't look like pre-commit
                return {
                    "installed": False,
                    "corrupted": True,
                    "error": "Hook file exists but doesn't appear to be pre-commit managed",
                }

            # Check for minimal expected content (avoid false positives)
            if len(content.strip()) < 50:
                return {
                    "installed": False,
                    "corrupted": True,
                    "error": "Hook file too small, may be corrupted",
                }

            return {"installed": True}

        except PermissionError:
            return {
                "installed": False,
                "error": "Permission denied reading hook file",
            }
        except UnicodeDecodeError:
            return {
                "installed": False,
                "corrupted": True,
                "error": "Hook file contains invalid text encoding",
            }
        except Exception as e:
            return {
                "installed": False,
                "error": f"Error reading hook file: {e}",
            }

    def _install_hooks(self) -> dict[str, Any]:
        """Install pre-commit hooks with comprehensive error handling.

        Returns:
            Dictionary with:
                - success (bool): Whether installation succeeded
                - error (str): Error message if failed
                - stderr (str): stderr output for diagnostics
        """
        try:
            result = subprocess.run(
                ["pre-commit", "install"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root,
            )

            if result.returncode == 0:
                return {"success": True}
            # Diagnose common failure modes
            stderr = result.stderr.lower()

            if "permission denied" in stderr:
                error = "Permission denied - check .git/hooks directory permissions"
            elif "network" in stderr or "connection" in stderr:
                error = "Network error - check internet connection for hook downloads"
            elif "not a git repository" in stderr:
                error = "Not a git repository or .git directory corrupted"
            elif "yaml" in stderr or "config" in stderr:
                error = "Invalid .pre-commit-config.yaml file"
            else:
                error = f"pre-commit install failed (exit {result.returncode})"

            return {
                "success": False,
                "error": error,
                "stderr": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Installation timed out after 30 seconds",
            }
        except FileNotFoundError:
            return {
                "success": False,
                "error": "pre-commit command not found",
            }
        except PermissionError as e:
            return {
                "success": False,
                "error": f"Permission error: {e}",
            }
        except OSError as e:
            return {
                "success": False,
                "error": f"OS error: {e}",
            }
        except Exception as e:
            self.log(f"Unexpected error installing hooks: {e}", "ERROR")
            return {
                "success": False,
                "error": f"Unexpected error: {e}",
            }


def main():
    """Entry point for the pre-commit installer hook."""
    hook = PrecommitInstallerHook()
    hook.run()


if __name__ == "__main__":
    main()
