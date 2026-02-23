"""E2E Outside-In Test Generator.

Automatically generates comprehensive Playwright end-to-end tests
for full-stack applications following outside-in testing methodology.
"""

from .models import (
    Bug,
    BugSeverity,
    GenerationConfig,
    LocatorStrategy,
    StackConfig,
    TestCategory,
    TestGenerationResult,
)
from .orchestrator import generate_e2e_tests

__all__ = [
    "generate_e2e_tests",
    "TestCategory",
    "LocatorStrategy",
    "StackConfig",
    "TestGenerationResult",
    "GenerationConfig",
    "Bug",
    "BugSeverity",
]

__version__ = "0.1.0"
