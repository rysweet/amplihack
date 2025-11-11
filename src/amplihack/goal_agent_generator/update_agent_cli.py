"""
CLI for updating goal agents.

Provides `amplihack update-agent` command.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

try:
    import click
except ImportError:
    click = None  # type: ignore[assignment]

from .update_agent import (
    BackupManager,
    ChangesetGenerator,
    SelectiveUpdater,
    VersionDetector,
)

logger = logging.getLogger(__name__)


@click.command(name="update-agent")
@click.argument("agent_dir", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--check-only",
    is_flag=True,
    help="Check for updates without applying",
)
@click.option(
    "--auto",
    is_flag=True,
    help="Auto-apply safe updates without prompting",
)
@click.option(
    "--backup/--no-backup",
    default=True,
    help="Create backup before updating (default: yes)",
)
@click.option(
    "--target-version",
    type=str,
    default="latest",
    help="Target version to update to (default: latest)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output",
)
def update_agent(
    agent_dir: Path,
    check_only: bool,
    auto: bool,
    backup: bool,
    target_version: str,
    verbose: bool,
) -> int:
    """
    Update a goal agent with latest improvements from amplihack.

    Checks for available updates to infrastructure and skills,
    and applies selected updates while preserving custom code.

    Example:
        amplihack update-agent ./my-agent
        amplihack update-agent ./my-agent --check-only
        amplihack update-agent ./my-agent --auto --no-backup
    """
    # Configure logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(levelname)s - %(message)s", stream=sys.stdout
    )

    try:
        click.echo(f"\nAnalyzing agent: {agent_dir}")

        # Step 1: Detect current version
        click.echo("\n[1/6] Detecting agent version...")
        detector = VersionDetector()
        version_info = detector.detect(agent_dir)

        click.echo(f"  Agent: {version_info.agent_name}")
        click.echo(f"  Version: {version_info.version}")
        click.echo(f"  Phase: {version_info.infrastructure_phase}")
        click.echo(f"  Skills: {len(version_info.installed_skills)}")
        click.echo(f"  Custom files: {len(version_info.custom_files)}")

        if verbose:
            logger.debug(f"Installed skills: {version_info.installed_skills}")
            logger.debug(f"Custom files: {version_info.custom_files}")

        # Step 2: Generate changeset
        click.echo(f"\n[2/6] Checking for updates to {target_version}...")
        generator = ChangesetGenerator()
        changeset = generator.generate(version_info, target_version)

        click.echo(f"  Infrastructure updates: {len(changeset.infrastructure_updates)}")
        click.echo(f"  Skill updates: {len(changeset.skill_updates)}")
        click.echo(f"  Breaking changes: {len(changeset.breaking_changes)}")
        click.echo(f"  Bug fixes: {len(changeset.bug_fixes)}")
        click.echo(f"  Enhancements: {len(changeset.enhancements)}")
        click.echo(f"  Estimated time: {changeset.estimated_time}")

        # Step 3: Show details
        click.echo("\n[3/6] Update details:")

        if changeset.total_changes == 0:
            click.echo("  No updates available!")
            return 0

        # Show breaking changes
        if changeset.breaking_changes:
            click.echo("\n  Breaking Changes:")
            for change in changeset.breaking_changes:
                click.echo(f"    - {change}")

        # Show bug fixes
        if changeset.bug_fixes:
            click.echo("\n  Bug Fixes:")
            for fix in changeset.bug_fixes:
                click.echo(f"    - {fix}")

        # Show enhancements
        if changeset.enhancements:
            click.echo("\n  Enhancements:")
            for enhancement in changeset.enhancements:
                click.echo(f"    - {enhancement}")

        # Show infrastructure updates
        if changeset.infrastructure_updates:
            click.echo("\n  Infrastructure Updates:")
            for update in changeset.infrastructure_updates:
                safety_marker = {
                    "safe": "✓",
                    "review": "⚠",
                    "breaking": "✗",
                }.get(update.safety, "?")
                click.echo(
                    f"    {safety_marker} {update.file_path} ({update.change_type})"
                )

        # Show skill updates
        if changeset.skill_updates:
            click.echo("\n  Skill Updates:")
            for skill in changeset.skill_updates[:10]:  # Limit to 10
                click.echo(f"    - {skill.skill_name} ({skill.change_type})")
            if len(changeset.skill_updates) > 10:
                click.echo(f"    ... and {len(changeset.skill_updates) - 10} more")

        # Check-only mode: stop here
        if check_only:
            click.echo("\n✓ Check complete (no changes applied)")
            return 0

        # Step 4: Get user approval (unless auto mode)
        if not auto:
            click.echo("\n[4/6] Select updates to apply:")
            if not click.confirm("Apply all safe updates?", default=True):
                click.echo("Update cancelled")
                return 0
        else:
            click.echo("\n[4/6] Auto mode: applying safe updates...")

        # Step 5: Create backup (if enabled)
        backup_path: Optional[Path] = None
        if backup:
            click.echo("\n[5/6] Creating backup...")
            backup_manager = BackupManager(agent_dir)
            backup_path = backup_manager.create_backup(label="pre_update")
            click.echo(f"  Backup created: {backup_path.name}")
        else:
            click.echo("\n[5/6] Skipping backup (--no-backup)...")

        # Step 6: Apply updates
        click.echo("\n[6/6] Applying updates...")
        updater = SelectiveUpdater(agent_dir)

        # In auto mode, only apply safe updates
        selected_infrastructure = None
        selected_skills = None

        if auto:
            # Filter to safe updates only
            selected_infrastructure = [
                str(u.file_path)
                for u in changeset.infrastructure_updates
                if u.safety == "safe"
            ]
            # Apply all skill updates in auto mode
            selected_skills = [s.skill_name for s in changeset.skill_updates]

        results = updater.apply_changeset(
            changeset,
            selected_infrastructure=selected_infrastructure,
            selected_skills=selected_skills,
        )

        click.echo(f"  Infrastructure updated: {results['infrastructure_updated']}")
        click.echo(f"  Skills updated: {results['skills_updated']}")

        if results["errors"]:
            click.echo(f"  Errors: {len(results['errors'])}")
            for error in results["errors"]:
                click.echo(f"    - {error}", err=True)

        # Validate agent
        click.echo("\nValidating agent...")
        is_valid, issues = updater.validate_agent()

        if is_valid:
            click.echo("  ✓ Agent validation passed")
        else:
            click.echo("  ✗ Agent validation failed:", err=True)
            for issue in issues:
                click.echo(f"    - {issue}", err=True)

            # Restore backup on validation failure
            if backup_path:
                click.echo("\nRestoring from backup due to validation failure...")
                backup_manager = BackupManager(agent_dir)
                backup_manager.restore_backup(backup_path.name)
                click.echo("  Backup restored")
                return 1

        # Success
        click.echo(f"\n✓ Agent updated successfully to {target_version}")
        if backup_path:
            click.echo(f"\nBackup available at: {backup_path}")

        return 0

    except ValueError as e:
        click.echo(f"\n✗ Error: {e}", err=True)
        return 1
    except FileNotFoundError as e:
        click.echo(f"\n✗ File not found: {e}", err=True)
        return 1
    except Exception as e:
        click.echo(f"\n✗ Unexpected error: {e}", err=True)
        if verbose:
            import traceback

            traceback.print_exc()
        return 1


# For testing and direct invocation
if __name__ == "__main__":
    sys.exit(update_agent())  # type: ignore[call-arg]  # Click handles args
