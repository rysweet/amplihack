"""Background indexing for Blarify operations.

Provides background job execution with status tracking and log management.
"""

import multiprocessing
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class JobStatus(Enum):
    """Status of a background indexing job."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class JobResult:
    """Result of an indexing job."""

    files_indexed: int
    languages_completed: list[str]
    error: str | None = None


@dataclass
class JobProgress:
    """Progress information for a job."""

    percentage: float
    current_language: str | None = None
    files_processed: int = 0


@dataclass
class IndexingJob:
    """Represents a background indexing job."""

    job_id: str
    status: JobStatus
    process: multiprocessing.Process | None
    log_file: Path
    codebase_path: Path
    languages: list[str]
    start_time: float = field(default_factory=time.time)
    result: JobResult | None = None

    def wait(self, timeout: float | None = None) -> bool:
        """Wait for job to complete.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if job completed, False if timeout
        """
        if self.process is None:
            return True

        self.process.join(timeout=timeout)

        if self.process.is_alive():
            return False

        # Update status based on exit code
        if self.process.exitcode == 0:
            self.status = JobStatus.COMPLETED
        else:
            self.status = JobStatus.FAILED

        return True


class BackgroundIndexer:
    """Manage background indexing jobs."""

    def __init__(self, log_dir: Path | None = None):
        """Initialize background indexer.

        Args:
            log_dir: Directory for log files (default: ~/.amplihack/.blarify_jobs/)
        """
        if log_dir is None:
            log_dir = Path.home() / ".amplihack" / ".blarify_jobs"

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        self._jobs: dict[str, IndexingJob] = {}
        self._completion_callbacks: list[Callable] = []

    def start_background_job(
        self,
        codebase_path: Path,
        languages: list[str],
        timeout: int | None = None,
    ) -> IndexingJob:
        """Start a background indexing job.

        Args:
            codebase_path: Path to codebase to index
            languages: Languages to index
            timeout: Optional timeout in seconds

        Returns:
            IndexingJob object
        """
        job_id = str(uuid.uuid4())
        log_file = self.log_dir / f"{job_id}.log"

        # Create log file
        log_file.touch()

        # Create worker process
        process = multiprocessing.Process(
            target=self._worker,
            args=(job_id, codebase_path, languages, log_file, timeout),
        )
        process.start()

        # Create job object
        job = IndexingJob(
            job_id=job_id,
            status=JobStatus.RUNNING,
            process=process,
            log_file=log_file,
            codebase_path=codebase_path,
            languages=languages,
        )

        self._jobs[job_id] = job

        return job

    def _worker(
        self,
        job_id: str,
        codebase_path: Path,
        languages: list[str],
        log_file: Path,
        timeout: int | None,
    ) -> None:
        """Worker function that runs in background process.

        Args:
            job_id: Job identifier
            codebase_path: Path to codebase
            languages: Languages to index
            log_file: Path to log file
            timeout: Optional timeout in seconds
        """
        # Close inherited stdio so parent process can exit cleanly
        import os as _os

        try:
            _os.close(0)  # stdin
            _os.close(1)  # stdout
            _os.close(2)  # stderr
        except OSError:
            pass

        try:
            with open(log_file, "w") as f:
                f.write(f"Starting indexing job {job_id}\n")
                f.write(f"Codebase: {codebase_path}\n")
                f.write(f"Languages: {', '.join(languages)}\n")
                f.write(f"Timeout: {timeout}s\n\n")

                # Run the actual orchestrator
                from amplihack.memory.kuzu.connector import KuzuConnector

                from .orchestrator import IndexingConfig, Orchestrator

                db_path = codebase_path / ".amplihack" / "kuzu_db"
                db_path.parent.mkdir(parents=True, exist_ok=True)

                connector = KuzuConnector(str(db_path))
                connector.connect()
                orchestrator = Orchestrator(connector=connector)

                config = IndexingConfig(max_retries=2)
                if timeout:
                    config.timeout = timeout

                f.write("Running orchestrator...\n")
                ix_result = orchestrator.run(
                    codebase_path=codebase_path,
                    languages=languages,
                    background=False,
                    config=config,
                )

                files_indexed = ix_result.total_files
                completed_languages = ix_result.completed_languages

                f.write(f"\nJob completed: success={ix_result.success}\n")
                f.write(f"Files: {ix_result.total_files}, Functions: {ix_result.total_functions}\n")
                f.write(f"Completed: {completed_languages}\n")
                if ix_result.failed_languages:
                    f.write(f"Failed: {ix_result.failed_languages}\n")

                # Store result
                result = JobResult(
                    files_indexed=files_indexed,
                    languages_completed=completed_languages,
                )
                self._store_result(job_id, result)

                # Notify completion callbacks
                for callback in self._completion_callbacks:
                    callback(job_id, result)

        except Exception as e:
            with open(log_file, "a") as f:
                f.write(f"\nError: {e}\n")

            result = JobResult(
                files_indexed=0,
                languages_completed=[],
                error=str(e),
            )
            self._store_result(job_id, result)

    def _store_result(self, job_id: str, result: JobResult) -> None:
        """Store job result.

        Args:
            job_id: Job identifier
            result: Job result
        """
        result_file = self.log_dir / f"{job_id}.result"
        with open(result_file, "w") as f:
            f.write(f"files_indexed: {result.files_indexed}\n")
            f.write(f"languages_completed: {','.join(result.languages_completed)}\n")
            if result.error:
                f.write(f"error: {result.error}\n")

    def get_job_status(self, job_id: str) -> JobStatus:
        """Get current status of a job.

        Args:
            job_id: Job identifier

        Returns:
            JobStatus
        """
        if job_id not in self._jobs:
            raise ValueError(f"Unknown job ID: {job_id}")

        job = self._jobs[job_id]

        # Check if process is still running
        if job.process and job.process.is_alive():
            return JobStatus.RUNNING

        # Check result file for completion status
        result = self._load_result(job_id)
        if result:
            if result.error:
                job.status = JobStatus.FAILED
            else:
                job.status = JobStatus.COMPLETED
            job.result = result

        return job.status

    def _load_result(self, job_id: str) -> JobResult | None:
        """Load job result from file.

        Args:
            job_id: Job identifier

        Returns:
            JobResult or None
        """
        result_file = self.log_dir / f"{job_id}.result"
        if not result_file.exists():
            return None

        files_indexed = 0
        languages = []
        error = None

        with open(result_file) as f:
            for line in f:
                if line.startswith("files_indexed:"):
                    files_indexed = int(line.split(":")[1].strip())
                elif line.startswith("languages_completed:"):
                    lang_str = line.split(":")[1].strip()
                    if lang_str:
                        languages = lang_str.split(",")
                elif line.startswith("error:"):
                    error = line.split(":", 1)[1].strip()

        return JobResult(
            files_indexed=files_indexed,
            languages_completed=languages,
            error=error,
        )

    def cancel_job(self, job_id: str) -> None:
        """Cancel a running job.

        Args:
            job_id: Job identifier
        """
        if job_id not in self._jobs:
            raise ValueError(f"Unknown job ID: {job_id}")

        job = self._jobs[job_id]
        if job.process and job.process.is_alive():
            job.process.terminate()
            job.process.join(timeout=5.0)
            if job.process.is_alive():
                job.process.kill()

        job.status = JobStatus.CANCELLED

    def stream_logs(self, job_id: str, max_lines: int = 100) -> list[str]:
        """Stream log output from a job.

        Args:
            job_id: Job identifier
            max_lines: Maximum number of lines to return

        Returns:
            List of log lines
        """
        if job_id not in self._jobs:
            raise ValueError(f"Unknown job ID: {job_id}")

        job = self._jobs[job_id]
        if not job.log_file.exists():
            return []

        with open(job.log_file) as f:
            lines = f.readlines()

        return lines[-max_lines:]

    def get_job_result(self, job_id: str) -> JobResult | None:
        """Get result of a completed job.

        Args:
            job_id: Job identifier

        Returns:
            JobResult or None
        """
        if job_id not in self._jobs:
            raise ValueError(f"Unknown job ID: {job_id}")

        job = self._jobs[job_id]
        if job.result:
            return job.result

        return self._load_result(job_id)

    def list_jobs(self) -> list[IndexingJob]:
        """List all jobs.

        Returns:
            List of IndexingJob objects
        """
        return list(self._jobs.values())

    def cleanup_completed_jobs(self, keep_results: bool = True) -> None:
        """Clean up completed jobs from memory.

        Args:
            keep_results: If True, keep result files for retrieval
        """
        completed = []
        for job_id, job in list(self._jobs.items()):
            # Update status first
            status = self.get_job_status(job_id)
            if status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                completed.append(job_id)

        for job_id in completed:
            if job_id in self._jobs:
                del self._jobs[job_id]

    def get_job_progress(self, job_id: str) -> JobProgress | None:
        """Get current progress of a job.

        Args:
            job_id: Job identifier

        Returns:
            JobProgress or None
        """
        if job_id not in self._jobs:
            return None

        job = self._jobs[job_id]

        # Parse progress from log file
        if not job.log_file.exists():
            return JobProgress(percentage=0.0)

        files_processed = 0
        current_language = None

        with open(job.log_file) as f:
            for line in f:
                if "Indexing" in line and "..." in line:
                    # Extract language being processed
                    current_language = line.split("Indexing")[1].split("...")[0].strip()
                elif "files" in line.lower() and ":" in line:
                    # Extract file count
                    try:
                        files_processed = int(line.split(":")[-1].strip().split()[0])
                    except (ValueError, IndexError):
                        pass

        # Estimate percentage based on languages completed
        total_languages = len(job.languages)
        completed_languages = sum(1 for lang in job.languages if lang in str(current_language))
        percentage = (completed_languages / total_languages) * 100.0 if total_languages > 0 else 0.0

        return JobProgress(
            percentage=percentage,
            current_language=current_language,
            files_processed=files_processed,
        )

    def register_completion_callback(self, callback: Callable) -> None:
        """Register callback for job completion.

        Args:
            callback: Function to call when job completes
        """
        self._completion_callbacks.append(callback)
