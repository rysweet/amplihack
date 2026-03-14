"""E2E Outside-In Test Generator.

Automatically generates comprehensive end-to-end tests for multiple app types:
- Web apps: Playwright tests following outside-in testing methodology
- CLI apps: Gadugi YAML scenarios from command/arg definitions
- TUI apps: Gadugi YAML scenarios from widget/navigation analysis
- APIs: Gadugi YAML scenarios from OpenAPI/Swagger specs
- MCPs: Gadugi YAML scenarios from MCP tool definitions
"""

from .app_type_detector import detect_app_type
from .models import (
    APIConfig,
    AppType,
    Bug,
    BugSeverity,
    CLIConfig,
    GenerationConfig,
    LocatorStrategy,
    MCPConfig,
    StackConfig,
    TestCategory,
    TestGenerationResult,
    TUIConfig,
)
from .orchestrator import generate_e2e_tests, generate_tests

__all__ = [
    # Entry points
    "generate_tests",  # New unified entry point (all app types)
    "generate_e2e_tests",  # Original web-only entry point (backward compat)
    "detect_app_type",  # App type detection
    # App type
    "AppType",
    # Config models
    "StackConfig",  # Web
    "CLIConfig",  # CLI
    "TUIConfig",  # TUI
    "APIConfig",  # API
    "MCPConfig",  # MCP
    # Shared models
    "TestCategory",
    "LocatorStrategy",
    "TestGenerationResult",
    "GenerationConfig",
    "Bug",
    "BugSeverity",
]

__version__ = "0.2.0"
