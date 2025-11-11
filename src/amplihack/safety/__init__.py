"""Safety module for preventing data loss in auto mode."""

from .git_conflict_detector import ConflictDetectionResult, GitConflictDetector
from .prompt_transformer import PromptTransformer
from .safe_copy_strategy import CopyStrategy, SafeCopyStrategy

__all__ = [
    "GitConflictDetector",
    "ConflictDetectionResult",
    "SafeCopyStrategy",
    "CopyStrategy",
    "PromptTransformer",
]
