#!/usr/bin/env python3
"""
Memory System Session Stop Hook

Captures learnings from the session and stores them using MemoryCoordinator.
Extracts patterns, decisions, and outcomes for future agent use.
Works with SQLite or Neo4j backend.
"""

import json
import os
import sys
from pathlib import Path

# Add project src to path
current = Path(__file__).resolve()
project_root = None
for parent in current.parents:
    if (parent / ".claude").exists() and (parent / "CLAUDE.md").exists():
        project_root = parent
        break
if project_root is None:
    print("[WARN] Could not locate project root", file=sys.stderr)
    sys.exit(0)  # Graceful exit if can't find project

sys.path.insert(0, str(project_root / "src"))


def main():
    """Capture session learnings and store using MemoryCoordinator."""
    try:
        # Import memory coordinator
        from amplihack.memory.coordinator import MemoryCoordinator
        from amplihack.memory.types import MemoryType

        # Get session context from environment or stdin
        session_context = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else {}

        # Extract agent type and output from context
        agent_type = session_context.get("agent_type", "general")
        agent_output = session_context.get("output", "")
        task_description = session_context.get("task", "")
        success = session_context.get("success", True)
        session_id = session_context.get("session_id", "hook_session")

        if not agent_output:
            # Nothing to learn from
            return

        # Initialize coordinator with session_id
        coordinator = MemoryCoordinator(session_id=session_id)

        # Store learning as SEMANTIC memory (reusable knowledge)
        # Extract key learnings (simplified - production would use more sophisticated extraction)
        learning_content = f"Agent {agent_type}: {agent_output[:500]}"

        memory_id = coordinator.store(
            content=learning_content,
            memory_type=MemoryType.SEMANTIC,
            agent_type=agent_type,
            tags=["learning", "session_end"],
            metadata={
                "task": task_description,
                "success": success,
                "project_id": os.getenv("AMPLIHACK_PROJECT_ID", "amplihack"),
            },
        )

        if memory_id:
            print("[INFO] Stored 1 learning in memory system", file=sys.stderr)

    except Exception as e:
        # Don't fail session stop if memory capture fails
        print(f"[WARN] Memory capture failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
