"""Language detection module for LSP Auto-Configuration.

Detects programming languages in project directory by scanning file extensions
and project markers (package.json, Cargo.toml, etc.).

Philosophy:
- Single responsibility: Language detection only
- Standard library only (Path, os, glob)
- Self-contained and regeneratable

Public API:
    LanguageDetection: Result of language detection scan
    LanguageDetector: Main language detection class
"""

import fnmatch
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LanguageDetection:
    """Result of language detection scan."""

    language: str  # e.g., "python", "typescript"
    file_count: int  # Number of files detected
    primary: bool  # True if this is primary project language
    markers: list[str]  # Framework markers found (e.g., "package.json")


class LanguageDetector:
    """Detects programming languages in project directory.

    Scans project files and identifies languages based on:
    - File extensions (.py, .ts, .rs, etc.)
    - Project markers (package.json, Cargo.toml, etc.)
    - Framework-specific files

    Example:
        >>> detector = LanguageDetector(Path("/path/to/project"))
        >>> languages = detector.detect_languages()
        >>> for lang in languages:
        ...     print(f"{lang}: {languages[lang]} files")
    """

    # Language definitions: extensions and project markers
    LANGUAGE_DEFINITIONS = {
        "python": {
            "extensions": [".py", ".pyi", ".pyw"],
            "markers": ["setup.py", "pyproject.toml", "requirements.txt", "Pipfile"],
        },
        "typescript": {
            "extensions": [".ts", ".tsx"],
            "markers": ["tsconfig.json", "package.json"],
        },
        "javascript": {
            "extensions": [".js", ".jsx", ".mjs", ".cjs"],
            "markers": ["package.json", "package-lock.json"],
        },
        "rust": {
            "extensions": [".rs"],
            "markers": ["Cargo.toml", "Cargo.lock"],
        },
        "go": {
            "extensions": [".go"],
            "markers": ["go.mod", "go.sum"],
        },
        "java": {
            "extensions": [".java"],
            "markers": ["pom.xml", "build.gradle", "build.gradle.kts"],
        },
        "cpp": {
            "extensions": [".cpp", ".cc", ".cxx", ".h", ".hpp"],
            "markers": ["CMakeLists.txt", "Makefile"],
        },
        "ruby": {
            "extensions": [".rb"],
            "markers": ["Gemfile", "Rakefile"],
        },
        "php": {
            "extensions": [".php"],
            "markers": ["composer.json"],
        },
        "csharp": {
            "extensions": [".cs"],
            "markers": [".csproj", ".sln"],
        },
        "kotlin": {
            "extensions": [".kt", ".kts"],
            "markers": ["build.gradle.kts"],
        },
        "swift": {
            "extensions": [".swift"],
            "markers": ["Package.swift"],
        },
        "scala": {
            "extensions": [".scala"],
            "markers": ["build.sbt"],
        },
        "lua": {
            "extensions": [".lua"],
            "markers": [],
        },
        "elixir": {
            "extensions": [".ex", ".exs"],
            "markers": ["mix.exs"],
        },
        "haskell": {
            "extensions": [".hs", ".lhs"],
            "markers": ["stack.yaml", "cabal.project"],
        },
    }

    # Common directories to ignore
    IGNORED_DIRS = {
        "node_modules",
        ".git",
        ".venv",
        "venv",
        "env",
        "__pycache__",
        ".pytest_cache",
        "dist",
        "build",
        "target",
        ".idea",
        ".vscode",
        "coverage",
        ".next",
        ".nuxt",
    }

    def __init__(self, project_root: Path, max_languages: int | None = None):
        """Initialize language detector.

        Args:
            project_root: Path to project root directory
            max_languages: Optional limit on number of languages to detect
        """
        self.project_root = Path(project_root)
        self.max_languages = max_languages
        self._gitignore_patterns: list[str] | None = None
        # Load gitignore patterns on init
        self._load_gitignore()

    def detect_languages(self, max_languages: int | None = None) -> dict[str, int]:
        """Detect all programming languages in project.

        Args:
            max_languages: Optional limit on number of languages to return (overrides init value)

        Returns:
            Dict mapping language name to file count, sorted by count descending

        Example:
            >>> detector.detect_languages()
            {'python': 23, 'yaml': 2}
        """
        language_counts: dict[str, int] = {}

        # Scan all files in project
        for file_path in self._scan_project_files():
            # Check each language's extensions
            for language, config in self.LANGUAGE_DEFINITIONS.items():
                if self._is_language_file(file_path, language):
                    language_counts[language] = language_counts.get(language, 0) + 1

        # Sort by count descending
        sorted_languages = dict(sorted(language_counts.items(), key=lambda x: x[1], reverse=True))

        # Apply max limit from parameter or init
        limit = max_languages if max_languages is not None else self.max_languages
        if limit is not None:
            sorted_languages = dict(list(sorted_languages.items())[:limit])

        return sorted_languages

    def detect_languages_with_confidence(self) -> dict[str, int]:
        """Detect languages with confidence scores (file counts).

        Returns:
            Dict mapping language name to file count (confidence score)

        Example:
            >>> detector.detect_languages_with_confidence()
            {'python': 23, 'javascript': 12}
        """
        return self.detect_languages()

    def get_primary_language(self) -> str | None:
        """Identify the primary language of the project.

        Primary language determined by:
        1. Presence of framework markers (package.json, Cargo.toml, etc.)
        2. Language with most files

        Returns:
            Primary language name, or None if no languages detected

        Example:
            >>> detector.get_primary_language()
            'python'
        """
        # First check for framework markers
        for language, config in self.LANGUAGE_DEFINITIONS.items():
            for marker in config.get("markers", []):
                marker_path = self.project_root / marker
                if marker_path.exists():
                    return language

        # Fall back to language with most files
        languages = self.detect_languages()
        if languages:
            return next(iter(languages))  # First key (highest count)

        return None

    def detect_language_frameworks(self, language: str) -> list[str]:
        """Detect frameworks for a specific language.

        Args:
            language: Language identifier (e.g., "python", "typescript")

        Returns:
            List of framework markers found

        Example:
            >>> detector.detect_language_frameworks("python")
            ['pyproject.toml', 'setup.py']
        """
        if language not in self.LANGUAGE_DEFINITIONS:
            return []

        markers_found = []
        markers = self.LANGUAGE_DEFINITIONS[language].get("markers", [])

        for marker in markers:
            marker_path = self.project_root / marker
            if marker_path.exists():
                markers_found.append(marker)

        return markers_found

    def _scan_project_files(self) -> list[Path]:
        """Scan project directory for all files, respecting ignored dirs.

        Returns:
            List of file paths to analyze
        """
        files = []

        for path in self.project_root.rglob("*"):
            # Skip if path is file and not in ignored directory
            if path.is_file():
                # Check if any parent is in ignored dirs
                if not self._should_ignore_path(path):
                    files.append(path)

        return files

    def _should_ignore_path(self, path: Path) -> bool:
        """Check if path should be ignored based on ignored dirs and gitignore.

        Args:
            path: Path to check

        Returns:
            True if path should be ignored
        """
        # Check if any parent directory is in ignored list
        parts = path.relative_to(self.project_root).parts
        for part in parts[:-1]:  # Exclude filename itself
            if part in self.IGNORED_DIRS:
                return True

        # Check gitignore patterns if available
        if self._gitignore_patterns is not None:
            relative_path = str(path.relative_to(self.project_root))
            filename = path.name

            for pattern in self._gitignore_patterns:
                # Handle directory patterns (ending with /)
                if pattern.endswith("/"):
                    dir_pattern = pattern[:-1]
                    # Check if path is inside this directory
                    if dir_pattern in parts:
                        return True
                # Handle wildcard patterns
                elif fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(relative_path, pattern):
                    return True

        return False

    def _load_gitignore(self) -> None:
        """Load .gitignore patterns for filtering."""
        gitignore_path = self.project_root / ".gitignore"
        if not gitignore_path.exists():
            self._gitignore_patterns = []
            return

        patterns = []
        with open(gitignore_path) as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith("#"):
                    patterns.append(line)

        self._gitignore_patterns = patterns

    def _is_language_file(self, file_path: Path, language: str) -> bool:
        """Check if file belongs to specified language.

        Args:
            file_path: Path to file
            language: Language to check

        Returns:
            True if file extension matches language
        """
        if language not in self.LANGUAGE_DEFINITIONS:
            return False

        extensions = self.LANGUAGE_DEFINITIONS[language]["extensions"]
        return file_path.suffix in extensions

    def get_file_extensions_for_language(self, language: str) -> list[str]:
        """Get file extensions for a specific language.

        Args:
            language: Language identifier

        Returns:
            List of file extensions (e.g., ['.py', '.pyi'])
        """
        if language not in self.LANGUAGE_DEFINITIONS:
            return []

        return self.LANGUAGE_DEFINITIONS[language]["extensions"]

    def get_extensions_for_language(self, language: str) -> list[str]:
        """Alias for get_file_extensions_for_language.

        Args:
            language: Language identifier

        Returns:
            List of file extensions
        """
        return self.get_file_extensions_for_language(language)

    def is_language_file(self, file_path: Path, language: str) -> bool:
        """Public API for checking if file is a specific language.

        Args:
            file_path: Path to file
            language: Language to check

        Returns:
            True if file belongs to language
        """
        return self._is_language_file(file_path, language)


__all__ = ["LanguageDetection", "LanguageDetector"]
