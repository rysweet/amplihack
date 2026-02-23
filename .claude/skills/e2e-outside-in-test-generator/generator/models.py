"""Data models for E2E Outside-In Test Generator.

All dataclasses used throughout the test generation system.
Provides type-safe data structures with validation.
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class TestCategory(Enum):
    """Test categories for comprehensive coverage."""

    SMOKE = "smoke"
    FORM_INTERACTION = "form_interaction"
    COMPONENT_INTERACTION = "component_interaction"
    KEYBOARD_SHORTCUTS = "keyboard_shortcuts"
    API_STREAMING = "api_streaming"
    RESPONSIVE = "responsive"
    PWA_BASICS = "pwa_basics"


class LocatorStrategy(Enum):
    """Locator strategies in priority order."""

    ROLE_BASED = "role_based"  # getByRole()
    USER_VISIBLE_TEXT = "user_visible_text"  # getByText()
    TEST_ID = "test_id"  # getByTestId()
    CSS_SELECTOR = "css_selector"  # Fallback


class BugSeverity(Enum):
    """Bug severity levels."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class Field:
    """Database field definition."""

    name: str
    type: str
    required: bool = False
    default: Any | None = None


@dataclass
class Relationship:
    """Database relationship definition."""

    name: str
    target_model: str
    relationship_type: str  # "one-to-many", "many-to-one", "many-to-many"


@dataclass
class Model:
    """Database model definition."""

    name: str
    fields: list[Field]
    relationships: list[Relationship] = field(default_factory=list)


@dataclass
class Route:
    """Frontend route definition."""

    path: str
    component: str
    requires_auth: bool = False
    description: str = ""


@dataclass
class APIEndpoint:
    """Backend API endpoint definition."""

    path: str
    method: str
    requires_auth: bool = False
    request_schema: dict | None = None
    response_schema: dict | None = None
    description: str = ""


@dataclass
class StackConfig:
    """Complete stack configuration (merged frontend/backend/database)."""

    # Frontend (required fields)
    frontend_framework: str  # nextjs, react, vue, angular
    frontend_dir: Path
    # Backend (required fields)
    backend_framework: str  # fastapi, express, django, flask
    backend_dir: Path
    api_base_url: str
    # Database (required fields)
    database_type: str  # postgresql, mysql, mongodb, sqlite
    # Optional fields with defaults
    routes: list[Route] = field(default_factory=list)
    components: list[str] = field(default_factory=list)
    api_endpoints: list[APIEndpoint] = field(default_factory=list)
    schema_files: list[Path] = field(default_factory=list)
    models: list[Model] = field(default_factory=list)
    auth_mechanism: str = "none"


@dataclass
class StackDetectionResult:
    """Result of stack detection with confidence scores."""

    frontend_framework: str
    frontend_confidence: float  # 0.0 to 1.0
    backend_framework: str
    backend_confidence: float
    database_type: str
    database_confidence: float
    warnings: list[str] = field(default_factory=list)


@dataclass
class GeneratedTest:
    """Metadata for a generated test file."""

    category: TestCategory
    file_path: Path
    test_count: int
    description: str
    locator_strategies: list[LocatorStrategy] = field(default_factory=list)


@dataclass
class Bug:
    """Real bug found during testing."""

    severity: BugSeverity
    location: str
    description: str
    test_file: Path
    stack_trace: str = ""


@dataclass
class CoverageReport:
    """Test coverage analysis report."""

    total_tests: int
    category_breakdown: dict[str, int]
    route_coverage: dict[str, bool]
    endpoint_coverage: dict[str, bool]
    bugs_found: list[Bug]
    recommendations: list[str]
    route_coverage_percent: float = 0.0
    endpoint_coverage_percent: float = 0.0


@dataclass
class GenerationConfig:
    """Configuration for test generation."""

    max_tests_per_category: int = 10
    enable_fix_loop: bool = True
    max_fix_iterations: int = 5
    enable_coverage_audit: bool = True
    custom_templates: list[str] = field(default_factory=list)
    workers: int = 1  # MANDATORY: Must always be 1
    output_dir: str = "e2e"  # MANDATORY: Must be "e2e" not "tests/e2e"

    def __post_init__(self):
        """Validate configuration."""
        if self.workers != 1:
            raise ValueError("workers MUST be 1 for deterministic test execution")
        if self.output_dir != "e2e":
            raise ValueError("output_dir MUST be 'e2e' not 'tests/e2e'")


@dataclass
class TestGenerationResult:
    """Final result of test generation process."""

    success: bool
    total_tests: int
    bugs_found: list[Bug]
    coverage_report: CoverageReport
    execution_time: float
    error: str | None = None


# Exception classes for error handling


class E2EGeneratorError(Exception):
    """Base exception for E2E generator errors."""


class StackDetectionError(E2EGeneratorError):
    """Stack detection failed."""


class InfrastructureSetupError(E2EGeneratorError):
    """Infrastructure setup failed."""


class TestGenerationError(E2EGeneratorError):
    """Test generation failed."""


class CoverageAuditError(E2EGeneratorError):
    """Coverage audit failed."""


class TemplateNotFoundError(E2EGeneratorError):
    """Template not found."""


class FrontendAnalysisError(StackDetectionError):
    """Frontend analysis failed."""


class BackendAnalysisError(StackDetectionError):
    """Backend analysis failed."""


class DatabaseAnalysisError(StackDetectionError):
    """Database analysis failed."""
