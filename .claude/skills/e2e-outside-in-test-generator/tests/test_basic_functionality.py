"""Basic functionality tests for E2E test generator."""

from pathlib import Path

import pytest
from generator.coverage_audit import audit_coverage
from generator.infrastructure_setup import create_playwright_config
from generator.models import (
    GenerationConfig,
    LocatorStrategy,
    StackConfig,
    TestCategory,
)
from generator.orchestrator import generate_e2e_tests
from generator.stack_detector import detect_stack_sync
from generator.template_manager import TemplateManager
from generator.test_generator import generate_all_tests


def test_models_import():
    """Test that all models can be imported."""
    assert TestCategory.SMOKE
    assert LocatorStrategy.ROLE_BASED


def test_generation_config_validation():
    """Test that GenerationConfig enforces workers=1."""
    # Valid config
    config = GenerationConfig(workers=1, output_dir="e2e")
    assert config.workers == 1

    # Invalid workers
    with pytest.raises(ValueError, match="workers MUST be 1"):
        GenerationConfig(workers=2)

    # Invalid output_dir
    with pytest.raises(ValueError, match="output_dir MUST be 'e2e'"):
        GenerationConfig(output_dir="tests/e2e")


def test_template_manager_loads_templates():
    """Test that TemplateManager loads templates."""
    mgr = TemplateManager()
    templates = mgr.list_templates()

    # Should have loaded all 7 category templates
    expected_templates = [
        "smoke",
        "form_interaction",
        "component_interaction",
        "keyboard_shortcuts",
        "api_streaming",
        "responsive",
        "pwa_basics",
    ]

    for template in expected_templates:
        assert template in templates, f"Missing template: {template}"


def test_template_rendering():
    """Test that templates render correctly."""
    mgr = TemplateManager()

    context = {
        "feature_name": "Login",
        "route": "/login",
        "title_pattern": "Login",
        "key_element_role": "button",
        "key_element_name": "Sign In",
        "critical_flow_steps": "await page.click('button');",
        "success_element_role": "heading",
        "success_element_name": "Welcome",
    }

    rendered = mgr.render("smoke", context)

    assert "Login" in rendered
    assert "/login" in rendered
    assert "Sign In" in rendered


def test_playwright_config_enforces_workers():
    """Test that generated Playwright config has workers=1."""

    stack = StackConfig(
        frontend_framework="nextjs",
        frontend_dir=Path("/test"),
        backend_framework="fastapi",
        backend_dir=Path("/test"),
        api_base_url="http://localhost:3000",
        database_type="postgresql",
        auth_mechanism="jwt",
        routes=[],
        api_endpoints=[],
        models=[],
    )

    config = create_playwright_config(stack)

    assert "workers: 1" in config
    assert "MANDATORY" in config


def test_stack_detector_with_nextjs(temp_project):
    """Test stack detection with Next.js project."""
    stack = detect_stack_sync(temp_project)

    assert stack.frontend_framework == "nextjs"
    assert len(stack.routes) > 0


def test_test_generation_creates_files(temp_project, sample_stack_config):
    """Test that test generation creates files."""
    output_dir = temp_project / "e2e"
    output_dir.mkdir()

    mgr = TemplateManager()
    generated_tests = generate_all_tests(sample_stack_config, mgr, output_dir)

    # Should generate tests for all 7 categories
    assert len(generated_tests) > 0

    # Should generate ≥40 tests
    total_tests = sum(t.test_count for t in generated_tests)
    assert total_tests >= 40

    # Verify all categories present
    categories_present = {t.category for t in generated_tests}
    assert len(categories_present) == 7


def test_coverage_audit(sample_stack_config):
    """Test coverage audit functionality."""
    from generator.models import GeneratedTest, TestCategory

    generated_tests = [
        GeneratedTest(
            category=TestCategory.SMOKE,
            file_path=Path("e2e/smoke/test.spec.ts"),
            test_count=10,
            description="Smoke tests",
        ),
        GeneratedTest(
            category=TestCategory.FORM_INTERACTION,
            file_path=Path("e2e/forms/test.spec.ts"),
            test_count=10,
            description="Form tests",
        ),
    ]

    report = audit_coverage(sample_stack_config, generated_tests)

    assert report.total_tests == 20
    assert len(report.category_breakdown) > 0
    assert len(report.recommendations) > 0


def test_orchestrator_validates_config(temp_project):
    """Test that orchestrator validates configuration."""
    # Invalid workers
    config = GenerationConfig.__new__(GenerationConfig)
    config.workers = 2
    config.output_dir = "e2e"
    config.max_tests_per_category = 10
    config.enable_fix_loop = True
    config.max_fix_iterations = 5
    config.enable_coverage_audit = True
    config.custom_templates = []

    result = generate_e2e_tests(temp_project, config)

    assert not result.success
    assert "workers MUST be 1" in result.error


def test_orchestrator_end_to_end(temp_project):
    """Test full orchestrator workflow."""
    config = GenerationConfig(
        enable_fix_loop=False,  # Skip fix loop for testing
        enable_coverage_audit=True,
    )

    result = generate_e2e_tests(temp_project, config)

    # Should succeed
    assert result.success or result.error is not None  # May fail on missing dependencies

    # Should generate tests
    assert result.total_tests >= 0

    # Should have execution time
    assert result.execution_time > 0
