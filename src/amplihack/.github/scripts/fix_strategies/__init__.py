"""Fix strategies for automated link fixing.

This package contains strategy implementations for fixing different types of
broken links. Each strategy implements the FixStrategy abstract base class.

Available strategies:
- CaseSensitivityFix: Fixes case mismatches (README.MD -> README.md)
- GitHistoryFix: Finds files that were moved using git history
- MissingExtensionFix: Adds missing .md extensions
- BrokenAnchorsFix: Fixes or suggests anchors
- RelativePathFix: Normalizes relative paths
- DoubleSlashFix: Removes double slashes from paths
"""

from .broken_anchors import BrokenAnchorsFix
from .case_sensitivity import CaseSensitivityFix
from .double_slash import DoubleSlashFix
from .git_history import GitHistoryFix
from .missing_extension import MissingExtensionFix
from .relative_path import RelativePathFix

__all__ = [
    "CaseSensitivityFix",
    "GitHistoryFix",
    "MissingExtensionFix",
    "BrokenAnchorsFix",
    "RelativePathFix",
    "DoubleSlashFix",
]
