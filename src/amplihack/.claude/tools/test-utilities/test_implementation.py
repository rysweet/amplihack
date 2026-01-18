#!/usr/bin/env python3
"""Test script to verify Agent Bundle Generator implementation."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from amplihack.bundle_generator import (
    AgentGenerator,
    BundleBuilder,
    BundlePackager,
    IntentExtractor,
    PromptParser,
)
from amplihack.bundle_generator.models import PackageFormat


def test_end_to_end():
    """Test the complete pipeline from prompt to package."""
    print("🧪 Testing Agent Bundle Generator Implementation")
    print("=" * 60)

    # Test prompt
    prompt = "Create an agent to monitor API endpoints and alert on failures"
    print(f"📝 Prompt: '{prompt}'")

    try:
        # 1. Parse prompt
        print("\n1️⃣  Parsing prompt...")
        parser = PromptParser()
        parsed = parser.parse(prompt)
        print(f"✅ Parsed with confidence: {parsed.confidence:.2f}")
        print(f"   Tokens: {parsed.tokens[:5]}...")
        print(f"   Entities: {parsed.entities}")

        # 2. Extract intent
        print("\n2️⃣  Extracting intent...")
        extractor = IntentExtractor(parser)
        intent = extractor.extract(parsed)
        print(f"✅ Intent: {intent.action} {intent.domain}")
        print(f"   Complexity: {intent.complexity}")
        print(f"   Requirements: {len(intent.requirements)} found")

        # 3. Generate agents
        print("\n3️⃣  Generating agents...")
        generator = AgentGenerator()
        agents = generator.generate(intent)
        print(f"✅ Generated {len(agents)} agent(s)")
        for agent in agents:
            print(f"   - {agent.name}: {len(agent.content)} chars")
            print(f"     Files: {list(agent.files.keys())}")

        # 4. Build bundle
        print("\n4️⃣  Building bundle...")
        builder = BundleBuilder()
        bundle = builder.build(agents, intent)
        print(f"✅ Bundle: {bundle.name} v{bundle.version}")
        print(f"   ID: {bundle.id}")
        print(f"   Agents: {len(bundle.agents)}")
        print(f"   Total size: ~{sum(len(a.content) for a in bundle.agents)} chars")

        # 5. Write bundle to disk
        print("\n5️⃣  Writing bundle to disk...")
        output_dir = Path("/tmp/test_bundles")
        bundle_path = builder.write_bundle(bundle, output_dir)
        print(f"✅ Bundle written to: {bundle_path}")

        # List bundle contents
        bundle_files = list(bundle_path.glob("**/*"))[:10]
        print(f"   Files created: {len(list(bundle_path.glob('**/*')))} total")
        for file in bundle_files[:5]:
            if file.is_file():
                print(f"   - {file.relative_to(bundle_path)}")

        # 6. Package bundle
        print("\n6️⃣  Packaging bundle...")
        packager = BundlePackager()
        package_path = packager.package(bundle_path, PackageFormat.TAR_GZ)
        print(f"✅ Package created: {package_path}")
        print(f"   Size: {package_path.stat().st_size / 1024:.2f} KB")

        print("\n✅ SUCCESS! All components working correctly.")
        print("🎉 Agent Bundle Generator is fully operational!")

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_simple_examples():
    """Test with simple example prompts."""
    print("\n\n📚 Testing Simple Examples")
    print("=" * 60)

    examples = [
        "Create a JSON validator agent",
        "Build an agent for code review",
        "Make a test runner agent",
    ]

    parser = PromptParser()
    extractor = IntentExtractor(parser)
    generator = AgentGenerator()

    for prompt in examples:
        print(f"\n📝 '{prompt}'")
        try:
            parsed = parser.parse(prompt)
            intent = extractor.extract(parsed)
            agents = generator.generate(intent)
            print(f"   ✅ Generated {len(agents)} agent(s): {[a.name for a in agents]}")
        except Exception as e:
            print(f"   ❌ Failed: {e}")


if __name__ == "__main__":
    # Run tests
    success = test_end_to_end()
    if success:
        test_simple_examples()

    sys.exit(0 if success else 1)
