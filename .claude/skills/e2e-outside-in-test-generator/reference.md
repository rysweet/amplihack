# E2E Outside-In Test Generator - API Reference

Complete API reference for the E2E Outside-In Test Generator skill.

## Table of Contents

- [Public API](#public-api)
- [Data Models](#data-models)
- [Configuration](#configuration)
- [Template System](#template-system)
- [Error Handling](#error-handling)

## Public API

### Main Entry Point

#### `generate_e2e_tests()`

```python
def generate_e2e_tests(
    project_root: Path,
    config: Optional[GenerationConfig] = None
) -> TestGenerationResult
```

Main entry point for E2E test generation.

**Parameters:**

- `project_root` (Path): Path to project root directory
- `config` (GenerationConfig, optional): Custom configuration options

**Returns:**

- `TestGenerationResult`: Result object with test count, bugs found, coverage report

**Raises:**

- `StackDetectionError`: If unable to detect application stack
- `InfrastructureSetupError`: If infrastructure creation fails
- `TestGenerationError`: If test generation fails
- `FixLoopError`: If fix loop exceeds max iterations

**Example:**

```python
from pathlib import Path
from e2e_outside_in_test_generator import generate_e2e_tests

result = generate_e2e_tests(Path.cwd())

if result.success:
    print(f"Generated {result.total_tests} tests")
    print(f"Found {len(result.bugs_found)} bugs")
else:
    print(f"Generation failed: {result.error}")
```

### Stack Detection

#### `detect_stack()`

```python
def detect_stack(project_root: Path) -> StackConfig
```

Detects application stack configuration.

**Parameters:**

- `project_root` (Path): Path to project root

**Returns:**

- `StackConfig`: Detected stack configuration

**Raises:**

- `StackDetectionError`: If unable to detect stack

**Example:**

```python
from e2e_outside_in_test_generator.stack_detector import detect_stack

stack = detect_stack(Path.cwd())
print(f"Frontend: {stack.frontend_framework}")
print(f"Backend: {stack.backend_framework}")
print(f"Database: {stack.database_type}")
```

#### `analyze_frontend()`

```python
def analyze_frontend(frontend_dir: Path) -> FrontendConfig
```

Analyzes frontend framework and routes.

**Parameters:**

- `frontend_dir` (Path): Path to frontend directory

**Returns:**

- `FrontendConfig`: Frontend configuration with routes and components

**Raises:**

- `FrontendAnalysisError`: If analysis fails

#### `analyze_backend()`

```python
def analyze_backend(backend_dir: Path) -> BackendConfig
```

Analyzes backend API endpoints and structure.

**Parameters:**

- `backend_dir` (Path): Path to backend directory

**Returns:**

- `BackendConfig`: Backend configuration with endpoints and models

**Raises:**

- `BackendAnalysisError`: If analysis fails

#### `analyze_database()`

```python
def analyze_database(db_config: Path) -> DatabaseConfig
```

Analyzes database schema and models.

**Parameters:**

- `db_config` (Path): Path to database configuration or schema

**Returns:**

- `DatabaseConfig`: Database configuration with schema information

**Raises:**

- `DatabaseAnalysisError`: If analysis fails

### Infrastructure Setup

#### `setup_infrastructure()`

```python
def setup_infrastructure(
    stack: StackConfig,
    output_dir: Path
) -> None
```

Creates complete testing infrastructure.

**Parameters:**

- `stack` (StackConfig): Detected stack configuration
- `output_dir` (Path): Directory to create infrastructure in (typically `e2e/`)

**Raises:**

- `InfrastructureSetupError`: If setup fails

**Generated Files:**

- `playwright.config.ts`: Playwright configuration
- `test-helpers/auth.ts`: Authentication helpers
- `test-helpers/navigation.ts`: Navigation helpers
- `test-helpers/assertions.ts`: Custom assertions
- `test-helpers/data-setup.ts`: Test data management
- `fixtures/*.json`: Seed data files

#### `create_playwright_config()`

```python
def create_playwright_config(stack: StackConfig) -> str
```

Generates Playwright configuration with workers=1.

**Parameters:**

- `stack` (StackConfig): Stack configuration

**Returns:**

- str: Playwright config file content

#### `create_test_helpers()`

```python
def create_test_helpers(stack: StackConfig) -> Dict[str, str]
```

Generates helper functions for authentication, navigation, etc.

**Parameters:**

- `stack` (StackConfig): Stack configuration

**Returns:**

- Dict[str, str]: Mapping of helper file paths to content

#### `create_seed_data()`

```python
def create_seed_data(stack: StackConfig) -> Dict[str, str]
```

Generates small deterministic seed datasets.

**Parameters:**

- `stack` (StackConfig): Stack configuration

**Returns:**

- Dict[str, str]: Mapping of fixture file paths to content

### Test Generation

#### `generate_all_tests()`

```python
def generate_all_tests(
    stack: StackConfig,
    template_mgr: TemplateManager,
    output_dir: Path
) -> List[GeneratedTest]
```

Generates all test categories.

**Parameters:**

- `stack` (StackConfig): Stack configuration
- `template_mgr` (TemplateManager): Template manager instance
- `output_dir` (Path): Output directory for tests

**Returns:**

- List[GeneratedTest]: List of generated tests with metadata

**Raises:**

- `TestGenerationError`: If generation fails

#### Category-Specific Generation Functions

```python
def generate_happy_path_tests(stack: StackConfig) -> List[str]
```

Generates critical user journey tests.

```python
def generate_edge_case_tests(stack: StackConfig) -> List[str]
```

Generates boundary condition tests.

```python
def generate_error_handling_tests(stack: StackConfig) -> List[str]
```

Generates failure scenario tests.

```python
def generate_performance_tests(stack: StackConfig) -> List[str]
```

Generates speed validation tests.

```python
def generate_security_tests(stack: StackConfig) -> List[str]
```

Generates authorization/XSS tests.

```python
def generate_accessibility_tests(stack: StackConfig) -> List[str]
```

Generates WCAG compliance tests.

```python
def generate_integration_tests(stack: StackConfig) -> List[str]
```

Generates database/API integration tests.

### Fix Loop

#### `run_fix_loop()`

```python
def run_fix_loop(
    test_dir: Path,
    max_iterations: int = 5
) -> FixLoopResult
```

Runs tests and fixes failures iteratively.

**Parameters:**

- `test_dir` (Path): Directory containing tests
- `max_iterations` (int): Maximum fix attempts (default: 5)

**Returns:**

- `FixLoopResult`: Result with iterations count, pass rate, fixes applied

**Raises:**

- `FixLoopError`: If max iterations exceeded without success

#### `run_tests()`

```python
def run_tests(test_dir: Path) -> TestRunResult
```

Executes Playwright tests and collects results.

**Parameters:**

- `test_dir` (Path): Directory containing tests

**Returns:**

- `TestRunResult`: Test execution results

#### `analyze_failures()`

```python
def analyze_failures(failures: List[TestFailure]) -> List[FailurePattern]
```

Categorizes failures into patterns.

**Parameters:**

- `failures` (List[TestFailure]): List of test failures

**Returns:**

- List[FailurePattern]: Identified patterns

#### `apply_fixes()`

```python
def apply_fixes(patterns: List[FailurePattern]) -> List[Fix]
```

Applies automated fixes based on failure patterns.

**Parameters:**

- `patterns` (List[FailurePattern]): Failure patterns to fix

**Returns:**

- List[Fix]: Applied fixes

### Coverage Audit

#### `audit_coverage()`

```python
def audit_coverage(
    stack: StackConfig,
    generated_tests: List[GeneratedTest]
) -> CoverageReport
```

Analyzes test coverage and generates recommendations.

**Parameters:**

- `stack` (StackConfig): Stack configuration
- `generated_tests` (List[GeneratedTest]): Generated tests

**Returns:**

- `CoverageReport`: Coverage metrics and recommendations

#### `calculate_route_coverage()`

```python
def calculate_route_coverage(
    stack: StackConfig,
    tests: List[GeneratedTest]
) -> Dict[str, bool]
```

Maps routes to test coverage.

**Parameters:**

- `stack` (StackConfig): Stack configuration
- `tests` (List[GeneratedTest]): Generated tests

**Returns:**

- Dict[str, bool]: Mapping of routes to coverage status

#### `calculate_endpoint_coverage()`

```python
def calculate_endpoint_coverage(
    stack: StackConfig,
    tests: List[GeneratedTest]
) -> Dict[str, bool]
```

Maps API endpoints to test coverage.

**Parameters:**

- `stack` (StackConfig): Stack configuration
- `tests` (List[GeneratedTest]): Generated tests

**Returns:**

- Dict[str, bool]: Mapping of endpoints to coverage status

#### `identify_bugs()`

```python
def identify_bugs(test_results: TestRunResult) -> List[Bug]
```

Identifies real bugs from test failures.

**Parameters:**

- `test_results` (TestRunResult): Test execution results

**Returns:**

- List[Bug]: Identified bugs with severity and location

#### `generate_recommendations()`

```python
def generate_recommendations(coverage: CoverageReport) -> List[str]
```

Generates actionable recommendations.

**Parameters:**

- `coverage` (CoverageReport): Coverage report

**Returns:**

- List[str]: Recommendations for improving coverage

### Template Manager

#### `TemplateManager`

```python
class TemplateManager:
    def __init__(self):
        """Loads all templates from templates/ directory."""

    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Renders template with context data."""

    def register_template(self, name: str, template: str) -> None:
        """Registers custom template."""

    def list_templates(self) -> List[str]:
        """Returns list of available templates."""
```

**Methods:**

```python
def render(self, template_name: str, context: Dict[str, Any]) -> str
```

Renders template with context data.

**Parameters:**

- `template_name` (str): Name of template (e.g., "happy_path")
- `context` (Dict[str, Any]): Data to populate template

**Returns:**

- str: Rendered test code

**Raises:**

- `TemplateNotFoundError`: If template does not exist
- `TemplateRenderError`: If rendering fails

**Example:**

```python
from e2e_outside_in_test_generator.template_manager import TemplateManager

template_mgr = TemplateManager()
test_code = template_mgr.render("happy_path", {
    "feature_name": "User Login",
    "test_description": "user can login with valid credentials",
    "helpers": "login, logout",
    "helper_module": "auth",
    "test_body": "await login(page, 'test@example.com', 'Test123!');"
})
```

## Data Models

### StackConfig

```python
@dataclass
class StackConfig:
    """Complete application stack configuration."""

    frontend_framework: str  # nextjs, react, vue, angular
    frontend_dir: Path
    backend_framework: str  # fastapi, express, django, flask
    api_base_url: str
    database_type: str  # postgresql, mysql, mongodb, sqlite
    auth_mechanism: str  # jwt, session, oauth
    routes: List[Route]
    api_endpoints: List[APIEndpoint]
    models: List[Model]
```

### Route

```python
@dataclass
class Route:
    """Frontend route definition."""

    path: str  # Route path (e.g., "/products/:id")
    component: str  # Component name
    requires_auth: bool = False  # Auth requirement
    dynamic_segments: List[str] = field(default_factory=list)  # Dynamic path segments
```

### APIEndpoint

```python
@dataclass
class APIEndpoint:
    """Backend API endpoint definition."""

    path: str  # Endpoint path
    method: str  # HTTP method (GET, POST, PUT, DELETE, PATCH)
    requires_auth: bool = False  # Auth requirement
    request_schema: Optional[Dict] = None  # Request body schema
    response_schema: Optional[Dict] = None  # Response schema
    query_params: List[str] = field(default_factory=list)  # Query parameters
```

### Model

```python
@dataclass
class Model:
    """Database model definition."""

    name: str  # Model name
    fields: List[Field]  # Model fields
    relationships: List[Relationship]  # Model relationships
```

### Field

```python
@dataclass
class Field:
    """Database field definition."""

    name: str  # Field name
    type: str  # Field type (string, integer, boolean, etc.)
    required: bool = False  # Required field
    unique: bool = False  # Unique constraint
    default: Optional[Any] = None  # Default value
```

### Relationship

```python
@dataclass
class Relationship:
    """Database relationship definition."""

    type: str  # Relationship type (one-to-one, one-to-many, many-to-many)
    target_model: str  # Target model name
    foreign_key: Optional[str] = None  # Foreign key field
```

**Relationship Detection:**

During database analysis, relationships are inferred from:

- Foreign key constraints in schema
- ORM relationship definitions (SQLAlchemy, Prisma, TypeORM)
- Migration files

**Example detection from Prisma schema:**

```prisma
model User {
  id      Int      @id
  orders  Order[]  // Detected: one-to-many
}

model Order {
  id      Int   @id
  userId  Int
  user    User  @relation(fields: [userId], references: [id])
}
```

Maps to:

```python
Relationship(
    type="one-to-many",
    target_model="Order",
    foreign_key="userId"
)
```

### GeneratedTest

```python
@dataclass
class GeneratedTest:
    """Metadata for generated test."""

    category: str  # Test category
    file_path: Path  # Test file path
    test_count: int  # Number of tests in file
    description: str  # Test description
```

### TestGenerationResult

```python
@dataclass
class TestGenerationResult:
    """Result of test generation process."""

    success: bool  # Success status
    total_tests: int  # Total tests generated
    bugs_found: List[Bug]  # Bugs discovered
    coverage_report: CoverageReport  # Coverage analysis
    execution_time: float  # Total execution time in seconds
    error: Optional[str] = None  # Error message if failed
```

### Bug

```python
@dataclass
class Bug:
    """Discovered bug information."""

    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    location: str  # File:line where bug exists
    description: str  # Bug description
    test_file: Path  # Test that found the bug
    evidence: str  # Evidence/reproduction steps
    fix_suggestion: Optional[str] = None  # Suggested fix
```

### FixLoopResult

```python
@dataclass
class FixLoopResult:
    """Result of fix loop execution."""

    iterations: int  # Number of iterations run
    final_pass_rate: float  # Final pass rate (0.0-1.0)
    fixes_applied: List[Fix]  # All fixes applied
    initial_failures: int  # Initial failure count
    final_failures: int  # Final failure count
```

### Fix

```python
@dataclass
class Fix:
    """Applied fix information."""

    pattern: str  # Fix pattern (locator, timing, data, logic)
    file_path: Path  # File that was fixed
    description: str  # Fix description
    before: str  # Code before fix
    after: str  # Code after fix
```

### CoverageReport

```python
@dataclass
class CoverageReport:
    """Test coverage analysis report."""

    total_tests: int  # Total tests generated
    category_breakdown: Dict[str, int]  # Tests per category
    route_coverage: float  # Route coverage percentage
    endpoint_coverage: float  # API endpoint coverage percentage
    bugs_found: List[Bug]  # Discovered bugs
    recommendations: List[str]  # Actionable recommendations
    uncovered_routes: List[str]  # Routes without coverage
    uncovered_endpoints: List[str]  # Endpoints without coverage
```

### GenerationConfig

```python
@dataclass
class GenerationConfig:
    """Configuration options for test generation."""

    max_tests_per_category: int = 15  # Max tests per category
    enable_fix_loop: bool = True  # Enable automatic fix loop
    max_fix_iterations: int = 5  # Max fix loop iterations
    enable_coverage_audit: bool = True  # Enable coverage analysis
    custom_templates: List[str] = field(default_factory=list)  # Custom template names
    workers: int = 1  # MANDATORY: must be 1
    seed_data_size: int = 10  # Seed data record count (10-20)
    output_dir: str = "e2e"  # Output directory name
    locator_priority: List[str] = field(
        default_factory=lambda: ["role", "text", "testid", "css"]
    )  # Locator strategy priority
```

## Configuration

### Environment Variables

```bash
# Database configuration
DATABASE_URL=postgresql://user:pass@localhost:5432/testdb  # pragma: allowlist secret

# API configuration
API_BASE_URL=http://localhost:8000/api

# Frontend configuration
FRONTEND_URL=http://localhost:3000

# Test user credentials
TEST_USER_EMAIL=test@example.com
TEST_USER_PASSWORD=Test123!
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=Admin123!

# Playwright configuration
PLAYWRIGHT_WORKERS=1  # CRITICAL: must be 1
PLAYWRIGHT_TIMEOUT=30000  # Per-test timeout (ms)
PLAYWRIGHT_RETRIES=2  # Number of retries on failure
```

### Playwright Configuration Options

```typescript
// e2e/playwright.config.ts
export default defineConfig({
  // Test execution
  testDir: "./e2e",
  fullyParallel: false, // MANDATORY: sequential execution
  workers: 1, // MANDATORY: prevents data races
  retries: process.env.CI ? 2 : 0,

  // Timeouts
  timeout: 30000, // Per-test timeout (30s)
  expect: {
    timeout: 5000, // Assertion timeout (5s)
  },

  // Artifacts
  use: {
    baseURL: "http://localhost:3000",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    trace: "on-first-retry",
    testIdAttribute: "data-testid", // Custom test ID attribute
  },

  // Projects
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],

  // Web server
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120000,
  },
});
```

## Template System

### Template Format

Templates use Python `.format()` style placeholders:

```python
TEMPLATE = """
import {{ test, expect }} from '@playwright/test';
import {{ {helpers} }} from '../test-helpers/{helper_module}';

test.describe('{feature_name}', () => {{
  test('{test_description}', async ({{ page }}) => {{
    {test_body}
  }});
}});
"""
```

### Template Variables

| Variable             | Type | Description                    |
| -------------------- | ---- | ------------------------------ |
| `{feature_name}`     | str  | Feature being tested           |
| `{test_description}` | str  | Test description               |
| `{helpers}`          | str  | Comma-separated helper imports |
| `{helper_module}`    | str  | Helper module name             |
| `{test_body}`        | str  | Test implementation code       |
| `{setup_code}`       | str  | Setup code in beforeEach       |
| `{arrange_code}`     | str  | Arrange section (AAA pattern)  |
| `{act_code}`         | str  | Act section (AAA pattern)      |
| `{assert_code}`      | str  | Assert section (AAA pattern)   |

### Custom Template Registration

```python
from e2e_outside_in_test_generator.template_manager import TemplateManager

CUSTOM_TEMPLATE = """
import {{ test, expect }} from '@playwright/test';

test('{test_name}', async ({{ page }}) => {{
  // Custom test structure
  {custom_code}
}});
"""

template_mgr = TemplateManager()
template_mgr.register_template("custom", CUSTOM_TEMPLATE)

test_code = template_mgr.render("custom", {
    "test_name": "my custom test",
    "custom_code": "await page.goto('/custom');"
})
```

## Error Handling

### Exception Hierarchy

```
E2ETestGeneratorError (base)
├── StackDetectionError
│   ├── FrontendAnalysisError
│   ├── BackendAnalysisError
│   └── DatabaseAnalysisError
├── InfrastructureSetupError
├── TestGenerationError
│   └── TemplateRenderError
├── FixLoopError
│   ├── TestExecutionError
│   ├── FailureAnalysisError
│   └── FixApplicationError
└── CoverageAuditError
```

### Exception Details

#### `E2ETestGeneratorError`

Base exception for all generator errors.

```python
class E2ETestGeneratorError(Exception):
    """Base exception for E2E test generator."""
    pass
```

#### `StackDetectionError`

Raised when stack detection fails.

```python
class StackDetectionError(E2ETestGeneratorError):
    """Unable to detect application stack."""

    def __init__(self, message: str, missing_files: List[str]):
        super().__init__(message)
        self.missing_files = missing_files
```

#### `InfrastructureSetupError`

Raised when infrastructure setup fails.

```python
class InfrastructureSetupError(E2ETestGeneratorError):
    """Failed to create testing infrastructure."""

    def __init__(self, message: str, failed_files: List[str]):
        super().__init__(message)
        self.failed_files = failed_files
```

#### `TestGenerationError`

Raised when test generation fails.

```python
class TestGenerationError(E2ETestGeneratorError):
    """Failed to generate tests."""

    def __init__(self, message: str, category: str):
        super().__init__(message)
        self.category = category
```

#### `FixLoopError`

Raised when fix loop fails or exceeds max iterations.

```python
class FixLoopError(E2ETestGeneratorError):
    """Fix loop failed or exceeded max iterations."""

    def __init__(self, message: str, iterations: int, failures: int):
        super().__init__(message)
        self.iterations = iterations
        self.failures = failures
```

### Error Recovery

```python
from e2e_outside_in_test_generator import generate_e2e_tests
from e2e_outside_in_test_generator.models import StackDetectionError

try:
    result = generate_e2e_tests(Path.cwd())
except StackDetectionError as e:
    print(f"Stack detection failed. Missing files: {e.missing_files}")
    # Provide manual stack configuration
except InfrastructureSetupError as e:
    print(f"Infrastructure setup failed. Failed files: {e.failed_files}")
    # Retry infrastructure setup
except FixLoopError as e:
    print(f"Fix loop exceeded {e.iterations} iterations with {e.failures} failures")
    # Review failures manually
except E2ETestGeneratorError as e:
    print(f"Generation failed: {e}")
    # General error handling
```

---

**See also:**

- [SKILL.md](./SKILL.md) - Complete skill documentation
- [README.md](./README.md) - Developer documentation
- [examples.md](./examples.md) - Usage examples
- [patterns.md](./patterns.md) - Common patterns
