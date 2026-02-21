"""5-way matrix evaluation across agent types.

Runs the long-horizon memory eval for each of 5 agent configurations:
  1. mini        - LearningAgent (direct, no SDK wrapper)
  2. claude      - ClaudeGoalSeekingAgent via SDK factory
  3. copilot     - CopilotGoalSeekingAgent via SDK factory
  4. microsoft   - MicrosoftGoalSeekingAgent via SDK factory
  5. multiagent-copilot - MultiAgentLearningAgent with spawning

Each agent uses a SEPARATE storage/DB path to avoid cross-contamination.
SDK agents that fail to instantiate are skipped gracefully.
Results are aggregated into a markdown report.

Usage:
    python -m amplihack.eval.matrix_eval
    python -m amplihack.eval.matrix_eval --turns 500 --questions 50
    python -m amplihack.eval.matrix_eval --output-dir /tmp/matrix-eval
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .long_horizon_memory import (
    EvalReport,
    LongHorizonMemoryEval,
    _print_report,
    _SDKAgentWrapper,
)

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Configuration for a single agent in the matrix."""

    name: str
    sdk: str
    multi_agent: bool = False
    enable_spawning: bool = False


@dataclass
class MatrixResult:
    """Result for a single agent in the matrix."""

    agent_name: str
    status: str  # "success", "skipped", "error"
    report: EvalReport | None = None
    error_message: str = ""
    instantiation_time_s: float = 0.0


@dataclass
class MatrixReport:
    """Complete matrix evaluation report across all agents."""

    results: list[MatrixResult]
    num_turns: int = 0
    num_questions: int = 0
    seed: int = 42
    grader_votes: int = 3
    agent_model: str = ""
    grader_model: str = ""
    timestamp: str = ""
    total_time_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "timestamp": self.timestamp,
            "num_turns": self.num_turns,
            "num_questions": self.num_questions,
            "seed": self.seed,
            "grader_votes": self.grader_votes,
            "agent_model": self.agent_model,
            "grader_model": self.grader_model,
            "total_time_s": round(self.total_time_s, 2),
            "results": [
                {
                    "agent_name": r.agent_name,
                    "status": r.status,
                    "error_message": r.error_message,
                    "instantiation_time_s": round(r.instantiation_time_s, 2),
                    "report": r.report.to_dict() if r.report else None,
                }
                for r in self.results
            ],
        }


# The 5 agent configurations to evaluate
AGENT_TYPES: list[AgentConfig] = [
    AgentConfig(name="mini", sdk="mini", multi_agent=False, enable_spawning=False),
    AgentConfig(name="claude", sdk="claude", multi_agent=False, enable_spawning=False),
    AgentConfig(name="copilot", sdk="copilot", multi_agent=False, enable_spawning=False),
    AgentConfig(name="microsoft", sdk="microsoft", multi_agent=False, enable_spawning=False),
    AgentConfig(name="multiagent-copilot", sdk="copilot", multi_agent=True, enable_spawning=True),
]


def _create_agent(
    config: AgentConfig,
    model: str,
    db_path: Path,
) -> Any:
    """Create an agent based on the configuration.

    For mini: uses LearningAgent directly.
    For multi_agent: uses MultiAgentLearningAgent.
    For SDK agents: uses create_agent from factory, wrapped in _SDKAgentWrapper.

    Args:
        config: Agent configuration
        model: LLM model to use
        db_path: Separate storage path for this agent

    Returns:
        Agent with learn_from_content/answer_question/get_memory_stats/close API

    Raises:
        Exception: If the agent cannot be created
    """
    if config.multi_agent:
        from amplihack.agents.goal_seeking.sub_agents.multi_agent import (
            MultiAgentLearningAgent,
        )

        return MultiAgentLearningAgent(
            agent_name=f"matrix_{config.name}",
            model=model,
            storage_path=db_path,
            use_hierarchical=True,
            enable_spawning=config.enable_spawning,
        )

    if config.sdk == "mini":
        from amplihack.agents.goal_seeking.learning_agent import LearningAgent

        return LearningAgent(
            agent_name=f"matrix_{config.name}",
            model=model,
            storage_path=db_path,
            use_hierarchical=True,
        )

    # SDK agents: use factory and wrap
    from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

    sdk_agent = create_agent(
        name=f"matrix_{config.name}",
        sdk=config.sdk,
        instructions="You are a learning agent. Learn facts and answer questions accurately.",
        model=model,
        storage_path=db_path,
        enable_memory=True,
    )
    return _SDKAgentWrapper(sdk_agent)


def run_matrix_eval(
    num_turns: int = 500,
    num_questions: int = 50,
    seed: int = 42,
    grader_votes: int = 3,
    agent_model: str = "",
    grader_model: str = "",
    output_dir: str = "/tmp/matrix-eval",
    agent_names: list[str] | None = None,
) -> MatrixReport:
    """Run the 5-way matrix evaluation.

    Generates dialogue and questions ONCE, then runs each agent against
    the same data. Agents are run sequentially to avoid API overload.

    Args:
        num_turns: Number of dialogue turns
        num_questions: Number of quiz questions
        seed: Random seed for reproducibility
        grader_votes: Number of grading votes per question
        agent_model: Model for agents (default from env or claude-sonnet-4-5-20250929)
        grader_model: Model for grading
        output_dir: Directory for results
        agent_names: Optional subset of agent names to run (default: all 5)

    Returns:
        MatrixReport with all results
    """
    start_time = time.time()
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    agent_model = agent_model or os.environ.get("EVAL_MODEL", "claude-sonnet-4-5-20250929")
    grader_model = grader_model or os.environ.get("GRADER_MODEL", "claude-sonnet-4-5-20250929")

    # Determine which agents to run
    if agent_names:
        configs = [c for c in AGENT_TYPES if c.name in agent_names]
    else:
        configs = list(AGENT_TYPES)

    logger.info(
        "Matrix eval: %d agents, %d turns, %d questions, seed=%d, grader_votes=%d",
        len(configs),
        num_turns,
        num_questions,
        seed,
        grader_votes,
    )

    # Step 1: Generate data ONCE (shared across all agents)
    evaluator = LongHorizonMemoryEval(
        num_turns=num_turns,
        num_questions=num_questions,
        seed=seed,
        grader_votes=grader_votes,
    )
    ground_truth, questions = evaluator.generate()
    logger.info(
        "Generated %d turns, %d questions",
        len(ground_truth.turns),
        len(questions),
    )

    # Save shared ground truth
    gt_path = out / "ground_truth.json"
    gt_data = {
        "num_turns": len(ground_truth.turns),
        "turns_with_facts": sum(1 for t in ground_truth.turns if t.facts),
        "total_facts": sum(len(t.facts) for t in ground_truth.turns),
        "current_values": ground_truth.current_values,
        "block_distribution": {},
    }
    for t in ground_truth.turns:
        gt_data["block_distribution"][t.block_name] = (
            gt_data["block_distribution"].get(t.block_name, 0) + 1
        )
    with open(gt_path, "w") as f:
        json.dump(gt_data, f, indent=2)

    # Step 2: Run each agent sequentially
    results: list[MatrixResult] = []

    for config in configs:
        print(f"\n{'=' * 70}")
        print(f"AGENT: {config.name} (sdk={config.sdk}, multi_agent={config.multi_agent})")
        print(f"{'=' * 70}")

        agent_out = out / config.name
        agent_out.mkdir(parents=True, exist_ok=True)
        db_path = agent_out / "memory_db"

        # Try to create the agent
        agent = None
        result = MatrixResult(agent_name=config.name, status="error")

        try:
            create_start = time.time()
            agent = _create_agent(config, agent_model, db_path)
            result.instantiation_time_s = time.time() - create_start
            logger.info("Agent %s created in %.1fs", config.name, result.instantiation_time_s)
        except Exception as e:
            result.status = "skipped"
            result.error_message = f"Failed to create agent: {e}"
            logger.warning("Skipping agent %s: %s", config.name, e)
            results.append(result)
            continue

        try:
            # Create a fresh evaluator for this agent (reuse generated data)
            agent_eval = LongHorizonMemoryEval(
                num_turns=num_turns,
                num_questions=num_questions,
                seed=seed,
                grader_votes=grader_votes,
            )
            agent_eval.ground_truth = ground_truth
            agent_eval.questions = questions

            # Run dialogue (learning phase)
            logger.info("Starting learning phase for %s...", config.name)
            learning_time = agent_eval.run_dialogue(agent)
            logger.info("Learning complete for %s: %.1fs", config.name, learning_time)

            # Run evaluation (questioning + grading)
            logger.info("Starting evaluation phase for %s...", config.name)
            report = agent_eval.evaluate(agent, grader_model=grader_model)
            report.learning_time_s = learning_time

            result.status = "success"
            result.report = report

            # Print per-agent report
            _print_report(report)

            # Save per-agent JSON report
            with open(agent_out / "report.json", "w") as f:
                json.dump(report.to_dict(), f, indent=2)

            logger.info(
                "Agent %s: overall=%.2f%%, learning=%.1fs, grading=%.1fs",
                config.name,
                report.overall_score * 100,
                report.learning_time_s,
                report.grading_time_s,
            )

        except Exception as e:
            result.status = "error"
            result.error_message = str(e)
            logger.error("Agent %s evaluation failed: %s", config.name, e, exc_info=True)

        finally:
            if agent is not None:
                try:
                    agent.close()
                except Exception:
                    pass

        results.append(result)

    total_time = time.time() - start_time

    # Build matrix report
    matrix_report = MatrixReport(
        results=results,
        num_turns=num_turns,
        num_questions=num_questions,
        seed=seed,
        grader_votes=grader_votes,
        agent_model=agent_model,
        grader_model=grader_model,
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        total_time_s=total_time,
    )

    # Save full matrix JSON
    with open(out / "matrix_report.json", "w") as f:
        json.dump(matrix_report.to_dict(), f, indent=2)

    # Print summary
    _print_matrix_summary(matrix_report)

    return matrix_report


def _print_matrix_summary(report: MatrixReport) -> None:
    """Print a human-readable matrix summary."""
    print(f"\n{'=' * 70}")
    print("MATRIX EVALUATION SUMMARY")
    print(f"{'=' * 70}")
    print(f"Timestamp: {report.timestamp}")
    print(f"Turns: {report.num_turns} | Questions: {report.num_questions}")
    print(f"Agent model: {report.agent_model}")
    print(f"Grader model: {report.grader_model}")
    print(f"Grader votes: {report.grader_votes}")
    print(f"Total time: {report.total_time_s:.1f}s")
    print()

    # Summary table
    print("AGENT RESULTS:")
    print("-" * 70)
    print(
        f"{'Agent':<22} {'Status':<10} {'Overall':>8} {'Learn(s)':>10} "
        f"{'Grade(s)':>10} {'Facts':>6}"
    )
    print("-" * 70)

    for r in report.results:
        if r.status == "success" and r.report:
            rp = r.report
            print(
                f"{r.agent_name:<22} {r.status:<10} {rp.overall_score:>7.2%} "
                f"{rp.learning_time_s:>10.1f} {rp.grading_time_s:>10.1f} "
                f"{rp.total_facts_delivered:>6}"
            )
        else:
            print(f"{r.agent_name:<22} {r.status:<10} {'--':>8} {'--':>10} {'--':>10} {'--':>6}")
            if r.error_message:
                print(f"  Error: {r.error_message[:80]}")

    print("-" * 70)

    # Category breakdown comparison
    successful = [r for r in report.results if r.status == "success" and r.report]
    if successful:
        # Collect all categories
        all_cats: set[str] = set()
        for r in successful:
            assert r.report is not None
            for cb in r.report.category_breakdown:
                all_cats.add(cb.category)

        print("\nCATEGORY SCORES BY AGENT:")
        print("-" * 70)
        header = f"{'Category':<25}"
        for r in successful:
            header += f" {r.agent_name:>12}"
        print(header)
        print("-" * 70)

        for cat in sorted(all_cats):
            row = f"{cat:<25}"
            for r in successful:
                score = 0.0
                assert r.report is not None
                for cb in r.report.category_breakdown:
                    if cb.category == cat:
                        score = cb.avg_score
                        break
                row += f" {score:>11.2%}"
            print(row)

        print("-" * 70)

        # Best performer per category
        print("\nBEST PERFORMER PER CATEGORY:")
        for cat in sorted(all_cats):
            best_agent = ""
            best_score = -1.0
            for r in successful:
                assert r.report is not None
                for cb in r.report.category_breakdown:
                    if cb.category == cat and cb.avg_score > best_score:
                        best_score = cb.avg_score
                        best_agent = r.agent_name
            print(f"  {cat}: {best_agent} ({best_score:.2%})")

        # Overall ranking
        print("\nOVERALL RANKING:")

        def _score_key(r: MatrixResult) -> float:
            return r.report.overall_score if r.report else 0.0

        ranked = sorted(successful, key=_score_key, reverse=True)
        for i, r in enumerate(ranked, 1):
            assert r.report is not None
            print(f"  {i}. {r.agent_name}: {r.report.overall_score:.2%}")


def generate_markdown_report(report: MatrixReport, output_path: str) -> None:
    """Generate a detailed markdown report from matrix results.

    Args:
        report: The matrix evaluation report
        output_path: Path to write the markdown file
    """
    successful = [r for r in report.results if r.status == "success" and r.report]
    skipped = [r for r in report.results if r.status != "success"]

    lines: list[str] = []
    lines.append("# Matrix Evaluation Report: 5-Way Agent Comparison")
    lines.append("")
    lines.append(f"**Date**: {report.timestamp}")
    lines.append(f"**Agent Model**: {report.agent_model}")
    lines.append(f"**Grader Model**: {report.grader_model}")
    lines.append(f"**Dialogue Turns**: {report.num_turns}")
    lines.append(f"**Quiz Questions**: {report.num_questions}")
    lines.append(f"**Seed**: {report.seed}")
    lines.append(f"**Grader Votes**: {report.grader_votes}")
    lines.append(f"**Total Evaluation Time**: {report.total_time_s:.1f}s")
    lines.append("")

    # Summary table
    lines.append("## Summary Table")
    lines.append("")
    lines.append("| Agent | Status | Overall Score | Learning Time | Grading Time | Facts |")
    lines.append("|-------|--------|--------------|---------------|--------------|-------|")

    for r in report.results:
        if r.status == "success" and r.report:
            rp = r.report
            lines.append(
                f"| {r.agent_name} | {r.status} | {rp.overall_score:.2%} | "
                f"{rp.learning_time_s:.1f}s | {rp.grading_time_s:.1f}s | "
                f"{rp.total_facts_delivered} |"
            )
        else:
            reason = r.error_message[:60] if r.error_message else "N/A"
            lines.append(f"| {r.agent_name} | {r.status} | -- | -- | -- | -- |")
            if r.error_message:
                lines.append(f"| | *{reason}* | | | | |")

    lines.append("")

    def _md_score_key(r: MatrixResult) -> float:
        return r.report.overall_score if r.report else 0.0

    # Category breakdown
    if successful:
        all_cats: set[str] = set()
        for r in successful:
            assert r.report is not None
            for cb in r.report.category_breakdown:
                all_cats.add(cb.category)

        lines.append("## Category Scores by Agent")
        lines.append("")

        header = "| Category |"
        separator = "|----------|"
        for r in successful:
            header += f" {r.agent_name} |"
            separator += "--------|"

        lines.append(header)
        lines.append(separator)

        for cat in sorted(all_cats):
            row = f"| {cat} |"
            for r in successful:
                score = 0.0
                assert r.report is not None
                for cb in r.report.category_breakdown:
                    if cb.category == cat:
                        score = cb.avg_score
                        break
                row += f" {score:.2%} |"
            lines.append(row)

        lines.append("")

        # Best performer per category
        lines.append("## Best Performer per Category")
        lines.append("")
        lines.append("| Category | Best Agent | Score |")
        lines.append("|----------|-----------|-------|")

        for cat in sorted(all_cats):
            best_agent = ""
            best_score = -1.0
            for r in successful:
                assert r.report is not None
                for cb in r.report.category_breakdown:
                    if cb.category == cat and cb.avg_score > best_score:
                        best_score = cb.avg_score
                        best_agent = r.agent_name
            lines.append(f"| {cat} | {best_agent} | {best_score:.2%} |")

        lines.append("")

        # Overall ranking
        lines.append("## Overall Ranking")
        lines.append("")
        ranked = sorted(successful, key=_md_score_key, reverse=True)
        for i, r in enumerate(ranked, 1):
            rp = r.report
            assert rp is not None
            lines.append(f"{i}. **{r.agent_name}**: {rp.overall_score:.2%}")
            lines.append(f"   - Learning time: {rp.learning_time_s:.1f}s")
            lines.append(f"   - Grading time: {rp.grading_time_s:.1f}s")
            lines.append(f"   - Memory stats: {json.dumps(rp.memory_stats, default=str)[:200]}")
            lines.append("")

        # Per-agent detailed results
        lines.append("## Per-Agent Detailed Results")
        lines.append("")

        for r in successful:
            rp = r.report
            assert rp is not None
            lines.append(f"### {r.agent_name}")
            lines.append("")
            lines.append(f"- **Overall Score**: {rp.overall_score:.2%}")
            lines.append(f"- **Learning Time**: {rp.learning_time_s:.1f}s")
            lines.append(f"- **Question + Grading Time**: {rp.questioning_time_s:.1f}s")
            lines.append(f"- **Total Facts Delivered**: {rp.total_facts_delivered}")
            lines.append("")

            lines.append("#### Category Breakdown")
            lines.append("")
            lines.append("| Category | Avg | Min | Max | Count |")
            lines.append("|----------|-----|-----|-----|-------|")
            for cb in rp.category_breakdown:
                lines.append(
                    f"| {cb.category} | {cb.avg_score:.2%} | {cb.min_score:.2%} | "
                    f"{cb.max_score:.2%} | {cb.num_questions} |"
                )
            lines.append("")

            # Dimension averages
            lines.append("#### Dimension Averages by Category")
            lines.append("")
            for cb in rp.category_breakdown:
                if cb.dimension_averages:
                    dims = ", ".join(
                        f"{k}: {v:.2%}" for k, v in sorted(cb.dimension_averages.items())
                    )
                    lines.append(f"- **{cb.category}**: {dims}")
            lines.append("")

            # Worst 5 questions
            lines.append("#### Worst 5 Questions")
            lines.append("")
            sorted_results = sorted(rp.results, key=lambda x: x.overall_score)
            for qr in sorted_results[:5]:
                lines.append(f"- [{qr.overall_score:.2%}] {qr.question_text[:80]}")
                lines.append(f"  - Expected: {qr.expected_answer[:100]}")
                lines.append(f"  - Got: {qr.actual_answer[:100]}")
            lines.append("")

    # Skipped agents
    if skipped:
        lines.append("## Skipped/Failed Agents")
        lines.append("")
        for r in skipped:
            lines.append(f"- **{r.agent_name}** ({r.status}): {r.error_message}")
        lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    lines.append("")
    if successful:
        ranked = sorted(successful, key=_md_score_key, reverse=True)
        best = ranked[0]
        assert best.report is not None
        lines.append(
            f"1. **Best overall agent**: {best.agent_name} ({best.report.overall_score:.2%})"
        )

        # Find categories where different agents excel
        agent_strengths: dict[str, list[str]] = {}
        for cat in sorted(all_cats):
            best_agent = ""
            best_score = -1.0
            for r in successful:
                assert r.report is not None
                for cb in r.report.category_breakdown:
                    if cb.category == cat and cb.avg_score > best_score:
                        best_score = cb.avg_score
                        best_agent = r.agent_name
            agent_strengths.setdefault(best_agent, []).append(cat)

        for agent_name, strengths in agent_strengths.items():
            lines.append(f"2. **{agent_name}** excels at: {', '.join(strengths)}")
    else:
        lines.append("No agents completed successfully. Check error messages above.")

    lines.append("")
    lines.append("---")
    lines.append(f"*Generated by matrix_eval.py on {report.timestamp}*")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))

    logger.info("Markdown report saved to %s", output_path)


def main() -> None:
    """CLI entry point for matrix evaluation."""
    parser = argparse.ArgumentParser(description="5-way matrix evaluation across agent types")
    parser.add_argument(
        "--turns", type=int, default=500, help="Number of dialogue turns (default: 500)"
    )
    parser.add_argument(
        "--questions", type=int, default=50, help="Number of quiz questions (default: 50)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="/tmp/matrix-eval",
        help="Output directory for results",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="",
        help="Agent model (default: env EVAL_MODEL or claude-sonnet-4-5-20250929)",
    )
    parser.add_argument(
        "--grader-model",
        type=str,
        default="",
        help="Grader model (default: env GRADER_MODEL or claude-sonnet-4-5-20250929)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--grader-votes", type=int, default=3, help="Grading votes per question")
    parser.add_argument(
        "--agents",
        nargs="+",
        choices=["mini", "claude", "copilot", "microsoft", "multiagent-copilot"],
        help="Subset of agents to run (default: all 5)",
    )
    parser.add_argument(
        "--report-path",
        type=str,
        default="",
        help="Path for markdown report (default: Specs/MATRIX_EVAL_REPORT.md)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    report = run_matrix_eval(
        num_turns=args.turns,
        num_questions=args.questions,
        seed=args.seed,
        grader_votes=args.grader_votes,
        agent_model=args.model,
        grader_model=args.grader_model,
        output_dir=args.output_dir,
        agent_names=args.agents,
    )

    # Generate markdown report
    report_path = args.report_path
    if not report_path:
        # Default: project Specs directory
        project_root = Path(__file__).resolve().parents[3]
        report_path = str(project_root / "Specs" / "MATRIX_EVAL_REPORT.md")

    generate_markdown_report(report, report_path)
    print(f"\nMarkdown report: {report_path}")
    print(f"JSON report: {args.output_dir}/matrix_report.json")


if __name__ == "__main__":
    main()


__all__ = [
    "AGENT_TYPES",
    "AgentConfig",
    "MatrixReport",
    "MatrixResult",
    "generate_markdown_report",
    "run_matrix_eval",
]
