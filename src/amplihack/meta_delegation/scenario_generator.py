"""Gadugi Scenario Generator Module.

This module generates comprehensive test scenarios for QA validation using the
gadugi-agentic-test framework conventions.

Scenario Categories:
- HAPPY_PATH: Normal operation flows
- ERROR_HANDLING: Error conditions and failure modes
- BOUNDARY_CONDITIONS: Edge cases, limits, empty inputs
- SECURITY: Authentication, authorization, injection attacks
- PERFORMANCE: Load, stress, scalability
- INTEGRATION: Cross-component interactions

Philosophy:
- Generate deterministic, comprehensive scenario coverage
- Aligned with gadugi-agentic-test YAML format
- Context-aware scenario generation
- Prioritize critical scenarios
"""

from dataclasses import dataclass, field
from enum import Enum


class ScenarioCategory(Enum):
    """Test scenario categories."""

    HAPPY_PATH = "happy_path"
    ERROR_HANDLING = "error_handling"
    BOUNDARY_CONDITIONS = "boundary_conditions"
    SECURITY = "security"
    PERFORMANCE = "performance"
    INTEGRATION = "integration"


@dataclass
class TestScenario:
    """Test scenario for gadugi-agentic-test framework.

    Attributes:
        name: Scenario name
        category: Scenario category
        description: Detailed description
        preconditions: List of preconditions that must be met
        steps: List of steps to execute
        expected_outcome: Expected result
        priority: Priority level (high, medium, low)
        tags: List of tags for categorization
    """

    name: str
    category: str
    description: str
    preconditions: list[str]
    steps: list[str]
    expected_outcome: str
    priority: str
    tags: list[str] = field(default_factory=list)


class GadugiScenarioGenerator:
    """Generates comprehensive test scenarios for QA validation."""

    def generate_scenarios(
        self,
        goal: str,
        success_criteria: str,
        context: str | None = None,
    ) -> list[TestScenario]:
        """Generate test scenarios based on goal and criteria.

        Args:
            goal: The task goal
            success_criteria: Success criteria to validate against
            context: Optional additional context

        Returns:
            List of test scenarios
        """
        scenarios = []

        # Detect domain/type of system being tested
        goal_lower = goal.lower()
        criteria_lower = success_criteria.lower()
        combined_text = f"{goal_lower} {criteria_lower}"

        # Detect if this is API-related
        is_api = any(
            keyword in combined_text
            for keyword in ["api", "endpoint", "rest", "http", "post", "get", "put", "delete"]
        )

        # Detect if authentication/security is involved
        is_auth = any(
            keyword in combined_text
            for keyword in ["auth", "login", "token", "jwt", "password", "permission", "secure"]
        )

        # Generate scenarios for each category
        scenarios.extend(self._generate_happy_path_scenarios(goal, success_criteria, is_api))
        scenarios.extend(self._generate_error_handling_scenarios(goal, success_criteria, is_api))
        scenarios.extend(self._generate_boundary_scenarios(goal, success_criteria, is_api))

        if is_auth or "security" in combined_text or "admin" in combined_text:
            scenarios.extend(self._generate_security_scenarios(goal, success_criteria))

        if "performance" in combined_text or "load" in combined_text or "scale" in combined_text:
            scenarios.extend(self._generate_performance_scenarios(goal, success_criteria))

        # Always add some integration scenarios
        scenarios.extend(self._generate_integration_scenarios(goal, success_criteria))

        return scenarios

    def _generate_happy_path_scenarios(
        self,
        goal: str,
        success_criteria: str,
        is_api: bool,
    ) -> list[TestScenario]:
        """Generate happy path test scenarios."""
        scenarios = []

        if is_api:
            # API happy path scenarios
            scenarios.append(
                TestScenario(
                    name="Valid request returns successful response",
                    category="happy_path",
                    description=f"Test that valid requests to the system return successful responses. Goal: {goal}",
                    preconditions=["System is running", "Valid credentials available"],
                    steps=[
                        "Prepare valid request data",
                        "Send request to endpoint",
                        "Verify response status code is 200/201",
                        "Verify response body contains expected data",
                    ],
                    expected_outcome="System returns successful response with correct data",
                    priority="high",
                    tags=["api", "happy_path", "critical"],
                )
            )

            scenarios.append(
                TestScenario(
                    name="Complete workflow with valid data",
                    category="happy_path",
                    description=f"Test complete workflow from start to finish with valid inputs. Goal: {goal}",
                    preconditions=["System initialized", "Test data prepared"],
                    steps=[
                        "Execute each step of the workflow",
                        "Verify each step completes successfully",
                        "Verify final state is as expected",
                    ],
                    expected_outcome="Complete workflow executes successfully",
                    priority="high",
                    tags=["workflow", "happy_path", "e2e"],
                )
            )
        else:
            # General happy path scenarios
            scenarios.append(
                TestScenario(
                    name="Basic functionality works as expected",
                    category="happy_path",
                    description=f"Test core functionality works with valid inputs. Goal: {goal}",
                    preconditions=["System is set up correctly"],
                    steps=[
                        "Provide valid input data",
                        "Execute main functionality",
                        "Verify output matches expectations",
                    ],
                    expected_outcome="System produces expected output",
                    priority="high",
                    tags=["core", "happy_path"],
                )
            )

        return scenarios

    def _generate_error_handling_scenarios(
        self,
        goal: str,
        success_criteria: str,
        is_api: bool,
    ) -> list[TestScenario]:
        """Generate error handling test scenarios."""
        scenarios = []

        if is_api:
            scenarios.append(
                TestScenario(
                    name="Invalid input returns appropriate error",
                    category="error_handling",
                    description="Test that invalid input data is rejected with clear error message",
                    preconditions=["System is running"],
                    steps=[
                        "Prepare request with invalid data",
                        "Send request to endpoint",
                        "Verify response status code is 400",
                        "Verify error message is clear and actionable",
                    ],
                    expected_outcome="System returns 400 Bad Request with clear error message",
                    priority="high",
                    tags=["api", "error_handling", "validation"],
                )
            )

            scenarios.append(
                TestScenario(
                    name="Malformed request is rejected",
                    category="error_handling",
                    description="Test that malformed requests are handled gracefully",
                    preconditions=["System is running"],
                    steps=[
                        "Send malformed request (invalid JSON, missing headers, etc.)",
                        "Verify system doesn't crash",
                        "Verify appropriate error code returned",
                    ],
                    expected_outcome="System handles malformed requests gracefully",
                    priority="medium",
                    tags=["api", "error_handling", "robustness"],
                )
            )
        else:
            scenarios.append(
                TestScenario(
                    name="Invalid input is handled gracefully",
                    category="error_handling",
                    description="Test that invalid inputs don't crash the system",
                    preconditions=["System initialized"],
                    steps=[
                        "Provide invalid input",
                        "Attempt to execute functionality",
                        "Verify error is caught and handled",
                        "Verify system remains stable",
                    ],
                    expected_outcome="System handles invalid input without crashing",
                    priority="high",
                    tags=["error_handling", "validation"],
                )
            )

        scenarios.append(
            TestScenario(
                name="Missing required data produces error",
                category="error_handling",
                description="Test that missing required fields are detected",
                preconditions=["System is ready"],
                steps=[
                    "Prepare request/input with missing required fields",
                    "Attempt operation",
                    "Verify error indicates missing fields",
                ],
                expected_outcome="System identifies and reports missing required data",
                priority="medium",
                tags=["error_handling", "validation"],
            )
        )

        return scenarios

    def _generate_boundary_scenarios(
        self,
        goal: str,
        success_criteria: str,
        is_api: bool,
    ) -> list[TestScenario]:
        """Generate boundary condition test scenarios."""
        scenarios = []

        scenarios.append(
            TestScenario(
                name="Empty input is handled correctly",
                category="boundary_conditions",
                description="Test system behavior with empty inputs",
                preconditions=["System ready"],
                steps=[
                    "Provide empty input",
                    "Execute operation",
                    "Verify appropriate handling (error or empty result)",
                ],
                expected_outcome="System handles empty input appropriately",
                priority="medium",
                tags=["boundary", "edge_case"],
            )
        )

        scenarios.append(
            TestScenario(
                name="Maximum size input is handled",
                category="boundary_conditions",
                description="Test system with maximum allowed input size",
                preconditions=["System ready", "Maximum limits known"],
                steps=[
                    "Prepare input at maximum allowed size",
                    "Execute operation",
                    "Verify system processes without error",
                ],
                expected_outcome="System handles maximum size input successfully",
                priority="medium",
                tags=["boundary", "limits"],
            )
        )

        if "paginat" in goal.lower() or "list" in goal.lower():
            scenarios.append(
                TestScenario(
                    name="Zero results returned correctly",
                    category="boundary_conditions",
                    description="Test pagination/listing with no results",
                    preconditions=["Database is empty or filter returns no results"],
                    steps=[
                        "Request list/page of items",
                        "Verify empty array returned",
                        "Verify proper pagination metadata",
                    ],
                    expected_outcome="Empty results handled correctly with proper response structure",
                    priority="medium",
                    tags=["boundary", "pagination"],
                )
            )

        return scenarios

    def _generate_security_scenarios(
        self,
        goal: str,
        success_criteria: str,
    ) -> list[TestScenario]:
        """Generate security test scenarios."""
        scenarios = []

        scenarios.append(
            TestScenario(
                name="Unauthorized access is blocked",
                category="security",
                description="Test that unauthenticated requests are rejected",
                preconditions=["System requires authentication"],
                steps=[
                    "Send request without credentials",
                    "Verify response is 401 Unauthorized",
                    "Verify no sensitive data leaked in error",
                ],
                expected_outcome="Unauthorized requests are rejected with 401",
                priority="high",
                tags=["security", "auth", "critical"],
            )
        )

        scenarios.append(
            TestScenario(
                name="Insufficient permissions denied",
                category="security",
                description="Test that users without proper permissions are blocked",
                preconditions=["System has role-based access control"],
                steps=[
                    "Authenticate as user without required permissions",
                    "Attempt restricted operation",
                    "Verify response is 403 Forbidden",
                ],
                expected_outcome="Users without permissions cannot access restricted operations",
                priority="high",
                tags=["security", "authorization", "rbac"],
            )
        )

        scenarios.append(
            TestScenario(
                name="SQL injection attempt is blocked",
                category="security",
                description="Test that SQL injection attacks are prevented",
                preconditions=["System uses database"],
                steps=[
                    "Prepare input with SQL injection payload",
                    "Submit malicious input",
                    "Verify injection is blocked",
                    "Verify database remains secure",
                ],
                expected_outcome="SQL injection attempts are prevented",
                priority="high",
                tags=["security", "injection", "database"],
            )
        )

        return scenarios

    def _generate_performance_scenarios(
        self,
        goal: str,
        success_criteria: str,
    ) -> list[TestScenario]:
        """Generate performance test scenarios."""
        scenarios = []

        scenarios.append(
            TestScenario(
                name="System handles concurrent requests",
                category="performance",
                description="Test system performance under concurrent load",
                preconditions=["System deployed", "Load testing tools available"],
                steps=[
                    "Generate multiple concurrent requests",
                    "Execute load test",
                    "Monitor response times and error rates",
                    "Verify performance meets requirements",
                ],
                expected_outcome="System handles concurrent requests within acceptable limits",
                priority="medium",
                tags=["performance", "load", "concurrency"],
            )
        )

        return scenarios

    def _generate_integration_scenarios(
        self,
        goal: str,
        success_criteria: str,
    ) -> list[TestScenario]:
        """Generate integration test scenarios."""
        scenarios = []

        scenarios.append(
            TestScenario(
                name="End-to-end workflow completes successfully",
                category="integration",
                description="Test complete workflow across all components",
                preconditions=["All components running", "Test data prepared"],
                steps=[
                    "Execute complete user workflow",
                    "Verify each component interaction",
                    "Verify data flows correctly",
                    "Verify final state is correct",
                ],
                expected_outcome="Complete workflow executes successfully across all components",
                priority="high",
                tags=["integration", "e2e", "workflow"],
            )
        )

        return scenarios
