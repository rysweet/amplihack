"""Orchestration infrastructure for Claude processes.

This package provides the core infrastructure for orchestrating multiple Claude
CLI processes with different execution patterns (parallel, sequential, fallback).

Key Components:
    - ClaudeProcess: Manages a single Claude subprocess with output capture
    - ProcessResult: Result dataclass with exit code, output, duration
    - OrchestratorSession: Session management with logging and process factory
    - Execution helpers: run_parallel, run_sequential, run_with_fallback, run_batched

Example Usage:
    >>> from orchestration import OrchestratorSession, run_parallel
    >>>
    >>> # Create session
    >>> session = OrchestratorSession("multi-agent-analysis")
    >>>
    >>> # Create processes
    >>> processes = [
    ...     session.create_process("Analyze security", "security"),
    ...     session.create_process("Analyze performance", "performance"),
    ...     session.create_process("Analyze maintainability", "maintainability"),
    ... ]
    >>>
    >>> # Run in parallel
    >>> results = run_parallel(processes, max_workers=3)
    >>>
    >>> # Check results
    >>> for result in results:
    ...     if result.exit_code == 0:
    ...         print(f"{result.process_id}: SUCCESS")
    ...     else:
    ...         print(f"{result.process_id}: FAILED")

Module Structure:
    orchestration/
    ├── __init__.py          # This file - public exports
    ├── claude_process.py    # ClaudeProcess and ProcessResult
    ├── execution.py         # Execution helpers
    ├── session.py           # OrchestratorSession
    └── patterns/            # Reusable orchestration patterns
        └── __init__.py
"""

from .claude_process import ClaudeProcess, ProcessResult
from .execution import (
    run_batched,
    run_parallel,
    run_sequential,
    run_with_fallback,
)
from .session import OrchestratorSession

__all__ = [
    # Core classes
    "ClaudeProcess",
    "ProcessResult",
    "OrchestratorSession",
    # Execution helpers
    "run_parallel",
    "run_sequential",
    "run_with_fallback",
    "run_batched",
]
