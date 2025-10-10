#!/usr/bin/env python3
"""
Test script to validate Enhanced Parallel Execution Documentation completeness.

This script validates that all required components for Issue #642 are present
in the CLAUDE.md file.
"""

import re
from pathlib import Path


def test_parallel_execution_docs():
    """Test that all required parallel execution documentation is present."""
    claude_md_path = Path(__file__).parent / "CLAUDE.md"

    if not claude_md_path.exists():
        raise FileNotFoundError(f"CLAUDE.md not found at {claude_md_path}")

    content = claude_md_path.read_text()

    # Required sections for Microsoft Amplifier parallel execution
    required_sections = [
        "Microsoft Amplifier Parallel Execution Engine",
        "Comprehensive Parallel Detection Framework",
        "Microsoft Amplifier Execution Templates",
        "Advanced Execution Patterns",
        "Microsoft Amplifier Coordination Protocols",
        "Anti-Patterns and Common Mistakes",
        "Systematic Decision Framework",
        "Template Responses for Common Scenarios",
        "Performance Optimization Guidelines",
    ]

    missing_sections = []
    for section in required_sections:
        if section not in content:
            missing_sections.append(section)

    if missing_sections:
        raise AssertionError(f"Missing required sections: {missing_sections}")

    # Test for specific parallel execution rules (6 rules total)
    rule_patterns = [
        r"RULE 1: File Operations",
        r"RULE 2: Multi-Perspective Analysis",
        r"RULE 3: Independent Components",
        r"RULE 4: Information Gathering",
        r"RULE 5: Development Lifecycle Tasks",
        r"RULE 6: Cross-Cutting Concerns",
    ]

    missing_rules = []
    for pattern in rule_patterns:
        if not re.search(pattern, content):
            missing_rules.append(pattern)

    if missing_rules:
        raise AssertionError(f"Missing parallel execution rules: {missing_rules}")

    # Test for execution templates (5 templates)
    template_patterns = [
        r"Template 1: Comprehensive Feature Development",
        r"Template 2: Multi-Dimensional Code Analysis",
        r"Template 3: Comprehensive Problem Diagnosis",
        r"Template 4: System Preparation and Validation",
        r"Template 5: Research and Discovery",
    ]

    missing_templates = []
    for pattern in template_patterns:
        if not re.search(pattern, content):
            missing_templates.append(pattern)

    if missing_templates:
        raise AssertionError(f"Missing execution templates: {missing_templates}")

    # Test for anti-patterns (3 anti-patterns)
    antipattern_patterns = [
        r"Anti-Pattern 1: Unnecessary Sequencing",
        r"Anti-Pattern 2: False Dependencies",
        r"Anti-Pattern 3: Over-Sequencing Complex Tasks",
    ]

    missing_antipatterns = []
    for pattern in antipattern_patterns:
        if not re.search(pattern, content):
            missing_antipatterns.append(pattern)

    if missing_antipatterns:
        raise AssertionError(f"Missing anti-patterns: {missing_antipatterns}")

    # Test for scenario templates (4 scenarios)
    scenario_patterns = [
        r"Scenario 1: New Feature Request",
        r"Scenario 2: Bug Investigation",
        r"Scenario 3: Code Review Request",
        r"Scenario 4: System Analysis",
    ]

    missing_scenarios = []
    for pattern in scenario_patterns:
        if not re.search(pattern, content):
            missing_scenarios.append(pattern)

    if missing_scenarios:
        raise AssertionError(f"Missing scenario templates: {missing_scenarios}")

    # Test for decision framework components
    decision_components = [
        "When to Use Parallel Execution",
        "When to Use Sequential Execution",
        "Decision Matrix",
        "PARALLEL-READY Agents",
        "SEQUENTIAL-REQUIRED Agents",
    ]

    missing_decisions = []
    for component in decision_components:
        if component not in content:
            missing_decisions.append(component)

    if missing_decisions:
        raise AssertionError(f"Missing decision framework components: {missing_decisions}")

    # Test for performance optimization guidelines
    performance_components = ["Parallel Execution Optimization", "Monitoring and Metrics"]

    missing_performance = []
    for component in performance_components:
        if component not in content:
            missing_performance.append(component)

    if missing_performance:
        raise AssertionError(f"Missing performance components: {missing_performance}")

    print("✅ All parallel execution documentation components are present!")
    print("✅ Microsoft Amplifier parallel execution guidance is complete!")

    # Count total enhancements
    enhancements = (
        len(required_sections)
        + len(rule_patterns)
        + len(template_patterns)
        + len(antipattern_patterns)
        + len(scenario_patterns)
    )
    print(f"✅ Total documented enhancements: {enhancements}")

    return True


def test_integration_with_existing_docs():
    """Test that new documentation integrates well with existing content."""
    claude_md_path = Path(__file__).parent / "CLAUDE.md"
    content = claude_md_path.read_text()

    # Ensure existing important sections are still present
    existing_sections = [
        "Project Overview",
        "Working Philosophy",
        "Agent Delegation Strategy",
        "Development Principles",
        "User Preferences",
    ]

    missing_existing = []
    for section in existing_sections:
        if section not in content:
            missing_existing.append(section)

    if missing_existing:
        raise AssertionError(f"Integration broke existing sections: {missing_existing}")

    # Ensure Microsoft Amplifier branding is consistent
    amplifier_mentions = content.count("Microsoft Amplifier")
    if amplifier_mentions < 3:
        raise AssertionError(
            f"Insufficient Microsoft Amplifier branding: {amplifier_mentions} mentions"
        )

    print("✅ Documentation integration successful!")
    print(f"✅ Microsoft Amplifier branding: {amplifier_mentions} mentions")

    return True


if __name__ == "__main__":
    try:
        test_parallel_execution_docs()
        test_integration_with_existing_docs()
        print("\n🎉 All tests passed! Enhanced Parallel Execution Documentation is complete.")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
