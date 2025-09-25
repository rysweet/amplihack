"""
XPIA CLI Command Implementation

Command-line interface for testing XPIA validation.
"""

import asyncio
import json
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

sys.path.append("/Users/ryan/src/hackathon/MicrosoftHackathon2025-AgenticCoding-xpia-133/Specs")
sys.path.append("/Users/ryan/src/hackathon/MicrosoftHackathon2025-AgenticCoding-xpia-133/src")

from xpia_defense_interface import ContentType, RiskLevel

from amplihack.security.config import get_config
from amplihack.security.xpia_defender import WebFetchXPIADefender

console = Console()


@click.group()
def xpia():
    """XPIA Defense System CLI"""
    pass


@xpia.command()
@click.option("--url", required=True, help="URL to validate")
@click.option("--prompt", required=True, help="Prompt to validate")
@click.option(
    "--security-level",
    type=click.Choice(["STRICT", "HIGH", "MODERATE", "LENIENT", "LOW"], case_sensitive=False),
    default="MODERATE",
    help="Security level for validation",
)
@click.option("--verbose", is_flag=True, help="Show detailed output")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
def validate(url: str, prompt: str, security_level: str, verbose: bool, output_json: bool):
    """Validate a WebFetch request for security threats"""

    # Create config with specified security level
    config = get_config()
    config.security_level = security_level

    # Create defender
    defender = WebFetchXPIADefender(config.to_security_configuration())

    # Run validation
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(defender.validate_webfetch_request(url, prompt))

        if output_json:
            # JSON output
            output = {
                "valid": result.is_valid,
                "risk_level": result.risk_level.value,
                "threats": [
                    {
                        "type": t.threat_type.value,
                        "severity": t.severity.value,
                        "description": t.description,
                        "mitigation": t.mitigation,
                    }
                    for t in result.threats
                ],
                "recommendations": result.recommendations,
                "metadata": result.metadata,
            }
            click.echo(json.dumps(output, indent=2))
        else:
            # Rich console output
            _display_validation_result(result, url, prompt, verbose)

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)
    finally:
        loop.close()


@xpia.command()
@click.option("--command", required=True, help="Bash command to validate")
@click.option(
    "--security-level",
    type=click.Choice(["STRICT", "HIGH", "MODERATE", "LENIENT", "LOW"], case_sensitive=False),
    default="MODERATE",
    help="Security level for validation",
)
@click.option("--verbose", is_flag=True, help="Show detailed output")
def validate_bash(command: str, security_level: str, verbose: bool):
    """Validate a Bash command for security threats"""

    config = get_config()
    config.security_level = security_level

    defender = WebFetchXPIADefender(config.to_security_configuration())

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(defender.validate_bash_command(command))

        _display_bash_validation_result(result, command, verbose)

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)
    finally:
        loop.close()


@xpia.command()
@click.option("--text", required=True, help="Text content to validate")
@click.option(
    "--type",
    type=click.Choice(["text", "code", "command", "data", "user_input"], case_sensitive=False),
    default="user_input",
    help="Content type",
)
@click.option(
    "--security-level",
    type=click.Choice(["STRICT", "HIGH", "MODERATE", "LENIENT", "LOW"], case_sensitive=False),
    default="MODERATE",
    help="Security level for validation",
)
@click.option("--verbose", is_flag=True, help="Show detailed output")
def validate_content(text: str, type: str, security_level: str, verbose: bool):
    """Validate arbitrary content for security threats"""

    config = get_config()
    config.security_level = security_level

    defender = WebFetchXPIADefender(config.to_security_configuration())

    # Map type string to ContentType enum
    content_type_map = {
        "text": ContentType.TEXT,
        "code": ContentType.CODE,
        "command": ContentType.COMMAND,
        "data": ContentType.DATA,
        "user_input": ContentType.USER_INPUT,
    }
    content_type = content_type_map[type.lower()]

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(defender.validate_content(text, content_type))

        _display_content_validation_result(result, text[:100], type, verbose)

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)
    finally:
        loop.close()


@xpia.command()
def patterns():
    """List all attack patterns"""
    from amplihack.security.xpia_patterns import PatternCategory, XPIAPatterns

    patterns = XPIAPatterns()

    # Group patterns by category
    categories = {}
    for pattern in patterns.patterns.values():
        if pattern.category not in categories:
            categories[pattern.category] = []
        categories[pattern.category].append(pattern)

    # Display patterns by category
    for category in PatternCategory:
        if category in categories:
            console.print(f"\n[bold cyan]{category.value.replace('_', ' ').title()}[/bold cyan]")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("ID", style="dim", width=6)
            table.add_column("Name", width=30)
            table.add_column("Severity", width=10)
            table.add_column("Description", width=50)

            for pattern in categories[category]:
                severity_color = _get_severity_color(pattern.severity)
                table.add_row(
                    pattern.id,
                    pattern.name,
                    f"[{severity_color}]{pattern.severity}[/{severity_color}]",
                    pattern.description[:50] + "..."
                    if len(pattern.description) > 50
                    else pattern.description,
                )

            console.print(table)


@xpia.command()
def config():
    """Show current XPIA configuration"""
    config = get_config()

    panel = Panel.fit(
        f"""[bold]XPIA Defense Configuration[/bold]

[cyan]Status:[/cyan] {"[green]Enabled[/green]" if config.enabled else "[red]Disabled[/red]"}
[cyan]Security Level:[/cyan] {config.security_level}
[cyan]Verbose Feedback:[/cyan] {config.verbose_feedback}

[bold]Blocking Settings:[/bold]
  Block on High Risk: {config.block_on_high_risk}
  Block on Critical: {config.block_on_critical}

[bold]Validation Features:[/bold]
  WebFetch: {config.validate_webfetch}
  Bash: {config.validate_bash}
  Agents: {config.validate_agents}

[bold]Domain Lists:[/bold]
  Whitelist: {len(config.whitelist_domains)} domains
  Blacklist: {len(config.blacklist_domains)} domains

[bold]Limits:[/bold]
  Max Prompt Length: {config.max_prompt_length:,}
  Max URL Length: {config.max_url_length:,}
""",
        title="Configuration",
        border_style="blue",
    )

    console.print(panel)


@xpia.command()
def health():
    """Check XPIA system health"""
    config = get_config()
    defender = WebFetchXPIADefender(config.to_security_configuration())

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        health_status = loop.run_until_complete(defender.health_check())

        status_color = "green" if health_status["status"] == "healthy" else "red"

        panel = Panel.fit(
            f"""[bold]XPIA Defense System Health[/bold]

[cyan]Status:[/cyan] [{status_color}]{health_status["status"].upper()}[/{status_color}]
[cyan]Enabled:[/cyan] {health_status["enabled"]}
[cyan]Security Level:[/cyan] {health_status["security_level"]}

[bold]System Stats:[/bold]
  Patterns Loaded: {health_status["patterns_loaded"]}
  Whitelist Size: {health_status["whitelist_size"]}
  Blacklist Size: {health_status["blacklist_size"]}
  Events Logged: {health_status["events_logged"]}
""",
            title="Health Check",
            border_style="green" if health_status["status"] == "healthy" else "red",
        )

        console.print(panel)

    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")
        sys.exit(1)
    finally:
        loop.close()


def _display_validation_result(result, url: str, prompt: str, verbose: bool):
    """Display WebFetch validation result"""
    risk_color = _get_risk_color(result.risk_level)

    # Summary panel
    if result.is_valid:
        console.print(
            Panel(
                f"[green]✓ Request is SAFE to proceed[/green]\n"
                f"Risk Level: [{risk_color}]{result.risk_level.value}[/{risk_color}]",
                title="Validation Passed",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[red]✗ Request BLOCKED for security[/red]\n"
                f"Risk Level: [{risk_color}]{result.risk_level.value}[/{risk_color}]",
                title="Validation Failed",
                border_style="red",
            )
        )

    # Input details
    if verbose:
        console.print("\n[bold]Input Details:[/bold]")
        console.print(f"  URL: {url}")
        console.print(f"  Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")

    # Threats table
    if result.threats:
        console.print("\n[bold]Detected Threats:[/bold]")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Type", width=20)
        table.add_column("Severity", width=10)
        table.add_column("Description", width=50)
        if verbose:
            table.add_column("Mitigation", width=40)

        for threat in result.threats:
            severity_color = _get_risk_color(threat.severity)
            row = [
                threat.threat_type.value,
                f"[{severity_color}]{threat.severity.value}[/{severity_color}]",
                threat.description,
            ]
            if verbose and threat.mitigation:
                row.append(threat.mitigation)
            table.add_row(*row)

        console.print(table)

    # Recommendations
    if result.recommendations:
        console.print("\n[bold]Recommendations:[/bold]")
        for rec in result.recommendations:
            console.print(f"  • {rec}")


def _display_bash_validation_result(result, command: str, verbose: bool):
    """Display Bash validation result"""
    risk_color = _get_risk_color(result.risk_level)

    # Summary
    if result.is_valid:
        console.print(
            Panel(
                f"[green]✓ Command is SAFE to execute[/green]\n"
                f"Risk Level: [{risk_color}]{result.risk_level.value}[/{risk_color}]",
                title="Validation Passed",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                f"[red]✗ Command BLOCKED for security[/red]\n"
                f"Risk Level: [{risk_color}]{result.risk_level.value}[/{risk_color}]",
                title="Validation Failed",
                border_style="red",
            )
        )

    if verbose:
        console.print(f"\n[bold]Command:[/bold] {command}")

    # Show threats if any
    if result.threats:
        console.print("\n[bold]Security Issues:[/bold]")
        for threat in result.threats:
            severity_color = _get_risk_color(threat.severity)
            console.print(f"  [{severity_color}]•[/{severity_color}] {threat.description}")
            if verbose and threat.mitigation:
                console.print(f"    → {threat.mitigation}")


def _display_content_validation_result(
    result, content_preview: str, content_type: str, verbose: bool
):
    """Display content validation result"""
    risk_color = _get_risk_color(result.risk_level)

    # Summary
    console.print(
        Panel(
            f"Content Type: {content_type}\n"
            f"Risk Level: [{risk_color}]{result.risk_level.value}[/{risk_color}]\n"
            f"Status: {'[green]SAFE[/green]' if result.is_valid else '[red]UNSAFE[/red]'}",
            title="Content Validation Result",
            border_style="green" if result.is_valid else "red",
        )
    )

    if verbose:
        console.print(f"\n[bold]Content Preview:[/bold] {content_preview}...")

    # Show threats
    if result.threats:
        console.print("\n[bold]Detected Patterns:[/bold]")
        for threat in result.threats:
            severity_color = _get_risk_color(threat.severity)
            console.print(f"  [{severity_color}]•[/{severity_color}] {threat.description}")


def _get_risk_color(risk_level: RiskLevel) -> str:
    """Get color for risk level"""
    colors = {
        RiskLevel.NONE: "green",
        RiskLevel.LOW: "yellow",
        RiskLevel.MEDIUM: "orange3",
        RiskLevel.HIGH: "red",
        RiskLevel.CRITICAL: "red bold",
    }
    return colors.get(risk_level, "white")


def _get_severity_color(severity: str) -> str:
    """Get color for severity string"""
    colors = {"low": "yellow", "medium": "orange3", "high": "red", "critical": "red bold"}
    return colors.get(severity.lower(), "white")


if __name__ == "__main__":
    xpia()
