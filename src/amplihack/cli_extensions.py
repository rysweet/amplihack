"""CLI extensions for amplihack to support bundle generation."""

from pathlib import Path
from typing import Optional

import click

from .bundle_generator import (
    AgentGenerator,
    BundleBuilder,
    BundleDistributor,
    BundleGeneratorError,
    BundlePackager,
    IntentExtractor,
    PromptParser,
)
from .bundle_generator.models import DistributionMethod, PackageFormat


@click.group()
def bundle():
    """Agent Bundle Generator commands."""


@bundle.command()
@click.argument("prompt")
@click.option("--output", "-o", type=click.Path(), default="./bundles", help="Output directory")
@click.option("--validate", is_flag=True, help="Validate generated bundle")
@click.option("--test", is_flag=True, help="Test agent before bundling")
def generate(prompt: str, output: str, validate: bool, test: bool):
    """Generate an agent bundle from a natural language prompt."""
    try:
        output_path = Path(output)
        output_path.mkdir(parents=True, exist_ok=True)

        click.echo(f"📦 Generating agent bundle from: '{prompt}'")

        # Parse prompt
        parser = PromptParser()
        parsed = parser.parse(prompt)
        click.echo(f"✅ Parsed prompt (confidence: {parsed.confidence:.2f})")

        # Extract intent
        extractor = IntentExtractor(parser)
        intent = extractor.extract(parsed)
        click.echo(f"✅ Extracted intent: {intent.action} {intent.domain}")

        # Test agent if requested
        if test:
            click.echo("🧪 Testing agent before bundling...")
            click.echo("⚠️  Agent testing not implemented - skipping validation")
            click.echo("✅ Agent tests skipped (no implementation)")

        # Generate agents
        generator = AgentGenerator()
        agents = generator.generate(intent)
        click.echo(f"✅ Generated {len(agents)} agent(s)")

        # Build bundle
        builder = BundleBuilder()
        bundle = builder.build(agents, intent)

        # Validate if requested
        if validate:
            click.echo("🔍 Validating bundle...")
            builder.validate_bundle(bundle)
            click.echo("✅ Bundle validation passed")

        # Write bundle
        bundle_path = builder.write_bundle(bundle, output_path)
        click.echo(f"✅ Bundle written to: {bundle_path}")

        click.echo("🎉 Bundle generation complete!")
        return bundle_path

    except BundleGeneratorError as e:
        click.echo(f"❌ Error: {e}", err=True)
        if e.recovery_suggestion:
            click.echo(f"💡 Suggestion: {e.recovery_suggestion}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        raise click.Abort()


@bundle.command()
@click.argument("bundle_path", type=click.Path(exists=True))
@click.option(
    "--format",
    "-f",
    type=click.Choice(["tar.gz", "zip", "directory", "uvx"]),
    default="uvx",
    help="Package format",
)
@click.option("--output", "-o", type=click.Path(), help="Output path")
def package(bundle_path: str, format: str, output: Optional[str]):
    """Package a bundle for distribution."""
    try:
        bundle_path = Path(bundle_path)
        format_enum = PackageFormat[format.replace(".", "_").upper()]

        click.echo(f"📦 Packaging bundle: {bundle_path}")

        packager = BundlePackager()
        package_path = packager.package(bundle_path, format_enum, Path(output) if output else None)

        click.echo(f"✅ Package created: {package_path}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@bundle.command()
@click.argument("package_path", type=click.Path(exists=True))
@click.option("--github", is_flag=True, help="Distribute to GitHub")
@click.option("--pypi", is_flag=True, help="Distribute to PyPI")
@click.option("--local", is_flag=True, help="Distribute locally")
@click.option("--release", is_flag=True, help="Create a release")
def distribute(package_path: str, github: bool, pypi: bool, local: bool, release: bool) -> None:
    """Distribute a package."""
    try:
        package_path = Path(package_path)

        if not any([github, pypi, local]):
            github = True  # Default to GitHub

        distributor = BundleDistributor()

        if github:
            click.echo("🚀 Distributing to GitHub...")
            method = DistributionMethod.GITHUB_RELEASE if release else DistributionMethod.GITHUB
            url = distributor.distribute(package_path, method)
            click.echo(f"✅ Published to: {url}")

        if pypi:
            click.echo("📦 Distributing to PyPI...")
            url = distributor.distribute(package_path, DistributionMethod.PYPI)
            click.echo(f"✅ Published to: {url}")

        if local:
            click.echo("💾 Distributing locally...")
            url = distributor.distribute(package_path, DistributionMethod.LOCAL)
            click.echo(f"✅ Saved to: {url}")

    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()


@bundle.command()
@click.argument("prompt")
@click.option("--output", "-o", type=click.Path(), default="./output", help="Output directory")
@click.option(
    "--format", "-f", type=click.Choice(["uvx", "zip"]), default="uvx", help="Package format"
)
@click.option("--distribute", "-d", is_flag=True, help="Distribute after packaging")
def pipeline(prompt: str, output: str, format: str, distribute: bool):
    """Run the complete bundle generation pipeline."""
    try:
        output_path = Path(output)
        format_enum = PackageFormat.UVX if format == "uvx" else PackageFormat.ZIP

        click.echo(f"🚀 Running complete pipeline for: '{prompt}'")
        click.echo("=" * 60)

        # Generate bundle
        ctx = click.get_current_context()
        bundle_path = ctx.invoke(
            generate, prompt=prompt, output=str(output_path / "bundles"), validate=True, test=True
        )

        # Package bundle
        click.echo("\n📦 Packaging bundle...")
        packager = BundlePackager()
        package_path = packager.package(Path(bundle_path), format_enum, output_path / "packages")
        click.echo(f"✅ Packaged to: {package_path}")

        # Distribute if requested
        if distribute:
            click.echo("\n🌐 Distributing bundle...")
            distributor = BundleDistributor()
            url = distributor.distribute(package_path, DistributionMethod.GITHUB_RELEASE)
            click.echo(f"✅ Published to: {url}")

        click.echo("\n🎉 Pipeline complete!")
        click.echo(f"📁 Bundle: {bundle_path}")
        click.echo(f"📦 Package: {package_path}")
        if distribute:
            click.echo(f"🌐 URL: {url}")

    except Exception as e:
        click.echo(f"❌ Pipeline failed: {e}", err=True)
        raise click.Abort()


def register_cli_extensions(cli):
    """Register bundle generator commands with the main CLI."""
    cli.add_command(bundle)
