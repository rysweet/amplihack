"""Agent subprocess for learning and testing phases.

Runs as a subprocess with memory isolation.
Philosophy: Stateless within each phase, state persists via memory backend.
Now uses LearningAgent with HierarchicalMemory for enhanced knowledge retrieval.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

from amplihack.agents.goal_seeking import LearningAgent


def _compute_dynamic_confidence(trace, stats: dict, level: str) -> float:
    """Compute dynamic confidence based on fact coverage and reasoning trace.

    Rather than hardcoding 0.8, estimate actual confidence based on:
    - Number of facts available vs expected
    - Whether the trace used simple or iterative path
    - Level complexity (L1 is simpler = higher base confidence)

    Args:
        trace: Reasoning trace (may be None)
        stats: Memory statistics dict
        level: Question level (L1-L12)

    Returns:
        Confidence score 0.0-1.0
    """
    base_confidence = 0.5

    # Adjust by fact coverage
    total_facts = stats.get("total_experiences", 0)
    if total_facts >= 10:
        base_confidence += 0.2
    elif total_facts >= 5:
        base_confidence += 0.1

    # Adjust by trace quality
    if trace is not None:
        facts_collected = getattr(trace, "total_facts_collected", 0)
        if facts_collected >= 5:
            base_confidence += 0.15
        elif facts_collected >= 1:
            base_confidence += 0.05

        # Simple path for simple questions = higher confidence
        if getattr(trace, "used_simple_path", False) and level in ("L1", "L6"):
            base_confidence += 0.1

    # Level complexity adjustment
    simple_levels = {"L1", "L4", "L6"}
    complex_levels = {"L9", "L10", "L8"}
    if level in simple_levels:
        base_confidence += 0.05
    elif level in complex_levels:
        base_confidence -= 0.05

    return min(1.0, max(0.1, round(base_confidence, 2)))


def learning_phase(news_articles: list[dict], agent_name: str) -> dict:
    """Learning phase: Store news articles using LearningAgent with hierarchical memory.

    Args:
        news_articles: List of article dicts
        agent_name: Agent identifier

    Returns:
        Status dict with count of stored experiences
    """
    # Create LearningAgent with hierarchical memory enabled
    storage_path = Path(tempfile.gettempdir()) / "amplihack_eval" / agent_name
    storage_path.mkdir(parents=True, exist_ok=True)

    # Get model from env or use default
    model = os.environ.get("EVAL_MODEL", "anthropic/claude-sonnet-4-5-20250929")

    agent = LearningAgent(
        agent_name=agent_name,
        model=model,
        storage_path=storage_path,
        use_hierarchical=True,
    )

    stored_count = 0
    try:
        for article in news_articles:
            # Combine title and content for learning
            content = f"Title: {article['title']}\n\n{article['content']}"

            result = agent.learn_from_content(content)
            if result["facts_stored"] > 0:
                stored_count += result["facts_stored"]
    finally:
        agent.close()

    return {"status": "success", "stored_count": stored_count, "total_articles": len(news_articles)}


def testing_phase(quiz_questions: list[dict], agent_name: str) -> dict:
    """Testing phase: Answer questions using LearningAgent with hierarchical memory.

    Args:
        quiz_questions: List of question dicts
        agent_name: Agent identifier

    Returns:
        Status dict with answers
    """
    # Create LearningAgent with same storage path
    storage_path = Path(tempfile.gettempdir()) / "amplihack_eval" / agent_name
    storage_path.mkdir(parents=True, exist_ok=True)

    # Get model from env or use default
    model = os.environ.get("EVAL_MODEL", "anthropic/claude-sonnet-4-5-20250929")

    agent = LearningAgent(
        agent_name=agent_name,
        model=model,
        storage_path=storage_path,
        use_hierarchical=True,
    )

    answers = []
    try:
        for question_data in quiz_questions:
            question = question_data["question"]
            level = question_data.get("level", "L1")

            # Use agent's answer_question with LLM synthesis and trace
            result = agent.answer_question(question, question_level=level, return_trace=True)
            if isinstance(result, tuple):
                answer, trace = result
            else:
                answer, trace = result, None

            # Get memory stats for metadata
            stats = agent.get_memory_stats()

            # Serialize trace if available
            trace_dict = None
            if trace is not None:
                trace_dict = {
                    "question": trace.question,
                    "intent": trace.intent,
                    "steps": [
                        {
                            "step_type": s.step_type,
                            "queries": s.queries,
                            "facts_found": s.facts_found,
                            "evaluation": s.evaluation,
                            "reasoning": s.reasoning,
                        }
                        for s in trace.steps
                    ],
                    "total_facts_collected": trace.total_facts_collected,
                    "total_queries_executed": trace.total_queries_executed,
                    "iterations": trace.iterations,
                    "final_confidence": trace.final_confidence,
                    "used_simple_path": trace.used_simple_path,
                }

            # Dynamic confidence based on fact coverage and trace
            confidence = _compute_dynamic_confidence(trace, stats, level)

            answers.append(
                {
                    "question": question,
                    "answer": answer,
                    "confidence": confidence,
                    "memories_used": stats.get("total_experiences", 0),
                    "reasoning_trace": trace_dict,
                }
            )
    finally:
        agent.close()

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
        if isinstance(input_data, list):
            articles = input_data
        elif isinstance(input_data, dict):
            articles = input_data.get("articles", [input_data])
        else:
            articles = [input_data]
        result = learning_phase(articles, args.agent_name)
    else:  # testing
        result = testing_phase(input_data, args.agent_name)

    # Output result as JSON
    print(json.dumps(result))


if __name__ == "__main__":
    main()


__all__ = ["learning_phase", "testing_phase"]
