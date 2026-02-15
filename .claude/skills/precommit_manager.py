#!/usr/bin/env python3
"""
Pre-commit Manager Skill - Implementation module.

Provides programmatic interface to pre-commit operations for Claude Code skills.
"""

import subprocess
import sys
from pathlib import Path
from typing import Any

# Import preference management
sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "amplihack" / "hooks"))
try:
    import precommit_prefs

    PREFS_AVAILABLE = True
except ImportError:
    PREFS_AVAILABLE = False


class PrecommitManager:
    """Manager for pre-commit operations."""

    # Template whitelist for security
    VALID_TEMPLATES = {"python", "javascript", "typescript", "go", "rust", "generic"}

    def __init__(self, project_root: Path | None = None):
        """Initialize manager.

        Args:
            project_root: Project root directory (defaults to current directory)
        """
        self.project_root = project_root or Path.cwd()

    def install(self) -> dict[str, Any]:
        """Install pre-commit hooks.

        Returns:
            Result dict with success boolean and message/error
        """
        # Check git repo
        if not (self.project_root / ".git").is_dir():
            return {"success": False, "error": "Not a git repository"}

        # Check config exists
        config_file = self.project_root / ".pre-commit-config.yaml"
        if not config_file.exists():
            return {"success": False, "error": "No .pre-commit-config.yaml found"}

        # Run pre-commit install
        try:
            result = subprocess.run(
                ["pre-commit", "install"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root,
            )

            if result.returncode == 0:
                return {"success": True, "message": "Pre-commit hooks installed successfully"}

            # Parse error
            if "permission" in result.stderr.lower():
                error = "Permission denied"
            else:
                error = f"pre-commit install failed: {result.stderr}"

            return {"success": False, "error": error}

        except FileNotFoundError:
            return {"success": False, "error": "pre-commit not found in PATH"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Installation timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def configure(self, template: str = "generic") -> dict[str, Any]:
        """Generate pre-commit config from template.

        Args:
            template: Template name (must be in whitelist)

        Returns:
            Result dict with success boolean and message/error
        """
        # Security: Validate template name
        if template not in self.VALID_TEMPLATES:
            return {
                "success": False,
                "error": f"Invalid template: {template}. Must be one of {self.VALID_TEMPLATES}",
            }

        # Security: Path traversal prevention
        if ".." in template or "/" in template or "\\" in template:
            return {"success": False, "error": "Invalid template name"}

        # Check git repo
        if not (self.project_root / ".git").is_dir():
            return {"success": False, "error": "Not a git repository"}

        config_file = self.project_root / ".pre-commit-config.yaml"

        # Check if overwriting
        overwriting = config_file.exists()

        # Get template content
        template_content = self._get_template_content(template)

        # Write config file
        try:
            config_file.write_text(template_content)
            if overwriting:
                return {
                    "success": True,
                    "message": f"Configuration overwritten with {template} template",
                }
            return {"success": True, "message": f"Configuration created from {template} template"}
        except Exception as e:
            return {"success": False, "error": f"Failed to write config: {e}"}

    def disable(self) -> dict[str, Any]:
        """Disable pre-commit auto-install.

        Returns:
            Result dict with success boolean and message/error
        """
        if not PREFS_AVAILABLE:
            return {"success": False, "error": "Preference management not available"}

        try:
            precommit_prefs.save_precommit_preference("never")
            return {"success": True, "message": "Pre-commit auto-install disabled"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def enable(self) -> dict[str, Any]:
        """Enable pre-commit auto-install.

        Returns:
            Result dict with success boolean and message/error
        """
        if not PREFS_AVAILABLE:
            return {"success": False, "error": "Preference management not available"}

        try:
            precommit_prefs.save_precommit_preference("always")
            return {"success": True, "message": "Pre-commit auto-install enabled"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def status(self) -> dict[str, Any]:
        """Get pre-commit status.

        Returns:
            Status dict with various status fields
        """
        status_dict = {}

        # Git repo check
        status_dict["git_repo"] = (self.project_root / ".git").is_dir()

        # Config file check
        config_file = self.project_root / ".pre-commit-config.yaml"
        status_dict["config_exists"] = config_file.exists()

        # Hooks installed check
        hook_file = self.project_root / ".git" / "hooks" / "pre-commit"
        if hook_file.exists():
            try:
                content = hook_file.read_text()
                status_dict["hooks_installed"] = "pre_commit" in content or "pre-commit" in content
            except Exception:
                status_dict["hooks_installed"] = False
        else:
            status_dict["hooks_installed"] = False

        # Preference
        if PREFS_AVAILABLE:
            try:
                status_dict["preference"] = precommit_prefs.load_precommit_preference()
            except Exception:
                status_dict["preference"] = "unknown"
        else:
            status_dict["preference"] = "unavailable"

        # Pre-commit availability
        try:
            result = subprocess.run(
                ["pre-commit", "--version"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            status_dict["precommit_available"] = result.returncode == 0
        except Exception:
            status_dict["precommit_available"] = False

        # Format human-readable output
        formatted = []
        formatted.append("Pre-commit Status:")
        formatted.append(f"  Git Repository: {'✓' if status_dict['git_repo'] else '✗'}")
        formatted.append(f"  Config File: {'✓' if status_dict['config_exists'] else '✗'}")
        formatted.append(f"  Hooks Installed: {'✓' if status_dict['hooks_installed'] else '✗'}")
        formatted.append(f"  Auto-install Preference: {status_dict['preference']}")
        formatted.append(
            f"  Pre-commit Binary: {'✓' if status_dict['precommit_available'] else '✗'}"
        )

        status_dict["formatted"] = "\n".join(formatted)

        return status_dict

    def baseline(self) -> dict[str, Any]:
        """Generate detect-secrets baseline.

        Returns:
            Result dict with success boolean and message/error
        """
        # Check git repo
        if not (self.project_root / ".git").is_dir():
            return {"success": False, "error": "Not a git repository"}

        baseline_file = self.project_root / ".secrets.baseline"
        overwriting = baseline_file.exists()

        # Run detect-secrets scan
        try:
            result = subprocess.run(
                ["detect-secrets", "scan", "--baseline", ".secrets.baseline"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.project_root,
            )

            if result.returncode == 0:
                if overwriting:
                    return {"success": True, "message": "Secrets baseline updated"}
                return {"success": True, "message": "Secrets baseline created"}

            return {"success": False, "error": "detect-secrets scan failed"}

        except FileNotFoundError:
            return {"success": False, "error": "detect-secrets not found in PATH"}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Baseline generation timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_template_content(self, template: str) -> str:
        """Get template content for a given template name.

        Args:
            template: Template name

        Returns:
            Template YAML content
        """
        # Minimal template content for testing
        templates = {
            "python": """repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
""",
            "javascript": """repos:
  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.1.0
    hooks:
      - id: prettier
  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v8.56.0
    hooks:
      - id: eslint
""",
            "typescript": """repos:
  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.1.0
    hooks:
      - id: prettier
        types_or: [javascript, jsx, ts, tsx]
""",
            "go": """repos:
  - repo: https://github.com/golangci/golangci-lint
    rev: v1.55.2
    hooks:
      - id: golangci-lint
""",
            "rust": """repos:
  - repo: https://github.com/doublify/pre-commit-rust
    rev: v1.0
    hooks:
      - id: fmt
      - id: clippy
""",
            "generic": """repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
""",
        }

        return templates.get(template, templates["generic"])


# Convenience functions for direct use
def install(project_root: Path | None = None) -> dict[str, Any]:
    """Install pre-commit hooks."""
    manager = PrecommitManager(project_root)
    return manager.install()


def configure(template: str = "generic", project_root: Path | None = None) -> dict[str, Any]:
    """Generate pre-commit config from template."""
    manager = PrecommitManager(project_root)
    return manager.configure(template)


def disable(project_root: Path | None = None) -> dict[str, Any]:
    """Disable pre-commit auto-install."""
    manager = PrecommitManager(project_root)
    return manager.disable()


def enable(project_root: Path | None = None) -> dict[str, Any]:
    """Enable pre-commit auto-install."""
    manager = PrecommitManager(project_root)
    return manager.enable()


def status(project_root: Path | None = None) -> dict[str, Any]:
    """Get pre-commit status."""
    manager = PrecommitManager(project_root)
    return manager.status()


def baseline(project_root: Path | None = None) -> dict[str, Any]:
    """Generate detect-secrets baseline."""
    manager = PrecommitManager(project_root)
    return manager.baseline()
