"""Progress tracking for Blarify indexing operations.

Tracks progress, estimates time, and provides status updates during indexing.
"""

import time
from dataclasses import dataclass, field


@dataclass
class LanguageProgress:
    """Progress information for a single language."""

    language: str
    processed_files: int
    total_files: int
    percentage: float
    completed: bool
    elapsed_seconds: float
    start_time: float = field(default_factory=time.time)


@dataclass
class ProgressUpdate:
    """Update about overall progress."""

    total_files: int
    processed_files: int
    percentage: float
    current_language: str | None = None
    languages_completed: list[str] = field(default_factory=list)
    languages_remaining: list[str] = field(default_factory=list)


class ProgressTracker:
    """Track progress during Blarify indexing."""

    def __init__(self, languages: list[str]):
        """Initialize progress tracker.

        Args:
            languages: List of languages to track
        """
        self.languages = languages
        self._progress: dict[str, LanguageProgress] = {}
        self._current_language: str | None = None
        self._start_times: dict[str, float] = {}

    def start_language(self, language: str, estimated_files: int) -> None:
        """Start tracking progress for a language.

        Args:
            language: Language name
            estimated_files: Estimated number of files to process
        """
        start_time = time.time()
        self._start_times[language] = start_time
        self._current_language = language

        self._progress[language] = LanguageProgress(
            language=language,
            processed_files=0,
            total_files=estimated_files,
            percentage=0.0,
            completed=False,
            elapsed_seconds=0.0,
            start_time=start_time,
        )

    def update_progress(self, language: str, processed_files: int) -> None:
        """Update progress for a language.

        Args:
            language: Language name
            processed_files: Number of files processed so far
        """
        if language not in self._progress:
            # Auto-start if not already started
            self.start_language(language, processed_files)

        progress = self._progress[language]
        progress.processed_files = processed_files

        # Update total if we've exceeded the estimate
        if processed_files > progress.total_files:
            progress.total_files = processed_files

        # Calculate percentage
        if progress.total_files > 0:
            progress.percentage = (processed_files / progress.total_files) * 100.0
        else:
            progress.percentage = 0.0

        # Update elapsed time
        progress.elapsed_seconds = time.time() - progress.start_time

    def complete_language(self, language: str, final_count: int) -> None:
        """Mark a language as completed.

        Args:
            language: Language name
            final_count: Final number of files processed
        """
        if language not in self._progress:
            self.start_language(language, final_count)

        progress = self._progress[language]
        progress.processed_files = final_count
        progress.total_files = final_count
        progress.percentage = 100.0
        progress.completed = True
        progress.elapsed_seconds = time.time() - progress.start_time

        # Clear current language if this was it
        if self._current_language == language:
            self._current_language = None

    def get_progress(self, language: str) -> LanguageProgress:
        """Get current progress for a language.

        Args:
            language: Language name

        Returns:
            LanguageProgress object
        """
        if language not in self._progress:
            return LanguageProgress(
                language=language,
                processed_files=0,
                total_files=0,
                percentage=0.0,
                completed=False,
                elapsed_seconds=0.0,
            )

        progress = self._progress[language]
        # Update elapsed time
        if not progress.completed:
            progress.elapsed_seconds = time.time() - progress.start_time

        return progress

    def get_current_language(self) -> str | None:
        """Get the currently processing language.

        Returns:
            Language name or None
        """
        return self._current_language

    def estimate_remaining_time(self, language: str) -> float:
        """Estimate remaining time for a language.

        Args:
            language: Language name

        Returns:
            Estimated seconds remaining
        """
        if language not in self._progress:
            return 0.0

        progress = self._progress[language]

        if progress.processed_files == 0:
            return 0.0

        # Calculate processing rate (files per second)
        elapsed = time.time() - progress.start_time
        if elapsed == 0:
            return 0.0

        rate = progress.processed_files / elapsed

        # Estimate remaining time
        remaining_files = progress.total_files - progress.processed_files
        if rate > 0:
            return remaining_files / rate
        return 0.0

    def get_overall_progress(self) -> ProgressUpdate:
        """Get overall progress across all languages.

        Returns:
            ProgressUpdate with overall status
        """
        total_files = 0
        processed_files = 0
        completed_languages = []
        remaining_languages = []

        for language in self.languages:
            if language in self._progress:
                progress = self._progress[language]
                total_files += progress.total_files
                processed_files += progress.processed_files

                if progress.completed:
                    completed_languages.append(language)
                else:
                    remaining_languages.append(language)
            else:
                remaining_languages.append(language)

        percentage = 0.0
        if total_files > 0:
            percentage = (processed_files / total_files) * 100.0

        return ProgressUpdate(
            total_files=total_files,
            processed_files=processed_files,
            percentage=percentage,
            current_language=self._current_language,
            languages_completed=completed_languages,
            languages_remaining=remaining_languages,
        )

    def format_progress_display(self, language: str) -> str:
        """Format progress for display.

        Args:
            language: Language name

        Returns:
            Formatted progress string
        """
        progress = self.get_progress(language)

        if progress.completed:
            return f"{language}: Completed ({progress.processed_files} files)"

        return (
            f"{language}: {progress.processed_files}/{progress.total_files} files "
            f"({progress.percentage:.1f}%)"
        )

    def reset_language(self, language: str) -> None:
        """Reset progress for a language.

        Args:
            language: Language name
        """
        if language in self._progress:
            del self._progress[language]
        if language in self._start_times:
            del self._start_times[language]
        if self._current_language == language:
            self._current_language = None
