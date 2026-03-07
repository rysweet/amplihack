"""Progress tracking, state management, and I/O for power-steering.

Owns semaphore files, redirect records, log writing, and compaction integration.
"""

import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .considerations import CheckerResult, PowerSteeringRedirect, PowerSteeringResult

logger = logging.getLogger(__name__)

# Retry configuration for cloud-sync resilient file writes
MAX_WRITE_RETRIES = 3
WRITE_RETRY_INITIAL_DELAY = 0.1  # seconds; doubles on each retry

# REQ-SEC-3: Per-line size limit for transcript parsing (10 MB)
# Prevents memory exhaustion from pathological oversized JSON lines
MAX_LINE_BYTES = 10 * 1024 * 1024

# REQ-SEC-1: Session ID validation pattern
# Allows alphanumeric, hyphens, underscores — rejects path traversal characters
_SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")


def _validate_session_id(session_id: str) -> bool:
    """Validate session ID to prevent path traversal attacks.

    REQ-SEC-1: Session IDs are interpolated into Path objects. Without
    validation, a crafted session_id like '../../etc/passwd' could read
    or write arbitrary files.

    Args:
        session_id: Session identifier to validate

    Returns:
        True if session_id matches the allowed pattern, False otherwise.
        Never raises — callers must treat False as a safe skip.
    """
    return bool(_SESSION_ID_PATTERN.match(session_id))


# Timeout for gh/git subprocess calls used in state verification
GH_PR_SUBPROCESS_TIMEOUT = 10

# Try to import compaction validator
try:
    from compaction_validator import (  # type: ignore[import-not-found]
        CompactionContext,
        CompactionValidator,
    )

    COMPACTION_AVAILABLE = True
except ImportError:
    COMPACTION_AVAILABLE = False

    # Create placeholder type for when module is unavailable
    class CompactionContext:  # type: ignore[no-redef]
        def __init__(self) -> None:
            self.has_compaction_event = False


def _write_with_retry(
    filepath: Path, data: str, mode: str = "w", max_retries: int = MAX_WRITE_RETRIES
) -> None:
    """Write file with exponential backoff for cloud sync resilience.

    Handles transient file I/O errors that can occur with cloud-synced directories
    (iCloud, OneDrive, Dropbox, etc.) by retrying with exponential backoff.

    Args:
        filepath: Path to file to write
        data: Content to write
        mode: File mode ('w' for write, 'a' for append)
        max_retries: Maximum retry attempts (default: MAX_WRITE_RETRIES)

    Raises:
        OSError: If all retries exhausted (fail-open: caller should handle)
    """
    retry_delay = WRITE_RETRY_INITIAL_DELAY

    for attempt in range(max_retries):
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            if mode == "w":
                filepath.write_text(data, encoding="utf-8")
            else:  # append mode
                with open(filepath, mode, encoding="utf-8") as f:
                    f.write(data)
            return  # Success!
        except OSError as e:
            if e.errno == 5 and attempt < max_retries - 1:  # Input/output error
                if attempt == 0:
                    # Only warn on first retry
                    sys.stderr.write(
                        "[Power Steering] File I/O error, retrying (may be cloud sync issue)\n"
                    )
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                raise  # Give up after max retries or non-transient error


class ProgressTrackingMixin:
    """Mixin for filesystem state, semaphore files, redirect records, and logging.

    All methods access self.runtime_dir, self.project_root, self.considerations
    etc. inherited from PowerSteeringChecker.
    """

    def _already_ran(self, session_id: str) -> bool:
        """Check if power-steering already ran for this session.

        Args:
            session_id: Session identifier

        Returns:
            True if already ran, False otherwise
        """
        if not _validate_session_id(session_id):
            self._log(f"Invalid session_id rejected in _already_ran: {session_id!r}", "WARNING")
            return False
        semaphore = self.runtime_dir / f".{session_id}_completed"
        return semaphore.exists()

    def _get_pre_compaction_transcript(self, session_id: str) -> Path | None:
        """Check if session was compacted and return pre-compaction transcript path.

        When Claude Code compacts a session, the transcript_path provided to hooks
        only contains the compacted summary (~50 messages). The pre_compact.py hook
        saves the FULL transcript before compaction. This method finds that saved
        transcript to ensure power-steering analyzes complete session history.

        Args:
            session_id: Session identifier

        Returns:
            Path to pre-compaction transcript if available, None otherwise

        Note:
            See Issue #1962: After compaction, power-steering only saw ~50 messages
            instead of 767+ causing false "work incomplete" blocks.
        """
        try:
            # Check for compaction events in session logs
            logs_dir = self.project_root / ".claude" / "runtime" / "logs"
            session_dir = logs_dir / session_id

            if not session_dir.exists():
                return None

            # Check if compaction events exist
            compaction_file = session_dir / "compaction_events.json"
            if not compaction_file.exists():
                return None

            # Parse compaction events to get transcript path
            try:
                with open(compaction_file) as f:
                    compaction_events = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                self._log(f"Failed to read compaction events: {e}", "WARNING")
                return None

            if not compaction_events:
                return None

            # Get the most recent compaction event's transcript
            # Events are appended chronologically, so last is most recent
            latest_event = compaction_events[-1]
            saved_transcript_path = latest_event.get("transcript_path")

            # REQ-SEC-4: Validate that saved_transcript_path is a non-empty string.
            # A malicious compaction_events.json could supply a non-string value
            # (e.g. a dict or list) that would bypass downstream path validation.
            if not isinstance(saved_transcript_path, str) or not saved_transcript_path:
                saved_transcript_path = None

            if not saved_transcript_path:
                # Fallback: Look for standard transcript file locations
                possible_paths = [
                    session_dir / "CONVERSATION_TRANSCRIPT.md",
                    session_dir / "conversation_transcript.jsonl",
                ]

                # Check transcripts subdirectory for timestamped copies
                transcripts_dir = session_dir / "transcripts"
                if transcripts_dir.exists():
                    transcript_files = sorted(
                        transcripts_dir.glob("conversation_*.md"), reverse=True
                    )
                    if transcript_files:
                        possible_paths.insert(0, transcript_files[0])

                for path in possible_paths:
                    if path.exists():
                        saved_transcript_path = str(path)
                        break

            if not saved_transcript_path:
                self._log("Compaction detected but no transcript path found", "WARNING")
                return None

            transcript_path = Path(saved_transcript_path)

            # Security: Validate path is within project
            if not self._validate_path(transcript_path, self.project_root):
                self._log(
                    f"Pre-compaction transcript path outside project: {transcript_path}",
                    "WARNING",
                )
                return None

            if transcript_path.exists():
                messages_count = latest_event.get("messages_exported", "unknown")
                self._log(
                    f"Using pre-compaction transcript ({messages_count} messages): {transcript_path}",
                    "INFO",
                )
                return transcript_path

            self._log(f"Pre-compaction transcript not found: {transcript_path}", "WARNING")
            return None

        except Exception as e:
            # Fail-open: If we can't check for pre-compaction, continue with provided transcript
            self._log(f"Pre-compaction transcript check failed: {e}", "WARNING", exc_info=True)
            return None

    def _load_pre_compaction_transcript(self, transcript_path: Path) -> list[dict]:
        """Load pre-compaction transcript from markdown or JSONL format.

        The pre_compact.py hook saves transcripts in markdown format (CONVERSATION_TRANSCRIPT.md).
        This method parses that format to extract message data for analysis.

        Args:
            transcript_path: Path to pre-compaction transcript file

        Returns:
            List of message dictionaries

        Note:
            Handles both markdown format from pre_compact.py and JSONL format.
        """
        messages = []

        try:
            content = transcript_path.read_text()

            # Detect format by extension and content
            if transcript_path.suffix == ".jsonl" or content.strip().startswith("{"):
                # JSONL format - parse line by line
                for line in content.strip().split("\n"):
                    if line.strip():
                        # REQ-SEC-3: Skip oversized lines to prevent memory exhaustion
                        if len(line.encode("utf-8")) > MAX_LINE_BYTES:
                            self._log(
                                f"Skipping oversized transcript line ({len(line)} chars, "
                                f"limit {MAX_LINE_BYTES} bytes)",
                                "WARNING",
                            )
                            continue
                        try:
                            messages.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            else:
                # Markdown format from context_preservation.py
                # Parse conversation entries marked with roles
                current_role = None
                current_content = []

                for line in content.split("\n"):
                    # Detect role headers like "## User" or "## Assistant" or "**User:**"
                    role_match = None
                    if (
                        line.startswith("## User")
                        or "**User:**" in line
                        or line.startswith("### User")
                    ):
                        role_match = "user"
                    elif (
                        line.startswith("## Assistant")
                        or "**Assistant:**" in line
                        or line.startswith("### Assistant")
                    ):
                        role_match = "assistant"

                    if role_match:
                        # Save previous message if exists
                        if current_role and current_content:
                            messages.append(
                                {
                                    "role": current_role,
                                    "content": "\n".join(current_content).strip(),
                                }
                            )
                        current_role = role_match
                        current_content = []
                    elif current_role:
                        current_content.append(line)

                # Don't forget the last message
                if current_role and current_content:
                    messages.append(
                        {"role": current_role, "content": "\n".join(current_content).strip()}
                    )

            self._log(f"Loaded {len(messages)} messages from pre-compaction transcript", "INFO")
            return messages

        except Exception as e:
            self._log(f"Failed to load pre-compaction transcript: {e}", "WARNING", exc_info=True)
            return []

    def _results_already_shown(self, session_id: str) -> bool:
        """Check if power-steering results were already shown for this session.

        Used for the "always block first" visibility feature. On first stop,
        we always block to show results. On subsequent stops, we only block
        if there are actual failures.

        Args:
            session_id: Session identifier

        Returns:
            True if results were already shown, False otherwise
        """
        if not _validate_session_id(session_id):
            self._log(
                f"Invalid session_id rejected in _results_already_shown: {session_id!r}", "WARNING"
            )
            return False
        semaphore = self.runtime_dir / f".{session_id}_results_shown"
        return semaphore.exists()

    def _mark_results_shown(self, session_id: str) -> None:
        """Create semaphore to indicate results have been shown.

        Called after displaying all consideration results on first stop.
        Uses atomic O_CREAT|O_EXCL|O_WRONLY with 0o600 mode to prevent
        the TOCTOU window between creation and chmod (REQ-SEC-6).

        Args:
            session_id: Session identifier
        """
        if not _validate_session_id(session_id):
            self._log(
                f"Invalid session_id rejected in _mark_results_shown: {session_id!r}", "WARNING"
            )
            return
        try:
            semaphore = self.runtime_dir / f".{session_id}_results_shown"
            semaphore.parent.mkdir(parents=True, exist_ok=True)
            # REQ-SEC-6: Atomic create with restrictive permissions — no TOCTOU window
            fd = os.open(str(semaphore), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        except FileExistsError:
            pass  # Suppressed — concurrent process already created the semaphore
        except OSError as e:
            # REQ-SEC-5: Log instead of silently swallowing I/O failures
            self._log(f"Failed to create results_shown semaphore: {e}", "WARNING")

    def _mark_complete(self, session_id: str) -> None:
        """Create semaphore to prevent re-running.

        Uses atomic O_CREAT|O_EXCL|O_WRONLY with 0o600 mode to prevent
        the TOCTOU window between creation and chmod (REQ-SEC-6).

        Args:
            session_id: Session identifier
        """
        if not _validate_session_id(session_id):
            self._log(f"Invalid session_id rejected in _mark_complete: {session_id!r}", "WARNING")
            return
        try:
            semaphore = self.runtime_dir / f".{session_id}_completed"
            semaphore.parent.mkdir(parents=True, exist_ok=True)
            # REQ-SEC-6: Atomic create with restrictive permissions — no TOCTOU window
            fd = os.open(str(semaphore), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        except FileExistsError:
            pass  # Suppressed — concurrent process already created the semaphore
        except OSError as e:
            # REQ-SEC-5: Log instead of silently swallowing I/O failures
            self._log(f"Failed to create completed semaphore: {e}", "WARNING")

    def _get_redirect_file(self, session_id: str) -> Path:
        """Get path to redirects file for a session.

        Args:
            session_id: Session identifier

        Returns:
            Path to redirects.jsonl file
        """
        if not _validate_session_id(session_id):
            self._log(
                f"Invalid session_id rejected in _get_redirect_file: {session_id!r}", "WARNING"
            )
            # Return a safe path that won't exist — callers check existence before reading
            return self.runtime_dir / "invalid_session" / "redirects.jsonl"
        session_dir = self.runtime_dir / session_id
        return session_dir / "redirects.jsonl"

    def _load_redirects(self, session_id: str) -> list[PowerSteeringRedirect]:
        """Load redirect history for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of PowerSteeringRedirect objects (empty if none exist)
        """
        redirects_file = self._get_redirect_file(session_id)

        if not redirects_file.exists():
            return []

        redirects = []
        try:
            with open(redirects_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        redirect = PowerSteeringRedirect(
                            redirect_number=data["redirect_number"],
                            timestamp=data["timestamp"],
                            failed_considerations=data["failed_considerations"],
                            continuation_prompt=data["continuation_prompt"],
                            work_summary=data.get("work_summary"),
                        )
                        redirects.append(redirect)
                    except (json.JSONDecodeError, KeyError) as e:
                        self._log(f"Skipping malformed redirect entry: {e}", "WARNING")
                        continue
        except OSError as e:
            self._log(f"Error loading redirects: {e}", "WARNING")
            return []

        return redirects

    def _save_redirect(
        self,
        session_id: str,
        failed_considerations: list[str],
        continuation_prompt: str,
        work_summary: str | None = None,
    ) -> None:
        """Save a redirect record to persistent storage.

        Args:
            session_id: Session identifier
            failed_considerations: List of failed consideration IDs
            continuation_prompt: The prompt shown to user
            work_summary: Optional summary of work done so far
        """
        try:
            # Load existing redirects to get next number
            existing = self._load_redirects(session_id)
            redirect_number = len(existing) + 1

            # Create redirect record
            redirect = PowerSteeringRedirect(
                redirect_number=redirect_number,
                timestamp=datetime.now().isoformat(),
                failed_considerations=failed_considerations,
                continuation_prompt=continuation_prompt,
                work_summary=work_summary,
            )

            # Save to JSONL file (append-only)
            redirects_file = self._get_redirect_file(session_id)
            redirects_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert to dict for JSON serialization
            redirect_dict = {
                "redirect_number": redirect.redirect_number,
                "timestamp": redirect.timestamp,
                "failed_considerations": redirect.failed_considerations,
                "continuation_prompt": redirect.continuation_prompt,
                "work_summary": redirect.work_summary,
            }

            with open(redirects_file, "a") as f:
                f.write(json.dumps(redirect_dict) + "\n")

            # Set permissions on new file
            if redirect_number == 1:
                redirects_file.chmod(0o600)  # Owner read/write only for security

            self._log(f"Saved redirect #{redirect_number} for session {session_id}", "INFO")

        except OSError as e:
            # Fail-open: Don't block user if we can't save redirect
            self._log(f"Failed to save redirect: {e}", "ERROR", exc_info=True)

    def _emit_progress(
        self,
        progress_callback: Any | None,
        event_type: str,
        message: str,
        details: dict | None = None,
    ) -> None:
        """Emit progress event to callback if provided.

        Fail-safe design: Never raises exceptions that would break checker.

        Args:
            progress_callback: Optional callback function
            event_type: Event type (start/category/consideration/complete)
            message: Progress message
            details: Optional event details
        """
        if progress_callback is None:
            return

        try:
            progress_callback(event_type, message, details)
        except Exception as e:
            # Fail-safe: Log but never raise
            self._log(f"Progress callback error: {e}", "WARNING", exc_info=True)

    def _write_summary(self, session_id: str, summary: str) -> None:
        """Write summary to file.

        Args:
            session_id: Session identifier
            summary: Summary content
        """
        if not _validate_session_id(session_id):
            self._log(f"Invalid session_id rejected in _write_summary: {session_id!r}", "WARNING")
            return
        try:
            summary_dir = self.runtime_dir / session_id
            summary_path = summary_dir / "summary.md"
            _write_with_retry(summary_path, summary, mode="w")
            summary_path.chmod(0o644)  # Owner read/write, others read
        except OSError as e:
            # REQ-SEC-5: Log instead of silently swallowing I/O failures
            self._log(f"Failed to write summary: {e}", "WARNING")

    def _is_consideration_enabled(self, consideration_id: str) -> bool:
        """Check if a consideration is enabled in considerations.yaml.

        Args:
            consideration_id: ID of consideration to check

        Returns:
            True if enabled or not found (default enabled), False if explicitly disabled
        """
        try:
            considerations_path = (
                self.project_root / ".claude" / "tools" / "amplihack" / "considerations.yaml"
            )
            if not considerations_path.exists():
                return True  # Default enabled

            import yaml

            with open(considerations_path) as f:
                considerations = yaml.safe_load(f)

            if not considerations:
                return True

            for consideration in considerations:
                if consideration.get("id") == consideration_id:
                    return consideration.get("enabled", True)

            return True  # Not found = default enabled
        except Exception as e:
            self._log(
                f"Could not check consideration enabled state, defaulting to enabled: {e}",
                "WARNING",
                exc_info=True,
            )
            return True  # Fail-open

    def _check_with_transcript_list(
        self, transcript: list[dict], session_id: str
    ) -> PowerSteeringResult:
        """Testing interface: Check with transcript list instead of file path.

        Args:
            transcript: Transcript as list of message dicts
            session_id: Session identifier

        Returns:
            PowerSteeringResult with compaction context and considerations
        """
        # Initialize compaction context
        compaction_context = CompactionContext()

        # Check if compaction handling is enabled
        compaction_enabled = self._is_consideration_enabled("compaction_handling")

        # Run compaction validation
        considerations = []
        if COMPACTION_AVAILABLE and compaction_enabled:
            try:
                validator = CompactionValidator(self.project_root)
                validation_result = validator.validate(transcript, session_id)
                compaction_context = validation_result.compaction_context

                # Create consideration result
                compaction_check = CheckerResult(
                    consideration_id="compaction_handling",
                    satisfied=validation_result.passed,
                    reason="; ".join(validation_result.warnings)
                    if validation_result.warnings
                    else "No compaction issues detected",
                    severity="warning",
                    recovery_steps=validation_result.recovery_steps,
                    executed=True,
                )

                considerations.append(compaction_check)
            except Exception as e:
                # Fail-open: Log error but don't block
                self._log(f"Compaction validation error: {e}", "WARNING", exc_info=True)
                compaction_check = CheckerResult(
                    consideration_id="compaction_handling",
                    satisfied=True,  # Fail-open
                    reason="Compaction validation skipped due to error",
                    severity="warning",
                    executed=True,
                )
                considerations.append(compaction_check)
        elif not compaction_enabled:
            # Add disabled marker
            compaction_check = CheckerResult(
                consideration_id="compaction_handling",
                satisfied=True,
                reason="Compaction handling disabled",
                severity="warning",
                executed=False,
            )
            considerations.append(compaction_check)

        # Return result
        return PowerSteeringResult(
            decision="approve",
            reasons=["test_mode"],
            compaction_context=compaction_context,
            considerations=considerations,
        )

    def _check_compaction_handling(self, transcript: list[dict], session_id: str) -> bool:
        """Consideration checker for compaction validation.

        Called by consideration framework. Returns True if compaction
        was handled appropriately or didn't occur.

        Args:
            transcript: Full conversation transcript
            session_id: Session identifier

        Returns:
            True if no compaction or validation passed, False if failed
        """
        if not COMPACTION_AVAILABLE:
            return True  # Fail-open if validator not available

        try:
            validator = CompactionValidator(self.project_root)
            result = validator.validate(transcript, session_id)
            return result.passed
        except Exception as e:
            self._log(f"Compaction validation error: {e}", "WARNING", exc_info=True)
            return True  # Fail-open on errors

    def _log(self, message: str, level: str = "INFO", exc_info: bool = False) -> None:
        """Log message to power-steering log file.

        Args:
            message: Message to log
            level: Log level (INFO, WARNING, ERROR, DEBUG)
            exc_info: If True, log exception info (stack trace)
        """
        try:
            log_file = self.runtime_dir / "power_steering.log"
            timestamp = datetime.now().isoformat()

            # Create with restrictive permissions if it doesn't exist
            is_new = not log_file.exists()

            # Use retry-enabled write for cloud sync resilience
            log_entry = f"[{timestamp}] {level}: {message}\n"
            _write_with_retry(log_file, log_entry, mode="a")

            # Set permissions on new files
            if is_new:
                log_file.chmod(0o600)  # Owner read/write only for security
        except OSError as e:
            # REQ-SEC-5: Use stdlib logger directly (avoid recursion into self._log)
            logger.warning("Power-steering log write failed: %s", e)

        # If exc_info requested, also log to stdlib logger (for stack traces)
        if exc_info:
            level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "ERROR": logging.ERROR,
            }
            level_int = level_map.get(level, logging.WARNING)
            logger.log(level_int, message, exc_info=True)
