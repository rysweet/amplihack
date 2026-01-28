"""Tests for BackgroundIndexer module.

Tests background process creation, job status tracking,
log file creation, process isolation, and completion notification.
"""

import time
from pathlib import Path

import pytest

from amplihack.memory.kuzu.indexing.background_indexer import (
    BackgroundIndexer,
    JobStatus,
)


class TestBackgroundIndexer:
    """Test background indexing functionality."""

    @pytest.fixture
    def indexer(self, tmp_path):
        """Create BackgroundIndexer instance."""
        return BackgroundIndexer(log_dir=tmp_path)

    def test_background_process_creation(self, indexer):
        """Test background process creation."""
        # Arrange
        codebase_path = Path("/path/to/codebase")
        languages = ["python", "javascript"]

        # Act
        job = indexer.start_background_job(
            codebase_path=codebase_path,
            languages=languages,
        )

        # Assert
        assert job.job_id is not None
        assert job.status == JobStatus.RUNNING
        assert job.process is not None
        assert job.process.pid > 0

    def test_job_status_tracking(self, indexer):
        """Test job status tracking."""
        # Arrange
        codebase_path = Path("/path/to/codebase")
        job = indexer.start_background_job(codebase_path, ["python"])

        # Act
        status1 = indexer.get_job_status(job.job_id)
        time.sleep(0.1)
        status2 = indexer.get_job_status(job.job_id)

        # Assert
        assert status1 in [JobStatus.RUNNING, JobStatus.COMPLETED]
        assert status2 in [JobStatus.RUNNING, JobStatus.COMPLETED]

    def test_log_file_creation(self, indexer, tmp_path):
        """Test log file creation."""
        # Arrange
        codebase_path = Path("/path/to/codebase")

        # Act
        job = indexer.start_background_job(codebase_path, ["python"])

        # Assert
        assert job.log_file is not None
        assert job.log_file.exists()
        assert job.log_file.parent == tmp_path

    def test_process_isolation_doesnt_block_main_thread(self, indexer):
        """Test process isolation (doesn't block main thread)."""
        # Arrange
        codebase_path = Path("/path/to/codebase")

        # Act
        start_time = time.time()
        job = indexer.start_background_job(codebase_path, ["python"])
        elapsed = time.time() - start_time

        # Assert - Should return immediately (< 1 second)
        assert elapsed < 1.0
        assert job.status == JobStatus.RUNNING

    def test_job_completion_notification(self, indexer):
        """Test job completion notification."""
        # Arrange
        notification_received = []

        def completion_callback(job_id, result):
            notification_received.append((job_id, result))

        indexer.register_completion_callback(completion_callback)
        codebase_path = Path("/path/to/codebase")

        # Act
        job = indexer.start_background_job(codebase_path, ["python"])
        job.wait(timeout=5.0)

        # Assert
        assert len(notification_received) == 1
        assert notification_received[0][0] == job.job_id

    def test_multiple_concurrent_jobs(self, indexer):
        """Test multiple concurrent background jobs."""
        # Arrange
        jobs = []

        # Act
        for i in range(3):
            job = indexer.start_background_job(
                codebase_path=Path(f"/path/to/codebase{i}"),
                languages=["python"],
            )
            jobs.append(job)

        # Assert
        assert len(jobs) == 3
        assert all(j.status == JobStatus.RUNNING for j in jobs)
        assert len(set(j.job_id for j in jobs)) == 3  # Unique job IDs

    def test_job_cancellation(self, indexer):
        """Test job cancellation."""
        # Arrange
        job = indexer.start_background_job(Path("/path/to/codebase"), ["python"])

        # Act
        indexer.cancel_job(job.job_id)
        time.sleep(0.5)
        status = indexer.get_job_status(job.job_id)

        # Assert
        assert status == JobStatus.CANCELLED

    def test_log_streaming(self, indexer):
        """Test streaming logs from background job."""
        # Arrange
        job = indexer.start_background_job(Path("/path/to/codebase"), ["python"])
        time.sleep(0.5)

        # Act
        log_lines = indexer.stream_logs(job.job_id, max_lines=10)

        # Assert
        assert isinstance(log_lines, list)
        assert len(log_lines) <= 10

    def test_job_result_retrieval(self, indexer):
        """Test retrieving job results after completion."""
        # Arrange
        job = indexer.start_background_job(Path("/path/to/codebase"), ["python"])
        job.wait(timeout=5.0)

        # Act
        result = indexer.get_job_result(job.job_id)

        # Assert
        assert result is not None
        assert hasattr(result, "files_indexed")
        assert hasattr(result, "languages_completed")

    def test_error_handling_in_background_job(self, indexer):
        """Test error handling in background job."""
        # Arrange
        job = indexer.start_background_job(
            Path("/nonexistent/path"),
            ["python"],
        )
        job.wait(timeout=5.0)

        # Act
        status = indexer.get_job_status(job.job_id)
        result = indexer.get_job_result(job.job_id)

        # Assert
        assert status == JobStatus.FAILED
        assert result.error is not None

    def test_job_timeout_handling(self, indexer):
        """Test job timeout handling."""
        # Arrange
        job = indexer.start_background_job(
            Path("/path/to/large/codebase"),
            ["python"],
            timeout=1,  # 1 second timeout
        )

        # Act
        job.wait(timeout=2.0)
        status = indexer.get_job_status(job.job_id)

        # Assert
        assert status in [JobStatus.TIMEOUT, JobStatus.COMPLETED]

    def test_list_all_jobs(self, indexer):
        """Test listing all background jobs."""
        # Arrange
        job1 = indexer.start_background_job(Path("/path1"), ["python"])
        job2 = indexer.start_background_job(Path("/path2"), ["javascript"])

        # Act
        all_jobs = indexer.list_jobs()

        # Assert
        assert len(all_jobs) >= 2
        assert job1.job_id in [j.job_id for j in all_jobs]
        assert job2.job_id in [j.job_id for j in all_jobs]

    def test_cleanup_completed_jobs(self, indexer):
        """Test cleanup of completed jobs."""
        # Arrange
        job = indexer.start_background_job(Path("/path/to/codebase"), ["python"])
        job.wait(timeout=5.0)

        # Act
        indexer.cleanup_completed_jobs()
        all_jobs = indexer.list_jobs()

        # Assert
        assert job.job_id not in [j.job_id for j in all_jobs]

    def test_progress_monitoring_during_background_job(self, indexer):
        """Test progress monitoring during background job."""
        # Arrange
        job = indexer.start_background_job(Path("/path/to/codebase"), ["python"])
        time.sleep(0.5)

        # Act
        progress = indexer.get_job_progress(job.job_id)

        # Assert
        assert progress is not None
        assert hasattr(progress, "percentage")
        assert 0 <= progress.percentage <= 100

    def test_resource_cleanup_on_completion(self, indexer, tmp_path):
        """Test resource cleanup on job completion."""
        # Arrange
        job = indexer.start_background_job(Path("/path/to/codebase"), ["python"])
        log_file = job.log_file
        job.wait(timeout=5.0)

        # Act
        indexer.cleanup_completed_jobs()

        # Assert - Log files should be archived or cleaned
        assert log_file.exists()  # Should still exist for retrieval
        assert indexer.get_job_result(job.job_id) is not None

    def test_process_isolation_prevents_deadlock(self, indexer):
        """Test that process isolation prevents deadlocks."""
        # Arrange
        jobs = []

        # Act - Start multiple jobs that could potentially deadlock
        for i in range(5):
            job = indexer.start_background_job(
                Path(f"/path/to/codebase{i}"),
                ["python"],
            )
            jobs.append(job)

        time.sleep(1.0)

        # Assert - All jobs should be running or completed, none stuck
        statuses = [indexer.get_job_status(j.job_id) for j in jobs]
        assert all(s in [JobStatus.RUNNING, JobStatus.COMPLETED] for s in statuses)
