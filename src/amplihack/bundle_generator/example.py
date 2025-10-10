"""
Example usage of the Agent Bundle Generator.

This script demonstrates the complete workflow from prompt to distributed bundle.
"""

from pathlib import Path

from .builder import BundleBuilder
from .distributor import GitHubDistributor
from .extractor import IntentExtractor
from .generator import AgentGenerator
from .packager import UVXPackager
from .parser import PromptParser


def example_simple_generation():
    """Example: Generate a simple agent bundle."""
    print("=" * 60)
    print("Example 1: Simple Agent Generation")
    print("=" * 60)

    # Natural language prompt
    prompt = """
    Create a data validation agent that checks JSON schemas and
    reports errors with detailed feedback. It should validate
    structure, data types, and required fields.
    """

    # Initialize components
    parser = PromptParser()
    extractor = IntentExtractor(parser)
    generator = AgentGenerator()
    builder = BundleBuilder()

    # Parse and extract
    parsed = parser.parse(prompt)
    print(f"\n✓ Parsed prompt (confidence: {parsed.confidence:.1%})")
    print(f"  - Sentences: {len(parsed.sentences)}")
    print(f"  - Key phrases: {parsed.key_phrases[:3]}")

    intent = extractor.extract(parsed)
    print("\n✓ Extracted intent")
    print(f"  - Action: {intent.action}")
    print(f"  - Domain: {intent.domain}")
    print(f"  - Complexity: {intent.complexity}")
    print(f"  - Agents: {len(intent.agent_requirements)}")

    # Generate agents
    agents = generator.generate(intent)
    print(f"\n✓ Generated {len(agents)} agent(s)")
    for agent in agents:
        print(f"  - {agent.name}: {agent.role} ({agent.file_size_kb:.1f} KB)")

    # Build bundle
    bundle = builder.build(agents, intent, name="json_validator_bundle")
    print(f"\n✓ Built bundle: {bundle.name}")
    print(f"  - Version: {bundle.version}")
    print(f"  - Total size: {bundle.total_size_kb:.1f} KB")

    # Write to disk
    bundle_path = builder.write_bundle(bundle)
    print(f"\n✓ Bundle written to: {bundle_path}")

    return bundle


def example_multi_agent_bundle():
    """Example: Generate a multi-agent bundle."""
    print("\n" + "=" * 60)
    print("Example 2: Multi-Agent Bundle Generation")
    print("=" * 60)

    prompt = """
    Create a comprehensive security analysis suite with the following agents:

    1. Vulnerability Scanner Agent - Scans code for security vulnerabilities
    2. Dependency Audit Agent - Checks dependencies for known CVEs
    3. Configuration Validator Agent - Validates security configurations
    4. Report Generator Agent - Creates detailed security reports

    All agents should work together to provide complete security coverage.
    """

    # Initialize components
    parser = PromptParser()
    extractor = IntentExtractor(parser)
    generator = AgentGenerator()
    builder = BundleBuilder()
    packager = UVXPackager()

    # Generate bundle
    parsed = parser.parse(prompt)
    intent = extractor.extract(parsed)

    print(f"\n✓ Detected {len(intent.agent_requirements)} agents to generate:")
    for req in intent.agent_requirements:
        print(f"  - {req.name}: {req.purpose}")

    agents = generator.generate(intent, {"include_tests": True, "include_docs": True})
    bundle = builder.build(agents, intent, name="security_suite")

    print(f"\n✓ Generated bundle with {len(bundle.agents)} agents")

    # Package for distribution
    package = packager.package(bundle, format="uvx")
    print("\n✓ Packaged bundle:")
    print(f"  - Format: {package.format}")
    print(f"  - Size: {package.size_bytes / 1024:.1f} KB")
    print(f"  - Path: {package.package_path}")

    return package


def example_complete_pipeline():
    """Example: Complete pipeline from prompt to distribution."""
    print("\n" + "=" * 60)
    print("Example 3: Complete Pipeline")
    print("=" * 60)

    prompt = """
    Create a performance monitoring agent that tracks application metrics,
    identifies bottlenecks, and provides optimization suggestions.
    It should monitor CPU, memory, and I/O operations.
    """

    try:
        # Initialize all components
        parser = PromptParser()
        extractor = IntentExtractor(parser)
        generator = AgentGenerator()
        builder = BundleBuilder()
        packager = UVXPackager()
        GitHubDistributor()

        # Stage 1: Parse and Extract
        print("\n[Stage 1] Parsing and extracting requirements...")
        parsed = parser.parse(prompt)
        intent = extractor.extract(parsed)
        print(f"✓ Extracted {intent.action} request in {intent.domain} domain")

        # Stage 2: Generate Agents
        print("\n[Stage 2] Generating agents...")
        agents = generator.generate(intent)
        print(f"✓ Generated {len(agents)} agent(s)")

        # Stage 3: Build Bundle
        print("\n[Stage 3] Building bundle...")
        bundle = builder.build(agents, intent)
        bundle_path = builder.write_bundle(bundle)
        print(f"✓ Bundle written to: {bundle_path}")

        # Stage 4: Test (simplified)
        print("\n[Stage 4] Testing bundle...")
        issues = builder.validate_bundle(bundle)
        if issues:
            print(f"⚠ Validation issues: {issues}")
        else:
            print("✓ Bundle validation passed")

        # Stage 5: Package
        print("\n[Stage 5] Packaging for distribution...")
        package = packager.package(bundle, format="uvx")
        print(f"✓ Created {package.format} package: {package.package_path}")

        # Stage 6: Distribute (optional)
        print("\n[Stage 6] Distribution (simulated)...")
        print("✓ Ready for distribution to GitHub/PyPI")
        # Actual distribution would require credentials:
        # result = distributor.distribute(package, repository="my-agent-bundle")

        print("\n" + "=" * 60)
        print("🎉 Pipeline Complete!")
        print(f"Bundle: {bundle.name}")
        print(f"Agents: {len(bundle.agents)}")
        print(f"Package: {package.package_path}")
        print("=" * 60)

        return bundle, package

    except Exception as e:
        print(f"\n❌ Pipeline failed: {e}")
        return None, None


def example_test_existing_bundle():
    """Example: Test an existing bundle."""
    print("\n" + "=" * 60)
    print("Example 4: Testing Existing Bundle")
    print("=" * 60)

    # Assume we have a bundle at this path
    bundle_path = Path("./bundles/json_validator_bundle")

    if not bundle_path.exists():
        print("⚠ No existing bundle found. Run example_simple_generation() first.")
        return

    # Load and validate bundle
    builder = BundleBuilder()

    # Load manifest
    import json

    manifest_path = bundle_path / "manifest.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    print(f"✓ Loaded bundle: {manifest['bundle']['name']}")
    print(f"  Agents: {len(manifest['agents'])}")

    # Validate structure
    from .models import AgentBundle

    bundle = AgentBundle(
        name=manifest["bundle"]["name"],
        version=manifest["bundle"]["version"],
        description=manifest["bundle"]["description"],
        agents=[],  # Would load actual agents here
        manifest=manifest,
    )

    issues = builder.validate_bundle(bundle)
    if issues:
        print("\n⚠ Validation issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✅ Bundle validation passed!")


def main():
    """Run all examples."""
    print("Agent Bundle Generator - Examples")
    print("=" * 60)

    # Example 1: Simple generation
    bundle = example_simple_generation()

    # Example 2: Multi-agent bundle
    package = example_multi_agent_bundle()

    # Example 3: Complete pipeline
    bundle, package = example_complete_pipeline()

    # Example 4: Test existing bundle
    example_test_existing_bundle()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("Check the ./bundles and ./packages directories for output.")
    print("=" * 60)


if __name__ == "__main__":
    main()
