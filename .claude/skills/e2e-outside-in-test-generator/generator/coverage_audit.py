"""Coverage analysis and reporting.

Verifies all 7 categories present, ≥40 total tests, and generates recommendations.
"""

from .models import (
    Bug,
    BugSeverity,
    CoverageAuditError,
    CoverageReport,
    GeneratedTest,
    StackConfig,
    TestCategory,
)
from .utils import calculate_coverage_percent


def audit_coverage(
    stack: StackConfig,
    generated_tests: list[GeneratedTest],
    test_results: None = None,  # Kept for API compatibility, not used
) -> CoverageReport:
    """Analyze test coverage and generate recommendations.

    Args:
        stack: Stack configuration
        generated_tests: List of generated tests
        test_results: Unused (kept for API compatibility)

    Returns:
        CoverageReport with coverage analysis

    Raises:
        CoverageAuditError: If audit fails
    """
    try:
        # Calculate total tests
        total_tests = sum(t.test_count for t in generated_tests)

        # Category breakdown
        category_breakdown = calculate_category_breakdown(generated_tests)

        # Route coverage
        route_coverage = calculate_route_coverage(stack, generated_tests)
        route_coverage_percent = calculate_coverage_percent(
            sum(1 for covered in route_coverage.values() if covered), len(route_coverage)
        )

        # Endpoint coverage
        endpoint_coverage = calculate_endpoint_coverage(stack, generated_tests)
        endpoint_coverage_percent = calculate_coverage_percent(
            sum(1 for covered in endpoint_coverage.values() if covered), len(endpoint_coverage)
        )

        # No bugs detected without test execution
        bugs: list[Bug] = []

        # Generate recommendations
        recommendations = generate_recommendations(
            total_tests,
            category_breakdown,
            route_coverage_percent,
            endpoint_coverage_percent,
            bugs,
        )

        return CoverageReport(
            total_tests=total_tests,
            category_breakdown=category_breakdown,
            route_coverage=route_coverage,
            endpoint_coverage=endpoint_coverage,
            bugs_found=bugs,
            recommendations=recommendations,
            route_coverage_percent=route_coverage_percent,
            endpoint_coverage_percent=endpoint_coverage_percent,
        )

    except Exception as e:
        raise CoverageAuditError(f"Coverage audit failed: {e}")


def calculate_category_breakdown(generated_tests: list[GeneratedTest]) -> dict[str, int]:
    """Calculate test count per category.

    Args:
        generated_tests: List of generated tests

    Returns:
        Dict of category name -> test count
    """
    breakdown = {category.value: 0 for category in TestCategory}

    for test in generated_tests:
        breakdown[test.category.value] += test.test_count

    return breakdown


def calculate_route_coverage(
    stack: StackConfig, generated_tests: list[GeneratedTest]
) -> dict[str, bool]:
    """Map routes to test coverage.

    Args:
        stack: Stack configuration
        generated_tests: List of generated tests

    Returns:
        Dict of route path -> covered (bool)
    """
    coverage = {route.path: False for route in stack.routes}

    # Check which routes are covered by tests
    for test in generated_tests:
        # Simple heuristic: if test file mentions route, it's covered
        route_slug = str(test.file_path.stem)
        for route in stack.routes:
            route_pattern = route.path.replace("/", "-").strip("-") or "home"
            if route_pattern in route_slug:
                coverage[route.path] = True

    return coverage


def calculate_endpoint_coverage(
    stack: StackConfig, generated_tests: list[GeneratedTest]
) -> dict[str, bool]:
    """Map API endpoints to test coverage.

    Args:
        stack: Stack configuration
        generated_tests: List of generated tests

    Returns:
        Dict of endpoint key -> covered (bool)
    """
    coverage = {}

    for endpoint in stack.api_endpoints:
        key = f"{endpoint.method} {endpoint.path}"
        coverage[key] = False

        # Check if any test covers this endpoint
        # In real implementation, would parse test files
        # For now, mark as not covered
        coverage[key] = False

    return coverage


def generate_recommendations(
    total_tests: int,
    category_breakdown: dict[str, int],
    route_coverage_percent: float,
    endpoint_coverage_percent: float,
    bugs: list[Bug],
) -> list[str]:
    """Generate actionable recommendations.

    Args:
        total_tests: Total number of tests
        category_breakdown: Tests per category
        route_coverage_percent: Route coverage percentage
        endpoint_coverage_percent: Endpoint coverage percentage
        bugs: List of bugs found

    Returns:
        List of recommendations
    """
    recommendations = []

    # Check minimum test count
    if total_tests < 40:
        recommendations.append(f"Add {40 - total_tests} more tests to reach minimum of 40 tests")

    # Check category coverage
    for category, count in category_breakdown.items():
        if count == 0:
            recommendations.append(f"Add tests for {category} category (currently 0)")
        elif count < 3:
            recommendations.append(f"Consider adding more {category} tests (currently {count})")

    # Check route coverage
    if route_coverage_percent < 80.0:
        recommendations.append(
            f"Increase route coverage from {route_coverage_percent:.1f}% to at least 80%"
        )

    # Check endpoint coverage
    if endpoint_coverage_percent < 70.0:
        recommendations.append(
            f"Increase API endpoint coverage from {endpoint_coverage_percent:.1f}% to at least 70%"
        )

    # Check bugs
    critical_bugs = [b for b in bugs if b.severity == BugSeverity.CRITICAL]
    if critical_bugs:
        recommendations.append(f"Fix {len(critical_bugs)} CRITICAL bugs immediately")

    high_bugs = [b for b in bugs if b.severity == BugSeverity.HIGH]
    if high_bugs:
        recommendations.append(f"Address {len(high_bugs)} HIGH severity bugs")

    # If everything looks good
    if not recommendations:
        recommendations.append(
            "Coverage looks good! All categories present, minimum test count met."
        )

    return recommendations
