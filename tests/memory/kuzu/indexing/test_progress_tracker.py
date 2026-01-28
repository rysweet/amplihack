"""Tests for ProgressTracker module.

Tests time estimation, progress updates, completion tracking,
and display of current language being processed.
"""

import time

import pytest

from amplihack.memory.kuzu.indexing.progress_tracker import (
    ProgressTracker,
)


class TestProgressTracker:
    """Test progress tracking during indexing."""

    @pytest.fixture
    def tracker(self):
        """Create ProgressTracker instance."""
        languages = ["python", "javascript", "typescript"]
        return ProgressTracker(languages=languages)

    def test_time_estimation_within_accuracy(self, tracker):
        """Test time estimation calculation (within ±20% accuracy)."""
        # Arrange
        tracker.start_language("python", estimated_files=100)
        time.sleep(0.1)  # Simulate 0.1 seconds for 10 files
        tracker.update_progress("python", processed_files=10)

        # Act
        estimated_remaining = tracker.estimate_remaining_time("python")

        # Assert - For 10 files in 0.1s, rate is ~0.01s/file
        # Remaining 90 files should take ~0.9s
        # Allow ±20% tolerance (0.72s - 1.08s)
        assert 0.72 <= estimated_remaining <= 1.08

    def test_progress_updates_during_indexing(self, tracker):
        """Test progress updates during indexing."""
        # Arrange
        tracker.start_language("python", estimated_files=100)

        # Act
        tracker.update_progress("python", processed_files=25)
        progress = tracker.get_progress("python")

        # Assert
        assert progress.language == "python"
        assert progress.processed_files == 25
        assert progress.total_files == 100
        assert progress.percentage == 25.0
        assert progress.completed is False

    def test_completion_tracking_per_language(self, tracker):
        """Test completion tracking per language."""
        # Arrange
        tracker.start_language("python", estimated_files=100)
        tracker.start_language("javascript", estimated_files=50)

        # Act - Complete python
        tracker.complete_language("python", final_count=100)
        python_progress = tracker.get_progress("python")

        # Complete javascript
        tracker.complete_language("javascript", final_count=50)
        javascript_progress = tracker.get_progress("javascript")

        # Assert
        assert python_progress.completed is True
        assert python_progress.processed_files == 100
        assert javascript_progress.completed is True
        assert javascript_progress.processed_files == 50

    def test_display_current_language_being_processed(self, tracker):
        """Test display of current language being processed."""
        # Arrange
        tracker.start_language("python", estimated_files=100)

        # Act
        current_language = tracker.get_current_language()

        # Assert
        assert current_language == "python"

    def test_multiple_language_progress_tracking(self, tracker):
        """Test tracking multiple languages simultaneously."""
        # Arrange
        tracker.start_language("python", estimated_files=100)
        tracker.update_progress("python", processed_files=50)

        tracker.start_language("javascript", estimated_files=50)
        tracker.update_progress("javascript", processed_files=25)

        # Act
        python_progress = tracker.get_progress("python")
        javascript_progress = tracker.get_progress("javascript")

        # Assert
        assert python_progress.percentage == 50.0
        assert javascript_progress.percentage == 50.0
        assert python_progress.completed is False
        assert javascript_progress.completed is False

    def test_overall_progress_calculation(self, tracker):
        """Test overall progress across all languages."""
        # Arrange
        tracker.start_language("python", estimated_files=100)
        tracker.update_progress("python", processed_files=100)
        tracker.complete_language("python", final_count=100)

        tracker.start_language("javascript", estimated_files=50)
        tracker.update_progress("javascript", processed_files=25)

        # Act
        overall_progress = tracker.get_overall_progress()

        # Assert
        # 100 + 25 = 125 out of 150 total = 83.33%
        assert overall_progress.total_files == 150
        assert overall_progress.processed_files == 125
        assert 83.0 <= overall_progress.percentage <= 84.0

    def test_time_estimation_accuracy_threshold(self, tracker):
        """Test that time estimation stays within ±20% after sufficient samples."""
        # Arrange
        tracker.start_language("python", estimated_files=1000)

        # Simulate processing with consistent rate
        start_time = time.time()
        for i in range(1, 11):
            time.sleep(0.01)  # 10ms per 10 files = 1ms per file
            tracker.update_progress("python", processed_files=i * 10)

        # Act
        estimated_remaining = tracker.estimate_remaining_time("python")

        # Assert - Should estimate ~900ms for remaining 900 files
        # Allow ±20% tolerance (720ms - 1080ms)
        assert 0.72 <= estimated_remaining <= 1.08

    def test_progress_percentage_calculation(self, tracker):
        """Test accurate percentage calculation."""
        # Arrange
        tracker.start_language("python", estimated_files=100)

        # Act & Assert various percentages
        tracker.update_progress("python", processed_files=0)
        assert tracker.get_progress("python").percentage == 0.0

        tracker.update_progress("python", processed_files=25)
        assert tracker.get_progress("python").percentage == 25.0

        tracker.update_progress("python", processed_files=50)
        assert tracker.get_progress("python").percentage == 50.0

        tracker.update_progress("python", processed_files=100)
        assert tracker.get_progress("python").percentage == 100.0

    def test_elapsed_time_tracking(self, tracker):
        """Test elapsed time tracking per language."""
        # Arrange
        tracker.start_language("python", estimated_files=100)
        time.sleep(0.2)  # Wait 200ms

        # Act
        progress = tracker.get_progress("python")

        # Assert
        assert progress.elapsed_seconds >= 0.2
        assert progress.elapsed_seconds < 0.3  # Allow some overhead

    def test_format_progress_display(self, tracker):
        """Test formatted progress display string."""
        # Arrange
        tracker.start_language("python", estimated_files=100)
        tracker.update_progress("python", processed_files=50)

        # Act
        display = tracker.format_progress_display("python")

        # Assert
        assert "python" in display.lower()
        assert "50" in display or "50%" in display
        assert "100" in display

    def test_no_division_by_zero_on_empty_estimate(self, tracker):
        """Test handling of zero estimated files."""
        # Arrange
        tracker.start_language("python", estimated_files=0)

        # Act
        tracker.update_progress("python", processed_files=10)
        progress = tracker.get_progress("python")

        # Assert - Should handle gracefully
        assert progress.percentage >= 0
        assert progress.total_files >= progress.processed_files

    def test_reset_language_progress(self, tracker):
        """Test resetting progress for a language."""
        # Arrange
        tracker.start_language("python", estimated_files=100)
        tracker.update_progress("python", processed_files=50)

        # Act
        tracker.reset_language("python")
        progress = tracker.get_progress("python")

        # Assert
        assert progress.processed_files == 0
        assert progress.completed is False
        assert progress.elapsed_seconds == 0

    def test_concurrent_language_tracking(self, tracker):
        """Test tracking multiple languages concurrently."""
        # Arrange & Act
        tracker.start_language("python", estimated_files=100)
        tracker.start_language("javascript", estimated_files=50)
        tracker.start_language("typescript", estimated_files=75)

        tracker.update_progress("python", processed_files=30)
        tracker.update_progress("javascript", processed_files=25)
        tracker.update_progress("typescript", processed_files=15)

        # Assert
        assert tracker.get_progress("python").percentage == 30.0
        assert tracker.get_progress("javascript").percentage == 50.0
        assert tracker.get_progress("typescript").percentage == 20.0
