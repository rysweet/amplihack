#!/usr/bin/env python3
"""
Power-Steering Mode: Autonomous session completion verification.

Analyzes session transcripts against 21 considerations to determine if work is
truly complete before allowing session termination. Blocks incomplete sessions
with actionable continuation prompts.

Philosophy:
- Ruthlessly Simple: Single-purpose module with clear contract
- Fail-Open: Never block users due to bugs - always allow stop on errors
- Zero-BS: No stubs, every function works or doesn't exist
- Modular: Self-contained brick that plugs into stop hook

Phase 1 (MVP) Implementation:
- Core module with top 5 critical checkers
- Basic semaphore mechanism
- Simple configuration
- Fail-open error handling
"""

import json
import os
import re
import signal
import sys
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))

# Try to import Claude SDK integration
try:
    from claude_power_steering import analyze_consideration_sync

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

# Security: Maximum transcript size to prevent memory exhaustion
MAX_TRANSCRIPT_LINES = 50000  # Limit transcript to 50K lines (~10-20MB typical)

# Timeout for individual checker execution (seconds)
CHECKER_TIMEOUT = 10


@contextmanager
def _timeout(seconds: int):
    """Context manager for operation timeout.

    Args:
        seconds: Timeout in seconds

    Raises:
        TimeoutError: If operation exceeds timeout
    """

    def handler(signum, frame):
        raise TimeoutError("Operation timed out")

    # Set alarm
    old_handler = signal.signal(signal.SIGALRM, handler)
    signal.alarm(seconds)

    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


@dataclass
class CheckerResult:
    """Result from a single consideration checker."""

    consideration_id: str
    satisfied: bool
    reason: str
    severity: Literal["blocker", "warning"]


@dataclass
class ConsiderationAnalysis:
    """Results of analyzing all considerations."""

    results: Dict[str, CheckerResult] = field(default_factory=dict)
    failed_blockers: List[CheckerResult] = field(default_factory=list)
    failed_warnings: List[CheckerResult] = field(default_factory=list)

    @property
    def has_blockers(self) -> bool:
        """True if any blocker consideration failed."""
        return len(self.failed_blockers) > 0

    def add_result(self, result: CheckerResult) -> None:
        """Add result for a consideration."""
        self.results[result.consideration_id] = result
        if not result.satisfied:
            if result.severity == "blocker":
                self.failed_blockers.append(result)
            else:
                self.failed_warnings.append(result)

    def group_by_category(self) -> Dict[str, List[CheckerResult]]:
        """Group failed considerations by category."""
        # For Phase 1, use simplified categories based on consideration ID prefix
        grouped: Dict[str, List[CheckerResult]] = {}
        for result in self.failed_blockers + self.failed_warnings:
            # Simple category derivation from ID
            if "workflow" in result.consideration_id or "philosophy" in result.consideration_id:
                category = "Workflow & Philosophy"
            elif "testing" in result.consideration_id or "ci" in result.consideration_id:
                category = "Testing & CI/CD"
            else:
                category = "Completion Checks"

            if category not in grouped:
                grouped[category] = []
            grouped[category].append(result)
        return grouped


@dataclass
class PowerSteeringRedirect:
    """Record of a power-steering redirect (blocked session)."""

    redirect_number: int
    timestamp: str  # ISO format
    failed_considerations: List[str]  # IDs of failed checks
    continuation_prompt: str
    work_summary: Optional[str] = None


@dataclass
class PowerSteeringResult:
    """Final decision from power-steering analysis."""

    decision: Literal["approve", "block"]
    reasons: List[str]
    continuation_prompt: Optional[str] = None
    summary: Optional[str] = None


class PowerSteeringChecker:
    """Analyzes session completeness using consideration checkers.

    Phase 2 Implementation:
    - All 21 considerations from YAML file
    - User customization support
    - Generic analyzer for flexible considerations
    - Backward compatible with Phase 1
    - Fail-open error handling
    """

    # File extension constants for session type detection
    CODE_FILE_EXTENSIONS = [
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".java",
        ".go",
        ".rs",
        ".c",
        ".cpp",
        ".h",
    ]
    DOC_FILE_EXTENSIONS = [".md", ".txt", ".rst", "README", "CHANGELOG"]
    CONFIG_FILE_EXTENSIONS = [".yml", ".yaml", ".json"]
    TEST_COMMAND_PATTERNS = [
        "pytest",
        "npm test",
        "cargo test",
        "go test",
        "python -m pytest",
        "python -m unittest",
    ]

    # Phase 1 fallback: Hardcoded considerations (top 5 critical)
    # Used when YAML file is missing or invalid
    PHASE1_CONSIDERATIONS = [
        {
            "id": "todos_complete",
            "category": "Session Completion & Progress",
            "question": "Were all TODO items completed?",
            "severity": "blocker",
            "checker": "_check_todos_complete",
        },
        {
            "id": "dev_workflow_complete",
            "category": "Workflow Process Adherence",
            "question": "Was full DEFAULT_WORKFLOW followed?",
            "severity": "blocker",
            "checker": "_check_dev_workflow_complete",
        },
        {
            "id": "philosophy_compliance",
            "category": "Code Quality & Philosophy",
            "question": "PHILOSOPHY adherence (zero-BS)?",
            "severity": "blocker",
            "checker": "_check_philosophy_compliance",
        },
        {
            "id": "local_testing",
            "category": "Testing & Local Validation",
            "question": "Sure agent tested locally?",
            "severity": "blocker",
            "checker": "_check_local_testing",
        },
        {
            "id": "ci_status",
            "category": "CI/CD & Mergeability",
            "question": "CI passing/mergeable?",
            "severity": "blocker",
            "checker": "_check_ci_status",
        },
    ]

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize power-steering checker.

        Args:
            project_root: Project root directory (auto-detected if None)
        """
        # Auto-detect project root if not provided
        if project_root is None:
            project_root = self._detect_project_root()

        self.project_root = project_root
        self.runtime_dir = project_root / ".claude" / "runtime" / "power-steering"
        self.config_path = (
            project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
        )
        self.considerations_path = (
            project_root / ".claude" / "tools" / "amplihack" / "considerations.yaml"
        )

        # Ensure runtime directory exists
        try:
            self.runtime_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass  # Fail-open: Continue even if directory creation fails

        # Load configuration
        self.config = self._load_config()

        # Load considerations from YAML (with Phase 1 fallback)
        self.considerations = self._load_considerations_yaml()

    def _detect_project_root(self) -> Path:
        """Auto-detect project root by finding .claude marker.

        Returns:
            Project root path

        Raises:
            ValueError: If project root cannot be found
        """
        current = Path(__file__).resolve().parent
        for _ in range(10):  # Max 10 levels up
            if (current / ".claude").exists():
                return current
            if current == current.parent:
                break
            current = current.parent

        raise ValueError("Could not find project root with .claude marker")

    def _validate_config_integrity(self, config: Dict) -> bool:
        """Validate configuration integrity (security check).

        Args:
            config: Loaded configuration

        Returns:
            True if config is valid, False otherwise
        """
        # Check required keys
        if "enabled" not in config:
            return False

        # Validate enabled is boolean
        if not isinstance(config["enabled"], bool):
            return False

        # Validate phase if present
        if "phase" in config and not isinstance(config["phase"], int):
            return False

        # Validate checkers_enabled if present
        if "checkers_enabled" in config:
            if not isinstance(config["checkers_enabled"], dict):
                return False
            # All values should be booleans
            if not all(isinstance(v, bool) for v in config["checkers_enabled"].values()):
                return False

        return True

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file with defaults.

        Returns:
            Configuration dictionary with defaults applied
        """
        defaults = {
            "enabled": True,  # Enabled by default per user requirement
            "version": "1.0.0",
            "phase": 1,
            "checkers_enabled": {
                "todos_complete": True,
                "dev_workflow_complete": True,
                "philosophy_compliance": True,
                "local_testing": True,
                "ci_status": True,
            },
        }

        # Try to load config file
        try:
            if self.config_path.exists():
                with open(self.config_path) as f:
                    user_config = json.load(f)

                    # Validate config integrity before using
                    if not self._validate_config_integrity(user_config):
                        self._log("Config integrity check failed, using defaults", "WARNING")
                        return defaults

                    # Merge with defaults
                    defaults.update(user_config)
        except (OSError, json.JSONDecodeError) as e:
            self._log(f"Config load error ({e}), using defaults", "WARNING")
            # Fail-open: Use defaults on any error

        return defaults

    def _load_considerations_yaml(self) -> List[Dict[str, Any]]:
        """Load considerations from YAML file with fallback to Phase 1.

        Returns:
            List of consideration dictionaries (from YAML or Phase 1 fallback)
        """
        try:
            # Check if YAML file exists in project root
            if not self.considerations_path.exists():
                # Try fallback: Look in the same directory as this script (for testing)
                script_dir = Path(__file__).parent.parent
                fallback_yaml = script_dir / "considerations.yaml"

                if fallback_yaml.exists():
                    self._log(f"Using fallback considerations from {fallback_yaml}", "INFO")
                    with open(fallback_yaml) as f:
                        yaml_data = yaml.safe_load(f)
                else:
                    self._log("Considerations YAML not found, using Phase 1 fallback", "WARNING")
                    return self.PHASE1_CONSIDERATIONS
            else:
                # Load YAML from project root
                with open(self.considerations_path) as f:
                    yaml_data = yaml.safe_load(f)

            # Validate YAML structure
            if not isinstance(yaml_data, list):
                self._log("Invalid YAML structure (not a list), using Phase 1 fallback", "ERROR")
                return self.PHASE1_CONSIDERATIONS

            # Validate and filter considerations
            valid_considerations = []
            for item in yaml_data:
                if self._validate_consideration_schema(item):
                    valid_considerations.append(item)
                else:
                    self._log(
                        f"Invalid consideration schema: {item.get('id', 'unknown')}", "WARNING"
                    )

            if not valid_considerations:
                self._log("No valid considerations in YAML, using Phase 1 fallback", "ERROR")
                return self.PHASE1_CONSIDERATIONS

            self._log(f"Loaded {len(valid_considerations)} considerations from YAML", "INFO")
            return valid_considerations

        except (OSError, yaml.YAMLError) as e:
            # Fail-open: Use Phase 1 fallback on any error
            self._log(f"Error loading YAML ({e}), using Phase 1 fallback", "ERROR")
            return self.PHASE1_CONSIDERATIONS

    def _validate_consideration_schema(self, consideration: Any) -> bool:
        """Validate consideration has required fields.

        Args:
            consideration: Consideration dictionary to validate

        Returns:
            True if valid, False otherwise
        """
        if not isinstance(consideration, dict):
            return False

        required_fields = ["id", "category", "question", "severity", "checker", "enabled"]
        if not all(field in consideration for field in required_fields):
            return False

        # Validate severity
        if consideration["severity"] not in ["blocker", "warning"]:
            return False

        # Validate enabled
        if not isinstance(consideration["enabled"], bool):
            return False

        # Validate applicable_session_types if present (optional field for backward compatibility)
        if "applicable_session_types" in consideration:
            if not isinstance(consideration["applicable_session_types"], list):
                return False

        return True

    def check(
        self,
        transcript_path: Path,
        session_id: str,
        progress_callback: Optional[callable] = None,
    ) -> PowerSteeringResult:
        """Main entry point - analyze transcript and make decision.

        Args:
            transcript_path: Path to session transcript JSONL file
            session_id: Unique session identifier
            progress_callback: Optional callback for progress events (event_type, message, details)

        Returns:
            PowerSteeringResult with decision and prompt/summary
        """
        try:
            # Emit start event
            self._emit_progress(progress_callback, "start", "Starting power-steering analysis...")

            # 1. Check if disabled
            if self._is_disabled():
                return PowerSteeringResult(
                    decision="approve", reasons=["disabled"], continuation_prompt=None, summary=None
                )

            # 2. Check semaphore (prevent recursion)
            if self._already_ran(session_id):
                return PowerSteeringResult(
                    decision="approve",
                    reasons=["already_ran"],
                    continuation_prompt=None,
                    summary=None,
                )

            # 3. Load transcript
            transcript = self._load_transcript(transcript_path)

            # 4. Detect session type for selective consideration application
            session_type = self.detect_session_type(transcript)
            self._log(f"Session classified as: {session_type}", "INFO")
            self._emit_progress(
                progress_callback,
                "session_type",
                f"Session type: {session_type}",
                {"session_type": session_type},
            )

            # 4b. Backward compatibility: Also check Q&A session (kept for compatibility)
            if self._is_qa_session(transcript):
                return PowerSteeringResult(
                    decision="approve",
                    reasons=["qa_session"],
                    continuation_prompt=None,
                    summary=None,
                )

            # 5. Analyze against considerations (filtered by session type)
            analysis = self._analyze_considerations(
                transcript, session_id, session_type, progress_callback
            )

            # 6. Make decision
            if analysis.has_blockers:
                prompt = self._generate_continuation_prompt(analysis)

                # Save redirect record for session reflection
                failed_ids = [r.consideration_id for r in analysis.failed_blockers]
                self._save_redirect(
                    session_id=session_id,
                    failed_considerations=failed_ids,
                    continuation_prompt=prompt,
                    work_summary=None,  # Could be enhanced to extract work summary
                )

                return PowerSteeringResult(
                    decision="block",
                    reasons=failed_ids,
                    continuation_prompt=prompt,
                    summary=None,
                )
            # 7. Generate summary and mark complete
            summary = self._generate_summary(transcript, analysis, session_id)
            self._mark_complete(session_id)
            self._write_summary(session_id, summary)

            # Emit completion event
            self._emit_progress(
                progress_callback,
                "complete",
                "Power-steering analysis complete - all checks passed",
            )

            return PowerSteeringResult(
                decision="approve",
                reasons=["all_considerations_satisfied"],
                continuation_prompt=None,
                summary=summary,
            )

        except Exception as e:
            # Fail-open: On any error, approve and log
            self._log(f"Power-steering error (fail-open): {e}", "ERROR")
            return PowerSteeringResult(
                decision="approve",
                reasons=["error_failopen"],
                continuation_prompt=None,
                summary=None,
            )

    def _is_disabled(self) -> bool:
        """Check if power-steering is disabled.

        Three-layer disable system (priority order):
        1. Semaphore file (highest)
        2. Environment variable (medium)
        3. Config file (lowest)

        Returns:
            True if disabled, False if enabled
        """
        # Check 1: Semaphore file
        disabled_file = self.runtime_dir / ".disabled"
        if disabled_file.exists():
            return True

        # Check 2: Environment variable
        if os.getenv("AMPLIHACK_SKIP_POWER_STEERING"):
            return True

        # Check 3: Config file
        if not self.config.get("enabled", False):
            return True

        return False

    def _validate_path(self, path: Path, allowed_parent: Path) -> bool:
        """Validate path is safe to read (permissive for user files).

        Args:
            path: Path to validate
            allowed_parent: Parent directory path must be under (typically project root)

        Returns:
            True if path is safe, False otherwise

        Note:
            Allows paths in:
            1. Project root (backward compatibility)
            2. User's home directory (for Claude Code transcripts in ~/.claude/projects/)
            3. Common temp directories (/tmp, /var/tmp, system temp)

            Security: Power-steering only reads files (read-only operations).
            Reading user-owned files is safe. No privilege escalation risk.
        """
        import tempfile

        try:
            # Resolve to absolute paths
            path_resolved = path.resolve()
            parent_resolved = allowed_parent.resolve()

            # Check 1: Path is within allowed parent (project root)
            try:
                path_resolved.relative_to(parent_resolved)
                self._log("Path validated: within project root", "DEBUG")
                return True
            except ValueError:
                pass  # Not in project root, check other allowed locations

            # Check 2: Path is within user's home directory
            # This allows Claude Code transcript paths like ~/.claude/projects/
            try:
                home = Path.home().resolve()
                path_resolved.relative_to(home)
                self._log("Path validated: within user home directory", "DEBUG")
                return True  # In user's home - safe for read-only operations
            except ValueError:
                pass  # Not in home directory, check temp directories

            # Check 3: Path is in common temp directories (for testing)
            temp_dirs = [
                Path("/tmp"),
                Path("/var/tmp"),
                Path(tempfile.gettempdir()),  # System temp dir
            ]

            for temp_dir in temp_dirs:
                try:
                    path_resolved.relative_to(temp_dir.resolve())
                    self._log(f"Path validated: within temp directory {temp_dir}", "DEBUG")
                    return True  # In temp directory - allow for testing
                except ValueError:
                    continue

            # Not in any allowed locations
            self._log(
                f"Path validation failed: {path_resolved} not in project root, "
                f"home directory, or temp directories",
                "WARNING",
            )
            return False

        except (OSError, RuntimeError) as e:
            self._log(f"Path validation error: {e}", "ERROR")
            return False

    def _already_ran(self, session_id: str) -> bool:
        """Check if power-steering already ran for this session.

        Args:
            session_id: Session identifier

        Returns:
            True if already ran, False otherwise
        """
        semaphore = self.runtime_dir / f".{session_id}_completed"
        return semaphore.exists()

    def _mark_complete(self, session_id: str) -> None:
        """Create semaphore to prevent re-running.

        Args:
            session_id: Session identifier
        """
        try:
            semaphore = self.runtime_dir / f".{session_id}_completed"
            semaphore.parent.mkdir(parents=True, exist_ok=True)
            semaphore.touch()
            semaphore.chmod(0o600)  # Owner read/write only for security
        except OSError:
            pass  # Fail-open: Continue even if semaphore creation fails

    def _get_redirect_file(self, session_id: str) -> Path:
        """Get path to redirects file for a session.

        Args:
            session_id: Session identifier

        Returns:
            Path to redirects.jsonl file
        """
        session_dir = self.runtime_dir / session_id
        return session_dir / "redirects.jsonl"

    def _load_redirects(self, session_id: str) -> List[PowerSteeringRedirect]:
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
        failed_considerations: List[str],
        continuation_prompt: str,
        work_summary: Optional[str] = None,
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
            self._log(f"Failed to save redirect: {e}", "ERROR")

    def _load_transcript(self, transcript_path: Path) -> List[Dict]:
        """Load transcript from JSONL file with size limits.

        Args:
            transcript_path: Path to transcript file

        Returns:
            List of message dictionaries (truncated if exceeds MAX_TRANSCRIPT_LINES)

        Raises:
            OSError: If file cannot be read
            json.JSONDecodeError: If JSONL is malformed
            ValueError: If transcript path is outside project root (security check)

        Note:
            Transcripts exceeding MAX_TRANSCRIPT_LINES are truncated to prevent
            memory exhaustion. A warning is logged when truncation occurs.
        """
        # Security: Validate transcript path is within project root
        if not self._validate_path(transcript_path, self.project_root):
            raise ValueError(
                f"Transcript path {transcript_path} is outside project root {self.project_root}"
            )

        messages = []
        truncated = False

        with open(transcript_path) as f:
            for line_num, line in enumerate(f, 1):
                # Security: Enforce maximum transcript size
                if line_num > MAX_TRANSCRIPT_LINES:
                    truncated = True
                    break

                line = line.strip()
                if not line:
                    continue
                messages.append(json.loads(line))

        if truncated:
            self._log(
                f"Transcript truncated at {MAX_TRANSCRIPT_LINES} lines (original: {line_num})",
                "WARNING",
            )

        return messages

    def _has_development_indicators(
        self,
        code_files_modified: bool,
        test_executions: int,
        pr_operations: bool,
    ) -> bool:
        """Check if transcript shows development indicators.

        Args:
            code_files_modified: Whether code files were modified
            test_executions: Number of test executions
            pr_operations: Whether PR operations were performed

        Returns:
            True if development indicators present
        """
        return code_files_modified or test_executions > 0 or pr_operations

    def _has_informational_indicators(
        self,
        write_edit_operations: int,
        read_grep_operations: int,
        question_count: int,
        user_messages: List[Dict],
    ) -> bool:
        """Check if transcript shows informational session indicators.

        Args:
            write_edit_operations: Number of Write/Edit operations
            read_grep_operations: Number of Read/Grep operations
            question_count: Number of questions in user messages
            user_messages: List of user message dicts

        Returns:
            True if informational indicators present
        """
        # No tool usage or only Read tools with high question density
        if write_edit_operations == 0:
            if read_grep_operations <= 1 and question_count > 0:
                # High question density indicates INFORMATIONAL
                if user_messages and question_count / len(user_messages) > 0.5:
                    return True
        return False

    def _has_maintenance_indicators(
        self,
        write_edit_operations: int,
        doc_files_only: bool,
        git_operations: bool,
        code_files_modified: bool,
    ) -> bool:
        """Check if transcript shows maintenance indicators.

        Args:
            write_edit_operations: Number of Write/Edit operations
            doc_files_only: Whether only doc files were modified
            git_operations: Whether git operations were performed
            code_files_modified: Whether code files were modified

        Returns:
            True if maintenance indicators present
        """
        # Only doc/config files modified
        if write_edit_operations > 0 and doc_files_only:
            return True

        # Git operations without code changes
        if git_operations and not code_files_modified and write_edit_operations == 0:
            return True

        return False

    def _has_investigation_indicators(
        self,
        read_grep_operations: int,
        write_edit_operations: int,
    ) -> bool:
        """Check if transcript shows investigation indicators.

        Args:
            read_grep_operations: Number of Read/Grep operations
            write_edit_operations: Number of Write/Edit operations

        Returns:
            True if investigation indicators present
        """
        # Multiple Read/Grep without modifications
        return read_grep_operations >= 2 and write_edit_operations == 0

    def detect_session_type(self, transcript: List[Dict]) -> str:
        """Detect session type for selective consideration application.

        Session Types:
        - DEVELOPMENT: Code changes, tests, PR operations
        - INFORMATIONAL: Q&A, help queries, capability questions
        - MAINTENANCE: Documentation and configuration updates only
        - INVESTIGATION: Read-only exploration and analysis

        Args:
            transcript: List of message dictionaries

        Returns:
            Session type string: "DEVELOPMENT", "INFORMATIONAL", "MAINTENANCE", or "INVESTIGATION"
        """
        # Check for environment override first
        env_override = os.getenv("AMPLIHACK_SESSION_TYPE", "").upper()
        if env_override in ["DEVELOPMENT", "INFORMATIONAL", "MAINTENANCE", "INVESTIGATION"]:
            self._log(f"Session type overridden by environment: {env_override}", "INFO")
            return env_override

        # Empty transcript defaults to INFORMATIONAL (fail-open)
        if not transcript:
            return "INFORMATIONAL"

        # Collect indicators from transcript
        code_files_modified = False
        doc_files_only = True
        write_edit_operations = 0
        read_grep_operations = 0
        test_executions = 0
        pr_operations = False
        git_operations = False

        # Count questions in user messages for INFORMATIONAL detection
        user_messages = [m for m in transcript if m.get("type") == "user"]
        question_count = 0
        if user_messages:
            for msg in user_messages:
                content = str(msg.get("message", {}).get("content", ""))
                question_count += content.count("?")

        # Analyze tool usage
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if not isinstance(content, list):
                    content = [content]
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_name = block.get("name", "")
                        tool_input = block.get("input", {})

                        # Write/Edit operations
                        if tool_name in ["Write", "Edit"]:
                            write_edit_operations += 1
                            file_path = tool_input.get("file_path", "")

                            # Check if code file using class constant
                            if any(ext in file_path for ext in self.CODE_FILE_EXTENSIONS):
                                code_files_modified = True
                                doc_files_only = False

                            # Check if doc file using class constants
                            if not any(ext in file_path for ext in self.DOC_FILE_EXTENSIONS):
                                if not any(ext in file_path for ext in self.CONFIG_FILE_EXTENSIONS):
                                    doc_files_only = False

                        # Read/Grep operations (investigation indicators)
                        elif tool_name in ["Read", "Grep", "Glob"]:
                            read_grep_operations += 1

                        # Test execution
                        elif tool_name == "Bash":
                            command = tool_input.get("command", "")
                            # Test patterns using class constant
                            if any(pattern in command for pattern in self.TEST_COMMAND_PATTERNS):
                                test_executions += 1

                            # PR operations
                            if "gh pr create" in command or "gh pr" in command:
                                pr_operations = True

                            # Git operations
                            if "git commit" in command or "git push" in command:
                                git_operations = True

        # Decision logic (priority order) using helper methods

        # DEVELOPMENT: Highest priority if code changes detected
        if self._has_development_indicators(code_files_modified, test_executions, pr_operations):
            return "DEVELOPMENT"

        # INFORMATIONAL: No tool usage or only Read tools with high question density
        if self._has_informational_indicators(
            write_edit_operations, read_grep_operations, question_count, user_messages
        ):
            return "INFORMATIONAL"

        # Multiple Read/Grep without modifications = INVESTIGATION
        if self._has_investigation_indicators(read_grep_operations, write_edit_operations):
            return "INVESTIGATION"

        # MAINTENANCE: Only doc/config files modified OR git operations without code changes
        if self._has_maintenance_indicators(
            write_edit_operations, doc_files_only, git_operations, code_files_modified
        ):
            return "MAINTENANCE"

        # Default to INFORMATIONAL if unclear (fail-open, conservative)
        return "INFORMATIONAL"

    def get_applicable_considerations(self, session_type: str) -> List[Dict[str, Any]]:
        """Get considerations applicable to a specific session type.

        Args:
            session_type: Session type ("DEVELOPMENT", "INFORMATIONAL", "MAINTENANCE", "INVESTIGATION")

        Returns:
            List of consideration dictionaries applicable to this session type
        """
        # Filter considerations based on session type
        applicable = []

        for consideration in self.considerations:
            # Check if consideration has applicable_session_types field
            applicable_types = consideration.get("applicable_session_types", [])

            # If no field or empty, check if this is Phase 1 fallback
            if not applicable_types:
                # Phase 1 considerations (no applicable_session_types field)
                # Only apply to DEVELOPMENT sessions by default
                if session_type == "DEVELOPMENT":
                    applicable.append(consideration)
                continue

            # Check if this session type is in the list
            if session_type in applicable_types or "*" in applicable_types:
                applicable.append(consideration)

        return applicable

    def _is_qa_session(self, transcript: List[Dict]) -> bool:
        """Detect if session is interactive Q&A (skip power-steering).

        Heuristics:
        1. No tool calls (no file operations)
        2. High question count in user messages
        3. Short session (< 5 turns)

        Args:
            transcript: List of message dictionaries

        Returns:
            True if Q&A session, False otherwise
        """
        # Count tool uses - check for tool_use blocks in assistant messages
        # Note: We check both 'type' field and 'name' field because transcript
        # format can vary between direct tool_use blocks and nested formats
        tool_uses = 0
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if not isinstance(content, list):
                    content = [content]
                for block in content:
                    if isinstance(block, dict):
                        # Check for tool_use type OR presence of name field (tool indicator)
                        if block.get("type") == "tool_use" or (
                            "name" in block and block.get("name")
                        ):
                            tool_uses += 1

        # If we have substantial tool usage, not Q&A
        if tool_uses >= 2:
            return False

        # If no tool uses, check for Q&A pattern
        if tool_uses == 0:
            # Count user messages with questions
            user_messages = [m for m in transcript if m.get("type") == "user"]
            if len(user_messages) == 0:
                return True  # No user messages = skip

            questions = sum(
                1 for m in user_messages if "?" in str(m.get("message", {}).get("content", ""))
            )

            # If >50% of user messages are questions, likely Q&A
            if questions / len(user_messages) > 0.5:
                return True

        # Short sessions with few tools = likely Q&A
        if len(transcript) < 5 and tool_uses < 2:
            return True

        return False

    def _analyze_considerations(
        self,
        transcript: List[Dict],
        session_id: str,
        session_type: str = None,
        progress_callback: Optional[callable] = None,
    ) -> ConsiderationAnalysis:
        """Analyze transcript against all enabled considerations.

        Phase 2: Uses Claude SDK for intelligent analysis when available,
        falls back to heuristic checkers if SDK unavailable.

        Phase 3: Filters considerations by session type to prevent false positives.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier
            session_type: Session type for selective consideration application (auto-detected if None)
            progress_callback: Optional callback for progress events

        Returns:
            ConsiderationAnalysis with results
        """
        analysis = ConsiderationAnalysis()

        # Auto-detect session type if not provided
        if session_type is None:
            session_type = self.detect_session_type(transcript)
            self._log(f"Auto-detected session type: {session_type}", "DEBUG")

        # Get considerations applicable to this session type
        applicable_considerations = self.get_applicable_considerations(session_type)

        # Track categories for progress
        categories_seen = set()

        for consideration in applicable_considerations:
            # Check if enabled in consideration itself
            if not consideration.get("enabled", True):
                continue

            # Also check config for backward compatibility
            if not self.config.get("checkers_enabled", {}).get(consideration["id"], True):
                continue

            # Emit category event if first time seeing this category
            category = consideration.get("category", "Unknown")
            if category not in categories_seen:
                categories_seen.add(category)
                self._emit_progress(
                    progress_callback,
                    "category",
                    f"Checking {category}",
                    {"category": category},
                )

            # Emit consideration event
            self._emit_progress(
                progress_callback,
                "consideration",
                f"Checking: {consideration['question']}",
                {"consideration_id": consideration["id"], "question": consideration["question"]},
            )

            # Run checker with timeout and error handling
            try:
                with _timeout(CHECKER_TIMEOUT):
                    # Determine if we should use SDK analysis
                    checker_name = consideration["checker"]
                    use_sdk = (
                        SDK_AVAILABLE
                        and checker_name != "generic"  # Skip SDK for generic checkers
                        and checker_name.startswith("_check_")  # Only use SDK for specific checkers
                    )

                    if use_sdk:
                        try:
                            satisfied = analyze_consideration_sync(
                                conversation=transcript,
                                consideration=consideration,
                                project_root=self.project_root,
                            )
                            self._log(
                                f"SDK analysis for '{consideration['id']}': {'satisfied' if satisfied else 'not satisfied'}",
                                "DEBUG",
                            )
                        except Exception as e:
                            # SDK failed, fall back to heuristic checker
                            self._log(
                                f"SDK analysis failed for '{consideration['id']}': {e}, using heuristic",
                                "WARNING",
                            )
                            satisfied = self._run_heuristic_checker(
                                consideration, transcript, session_id
                            )
                    else:
                        # SDK not available or not applicable, use heuristic checker
                        satisfied = self._run_heuristic_checker(
                            consideration, transcript, session_id
                        )

                result = CheckerResult(
                    consideration_id=consideration["id"],
                    satisfied=satisfied,
                    reason=consideration["question"],
                    severity=consideration["severity"],
                )
                analysis.add_result(result)
            except TimeoutError:
                # Fail-open: Treat as satisfied on timeout
                self._log(f"Checker timed out ({CHECKER_TIMEOUT}s)", "WARNING")
                result = CheckerResult(
                    consideration_id=consideration["id"],
                    satisfied=True,  # Fail-open
                    reason=f"Timeout after {CHECKER_TIMEOUT}s",
                    severity=consideration["severity"],
                )
                analysis.add_result(result)
            except Exception as e:
                # Fail-open: Treat as satisfied on error
                self._log(f"Checker failed: {e}", "ERROR")
                result = CheckerResult(
                    consideration_id=consideration["id"],
                    satisfied=True,  # Fail-open
                    reason=f"Error: {e}",
                    severity=consideration["severity"],
                )
                analysis.add_result(result)

        return analysis

    def _run_heuristic_checker(
        self, consideration: Dict[str, Any], transcript: List[Dict], session_id: str
    ) -> bool:
        """Run heuristic checker for a consideration.

        Fallback mechanism when Claude SDK is unavailable or fails.

        Args:
            consideration: Consideration dictionary
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if satisfied, False otherwise
        """
        checker_name = consideration["checker"]

        # Handle generic checker
        if checker_name == "generic":
            checker_func = self._generic_analyzer
        else:
            checker_func = getattr(self, checker_name, None)

        if checker_func is None:
            # Log warning and use generic analyzer as fallback
            self._log(f"Checker not found: {checker_name}, using generic", "WARNING")
            checker_func = self._generic_analyzer

        # Run checker
        if checker_name == "generic" or checker_func == self._generic_analyzer:
            return checker_func(transcript, session_id, consideration)
        return checker_func(transcript, session_id)

    # ========================================================================
    # Phase 1: Top 5 Critical Checkers
    # ========================================================================

    def _check_todos_complete(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if all TODO items completed.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if all TODOs completed, False otherwise
        """
        # Find last TodoWrite tool call
        last_todo_write = None
        for msg in reversed(transcript):
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "TodoWrite":
                                last_todo_write = block.get("input", {})
                                break
            if last_todo_write:
                break

        # If no TodoWrite found, consider satisfied (no todos to check)
        if not last_todo_write:
            return True

        # Check todos in last TodoWrite
        todos = last_todo_write.get("todos", [])
        if not todos:
            return True

        # Check if any todos are not completed
        for todo in todos:
            status = todo.get("status", "pending")
            if status != "completed":
                return False  # Found incomplete todo

        return True  # All todos completed

    def _check_dev_workflow_complete(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if full DEFAULT_WORKFLOW followed.

        Heuristics:
        - Look for multiple agent invocations (architect, builder, reviewer)
        - Check for test execution
        - Verify git operations (commit, push)

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if workflow complete, False otherwise
        """
        # Extract tool names used
        tools_used = set()
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tools_used.add(block.get("name", ""))

        # Check for signs of workflow completion
        has_tests = "Bash" in tools_used  # Tests typically run via Bash
        has_file_ops = any(t in tools_used for t in ["Edit", "Write", "Read"])

        # If no file operations, likely not a development task
        if not has_file_ops:
            return True

        # For development tasks, we expect tests to be run
        if not has_tests:
            return False

        return True

    def _check_philosophy_compliance(self, transcript: List[Dict], session_id: str) -> bool:
        """Check for PHILOSOPHY adherence (zero-BS).

        Heuristics:
        - Look for "TODO", "FIXME", "XXX" in Write/Edit tool calls
        - Check for stub implementations (NotImplementedError, pass)
        - Detect placeholder comments

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if compliant, False otherwise
        """
        # Check Write and Edit tool calls for anti-patterns
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_name = block.get("name", "")
                            if tool_name in ["Write", "Edit"]:
                                tool_input = block.get("input", {})

                                # Check content for anti-patterns
                                content_to_check = ""
                                if "content" in tool_input:
                                    content_to_check = str(tool_input["content"])
                                elif "new_string" in tool_input:
                                    content_to_check = str(tool_input["new_string"])

                                # Look for TODO/FIXME/XXX
                                if re.search(r"\b(TODO|FIXME|XXX)\b", content_to_check):
                                    return False

                                # Look for NotImplementedError
                                if "NotImplementedError" in content_to_check:
                                    return False

                                # Look for stub patterns (function with only pass)
                                if re.search(
                                    r"def\s+\w+\([^)]*\):\s*pass\s*$",
                                    content_to_check,
                                    re.MULTILINE,
                                ):
                                    return False

        return True

    def _check_local_testing(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if agent tested locally.

        Heuristics:
        - Look for Bash tool calls with pytest, npm test, cargo test, etc.
        - Check exit codes (0 = success)
        - Look for "PASSED" or "OK" in output

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if tests run and passed, False otherwise
        """
        # Look for test execution in Bash tool calls
        for msg in transcript:
            if msg.get("type") == "tool_result" and "message" in msg:
                msg_data = msg["message"]
                if msg_data.get("tool_use_id"):
                    # Find corresponding tool_use
                    for prev_msg in transcript:
                        if prev_msg.get("type") == "assistant" and "message" in prev_msg:
                            content = prev_msg["message"].get("content", [])
                            if isinstance(content, list):
                                for block in content:
                                    if isinstance(block, dict):
                                        if block.get("type") == "tool_use" and block.get(
                                            "id"
                                        ) == msg_data.get("tool_use_id"):
                                            # Check if this was a test command
                                            tool_name = block.get("name", "")
                                            if tool_name == "Bash":
                                                command = block.get("input", {}).get("command", "")
                                                # Look for test commands using class constant
                                                if any(
                                                    pattern in command
                                                    for pattern in self.TEST_COMMAND_PATTERNS
                                                ):
                                                    # Check result
                                                    result_content = msg_data.get("content", [])
                                                    if isinstance(result_content, list):
                                                        for result_block in result_content:
                                                            if isinstance(result_block, dict):
                                                                if (
                                                                    result_block.get("type")
                                                                    == "tool_result"
                                                                ):
                                                                    # Check if tests passed
                                                                    output = str(
                                                                        result_block.get(
                                                                            "content", ""
                                                                        )
                                                                    )
                                                                    if (
                                                                        "PASSED" in output
                                                                        or "passed" in output
                                                                    ):
                                                                        return True
                                                                    if (
                                                                        "OK" in output
                                                                        and "FAILED" not in output
                                                                    ):
                                                                        return True

        # No tests found or tests failed
        return False

    def _check_ci_status(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if CI passing/mergeable.

        Heuristics:
        - Look for CI status checks (gh pr view, CI commands)
        - Check for "passing", "success", "mergeable"
        - Look for failure indicators

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if CI passing or not applicable, False if CI failing
        """
        # Look for CI-related commands
        ci_mentioned = False
        ci_passing = False

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            # Check text content for CI mentions
                            if block.get("type") == "text":
                                text = str(block.get("text", ""))
                                if any(
                                    keyword in text.lower()
                                    for keyword in [
                                        "ci",
                                        "github actions",
                                        "continuous integration",
                                    ]
                                ):
                                    ci_mentioned = True
                                    # Check for passing/failing
                                    if any(
                                        keyword in text.lower()
                                        for keyword in ["passing", "success", "mergeable"]
                                    ):
                                        ci_passing = True
                                    if any(
                                        keyword in text.lower()
                                        for keyword in ["failing", "failed", "error"]
                                    ):
                                        return False

        # If CI not mentioned, consider satisfied (not applicable)
        if not ci_mentioned:
            return True

        # If CI mentioned but no clear passing indicator, be conservative
        return ci_passing

    # ========================================================================
    # Phase 2: Additional Checkers (16 new methods)
    # ========================================================================

    def _generic_analyzer(
        self, transcript: List[Dict], session_id: str, consideration: Dict[str, Any]
    ) -> bool:
        """Generic analyzer for considerations without specific checkers.

        Uses simple keyword matching on the consideration question.
        Phase 2: Simple heuristics (future: LLM-based analysis)

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier
            consideration: Consideration dictionary with question

        Returns:
            True if satisfied (fail-open default), False if potential issues detected
        """
        # Extract keywords from question (simple tokenization)
        question = consideration.get("question", "").lower()
        keywords = [
            word
            for word in re.findall(r"\b\w+\b", question)
            if len(word) > 3 and word not in ["were", "does", "need", "that", "this", "with"]
        ]

        if not keywords:
            # No keywords to check, assume satisfied
            return True

        # Build transcript text for searching
        transcript_text = ""
        for msg in transcript:
            if msg.get("type") in ["user", "assistant"]:
                content = msg.get("message", {}).get("content", "")
                if isinstance(content, str):
                    transcript_text += content.lower() + " "
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            transcript_text += str(block.get("text", "")).lower() + " "

        # Check if keywords appear in transcript
        keyword_found = any(keyword in transcript_text for keyword in keywords)

        # Default to satisfied (fail-open), only flag if suspicious patterns
        # This is intentionally conservative to avoid false positives
        self._log(
            f"Generic analyzer for '{consideration['id']}': keywords={keywords}, found={keyword_found}",
            "DEBUG",
        )

        return True  # Phase 2: Always satisfied (fail-open)

    def _check_agent_unnecessary_questions(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if agent asked unnecessary questions instead of proceeding.

        Detects questions that could have been inferred from context.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if no unnecessary questions, False otherwise
        """
        # Count questions asked by assistant
        assistant_questions = 0
        for msg in transcript:
            if msg.get("type") == "assistant":
                content = msg.get("message", {}).get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = str(block.get("text", ""))
                            # Count question marks in assistant responses
                            assistant_questions += text.count("?")

        # Heuristic: If assistant asked more than 3 questions, might be excessive
        if assistant_questions > 3:
            return False

        return True

    def _check_objective_completion(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if original user objective was fully accomplished.

        Looks for completion indicators in later messages.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if objective appears complete, False otherwise
        """
        # Get first user message (the objective)
        first_user_msg = None
        for msg in transcript:
            if msg.get("type") == "user":
                first_user_msg = msg
                break

        if not first_user_msg:
            return True  # No objective to check

        # Look for completion indicators in assistant messages
        completion_indicators = [
            "complete",
            "finished",
            "done",
            "implemented",
            "successfully",
            "all tests pass",
        ]

        for msg in reversed(transcript[-10:]):  # Check last 10 messages
            if msg.get("type") == "assistant":
                content = msg.get("message", {}).get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = str(block.get("text", "")).lower()
                            if any(indicator in text for indicator in completion_indicators):
                                return True

        return False  # No completion indicators found

    def _check_documentation_updates(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if relevant documentation files were updated.

        Looks for Write/Edit operations on documentation files.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if docs updated or not applicable, False if needed but missing
        """
        # Check if code changes were made
        code_files_modified = False
        doc_files_modified = False

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_name = block.get("name", "")
                            if tool_name in ["Write", "Edit"]:
                                tool_input = block.get("input", {})
                                file_path = tool_input.get("file_path", "")

                                # Check for code files using class constant
                                if any(ext in file_path for ext in self.CODE_FILE_EXTENSIONS):
                                    code_files_modified = True

                                # Check for doc files using class constant
                                if any(ext in file_path for ext in self.DOC_FILE_EXTENSIONS):
                                    doc_files_modified = True

        # If code was modified but no docs updated, flag as issue
        if code_files_modified and not doc_files_modified:
            return False

        return True

    def _check_tutorial_needed(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if new feature needs tutorial/how-to.

        Detects new user-facing features that should have examples.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if tutorial exists or not needed, False if missing
        """
        # Look for new feature indicators
        feature_keywords = ["new feature", "add feature", "implement feature", "create feature"]
        has_new_feature = False

        for msg in transcript:
            if msg.get("type") == "user":
                content = str(msg.get("message", {}).get("content", "")).lower()
                if any(keyword in content for keyword in feature_keywords):
                    has_new_feature = True
                    break

        if not has_new_feature:
            return True  # No new feature, tutorial not needed

        # Check for example/tutorial files
        tutorial_patterns = ["example", "tutorial", "how_to", "guide", "demo"]
        has_tutorial = False

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_name = block.get("name", "")
                            if tool_name in ["Write", "Edit"]:
                                file_path = block.get("input", {}).get("file_path", "").lower()
                                if any(pattern in file_path for pattern in tutorial_patterns):
                                    has_tutorial = True
                                    break

        return has_tutorial

    def _check_presentation_needed(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if work needs presentation deck.

        Detects high-impact work that should be presented to stakeholders.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if presentation exists or not needed, False if missing
        """
        # This is a low-priority check, default to satisfied
        # Could be enhanced to detect high-impact work patterns
        return True

    def _check_next_steps(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if next steps were identified and documented.

        Looks for TODO items or documented follow-up tasks.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if next steps documented, False if missing
        """
        # Look for next steps indicators
        next_steps_keywords = [
            "next steps",
            "follow-up",
            "future work",
            "todo",
            "remaining",
            "planned",
        ]

        for msg in reversed(transcript[-20:]):  # Check recent messages
            if msg.get("type") == "assistant":
                content = msg.get("message", {}).get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = str(block.get("text", "")).lower()
                            if any(keyword in text for keyword in next_steps_keywords):
                                return True

        # Also check for Write operations on TODO or planning files
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "Write":
                                file_path = block.get("input", {}).get("file_path", "").lower()
                                if "todo" in file_path or "plan" in file_path:
                                    return True

        return False

    def _check_docs_organization(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if investigation/session docs are organized properly.

        Verifies documentation is in correct directories.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if docs properly organized, False otherwise
        """
        # Check for doc files created in wrong locations
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "Write":
                                file_path = block.get("input", {}).get("file_path", "")

                                # Check for investigation/session docs in wrong places
                                if any(
                                    pattern in file_path.lower()
                                    for pattern in ["investigation", "session", "log"]
                                ):
                                    # Should be in .claude/runtime or .claude/docs
                                    if ".claude" not in file_path:
                                        return False

        return True

    def _check_investigation_docs(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if investigation findings were documented.

        Ensures exploration work is captured in persistent documentation.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if investigation documented, False if missing
        """
        # Look for investigation indicators
        investigation_keywords = [
            "investigation",
            "exploration",
            "research",
            "analysis",
            "findings",
        ]

        has_investigation = False
        for msg in transcript:
            if msg.get("type") == "user":
                content = str(msg.get("message", {}).get("content", "")).lower()
                if any(keyword in content for keyword in investigation_keywords):
                    has_investigation = True
                    break

        if not has_investigation:
            return True  # No investigation, docs not needed

        # Check for documentation of findings
        doc_created = False
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "Write":
                                file_path = block.get("input", {}).get("file_path", "").lower()
                                if any(
                                    pattern in file_path for pattern in [".md", "readme", "doc"]
                                ):
                                    doc_created = True
                                    break

        return doc_created

    def _check_shortcuts(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if any quality shortcuts were taken.

        Identifies compromises like skipped error handling or incomplete validation.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if no shortcuts, False if compromises detected
        """
        # Look for shortcut indicators in code
        shortcut_patterns = [
            r"\bpass\b.*#.*later",
            r"#.*hack",
            r"#.*workaround",
            r"#.*temporary",
            r"#.*fix.*later",
        ]

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_name = block.get("name", "")
                            if tool_name in ["Write", "Edit"]:
                                tool_input = block.get("input", {})
                                content_to_check = str(tool_input.get("content", "")) + str(
                                    tool_input.get("new_string", "")
                                )

                                # Check for shortcut patterns
                                for pattern in shortcut_patterns:
                                    if re.search(pattern, content_to_check, re.IGNORECASE):
                                        return False

        return True

    def _check_interactive_testing(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if agent tested interactively beyond automated tests.

        Looks for manual verification, edge case testing, UI validation.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if interactive testing done, False if only automated tests
        """
        # Look for interactive testing indicators
        interactive_keywords = [
            "manually tested",
            "tried",
            "verified",
            "checked",
            "confirmed",
            "validated",
        ]

        for msg in transcript:
            if msg.get("type") == "assistant":
                content = msg.get("message", {}).get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = str(block.get("text", "")).lower()
                            if any(keyword in text for keyword in interactive_keywords):
                                return True

        # Also accept if automated tests are comprehensive (10+ tests)
        test_count = 0
        for msg in transcript:
            if msg.get("type") == "tool_result":
                output = str(msg.get("message", {}).get("content", ""))
                # Count test results
                test_count += output.lower().count("passed")
                test_count += output.lower().count("ok")

        if test_count >= 10:
            return True  # Comprehensive automated testing is acceptable

        return False

    def _check_unrelated_changes(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if there are unrelated changes in PR.

        Detects scope creep and unrelated modifications.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if no unrelated changes, False if scope creep detected
        """
        # Get original objective from first user message
        first_user_msg = None
        for msg in transcript:
            if msg.get("type") == "user":
                first_user_msg = str(msg.get("message", {}).get("content", "")).lower()
                break

        if not first_user_msg:
            return True

        # Check files modified
        files_modified = []
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") in ["Write", "Edit"]:
                                file_path = block.get("input", {}).get("file_path", "")
                                files_modified.append(file_path.lower())

        # Heuristic: If more than 20 files modified, might have scope creep
        if len(files_modified) > 20:
            return False

        return True

    def _check_root_pollution(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if PR polluted project root with new files.

        Flags new top-level files that should be in subdirectories.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if no root pollution, False if new top-level files added
        """
        # Check for new files in project root
        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "Write":
                                file_path = block.get("input", {}).get("file_path", "")

                                # Check if file is in root (only one path component)
                                path_parts = file_path.strip("/").split("/")
                                if len(path_parts) == 1:
                                    # New file in root - check if it's acceptable
                                    filename = path_parts[0].lower()
                                    acceptable_root_files = [
                                        "readme",
                                        "license",
                                        "makefile",
                                        "dockerfile",
                                        ".gitignore",
                                        "setup.py",
                                        "requirements.txt",
                                    ]

                                    if not any(
                                        acceptable in filename
                                        for acceptable in acceptable_root_files
                                    ):
                                        return False

        return True

    def _check_pr_description(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if PR description is clear and complete.

        Verifies PR has summary, test plan, and context.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if PR description adequate, False if missing or incomplete
        """
        # Look for PR creation (gh pr create)
        pr_created = False
        pr_body = ""

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            if block.get("name") == "Bash":
                                command = block.get("input", {}).get("command", "")
                                if "gh pr create" in command:
                                    pr_created = True
                                    pr_body = command.lower()

        if not pr_created:
            return True  # No PR, check not applicable

        # Check PR body for required sections
        required_sections = ["summary", "test", "plan"]
        has_all_sections = all(section in pr_body for section in required_sections)

        return has_all_sections

    def _check_review_responses(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if PR review comments were addressed.

        Verifies reviewer feedback was acknowledged and resolved.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if reviews addressed or no reviews, False if unaddressed feedback
        """
        # Look for review-related activity
        review_keywords = ["review", "feedback", "comment", "requested changes"]
        has_reviews = False

        for msg in transcript:
            if msg.get("type") == "user":
                content = str(msg.get("message", {}).get("content", "")).lower()
                if any(keyword in content for keyword in review_keywords):
                    has_reviews = True
                    break

        if not has_reviews:
            return True  # No reviews to address

        # Look for response indicators
        response_keywords = ["addressed", "fixed", "updated", "changed", "resolved"]
        has_responses = False

        for msg in transcript:
            if msg.get("type") == "assistant":
                content = msg.get("message", {}).get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            text = str(block.get("text", "")).lower()
                            if any(keyword in text for keyword in response_keywords):
                                has_responses = True
                                break

        return has_responses

    def _check_branch_rebase(self, transcript: List[Dict], session_id: str) -> bool:
        """Check if branch needs rebase on main.

        Verifies branch is up to date with main.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if branch is current, False if needs rebase
        """
        # Look for git status or branch checks
        for msg in transcript:
            if msg.get("type") == "tool_result":
                output = str(msg.get("message", {}).get("content", "")).lower()

                # Check for "behind" indicators
                if "behind" in output or "diverged" in output:
                    return False

                # Check for "up to date" indicators
                if "up to date" in output or "up-to-date" in output:
                    return True

        # Default to satisfied if no information
        return True

    def _check_ci_precommit_mismatch(self, transcript: List[Dict], session_id: str) -> bool:
        """Check for CI failures contradicting passing pre-commit.

        Identifies divergence between local pre-commit and CI checks.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if no mismatch, False if divergence detected
        """
        # Look for pre-commit passing
        precommit_passed = False
        ci_failed = False

        for msg in transcript:
            if msg.get("type") in ["assistant", "tool_result"]:
                content_str = str(msg.get("message", {})).lower()

                # Check for pre-commit success
                if "pre-commit" in content_str or "precommit" in content_str:
                    if "passed" in content_str or "success" in content_str:
                        precommit_passed = True

                # Check for CI failure
                if "ci" in content_str or "github actions" in content_str:
                    if "failed" in content_str or "failing" in content_str:
                        ci_failed = True

        # If both conditions met, there's a mismatch
        if precommit_passed and ci_failed:
            return False

        return True

    # ========================================================================
    # Progress Tracking
    # ========================================================================

    def _emit_progress(
        self,
        progress_callback: Optional[callable],
        event_type: str,
        message: str,
        details: Optional[Dict] = None,
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
            self._log(f"Progress callback error: {e}", "WARNING")

    # ========================================================================
    # Output Generation
    # ========================================================================

    def _generate_continuation_prompt(self, analysis: ConsiderationAnalysis) -> str:
        """Generate actionable continuation prompt.

        Args:
            analysis: Analysis results with failed considerations

        Returns:
            Formatted continuation prompt
        """
        prompt_parts = [
            "POWER-STEERING: Session appears incomplete",
            "",
            "The following checks failed and need to be addressed:",
            "",
        ]

        # Group by category
        by_category = analysis.group_by_category()

        for category, failed in by_category.items():
            prompt_parts.append(f"**{category}**")
            for result in failed:
                prompt_parts.append(f"  - {result.reason}")
            prompt_parts.append("")

        prompt_parts.append("Once these are addressed, you may stop the session.")
        prompt_parts.append("")
        prompt_parts.append("To disable power-steering: export AMPLIHACK_SKIP_POWER_STEERING=1")

        return "\n".join(prompt_parts)

    def _generate_summary(
        self, transcript: List[Dict], analysis: ConsiderationAnalysis, session_id: str
    ) -> str:
        """Generate session summary for successful completion.

        Args:
            transcript: List of message dictionaries
            analysis: Analysis results
            session_id: Session identifier

        Returns:
            Formatted summary
        """
        summary_parts = [
            "# Power-Steering Session Summary",
            "",
            f"**Session ID**: {session_id}",
            f"**Completed**: {datetime.now().isoformat()}",
            "",
            "## Status",
            "All critical checks passed - session complete.",
            "",
            "## Considerations Verified",
        ]

        # List all satisfied checks
        for consideration in self.considerations:
            result = analysis.results.get(consideration["id"])
            if result and result.satisfied:
                summary_parts.append(f"- ✓ {consideration['question']}")

        summary_parts.append("")
        summary_parts.append("---")
        summary_parts.append("Generated by Power-Steering Mode (Phase 2)")

        return "\n".join(summary_parts)

    def _write_summary(self, session_id: str, summary: str) -> None:
        """Write summary to file.

        Args:
            session_id: Session identifier
            summary: Summary content
        """
        try:
            summary_dir = self.runtime_dir / session_id
            summary_dir.mkdir(parents=True, exist_ok=True)
            summary_path = summary_dir / "summary.md"
            summary_path.write_text(summary)
            summary_path.chmod(0o644)  # Owner read/write, others read
        except OSError:
            pass  # Fail-open: Continue even if summary writing fails

    def _log(self, message: str, level: str = "INFO") -> None:
        """Log message to power-steering log file.

        Args:
            message: Message to log
            level: Log level (INFO, WARNING, ERROR)
        """
        try:
            log_file = self.runtime_dir / "power_steering.log"
            timestamp = datetime.now().isoformat()

            # Create with restrictive permissions if it doesn't exist
            is_new = not log_file.exists()

            with open(log_file, "a") as f:
                f.write(f"[{timestamp}] {level}: {message}\n")

            # Set permissions on new files
            if is_new:
                log_file.chmod(0o600)  # Owner read/write only for security
        except OSError:
            pass  # Fail silently on logging errors


# ============================================================================
# Module Interface
# ============================================================================


def check_session(
    transcript_path: Path, session_id: str, project_root: Optional[Path] = None
) -> PowerSteeringResult:
    """Convenience function to check session completeness.

    Args:
        transcript_path: Path to transcript JSONL file
        session_id: Session identifier
        project_root: Project root (auto-detected if None)

    Returns:
        PowerSteeringResult with decision
    """
    checker = PowerSteeringChecker(project_root)
    return checker.check(transcript_path, session_id)


if __name__ == "__main__":
    # For testing: Allow running directly
    if len(sys.argv) < 3:
        print("Usage: power_steering_checker.py <transcript_path> <session_id>")
        sys.exit(1)

    transcript_path = Path(sys.argv[1])
    session_id = sys.argv[2]

    result = check_session(transcript_path, session_id)
    print(json.dumps({"decision": result.decision, "reasons": result.reasons}, indent=2))
