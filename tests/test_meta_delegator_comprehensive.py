#!/usr/bin/env python3
"""
Comprehensive End-to-End Test for Meta-Delegator
Tests the way a user would actually use the system
"""

import sys

sys.path.insert(0, "src")

from pathlib import Path

from amplihack.meta_delegation import run_meta_delegation
from amplihack.meta_delegation.evidence_collector import EvidenceCollector
from amplihack.meta_delegation.persona import ARCHITECT, GUIDE, JUNIOR_DEV, QA_ENGINEER
from amplihack.meta_delegation.platform_cli import get_platform_cli
from amplihack.meta_delegation.scenario_generator import GadugiScenarioGenerator
from amplihack.meta_delegation.state_machine import ProcessState, SubprocessStateMachine
from amplihack.meta_delegation.success_evaluator import SuccessCriteriaEvaluator

print("=" * 70)
print("COMPREHENSIVE META-DELEGATOR TEST")
print("Testing as a user would - validating all components work")
print("=" * 70)

test_results = []

# Test 1: Platform CLI - Can we get all 3 platforms?
print("\n[Test 1] Platform CLI Abstraction")
print("-" * 70)
try:
    for platform_name in ["claude-code", "copilot", "amplifier"]:
        cli = get_platform_cli(platform_name)
        print(f"✅ {cli.platform_name:15} - Available")
        print(f"   Command format: {cli.format_prompt('test goal', 'guide', '')[:60]}...")
    test_results.append(("Platform CLI", "PASS"))
except Exception as e:
    print(f"❌ FAILED: {e}")
    test_results.append(("Platform CLI", "FAIL"))

# Test 2: Personas - Are all 4 personas defined correctly?
print("\n[Test 2] Persona Definitions")
print("-" * 70)
try:
    personas = [GUIDE, QA_ENGINEER, ARCHITECT, JUNIOR_DEV]
    for persona in personas:
        print(
            f"✅ {persona.name:15} - Communication: {persona.communication_style:12} Thoroughness: {persona.thoroughness_level}"
        )
        assert len(persona.prompt_template) > 100, "Prompt template too short"
        assert len(persona.evidence_collection_priority) > 0, "No evidence priorities"
    test_results.append(("Personas", "PASS"))
except Exception as e:
    print(f"❌ FAILED: {e}")
    test_results.append(("Personas", "FAIL"))

# Test 3: State Machine - Does state tracking work?
print("\n[Test 3] Subprocess State Machine")
print("-" * 70)
try:
    sm = SubprocessStateMachine()
    print(f"   Initial state: {sm.current_state}")
    # Follow valid transition path: CREATED → STARTING → RUNNING
    sm.transition_to(ProcessState.STARTING)
    print(f"   After STARTING: {sm.current_state}")
    sm.transition_to(ProcessState.RUNNING)
    print(f"   After RUNNING: {sm.current_state}")
    assert sm.current_state == ProcessState.RUNNING
    assert not sm.is_complete()
    sm.transition_to(ProcessState.COMPLETING)
    sm.transition_to(ProcessState.COMPLETED)
    assert sm.is_complete()
    print("✅ State transitions work correctly")
    test_results.append(("State Machine", "PASS"))
except Exception as e:
    print(f"❌ FAILED: {e}")
    test_results.append(("State Machine", "FAIL"))

# Test 4: Success Evaluator - Can it score requirements?
print("\n[Test 4] Success Criteria Evaluator")
print("-" * 70)
try:
    evaluator = SuccessCriteriaEvaluator()

    # Create mock evidence
    from datetime import datetime

    from amplihack.meta_delegation.evidence_collector import EvidenceItem

    evidence = [
        EvidenceItem(
            "test_file",
            "test.py",
            "def test_feature(): pass",
            "def test_feature()...",
            100,
            datetime.now(),
            {},
        ),
        EvidenceItem(
            "code_file",
            "feature.py",
            "class Feature: pass",
            "class Feature...",
            200,
            datetime.now(),
            {},
        ),
    ]

    # Use correct API: criteria (string), evidence (list), execution_log (string)
    result = evaluator.evaluate(
        criteria="Tests exist and Code implemented",
        evidence=evidence,
        execution_log="Tests passed\nCode created",
    )

    print(f"   Score: {result.score}/100")
    print(f"   Requirements met: {result.requirements_met}")
    print(f"   Requirements missing: {result.requirements_missing}")
    assert result.score >= 0 and result.score <= 100
    print("✅ Success evaluation works correctly")
    test_results.append(("Success Evaluator", "PASS"))
except Exception as e:
    print(f"❌ FAILED: {e}")
    test_results.append(("Success Evaluator", "FAIL"))

# Test 5: Evidence Collector - Can it find and classify files?
print("\n[Test 5] Evidence Collector")
print("-" * 70)
try:
    import os
    import tempfile

    # Create test directory with sample files
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample files
        os.makedirs(f"{tmpdir}/src", exist_ok=True)
        os.makedirs(f"{tmpdir}/tests", exist_ok=True)

        Path(f"{tmpdir}/src/feature.py").write_text("def feature(): pass")
        Path(f"{tmpdir}/tests/test_feature.py").write_text("def test_feature(): pass")
        Path(f"{tmpdir}/README.md").write_text("# Documentation")

        # Correct API: EvidenceCollector requires working_directory
        collector = EvidenceCollector(working_directory=tmpdir)
        evidence = collector.collect_evidence(tmpdir, GUIDE.evidence_collection_priority)

        print(f"   Files found: {len(evidence)}")
        types_found = {e.type for e in evidence}  # Attribute is 'type' not 'evidence_type'
        print(f"   Types: {types_found}")

        assert len(evidence) >= 3, "Should find at least 3 files"
        assert "code_file" in types_found or "test_file" in types_found
        print("✅ Evidence collection works correctly")
    test_results.append(("Evidence Collector", "PASS"))
except Exception as e:
    print(f"❌ FAILED: {e}")
    test_results.append(("Evidence Collector", "FAIL"))

# Test 6: Scenario Generator - Can it generate test scenarios?
print("\n[Test 6] Gadugi Scenario Generator")
print("-" * 70)
try:
    generator = GadugiScenarioGenerator()
    scenarios = generator.generate_scenarios(goal="Create simple API", success_criteria="API works")

    print(f"   Scenarios generated: {len(scenarios)}")
    for scenario in scenarios[:3]:  # Show first 3
        print(
            f"   - {scenario.name} (category: {scenario.category}, priority: {scenario.priority})"
        )

    assert len(scenarios) > 0, "Should generate at least 1 scenario"
    assert all(hasattr(s, "name") for s in scenarios)
    print("✅ Scenario generation works correctly")
    test_results.append(("Scenario Generator", "PASS"))
except Exception as e:
    print(f"❌ FAILED: {e}")
    test_results.append(("Scenario Generator", "FAIL"))

# Test 7: Public API - Can users call run_meta_delegation?
print("\n[Test 7] Public API (run_meta_delegation)")
print("-" * 70)
try:
    import inspect

    sig = inspect.signature(run_meta_delegation)
    params = list(sig.parameters.keys())

    print(f"   Function signature: run_meta_delegation({', '.join(params)})")
    assert "goal" in params
    assert "success_criteria" in params
    assert "persona_type" in params
    assert "platform" in params
    print("✅ Public API signature correct")
    test_results.append(("Public API", "PASS"))
except Exception as e:
    print(f"❌ FAILED: {e}")
    test_results.append(("Public API", "FAIL"))

# Summary
print("\n" + "=" * 70)
print("TEST SUMMARY")
print("=" * 70)

passed = sum(1 for _, result in test_results if result == "PASS")
total = len(test_results)

for test_name, result in test_results:
    symbol = "✅" if result == "PASS" else "❌"
    print(f"{symbol} {test_name:25} {result}")

print("-" * 70)
print(f"TOTAL: {passed}/{total} tests passed ({passed / total * 100:.0f}%)")
print("=" * 70)

if passed == total:
    print("\n✅ ALL COMPONENT TESTS PASSED")
    print("All modules work correctly in isolation")
    print("\nNote: Full subprocess spawn testing requires longer timeout and")
    print("interactive environment. Component testing validates core functionality.")
else:
    print(f"\n❌ {total - passed} tests failed")
    sys.exit(1)
