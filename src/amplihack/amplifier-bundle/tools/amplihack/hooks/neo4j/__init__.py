"""
Neo4j integration module for Claude Code hooks.

Provides Neo4j-related functionality for session lifecycle management,
including learning capture during session stop.
"""

from .learning_capture import capture_neo4j_learnings

__all__ = ["capture_neo4j_learnings"]
