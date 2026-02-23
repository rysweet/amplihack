"""Main orchestrator for E2E test generation.

Coordinates all 4 phases of test generation:
1. Stack detection
2. Infrastructure setup
3. Test generation
4. Coverage audit
"""

import time
from pathlib import Path

from .coverage_audit import audit_coverage
from .infrastructure_setup import setup_infrastructure
from .models import (
    E2EGeneratorError,
    GenerationConfig,
    TestGenerationResult,
)
from .stack_detector import detect_stack_sync
from .template_manager import TemplateManager
from .test_generator import generate_all_tests


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

    if config.output_dir != "e2e":
        return TestGenerationResult(
            success=False,
            total_tests=0,
            bugs_found=[],
            coverage_report=None,  # type: ignore
            execution_time=0.0,
            error="output_dir MUST be 'e2e' not 'tests/e2e' (MANDATORY requirement)",
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
