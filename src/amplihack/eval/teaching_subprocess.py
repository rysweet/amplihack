"""Teaching subprocess for L7 teacher-student evaluation.

Runs as a subprocess to isolate the teaching session state.
The teacher learns from a knowledge base and stores what it teaches
in the same memory DB as the main eval agent, so the subsequent
testing phase can access the knowledge.

Philosophy: Subprocess isolation for clean state management.
"""

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path


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
        # First, learn all articles directly (teacher preparation)
        for kb_item in knowledge_base:
            agent.learn_from_content(kb_item)

        # Nested-loop guard — teaching_phase() cannot be called from async context
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass  # Safe — no loop running
        else:
            raise RuntimeError(
                "teaching_phase() cannot be called from an async context. "
                "It uses asyncio.run() internally."
            )

        from amplihack.llm.client import completion

        kb_text = "\n\n".join(knowledge_base)

        # Teacher generates a structured lesson
        teacher_prompt = f"""You are a teacher preparing a lesson from this knowledge base.
Create a structured lesson that covers ALL key facts, organized by topic.
For each topic, list the specific facts a student must learn.

Knowledge base:
{kb_text[:3000]}

Return a structured lesson plan with numbered key facts."""

        lesson = asyncio.run(
            completion(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert teacher creating a lesson plan.",
                    },
                    {"role": "user", "content": teacher_prompt},
                ],
                temperature=0.3,
            )
        )

        # Store the lesson as additional knowledge
        agent.learn_from_content(f"Teaching Summary:\n{lesson}")

        stats = agent.get_memory_stats()

        return {
            "status": "success",
            "turns": 1,
            "lesson_length": len(lesson),
            "total_facts": stats.get("total_experiences", 0),
        }

    except Exception as e:
        # REQ-DATA-2: log only the exception type — str(e) may contain knowledge-base
        # content or partial LLM prompts that must not be written to stdout.
        import logging

        logging.getLogger(__name__).warning("teaching_phase failed: %s", type(e).__name__)
        return {"status": "error", "turns": 0, "error": type(e).__name__}
    finally:
        agent.close()


def main():
    """Main entry point for subprocess."""
    import argparse

    parser = argparse.ArgumentParser(description="Teaching subprocess for L7 eval")
    parser.add_argument("--agent-name", required=True)

    args = parser.parse_args()

    input_data = json.load(sys.stdin)

    # REQ-DATA-2: knowledge_base is a required field — silent default to [] would
    # run a lesson against an empty corpus and return {"status": "success"}, producing
    # structurally valid but semantically corrupt output (forbidden silent degradation).
    if "knowledge_base" not in input_data or not input_data["knowledge_base"]:
        print(json.dumps({"status": "error", "error": "missing required field: knowledge_base"}))
        sys.exit(1)
    knowledge_base = input_data["knowledge_base"]
    max_turns = input_data.get("max_turns", 4)

    result = teaching_phase(knowledge_base, args.agent_name, max_turns)
    print(json.dumps(result))


if __name__ == "__main__":
    main()


__all__ = ["teaching_phase"]
