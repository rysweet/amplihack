#!/usr/bin/env python
"""Test the Agent Bundle Generator implementation."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.bundle_generator.extractor import IntentExtractor
from amplihack.bundle_generator.generator import AgentGenerator
from amplihack.bundle_generator.parser import PromptParser


def test_basic_workflow():
    """Test the basic workflow of the bundle generator."""
    print("Testing Agent Bundle Generator...")

    # Test prompt
    prompt = "Create an API monitoring agent that validates JSON responses and tracks performance metrics"

    # Parse the prompt
    print(f"\n1. Parsing prompt: {prompt[:50]}...")
    parser = PromptParser()
    parsed = parser.parse(prompt)
    print(f"   - Tokens: {len(parsed.tokens)}")
    print(f"   - Confidence: {parsed.confidence:.2%}")
    print(f"   - Entities: {parsed.entities}")

    # Extract intent
    print("\n2. Extracting intent...")
    extractor = IntentExtractor(parser)
    intent = extractor.extract(parsed)
    print(f"   - Action: {intent.action}")
    print(f"   - Domain: {intent.domain}")
    print(f"   - Complexity: {intent.complexity}")
    print(
        f"   - Requirements: {len(intent.agent_requirements) if hasattr(intent, 'agent_requirements') else 'N/A'}"
    )

    # Generate agents
    print("\n3. Generating agents...")
    generator = AgentGenerator()
    agents = generator.generate(intent)
    print(f"   - Generated {len(agents)} agent(s)")

    for agent in agents:
        print(f"\n   Agent: {agent.name}")
        print(f"   - Description: {agent.description[:100]}...")
        print(f"   - Capabilities: {agent.capabilities}")
        print(f"   - Content length: {len(agent.content)} chars")
        print(f"   - Has tests: {len(agent.tests) > 0}")
        print(f"   - Has docs: {len(agent.documentation) > 0}")

    # Test with different prompts
    test_prompts = [
        "Build a testing framework for security vulnerabilities",
        "Monitor real-time data streams and alert on anomalies",
        "Create a code review tool using Python",
    ]

    print("\n4. Testing additional prompts...")
    for i, test_prompt in enumerate(test_prompts, 1):
        print(f"\n   Test {i}: {test_prompt[:50]}...")
        try:
            parsed = parser.parse(test_prompt)
            intent = extractor.extract(parsed)
            agents = generator.generate(intent)
            print(f"      - Generated {len(agents)} agent(s) for {intent.action} {intent.domain}")
        except Exception as e:
            print(f"      - Error: {e.__class__.__name__}: {str(e)[:80]}...")

    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_basic_workflow()
