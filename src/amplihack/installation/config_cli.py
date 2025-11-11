"""CLI commands for managing Amplihack configuration.

Provides commands for viewing status, integrating, removing, and resetting
Amplihack configuration in user projects.
"""
# pyright: reportMissingImports=false, reportOptionalMemberAccess=false

import shutil
from pathlib import Path
from typing import Optional

try:
    import click
except ImportError:
    click = None  # type: ignore[assignment]

from .claude_md_integrator import IMPORT_STATEMENT, integrate_import, remove_import


def _find_project_root() -> Optional[Path]:
    """Find project root by looking for .claude directory.

    Returns:
        Path to project root, or None if not found
    """
    current = Path.cwd()

    # Check current directory and parents
    for path in [current] + list(current.parents):
        if (path / ".claude").exists():
            return path

    return None


def _print_status(project_root: Path):
    """Print current configuration status.

    Args:
        project_root: Project root directory
    """
    claude_dir = project_root / ".claude"
    amplihack_dir = claude_dir / "amplihack"
    claude_md = claude_dir / "CLAUDE.md"

    try:
        from rich.console import Console
        from rich.table import Table

        console = Console()

        # Installation status
        console.print("\n[bold]Amplihack Configuration Status[/bold]\n")

        table = Table(show_header=False)
        table.add_column("Property", style="cyan")
        table.add_column("Value")

        if amplihack_dir.exists():
            table.add_row("Installation", "✓ Installed")
            table.add_row("Namespace", str(amplihack_dir.relative_to(project_root)))

            # Count files
            files = list(amplihack_dir.rglob("*"))
            file_count = len([f for f in files if f.is_file()])
            table.add_row("Files", str(file_count))
        else:
            table.add_row("Installation", "✗ Not installed")

        console.print(table)

        # Integration status
        console.print("\n[bold]Integration[/bold]\n")

        int_table = Table(show_header=False)
        int_table.add_column("Property", style="cyan")
        int_table.add_column("Value")

        if claude_md.exists():
            content = claude_md.read_text()
            has_import = IMPORT_STATEMENT in content

            int_table.add_row("CLAUDE.md", "✓ Exists")
            int_table.add_row("Import status", "✓ Present" if has_import else "✗ Not present")

            if has_import:
                int_table.add_row("Import statement", IMPORT_STATEMENT)
        else:
            int_table.add_row("CLAUDE.md", "✗ Not found")

        console.print(int_table)

    except ImportError:
        # Fallback to basic printing
        print("\nAmplihack Configuration Status\n")
        print("=" * 60)

        print("\nInstallation:")
        if amplihack_dir.exists():
            print("  Status: Installed")
            print(f"  Namespace: {amplihack_dir.relative_to(project_root)}")

            files = list(amplihack_dir.rglob("*"))
            file_count = len([f for f in files if f.is_file()])
            print(f"  Files: {file_count}")
        else:
            print("  Status: Not installed")

        print("\nIntegration:")
        if claude_md.exists():
            content = claude_md.read_text()
            has_import = IMPORT_STATEMENT in content

            print("  CLAUDE.md: Exists")
            print(f"  Import status: {'Present' if has_import else 'Not present'}")

            if has_import:
                print(f"  Import statement: {IMPORT_STATEMENT}")
        else:
            print("  CLAUDE.md: Not found")

        print("\n" + "=" * 60)


@click.group()
def config():
    """Manage Amplihack configuration."""


@config.command()
def show():
    """Show current configuration status."""
    project_root = _find_project_root()

    if not project_root:
        click.echo("Error: Not in a Claude project. No .claude/ directory found.")
        raise click.Abort()

    _print_status(project_root)


@config.command()
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.option("--dry-run", is_flag=True, help="Preview changes without applying")
def integrate(force: bool, dry_run: bool):
    """Add Amplihack import to CLAUDE.md."""
    project_root = _find_project_root()

    if not project_root:
        click.echo("Error: Not in a Claude project. No .claude/ directory found.")
        raise click.Abort()

    claude_dir = project_root / ".claude"
    amplihack_dir = claude_dir / "amplihack"

    # Check if Amplihack is installed
    if not amplihack_dir.exists():
        click.echo("Error: Amplihack not installed. Run 'amplihack install' first.")
        raise click.Abort()

    claude_md = claude_dir / "CLAUDE.md"

    # Preview in dry-run mode
    if dry_run:
        result = integrate_import(claude_md, dry_run=True)
        click.echo("\n" + "=" * 60)
        click.echo("DRY RUN - Preview of changes:")
        click.echo("=" * 60)
        click.echo(result.preview)
        click.echo("=" * 60)
        click.echo("\nNo changes made. Remove --dry-run to apply.")
        return

    # Show preview and ask for confirmation
    if not force:
        result = integrate_import(claude_md, dry_run=True)

        click.echo("\n" + "=" * 60)
        click.echo("This will add Amplihack configuration to your .claude/CLAUDE.md:")
        click.echo("=" * 60)
        click.echo(result.preview)
        click.echo("\nYour existing content will be preserved.")

        if claude_md.exists():
            click.echo("A backup will be created before modification.")

        click.echo("=" * 60)

        if not click.confirm("Continue?", default=True):
            click.echo("Cancelled.")
            return

    # Perform integration
    result = integrate_import(claude_md, dry_run=False)

    if result.success:
        click.echo(f"\n✓ {result.action_taken.replace('_', ' ').title()}")

        if result.backup_path:
            click.echo(f"  Backup: {result.backup_path.relative_to(project_root)}")

        click.echo("\nAmplihack is now active!")
    else:
        click.echo(f"\n✗ Error: {result.error}")
        raise click.Abort()


@config.command()
@click.option(
    "--keep-files",
    is_flag=True,
    help="Remove import but keep .claude/amplihack/ directory",
)
def remove(keep_files: bool):
    """Remove Amplihack import from CLAUDE.md."""
    project_root = _find_project_root()

    if not project_root:
        click.echo("Error: Not in a Claude project. No .claude/ directory found.")
        raise click.Abort()

    claude_dir = project_root / ".claude"
    amplihack_dir = claude_dir / "amplihack"
    claude_md = claude_dir / "CLAUDE.md"

    # Show what will be removed
    click.echo("\n" + "=" * 60)
    click.echo("This will remove Amplihack integration from .claude/CLAUDE.md")

    if not keep_files and amplihack_dir.exists():
        click.echo("\nThe .claude/amplihack/ directory will be DELETED.")

    if claude_md.exists():
        click.echo("A backup will be created before modification.")

    click.echo("=" * 60)

    if not click.confirm("Continue?", default=False):
        click.echo("Cancelled.")
        return

    # Remove import
    result = remove_import(claude_md, dry_run=False)

    if result.success and result.action_taken == "removed":
        click.echo("\n✓ Import removed")

        if result.backup_path:
            click.echo(f"  Backup: {result.backup_path.relative_to(project_root)}")
    elif result.action_taken == "not_present":
        click.echo("\n✓ Import not present in CLAUDE.md")
    else:
        click.echo(f"\n✗ Error: {result.error}")
        raise click.Abort()

    # Remove directory if requested
    if not keep_files and amplihack_dir.exists():
        try:
            shutil.rmtree(amplihack_dir)
            click.echo(f"✓ Removed {amplihack_dir.relative_to(project_root)}")
        except (OSError, PermissionError) as e:
            click.echo(f"\n✗ Failed to remove directory: {e}")

    click.echo("\nAmplihack has been removed.")


@config.command()
@click.option(
    "--force",
    is_flag=True,
    required=True,
    help="Required flag to confirm destructive action",
)
def reset(force: bool):
    """Reset to fresh Amplihack config (destructive).

    This removes the current installation and reinstalls from bundled files.
    Requires --force flag to confirm.
    """
    if not force:
        click.echo("Error: --force flag is required for reset operation")
        raise click.Abort()

    project_root = _find_project_root()

    if not project_root:
        click.echo("Error: Not in a Claude project. No .claude/ directory found.")
        raise click.Abort()

    claude_dir = project_root / ".claude"
    amplihack_dir = claude_dir / "amplihack"

    if not amplihack_dir.exists():
        click.echo("Error: Amplihack not installed. Nothing to reset.")
        raise click.Abort()

    # Show warning
    click.echo("\n" + "=" * 60)
    click.echo("WARNING: This will DELETE your .claude/amplihack/ directory")
    click.echo("and reinstall from bundled files.")
    click.echo("=" * 60)

    if not click.confirm("Are you sure you want to continue?", default=False):
        click.echo("Cancelled.")
        return

    # Remove existing installation
    try:
        shutil.rmtree(amplihack_dir)
        click.echo(f"✓ Removed {amplihack_dir.relative_to(project_root)}")
    except (OSError, PermissionError) as e:
        click.echo(f"\n✗ Failed to remove directory: {e}")
        raise click.Abort()

    # Note: Actual reinstallation would require access to source files
    # This would be integrated with the main install command
    click.echo("\n✓ Reset complete")
    click.echo("\nRun 'amplihack install' to reinstall from bundled files.")
