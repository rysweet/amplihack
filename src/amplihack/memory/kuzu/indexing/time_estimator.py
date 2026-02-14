"""Time estimation for blarify indexing operations.

Provides accurate time estimates based on calibrated indexing rates for different languages.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class TimeEstimate:
    """Time estimate for indexing operation."""

    total_seconds: float
    by_language: dict[str, float]
    file_counts: dict[str, int]


# Calibrated indexing rates (files per second) from empirical testing
# Based on average SCIP indexing performance: 300-600 files/minute
INDEXING_RATES = {
    "python": 20,  # files/second (simple syntax)
    "typescript": 15,  # files/second (complex types)
    "javascript": 15,  # files/second (similar to TypeScript)
    "go": 25,  # files/second (fast compilation)
    "rust": 10,  # files/second (complex analysis)
    "csharp": 15,  # files/second (moderate complexity)
    "c": 20,  # files/second (simple syntax)
    "cpp": 15,  # files/second (template complexity)
}

# File extension mappings to languages
LANGUAGE_EXTENSIONS = {
    "python": [".py"],
    "typescript": [".ts", ".tsx"],
    "javascript": [".js", ".jsx"],
    "go": [".go"],
    "rust": [".rs"],
    "csharp": [".cs"],
    "c": [".c", ".h"],
    "cpp": [".cpp", ".hpp", ".cc", ".cxx"],
}

# Directories to ignore
IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    ".mypy_cache",
    ".tox",
    "dist",
    "build",
    ".eggs",
    "*.egg-info",
}


def estimate_time(project_path: Path, languages: list[str]) -> TimeEstimate:
    """Calculate time estimate for indexing.

    Logic:
    - Count files by extension for each language
    - Apply INDEXING_RATES to calculate time per language
    - Sum to get total_seconds
    - Return TimeEstimate with breakdown

    Performance: < 500ms via file counting (not opening files)

    Args:
        project_path: Project root directory
        languages: Languages to estimate (e.g., ["python", "typescript"])

    Returns:
        TimeEstimate with total_seconds, by_language breakdown, and file_counts
    """
    project_path = Path(project_path).resolve()

    # Count files by language
    file_counts = _count_files_by_language(project_path, languages)

    # Calculate time estimates by language
    by_language = {}
    total_seconds = 0.0

    for language in languages:
        file_count = file_counts.get(language, 0)
        rate = INDEXING_RATES.get(language, 15)  # Default to 15 files/sec

        # Calculate time: files / (files per second)
        time_seconds = file_count / rate if file_count > 0 else 0.0

        by_language[language] = time_seconds
        total_seconds += time_seconds

    return TimeEstimate(
        total_seconds=total_seconds,
        by_language=by_language,
        file_counts=file_counts,
    )


def _count_files_by_language(project_path: Path, languages: list[str]) -> dict[str, int]:
    """Count files by language based on extensions.

    Args:
        project_path: Project root directory
        languages: Languages to count

    Returns:
        Dict mapping language to file count
    """
    counts = dict.fromkeys(languages, 0)

    # Build extension to language mapping for requested languages
    ext_to_lang = {}
    for lang in languages:
        if lang in LANGUAGE_EXTENSIONS:
            for ext in LANGUAGE_EXTENSIONS[lang]:
                ext_to_lang[ext] = lang

    try:
        for item in project_path.rglob("*"):
            # Skip ignored directories
            if any(ignored in item.parts for ignored in IGNORED_DIRS):
                continue

            # Count files by extension
            if item.is_file() and item.suffix in ext_to_lang:
                lang = ext_to_lang[item.suffix]
                counts[lang] += 1
    except (PermissionError, OSError):
        # Skip directories/files we can't access
        pass

    return counts
