"""Teaching subprocess for L7 teacher-student evaluation.

Runs as a subprocess to isolate the teaching session state.
The teacher learns from a knowledge base and stores what it teaches
in the same memory DB as the main eval agent, so the subsequent
testing phase can access the knowledge.

Philosophy: Subprocess isolation for clean state management.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from amplihack.agents.goal_seeking import LearningAgent


def teaching_phase(knowledge_base: list[str], agent_name: str, max_turns: int = 4) -> dict:
    """Run teaching phase: teacher teaches student using knowledge base.

    The teacher generates teaching messages from the knowledge base,
    and the student responds with understanding. Key facts from the
    teaching dialogue are stored in the agent's memory for later testing.

    Args:
        knowledge_base: List of knowledge strings to teach from
        agent_name: Agent identifier (shared with testing phase)
        max_turns: Number of teaching turns

    Returns:
        Status dict with teaching session metrics
    """
    from amplihack.agents.goal_seeking import LearningAgent

    storage_path = Path(tempfile.gettempdir()) / "amplihack_eval" / agent_name
    storage_path.mkdir(parents=True, exist_ok=True)

    model = os.environ.get("EVAL_MODEL", "claude-opus-4-6")

    # Create learning agent - same agent that will be used in testing phase
    agent = LearningAgent(
        agent_name=agent_name,
        model=model,
        storage_path=storage_path,
        use_hierarchical=True,
    )

    try:
        import asyncio

        result = asyncio.run(_async_teaching_phase(agent, knowledge_base, model))
        return result

    except Exception as e:
        return {"status": "error", "turns": 0, "error": str(e)}
    finally:
        agent.close()


async def _async_teaching_phase(
    agent: LearningAgent, knowledge_base: list[str], model: str
) -> dict:
    """Async helper that runs all async LearningAgent + LLM calls in one event loop."""
    # First, learn all articles directly (teacher preparation)
    for kb_item in knowledge_base:
        await agent.learn_from_content(kb_item)

    # Then run a simplified teaching dialogue
    # The teacher extracts key concepts and stores teaching summaries
    kb_text = "\n\n".join(knowledge_base)

    # Teacher generates a structured lesson
    teacher_prompt = f"""You are a teacher preparing a lesson from this knowledge base.
Create a structured lesson that covers ALL key facts, organized by topic.
For each topic, list the specific facts a student must learn.

Knowledge base:
{kb_text[:3000]}

Return a structured lesson plan with numbered key facts."""

    lesson = await _generate_lesson(model, teacher_prompt)

    # Store the lesson as additional knowledge
    await agent.learn_from_content(f"Teaching Summary:\n{lesson}")

    stats = agent.get_memory_stats()

    return {
        "status": "success",
        "turns": 1,
        "lesson_length": len(lesson),
        "total_facts": stats.get("total_experiences", 0),
    }


async def _generate_lesson(model: str, teacher_prompt: str) -> str:
    """Generate a lesson plan via the LLM adapter."""
    from amplihack.llm import completion

    response_text = await completion(
        [
            {"role": "system", "content": "You are an expert teacher creating a lesson plan."},
            {"role": "user", "content": teacher_prompt},
        ],
        model=model,
        temperature=0.3,
    )
    return response_text.strip()


def main():
    """Main entry point for subprocess."""
    import argparse

    parser = argparse.ArgumentParser(description="Teaching subprocess for L7 eval")
    parser.add_argument("--agent-name", required=True)

    args = parser.parse_args()

    input_data = json.load(sys.stdin)

    knowledge_base = input_data.get("knowledge_base", [])
    max_turns = input_data.get("max_turns", 4)

    result = teaching_phase(knowledge_base, args.agent_name, max_turns)
    print(json.dumps(result))


if __name__ == "__main__":
    main()


__all__ = ["teaching_phase"]
