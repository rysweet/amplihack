"""Agent learning evaluation harness.

Production-ready framework for evaluating goal-seeking agents
across execution boundaries using persistent memory.

Also provides domain-specific evaluation:
- DomainEvalHarness: Generic harness for domain agents
- DomainTeachingEvaluator: Teaching ability evaluation
- run_combined_eval: Combined domain + teaching scores
"""

from .grader import GradeResult, grade_answer
from .harness_runner import HarnessConfig, HarnessResult, run_harness
from .multi_source_collector import NewsArticle, collect_news
from .quiz_generator import QuizQuestion, generate_quiz

__all__ = [
    "collect_news",
    "NewsArticle",
    "generate_quiz",
    "QuizQuestion",
    "grade_answer",
    "GradeResult",
    "run_harness",
    "HarnessConfig",
    "HarnessResult",
]
