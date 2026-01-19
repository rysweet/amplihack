"""Basic tests for MCP evaluation framework.

These tests verify that the framework components work correctly.
"""

from .framework import (
    ComparisonMode,
    Criterion,
    ExpectedImprovement,
    MockToolAdapter,
    ScenarioCategory,
    TestScenario,
    ToolCapability,
    ToolConfiguration,
)


def test_types():
    """Test that core types can be instantiated."""
    print("Testing core types...")

    # Test enums
    category = ScenarioCategory.NAVIGATION
    assert category.value == "NAVIGATION"

    improvement = ExpectedImprovement.BOTH
    assert improvement.value == "both"

    mode = ComparisonMode.WITH_VS_WITHOUT
    assert mode.value == "with_vs_without"

    print("  ✓ Types work correctly")


def test_tool_configuration():
    """Test tool configuration creation and validation."""
    print("Testing tool configuration...")

    config = ToolConfiguration(
        tool_id="test_tool",
        tool_name="Test Tool",
        version="1.0.0",
        description="A test tool",
        capabilities=[
            ToolCapability(
                id="test_cap",
                name="Test Capability",
                description="Test",
                relevant_scenarios=[ScenarioCategory.NAVIGATION],
                expected_improvement=ExpectedImprovement.FASTER,
                mcp_commands=["test/command"],
            )
        ],
        adapter_class="MockToolAdapter",
        setup_required=False,
        setup_instructions="",
        expected_advantages={ScenarioCategory.NAVIGATION: ["Test advantage"]},
        baseline_comparison_mode=ComparisonMode.WITH_VS_WITHOUT,
    )

    # Validate
    errors = config.validate()
    assert len(errors) == 0, f"Validation errors: {errors}"

    print("  ✓ Tool configuration works correctly")


def test_mock_adapter():
    """Test mock adapter functionality."""
    print("Testing mock adapter...")

    adapter = MockToolAdapter()

    # Test enable/disable
    assert not adapter.enabled
    adapter.enable()
    assert adapter.enabled
    adapter.disable()
    assert not adapter.enabled

    # Test availability
    assert adapter.is_available()

    # Test metrics collection
    metrics = adapter.collect_tool_metrics()
    assert len(metrics.features_used) > 0

    # Test capabilities
    capabilities = adapter.get_capabilities()
    assert len(capabilities) > 0

    print("  ✓ Mock adapter works correctly")


def test_scenario_creation():
    """Test scenario creation."""
    print("Testing scenario creation...")

    codebase_path = Path(__file__).parent / "scenarios" / "test_codebases" / "microservice_project"

    scenario = TestScenario(
        id="test_001",
        category=ScenarioCategory.NAVIGATION,
        name="Test Scenario",
        description="A test scenario",
        test_codebase=codebase_path,
        initial_state={"test": True},
        task_prompt="Test task",
        success_criteria=[
            Criterion(name="test_criterion", check=lambda r: True, description="Test")
        ],
        baseline_metrics=["file_reads"],
        tool_metrics=["features_used"],
    )

    assert scenario.category == ScenarioCategory.NAVIGATION
    assert len(scenario.success_criteria) == 1

    print("  ✓ Scenario creation works correctly")


def test_config_loading():
    """Test loading Serena configuration."""
    print("Testing configuration loading...")

    from tests.mcp_evaluation.tools import load_tool_config

    try:
        config = load_tool_config("serena")
        assert config.tool_id == "serena"
        assert len(config.capabilities) > 0

        # Validate
        errors = config.validate()
        if errors:
            print(f"  ⚠ Configuration has validation errors: {errors}")
        else:
            print("  ✓ Serena configuration loads and validates correctly")

    except FileNotFoundError:
        print("  ⚠ Serena config not found (expected in tools/serena_config.yaml)")
    except Exception as e:
        print(f"  ✗ Configuration loading failed: {e}")
        raise


def test_scenarios_loading():
    """Test loading test scenarios."""
    print("Testing scenarios loading...")

    from tests.mcp_evaluation.scenarios import get_all_scenarios

    scenarios = get_all_scenarios()
    assert len(scenarios) == 3, f"Expected 3 scenarios, got {len(scenarios)}"

    # Check scenario types
    categories = [s.category for s in scenarios]
    assert ScenarioCategory.NAVIGATION in categories
    assert ScenarioCategory.ANALYSIS in categories
    assert ScenarioCategory.MODIFICATION in categories

    print(f"  ✓ All {len(scenarios)} scenarios loaded correctly")


def main():
    """Run all tests."""
    print("=" * 60)
    print("MCP Evaluation Framework Tests")
    print("=" * 60)
    print()

    tests = [
        test_types,
        test_tool_configuration,
        test_mock_adapter,
        test_scenario_creation,
        test_config_loading,
        test_scenarios_loading,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"  ✗ Test failed: {e}")
            failed += 1
            import traceback

            traceback.print_exc()

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
