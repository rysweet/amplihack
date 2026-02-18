"""Agent subprocess for learning and testing phases.

Runs as a subprocess with memory isolation.
Philosophy: Stateless within each phase, state persists via memory backend.
"""

import json
import sys

from amplihack_memory import (  # type: ignore[import-untyped]
    Experience,
    ExperienceType,
    MemoryConnector,
)


def learning_phase(news_articles: list[dict], agent_name: str) -> dict:
    """Learning phase: Store news articles in memory.

    Args:
        news_articles: List of article dicts
        agent_name: Agent identifier

    Returns:
        Status dict with count of stored experiences
    """
    connector = MemoryConnector(agent_name=agent_name)

    stored_count = 0
    for article in news_articles:
        # Store article as an experience (use SUCCESS type)
        experience = Experience(
            experience_type=ExperienceType.SUCCESS,
            context=f"Article: {article['title']}",
            outcome=article["content"],
            confidence=1.0,
            metadata=json.dumps({"url": article["url"], "published": article["published"]}),
        )

        exp_id = connector.store_experience(experience)
        if exp_id:
            stored_count += 1

    return {"status": "success", "stored_count": stored_count, "total_articles": len(news_articles)}


def testing_phase(quiz_questions: list[dict], agent_name: str) -> dict:
    """Testing phase: Answer questions using memory.

    Args:
        quiz_questions: List of question dicts
        agent_name: Agent identifier

    Returns:
        Status dict with answers
    """
    connector = MemoryConnector(agent_name=agent_name)

    # Retrieve all stored experiences
    memories = connector.retrieve_experiences(limit=100)

    answers = []
    for question_data in quiz_questions:
        question = question_data["question"]

        # Formulate answer based on memories
        if memories:
            # Combine relevant context from memories (simplified - use all memories)
            context_parts = [m.outcome[:200] for m in memories[:3]]
            answer = " ".join(context_parts)
            confidence = sum(m.confidence for m in memories[:3]) / min(len(memories), 3)
        else:
            answer = "No relevant information found in memory"
            confidence = 0.0

        answers.append(
            {
                "question": question,
                "answer": answer,
                "confidence": confidence,
                "memories_used": len(memories),
            }
        )

    return {"status": "success", "answers": answers}


def main():
    """Main entry point for subprocess."""
    import argparse

    parser = argparse.ArgumentParser(description="Agent subprocess for eval harness")
    parser.add_argument("--phase", required=True, choices=["learning", "testing"])
    parser.add_argument("--agent-name", required=True)
    parser.add_argument("--input-file", help="Input JSON file (alternative to stdin)")

    args = parser.parse_args()

    # Read input data
    if args.input_file:
        with open(args.input_file) as f:
            input_data = json.load(f)
    else:
        input_data = json.load(sys.stdin)

    # Execute phase
    if args.phase == "learning":
        result = learning_phase(input_data, args.agent_name)
    else:  # testing
        result = testing_phase(input_data, args.agent_name)

    # Output result as JSON
    print(json.dumps(result))


if __name__ == "__main__":
    main()


__all__ = ["learning_phase", "testing_phase"]
