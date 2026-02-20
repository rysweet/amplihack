"""Meta-eval teaching experiment runner.

Orchestrates the complete experiment:
1. Build knowledge base from eval system documentation
2. Run teaching session (Eval Expert -> Student)
3. Quiz the student on learned knowledge
4. Grade with metacognition metrics
5. Produce structured report

Philosophy:
- Single responsibility: Orchestrate experiment
- Uses TeachingSession for dialogue
- Uses MetacognitionGrader for evaluation
- Deterministic knowledge base (no LLM for KB building)
- JSON report output
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from .metacognition_grader import MetacognitionGrader
from .teaching_session import TeachingConfig, TeachingSession

logger = logging.getLogger(__name__)


# Knowledge base about the eval system - derived from actual source code
EVAL_KNOWLEDGE_BASE = [
    (
        "The evaluation harness tests agent learning using a learn-then-test pattern. "
        "The agent first learns from news articles, then answers quiz questions "
        "about what it learned. Learning and testing run in separate subprocesses "
        "for memory isolation."
    ),
    (
        "L1 (Recall) questions test direct fact retrieval from a single source. "
        "They ask about specific entities, dates, or facts mentioned in articles. "
        "Example: 'According to the article, what is mentioned about [Entity]?' "
        "Expected answers are direct sentences from the source."
    ),
    (
        "L2 (Inference) questions test reasoning from facts. They require the agent "
        "to connect cause and effect, or make predictions based on information. "
        "Keywords that trigger L2: 'because', 'due to', 'resulted in', 'led to'. "
        "Example: 'Why did the described events occur or what was the impact?'"
    ),
    (
        "L3 (Synthesis) questions require combining information from multiple sources. "
        "They need at least 2 articles and ask about relationships or common themes. "
        "Example: 'How do the events in article A and article B relate to each other?' "
        "Expected answers reference content from both sources."
    ),
    (
        "L4 (Application) questions ask the agent to apply knowledge to new scenarios. "
        "They test whether the agent can generalize from learned facts. "
        "Example: 'If the trends described continue, what implications might this have?' "
        "These are the most challenging questions requiring true understanding."
    ),
    (
        "The grading system uses semantic comparison via LLM (Claude). "
        "Scores range from 0.0 to 1.0: "
        "1.0 = perfect/semantically equivalent, "
        "0.8-0.9 = correct main points with minor differences, "
        "0.6-0.7 = partially correct with missing details, "
        "0.4-0.5 = some relevant content with significant gaps, "
        "0.0-0.3 = incorrect or unrelated."
    ),
    (
        "The quiz generator creates questions deterministically from articles. "
        "It uses regex to extract entities and dates for L1 questions. "
        "L2 questions look for causal language patterns. "
        "L3 questions compare the first two articles. "
        "L4 questions create hypothetical scenarios from article content."
    ),
    (
        "The harness runner orchestrates the full pipeline: "
        "1. Collect news from WebSearch JSON input, "
        "2. Generate quiz questions at L1-L4 levels, "
        "3. Run learning phase in subprocess (stores articles in memory), "
        "4. Run testing phase in subprocess (answers questions from memory), "
        "5. Grade answers using semantic LLM comparison. "
        "Results are saved as JSON in the output directory."
    ),
    (
        "To run the eval harness from command line: "
        "python -m amplihack.eval.harness_runner "
        "--news-file <path-to-websearch-json> "
        "--output-dir ./eval_results "
        "--agent-name test-agent. "
        "The news file must be JSON with a 'sources' array containing objects "
        "with 'url', 'title', 'content', and 'published' fields."
    ),
    (
        "The multi-source collector transforms WebSearch results into "
        "structured NewsArticle objects with url, title, content, and published fields. "
        "It validates that all required fields are present and raises ValueError "
        "if any are missing. This is the data pipeline entry point."
    ),
]


# Quiz questions about the eval system itself
EVAL_QUIZ = [
    {
        "question": "What are the four cognitive levels (L1-L4) in the evaluation system, and what does each one test?",
        "expected_answer": (
            "L1 (Recall) tests direct fact retrieval from single sources. "
            "L2 (Inference) tests reasoning from facts and connecting cause and effect. "
            "L3 (Synthesis) requires combining information from multiple sources. "
            "L4 (Application) tests applying knowledge to new hypothetical scenarios."
        ),
    },
    {
        "question": "How does the grading system score answers, and what does a score of 0.8 mean?",
        "expected_answer": (
            "The grading system uses semantic LLM comparison with scores from 0.0 to 1.0. "
            "A score of 0.8-0.9 means the answer has correct main points with minor differences. "
            "1.0 is a perfect match, 0.6-0.7 is partially correct, and below 0.4 is mostly incorrect."
        ),
    },
    {
        "question": "What are the five steps in the evaluation harness pipeline?",
        "expected_answer": (
            "1. Collect news from WebSearch JSON, "
            "2. Generate quiz questions at L1-L4 levels, "
            "3. Run learning phase in subprocess to store articles in memory, "
            "4. Run testing phase in subprocess to answer questions from memory, "
            "5. Grade answers using semantic LLM comparison."
        ),
    },
    {
        "question": "Why does the harness run learning and testing in separate subprocesses?",
        "expected_answer": (
            "Learning and testing run in separate subprocesses for memory isolation. "
            "This ensures the testing phase can only access knowledge that was properly "
            "stored during the learning phase, preventing information leakage."
        ),
    },
    {
        "question": "What format does the news input file need to be in?",
        "expected_answer": (
            "The news file must be JSON with a 'sources' array. Each source object "
            "must have 'url', 'title', 'content', and 'published' fields. "
            "Missing required fields raise a ValueError."
        ),
    },
]


@dataclass
class ExperimentConfig:
    """Configuration for the meta-eval experiment.

    Attributes:
        teaching_turns: Number of teacher-student dialogue turns
        quiz_questions: Number of quiz questions to ask student
        model: LLM model identifier
        output_dir: Directory for saving reports
    """

    teaching_turns: int = 6
    quiz_questions: int = 5
    model: str = "claude-sonnet-4-5-20250929"
    output_dir: str = "./meta_eval_results"


@dataclass
class ExperimentReport:
    """Report from a complete meta-eval experiment.

    Attributes:
        knowledge_base_size: Number of facts in knowledge base
        teaching_turns_completed: Actual turns completed
        quiz_results: Per-question quiz results
        metacognition_scores: Per-question metacognition scores
        overall_score: Overall experiment score
        summary: Human-readable summary
    """

    knowledge_base_size: int
    teaching_turns_completed: int
    quiz_results: list[dict]
    metacognition_scores: list[dict]
    overall_score: float
    summary: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "knowledge_base_size": self.knowledge_base_size,
            "teaching_turns_completed": self.teaching_turns_completed,
            "quiz_results": self.quiz_results,
            "metacognition_scores": self.metacognition_scores,
            "overall_score": self.overall_score,
            "summary": self.summary,
        }


class MetaEvalExperiment:
    """Runs the complete meta-eval teaching experiment.

    The experiment:
    1. Builds a knowledge base about the eval system from source code
    2. Runs a teaching session where an expert teaches a student
    3. Quizzes the student on what they learned
    4. Grades the student's metacognition
    5. Produces a structured report

    Args:
        config: Experiment configuration

    Example:
        >>> experiment = MetaEvalExperiment(ExperimentConfig(teaching_turns=3))
        >>> report = experiment.run()
        >>> print(report.overall_score)
    """

    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config

    def build_knowledge_base(self) -> list[str]:
        """Build knowledge base from eval system documentation.

        Returns deterministic knowledge derived from source code analysis.

        Returns:
            List of knowledge strings about the eval system
        """
        return list(EVAL_KNOWLEDGE_BASE)

    def generate_eval_quiz(self, knowledge_base: list[str]) -> list[dict[str, str]]:
        """Generate quiz questions about the eval system.

        Args:
            knowledge_base: The knowledge base (used for context, not generation)

        Returns:
            List of dicts with 'question' and 'expected_answer' keys
        """
        # Use pre-built quiz, limited by config
        return EVAL_QUIZ[: self.config.quiz_questions]

    def run(self) -> ExperimentReport:
        """Run the complete experiment.

        Returns:
            ExperimentReport with all results
        """
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Step 1: Build knowledge base
        kb = self.build_knowledge_base()
        logger.info("Knowledge base built: %d facts", len(kb))

        # Step 2: Run teaching session
        try:
            teaching_config = TeachingConfig(
                max_turns=self.config.teaching_turns,
                model=self.config.model,
            )
            session = TeachingSession(knowledge_base=kb, config=teaching_config)
            teaching_result = session.run()
            turns_completed = len(teaching_result.turns)
            logger.info("Teaching session completed: %d turns", turns_completed)
        except Exception as e:
            logger.error("Teaching session failed: %s", e)
            return self._error_report(kb, str(e))

        # Step 3: Generate quiz
        quiz = self.generate_eval_quiz(kb)
        logger.info("Quiz generated: %d questions", len(quiz))

        # Step 4: Quiz the student (use teaching history as context)
        quiz_results = self._quiz_student(quiz, teaching_result)

        # Step 5: Grade metacognition
        grader = MetacognitionGrader(model=self.config.model)
        metacognition_scores = []
        score_values = []

        for i, (q, result) in enumerate(zip(quiz, quiz_results, strict=False)):
            mc_score = grader.grade(
                question=q["question"],
                expected_answer=q["expected_answer"],
                student_answer=result.get("student_answer", ""),
                self_explanation=result.get("self_explanation", ""),
            )
            metacognition_scores.append(
                {
                    "question": q["question"],
                    "overall": mc_score.overall_score,
                    "dimensions": {
                        d.name: {"score": d.score, "reasoning": d.reasoning}
                        for d in mc_score.dimensions
                    },
                    "summary": mc_score.summary,
                }
            )
            score_values.append(mc_score.overall_score)

        overall = sum(score_values) / len(score_values) if score_values else 0.0

        report = ExperimentReport(
            knowledge_base_size=len(kb),
            teaching_turns_completed=turns_completed,
            quiz_results=quiz_results,
            metacognition_scores=metacognition_scores,
            overall_score=overall,
            summary=self._generate_summary(overall, turns_completed, len(quiz)),
        )

        # Save report
        report_path = output_dir / "meta_eval_report.json"
        with open(report_path, "w") as f:
            json.dump(report.to_dict(), f, indent=2)

        logger.info("Report saved to %s", report_path)
        return report

    def _quiz_student(
        self,
        quiz: list[dict[str, str]],
        teaching_result,
    ) -> list[dict]:
        """Quiz the student using teaching history as context.

        The student has no direct access to the knowledge base;
        it can only use what it learned during the teaching session.
        """
        import litellm  # type: ignore[import-unresolved]

        # Build teaching context from the session
        teaching_context = ""
        for turn in teaching_result.turns:
            teaching_context += f"Teacher: {turn.teacher_message}\n"
            teaching_context += f"Student: {turn.student_response}\n\n"

        results = []
        for q in quiz:
            try:
                response = litellm.completion(
                    model=self.config.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a student who learned about an evaluation system. "
                                "Answer questions based ONLY on what you learned during teaching. "
                                "Also explain your reasoning. "
                                "Respond with JSON: "
                                '{"answer": "your answer", "self_explanation": "why you think this"}'
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                f"During your teaching session you learned:\n"
                                f"{teaching_context}\n\n"
                                f"Now answer this question:\n{q['question']}"
                            ),
                        },
                    ],
                    temperature=0.3,
                )

                text = response.choices[0].message.content.strip()
                try:
                    parsed = json.loads(text)
                    results.append(
                        {
                            "question": q["question"],
                            "student_answer": parsed.get("answer", text),
                            "self_explanation": parsed.get("self_explanation", ""),
                        }
                    )
                except json.JSONDecodeError:
                    results.append(
                        {
                            "question": q["question"],
                            "student_answer": text,
                            "self_explanation": "",
                        }
                    )

            except Exception as e:
                logger.warning("Quiz question failed: %s", e)
                results.append(
                    {
                        "question": q["question"],
                        "student_answer": f"Error: {e}",
                        "self_explanation": "",
                    }
                )

        return results

    def _generate_summary(self, overall: float, turns: int, questions: int) -> str:
        """Generate human-readable summary."""
        if overall >= 0.8:
            quality = "excellent"
        elif overall >= 0.6:
            quality = "good"
        elif overall >= 0.4:
            quality = "moderate"
        else:
            quality = "limited"

        return (
            f"Meta-eval experiment completed with {quality} results. "
            f"Teaching: {turns} turns. Quiz: {questions} questions. "
            f"Overall metacognition score: {overall:.2f}."
        )

    def _error_report(self, kb: list[str], error: str) -> ExperimentReport:
        """Generate an error report when experiment fails."""
        return ExperimentReport(
            knowledge_base_size=len(kb),
            teaching_turns_completed=0,
            quiz_results=[],
            metacognition_scores=[],
            overall_score=0.0,
            summary=f"Experiment failed: {error}",
        )


def main():
    """CLI entry point for meta-eval experiment."""
    import argparse

    parser = argparse.ArgumentParser(description="Meta-Eval Teaching Experiment")
    parser.add_argument(
        "--teaching-turns",
        type=int,
        default=6,
        help="Number of teaching dialogue turns",
    )
    parser.add_argument(
        "--quiz-questions",
        type=int,
        default=5,
        help="Number of quiz questions",
    )
    parser.add_argument(
        "--model",
        default="claude-sonnet-4-5-20250929",
        help="LLM model to use",
    )
    parser.add_argument(
        "--output-dir",
        default="./meta_eval_results",
        help="Output directory for report",
    )

    args = parser.parse_args()

    config = ExperimentConfig(
        teaching_turns=args.teaching_turns,
        quiz_questions=args.quiz_questions,
        model=args.model,
        output_dir=args.output_dir,
    )

    print("=" * 70)
    print("META-EVAL TEACHING EXPERIMENT")
    print("=" * 70)
    print(f"Teaching turns: {config.teaching_turns}")
    print(f"Quiz questions: {config.quiz_questions}")
    print(f"Model: {config.model}")
    print(f"Output: {config.output_dir}")
    print("=" * 70)

    experiment = MetaEvalExperiment(config=config)
    report = experiment.run()

    print(f"\n{report.summary}")
    print(f"\nOverall Score: {report.overall_score:.2%}")
    print(f"Knowledge Base: {report.knowledge_base_size} facts")
    print(f"Teaching Turns: {report.teaching_turns_completed}")
    print(f"Quiz Questions: {len(report.quiz_results)}")

    if report.metacognition_scores:
        print("\nPer-Question Metacognition Scores:")
        for mc in report.metacognition_scores:
            print(f"  Q: {mc['question'][:60]}...")
            print(f"    Overall: {mc['overall']:.2f}")
            for dim_name, dim_data in mc["dimensions"].items():
                print(f"    {dim_name}: {dim_data['score']:.2f}")
            print()

    print(f"\nReport saved to: {config.output_dir}/meta_eval_report.json")


if __name__ == "__main__":
    main()


__all__ = [
    "MetaEvalExperiment",
    "ExperimentConfig",
    "ExperimentReport",
]
