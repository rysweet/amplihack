"""Reusable orchestration patterns.

This package contains pre-built orchestration patterns that combine
the core orchestration infrastructure in common ways.

Implemented patterns:
- N-Version Programming: Generate multiple independent implementations and select best
- Multi-Agent Debate: Structured debate with multiple perspectives for decisions
- Fallback Cascade: Graceful degradation through cascading fallback strategies

Each pattern is a self-contained module that:
1. Takes high-level inputs (prompts, configs)
2. Creates appropriate ClaudeProcess instances
3. Orchestrates execution with the right strategy
4. Returns structured results

Example usage:
    from .n_version import run_n_version
    from .debate import run_debate
    from .cascade import run_cascade

    # N-Version Programming
    result = run_n_version("Implement password hashing", n=3)

    # Multi-Agent Debate
    result = run_debate("Should we use PostgreSQL or Redis?", rounds=3)

    # Fallback Cascade
    result = run_cascade("Generate docs", timeout_strategy="balanced")
"""

from .cascade import create_custom_cascade, run_cascade
from .debate import run_debate
from .n_version import run_n_version

__all__ = [
    "run_n_version",
    "run_debate",
    "run_cascade",
    "create_custom_cascade",
]
