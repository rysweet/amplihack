"""Meta-Agentic Task Delegation System.

This package provides a meta-delegation system that spawns AI coding assistants
as subprocesses, manages their execution, collects evidence, and evaluates
success against criteria.

Main Entry Point:
    run_meta_delegation: Delegate task to AI assistant subprocess

Key Components:
    - Platform CLI Abstraction: Unified interface for Claude Code, Copilot, Amplifier
    - State Machine: Subprocess lifecycle management
    - Persona Strategies: Behavioral patterns (guide, qa_engineer, architect, junior_dev)
    - Evidence Collector: Artifact collection and organization
    - Success Evaluator: Criteria-based scoring
    - Scenario Generator: Gadugi test scenario generation
    - Orchestrator: Complete delegation coordination

Example Usage:
    >>> from amplihack.meta_delegation import run_meta_delegation
    >>>
    >>> result = run_meta_delegation(
    ...     goal="Create a user authentication system",
    ...     success_criteria="System has login/logout, JWT tokens, tests",
    ...     persona_type="architect",
    ... )
    >>>
    >>> print(f"Status: {result.status}")
    >>> print(f"Score: {result.success_score}/100")
    >>> print(f"Evidence collected: {len(result.evidence)} items")

Philosophy:
    - Ruthless simplicity: Each module has ONE clear job
    - Brick & studs: Self-contained modules with clear contracts
    - Zero-BS: No stubs, placeholders, or TODOs
    - Standard library preferred: Minimize dependencies
"""

# Main entry point
from .orchestrator import (
    DelegationError,
    DelegationTimeout,
    MetaDelegationOrchestrator,
    MetaDelegationResult,
    run_meta_delegation,
)

# Core modules (for advanced usage)
from .evidence_collector import EVIDENCE_PATTERNS, EvidenceCollector, EvidenceItem
from .persona import (
    ARCHITECT,
    GUIDE,
    JUNIOR_DEV,
    QA_ENGINEER,
    PersonaStrategy,
    get_persona_strategy,
    register_persona,
)
from .platform_cli import (
    AmplifierCLI,
    ClaudeCodeCLI,
    CopilotCLI,
    PlatformCLI,
    get_platform_cli,
    register_platform,
)
from .scenario_generator import (
    GadugiScenarioGenerator,
    ScenarioCategory,
    TestScenario,
)
from .state_machine import (
    ProcessState,
    StateTransitionError,
    SubprocessStateMachine,
)
from .success_evaluator import (
    EvaluationResult,
    SuccessCriteriaEvaluator,
    parse_success_criteria,
)

# Public API
__all__ = [
    # Main entry point
    "run_meta_delegation",
    "MetaDelegationResult",
    "MetaDelegationOrchestrator",
    "DelegationTimeout",
    "DelegationError",
    # Personas
    "PersonaStrategy",
    "GUIDE",
    "QA_ENGINEER",
    "ARCHITECT",
    "JUNIOR_DEV",
    "get_persona_strategy",
    "register_persona",
    # Platform CLI
    "PlatformCLI",
    "ClaudeCodeCLI",
    "CopilotCLI",
    "AmplifierCLI",
    "get_platform_cli",
    "register_platform",
    # State Machine
    "ProcessState",
    "SubprocessStateMachine",
    "StateTransitionError",
    # Evidence Collection
    "EvidenceCollector",
    "EvidenceItem",
    "EVIDENCE_PATTERNS",
    # Success Evaluation
    "SuccessCriteriaEvaluator",
    "EvaluationResult",
    "parse_success_criteria",
    # Scenario Generation
    "GadugiScenarioGenerator",
    "TestScenario",
    "ScenarioCategory",
]

__version__ = "0.1.0"
__author__ = "Amplihack Team"
__description__ = "Meta-agentic task delegation system for AI coding assistants"
