#!/usr/bin/env python
"""Run L1-L6 progressive evaluation for the Claude SDK adapter.

Evaluates the LearningAgent (mini-framework baseline) using built-in
test content across 6 cognitive complexity levels.

Usage:
    python run_eval.py
    python run_eval.py --parallel 3
    python run_eval.py --levels L1 L2
"""

import json
import os
import shutil
import statistics
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set model - use Anthropic since key is available
os.environ.setdefault("EVAL_MODEL", "claude-haiku-4-5-20251001")

# Test content: L1-L6 articles and questions
TEST_LEVELS = {
    "L1": {
        "name": "Single Source Direct Recall",
        "articles": [
            "Title: 2026 Winter Olympics Medal Update - February 15\n"
            "As of February 15, 2026, the Milan-Cortina Winter Olympics medal standings show: "
            "Norway leads with 26 total medals (12 gold, 8 silver, 6 bronze). "
            "Italy is in second place with 22 total medals (8 gold, 7 silver, 7 bronze). "
            "The United States has 17 medals (5 gold, 6 silver, 6 bronze). "
            "Germany has 14 medals (4 gold, 5 silver, 5 bronze). "
            "The Games continue through February 21, 2026."
        ],
        "questions": [
            ("How many total medals does Norway have as of February 15?", "26 total medals (12 gold, 8 silver, 6 bronze)", "L1"),
            ("Which country is in second place?", "Italy with 22 total medals", "L1"),
        ],
    },
    "L2": {
        "name": "Multi-Source Synthesis",
        "articles": [
            "Title: Norway's Cross-Country Skiing Dominance\n"
            "Norway continues its cross-country skiing dominance with Johannes Klaebo winning his 4th Olympic gold. "
            "The Norwegian team has won 8 of 12 possible cross-country medals so far.",
            "Title: Athlete Profile: Johannes Klaebo\n"
            "Johannes Klaebo (born 1996) is a Norwegian cross-country skier. "
            "He won his first Olympic gold at age 21 in Pyeongchang 2018. "
            "Known for his sprint technique, he now has 7 Olympic medals total.",
        ],
        "questions": [
            ("How many Olympic golds does Klaebo have and what fraction of Norway's cross-country medals has the team won?", "Klaebo has 4 Olympic golds; Norway has won 8 of 12 cross-country medals", "L2"),
        ],
    },
    "L3": {
        "name": "Temporal Reasoning",
        "articles": [
            "Title: Medal Standings - Day 7\n"
            "Day 7 standings: Norway has 8 gold medals, Italy has 5 gold medals, Germany has 3 gold medals.",
            "Title: Medal Standings - Day 10\n"
            "Day 10 standings: Norway has 12 gold medals, Italy has 8 gold medals, Germany has 4 gold medals.",
        ],
        "questions": [
            ("Which country gained the most gold medals between Day 7 and Day 10?", "Norway gained 4 golds (8 to 12), Italy gained 3 (5 to 8), Germany gained 1 (3 to 4). Norway gained the most.", "L3"),
        ],
    },
    "L4": {
        "name": "Procedural Learning",
        "articles": [
            "Title: How to Set Up Olympic Biathlon Scoring\n"
            "Step 1: Record the skiing time for each athlete. "
            "Step 2: Add 1 minute penalty for each missed target. "
            "Step 3: Calculate total time (ski time + penalties). "
            "Step 4: Rank athletes by lowest total time. "
            "Step 5: Award gold to first place, silver to second, bronze to third.",
        ],
        "questions": [
            ("Describe the complete biathlon scoring procedure.", "5 steps: Record skiing time, add 1 min per missed target, calculate total, rank by lowest time, award medals.", "L4"),
        ],
    },
    "L5": {
        "name": "Contradiction Handling",
        "articles": [
            "Title: Medal Count - Source A\n"
            "According to the official IOC website, Norway has 26 total medals.",
            "Title: Medal Count - Source B\n"
            "A news report states Norway has 28 total medals including two unofficial exhibition events.",
        ],
        "questions": [
            ("How many medals does Norway have? Note any discrepancies.", "There is a discrepancy: official IOC count is 26, news report says 28 (including exhibition events).", "L3"),
        ],
    },
    "L6": {
        "name": "Incremental Learning",
        "articles": [
            "Title: Day 9 Update\n"
            "As of Day 9, Klaebo has 3 gold medals.",
            "Title: Day 10 Update\n"
            "Klaebo won another gold on Day 10, bringing his total to 4 gold medals.",
        ],
        "questions": [
            ("How many gold medals does Klaebo have now?", "4 gold medals (3 as of Day 9, plus 1 more on Day 10)", "L1"),
        ],
    },
}


@dataclass
class EvalResult:
    level: str
    scores: list[float]
    avg_score: float


def run_single_eval(run_id: int, levels: list[str] | None = None) -> dict:
    """Run a single evaluation pass."""
    from amplihack.agents.goal_seeking.learning_agent import LearningAgent
    from amplihack.eval.grader import grade_answer

    temp_dir = Path(tempfile.mkdtemp())
    results = {}

    try:
        agent = LearningAgent(
            agent_name=f"eval_run_{run_id}",
            storage_path=temp_dir,
            use_hierarchical=True,
        )

        for level_id, level_data in TEST_LEVELS.items():
            if levels and level_id not in levels:
                continue

            # Learning phase
            for article in level_data["articles"]:
                agent.learn_from_content(article)

            # Testing phase
            level_scores = []
            for question, expected, q_level in level_data["questions"]:
                answer = agent.answer_question(question, question_level=q_level)
                if isinstance(answer, tuple):
                    answer = answer[0]

                grade = grade_answer(
                    question=question,
                    expected=expected,
                    actual=str(answer),
                    level=q_level,
                )
                level_scores.append(grade.score)

            if level_scores:
                results[level_id] = {
                    "scores": level_scores,
                    "avg": statistics.mean(level_scores),
                }

        agent.close()
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)

    # Overall
    all_scores = []
    for v in results.values():
        all_scores.extend(v["scores"])
    if all_scores:
        results["overall"] = statistics.mean(all_scores)

    return results


def main():
    import argparse

    parser = argparse.ArgumentParser(description="L1-L6 Progressive Eval")
    parser.add_argument("--parallel", type=int, default=3, help="Number of parallel runs")
    parser.add_argument("--levels", nargs="+", help="Specific levels to run")
    args = parser.parse_args()

    print("=" * 60)
    print("L1-L6 PROGRESSIVE EVALUATION")
    print(f"Parallel runs: {args.parallel}")
    print(f"Model: {os.environ.get('EVAL_MODEL', 'default')}")
    print("=" * 60)

    all_run_results = []

    if args.parallel > 1:
        with ProcessPoolExecutor(max_workers=min(args.parallel, 4)) as executor:
            futures = {
                executor.submit(run_single_eval, i, args.levels): i
                for i in range(args.parallel)
            }
            for future in as_completed(futures):
                run_id = futures[future]
                try:
                    result = future.result()
                    all_run_results.append(result)
                    print(f"Run {run_id} complete: overall={result.get('overall', 0):.2%}")
                except Exception as e:
                    print(f"Run {run_id} failed: {e}")
    else:
        result = run_single_eval(0, args.levels)
        all_run_results.append(result)
        print(f"Run 0 complete: overall={result.get('overall', 0):.2%}")

    # Compute median scores across runs
    print("\n" + "=" * 60)
    print("MEDIAN SCORES ACROSS RUNS")
    print("=" * 60)

    level_medians = {}
    for level_id in TEST_LEVELS:
        level_scores = [
            r[level_id]["avg"]
            for r in all_run_results
            if level_id in r
        ]
        if level_scores:
            median = statistics.median(level_scores)
            level_medians[level_id] = median
            print(f"  {level_id}: {median:.2%}")

    overall_scores = [r.get("overall", 0) for r in all_run_results if "overall" in r]
    if overall_scores:
        overall_median = statistics.median(overall_scores)
        print(f"\n  Overall Median: {overall_median:.2%}")

    # Save results
    output_path = Path("eval_results.json")
    with open(output_path, "w") as f:
        json.dump({
            "runs": all_run_results,
            "medians": level_medians,
            "overall_median": statistics.median(overall_scores) if overall_scores else 0,
        }, f, indent=2)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
