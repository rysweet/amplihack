"""
Beads Prerequisites - Detection, Installation, and Setup Verification.

Provides beads detection, version compatibility checking, initialization,
and installation guidance when beads is missing.

Philosophy:
- Zero-BS: Direct detection, no complex dependency management
- Ruthless Simplicity: Straightforward version checks
- Helpful Guidance: Clear installation instructions
"""

import subprocess
from typing import Optional
from pathlib import Path


# =============================================================================
# Result Type for Explicit Error Handling
# =============================================================================

class PrerequisiteError(Exception):
    """Prerequisites check error."""
    pass


class Result:
    """Result wrapper for explicit error handling."""

    def __init__(self, value=None, error=None):
        self.value = value
        self.error = error
        self.is_ok = error is None

    @staticmethod
    def ok(value):
        """Create successful result."""
        return Result(value=value)

    @staticmethod
    def err(error):
        """Create error result."""
        return Result(error=error)


# =============================================================================
# BeadsPrerequisites - Detection and Installation
# =============================================================================

class BeadsPrerequisites:
    """
    Handles beads detection, version checking, and installation guidance.

    Provides methods to:
    - Check if beads CLI is installed
    - Verify beads is initialized in project
    - Check version compatibility
    - Initialize beads in new projects
    - Provide installation instructions
    """

    BEADS_CLI_COMMAND = "bd"
    MIN_VERSION = "0.1.0"

    @staticmethod
    def check_installed() -> Result:
        """
        Check if beads CLI is installed.

        Returns:
            Result with bool indicating if beads is available
        """
        try:
            result = subprocess.run(
                [BeadsPrerequisites.BEADS_CLI_COMMAND, "version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return Result.ok(result.returncode == 0)

        except (FileNotFoundError, subprocess.TimeoutExpired):
            return Result.ok(False)

        except Exception as e:
            return Result.err(PrerequisiteError(f"Failed to check installation: {e}"))

    @staticmethod
    def check_initialized(project_dir: Optional[Path] = None) -> Result:
        """
        Check if beads is initialized in project.

        Args:
            project_dir: Project directory (defaults to cwd)

        Returns:
            Result with bool indicating if initialized
        """
        try:
            project_path = project_dir or Path.cwd()
            beads_dir = project_path / ".beads"
            return Result.ok(beads_dir.exists() and beads_dir.is_dir())

        except Exception as e:
            return Result.err(PrerequisiteError(f"Failed to check initialization: {e}"))

    @staticmethod
    def initialize(project_dir: Optional[Path] = None) -> Result:
        """
        Initialize beads in project directory.

        Args:
            project_dir: Project directory (defaults to cwd)

        Returns:
            Result with bool indicating success
        """
        # Check if beads is installed
        installed_result = BeadsPrerequisites.check_installed()
        if not installed_result.is_ok:
            return installed_result

        if not installed_result.value:
            return Result.err(PrerequisiteError("Beads CLI not installed"))

        try:
            project_path = str(project_dir or Path.cwd())

            result = subprocess.run(
                [BeadsPrerequisites.BEADS_CLI_COMMAND, "init"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                return Result.ok(True)
            else:
                return Result.err(PrerequisiteError(f"Init failed: {result.stderr}"))

        except Exception as e:
            return Result.err(PrerequisiteError(f"Failed to initialize: {e}"))

    @staticmethod
    def get_version() -> Result:
        """
        Get beads CLI version.

        Returns:
            Result with version string or error
        """
        try:
            result = subprocess.run(
                [BeadsPrerequisites.BEADS_CLI_COMMAND, "version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Parse version from output
                version_output = result.stdout.strip()
                # Extract version number (e.g., "beads 0.2.0" -> "0.2.0")
                parts = version_output.split()
                if len(parts) >= 2:
                    version = parts[-1]
                else:
                    version = version_output

                return Result.ok(version)
            else:
                return Result.err(PrerequisiteError("Failed to get version"))

        except FileNotFoundError:
            return Result.err(PrerequisiteError("Beads CLI not found"))

        except Exception as e:
            return Result.err(PrerequisiteError(f"Failed to get version: {e}"))

    @staticmethod
    def check_version_compatibility(min_version: Optional[str] = None) -> Result:
        """
        Check if installed version meets minimum requirements.

        Args:
            min_version: Minimum required version (defaults to MIN_VERSION)

        Returns:
            Result with bool indicating compatibility
        """
        required_version = min_version or BeadsPrerequisites.MIN_VERSION

        version_result = BeadsPrerequisites.get_version()
        if not version_result.is_ok:
            return version_result

        current_version = version_result.value

        try:
            # Simple version comparison (major.minor.patch)
            def parse_version(v: str) -> tuple:
                parts = v.lstrip('v').split('.')
                return tuple(int(p) for p in parts[:3])

            current = parse_version(current_version)
            required = parse_version(required_version)

            is_compatible = current >= required
            return Result.ok(is_compatible)

        except Exception as e:
            return Result.err(PrerequisiteError(f"Version comparison failed: {e}"))

    @staticmethod
    def get_installation_guidance() -> str:
        """
        Get installation instructions for beads.

        Returns:
            Installation instructions string
        """
        return """
# Beads CLI Installation

Beads is required for memory persistence and issue tracking.

## Installation Options:

### Option 1: Direct Download (Recommended)
Visit: https://github.com/beadshq/beads
Download the latest release for your platform

### Option 2: Build from Source
```bash
git clone https://github.com/beadshq/beads
cd beads
cargo build --release
cp target/release/bd /usr/local/bin/
```

### Option 3: Package Manager (if available)
```bash
# Homebrew (macOS)
brew install beads

# apt (Ubuntu/Debian)
sudo apt install beads-cli
```

## Verify Installation:
```bash
bd version
```

## Initialize in Project:
```bash
cd /path/to/your/project
bd init
```

## Documentation:
https://beadshq.com/docs
"""

    @staticmethod
    def verify_setup() -> dict:
        """
        Comprehensive setup verification.

        Returns:
            Dictionary with setup status information
        """
        status = {
            "beads_available": False,
            "beads_initialized": False,
            "version": None,
            "version_compatible": False,
            "errors": []
        }

        # Check installation
        installed_result = BeadsPrerequisites.check_installed()
        if installed_result.is_ok:
            status["beads_available"] = installed_result.value
        else:
            status["errors"].append(str(installed_result.error))

        # If installed, check version
        if status["beads_available"]:
            version_result = BeadsPrerequisites.get_version()
            if version_result.is_ok:
                status["version"] = version_result.value

                # Check compatibility
                compat_result = BeadsPrerequisites.check_version_compatibility()
                if compat_result.is_ok:
                    status["version_compatible"] = compat_result.value

            # Check initialization
            init_result = BeadsPrerequisites.check_initialized()
            if init_result.is_ok:
                status["beads_initialized"] = init_result.value

        return status


# =============================================================================
# BeadsInstaller - Installation Helpers
# =============================================================================

class BeadsInstaller:
    """
    Provides installation helpers and guidance.

    Note: Automatic installation is intentionally limited for security.
    Users should manually install beads from trusted sources.
    """

    @staticmethod
    def get_installation_instructions() -> str:
        """Get installation instructions."""
        return BeadsPrerequisites.get_installation_guidance()

    @staticmethod
    def can_auto_install() -> bool:
        """
        Check if automatic installation is supported.

        Returns:
            False - automatic installation not supported for security
        """
        return False

    @staticmethod
    def requires_confirmation() -> bool:
        """
        Check if installation requires user confirmation.

        Returns:
            True - always require confirmation for security
        """
        return True


# =============================================================================
# BeadsSetup - High-Level Setup Functions
# =============================================================================

def verify_beads_setup() -> dict:
    """
    Verify complete beads setup.

    Returns:
        Dictionary with setup verification results
    """
    return BeadsPrerequisites.verify_setup()


# =============================================================================
# Convenience Functions for Tests
# =============================================================================

def check_beads_available() -> bool:
    """
    Simple availability check.

    Returns:
        True if beads is available and initialized
    """
    result = BeadsPrerequisites.check_installed()
    if not result.is_ok or not result.value:
        return False

    init_result = BeadsPrerequisites.check_initialized()
    return init_result.is_ok and init_result.value
