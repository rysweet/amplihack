# File: src/amplihack/tools/supply_chain_audit/cli.py
"""Click CLI for supply chain audit tool.

Commands: audit, list-advisories, validate-config
"""

from __future__ import annotations

import json
import logging
import sys

import click

logger = logging.getLogger(__name__)

from .advisories import get_advisory, list_advisories, validate_advisory_yaml
from .analyzer import Analyzer
from .github_client import GitHubClient
from .report import generate_json_report, generate_text_report, write_report


@click.group(invoke_without_command=True)
@click.pass_context
def supply_chain_audit(ctx: click.Context) -> None:
    """Supply chain audit — analyze repos for known supply chain incidents."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@supply_chain_audit.command()
@click.argument("advisory_id")
@click.option("--repos", default=None, help="Comma-separated list of repos (owner/repo)")
@click.option("--org", default=None, help="GitHub organization to scan all repos")
@click.option(
    "--format", "fmt", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.option("--output", "output_file", default=None, help="Write report to file")
@click.option("--config", default=None, help="Custom advisory YAML config path")
@click.option("--max-runs", default=100, type=int, help="Max workflow runs per repo")
def audit(
    advisory_id: str,
    repos: str | None,
    org: str | None,
    fmt: str,
    output_file: str | None,
    config: str | None,
    max_runs: int,
) -> None:
    """Audit repos against a known supply chain advisory."""
    # Validate repo/org args
    if repos and org:
        click.echo("Error: Specify --repos or --org, not both.", err=True)
        sys.exit(1)
    if not repos and not org:
        click.echo("Error: Specify --repos or --org to identify target repos.", err=True)
        sys.exit(1)

    # Resolve advisory
    advisory = get_advisory(advisory_id)
    if advisory is None and config:
        from .advisories import load_custom_advisories

        try:
            custom = load_custom_advisories(config)
            for a in custom:
                if a.id == advisory_id:
                    advisory = a
                    break
        except Exception as e:
            logger.warning("Failed to load custom advisories from %s: %s", config, e)

    if advisory is None:
        click.echo(f"Error: Unknown advisory ID: {advisory_id}", err=True)
        sys.exit(1)

    # Build repo list
    client = GitHubClient()
    analyzer = Analyzer(github_client=client)

    if org:
        try:
            repo_list = client.list_org_repos(org)
        except RuntimeError as e:
            click.echo(f"Error listing org repos: {e}", err=True)
            sys.exit(1)
    else:
        assert repos is not None  # guaranteed by earlier validation
        repo_list = [r.strip() for r in repos.split(",") if r.strip()]

    if not repo_list:
        click.echo("Error: No repos to audit.", err=True)
        sys.exit(1)

    # Run audit
    report = analyzer.audit(
        advisory=advisory,
        repos=repo_list,
        max_runs=max_runs,
    )

    # Output
    if fmt == "json":
        output = generate_json_report(report)
    else:
        output = generate_text_report(report)

    if output_file:
        write_report(report, output_file, fmt)
    else:
        click.echo(output)

    # Exit code based on verdict
    if report.has_compromised():
        sys.exit(1)
    elif report.has_inconclusive():
        sys.exit(2)
    sys.exit(0)


@supply_chain_audit.command("list-advisories")
@click.option(
    "--format", "fmt", type=click.Choice(["text", "json"]), default="text", help="Output format"
)
@click.option("--config", default=None, help="Custom advisory YAML config path")
def list_advisories_cmd(fmt: str, config: str | None) -> None:
    """List all known supply chain advisories."""
    advisories = list_advisories(config=config)

    if fmt == "json":
        data = [
            {
                "id": a.id,
                "title": a.title,
                "attack_vector": a.attack_vector,
                "package_name": a.package_name,
                "exposure_window_start": a.exposure_window_start.isoformat(),
                "exposure_window_end": a.exposure_window_end.isoformat(),
                "compromised_versions": a.compromised_versions,
            }
            for a in advisories
        ]
        click.echo(json.dumps(data, indent=2))
    else:
        for a in advisories:
            click.echo(
                f"{a.id}: {a.title}\n"
                f"  Vector: {a.attack_vector} | Package: {a.package_name}\n"
                f"  Window: {a.exposure_window_start.isoformat()} — "
                f"{a.exposure_window_end.isoformat()}\n"
                f"  Compromised: {', '.join(a.compromised_versions)}\n"
            )


@supply_chain_audit.command("validate-config")
@click.argument("config_path")
def validate_config_cmd(config_path: str) -> None:
    """Validate a custom advisory YAML config file."""
    errors = validate_advisory_yaml(config_path)
    if errors:
        click.echo("Validation errors:", err=True)
        for err in errors:
            click.echo(f"  - {err}", err=True)
        sys.exit(1)
    else:
        click.echo("Config is valid.")
        sys.exit(0)
