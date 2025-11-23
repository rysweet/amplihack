"""CLI commands for profile management.

Provides user-facing commands for managing amplihack profiles.
"""

import click
import yaml
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from .switcher import ProfileSwitcher
from .loader import ProfileLoader


console = Console()


@click.group(name="profile")
def profile_cli():
    """Manage amplihack profiles.

    Profile system controls which components are visible to Claude Code.
    Switch profiles BEFORE starting Claude Code to customize your environment.

    Example:
        amplihack profile list
        amplihack profile use coding
        claude  # Now starts with coding profile
    """
    pass


@profile_cli.command()
def list():
    """List available profiles.

    Shows all profiles in .claude/profiles/ with descriptions
    and indicates which profile is currently active.

    Example:
        amplihack profile list
    """
    try:
        loader = ProfileLoader()
        switcher = ProfileSwitcher()
        current = switcher.get_current_profile()

        table = Table(title="Available Profiles", show_header=True, header_style="bold cyan")
        table.add_column("Profile", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Status", style="dim", no_wrap=True)

        available = loader.list_available_profiles()

        if not available:
            console.print("[yellow]No profiles found in .claude/profiles/[/yellow]")
            console.print("\nCreate a profile first using: amplihack profile create <name>")
            return

        for profile_name in available:
            try:
                profile = loader.load_profile(profile_name)
                status = "[green]* active[/green]" if profile_name == current else ""
                table.add_row(profile.name, profile.description, status)
            except Exception as e:
                table.add_row(profile_name, f"[red]Error: {e}[/red]", "")

        console.print(table)

        # Show usage hint
        console.print("\n[dim]Use 'amplihack profile use <name>' to switch profiles[/dim]")

    except Exception as e:
        console.print(f"[red]Error listing profiles: {e}[/red]")
        raise click.Abort()


@profile_cli.command()
def current():
    """Show current profile details.

    Displays information about the currently active profile
    including enabled component counts.

    Example:
        amplihack profile current
    """
    try:
        switcher = ProfileSwitcher()
        profile_name = switcher.get_current_profile()
        info = switcher.get_profile_info(profile_name)

        # Build info text
        info_text = f"[bold cyan]{info['name']}[/bold cyan]\n\n"
        info_text += f"{info['description']}\n\n"
        info_text += f"[dim]Version: {info['version']}[/dim]\n\n"
        info_text += "[bold]Enabled Components:[/bold]\n"
        info_text += f"  Commands: {info['component_counts']['commands']}\n"
        info_text += f"  Agents: {info['component_counts']['agents']}\n"
        info_text += f"  Skills: {info['component_counts']['skills']}"

        console.print(Panel(info_text, title="Current Profile", border_style="cyan"))

    except Exception as e:
        console.print(f"[red]Error getting current profile: {e}[/red]")
        raise click.Abort()


@profile_cli.command()
@click.argument("profile_name")
def use(profile_name: str):
    """Switch to specified profile.

    Changes the active profile which controls what components
    Claude Code will see when it starts.

    IMPORTANT: Must be run BEFORE starting Claude Code.

    Args:
        profile_name: Name of profile to switch to

    Example:
        amplihack profile use coding
        claude  # Start Claude Code with coding profile
    """
    try:
        switcher = ProfileSwitcher()

        # Check if profile exists
        if not switcher.loader.profile_exists(profile_name):
            available = switcher.loader.list_available_profiles()
            console.print(f"[red]Profile '{profile_name}' not found.[/red]")
            console.print(f"\nAvailable profiles: {', '.join(available)}")
            raise click.Abort()

        # Perform switch
        with console.status(f"[bold cyan]Switching to '{profile_name}' profile...[/bold cyan]"):
            result = switcher.switch_profile(profile_name)

        # Show success message
        console.print(f"[green]✓[/green] Switched to '[cyan]{profile_name}[/cyan]' profile")
        console.print(f"\n[bold]Enabled Components:[/bold]")
        console.print(f"  Commands: {result['components']['commands']}")
        console.print(f"  Agents: {result['components']['agents']}")
        console.print(f"  Skills: {result['components']['skills']}")

        console.print("\n[dim]Start Claude Code now to use this profile[/dim]")

    except Exception as e:
        console.print(f"[red]✗ Switch failed: {e}[/red]")
        raise click.Abort()


@profile_cli.command()
@click.argument("profile_name")
def show(profile_name: str):
    """Show detailed profile information.

    Displays complete profile configuration including all
    component filters and metadata.

    Args:
        profile_name: Name of profile to show

    Example:
        amplihack profile show coding
    """
    try:
        switcher = ProfileSwitcher()
        loader = ProfileLoader()

        # Load profile
        profile = loader.load_profile(profile_name)
        info = switcher.get_profile_info(profile_name)

        # Header
        console.print(f"\n[bold cyan]{profile.name}[/bold cyan]")
        console.print(f"{profile.description}")
        console.print(f"[dim]Version: {profile.version}[/dim]")

        if info["is_current"]:
            console.print("[green]* Currently active[/green]")

        # Component counts
        console.print(f"\n[bold]Enabled Components:[/bold]")
        console.print(f"  Commands: {info['component_counts']['commands']}")
        console.print(f"  Agents: {info['component_counts']['agents']}")
        console.print(f"  Skills: {info['component_counts']['skills']}")

        # Show filters
        console.print("\n[bold]Component Filters:[/bold]")

        for category in ["commands", "agents", "skills"]:
            filter_obj = getattr(profile, category)
            console.print(f"\n[cyan]{category.capitalize()}:[/cyan]")
            console.print(f"  Includes: {', '.join(filter_obj.includes)}")
            if filter_obj.excludes:
                console.print(f"  Excludes: {', '.join(filter_obj.excludes)}")

        # Show metadata if present
        if profile.metadata:
            console.print("\n[bold]Metadata:[/bold]")
            for key, value in profile.metadata.items():
                console.print(f"  {key}: {value}")

    except Exception as e:
        console.print(f"[red]Error showing profile: {e}[/red]")
        raise click.Abort()


@profile_cli.command()
@click.argument("profile_name")
@click.option("--view", is_flag=True, help="View profile file in editor after creation")
def create(profile_name: str, view: bool = False):
    """Create a new profile from template.

    Creates a new profile YAML file in .claude/profiles/ with
    a basic template that you can customize.

    Args:
        profile_name: Name for new profile

    Example:
        amplihack profile create myprofile
        # Edit .claude/profiles/myprofile.yaml
        amplihack profile use myprofile
    """
    try:
        loader = ProfileLoader()
        profile_path = loader.get_profile_path(profile_name)

        # Check if already exists
        if profile_path.exists():
            console.print(f"[yellow]Profile '{profile_name}' already exists at {profile_path}[/yellow]")
            raise click.Abort()

        # Create profiles directory if needed
        profile_path.parent.mkdir(parents=True, exist_ok=True)

        # Create template
        template = {
            "name": profile_name,
            "description": f"Custom profile: {profile_name}",
            "version": "1.0.0",
            "includes": {
                "commands": ["**/*"],
                "agents": ["**/*"],
                "skills": ["**/*"]
            },
            "excludes": {
                "commands": [],
                "agents": [],
                "skills": []
            },
            "metadata": {
                "author": "user",
                "tags": ["custom"]
            }
        }

        # Write template
        with open(profile_path, 'w') as f:
            yaml.dump(template, f, default_flow_style=False, sort_keys=False)

        console.print(f"[green]✓[/green] Created profile '[cyan]{profile_name}[/cyan]' at {profile_path}")
        console.print("\n[bold]Next steps:[/bold]")
        console.print(f"  1. Edit {profile_path} to customize filters")
        console.print(f"  2. Run: amplihack profile validate {profile_name}")
        console.print(f"  3. Run: amplihack profile use {profile_name}")

        if view:
            # Show file contents
            console.print("\n[bold]Profile contents:[/bold]")
            with open(profile_path) as f:
                syntax = Syntax(f.read(), "yaml", theme="monokai", line_numbers=True)
                console.print(syntax)

    except Exception as e:
        console.print(f"[red]Error creating profile: {e}[/red]")
        raise click.Abort()


@profile_cli.command()
@click.argument("profile_name")
def validate(profile_name: str):
    """Validate a profile configuration.

    Checks that a profile YAML file is well-formed and
    contains all required fields.

    Args:
        profile_name: Name of profile to validate

    Example:
        amplihack profile validate coding
    """
    try:
        loader = ProfileLoader()

        # Load and validate
        with console.status(f"[bold cyan]Validating '{profile_name}'...[/bold cyan]"):
            profile = loader.load_profile(profile_name)
            errors = loader.validate_profile(profile)

        if errors:
            console.print(f"[red]✗ Profile '{profile_name}' validation failed:[/red]")
            for error in errors:
                console.print(f"  - {error}")
            raise click.Abort()
        else:
            console.print(f"[green]✓[/green] Profile '[cyan]{profile_name}[/cyan]' is valid")

            # Show what would be enabled
            switcher = ProfileSwitcher()
            components = switcher._resolve_components(profile)
            console.print(f"\n[bold]Would enable:[/bold]")
            console.print(f"  Commands: {len(components['commands'])}")
            console.print(f"  Agents: {len(components['agents'])}")
            console.print(f"  Skills: {len(components['skills'])}")

    except Exception as e:
        console.print(f"[red]Error validating profile: {e}[/red]")
        raise click.Abort()


@profile_cli.command()
def verify():
    """Verify current profile integrity.

    Checks that the current profile setup is valid and
    all symlinks are correctly configured.

    Example:
        amplihack profile verify
    """
    try:
        switcher = ProfileSwitcher()

        with console.status("[bold cyan]Verifying profile setup...[/bold cyan]"):
            is_valid = switcher.verify_profile_integrity()

        if is_valid:
            current = switcher.get_current_profile()
            console.print(f"[green]✓[/green] Profile setup is valid")
            console.print(f"\nCurrent profile: [cyan]{current}[/cyan]")
        else:
            console.print("[red]✗ Profile setup is corrupted or incomplete[/red]")
            console.print("\nRun 'amplihack profile use <name>' to fix")
            raise click.Abort()

    except Exception as e:
        console.print(f"[red]Error verifying profile: {e}[/red]")
        raise click.Abort()


@profile_cli.command()
@click.argument("profile_name")
@click.option("--components", is_flag=True, help="Show individual component paths")
def inspect(profile_name: str, components: bool = False):
    """Inspect what components a profile would enable.

    Shows detailed list of components that would be enabled
    by a profile without actually switching to it.

    Args:
        profile_name: Name of profile to inspect

    Example:
        amplihack profile inspect coding
        amplihack profile inspect coding --components
    """
    try:
        switcher = ProfileSwitcher()
        loader = ProfileLoader()

        # Load profile
        profile = loader.load_profile(profile_name)
        resolved = switcher._resolve_components(profile)

        console.print(f"\n[bold cyan]{profile_name}[/bold cyan] would enable:\n")

        for category in ["commands", "agents", "skills"]:
            count = len(resolved[category])
            console.print(f"[bold]{category.capitalize()}:[/bold] {count} files")

            if components and resolved[category]:
                for comp in sorted(resolved[category])[:10]:  # Limit to 10
                    rel_path = comp.relative_to(switcher.claude_dir / "_all" / category)
                    console.print(f"  - {rel_path}")

                if len(resolved[category]) > 10:
                    console.print(f"  ... and {len(resolved[category]) - 10} more")

            console.print()

    except Exception as e:
        console.print(f"[red]Error inspecting profile: {e}[/red]")
        raise click.Abort()
