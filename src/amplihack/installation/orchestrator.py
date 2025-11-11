"""Orchestrate the complete installation workflow.

This module coordinates conflict detection, namespace installation, and
CLAUDE.md integration with user interaction.
"""
# pyright: reportMissingImports=false

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

from .claude_md_integrator import IntegrationResult, integrate_import
from .conflict_detector import detect_conflicts
from .namespace_installer import InstallResult, install_to_namespace


class InstallMode(Enum):
    """Installation mode."""

    INSTALL = "install"  # Persistent installation
    UVX = "uvx"  # Ephemeral installation


@dataclass
class OrchestrationResult:
    """Complete installation result.

    Attributes:
        success: True if installation completed successfully
        mode: Installation mode used
        conflicts_detected: True if conflicts were found
        conflicts_resolved: True if conflicts were resolved
        installation_result: Result from namespace installer
        integration_result: Result from CLAUDE.md integration (if performed)
        user_actions_required: List of manual actions user needs to take
        errors: List of error messages
    """

    success: bool
    mode: InstallMode
    conflicts_detected: bool
    conflicts_resolved: bool
    installation_result: InstallResult
    integration_result: Optional[IntegrationResult] = None
    user_actions_required: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def _prompt_user(message: str, default: bool = True) -> bool:
    """Prompt user for yes/no decision.

    Args:
        message: Prompt message to display
        default: Default value if user just presses enter

    Returns:
        True if user answered yes, False otherwise
    """
    try:
        # Try to use rich for better prompts
        from rich.prompt import Confirm

        return Confirm.ask(message, default=default)
    except ImportError:
        # Fallback to basic input
        suffix = "[Y/n]" if default else "[y/N]"
        response = input(f"{message} {suffix}: ").strip().lower()

        if not response:
            return default

        return response in ["y", "yes"]


def orchestrate_installation(
    mode: InstallMode,
    target_dir: Path,
    source_dir: Path,
    force: bool = False,
    auto_integrate: bool = True,
    non_interactive: bool = False,
) -> OrchestrationResult:
    """Orchestrate complete installation workflow.

    Args:
        mode: Installation mode (install or uvx)
        target_dir: Project root containing .claude/
        source_dir: Source directory with Amplihack config files
        force: Skip prompts and force overwrite
        auto_integrate: Automatically integrate with CLAUDE.md
        non_interactive: Skip all prompts (for CI/automated installs)

    Returns:
        OrchestrationResult with complete installation details

    Example:
        >>> result = orchestrate_installation(
        ...     InstallMode.INSTALL,
        ...     Path("."),
        ...     Path("src/amplihack/config"),
        ... )
        >>> assert result.success
    """
    claude_dir = target_dir / ".claude"
    errors = []
    user_actions = []

    # Step 1: Detect conflicts
    manifest = [
        "CLAUDE.md",
        "agents/architect.md",
        "agents/builder.md",
        "commands/ultrathink.md",
    ]

    conflict_report = detect_conflicts(claude_dir, manifest)

    # Step 2: Handle upgrade scenario
    amplihack_dir = claude_dir / "amplihack"
    is_upgrade = amplihack_dir.exists()

    if is_upgrade and not force and not non_interactive:
        print("\n" + "=" * 60)
        print("Amplihack is already installed at .claude/amplihack/")
        print("\nThis will upgrade your installation.")
        print("Your existing configuration will be backed up.")
        print("=" * 60)

        if not _prompt_user("Continue with upgrade?", default=True):
            return OrchestrationResult(
                success=False,
                mode=mode,
                conflicts_detected=conflict_report.has_conflicts,
                conflicts_resolved=False,
                installation_result=InstallResult(
                    success=False,
                    installed_path=amplihack_dir,
                    errors=["Upgrade cancelled by user"],
                ),
                errors=["Upgrade cancelled by user"],
            )

    # Step 3: Show conflict information if any
    if conflict_report.has_conflicts and not is_upgrade and not non_interactive:
        print("\n" + "=" * 60)
        print("Existing configuration detected:")

        if conflict_report.existing_claude_md:
            print("  • .claude/CLAUDE.md exists")

        if conflict_report.existing_agents:
            print(f"  • Custom agents: {', '.join(conflict_report.existing_agents)}")

        print("\nInstalling to .claude/amplihack/ will avoid these conflicts.")
        print("Your existing files will not be modified.")
        print("=" * 60)

        if not force:
            if not _prompt_user("Continue with namespaced installation?", default=True):
                return OrchestrationResult(
                    success=False,
                    mode=mode,
                    conflicts_detected=True,
                    conflicts_resolved=False,
                    installation_result=InstallResult(
                        success=False,
                        installed_path=amplihack_dir,
                        errors=["Installation cancelled by user"],
                    ),
                    errors=["Installation cancelled by user"],
                )

    # Step 4: Install to namespace
    install_result = install_to_namespace(
        source_dir=source_dir,
        target_dir=claude_dir,
        force=force or is_upgrade,
    )

    if not install_result.success:
        return OrchestrationResult(
            success=False,
            mode=mode,
            conflicts_detected=conflict_report.has_conflicts,
            conflicts_resolved=False,
            installation_result=install_result,
            errors=install_result.errors,
        )

    # Step 5: Integration decision (only for persistent install mode)
    integration_result = None

    if mode == InstallMode.INSTALL and auto_integrate:
        claude_md_path = claude_dir / "CLAUDE.md"

        # In non-interactive or force mode, integrate automatically
        if non_interactive or force:
            integration_result = integrate_import(claude_md_path, dry_run=False)
        else:
            # Show integration offer
            print("\n" + "=" * 60)
            print("Amplihack has been installed to .claude/amplihack/")
            print("\nTo activate it, we can add an import to your .claude/CLAUDE.md:")
            print("\n  @.claude/amplihack/CLAUDE.md")
            print("\nThis allows Claude to use Amplihack's agents and tools.")
            print("=" * 60)

            if _prompt_user("Add import to CLAUDE.md?", default=True):
                integration_result = integrate_import(claude_md_path, dry_run=False)
            else:
                user_actions.append(
                    "To activate Amplihack, add '@.claude/amplihack/CLAUDE.md' "
                    "to your .claude/CLAUDE.md, or run: amplihack config integrate"
                )

    elif mode == InstallMode.UVX:
        # UVX mode: skip integration (temporary session)
        user_actions.append(
            "UVX mode: Changes won't persist. For permanent installation: pip install amplihack"
        )

    # Step 6: Build final result
    integration_success = (
        integration_result is None
        or integration_result.success
        or integration_result.action_taken == "already_present"
    )

    return OrchestrationResult(
        success=install_result.success and integration_success,
        mode=mode,
        conflicts_detected=conflict_report.has_conflicts,
        conflicts_resolved=conflict_report.has_conflicts,
        installation_result=install_result,
        integration_result=integration_result,
        user_actions_required=user_actions,
        errors=errors,
    )
