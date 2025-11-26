"""Command-line interface for profile management.

This module provides CLI commands for listing, viewing, switching, and validating
amplihack profiles.
"""

import sys
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    HAS_RICH = True
except ImportError:
    HAS_RICH = False

    # Fallback implementations if rich is not available
    class Console:
        def print(self, *args, **kwargs):
            print(*args)

    class Panel:
        def __init__(self, *args, **kwargs):
            pass

    class Table:
        def __init__(self, *args, **kwargs):
            self.rows = []

        def add_column(self, *args, **kwargs):
            pass

        def add_row(self, *args, **kwargs):
            self.rows.append(args)


from .config import ConfigManager
from .discovery import ComponentDiscovery
from .filter import ComponentFilter, estimate_token_count
from .loader import ProfileLoader
from .parser import ProfileParser

console = Console()


class ProfileCLI:
    """Command-line interface for profile management.

    Provides commands for:
    - Listing available profiles
    - Showing profile details
    - Switching active profile
    - Validating profile configuration

    Example:
        >>> cli = ProfileCLI()
        >>> cli.list_profiles()
        >>> cli.switch_profile("amplihack://profiles/coding")
    """

    def __init__(self):
        """Initialize CLI with loader, parser, and config manager."""
        self.loader = ProfileLoader()
        self.parser = ProfileParser()
        self.config = ConfigManager()
        self.discovery = ComponentDiscovery()
        self.filter = ComponentFilter()

    def list_profiles(self):
        """List all available built-in profiles.

        Displays a table with profile name, description, and URI.
        """
        profiles_dir = Path(".claude/profiles")

        if not profiles_dir.exists():
            console.print("[yellow]No built-in profiles found[/yellow]")
            return

        table = Table(title="Available Profiles")
        table.add_column("Name", style="cyan")
        table.add_column("Description", style="white")
        table.add_column("URI", style="dim")

        for profile_file in sorted(profiles_dir.glob("*.yaml")):
            try:
                # Load and parse profile
                profile_name = profile_file.stem
                yaml_content = self.loader.load(profile_name)
                profile = self.parser.parse(yaml_content)

                table.add_row(profile.name, profile.description, profile_name)
            except Exception as e:
                table.add_row(profile_file.stem, f"[red]Error: {e}[/red]", profile_file.stem)

        console.print(table)

    def show_profile(self, uri: str | None = None):
        """Show details of a specific profile.

        Args:
            uri: Profile URI (if None, shows current profile)
        """
        if uri is None:
            uri = self.config.get_current_profile()

        try:
            # Load profile
            yaml_content = self.loader.load(uri)
            profile = self.parser.parse(yaml_content)

            # Create info panel
            info = f"""
[bold]Name:[/bold] {profile.name}
[bold]Description:[/bold] {profile.description}
[bold]Version:[/bold] {profile.version}
[bold]URI:[/bold] {uri}

[bold cyan]Components:[/bold cyan]
"""

            # Commands
            cmd_spec = profile.components.commands
            if cmd_spec.include_all:
                info += "  [bold]Commands:[/bold] All\n"
            elif cmd_spec.include:
                info += f"  [bold]Commands:[/bold] {', '.join(cmd_spec.include[:5])}"
                if len(cmd_spec.include) > 5:
                    info += f" ... ({len(cmd_spec.include)} total)"
                info += "\n"

            # Context
            ctx_spec = profile.components.context
            if ctx_spec.include_all:
                info += "  [bold]Context:[/bold] All\n"
            elif ctx_spec.include:
                info += f"  [bold]Context:[/bold] {', '.join(ctx_spec.include)}\n"

            # Agents
            agent_spec = profile.components.agents
            if agent_spec.include_all:
                info += "  [bold]Agents:[/bold] All\n"
            elif agent_spec.include:
                info += f"  [bold]Agents:[/bold] {', '.join(agent_spec.include[:5])}"
                if len(agent_spec.include) > 5:
                    info += f" ... ({len(agent_spec.include)} total)"
                info += "\n"

            # Skills
            skill_spec = profile.components.skills
            if skill_spec.include_all:
                info += "  [bold]Skills:[/bold] All\n"
            elif skill_spec.include_categories:
                info += f"  [bold]Skills (categories):[/bold] {', '.join(skill_spec.include_categories)}\n"
            elif skill_spec.include:
                info += f"  [bold]Skills:[/bold] {', '.join(skill_spec.include[:5])}"
                if len(skill_spec.include) > 5:
                    info += f" ... ({len(skill_spec.include)} total)"
                info += "\n"

            console.print(
                Panel(info.strip(), title=f"Profile: {profile.name}", border_style="cyan")
            )

            # Show token estimate if possible
            try:
                inventory = self.discovery.discover_all()
                filtered = self.filter.filter(profile, inventory)
                tokens = estimate_token_count(filtered)

                console.print(f"\n[dim]Estimated token usage: ~{tokens:,} tokens[/dim]")
                console.print(
                    f"[dim]Components: {len(filtered.commands)} commands, {len(filtered.context)} context, {len(filtered.agents)} agents, {len(filtered.skills)} skills[/dim]"
                )
            except Exception:
                pass

        except Exception as e:
            console.print(f"[red]Error loading profile: {e}[/red]")
            sys.exit(1)

    def switch_profile(self, uri: str):
        """Switch to a different profile.

        Args:
            uri: Profile URI to switch to
        """
        try:
            # Validate profile exists and is valid
            yaml_content = self.loader.load(uri)
            profile = self.parser.parse(yaml_content)

            # Save as current profile
            self.config.set_current_profile(uri)

            console.print(f"[green]✓[/green] Switched to profile: [cyan]{profile.name}[/cyan]")
            console.print(f"[dim]URI: {uri}[/dim]")
            console.print("\n[yellow]Note:[/yellow] Restart Claude Code for changes to take effect")

        except Exception as e:
            console.print(f"[red]Error switching profile: {e}[/red]")
            sys.exit(1)

    def current_profile(self):
        """Show currently active profile."""
        uri = self.config.get_current_profile()

        if self.config.is_env_override_active():
            console.print("[yellow]Profile set via AMPLIHACK_PROFILE environment variable[/yellow]")

        self.show_profile(uri)

    def validate_profile(self, uri: str):
        """Validate a profile.

        Args:
            uri: Profile URI to validate
        """
        try:
            # Load and parse
            yaml_content = self.loader.load(uri)
            profile = self.parser.parse(yaml_content)

            console.print(f"[green]✓[/green] Profile is valid: [cyan]{profile.name}[/cyan]")
            console.print(f"[dim]URI: {uri}[/dim]")

            # Show warnings if any
            if (
                not profile.components.commands.include_all
                and not profile.components.commands.include
            ):
                console.print("[yellow]⚠[/yellow] Warning: No commands specified")

            if not profile.components.agents.include_all and not profile.components.agents.include:
                console.print("[yellow]⚠[/yellow] Warning: No agents specified")

        except Exception as e:
            console.print(f"[red]✗[/red] Profile is invalid: {e}")
            sys.exit(1)


def main():
    """Main CLI entry point.

    Parses command-line arguments and dispatches to appropriate CLI method.
    """
    if len(sys.argv) < 2:
        console.print("[red]Usage:[/red] profile <command> [options]")
        console.print("\n[bold]Commands:[/bold]")
        console.print("  list              List available profiles")
        console.print("  show [uri]        Show profile details")
        console.print("  current           Show current profile")
        console.print("  switch <uri>      Switch to profile")
        console.print("  validate <uri>    Validate profile")
        sys.exit(1)

    cli = ProfileCLI()
    command = sys.argv[1]

    if command == "list":
        cli.list_profiles()
    elif command == "show":
        uri = sys.argv[2] if len(sys.argv) > 2 else None
        cli.show_profile(uri)
    elif command == "current":
        cli.current_profile()
    elif command == "switch":
        if len(sys.argv) < 3:
            console.print("[red]Error:[/red] Missing profile URI")
            sys.exit(1)
        cli.switch_profile(sys.argv[2])
    elif command == "validate":
        if len(sys.argv) < 3:
            console.print("[red]Error:[/red] Missing profile URI")
            sys.exit(1)
        cli.validate_profile(sys.argv[2])
    else:
        console.print(f"[red]Unknown command:[/red] {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
