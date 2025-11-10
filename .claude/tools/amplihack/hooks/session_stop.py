#!/usr/bin/env python3
"""
Memory System Session Stop Hook

Captures learnings from the session and stores them in Neo4j memory.
Extracts patterns, decisions, and outcomes for future agent use.
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
    """Capture session learnings and store in Neo4j."""
    try:
        # Import memory system
        from amplihack.memory.neo4j import lifecycle
        from amplihack.memory.neo4j.agent_integration import extract_and_store_learnings

        # Check if Neo4j is available
        if not lifecycle.is_neo4j_running():
            # Graceful degradation - no memory available
            return

        # Get session context from environment or stdin
        session_context = json.loads(sys.stdin.read()) if not sys.stdin.isatty() else {}

        # Extract agent type and output from context
        agent_type = session_context.get("agent_type", "general")
        agent_output = session_context.get("output", "")
        task_description = session_context.get("task", "")
        success = session_context.get("success", True)

        if not agent_output:
            # Nothing to learn from
            return

        # Extract and store learnings
        memory_ids = extract_and_store_learnings(
            agent_type=agent_type,
            output=agent_output,
            task=task_description,
            success=success,
            project_id=os.getenv("AMPLIHACK_PROJECT_ID", "amplihack"),
        )

        if memory_ids:
            print(f"[INFO] Stored {len(memory_ids)} learnings in Neo4j", file=sys.stderr)

    except Exception as e:
        # Don't fail session stop if memory capture fails
        print(f"[WARN] Memory capture failed: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
