#!/usr/bin/env python
"""Demo script for the Agent Bundle Generator."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.bundle_generator import (
    AgentGenerator,
    BundleBuilder,
    IntentExtractor,
    PromptParser,
    UVXPackager,
)


def main():
    """Run the bundle generator demo."""
    print("\n🚀 Agent Bundle Generator Demo\n")
    print("=" * 50)

    # Example prompts
    prompts = [
        "Create a monitoring agent that tracks API performance and sends alerts",
        "Build a data validation agent for JSON and XML formats",
        "Generate a code analysis agent that finds security vulnerabilities",
        "Make an agent for automated testing of REST APIs",
    ]

    # Initialize components
    parser = PromptParser()
    extractor = IntentExtractor()
    generator = AgentGenerator()
    builder = BundleBuilder()
    packager = UVXPackager()

    for i, prompt in enumerate(prompts, 1):
        print(f"\nExample {i}: {prompt}")
        print("-" * 50)

        try:
            # Parse the prompt
            parsed = parser.parse(prompt)
            print(f"   Parsed: {len(parsed.tokens)} tokens, confidence: {parsed.confidence:.1%}")

            # Extract intent
            intent = extractor.extract(parsed)
            print(f"   Intent: {intent.action} {intent.domain} ({intent.complexity})")

            # Generate agents
            agents = generator.generate(intent)
            print(f"   Generated: {len(agents)} agent(s)")

            # Build bundle
            bundle = builder.build(agents, intent)
            bundle_dir = builder.write_bundle(bundle)
            print(f"✅ Bundle created: {bundle.name}")
            print(f"   - Output: {bundle_dir}")

            # Package for UVX
            package = packager.package(bundle)
            print(f"   - Package: {package.package_path}")
            print(f"   - Format: {package.format}")
            print(f"   - Size: {package.size_bytes / 1024:.1f} KB")

        except Exception as e:
            print(f"❌ Error: {e.__class__.__name__}: {str(e)[:100]}...")

    print("\n" + "=" * 50)
    print("Demo complete! Check the 'output' directory for generated bundles.\n")


if __name__ == "__main__":
    main()
