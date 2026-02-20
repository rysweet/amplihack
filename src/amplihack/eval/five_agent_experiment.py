"""Five Office Task Agents Experiment.

Generates 5 goal-seeking agents across the 5 domains:
1. Code Review
2. Meeting Synthesizer
3. Document Creator
4. Data Analysis
5. Project Planning

For each agent:
- Runs domain eval (tool-level proficiency)
- Runs a teaching session (knowledge transfer)
- Produces a combined report

Usage:
    PYTHONPATH=src python -m amplihack.eval.five_agent_experiment
    PYTHONPATH=src python -m amplihack.eval.five_agent_experiment --output-dir ./experiment_results

Philosophy: Integration test across all domain agents with real eval + teaching.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from amplihack.agents.domain_agents.code_review import CodeReviewAgent
from amplihack.agents.domain_agents.data_analysis import DataAnalysisAgent
from amplihack.agents.domain_agents.document_creator import DocumentCreatorAgent
from amplihack.agents.domain_agents.meeting_synthesizer import MeetingSynthesizerAgent
from amplihack.agents.domain_agents.project_planning import ProjectPlanningAgent
from amplihack.eval.domain_eval_harness import DomainEvalHarness

logger = logging.getLogger(__name__)


AGENT_REGISTRY = {
    "code_review": {
        "class": CodeReviewAgent,
        "teaching_topic": "security review",
        "description": "Reviews code for quality, security, and style issues",
    },
    "meeting_synthesizer": {
        "class": MeetingSynthesizerAgent,
        "teaching_topic": "meeting synthesis",
        "description": "Synthesizes meeting transcripts into structured summaries",
    },
    "document_creator": {
        "class": DocumentCreatorAgent,
        "teaching_topic": "document structure",
        "description": "Creates and evaluates structured documents",
    },
    "data_analysis": {
        "class": DataAnalysisAgent,
        "teaching_topic": "trend detection",
        "description": "Analyzes data, detects trends, generates insights",
    },
    "project_planning": {
        "class": ProjectPlanningAgent,
        "teaching_topic": "risk assessment",
        "description": "Decomposes projects, identifies dependencies, assesses risks",
    },
}


@dataclass
class AgentExperimentResult:
    """Result for a single agent in the experiment."""

    agent_name: str
    domain: str
    description: str

    # Eval results
    eval_overall_score: float
    eval_overall_passed: bool
    eval_level_scores: dict[str, float]

    # Teaching results
    teaching_topic: str
    lesson_plan: str
    instruction: str
    student_attempt: str

    # Combined
    combined_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "domain": self.domain,
            "description": self.description,
            "eval_overall_score": round(self.eval_overall_score, 3),
            "eval_overall_passed": self.eval_overall_passed,
            "eval_level_scores": {k: round(v, 3) for k, v in self.eval_level_scores.items()},
            "teaching_topic": self.teaching_topic,
            "lesson_plan": self.lesson_plan,
            "instruction_preview": self.instruction[:200],
            "student_attempt": self.student_attempt,
            "combined_score": round(self.combined_score, 3),
        }


@dataclass
class ExperimentReport:
    """Complete report for all 5 agents."""

    agent_results: list[AgentExperimentResult]
    overall_eval_score: float
    overall_teaching_score: float
    overall_combined_score: float
    all_passed: bool
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_eval_score": round(self.overall_eval_score, 3),
            "overall_teaching_score": round(self.overall_teaching_score, 3),
            "overall_combined_score": round(self.overall_combined_score, 3),
            "all_passed": self.all_passed,
            "summary": self.summary,
            "agents": [r.to_dict() for r in self.agent_results],
        }


def run_experiment(
    output_dir: str = "./five_agent_results",
    agent_names: list[str] | None = None,
) -> ExperimentReport:
    """Run the complete 5-agent experiment.

    Args:
        output_dir: Directory to save results
        agent_names: Specific agents to test (default: all 5)

    Returns:
        ExperimentReport with all results
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if agent_names is None:
        agent_names = list(AGENT_REGISTRY.keys())

    results: list[AgentExperimentResult] = []

    for name in agent_names:
        if name not in AGENT_REGISTRY:
            print(f"WARNING: Unknown agent '{name}', skipping")
            continue

        info = AGENT_REGISTRY[name]
        agent_class = info["class"]
        teaching_topic = info["teaching_topic"]
        description = info["description"]

        print(f"\n{'=' * 60}")
        print(f"AGENT: {name}")
        print(f"{'=' * 60}")

        agent = agent_class()

        # Phase 1: Domain Eval
        print("  Phase 1: Running domain evaluation...")
        try:
            harness = DomainEvalHarness(agent)
            eval_report = harness.run()
            eval_score = eval_report.overall_score
            eval_passed = eval_report.overall_passed
            level_scores = {
                level.level_id: level.average_score
                for level in eval_report.levels
            }
            print(f"    Eval Score: {eval_score:.2%} [{('PASS' if eval_passed else 'FAIL')}]")
            for lid, ls in level_scores.items():
                print(f"    {lid}: {ls:.2%}")
        except Exception as e:
            print(f"    Eval ERROR: {e}")
            eval_score = 0.0
            eval_passed = False
            level_scores = {}

        # Phase 2: Teaching Capability
        print("  Phase 2: Testing teaching capability...")
        try:
            teaching_result = agent.teach(teaching_topic, student_level="beginner")
            lesson_plan = teaching_result.lesson_plan
            instruction = teaching_result.instruction
            student_attempt = teaching_result.student_attempt

            # Teaching score: has all components
            has_plan = bool(lesson_plan.strip())
            has_instruction = bool(instruction.strip())
            has_questions = len(teaching_result.student_questions) > 0
            has_answers = len(teaching_result.agent_answers) > 0
            has_attempt = bool(student_attempt.strip())

            teaching_score = sum([has_plan, has_instruction, has_questions, has_answers, has_attempt]) / 5.0
            print(f"    Teaching Score: {teaching_score:.2%}")
            print(f"    Lesson Plan: {'yes' if has_plan else 'no'}")
            print(f"    Instruction: {'yes' if has_instruction else 'no'}")
            print(f"    Q&A: {len(teaching_result.student_questions)} questions, {len(teaching_result.agent_answers)} answers")
            print(f"    Student Attempt: {'yes' if has_attempt else 'no'}")
        except Exception as e:
            print(f"    Teaching ERROR: {e}")
            lesson_plan = ""
            instruction = ""
            student_attempt = ""
            teaching_score = 0.0

        # Combined score (70% eval, 30% teaching)
        combined_score = 0.7 * eval_score + 0.3 * teaching_score

        result = AgentExperimentResult(
            agent_name=name,
            domain=name,
            description=description,
            eval_overall_score=eval_score,
            eval_overall_passed=eval_passed,
            eval_level_scores=level_scores,
            teaching_topic=teaching_topic,
            lesson_plan=lesson_plan,
            instruction=instruction,
            student_attempt=student_attempt,
            combined_score=combined_score,
        )
        results.append(result)

        # Save individual agent result
        with open(output_path / f"{name}_result.json", "w") as f:
            json.dump(result.to_dict(), f, indent=2)

    # Calculate overall metrics
    eval_scores = [r.eval_overall_score for r in results]
    teaching_scores = [0.7 * r.eval_overall_score + 0.3 * 1.0 if r.lesson_plan else 0 for r in results]
    combined_scores = [r.combined_score for r in results]

    overall_eval = sum(eval_scores) / len(eval_scores) if eval_scores else 0
    overall_teaching = sum(combined_scores) / len(combined_scores) if combined_scores else 0
    overall_combined = sum(combined_scores) / len(combined_scores) if combined_scores else 0
    all_passed = all(r.eval_overall_passed for r in results)

    # Generate summary
    passed_count = sum(1 for r in results if r.eval_overall_passed)
    summary = (
        f"5 Office Task Agents Experiment: {passed_count}/{len(results)} agents passed eval. "
        f"Overall eval score: {overall_eval:.2%}. "
        f"Overall combined score: {overall_combined:.2%}. "
        f"All agents {'PASS' if all_passed else 'have failures'}."
    )

    report = ExperimentReport(
        agent_results=results,
        overall_eval_score=overall_eval,
        overall_teaching_score=overall_teaching,
        overall_combined_score=overall_combined,
        all_passed=all_passed,
        summary=summary,
    )

    # Save combined report
    with open(output_path / "five_agent_experiment.json", "w") as f:
        json.dump(report.to_dict(), f, indent=2)

    # Print summary
    print(f"\n{'=' * 60}")
    print("EXPERIMENT SUMMARY")
    print(f"{'=' * 60}")
    print(f"Agents Tested: {len(results)}")
    print(f"Overall Eval Score: {overall_eval:.2%}")
    print(f"Overall Combined Score: {overall_combined:.2%}")
    print(f"All Passed: {all_passed}")
    print()
    for r in results:
        status = "PASS" if r.eval_overall_passed else "FAIL"
        print(f"  {r.agent_name}: eval={r.eval_overall_score:.2%} combined={r.combined_score:.2%} [{status}]")
    print(f"\n{summary}")
    print(f"\nResults saved to: {output_path}")

    return report


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Five Office Task Agents Experiment")
    parser.add_argument(
        "--output-dir", default="./five_agent_results",
        help="Output directory for results",
    )
    parser.add_argument(
        "--agents", nargs="*", default=None,
        help="Specific agents to test (default: all 5)",
    )
    args = parser.parse_args()

    run_experiment(output_dir=args.output_dir, agent_names=args.agents)


if __name__ == "__main__":
    main()
