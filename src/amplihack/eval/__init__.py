"""Agent learning evaluation harness.

Production-ready framework for evaluating goal-seeking agents
across execution boundaries using persistent memory.

Includes meta-eval teaching experiment for agent-teaches-agent evaluation.
"""

from .grader import GradeResult, grade_answer
from .harness_runner import HarnessConfig, HarnessResult, run_harness
from .meta_eval_experiment import ExperimentConfig, ExperimentReport, MetaEvalExperiment
from .metacognition_grader import Dimension, MetacognitionGrader, MetacognitionScore
from .multi_source_collector import NewsArticle, collect_news
from .quiz_generator import QuizQuestion, generate_quiz
from .teaching_session import TeachingConfig, TeachingResult, TeachingSession, Turn

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
    "TeachingSession",
    "TeachingConfig",
    "TeachingResult",
    "Turn",
    "MetacognitionGrader",
    "MetacognitionScore",
    "Dimension",
    "MetaEvalExperiment",
    "ExperimentConfig",
    "ExperimentReport",
]
