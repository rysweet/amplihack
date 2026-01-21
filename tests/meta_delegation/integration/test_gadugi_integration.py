"""Integration tests for Gadugi scenario generator with success evaluator.

Tests how generated scenarios integrate with evidence collection and evaluation.
"""

import pytest

# These imports will fail until implementation exists
try:
    from amplihack.meta_delegation.evidence_collector import EvidenceCollector, EvidenceItem
    from amplihack.meta_delegation.scenario_generator import GadugiScenarioGenerator
    from amplihack.meta_delegation.success_evaluator import SuccessCriteriaEvaluator
except ImportError:
    pytest.skip("Required modules not implemented yet", allow_module_level=True)


@pytest.mark.integration
class TestGadugiScenarioGenerationAndEvaluation:
    """Test scenario generation integrated with evaluation."""

    @pytest.fixture
    def generator(self):
        return GadugiScenarioGenerator()

    @pytest.fixture
    def evaluator(self):
        return SuccessCriteriaEvaluator()

    def test_generated_scenarios_align_with_success_criteria(self, generator, evaluator):
        """Test generated scenarios align with success criteria."""
        goal = "Create user authentication API"
        success_criteria = """
        - Has login endpoint
        - Has registration endpoint
        - Returns JWT tokens
        - Has comprehensive tests
        """

        scenarios = generator.generate_scenarios(goal, success_criteria)

        # Scenarios should reflect success criteria requirements
        scenario_text = " ".join([s.name + s.description for s in scenarios]).lower()

        assert "login" in scenario_text or "auth" in scenario_text
        assert "registration" in scenario_text or "register" in scenario_text
        assert "token" in scenario_text or "jwt" in scenario_text

    def test_scenario_categories_support_comprehensive_evaluation(self, generator):
        """Test scenario categories enable comprehensive evaluation."""
        goal = "Create API endpoint"
        success_criteria = "Endpoint handles all cases correctly"

        scenarios = generator.generate_scenarios(goal, success_criteria)

        categories = set(s.category for s in scenarios)

        # Should have multiple categories for comprehensive testing
        assert len(categories) >= 3

        # Should cover major testing categories
        category_list = list(categories)
        assert any("happy" in cat or "success" in cat for cat in category_list)
        assert any("error" in cat for cat in category_list)

    def test_high_priority_scenarios_validated_first(self, generator, evaluator):
        """Test high priority scenarios are emphasized in evaluation."""
        goal = "Create payment processing API"
        success_criteria = "Process payments securely and reliably"

        scenarios = generator.generate_scenarios(goal, success_criteria)

        high_priority = [s for s in scenarios if s.priority == "high"]

        # Critical systems should have many high-priority scenarios
        assert len(high_priority) >= 3

        # High priority should include security scenarios
        high_priority_categories = [s.category for s in high_priority]
        assert any("security" in cat or "error" in cat for cat in high_priority_categories)


@pytest.mark.integration
class TestGadugiWithEvidenceCollection:
    """Test scenario generation with evidence collection."""

    @pytest.fixture
    def generator(self):
        return GadugiScenarioGenerator()

    @pytest.fixture
    def test_workspace(self, tmp_path):
        """Create workspace with test results."""
        workspace = tmp_path / "test_results"
        workspace.mkdir()

        # Create test result files based on scenarios
        (workspace / "test_login_success.py").write_text(
            """
def test_valid_login():
    \"\"\"Test successful login with valid credentials.\"\"\"
    response = login("user@example.com", "password123")
    assert response.status_code == 200
    assert "token" in response.json()
"""
        )

        (workspace / "test_login_errors.py").write_text(
            """
def test_invalid_password():
    \"\"\"Test login with invalid password.\"\"\"
    response = login("user@example.com", "wrongpassword")
    assert response.status_code == 401

def test_nonexistent_user():
    \"\"\"Test login with non-existent user.\"\"\"
    response = login("nobody@example.com", "password")
    assert response.status_code == 401
"""
        )

        (workspace / "test_results.txt").write_text(
            """
PASS test_login_success.py::test_valid_login
PASS test_login_errors.py::test_invalid_password
PASS test_login_errors.py::test_nonexistent_user
All tests passed (3/3)
"""
        )

        return workspace

    def test_scenarios_validated_against_evidence(self, generator, test_workspace):
        """Test generated scenarios can be validated against evidence."""
        goal = "Create login endpoint"
        success_criteria = "Endpoint handles valid and invalid credentials"

        scenarios = generator.generate_scenarios(goal, success_criteria)

        # Collect evidence
        collector = EvidenceCollector(working_directory=str(test_workspace))
        evidence = collector.collect_evidence()

        # Check if evidence covers generated scenarios
        test_files = [e for e in evidence if e.type == "test_file"]
        assert len(test_files) >= 2

        # Test content should align with scenario categories
        test_content = " ".join([e.content for e in test_files])
        assert "test_valid" in test_content.lower() or "success" in test_content.lower()
        assert "test_invalid" in test_content.lower() or "error" in test_content.lower()

    def test_scenario_coverage_measured_by_evidence(self, generator, test_workspace):
        """Test scenario coverage can be measured from evidence."""
        goal = "Create authentication system"
        success_criteria = "Comprehensive test coverage"

        scenarios = generator.generate_scenarios(goal, success_criteria)

        # Collect evidence
        collector = EvidenceCollector(working_directory=str(test_workspace))
        evidence = collector.collect_evidence()

        # Count covered scenarios by matching test names to scenario categories
        test_files = [e for e in evidence if e.type == "test_file"]

        scenario_categories = set(s.category for s in scenarios)

        # Should have evidence for multiple scenario categories
        # (In real implementation, would match test names to scenarios)
        assert len(test_files) > 0
        assert len(scenario_categories) >= 2


@pytest.mark.integration
class TestGadugiEndToEndValidation:
    """Test end-to-end scenario generation through evaluation."""

    @pytest.fixture
    def full_test_system(self, tmp_path):
        """Create complete test system with implementation and tests."""
        system = tmp_path / "auth_system"
        system.mkdir()

        # Implementation
        (system / "auth.py").write_text(
            """
import jwt
from datetime import datetime, timedelta

def login(email: str, password: str) -> dict:
    # Simplified authentication
    if email and password:
        token = generate_token(email)
        return {"status": "success", "token": token}
    return {"status": "error", "message": "Invalid credentials"}

def generate_token(email: str) -> str:
    payload = {"email": email, "exp": datetime.utcnow() + timedelta(hours=1)}
    return jwt.encode(payload, "secret", algorithm="HS256")
"""
        )

        # Comprehensive tests
        (system / "test_auth.py").write_text(
            """
import pytest
from auth import login, generate_token

# Happy path
def test_successful_login():
    result = login("user@test.com", "password123")
    assert result["status"] == "success"
    assert "token" in result

# Error handling
def test_empty_credentials():
    result = login("", "")
    assert result["status"] == "error"

def test_invalid_email():
    result = login("invalid", "password")
    # Should handle gracefully

# Security
def test_token_expiration():
    token = generate_token("user@test.com")
    assert token is not None

# Boundary conditions
def test_very_long_password():
    result = login("user@test.com", "x" * 1000)
    assert result is not None
"""
        )

        # Test results
        (system / "test_results.log").write_text(
            """
PASS test_auth.py::test_successful_login
PASS test_auth.py::test_empty_credentials
PASS test_auth.py::test_invalid_email
PASS test_auth.py::test_token_expiration
PASS test_auth.py::test_very_long_password
5 passed in 0.12s
"""
        )

        # Documentation
        (system / "README.md").write_text(
            """
# Authentication System

## Features
- Login with email/password
- JWT token generation
- Comprehensive test coverage

## Usage
```python
from auth import login
result = login("user@example.com", "password")
```
"""
        )

        return system

    def test_complete_scenario_validation_workflow(self, full_test_system):
        """Test complete workflow from scenario generation to validation."""
        generator = GadugiScenarioGenerator()
        collector = EvidenceCollector(working_directory=str(full_test_system))
        evaluator = SuccessCriteriaEvaluator()

        # Generate scenarios
        goal = "Create authentication system with JWT tokens"
        success_criteria = """
        - Has login function
        - Generates JWT tokens
        - Has comprehensive tests covering happy path, errors, security
        - Tests pass
        - Has documentation
        """

        scenarios = generator.generate_scenarios(goal, success_criteria)

        # Collect evidence
        evidence = collector.collect_evidence()

        # Evaluate success
        execution_log = (full_test_system / "test_results.log").read_text()
        result = evaluator.evaluate(success_criteria, evidence, execution_log)

        # Validation
        assert len(scenarios) >= 10, "Should generate comprehensive scenarios"
        assert len(evidence) >= 4, "Should collect multiple evidence types"
        assert result.score >= 80, "Should score high with complete implementation"

        # Verify scenario categories are represented in evidence
        scenario_categories = set(s.category for s in scenarios)
        assert len(scenario_categories) >= 3

        # Verify evidence types align with requirements
        evidence_types = set(e.type for e in evidence)
        assert "code_file" in evidence_types
        assert "test_file" in evidence_types
        assert "documentation" in evidence_types

    def test_scenario_driven_evaluation_identifies_gaps(self):
        """Test scenarios help identify gaps in implementation."""
        from datetime import datetime

        generator = GadugiScenarioGenerator()
        evaluator = SuccessCriteriaEvaluator()

        goal = "Create user registration API"
        success_criteria = """
        - Has registration endpoint
        - Validates email format
        - Handles duplicate users
        - Has security measures
        - Has comprehensive tests
        """

        scenarios = generator.generate_scenarios(goal, success_criteria)

        # Incomplete evidence (missing security tests)
        incomplete_evidence = [
            EvidenceItem(
                type="code_file",
                path="register.py",
                content="def register(email): return True",
                excerpt="def register...",
                size_bytes=50,
                timestamp=datetime.now(),
                metadata={},
            ),
            EvidenceItem(
                type="test_file",
                path="test_register.py",
                content="def test_register(): assert register('email@test.com')",
                excerpt="def test...",
                size_bytes=60,
                timestamp=datetime.now(),
                metadata={},
            ),
        ]

        execution_log = "PASS test_register.py\n1 passed"

        result = evaluator.evaluate(success_criteria, incomplete_evidence, execution_log)

        # Should identify gaps
        assert result.score < 80, "Should score lower with missing security coverage"

        # Check if security scenarios exist but aren't covered
        security_scenarios = [s for s in scenarios if s.category == "security"]
        assert len(security_scenarios) > 0, "Should generate security scenarios"
