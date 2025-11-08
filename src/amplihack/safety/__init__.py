"""Safety module for preventing data loss in auto mode."""

from .git_conflict_detector import GitConflictDetector, ConflictDetectionResult
from .safe_copy_strategy import SafeCopyStrategy, CopyStrategy
from .prompt_transformer import PromptTransformer

__all__ = [
    "GitConflictDetector",
    "ConflictDetectionResult",
    "SafeCopyStrategy",
    "CopyStrategy",
    "PromptTransformer",
]
