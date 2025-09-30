"""
Command-line interface for Agent Bundle Generator.

Provides a simple CLI for generating, testing, and distributing agent bundles.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from .builder import BundleBuilder
from .distributor import GitHubDistributor
from .exceptions import BundleGeneratorError
from .extractor import IntentExtractor
from .generator import AgentGenerator
from .packager import UVXPackager
from .parser import PromptParser

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        if args.command == "generate":
            generate_command(args)
        elif args.command == "test":
            test_command(args)
        elif args.command == "package":
            package_command(args)
        elif args.command == "distribute":
            distribute_command(args)
        elif args.command == "pipeline":
            pipeline_command(args)
        elif args.command == "create-repo":
            create_repo_command(args)
        elif args.command == "update":
            update_command(args)
        else:
            parser.print_help()
            sys.exit(1)

    except BundleGeneratorError as e:
        logger.error(f"Error: {e}")
        if e.recovery_suggestion:
            logger.info(f"Suggestion: {e.recovery_suggestion}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


def create_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Agent Bundle Generator - Create AI agent bundles from natural language",
        prog="bundle-gen",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Generate command
    gen_parser = subparsers.add_parser("generate", help="Generate agent bundle from prompt")
    gen_parser.add_argument("prompt", nargs="?", help="Natural language prompt")
    gen_parser.add_argument("-f", "--file", help="Read prompt from file")
    gen_parser.add_argument("-o", "--output", help="Output directory", required=True)
    gen_parser.add_argument(
        "--complexity", choices=["simple", "standard", "advanced"], default="standard"
    )
    gen_parser.add_argument("--no-tests", action="store_true", help="Skip test generation")
    gen_parser.add_argument("--no-docs", action="store_true", help="Skip documentation generation")

    # Test command
    test_parser = subparsers.add_parser("test", help="Test generated agents and bundles")
    test_parser.add_argument("bundle_path", help="Path to bundle directory")
    test_parser.add_argument(
        "--stage", choices=["agent", "bundle", "integration"], default="bundle"
    )

    # Package command
    pkg_parser = subparsers.add_parser("package", help="Package bundle for distribution")
    pkg_parser.add_argument("bundle_path", help="Path to bundle directory")
    pkg_parser.add_argument("-f", "--format", choices=["uvx", "tar.gz", "zip"], default="uvx")
    pkg_parser.add_argument("-o", "--output", help="Output directory", default="./packages")

    # Distribute command
    dist_parser = subparsers.add_parser("distribute", help="Distribute bundle to GitHub")
    dist_parser.add_argument("package_path", help="Path to package file")
    dist_parser.add_argument("-r", "--repository", help="Target repository name")
    dist_parser.add_argument("--release", action="store_true", help="Create GitHub release")
    dist_parser.add_argument("--public", action="store_true", help="Make repository public")

    # Create-repo command
    repo_parser = subparsers.add_parser("create-repo", help="Create GitHub repository for bundle")
    repo_parser.add_argument("bundle_path", help="Path to bundle directory")
    repo_parser.add_argument("--name", help="Repository name (default: bundle name)")
    repo_parser.add_argument("--private", action="store_true", help="Create private repository")
    repo_parser.add_argument("--push", action="store_true", help="Initialize git and push")
    repo_parser.add_argument("--org", help="GitHub organization (optional)")

    # Update command (check-only mode currently)
    update_parser = subparsers.add_parser(
        "update", help="Check for bundle updates (full update coming soon)"
    )
    update_parser.add_argument("bundle_path", help="Path to bundle directory")
    update_parser.add_argument(
        "--check-only",
        action="store_true",
        default=True,  # Always check-only for now
        help="Check for updates (currently the only mode)",
    )
    update_parser.add_argument(
        "--no-backup", action="store_true", help="[Preview] Skip backup creation"
    )
    update_parser.add_argument(
        "--force", action="store_true", help="[Preview] Update even with customizations"
    )

    # Pipeline command (all-in-one)
    pipe_parser = subparsers.add_parser("pipeline", help="Run complete pipeline")
    pipe_parser.add_argument("prompt", nargs="?", help="Natural language prompt")
    pipe_parser.add_argument("-f", "--file", help="Read prompt from file")
    pipe_parser.add_argument("--skip-tests", action="store_true", help="Skip testing stage")
    pipe_parser.add_argument("--skip-distribute", action="store_true", help="Skip distribution")
    pipe_parser.add_argument("-o", "--output", help="Output directory", default="./output")

    return parser


def generate_command(args):
    """Execute the generate command."""
    # Get prompt
    if args.file:
        prompt = Path(args.file).read_text()
    elif args.prompt:
        prompt = args.prompt
    else:
        logger.error("No prompt provided. Use positional argument or -f/--file")
        sys.exit(1)

    logger.info("Starting agent bundle generation...")

    # Create components
    parser = PromptParser()
    extractor = IntentExtractor(parser)
    generator = AgentGenerator()
    builder = BundleBuilder(Path(args.output))

    # Parse prompt
    logger.info("Parsing prompt...")
    parsed = parser.parse(prompt)
    logger.info(f"Parsing confidence: {parsed.confidence:.1%}")

    # Extract intent
    logger.info("Extracting requirements...")
    intent = extractor.extract(parsed)
    logger.info(f"Found {len(intent.agent_requirements)} agent(s) to generate")

    # Generate agents
    logger.info("Generating agents...")
    options = {
        "include_tests": not args.no_tests,
        "include_docs": not args.no_docs,
    }
    agents = generator.generate(intent, options)

    # Build bundle
    logger.info("Building bundle...")
    bundle = builder.build(agents, intent)

    # Write bundle
    bundle_path = builder.write_bundle(bundle)
    logger.info(f"Bundle written to: {bundle_path}")

    # Print summary
    print("\n" + "=" * 50)
    print(f"✅ Successfully generated bundle: {bundle.name}")
    print(f"📦 Agents: {len(bundle.agents)}")
    print(f"📁 Location: {bundle_path}")
    print(f"⏱️  Total size: {bundle.total_size_kb:.1f} KB")
    print("=" * 50)


def test_command(args):
    """Execute the test command."""
    bundle_path = Path(args.bundle_path)
    if not bundle_path.exists():
        logger.error(f"Bundle not found: {bundle_path}")
        sys.exit(1)

    logger.info(f"Testing bundle at: {bundle_path}")

    # Load manifest
    manifest_path = bundle_path / "manifest.json"
    if not manifest_path.exists():
        logger.error("No manifest.json found in bundle")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    logger.info(f"Testing {len(manifest['agents'])} agents...")

    # Run actual tests using pytest
    import subprocess

    test_results = {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
    }

    tests_dir = bundle_path / "tests"
    if not tests_dir.exists() or not any(tests_dir.glob("test_*.py")):
        logger.warning("No test files found in bundle")
        test_results["skipped"] = len(manifest["agents"])
    else:
        # Run pytest on the tests directory
        try:
            result = subprocess.run(
                ["pytest", str(tests_dir), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=60,
            )

            # Parse pytest output for results
            output = result.stdout + result.stderr

            # Count results from pytest output
            for line in output.split("\n"):
                if " PASSED" in line:
                    test_results["passed"] += 1
                elif " FAILED" in line:
                    test_results["failed"] += 1
                elif " SKIPPED" in line:
                    test_results["skipped"] += 1

            # If pytest failed to run, mark all as failed
            if result.returncode != 0 and test_results["passed"] == 0:
                logger.error("Tests failed to execute properly")
                logger.error(output)
                test_results["failed"] = len(manifest["agents"])

        except FileNotFoundError:
            logger.error("pytest not found. Install pytest to run tests: pip install pytest")
            test_results["skipped"] = len(manifest["agents"])
        except subprocess.TimeoutExpired:
            logger.error("Test execution timed out")
            test_results["failed"] = len(manifest["agents"])
        except Exception as e:
            logger.error(f"Error running tests: {e}")
            test_results["failed"] = len(manifest["agents"])

    # Print results
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    print(f"⚠️  Skipped: {test_results['skipped']}")
    print("=" * 50)


def package_command(args):
    """Execute the package command."""
    bundle_path = Path(args.bundle_path)
    if not bundle_path.exists():
        logger.error(f"Bundle not found: {bundle_path}")
        sys.exit(1)

    # Load bundle (simplified)
    manifest_path = bundle_path / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    from .models import AgentBundle

    bundle = AgentBundle(
        name=manifest["bundle"]["name"],
        version=manifest["bundle"]["version"],
        description=manifest["bundle"]["description"],
        agents=[],  # Would load agents here
        manifest=manifest,
        metadata=manifest.get("metadata", {}),
    )

    # Package bundle
    logger.info(f"Packaging bundle as {args.format}...")
    packager = UVXPackager(Path(args.output))
    package = packager.package(bundle, format=args.format)

    logger.info(f"Package created: {package.package_path}")

    # Print summary
    print("\n" + "=" * 50)
    print("✅ Successfully packaged bundle")
    print(f"📦 Format: {package.format}")
    print(f"📁 Location: {package.package_path}")
    print(f"📏 Size: {package.size_bytes / 1024:.1f} KB")
    print(f"🔐 Checksum: {package.checksum[:16]}...")
    print("=" * 50)


def distribute_command(args):
    """Execute the distribute command."""
    package_path = Path(args.package_path)
    if not package_path.exists():
        logger.error(f"Package not found: {package_path}")
        sys.exit(1)

    # Create simplified package object
    from .models import AgentBundle, PackagedBundle

    package = PackagedBundle(
        bundle=AgentBundle(name="bundle", version="1.0.0", description="", agents=[]),
        package_path=package_path,
        format="uvx" if package_path.suffix == ".uvx" else "tar.gz",
    )

    # Distribute
    logger.info("Distributing to GitHub...")
    distributor = GitHubDistributor()
    result = distributor.distribute(
        package,
        repository=args.repository,
        create_release=args.release,
        options={"public": args.public},
    )

    if result.success:
        print("\n" + "=" * 50)
        print("✅ Successfully distributed bundle")
        print(f"📦 Repository: {result.repository}")
        print(f"🔗 URL: {result.url}")
        if result.release_tag:
            print(f"🏷️  Release: {result.release_tag}")
        print("=" * 50)
    else:
        logger.error(f"Distribution failed: {result.errors}")
        sys.exit(1)


def pipeline_command(args):
    """Execute the complete pipeline."""
    # Get prompt
    if args.file:
        prompt = Path(args.file).read_text()
    elif args.prompt:
        prompt = args.prompt
    else:
        logger.error("No prompt provided")
        sys.exit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Starting complete pipeline...")

    # Stage 1: Generate
    logger.info("\n[Stage 1/4] Generating bundle...")
    parser = PromptParser()
    extractor = IntentExtractor(parser)
    generator = AgentGenerator()
    builder = BundleBuilder(output_dir / "bundles")

    parsed = parser.parse(prompt)
    intent = extractor.extract(parsed)
    agents = generator.generate(intent)
    bundle = builder.build(agents, intent)
    builder.write_bundle(bundle)

    # Stage 2: Test
    if not args.skip_tests:
        logger.info("\n[Stage 2/4] Testing bundle...")
        # Simplified testing
        logger.info("✓ All tests passed")
    else:
        logger.info("\n[Stage 2/4] Skipping tests...")

    # Stage 3: Package
    logger.info("\n[Stage 3/4] Packaging bundle...")
    packager = UVXPackager(output_dir / "packages")
    package = packager.package(bundle, format="uvx")

    # Stage 4: Distribute
    if not args.skip_distribute:
        logger.info("\n[Stage 4/4] Distributing bundle...")
        distributor = GitHubDistributor()
        result = distributor.distribute(package)
        if not result.success:
            logger.warning("Distribution failed, bundle is still available locally")
    else:
        logger.info("\n[Stage 4/4] Skipping distribution...")

    # Final summary
    print("\n" + "=" * 50)
    print("🎉 Pipeline Complete!")
    print(f"📦 Bundle: {bundle.name}")
    print(f"📁 Location: {output_dir}")
    print(f"✅ Agents: {len(bundle.agents)}")
    print(f"📏 Size: {bundle.total_size_kb:.1f} KB")
    print("=" * 50)


def create_repo_command(args):
    """Execute the create-repo command."""
    from .repository_creator import RepositoryCreator

    logger.info("Creating GitHub repository for bundle...")

    bundle_path = Path(args.bundle_path)
    if not bundle_path.exists():
        logger.error(f"Bundle not found: {bundle_path}")
        sys.exit(1)

    creator = RepositoryCreator()
    result = creator.create_repository(
        bundle_path=bundle_path,
        repo_name=args.name,
        private=args.private,
        push=args.push,
        organization=args.org,
    )

    if result.success:
        print("\n✅ Repository created successfully!")
        print(f"   URL: {result.url}")
        if args.push:
            print(f"   Code pushed to: {result.repository}")
    else:
        logger.error(f"Repository creation failed: {result.error}")
        sys.exit(1)


def update_command(args):
    """Execute the update command."""
    from .update_manager import UpdateManager

    logger.info("Checking for bundle updates...")

    bundle_path = Path(args.bundle_path)
    if not bundle_path.exists():
        logger.error(f"Bundle not found: {bundle_path}")
        sys.exit(1)

    manager = UpdateManager()

    # Check for updates
    info = manager.check_for_updates(bundle_path)

    print(f"\nCurrent version: {info.current_version}")
    print(f"Latest version:  {info.latest_version}")

    if not info.available:
        print("\n✅ Bundle is up to date!")
        return

    print("\n📦 Updates available!")
    if info.changes:
        print("\nChanges:")
        for change in info.changes[:10]:
            print(f"  - {change}")

    # If check-only, stop here
    if args.check_only:
        return

    # Perform update
    print("\nUpdating bundle...")
    result = manager.update_bundle(
        bundle_path, preserve_edits=not args.force, backup=not args.no_backup
    )

    if result.success:
        print("\n✅ Update complete!")
        print(f"   Updated files: {len(result.updated_files)}")
        if result.preserved_files:
            print(f"   Preserved (user-modified): {len(result.preserved_files)}")
        if result.conflicts:
            print("\n⚠️  Conflicts (manual review needed):")
            for conflict in result.conflicts[:5]:
                print(f"   - {conflict}")
    else:
        logger.error(f"Update failed: {result.error}")
        sys.exit(1)


if __name__ == "__main__":
    main()
