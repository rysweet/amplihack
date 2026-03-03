"""Main orchestrator for E2E test generation.

Coordinates test generation for multiple app types:
- Web apps: Playwright tests (original behavior)
- CLI apps: Gadugi YAML scenarios from command definitions
- TUI apps: Gadugi YAML scenarios from widget/navigation analysis
- APIs: Gadugi YAML scenarios from OpenAPI/Swagger specs
- MCPs: Gadugi YAML scenarios from tool definitions

Phases:
1. App type detection (or use explicit type)
2. Config detection (stack for web, CLI/TUI/API/MCP config)
3. Infrastructure setup (web only) or output dir creation
4. Test generation (dispatched by app type)
5. Coverage audit
"""

import time
from pathlib import Path

from .api_test_generator import generate_api_tests
from .app_type_detector import (
    detect_api_config,
    detect_app_type,
    detect_cli_config,
    detect_mcp_config,
    detect_tui_config,
)
from .cli_test_generator import generate_cli_tests
from .coverage_audit import audit_coverage
from .infrastructure_setup import setup_infrastructure
from .mcp_test_generator import generate_mcp_tests
from .models import (
    AppType,
    E2EGeneratorError,
    GenerationConfig,
    TestGenerationResult,
)
from .stack_detector import detect_stack_sync
from .template_manager import TemplateManager
from .test_generator import generate_all_tests
from .tui_test_generator import generate_tui_tests
from .utils import ensure_directory


def generate_tests(
    project_root: Path,
    app_type: str | None = None,
    config: GenerationConfig | None = None,
) -> TestGenerationResult:
    """Unified entry point for test generation across all app types.

    Auto-detects the app type or uses the explicitly specified type,
    then dispatches to the appropriate generator.

    Args:
        project_root: Path to project root directory
        app_type: Explicit app type ("web", "cli", "tui", "api", "mcp") or None for auto-detect
        config: Optional generation configuration

    Returns:
        TestGenerationResult with success status, test count, bugs, coverage
    """
    start_time = time.time()

    if config is None:
        config = GenerationConfig()

    try:
        # Phase 1: Detect app type
        detected_type = detect_app_type(project_root, app_type)
        print(f"Detected app type: {detected_type.value}")

        # Phase 2+3+4: Dispatch to appropriate generator
        _GENERATORS = {
            AppType.CLI: _generate_cli,
            AppType.TUI: _generate_tui,
            AppType.API: _generate_api,
            AppType.MCP: _generate_mcp,
        }

        generator = _GENERATORS.get(detected_type)
        if generator:
            return generator(project_root, config, start_time)
        # Default: web (includes AppType.WEB and any unknown)
        return generate_e2e_tests(project_root, config)

    except E2EGeneratorError as e:
        return TestGenerationResult(
            success=False,
            total_tests=0,
            bugs_found=[],
            coverage_report=None,  # type: ignore
            execution_time=time.time() - start_time,
            error=str(e),
        )
    except Exception as e:
        return TestGenerationResult(
            success=False,
            total_tests=0,
            bugs_found=[],
            coverage_report=None,  # type: ignore
            execution_time=time.time() - start_time,
            error=f"Unexpected error: {e}",
        )


def _generate_cli(
    project_root: Path, config: GenerationConfig, start_time: float
) -> TestGenerationResult:
    """Generate CLI test scenarios."""
    print("Phase 1/3: Detecting CLI configuration...")
    cli_config = detect_cli_config(project_root)
    print(f"  Framework: {cli_config.framework}, Commands: {len(cli_config.commands)}")

    print("Phase 2/3: Generating CLI test scenarios...")
    output_dir = project_root / config.output_dir
    ensure_directory(output_dir)
    template_mgr = TemplateManager()
    generated_tests = generate_cli_tests(cli_config, template_mgr, output_dir)
    total_tests = sum(t.test_count for t in generated_tests)
    print(f"  Generated: {total_tests} test scenarios")

    print("Phase 3/3: Coverage summary...")
    return TestGenerationResult(
        success=True,
        total_tests=total_tests,
        bugs_found=[],
        coverage_report=None,  # type: ignore
        execution_time=time.time() - start_time,
    )


def _generate_tui(
    project_root: Path, config: GenerationConfig, start_time: float
) -> TestGenerationResult:
    """Generate TUI test scenarios."""
    print("Phase 1/3: Detecting TUI configuration...")
    tui_config = detect_tui_config(project_root)
    print(f"  Framework: {tui_config.framework}, Widgets: {len(tui_config.widgets)}")

    print("Phase 2/3: Generating TUI test scenarios...")
    output_dir = project_root / config.output_dir
    ensure_directory(output_dir)
    template_mgr = TemplateManager()
    generated_tests = generate_tui_tests(tui_config, template_mgr, output_dir)
    total_tests = sum(t.test_count for t in generated_tests)
    print(f"  Generated: {total_tests} test scenarios")

    print("Phase 3/3: Coverage summary...")
    return TestGenerationResult(
        success=True,
        total_tests=total_tests,
        bugs_found=[],
        coverage_report=None,  # type: ignore
        execution_time=time.time() - start_time,
    )


def _generate_api(
    project_root: Path, config: GenerationConfig, start_time: float
) -> TestGenerationResult:
    """Generate API test scenarios."""
    print("Phase 1/3: Detecting API configuration...")
    api_config = detect_api_config(project_root)
    print(f"  Spec: {api_config.spec_format}, Endpoints: {len(api_config.endpoints)}")

    print("Phase 2/3: Generating API test scenarios...")
    output_dir = project_root / config.output_dir
    ensure_directory(output_dir)
    template_mgr = TemplateManager()
    generated_tests = generate_api_tests(api_config, template_mgr, output_dir)
    total_tests = sum(t.test_count for t in generated_tests)
    print(f"  Generated: {total_tests} test scenarios")

    print("Phase 3/3: Coverage summary...")
    return TestGenerationResult(
        success=True,
        total_tests=total_tests,
        bugs_found=[],
        coverage_report=None,  # type: ignore
        execution_time=time.time() - start_time,
    )


def _generate_mcp(
    project_root: Path, config: GenerationConfig, start_time: float
) -> TestGenerationResult:
    """Generate MCP test scenarios."""
    print("Phase 1/3: Detecting MCP configuration...")
    mcp_config = detect_mcp_config(project_root)
    print(f"  Tools: {len(mcp_config.tools)}, Transport: {mcp_config.transport}")

    print("Phase 2/3: Generating MCP test scenarios...")
    output_dir = project_root / config.output_dir
    ensure_directory(output_dir)
    template_mgr = TemplateManager()
    generated_tests = generate_mcp_tests(mcp_config, template_mgr, output_dir)
    total_tests = sum(t.test_count for t in generated_tests)
    print(f"  Generated: {total_tests} test scenarios")

    print("Phase 3/3: Coverage summary...")
    return TestGenerationResult(
        success=True,
        total_tests=total_tests,
        bugs_found=[],
        coverage_report=None,  # type: ignore
        execution_time=time.time() - start_time,
    )


def generate_e2e_tests(
    project_root: Path, config: GenerationConfig | None = None
) -> TestGenerationResult:
    """Main entry point for E2E test generation.

    Executes all phases in sequence:
    1. Detect stack (frontend, backend, database)
    2. Setup infrastructure (config, helpers, fixtures)
    3. Generate tests (7 categories, ≥40 tests)
    4. Coverage audit (verify requirements, report gaps)

    Args:
        project_root: Path to project root directory
        config: Optional generation configuration

    Returns:
        TestGenerationResult with success status, test count, bugs, coverage

    Raises:
        StackDetectionError: If unable to detect stack
        InfrastructureSetupError: If infrastructure creation fails
        TestGenerationError: If test generation fails
        CoverageAuditError: If coverage audit fails

    Example:
        >>> from pathlib import Path
        >>> from generator import generate_e2e_tests
        >>> result = generate_e2e_tests(Path.cwd())
        >>> print(f"Generated {result.total_tests} tests")
        >>> print(f"Found {len(result.bugs_found)} bugs")
    """
    start_time = time.time()

    # Use default config if none provided
    if config is None:
        config = GenerationConfig()

    # Validate config
    if config.workers != 1:
        return TestGenerationResult(
            success=False,
            total_tests=0,
            bugs_found=[],
            coverage_report=None,  # type: ignore
            execution_time=0.0,
            error="workers MUST be 1 (MANDATORY requirement)",
        )

    try:
        # Phase 1: Stack Detection
        print("Phase 1/4: Detecting stack...")
        stack = detect_stack_sync(project_root)
        print(
            f"  Detected: {stack.frontend_framework} + {stack.backend_framework} + {stack.database_type}"
        )

        # Phase 2: Infrastructure Setup
        print("Phase 2/4: Setting up infrastructure...")
        output_dir = project_root / config.output_dir
        setup_infrastructure(stack, output_dir)
        print("  Created: playwright.config.ts, test-helpers/, fixtures/")

        # Phase 3: Test Generation
        print("Phase 3/4: Generating tests...")
        template_mgr = TemplateManager()
        generated_tests = generate_all_tests(stack, template_mgr, output_dir)
        total_tests = sum(t.test_count for t in generated_tests)
        print(f"  Generated: {total_tests} tests across 7 categories")

        # Verify minimum test count
        if total_tests < 40:
            return TestGenerationResult(
                success=False,
                total_tests=total_tests,
                bugs_found=[],
                coverage_report=None,  # type: ignore
                execution_time=time.time() - start_time,
                error=f"Generated only {total_tests} tests, minimum is 40",
            )

        # Phase 4: Coverage Audit (if enabled)
        coverage_report = None
        if config.enable_coverage_audit:
            print("Phase 4/4: Auditing coverage...")
            coverage_report = audit_coverage(stack, generated_tests, None)
            print(
                f"  Coverage: {coverage_report.route_coverage_percent:.1f}% routes, {coverage_report.endpoint_coverage_percent:.1f}% endpoints"
            )

        # Calculate execution time
        execution_time = time.time() - start_time

        # Determine success
        success = True
        error = None

        # Check acceptance criteria
        if total_tests < 40:
            success = False
            error = f"Generated only {total_tests} tests (minimum: 40)"

        # Check all 7 categories present
        if coverage_report:
            missing_categories = [
                cat for cat, count in coverage_report.category_breakdown.items() if count == 0
            ]
            if missing_categories:
                success = False
                error = f"Missing categories: {', '.join(missing_categories)}"

        # Return result
        return TestGenerationResult(
            success=success,
            total_tests=total_tests,
            bugs_found=coverage_report.bugs_found if coverage_report else [],
            coverage_report=coverage_report if coverage_report else None,  # type: ignore
            execution_time=execution_time,
            error=error,
        )

    except E2EGeneratorError as e:
        # Handle known errors
        execution_time = time.time() - start_time
        return TestGenerationResult(
            success=False,
            total_tests=0,
            bugs_found=[],
            coverage_report=None,  # type: ignore
            execution_time=execution_time,
            error=str(e),
        )

    except Exception as e:
        # Handle unexpected errors
        execution_time = time.time() - start_time
        return TestGenerationResult(
            success=False,
            total_tests=0,
            bugs_found=[],
            coverage_report=None,  # type: ignore
            execution_time=execution_time,
            error=f"Unexpected error: {e}",
        )
