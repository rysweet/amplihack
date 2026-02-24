"""Language detection for multi-language codebases.

Scans codebase to identify programming languages and loads language-specific
degradation patterns. Supports Python, JavaScript, TypeScript, Rust, Go, Java,
C#, Ruby, and PHP.
"""

from collections import Counter
from pathlib import Path


class LanguageDetector:
    """Detects programming languages in a codebase."""

    EXTENSION_MAP = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".cs": "csharp",
        ".rb": "ruby",
        ".php": "php",
    }

    IGNORE_DIRS = {
        "node_modules",
        "venv",
        ".venv",
        "env",
        ".env",
        "__pycache__",
        ".git",
        "dist",
        "build",
        "target",
        "bin",
        "obj",
        ".pytest_cache",
        ".mypy_cache",
    }

    def __init__(self, min_files: int = 5, min_percentage: float = 5.0):
        """Initialize language detector.

        Args:
            min_files: Minimum number of files to consider a language present
            min_percentage: Minimum percentage of files to consider a language significant
        """
        self.min_files = min_files
        self.min_percentage = min_percentage

    def detect_languages(self, codebase_path: str | Path) -> dict[str, int]:
        """Detect languages in codebase by file extensions.

        Args:
            codebase_path: Path to codebase root (str or Path object)

        Returns:
            Dictionary mapping language names to file counts
        """
        # Convert to Path if string
        if isinstance(codebase_path, str):
            codebase_path = Path(codebase_path)

        if not codebase_path.exists() or not codebase_path.is_dir():
            return {}

        language_counts = Counter()

        for file_path in self._scan_files(codebase_path):
            ext = file_path.suffix.lower()
            if ext in self.EXTENSION_MAP:
                language = self.EXTENSION_MAP[ext]
                language_counts[language] += 1

        total_files = sum(language_counts.values())
        if total_files == 0:
            return {}

        significant_languages = {}
        for language, count in language_counts.items():
            percentage = (count / total_files) * 100
            if count >= self.min_files or percentage >= self.min_percentage:
                significant_languages[language] = count

        return significant_languages

    def load_patterns_for_languages(self, languages: list[str]) -> dict[str, list[dict[str, str]]]:
        """Load language-specific degradation patterns.

        Args:
            languages: List of detected language names

        Returns:
            Dictionary mapping language names to pattern lists

        Note:
            Returns default patterns for each language. In production,
            this could be extended to load from external configuration.
        """
        patterns = {}

        for language in languages:
            patterns[language] = self._get_default_patterns(language)

        return patterns

    def _scan_files(self, directory: Path) -> list[Path]:
        """Recursively scan directory for code files."""
        files = []

        try:
            for item in directory.rglob("*"):
                if item.is_file():
                    if not any(ignore_dir in item.parts for ignore_dir in self.IGNORE_DIRS):
                        files.append(item)
        except PermissionError as e:
            # ALWAYS log permission errors - silent errors are what we hunt!
            # Permission denied can indicate security issues or audit blind spots
            print(f"Warning: Permission denied accessing {directory}: {e}")

        return files

    def _get_default_patterns(self, language: str) -> list[dict[str, str]]:
        """Get default degradation patterns for a language."""
        common_patterns = [
            {
                "pattern": "try.*except.*pass",
                "description": "Silent exception swallowing",
                "category": "config-errors",
            },
            {
                "pattern": "import.*# type: ignore",
                "description": "Type checking disabled",
                "category": "dependency-failures",
            },
        ]

        language_patterns = {
            "python": [
                {
                    "pattern": "except Exception:",
                    "description": "Bare except catching all exceptions",
                    "category": "background-work",
                },
                {
                    "pattern": "return {}",
                    "description": "Empty dict return (potential stub)",
                    "category": "functional-stubs",
                },
                {
                    "pattern": "return []",
                    "description": "Empty list return (potential stub)",
                    "category": "functional-stubs",
                },
            ],
            "javascript": [
                {
                    "pattern": "catch.*{}",
                    "description": "Empty catch block",
                    "category": "background-work",
                },
                {
                    "pattern": "return {};",
                    "description": "Empty object return (potential stub)",
                    "category": "functional-stubs",
                },
            ],
            "typescript": [
                {
                    "pattern": "// @ts-ignore",
                    "description": "TypeScript error suppression",
                    "category": "config-errors",
                },
                {
                    "pattern": "return {} as",
                    "description": "Empty object with type assertion (potential stub)",
                    "category": "functional-stubs",
                },
            ],
            "rust": [
                {
                    "pattern": "unwrap\\(\\)",
                    "description": "Panic on error instead of handling",
                    "category": "dependency-failures",
                },
                {
                    "pattern": "todo!\\(\\)",
                    "description": "Unimplemented code marker",
                    "category": "functional-stubs",
                },
            ],
            "go": [
                {
                    "pattern": "if err != nil { _ = err }",
                    "description": "Error discarded",
                    "category": "background-work",
                },
                {
                    "pattern": "return nil",
                    "description": "Nil return (potential stub)",
                    "category": "functional-stubs",
                },
            ],
            "java": [
                {
                    "pattern": "catch.*Exception.*\\{\\s*\\}",
                    "description": "Empty catch block",
                    "category": "background-work",
                },
                {
                    "pattern": "return null;",
                    "description": "Null return (potential stub)",
                    "category": "functional-stubs",
                },
            ],
            "csharp": [
                {
                    "pattern": "catch.*\\{\\s*\\}",
                    "description": "Empty catch block",
                    "category": "background-work",
                },
                {
                    "pattern": "Task.CompletedTask",
                    "description": "Empty async task (potential stub)",
                    "category": "functional-stubs",
                },
                {
                    "pattern": "return default;",
                    "description": "Default value return (potential stub)",
                    "category": "functional-stubs",
                },
            ],
            "ruby": [
                {
                    "pattern": "rescue.*nil",
                    "description": "Exception rescued and ignored",
                    "category": "background-work",
                },
            ],
            "php": [
                {
                    "pattern": "@.*\\(",
                    "description": "Error suppression operator",
                    "category": "config-errors",
                },
            ],
        }

        return common_patterns + language_patterns.get(language, [])


def detect_languages(codebase_path: Path) -> dict[str, int]:
    """Convenience function to detect languages.

    Args:
        codebase_path: Path to codebase root

    Returns:
        Dictionary mapping language names to file counts
    """
    detector = LanguageDetector()
    return detector.detect_languages(codebase_path)


def load_patterns_for_languages(languages: list[str]) -> dict[str, list[dict[str, str]]]:
    """Convenience function to load patterns.

    Args:
        languages: List of detected language names

    Returns:
        Dictionary mapping language names to pattern lists
    """
    detector = LanguageDetector()
    return detector.load_patterns_for_languages(languages)
