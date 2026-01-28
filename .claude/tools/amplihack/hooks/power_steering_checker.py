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

Phase 4 (Performance) Implementation:
- Parallel SDK calls using asyncio.gather()
- Transcript loaded ONCE, shared across parallel workers
- All checks run (no early exit) for comprehensive feedback
- No caching (not applicable to session-specific analysis)
"""

import asyncio
import json
import os
import re
import signal
import sys
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

import yaml

# Clean import structure
sys.path.insert(0, str(Path(__file__).parent))

# Try to import Claude SDK integration
try:
    from claude_power_steering import (
        analyze_claims_sync,
        analyze_consideration,
        analyze_if_addressed_sync,
    )

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

# Import turn-aware state management with delta analysis
try:
    from power_steering_state import (
        DeltaAnalysisResult,
        DeltaAnalyzer,
        FailureEvidence,
        PowerSteeringTurnState,
        TurnStateManager,
    )

    TURN_STATE_AVAILABLE = True
except ImportError:
    TURN_STATE_AVAILABLE = False

# Try to import completion evidence module
try:
    from completion_evidence import (
        CompletionEvidenceChecker,
        EvidenceType,
    )

    EVIDENCE_AVAILABLE = True
except ImportError:
    EVIDENCE_AVAILABLE = False

# Try to import compaction validator
try:
    from compaction_validator import (
        CompactionContext,
        CompactionValidator,
    )

    COMPACTION_AVAILABLE = True
except ImportError:
    COMPACTION_AVAILABLE = False

    # Create placeholder
    class CompactionContext:
        def __init__(self):
            self.has_compaction_event = False


# Security: Maximum transcript size to prevent memory exhaustion
MAX_TRANSCRIPT_LINES = 50000  # Limit transcript to 50K lines (~10-20MB typical)

# Timeout hierarchy: HOOK_TIMEOUT (120s) > PARALLEL_TIMEOUT (60s) > CHECKER_TIMEOUT (25s)
# Individual checker execution budget (within parallel execution budget)
CHECKER_TIMEOUT = 25

# Parallel execution budget: All 21 checks complete in ~15-20s typically, 60s provides buffer
# Must be less than HOOK_TIMEOUT (120s) to avoid being killed by framework
PARALLEL_TIMEOUT = 60

# Public API (the "studs" for this brick)
__all__ = [
    "PowerSteeringChecker",
    "PowerSteeringResult",
    "CheckerResult",
    "ConsiderationAnalysis",
]


def _write_with_retry(filepath: Path, data: str, mode: str = "w", max_retries: int = 3) -> None:
    """Write file with exponential backoff for cloud sync resilience.

    Handles transient file I/O errors that can occur with cloud-synced directories
    (iCloud, OneDrive, Dropbox, etc.) by retrying with exponential backoff.

    Args:
        filepath: Path to file to write
        data: Content to write
        mode: File mode ('w' for write, 'a' for append)
        max_retries: Maximum retry attempts (default: 3)

    Raises:
        OSError: If all retries exhausted (fail-open: caller should handle)
    """
    import time

    retry_delay = 0.1

    for attempt in range(max_retries):
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            if mode == "w":
                filepath.write_text(data)
            else:  # append mode
                with open(filepath, mode) as f:
                    f.write(data)
            return  # Success!
        except OSError as e:
            if e.errno == 5 and attempt < max_retries - 1:  # Input/output error
                if attempt == 0:
                    # Only warn on first retry
                    import sys

                    sys.stderr.write(
                        "[Power Steering] File I/O error, retrying (may be cloud sync issue)\n"
                    )
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                raise  # Give up after max retries or non-transient error


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
    recovery_steps: list[str] = field(default_factory=list)  # Optional recovery guidance
    executed: bool = True  # Whether this check was actually executed

    @property
    def id(self) -> str:
        """Alias for consideration_id for backward compatibility."""
        return self.consideration_id


@dataclass
class ConsiderationAnalysis:
    """Results of analyzing all considerations."""

    results: dict[str, CheckerResult] = field(default_factory=dict)
    failed_blockers: list[CheckerResult] = field(default_factory=list)
    failed_warnings: list[CheckerResult] = field(default_factory=list)

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

    def group_by_category(self) -> dict[str, list[CheckerResult]]:
        """Group failed considerations by category."""
        # For Phase 1, use simplified categories based on consideration ID prefix
        grouped: dict[str, list[CheckerResult]] = {}
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
    failed_considerations: list[str]  # IDs of failed checks
    continuation_prompt: str
    work_summary: str | None = None


@dataclass
class PowerSteeringResult:
    """Final decision from power-steering analysis."""

    decision: Literal["approve", "block"]
    reasons: list[str]
    continuation_prompt: str | None = None
    summary: str | None = None
    analysis: Optional["ConsiderationAnalysis"] = None  # Full analysis results for visibility
    is_first_stop: bool = False  # True if this is the first stop attempt in session
    evidence_results: list = field(default_factory=list)  # Concrete evidence from Phase 1
    compaction_context: Any = None  # Compaction diagnostics (CompactionContext if available)
    considerations: list = field(
        default_factory=list
    )  # List of CheckerResult objects for visibility


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

    # Keywords that indicate simple housekeeping tasks (skip power-steering)
    # When found in user messages, session is classified as SIMPLE and most
    # considerations are skipped. These are routine maintenance tasks.
    SIMPLE_TASK_KEYWORDS = [
        "cleanup",
        "clean up",
        "fetch",
        "git fetch",
        "git pull",
        "pull latest",
        "sync",
        "update branch",
        "rebase",
        "git rebase",
        "merge main",
        "merge master",
        "workspace",
        "stash",
        "git stash",
        "discard changes",
        "reset",
        "checkout",
        "switch branch",
        "list files",
        "show status",
        "git status",
        "what's changed",
        "what changed",
    ]

    # Keywords that indicate investigation/troubleshooting sessions
    # When found in early user messages, session is classified as INVESTIGATION
    # regardless of tool usage patterns (fixes #1604)
    #
    # Note: Using substring matching, so shorter forms match longer variants:
    # - "troubleshoot" matches "troubleshooting"
    # - "diagnos" matches "diagnose", "diagnosis", "diagnosing"
    # - "debug" matches "debugging"
    INVESTIGATION_KEYWORDS = [
        "investigate",
        "troubleshoot",
        "diagnos",  # matches diagnose, diagnosis, diagnosing
        "analyze",
        "analyse",
        "research",
        "explore",
        "understand",
        "figure out",
        "why does",
        "why is",
        "how does",
        "how is",
        "what causes",
        "what's causing",
        "root cause",
        "debug",
        "explain",
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

    def __init__(self, project_root: Path | None = None):
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

    def _validate_config_integrity(self, config: dict) -> bool:
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

    def _load_config(self) -> dict[str, Any]:
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

    def _load_considerations_yaml(self) -> list[dict[str, Any]]:
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
        transcript_path: Path | list[dict],
        session_id: str,
        progress_callback: Callable | None = None,
    ) -> PowerSteeringResult:
        """Main entry point - analyze transcript and make decision using two-phase verification.

        Phase 1: Check concrete evidence (GitHub, filesystem, user confirmation)
        Phase 2: SDK analysis (only if no concrete evidence of completion)
        Phase 3: Combine results (evidence can override SDK concerns)

        Args:
            transcript_path: Path to session transcript JSONL file OR transcript list (for testing)
            session_id: Unique session identifier
            progress_callback: Optional callback for progress events (event_type, message, details)

        Returns:
            PowerSteeringResult with decision and prompt/summary
        """
        # Handle transcript list (testing interface)
        if isinstance(transcript_path, list):
            return self._check_with_transcript_list(transcript_path, session_id)

        # Initialize turn state tracking (outside try block for fail-open)
        turn_state: PowerSteeringTurnState | None = None
        turn_state_manager: TurnStateManager | None = None

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

            # 3. Load transcript (with pre-compaction fallback - Issue #1962)
            # Check if session was compacted - if so, use the FULL pre-compaction transcript
            # instead of the truncated compacted version Claude Code provides
            pre_compaction_path = self._get_pre_compaction_transcript(session_id)
            compaction_detected = pre_compaction_path is not None

            if pre_compaction_path:
                # Session was compacted - load the full transcript from pre-compaction save
                self._emit_progress(
                    progress_callback,
                    "compaction_detected",
                    "Session compaction detected - using pre-compaction transcript",
                    {"pre_compaction_path": str(pre_compaction_path)},
                )
                transcript = self._load_pre_compaction_transcript(pre_compaction_path)

                # If pre-compaction loading failed, fall back to provided transcript
                if not transcript:
                    self._log(
                        "Pre-compaction transcript load failed, falling back to provided transcript",
                        "WARNING",
                    )
                    transcript = self._load_transcript(transcript_path)
                    compaction_detected = False  # Reset since we couldn't use pre-compaction
            else:
                # No compaction or compaction data unavailable - use provided transcript
                transcript = self._load_transcript(transcript_path)

            # 3b. Initialize turn state management (fail-open on import error)
            if TURN_STATE_AVAILABLE:
                turn_state_manager = TurnStateManager(
                    project_root=self.project_root,
                    session_id=session_id,
                    log=lambda msg: self._log(msg, "INFO"),
                )
                turn_state = turn_state_manager.load_state()
                turn_state = turn_state_manager.increment_turn(turn_state)
                self._log(
                    f"Turn state: turn={turn_state.turn_count}, blocks={turn_state.consecutive_blocks}",
                    "INFO",
                )

                # 3c. Check auto-approve threshold BEFORE running analysis
                should_approve, reason, escalation_msg = turn_state_manager.should_auto_approve(
                    turn_state
                )
                if should_approve:
                    self._log(f"Auto-approve triggered: {reason}", "INFO")
                    self._emit_progress(
                        progress_callback,
                        "auto_approve",
                        f"Auto-approving after {turn_state.consecutive_blocks} consecutive blocks",
                        {"reason": reason},
                    )

                    # Reset state and approve
                    turn_state = turn_state_manager.record_approval(turn_state)
                    turn_state_manager.save_state(turn_state)

                    return PowerSteeringResult(
                        decision="approve",
                        reasons=["auto_approve_threshold"],
                        continuation_prompt=None,
                        summary=f"Auto-approved: {reason}",
                    )

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
                # Reset turn state on approval
                if turn_state_manager and turn_state:
                    turn_state = turn_state_manager.record_approval(turn_state)
                    turn_state_manager.save_state(turn_state)
                return PowerSteeringResult(
                    decision="approve",
                    reasons=["qa_session"],
                    continuation_prompt=None,
                    summary=None,
                )

            # 4c. State-based verification (Issue #1962 - robust fallback for post-compaction)
            # When compaction is detected, supplement transcript analysis with actual state checks
            # This provides ground truth even when transcript history is incomplete
            if compaction_detected:
                state_verification = self._verify_actual_state(session_id)
                if state_verification.get("all_passing"):
                    self._log(
                        "State-based verification passed (PR mergeable, CI passing, branch current)",
                        "INFO",
                    )
                    self._emit_progress(
                        progress_callback,
                        "state_verified",
                        "Work completion verified via state checks",
                        state_verification,
                    )
                    # If all state checks pass, this is strong evidence of completion
                    # Store for decision-making but don't auto-approve yet (let evidence checker run too)
                    self._state_verification_passed = True
                else:
                    self._state_verification_passed = False
            else:
                self._state_verification_passed = False

            # 4d. PHASE 1: Evidence-based verification (fail-fast on concrete completion signals)
            if EVIDENCE_AVAILABLE:
                try:
                    evidence_checker = CompletionEvidenceChecker(self.project_root)
                    evidence_results = []

                    # Check PR status (strongest evidence)
                    pr_evidence = evidence_checker.check_pr_status()
                    if pr_evidence:
                        evidence_results.append(pr_evidence)

                        # If PR merged, work is definitely complete
                        if (
                            pr_evidence.evidence_type == EvidenceType.PR_MERGED
                            and pr_evidence.verified
                        ):
                            self._log("PR merged - work complete (concrete evidence)", "INFO")
                            return PowerSteeringResult(
                                decision="approve",
                                reasons=["PR merged successfully"],
                            )

                    # Check user confirmation (escape hatch)
                    session_dir = (
                        self.project_root / ".claude" / "runtime" / "power-steering" / session_id
                    )
                    user_confirm = evidence_checker.check_user_confirmation(session_dir)
                    if user_confirm and user_confirm.verified:
                        evidence_results.append(user_confirm)
                        self._log("User confirmed completion - allowing stop", "INFO")
                        return PowerSteeringResult(
                            decision="approve",
                            reasons=["User explicitly confirmed work is complete"],
                        )

                    # Check TODO completion
                    todo_evidence = evidence_checker.check_todo_completion(transcript_path)
                    evidence_results.append(todo_evidence)

                    # Store evidence for later use in Phase 3
                    self._evidence_results = evidence_results

                except Exception as e:
                    # Fail-open: If evidence checking fails, continue to SDK analysis
                    self._log(f"Evidence checking failed (non-critical): {e}", "WARNING")
                    self._evidence_results = []

            # 5. Analyze against considerations (filtered by session type)
            analysis = self._analyze_considerations(
                transcript, session_id, session_type, progress_callback
            )

            # 5b. Delta analysis: Check if NEW content addresses previous failures
            addressed_concerns: dict[str, str] = {}
            user_claims: list[str] = []
            delta_result: DeltaAnalysisResult | None = None

            if (
                TURN_STATE_AVAILABLE
                and turn_state
                and turn_state.block_history
                and turn_state_manager
            ):
                # Get previous block's failures for delta analysis
                previous_block = turn_state.get_previous_block()
                if previous_block and previous_block.failed_evidence:
                    # Initialize delta analyzer for text extraction
                    delta_analyzer = DeltaAnalyzer(log=lambda msg: self._log(msg, "INFO"))

                    # Get delta transcript (new messages since last block)
                    start_idx, end_idx = turn_state_manager.get_delta_transcript_range(
                        turn_state, len(transcript)
                    )
                    delta_messages = transcript[start_idx:end_idx]

                    self._log(
                        f"Delta analysis: {len(delta_messages)} new messages since last block",
                        "INFO",
                    )

                    # Extract delta text for LLM analysis
                    delta_text = delta_analyzer._extract_all_text(delta_messages)

                    # Use LLM-based claim detection (replaces regex patterns)
                    if SDK_AVAILABLE and delta_text:
                        self._log("Using LLM-based claim detection", "DEBUG")
                        user_claims = analyze_claims_sync(delta_text, self.project_root)
                    else:
                        user_claims = []

                    # Use LLM-based address checking for each previous failure
                    if SDK_AVAILABLE and delta_text:
                        self._log("Using LLM-based address checking", "DEBUG")
                        for failure in previous_block.failed_evidence:
                            evidence = analyze_if_addressed_sync(
                                failure.consideration_id,
                                failure.reason,
                                delta_text,
                                self.project_root,
                            )
                            if evidence:
                                addressed_concerns[failure.consideration_id] = evidence
                    else:
                        # Fallback to simple DeltaAnalyzer (heuristics) if SDK unavailable
                        delta_result = delta_analyzer.analyze_delta(
                            delta_messages, previous_block.failed_evidence
                        )
                        addressed_concerns = delta_result.new_content_addresses_failures
                        if not user_claims:
                            user_claims = delta_result.new_claims_detected

                    if addressed_concerns:
                        self._log(
                            f"Delta addressed {len(addressed_concerns)} concerns: "
                            f"{list(addressed_concerns.keys())}",
                            "INFO",
                        )
                    if user_claims:
                        self._log(f"Detected {len(user_claims)} completion claims", "INFO")

            # 6. Check if this is first stop (visibility feature)
            is_first_stop = not self._results_already_shown(session_id)

            # 7. Make decision based on first/subsequent stop
            if analysis.has_blockers:
                # Filter out addressed concerns from blockers
                remaining_blockers = [
                    r
                    for r in analysis.failed_blockers
                    if r.consideration_id not in addressed_concerns
                ]

                # If all blockers were addressed, treat as passing
                if not remaining_blockers and addressed_concerns:
                    self._log(
                        f"All {len(addressed_concerns)} blockers were addressed in this turn",
                        "INFO",
                    )
                    analysis = self._create_passing_analysis(analysis, addressed_concerns)

                # Issue #1962: State-based override for post-compaction scenarios
                # When session was compacted and state verification passed (PR mergeable, CI passing),
                # trust actual state over potentially incomplete transcript analysis
                elif (
                    compaction_detected
                    and getattr(self, "_state_verification_passed", False)
                    and remaining_blockers
                ):
                    self._log(
                        f"Post-compaction state override: {len(remaining_blockers)} transcript-based "
                        "blockers overridden by passing state verification (PR mergeable, CI passing)",
                        "INFO",
                    )
                    self._emit_progress(
                        progress_callback,
                        "state_override",
                        f"Overriding {len(remaining_blockers)} blockers via state verification",
                        {"blockers_overridden": [r.consideration_id for r in remaining_blockers]},
                    )
                    # Create a passing analysis with note about state override
                    override_note = {
                        r.consideration_id: "Overridden by state verification (PR mergeable, CI passing)"
                        for r in remaining_blockers
                    }
                    analysis = self._create_passing_analysis(analysis, override_note)

                else:
                    # Actual failures - block
                    # Mark results shown on first stop to prevent race condition
                    if is_first_stop:
                        self._mark_results_shown(session_id)

                    # Record block in turn state with full evidence
                    blockers_to_record = remaining_blockers or analysis.failed_blockers

                    if turn_state_manager and turn_state:
                        # Convert CheckerResults to FailureEvidence
                        failed_evidence = self._convert_to_failure_evidence(
                            blockers_to_record, transcript, user_claims
                        )

                        turn_state = turn_state_manager.record_block_with_evidence(
                            turn_state, failed_evidence, len(transcript), user_claims
                        )
                        turn_state_manager.save_state(turn_state)

                    failed_ids = [r.consideration_id for r in blockers_to_record]

                    prompt = self._generate_continuation_prompt(
                        analysis, transcript, turn_state, addressed_concerns, user_claims
                    )

                    # Include formatted results in the prompt for visibility
                    results_text = self._format_results_text(analysis, session_type)
                    prompt_with_results = f"{prompt}\n{results_text}"

                    # Save redirect record for session reflection
                    self._save_redirect(
                        session_id=session_id,
                        failed_considerations=failed_ids,
                        continuation_prompt=prompt_with_results,
                        work_summary=None,  # Could be enhanced to extract work summary
                    )

                    return PowerSteeringResult(
                        decision="block",
                        reasons=failed_ids,
                        continuation_prompt=prompt_with_results,
                        summary=None,
                        analysis=analysis,
                        is_first_stop=is_first_stop,
                    )

            # All checks passed (or all blockers were addressed)
            # FIX (Issue #1744): Check if any checks were actually evaluated
            # If all checks were skipped (no results), approve immediately without blocking
            if len(analysis.results) == 0:
                self._log(
                    "No power-steering checks applicable for session type - approving immediately",
                    "INFO",
                )
                # Mark complete to prevent re-running
                self._mark_complete(session_id)
                self._emit_progress(
                    progress_callback,
                    "complete",
                    "Power-steering analysis complete - no applicable checks for session type",
                )
                return PowerSteeringResult(
                    decision="approve",
                    reasons=["no_applicable_checks"],
                    continuation_prompt=None,
                    summary=None,
                    analysis=analysis,
                    is_first_stop=False,
                )

            if is_first_stop:
                # FIRST STOP: Block to show results (visibility feature)
                # Mark results shown immediately to prevent race condition
                self._mark_results_shown(session_id)
                self._log("First stop - blocking to display all results for visibility", "INFO")
                self._emit_progress(
                    progress_callback,
                    "complete",
                    "Power-steering analysis complete - all checks passed (first stop - displaying results)",
                )

                # Format results for inclusion in continuation_prompt
                # This ensures results are visible even when stderr is not shown
                results_text = self._format_results_text(analysis, session_type)

                return PowerSteeringResult(
                    decision="block",
                    reasons=["first_stop_visibility"],
                    continuation_prompt=f"All power-steering checks passed! Please present these results to the user:\n{results_text}",
                    summary=None,
                    analysis=analysis,
                    # FIX (Issue #1744): Pass through calculated is_first_stop value
                    # This prevents infinite loop by allowing stop.py (line 132) to distinguish
                    # between first stop (display results) vs subsequent stops (don't block).
                    # Previously hardcoded to True, causing every stop to block indefinitely.
                    # NOTE: This was fixed in PR #1745; kept here for documentation.
                    is_first_stop=is_first_stop,
                )

            # SUBSEQUENT STOP: All checks passed, approve
            # 8. Generate summary and mark complete
            summary = self._generate_summary(transcript, analysis, session_id)
            self._mark_complete(session_id)
            self._write_summary(session_id, summary)

            # Reset turn state on approval
            if turn_state_manager and turn_state:
                turn_state = turn_state_manager.record_approval(turn_state)
                turn_state_manager.save_state(turn_state)

            # Emit completion event
            self._emit_progress(
                progress_callback,
                "complete",
                "Power-steering analysis complete - all checks passed",
            )

            result = PowerSteeringResult(
                decision="approve",
                reasons=["all_considerations_satisfied"],
                continuation_prompt=None,
                summary=summary,
                analysis=analysis,
                is_first_stop=False,
            )

            # Add evidence to result if available
            if hasattr(self, "_evidence_results"):
                result.evidence_results = self._evidence_results

            return result

        except Exception as e:
            # Fail-open: On any error, approve and log
            self._log(f"Power-steering error (fail-open): {e}", "ERROR")
            return PowerSteeringResult(
                decision="approve",
                reasons=["error_failopen"],
                continuation_prompt=None,
                summary=None,
            )

    def _evidence_suggests_complete(self, evidence_results: list) -> bool:
        """Check if concrete evidence suggests work is complete.

        Args:
            evidence_results: List of Evidence objects from Phase 1

        Returns:
            True if concrete evidence indicates completion
        """
        if not evidence_results:
            return False

        # Strong evidence types that indicate completion
        strong_evidence = [
            EvidenceType.PR_MERGED,
            EvidenceType.USER_CONFIRMATION,
            EvidenceType.CI_PASSING,
        ]

        # Check if any strong evidence is verified
        for evidence in evidence_results:
            if evidence.evidence_type in strong_evidence and evidence.verified:
                return True

        # Check if multiple medium evidence types are verified
        verified_count = sum(1 for e in evidence_results if e.verified)

        # If 3+ evidence types verified, trust concrete evidence
        return verified_count >= 3

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
            self._log(f"Pre-compaction transcript check failed: {e}", "WARNING")
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
            self._log(f"Failed to load pre-compaction transcript: {e}", "WARNING")
            return []

    def _verify_actual_state(self, session_id: str) -> dict[str, Any]:
        """Verify work completion by checking actual git/GitHub state.

        This provides ground truth verification independent of transcript analysis.
        Used as robust fallback when session has been compacted (Issue #1962).

        Args:
            session_id: Session identifier

        Returns:
            Dict with verification results:
            - ci_passing: bool - All CI checks passed
            - pr_mergeable: bool - PR is in mergeable state
            - branch_current: bool - Branch is up to date with main
            - tests_local: bool - Local tests pass (if available)
            - all_passing: bool - All checks passed

        Note:
            Fail-open design: Returns False for individual checks on errors,
            but doesn't block overall verification.
        """
        import subprocess

        results = {
            "ci_passing": False,
            "pr_mergeable": False,
            "branch_current": False,
            "tests_local": None,  # None = not checked
            "all_passing": False,
            "details": {},
        }

        try:
            # 1. Check if there's an open PR for current branch
            pr_result = subprocess.run(
                ["gh", "pr", "view", "--json", "state,mergeable,statusCheckRollup"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.project_root),
            )

            if pr_result.returncode == 0:
                try:
                    pr_data = json.loads(pr_result.stdout)
                    results["details"]["pr_state"] = pr_data.get("state")
                    results["details"]["mergeable"] = pr_data.get("mergeable")

                    # Check PR is open and mergeable
                    if pr_data.get("state") == "OPEN":
                        results["pr_mergeable"] = pr_data.get("mergeable") == "MERGEABLE"

                        # Check CI status
                        status_checks = pr_data.get("statusCheckRollup", [])
                        if status_checks:
                            # All checks must pass
                            all_success = all(
                                check.get("conclusion") in ("SUCCESS", "NEUTRAL", "SKIPPED")
                                for check in status_checks
                                if check.get("conclusion")  # Ignore pending
                            )
                            # At least some checks must have run
                            has_completed = any(check.get("conclusion") for check in status_checks)
                            results["ci_passing"] = all_success and has_completed
                            results["details"]["ci_checks"] = len(status_checks)
                            results["details"]["ci_conclusions"] = [
                                check.get("conclusion") for check in status_checks
                            ]
                        else:
                            # No status checks configured - consider CI passing
                            results["ci_passing"] = True
                            results["details"]["ci_checks"] = 0

                except json.JSONDecodeError:
                    self._log("Failed to parse PR data", "WARNING")
            else:
                # No PR found - check if we're on main branch (might be direct work)
                results["details"]["no_pr"] = True

            # 2. Check if branch is up to date with main/master
            # Get commits behind main
            for main_branch in ["origin/main", "origin/master"]:
                behind_result = subprocess.run(
                    ["git", "rev-list", "--count", f"HEAD..{main_branch}"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    cwd=str(self.project_root),
                )
                if behind_result.returncode == 0:
                    commits_behind = int(behind_result.stdout.strip())
                    results["branch_current"] = commits_behind == 0
                    results["details"]["commits_behind"] = commits_behind
                    results["details"]["main_branch"] = main_branch
                    break

            # 3. Determine overall result
            # For state verification to pass, we need PR mergeable AND CI passing
            # (branch_current is informational but not blocking)
            if results.get("pr_mergeable") and results.get("ci_passing"):
                results["all_passing"] = True
            elif results.get("details", {}).get("no_pr"):
                # No PR - check if on main branch directly
                results["all_passing"] = results.get("branch_current", False)

            self._log(
                f"State verification: ci={results['ci_passing']}, "
                f"mergeable={results['pr_mergeable']}, current={results['branch_current']}",
                "INFO",
            )

        except subprocess.TimeoutExpired:
            self._log("State verification timed out", "WARNING")
        except FileNotFoundError:
            self._log("gh or git command not found for state verification", "WARNING")
        except Exception as e:
            self._log(f"State verification failed: {e}", "WARNING")

        return results

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
        semaphore = self.runtime_dir / f".{session_id}_results_shown"
        return semaphore.exists()

    def _mark_results_shown(self, session_id: str) -> None:
        """Create semaphore to indicate results have been shown.

        Called after displaying all consideration results on first stop.

        Args:
            session_id: Session identifier
        """
        try:
            semaphore = self.runtime_dir / f".{session_id}_results_shown"
            semaphore.parent.mkdir(parents=True, exist_ok=True)
            semaphore.touch()
            semaphore.chmod(0o600)  # Owner read/write only for security
        except OSError:
            pass  # Fail-open: Continue even if semaphore creation fails

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
            self._log(f"Failed to save redirect: {e}", "ERROR")

    def _load_transcript(self, transcript_path: Path) -> list[dict]:
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
        user_messages: list[dict],
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

    def _has_simple_task_keywords(self, transcript: list[dict]) -> bool:
        """Check user messages for simple housekeeping task keywords.

        Simple tasks like "cleanup workspace", "fetch latest", "git pull" should
        skip most power-steering checks as they are routine maintenance.

        Args:
            transcript: List of message dictionaries

        Returns:
            True if simple task keywords found in user messages
        """
        # Check first 3 user messages for simple task keywords
        user_messages = [m for m in transcript if m.get("type") == "user"][:3]

        if not user_messages:
            return False

        for msg in user_messages:
            content = str(msg.get("message", {}).get("content", "")).lower()

            # Check for simple task keywords
            for keyword in self.SIMPLE_TASK_KEYWORDS:
                if keyword in content:
                    self._log(
                        f"Simple task keyword '{keyword}' found in user message",
                        "DEBUG",
                    )
                    return True

        return False

    def _has_investigation_keywords(self, transcript: list[dict]) -> bool:
        """Check early user messages for investigation/troubleshooting keywords.

        This check takes PRIORITY over tool-based heuristics. If investigation
        keywords are found, the session is classified as INVESTIGATION regardless
        of what tools were used. This fixes #1604 where troubleshooting sessions
        were incorrectly blocked by development-specific checks.

        Args:
            transcript: List of message dictionaries

        Returns:
            True if investigation keywords found in early user messages
        """
        # Check first 5 user messages for investigation keywords
        user_messages = [m for m in transcript if m.get("type") == "user"][:5]

        if not user_messages:
            return False

        for msg in user_messages:
            content = str(msg.get("message", {}).get("content", "")).lower()

            # Check for investigation keywords
            for keyword in self.INVESTIGATION_KEYWORDS:
                if keyword in content:
                    self._log(
                        f"Investigation keyword '{keyword}' found in user message",
                        "DEBUG",
                    )
                    return True

        return False

    def detect_session_type(self, transcript: list[dict]) -> str:
        """Detect session type for selective consideration application.

        Session Types:
        - SIMPLE: Routine housekeeping tasks (cleanup, fetch, sync) - skip most checks
        - DEVELOPMENT: Code changes, tests, PR operations
        - INFORMATIONAL: Q&A, help queries, capability questions
        - MAINTENANCE: Documentation and configuration updates only
        - INVESTIGATION: Exploration, analysis, troubleshooting, and debugging

        Detection Priority:
        1. Environment override (AMPLIHACK_SESSION_TYPE)
        2. Simple task keywords (cleanup, fetch, workspace) - highest priority heuristic
        3. Investigation keywords in user messages
        4. Tool usage patterns (code changes, tests, etc.)

        The keyword detection takes priority over tool-based heuristics because
        troubleshooting sessions often involve Bash commands and doc updates,
        which can be misclassified as DEVELOPMENT or MAINTENANCE.

        Args:
            transcript: List of message dictionaries

        Returns:
            Session type string: "SIMPLE", "DEVELOPMENT", "INFORMATIONAL", "MAINTENANCE", or "INVESTIGATION"
        """
        # Check for environment override first
        env_override = os.getenv("AMPLIHACK_SESSION_TYPE", "").upper()
        if env_override in [
            "SIMPLE",
            "DEVELOPMENT",
            "INFORMATIONAL",
            "MAINTENANCE",
            "INVESTIGATION",
        ]:
            self._log(f"Session type overridden by environment: {env_override}", "INFO")
            return env_override

        # Empty transcript defaults to INFORMATIONAL (fail-open)
        if not transcript:
            return "INFORMATIONAL"

        # HIGHEST PRIORITY: Simple task keywords (cleanup, fetch, sync, workspace)
        # These routine maintenance tasks should skip most power-steering checks
        if self._has_simple_task_keywords(transcript):
            self._log("Session classified as SIMPLE via keyword detection", "INFO")
            return "SIMPLE"

        # PRIORITY CHECK: Investigation keywords in user messages
        # This takes precedence over tool-based heuristics (fixes #1604)
        if self._has_investigation_keywords(transcript):
            self._log("Session classified as INVESTIGATION via keyword detection", "INFO")
            return "INVESTIGATION"

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

    def get_applicable_considerations(self, session_type: str) -> list[dict[str, Any]]:
        """Get considerations applicable to a specific session type.

        Args:
            session_type: Session type ("SIMPLE", "DEVELOPMENT", "INFORMATIONAL", "MAINTENANCE", "INVESTIGATION")

        Returns:
            List of consideration dictionaries applicable to this session type
        """
        # SIMPLE sessions skip ALL considerations - they are routine maintenance tasks
        # like cleanup, fetch, sync, workspace management that don't need verification
        if session_type == "SIMPLE":
            self._log("SIMPLE session - skipping all considerations", "INFO")
            return []

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

    def _is_qa_session(self, transcript: list[dict]) -> bool:
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

    def _create_passing_analysis(
        self,
        original_analysis: ConsiderationAnalysis,
        addressed_concerns: dict[str, str],
    ) -> ConsiderationAnalysis:
        """Create a modified analysis with addressed blockers marked as satisfied.

        Used when all blockers were addressed in the current turn to convert
        a failing analysis to a passing one.

        Args:
            original_analysis: The original analysis with blockers
            addressed_concerns: Map of concern_id -> how it was addressed

        Returns:
            New ConsiderationAnalysis with blockers converted to satisfied
        """
        # Create a copy of results with addressed concerns marked satisfied
        modified_results = dict(original_analysis.results)

        for consideration_id, how_addressed in addressed_concerns.items():
            if consideration_id in modified_results:
                old_result = modified_results[consideration_id]
                modified_results[consideration_id] = CheckerResult(
                    consideration_id=consideration_id,
                    satisfied=True,
                    reason=f"{old_result.reason} [ADDRESSED: {how_addressed}]",
                    severity=old_result.severity,
                )

        # Create new analysis with modified results
        return ConsiderationAnalysis(results=modified_results)

    def _convert_to_failure_evidence(
        self,
        failed_results: list[CheckerResult],
        transcript: list[dict],
        user_claims: list[str] | None = None,
    ) -> list["FailureEvidence"]:
        """Convert CheckerResults to FailureEvidence with evidence quotes.

        Extracts specific evidence from the transcript to show WHY each
        check failed, enabling the agent to understand exactly what's missing.

        Args:
            failed_results: List of failed CheckerResult objects
            transcript: Full transcript for evidence extraction
            user_claims: User claims detected (to mark as was_claimed_complete)

        Returns:
            List of FailureEvidence objects with detailed evidence
        """
        if not TURN_STATE_AVAILABLE:
            return []

        evidence_list: list[FailureEvidence] = []
        claimed_ids = set()

        # Extract consideration IDs that were claimed as complete
        if user_claims:
            for claim in user_claims:
                claim_lower = claim.lower()
                for result in failed_results:
                    cid = result.consideration_id.lower()
                    # Simple heuristic: if claim mentions words from consideration ID
                    if any(word in claim_lower for word in cid.split("_") if len(word) > 2):
                        claimed_ids.add(result.consideration_id)

        for result in failed_results:
            # Try to find specific evidence quote from transcript
            quote = self._find_evidence_quote(result, transcript)

            evidence = FailureEvidence(
                consideration_id=result.consideration_id,
                reason=result.reason,
                evidence_quote=quote,
                was_claimed_complete=result.consideration_id in claimed_ids,
            )
            evidence_list.append(evidence)

        return evidence_list

    def _find_evidence_quote(
        self,
        result: CheckerResult,
        transcript: list[dict],
    ) -> str | None:
        """Find a specific quote from transcript showing why check failed.

        Searches for relevant context based on the consideration type to
        provide concrete evidence of what's missing or failing.

        Args:
            result: CheckerResult to find evidence for
            transcript: Full transcript to search

        Returns:
            Evidence quote string if found, None otherwise
        """
        cid = result.consideration_id.lower()

        # Define search patterns for each consideration type
        search_terms: dict[str, list[str]] = {
            "todos": ["todo", "task", "item", "remaining"],
            "testing": ["test", "pytest", "unittest", "failing", "error"],
            "ci": ["ci", "github actions", "pipeline", "build", "workflow"],
            "workflow": ["step", "workflow", "phase"],
            "review": ["review", "feedback", "comment"],
            "philosophy": ["philosophy", "simplicity", "stub", "placeholder"],
            "docs": ["documentation", "readme", "doc"],
        }

        # Find which search terms apply to this consideration
        relevant_terms = []
        for key, terms in search_terms.items():
            if key in cid:
                relevant_terms.extend(terms)

        if not relevant_terms:
            return None

        # Search recent transcript for relevant content
        recent_messages = transcript[-20:] if len(transcript) > 20 else transcript

        for msg in reversed(recent_messages):
            content = self._extract_message_text(msg).lower()

            for term in relevant_terms:
                if term in content:
                    # Found relevant content - extract context
                    idx = content.find(term)
                    start = max(0, idx - 30)
                    end = min(len(content), idx + len(term) + 70)

                    # Get original case text
                    original_content = self._extract_message_text(msg)
                    quote = original_content[start:end].strip()

                    if len(quote) > 10:  # Only return meaningful quotes
                        return f"...{quote}..."

        return None

    def _analyze_considerations(
        self,
        transcript: list[dict],
        session_id: str,
        session_type: str | None = None,
        progress_callback: Callable | None = None,
    ) -> ConsiderationAnalysis:
        """Analyze transcript against all enabled considerations IN PARALLEL.

        Phase 4 (Performance): Uses asyncio.gather() to run ALL SDK checks in parallel,
        reducing total time from ~220s (sequential) to ~15-20s (parallel).

        Key design decisions:
        - Transcript is loaded ONCE upfront, shared across all parallel workers
        - ALL checks run - no early exit - for comprehensive feedback
        - No caching - session-specific analysis doesn't benefit from caching
        - Fail-open: Any errors result in "satisfied" to never block users

        Args:
            transcript: List of message dictionaries (PRE-LOADED, not fetched by workers)
            session_id: Session identifier
            session_type: Session type for selective consideration application (auto-detected if None)
            progress_callback: Optional callback for progress events

        Returns:
            ConsiderationAnalysis with results from ALL considerations
        """
        # Auto-detect session type if not provided
        if session_type is None:
            session_type = self.detect_session_type(transcript)
            self._log(f"Auto-detected session type: {session_type}", "DEBUG")

        # Get considerations applicable to this session type
        applicable_considerations = self.get_applicable_considerations(session_type)

        # Filter to enabled considerations only
        enabled_considerations = []
        for consideration in applicable_considerations:
            # Check if enabled in consideration itself
            if not consideration.get("enabled", True):
                continue
            # Also check config for backward compatibility
            if not self.config.get("checkers_enabled", {}).get(consideration["id"], True):
                continue
            enabled_considerations.append(consideration)

        # Emit progress for all categories upfront
        categories = set(c.get("category", "Unknown") for c in enabled_considerations)
        for category in categories:
            self._emit_progress(
                progress_callback,
                "category",
                f"Checking {category}",
                {"category": category},
            )

        # Emit progress for parallel execution start
        self._emit_progress(
            progress_callback,
            "parallel_start",
            f"Running {len(enabled_considerations)} checks in parallel...",
            {"count": len(enabled_considerations)},
        )

        # Run all considerations in parallel using asyncio
        try:
            # Use asyncio.run() to execute the parallel async method
            # This is the single event loop for all parallel checks
            start_time = datetime.now()

            analysis = asyncio.run(
                self._analyze_considerations_parallel_async(
                    transcript=transcript,
                    session_id=session_id,
                    enabled_considerations=enabled_considerations,
                    progress_callback=progress_callback,
                )
            )

            elapsed = (datetime.now() - start_time).total_seconds()
            self._log(
                f"Parallel analysis completed: {len(enabled_considerations)} checks in {elapsed:.1f}s",
                "INFO",
            )
            self._emit_progress(
                progress_callback,
                "parallel_complete",
                f"Completed {len(enabled_considerations)} checks in {elapsed:.1f}s",
                {"count": len(enabled_considerations), "elapsed_seconds": elapsed},
            )

            return analysis

        except Exception as e:
            # Fail-open: On any error with parallel execution, return empty analysis
            self._log(f"Parallel analysis failed (fail-open): {e}", "ERROR")
            return ConsiderationAnalysis()

    async def _analyze_considerations_parallel_async(
        self,
        transcript: list[dict],
        session_id: str,
        enabled_considerations: list[dict[str, Any]],
        progress_callback: Callable | None = None,
    ) -> ConsiderationAnalysis:
        """Async implementation that runs ALL considerations in parallel.

        Args:
            transcript: Pre-loaded transcript (shared across all workers)
            session_id: Session identifier
            enabled_considerations: List of enabled consideration dictionaries
            progress_callback: Optional callback for progress events

        Returns:
            ConsiderationAnalysis with results from all considerations
        """
        analysis = ConsiderationAnalysis()

        # Create async tasks for ALL considerations
        # Each task receives the SAME transcript (no re-fetching)
        tasks = [
            self._check_single_consideration_async(
                consideration=consideration,
                transcript=transcript,
                session_id=session_id,
            )
            for consideration in enabled_considerations
        ]

        # Run ALL tasks in parallel with overall timeout
        # return_exceptions=True ensures all tasks complete even if some fail
        try:
            async with asyncio.timeout(PARALLEL_TIMEOUT):
                results = await asyncio.gather(*tasks, return_exceptions=True)
        except TimeoutError:
            self._log(f"Parallel execution timed out after {PARALLEL_TIMEOUT}s", "WARNING")
            # Fail-open: Return empty analysis on timeout
            return analysis

        # Process results from all parallel tasks
        for consideration, result in zip(enabled_considerations, results, strict=False):
            if isinstance(result, Exception):
                # Task raised an exception - fail-open
                self._log(
                    f"Check '{consideration['id']}' failed with exception: {result}",
                    "WARNING",
                )
                checker_result = CheckerResult(
                    consideration_id=consideration["id"],
                    satisfied=True,  # Fail-open
                    reason=f"Error: {result}",
                    severity=consideration["severity"],
                )
            elif isinstance(result, CheckerResult):
                # Normal result
                checker_result = result
            else:
                # Unexpected result type - fail-open
                self._log(
                    f"Check '{consideration['id']}' returned unexpected type: {type(result)}",
                    "WARNING",
                )
                checker_result = CheckerResult(
                    consideration_id=consideration["id"],
                    satisfied=True,  # Fail-open
                    reason="Unexpected result type",
                    severity=consideration["severity"],
                )

            analysis.add_result(checker_result)

            # Emit individual result progress
            self._emit_progress(
                progress_callback,
                "consideration_result",
                f"{'✓' if checker_result.satisfied else '✗'} {consideration['question']}",
                {
                    "consideration_id": consideration["id"],
                    "satisfied": checker_result.satisfied,
                    "question": consideration["question"],
                },
            )

        return analysis

    async def _check_single_consideration_async(
        self,
        consideration: dict[str, Any],
        transcript: list[dict],
        session_id: str,
    ) -> CheckerResult:
        """Check a single consideration asynchronously.

        Phase 5 (SDK-First): Use Claude SDK as PRIMARY method
        - ALL considerations analyzed by SDK first (when available)
        - Specific checkers (_check_*) used ONLY as fallback
        - Fail-open when SDK unavailable or fails

        This is the parallel worker that handles one consideration.
        The transcript is already loaded - this method does NOT fetch it.

        Args:
            consideration: Consideration dictionary
            transcript: Pre-loaded transcript (shared, not fetched)
            session_id: Session identifier

        Returns:
            CheckerResult with satisfaction status
        """
        try:
            # SDK-FIRST: Try SDK for ALL considerations (when available)
            if SDK_AVAILABLE:
                try:
                    # Use async SDK function directly (already awaitable)
                    # Returns tuple: (satisfied, reason)
                    satisfied, sdk_reason = await analyze_consideration(
                        conversation=transcript,
                        consideration=consideration,
                        project_root=self.project_root,
                    )

                    # SDK succeeded - return result with SDK-provided reason
                    return CheckerResult(
                        consideration_id=consideration["id"],
                        satisfied=satisfied,
                        reason=(
                            "SDK analysis: satisfied"
                            if satisfied
                            else f"SDK analysis: {sdk_reason or consideration['question'] + ' not met'}"
                        ),
                        severity=consideration["severity"],
                    )
                except Exception as e:
                    # SDK failed - log to stderr and fall through to fallback
                    import sys

                    error_msg = f"[Power Steering SDK Error] {consideration['id']}: {e!s}\n"
                    sys.stderr.write(error_msg)
                    sys.stderr.flush()

                    self._log(
                        f"SDK analysis failed for '{consideration['id']}': {e}",
                        "DEBUG",
                    )
                    # Continue to fallback methods below

            # FALLBACK: Use heuristic checkers when SDK unavailable or failed
            checker_name = consideration["checker"]

            # Dispatch to specific checker or generic analyzer
            if hasattr(self, checker_name) and callable(getattr(self, checker_name)):
                checker_func = getattr(self, checker_name)
                satisfied = checker_func(transcript, session_id)
            else:
                # Generic analyzer for considerations without specific checker
                satisfied = self._generic_analyzer(transcript, session_id, consideration)

            return CheckerResult(
                consideration_id=consideration["id"],
                satisfied=satisfied,
                reason=(f"Heuristic fallback: {'satisfied' if satisfied else 'not met'}"),
                severity=consideration["severity"],
            )

        except Exception as e:
            # Fail-open: Never block on errors
            self._log(
                f"Checker error for '{consideration['id']}': {e}",
                "WARNING",
            )
            return CheckerResult(
                consideration_id=consideration["id"],
                satisfied=True,  # Fail-open
                reason=f"Error (fail-open): {e}",
                severity=consideration["severity"],
            )

    def _format_results_text(self, analysis: ConsiderationAnalysis, session_type: str) -> str:
        """Format analysis results as text for inclusion in continuation_prompt.

        This allows users to see results even when stderr isn't visible.

        Note on message branches: This method handles three cases:
        1. Some checks passed → "ALL CHECKS PASSED"
        2. No checks ran (all skipped) → "NO CHECKS APPLICABLE"
        3. Some checks failed → "CHECKS FAILED"

        Case #2 is primarily for testing - in production, check() returns early
        (line 759) when len(analysis.results)==0, so this method won't be called.
        However, tests call this method directly to verify message formatting works.

        Args:
            analysis: ConsiderationAnalysis with results
            session_type: Session type (e.g., "SIMPLE", "STANDARD")

        Returns:
            Formatted text string with results grouped by category
        """
        lines = []
        lines.append("\n" + "=" * 60)
        lines.append("⚙️  POWER-STEERING ANALYSIS RESULTS")
        lines.append("=" * 60 + "\n")
        lines.append(f"Session Type: {session_type}\n")

        # Group results by category
        by_category: dict[str, list[tuple]] = {}
        for consideration in self.considerations:
            category = consideration.get("category", "Unknown")
            cid = consideration["id"]
            result = analysis.results.get(cid)

            if category not in by_category:
                by_category[category] = []

            by_category[category].append((consideration, result))

        # Display by category
        total_passed = 0
        total_failed = 0
        total_skipped = 0

        for category, items in sorted(by_category.items()):
            lines.append(f"📋 {category}")
            lines.append("-" * 40)

            for consideration, result in items:
                if result is None:
                    indicator = "⬜"  # Not checked (skipped)
                    total_skipped += 1
                elif result.satisfied:
                    indicator = "✅"
                    total_passed += 1
                else:
                    indicator = "❌"
                    total_failed += 1

                question = consideration.get("question", consideration["id"])
                severity = consideration.get("severity", "warning")
                severity_tag = " [blocker]" if severity == "blocker" else ""

                lines.append(f"  {indicator} {question}{severity_tag}")

            lines.append("")

        # Summary line
        lines.append("=" * 60)
        if total_failed == 0 and total_passed > 0:
            # Some checks passed and none failed
            self._log(
                f"Message branch: ALL_CHECKS_PASSED (passed={total_passed}, failed=0, skipped={total_skipped})",
                "DEBUG",
            )
            lines.append(f"✅ ALL CHECKS PASSED ({total_passed} passed, {total_skipped} skipped)")
            lines.append("\n📌 This was your first stop. Next stop will proceed without blocking.")
            lines.append("\n💡 To disable power-steering: export AMPLIHACK_SKIP_POWER_STEERING=1")
            lines.append("   Or create: .claude/runtime/power-steering/.disabled")
        elif total_failed == 0 and total_passed == 0:
            # No checks were evaluated (all skipped) - not a "pass", just no applicable checks
            self._log(
                f"Message branch: NO_CHECKS_APPLICABLE (passed=0, failed=0, skipped={total_skipped})",
                "DEBUG",
            )
            lines.append(f"⚠️  NO CHECKS APPLICABLE ({total_skipped} skipped for session type)")
            lines.append("\n📌 No power-steering checks apply to this session type.")
            lines.append("   This is expected for simple Q&A or informational sessions.")
        else:
            # Some checks failed
            self._log(
                f"Message branch: CHECKS_FAILED (passed={total_passed}, failed={total_failed}, skipped={total_skipped})",
                "DEBUG",
            )
            lines.append(
                f"❌ CHECKS FAILED ({total_passed} passed, {total_failed} failed, {total_skipped} skipped)"
            )
            lines.append("\n📌 Address the failed checks above before stopping.")
        lines.append("=" * 60 + "\n")

        return "\n".join(lines)

    # ========================================================================
    # Phase 1: Top 5 Critical Checkers
    # ========================================================================

    def _check_todos_complete(self, transcript: list[dict], session_id: str) -> bool:
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

    def _extract_incomplete_todos(self, transcript: list[dict]) -> list[str]:
        """Extract list of incomplete todo items from transcript.

        Helper method used by continuation prompt generation to show
        specific items the agent needs to complete.

        Args:
            transcript: List of message dictionaries

        Returns:
            List of incomplete todo item descriptions
        """
        incomplete_todos = []

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

        if not last_todo_write:
            return []

        todos = last_todo_write.get("todos", [])
        for todo in todos:
            status = todo.get("status", "pending")
            if status != "completed":
                content = todo.get("content", "Unknown task")
                incomplete_todos.append(f"[{status}] {content}")

        return incomplete_todos

    def _extract_next_steps_mentioned(self, transcript: list[dict]) -> list[str]:
        """Extract specific next steps mentioned in recent assistant messages.

        Helper method used by continuation prompt generation to show
        specific next steps the agent mentioned but hasn't completed.

        Args:
            transcript: List of message dictionaries

        Returns:
            List of next step descriptions (extracted sentences/phrases)
        """
        next_steps = []
        next_steps_triggers = [
            "next step",
            "next steps",
            "follow-up",
            "remaining",
            "still need",
            "todo",
            "left to",
        ]

        # Check recent assistant messages
        recent_messages = [m for m in transcript[-15:] if m.get("type") == "assistant"][-5:]

        for msg in recent_messages:
            content = msg.get("message", {}).get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = str(block.get("text", ""))
                        text_lower = text.lower()

                        # Check if this block mentions next steps
                        if any(trigger in text_lower for trigger in next_steps_triggers):
                            # Extract sentences containing the trigger
                            sentences = text.replace("\n", " ").split(". ")
                            for sentence in sentences:
                                sentence_lower = sentence.lower()
                                if any(
                                    trigger in sentence_lower for trigger in next_steps_triggers
                                ):
                                    clean_sentence = sentence.strip()
                                    if clean_sentence and len(clean_sentence) > 10:
                                        # Truncate long sentences
                                        if len(clean_sentence) > 150:
                                            clean_sentence = clean_sentence[:147] + "..."
                                        if clean_sentence not in next_steps:
                                            next_steps.append(clean_sentence)

        return next_steps[:5]  # Limit to 5 items

    def _check_workflow_invocation(self, transcript: list[dict], session_id: str) -> bool:
        """Check if workflow was properly invoked via Skill or Read tool.

        Validates that when ultrathink-orchestrator is triggered, the appropriate
        workflow skill is invoked using Skill tool or Read tool fallback.

        Issue #2040: Enforce workflow invocation compliance

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if workflow properly invoked or not required, False otherwise
        """
        try:
            # Import validator
            from workflow_invocation_validator import validate_workflow_invocation

            # Convert transcript to string format for validator
            transcript_text = self._transcript_to_text(transcript)

            # Determine session type from state if available
            session_type = "DEVELOPMENT"  # Default
            try:
                state_file = self.runtime_dir / session_id / "turn_state.json"
                if state_file.exists():
                    state = json.loads(state_file.read_text())
                    session_type = state.get("session_type", "DEVELOPMENT")
            except Exception:
                pass  # Use default

            # Validate workflow invocation
            result = validate_workflow_invocation(transcript_text, session_type)

            if not result.valid:
                # Log violation details
                self._log_violation(
                    "workflow_invocation",
                    {
                        "reason": result.reason,
                        "violation_type": result.violation_type,
                        "evidence": result.evidence,
                        "session_type": session_type,
                    },
                    session_id,
                )

            return result.valid

        except ImportError:
            # Validator not available - fail open
            import sys

            sys.stderr.write(
                "[Power Steering] workflow_invocation_validator not found, skipping check\n"
            )
            return True
        except Exception as e:
            # Fail-open on errors
            import sys

            sys.stderr.write(f"[Power Steering] Error in _check_workflow_invocation: {e}\n")
            return True

    def _transcript_to_text(self, transcript: list[dict]) -> str:
        """Convert transcript list to plain text for pattern matching.

        Args:
            transcript: List of message dictionaries

        Returns:
            Plain text representation of transcript
        """
        lines = []
        for msg in transcript:
            role = msg.get("type", "unknown")
            if role == "user":
                lines.append(f"User: {self._extract_message_text(msg)}")
            elif role == "assistant":
                lines.append(f"Claude: {self._extract_message_text(msg)}")
        return "\n".join(lines)

    def _extract_message_text(self, msg: dict) -> str:
        """Extract text content from message.

        Args:
            msg: Message dictionary

        Returns:
            Text content
        """
        message = msg.get("message", {})
        content = message.get("content", [])

        if isinstance(content, str):
            return content

        if isinstance(content, list):
            texts = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        texts.append(block.get("text", ""))
                    elif block.get("type") == "tool_use":
                        # Include tool invocations in text
                        tool_name = block.get("name", "")
                        tool_input = block.get("input", {})
                        texts.append(f'<invoke name="{tool_name}">{tool_input}')
            return " ".join(texts)

        return ""

    def _log_violation(self, consideration_id: str, details: dict, session_id: str) -> None:
        """Log violation details to session logs.

        Args:
            consideration_id: ID of failed consideration
            details: Violation details
            session_id: Session identifier
        """
        try:
            log_file = self.runtime_dir / session_id / "violations.json"
            log_file.parent.mkdir(parents=True, exist_ok=True)

            violations = []
            if log_file.exists():
                violations = json.loads(log_file.read_text())

            violations.append(
                {
                    "consideration_id": consideration_id,
                    "timestamp": datetime.now().isoformat(),
                    "details": details,
                }
            )

            log_file.write_text(json.dumps(violations, indent=2))
        except Exception:
            pass  # Fail silently

    def _check_dev_workflow_complete(self, transcript: list[dict], session_id: str) -> bool:
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

    def _check_philosophy_compliance(self, transcript: list[dict], session_id: str) -> bool:
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

    def _check_local_testing(self, transcript: list[dict], session_id: str) -> bool:
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

    def _user_prefers_no_auto_merge(self) -> bool:
        """Detect if user has set preference to never auto-merge PRs.

        Searches .claude/context/USER_PREFERENCES.md for pattern:
        "(never|must not|do not|don't) ... merge ... without ... (permission|approval|explicit)"

        Returns:
            True if preference detected, False otherwise (fail-open on any error)
        """
        try:
            preferences_path = self.project_root / ".claude" / "context" / "USER_PREFERENCES.md"

            if not preferences_path.exists():
                return False

            content = preferences_path.read_text(encoding="utf-8")

            # Pattern: (never|must not|do not|don't).*merge.*without.*(permission|approval|explicit)
            pattern = r"(?i)(never|must not|do not|don\'t).*merge.*without.*(permission|approval|explicit)"

            return re.search(pattern, content, re.DOTALL) is not None

        except Exception as e:
            # Fail-open: any error returns False
            self._log(f"Error detecting merge preference: {e}", "WARNING")
            return False

    def _check_ci_status_no_auto_merge(self, transcript: list[dict]) -> bool:
        """Check CI status WITHOUT requiring PR merge.

        Used when user preference "never merge without permission" is active.
        Treats "PR ready + CI passing" as valid completion state.

        Args:
            transcript: List of message dictionaries

        Returns:
            True if PR ready and CI passing, False if CI failing or draft PR
        """
        # Look for PR and CI indicators
        pr_mentioned = False
        ci_mentioned = False
        ci_passing = False
        is_draft = False

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                text = str(block.get("text", "")).lower()

                                # Check for PR mentions
                                if any(
                                    keyword in text
                                    for keyword in ["pr #", "pull request", "created pr"]
                                ):
                                    pr_mentioned = True

                                # Check for draft PR
                                if "draft" in text and "pr" in text:
                                    is_draft = True

                                # Check for CI mentions
                                if any(
                                    keyword in text
                                    for keyword in [
                                        "ci",
                                        "github actions",
                                        "continuous integration",
                                        "checks",
                                    ]
                                ):
                                    ci_mentioned = True

                                    # Check for passing indicators
                                    if any(
                                        keyword in text
                                        for keyword in [
                                            "passing",
                                            "passed",
                                            "success",
                                            "ready for review",
                                            "ready for your review",
                                        ]
                                    ):
                                        ci_passing = True

                                    # Check for failing indicators
                                    if any(
                                        keyword in text
                                        for keyword in ["failing", "failed", "error"]
                                    ):
                                        return False

        # If draft PR, not ready
        if is_draft:
            return False

        # If CI mentioned and failing, return False
        if ci_mentioned and not ci_passing:
            return False

        # If PR mentioned with CI passing, or PR ready indicators
        if pr_mentioned and (ci_passing or not ci_mentioned):
            return True

        # If neither PR nor CI mentioned, assume satisfied (fail-open)
        if not pr_mentioned and not ci_mentioned:
            return True

        # Default: if we have indicators but unclear state, be conservative
        return ci_passing or not ci_mentioned

    def _check_ci_status(self, transcript: list[dict], session_id: str) -> bool:
        """Check if CI passing/mergeable (preference-aware).

        This method delegates to the appropriate CI checker based on user preference:
        - If user prefers no auto-merge: use _check_ci_status_no_auto_merge()
        - Otherwise: use standard CI check logic (requires merge indicators)

        Heuristics (standard mode):
        - Look for CI status checks (gh pr view, CI commands)
        - Check for "passing", "success", "mergeable" (strict - requires "mergeable")
        - Look for failure indicators

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if CI passing or not applicable, False if CI failing
        """
        # Check user preference first (lazy detection)
        if self._user_prefers_no_auto_merge():
            return self._check_ci_status_no_auto_merge(transcript)

        # Standard logic for users without preference (strict - requires "mergeable")
        ci_mentioned = False
        mergeable_mentioned = False

        for msg in transcript:
            if msg.get("type") == "assistant" and "message" in msg:
                content = msg["message"].get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            # Check text content for CI mentions
                            if block.get("type") == "text":
                                text = str(block.get("text", ""))
                                text_lower = text.lower()

                                if any(
                                    keyword in text_lower
                                    for keyword in [
                                        "ci",
                                        "github actions",
                                        "continuous integration",
                                    ]
                                ):
                                    ci_mentioned = True

                                # Standard mode: only accept explicit "mergeable" or "passing" + "mergeable"
                                # Don't accept just "ready" or "passing" alone
                                if "mergeable" in text_lower:
                                    mergeable_mentioned = True

                                # Check for failure indicators
                                if any(
                                    keyword in text_lower
                                    for keyword in ["failing", "failed", "error"]
                                ):
                                    return False

        # If CI not mentioned, consider satisfied (not applicable)
        if not ci_mentioned:
            return True

        # Standard mode requires explicit "mergeable" indicator
        return mergeable_mentioned

    # ========================================================================
    # Phase 2: Additional Checkers (16 new methods)
    # ========================================================================

    def _generic_analyzer(
        self, transcript: list[dict], session_id: str, consideration: dict[str, Any]
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

    def _check_agent_unnecessary_questions(self, transcript: list[dict], session_id: str) -> bool:
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

    def _check_objective_completion(self, transcript: list[dict], session_id: str) -> bool:
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

    def _check_documentation_updates(self, transcript: list[dict], session_id: str) -> bool:
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

    def _check_tutorial_needed(self, transcript: list[dict], session_id: str) -> bool:
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

    def _check_presentation_needed(self, transcript: list[dict], session_id: str) -> bool:
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

    def _check_feature_docs_discoverable(self, transcript: list[dict], session_id: str) -> bool:
        """Check if feature documentation is discoverable from multiple paths.

        Verifies new features have documentation discoverable from README and docs/ directory.
        This ensures users can find documentation through:
        1. README features/documentation section
        2. docs/ directory listing

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if docs are discoverable or not applicable, False if missing navigation
        """
        try:
            # Phase 1: Detect new features
            # Look for new commands, agents, skills, scenarios in Write/Edit operations
            new_features = []
            docs_file = None

            for msg in transcript:
                if msg.get("type") == "assistant" and "message" in msg:
                    content = msg["message"].get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                tool_name = block.get("name", "")
                                if tool_name in ["Write", "Edit"]:
                                    file_path = block.get("input", {}).get("file_path", "")

                                    # Detect new feature by file location
                                    if ".claude/commands/" in file_path and file_path.endswith(
                                        ".md"
                                    ):
                                        new_features.append(("command", file_path))
                                    elif ".claude/agents/" in file_path and file_path.endswith(
                                        ".md"
                                    ):
                                        new_features.append(("agent", file_path))
                                    elif ".claude/skills/" in file_path:
                                        new_features.append(("skill", file_path))
                                    elif ".claude/scenarios/" in file_path:
                                        new_features.append(("scenario", file_path))

                                    # Track docs file creation in docs/
                                    if "docs/" in file_path and file_path.endswith(".md"):
                                        docs_file = file_path

            # Edge case 1: No new features detected
            if not new_features:
                return True

            # Edge case 2: Docs-only session (no code files modified)
            if self._is_docs_only_session(transcript):
                return True

            # Edge case 3: Internal changes (tools/, tests/, etc.)
            # If all features are in internal paths, pass
            internal_paths = [".claude/tools/", "tests/", ".claude/runtime/"]
            all_internal = all(
                any(internal in feature[1] for internal in internal_paths)
                for feature in new_features
            )
            if all_internal:
                return True

            # Phase 2: Check for docs file in docs/ directory
            if not docs_file:
                return False  # New feature but no docs file created

            # Phase 3: Verify 2+ navigation paths in README
            readme_paths_count = 0

            for msg in transcript:
                if msg.get("type") == "assistant" and "message" in msg:
                    content = msg["message"].get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                tool_name = block.get("name", "")
                                if tool_name in ["Write", "Edit"]:
                                    file_path = block.get("input", {}).get("file_path", "")

                                    # Check if README was edited
                                    if "README.md" in file_path.lower():
                                        # Get the new content to check for documentation links
                                        new_string = block.get("input", {}).get("new_string", "")
                                        content_to_check = block.get("input", {}).get("content", "")
                                        full_content = new_string or content_to_check

                                        # Count references to the docs file
                                        if docs_file and full_content:
                                            # Extract just the filename from the path
                                            doc_filename = docs_file.split("/")[-1]
                                            # Count occurrences of the doc filename in README content
                                            readme_paths_count += full_content.count(doc_filename)

            # Need at least 2 navigation paths (e.g., Features section + Documentation section)
            if readme_paths_count < 2:
                return False

            # All checks passed
            return True

        except Exception:
            # Fail-open: Return True on errors to avoid blocking users
            return True

    def _is_docs_only_session(self, transcript: list[dict]) -> bool:
        """Check if session only modified documentation files.

        Helper method to detect docs-only sessions where no code files were touched.

        Args:
            transcript: List of message dictionaries

        Returns:
            True if only .md files were modified, False if code files modified
        """
        try:
            code_modified = False
            docs_modified = False

            for msg in transcript:
                if msg.get("type") == "assistant" and "message" in msg:
                    content = msg["message"].get("content", [])
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "tool_use":
                                tool_name = block.get("name", "")
                                if tool_name in ["Write", "Edit"]:
                                    file_path = block.get("input", {}).get("file_path", "")

                                    # Check for code files using class constant
                                    if any(ext in file_path for ext in self.CODE_FILE_EXTENSIONS):
                                        code_modified = True

                                    # Check for doc files using class constant
                                    if any(ext in file_path for ext in self.DOC_FILE_EXTENSIONS):
                                        docs_modified = True

            # Docs-only session if docs modified but no code files
            return docs_modified and not code_modified

        except Exception:
            # Fail-open: Return False on errors (assume code might be modified)
            return False

    def _check_next_steps(self, transcript: list[dict], session_id: str) -> bool:
        """Check that work is complete with NO remaining next steps.

        INVERTED LOGIC: If the agent mentions "next steps", "remaining work", or
        similar phrases in their final messages, that means they're acknowledging
        there's MORE work to do. This check FAILS when next steps are found,
        prompting the agent to continue working until no next steps remain.

        Args:
            transcript: List of message dictionaries
            session_id: Session identifier

        Returns:
            True if NO next steps found (work is complete)
            False if next steps ARE found (work is incomplete - should continue)
        """
        # Keywords that indicate incomplete work
        incomplete_work_keywords = [
            "next steps",
            "next step",
            "follow-up",
            "follow up",
            "future work",
            "remaining work",
            "remaining tasks",
            "still need to",
            "still needs to",
            "todo",
            "to-do",
            "to do",
            "left to do",
            "more to do",
            "additional work",
            "further work",
            "outstanding",
            "not yet complete",
            "not yet done",
            "incomplete",
            "pending",
            "planned for later",
            "deferred",
        ]

        # Check RECENT assistant messages (last 10) for incomplete work indicators
        # These are where the agent would summarize before stopping
        recent_messages = [m for m in transcript[-20:] if m.get("type") == "assistant"][-10:]

        for msg in reversed(recent_messages):
            content = msg.get("message", {}).get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = str(block.get("text", "")).lower()
                        for keyword in incomplete_work_keywords:
                            if keyword in text:
                                self._log(
                                    f"Incomplete work indicator found: '{keyword}' - agent should continue",
                                    "INFO",
                                )
                                return False  # Work is INCOMPLETE

        # No incomplete work indicators found - work is complete
        return True

    def _check_docs_organization(self, transcript: list[dict], session_id: str) -> bool:
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

    def _check_investigation_docs(self, transcript: list[dict], session_id: str) -> bool:
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

    def _check_shortcuts(self, transcript: list[dict], session_id: str) -> bool:
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

    def _check_interactive_testing(self, transcript: list[dict], session_id: str) -> bool:
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

    def _check_unrelated_changes(self, transcript: list[dict], session_id: str) -> bool:
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

    def _check_root_pollution(self, transcript: list[dict], session_id: str) -> bool:
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

    def _check_pr_description(self, transcript: list[dict], session_id: str) -> bool:
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

    def _check_review_responses(self, transcript: list[dict], session_id: str) -> bool:
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

    def _check_branch_rebase(self, transcript: list[dict], session_id: str) -> bool:
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

    def _check_ci_precommit_mismatch(self, transcript: list[dict], session_id: str) -> bool:
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
        progress_callback: Callable | None,
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
            self._log(f"Progress callback error: {e}", "WARNING")

    # ========================================================================
    # Output Generation
    # ========================================================================

    def _generate_continuation_prompt(
        self,
        analysis: ConsiderationAnalysis,
        transcript: list[dict] | None = None,
        turn_state: Optional["PowerSteeringTurnState"] = None,
        addressed_concerns: dict[str, str] | None = None,
        user_claims: list[str] | None = None,
    ) -> str:
        """Generate actionable continuation prompt with turn-awareness and evidence.

        Enhanced to show:
        - Specific incomplete TODO items that need completion
        - Specific "next steps" mentioned that indicate incomplete work
        - User claims vs actual evidence gap
        - Persistent failures across blocks
        - Escalating severity on repeated blocks

        Args:
            analysis: Analysis results with failed considerations
            transcript: Optional transcript for extracting specific incomplete items
            turn_state: Optional turn state for turn-aware prompting
            addressed_concerns: Optional dict of concerns addressed in this turn
            user_claims: Optional list of completion claims detected from user/agent

        Returns:
            Formatted continuation prompt with evidence and turn information
        """
        blocks = turn_state.consecutive_blocks if turn_state else 1
        threshold = PowerSteeringTurnState.MAX_CONSECUTIVE_BLOCKS if TURN_STATE_AVAILABLE else 10

        # Extract specific incomplete items for detailed guidance
        incomplete_todos = []
        next_steps_mentioned = []
        if transcript:
            incomplete_todos = self._extract_incomplete_todos(transcript)
            next_steps_mentioned = self._extract_next_steps_mentioned(transcript)

        # Escalating tone based on block count
        if blocks == 1:
            severity_header = "First check"
        elif blocks <= threshold // 2:
            severity_header = f"Block {blocks}/{threshold}"
        else:
            severity_header = (
                f"**CRITICAL: Block {blocks}/{threshold}** - Auto-approval approaching"
            )

        prompt_parts = [
            "",
            "=" * 60,
            f"POWER-STEERING Analysis - {severity_header}",
            "=" * 60,
            "",
        ]

        # CRITICAL: Show specific incomplete items that MUST be completed
        if incomplete_todos or next_steps_mentioned:
            prompt_parts.append("**INCOMPLETE WORK DETECTED - YOU MUST CONTINUE:**")
            prompt_parts.append("")

            if incomplete_todos:
                prompt_parts.append("**Incomplete TODO Items** (you MUST complete these):")
                for todo in incomplete_todos:
                    prompt_parts.append(f"  • {todo}")
                prompt_parts.append("")

            if next_steps_mentioned:
                prompt_parts.append("**Next Steps You Mentioned** (you MUST complete these):")
                for step in next_steps_mentioned:
                    prompt_parts.append(f"  • {step}")
                prompt_parts.append("")

            prompt_parts.append(
                "**ACTION REQUIRED**: Continue working on the items above. "
                "Do NOT stop until ALL todos are completed and NO next steps remain."
            )
            prompt_parts.append("")

        # Show progress if addressing concerns
        if addressed_concerns:
            prompt_parts.append("**Progress Since Last Block** (recognized from your actions):")
            for concern_id, how_addressed in addressed_concerns.items():
                prompt_parts.append(f"  + {concern_id}: {how_addressed}")
            prompt_parts.append("")

        # Show user claims vs evidence gap
        if user_claims:
            prompt_parts.append("**Completion Claims Detected:**")
            prompt_parts.append("You or Claude claimed the following:")
            for claim in user_claims[:3]:  # Limit to 3 claims
                prompt_parts.append(f"  - {claim[:100]}...")  # Truncate long claims
            prompt_parts.append("")
            prompt_parts.append(
                "**However, the checks below still failed.** "
                "Please provide specific evidence these checks pass, or complete the remaining work."
            )
            prompt_parts.append("")

        # Show persistent failures if repeated blocks
        if turn_state and blocks > 1:
            persistent = turn_state.get_persistent_failures()
            repeatedly_failed = {k: v for k, v in persistent.items() if v > 1}

            if repeatedly_failed:
                prompt_parts.append("**Persistent Issues** (failed multiple times):")
                for cid, count in sorted(repeatedly_failed.items(), key=lambda x: -x[1]):
                    prompt_parts.append(f"  - {cid}: Failed {count} times")
                prompt_parts.append("")
                prompt_parts.append("These issues require immediate attention.")
                prompt_parts.append("")

        # Show current failures grouped by category with evidence
        prompt_parts.append("**Current Failures:**")
        prompt_parts.append("")

        by_category = analysis.group_by_category()

        for category, failed in by_category.items():
            # Filter out addressed concerns
            remaining_failures = [
                r
                for r in failed
                if not addressed_concerns or r.consideration_id not in addressed_concerns
            ]
            if remaining_failures:
                prompt_parts.append(f"### {category}")
                for result in remaining_failures:
                    prompt_parts.append(f"  - **{result.consideration_id}**: {result.reason}")

                    # Show evidence if available from turn state
                    if turn_state and turn_state.block_history:
                        current_block = turn_state.get_previous_block()
                        if current_block:
                            for ev in current_block.failed_evidence:
                                if ev.consideration_id == result.consideration_id:
                                    if ev.evidence_quote:
                                        prompt_parts.append(f"    Evidence: {ev.evidence_quote}")
                                    if ev.was_claimed_complete:
                                        prompt_parts.append(
                                            "    **Note**: This was claimed complete but check still fails"
                                        )
                prompt_parts.append("")

        # Call to action
        prompt_parts.append("**Next Steps:**")
        prompt_parts.append("1. Complete the failed checks listed above")
        prompt_parts.append("2. Provide specific evidence that checks now pass")
        remaining = threshold - blocks
        prompt_parts.append(f"3. Or continue working ({remaining} more blocks until auto-approval)")
        prompt_parts.append("")

        # Add acknowledgment hint if nearing auto-approve threshold
        if blocks >= threshold // 2:
            prompt_parts.append(
                "**Tip**: If checks are genuinely complete, say 'I acknowledge these concerns' "
                "or create SESSION_SUMMARY.md to indicate intentional completion."
            )
            prompt_parts.append("")

        prompt_parts.extend(
            [
                "To disable power-steering immediately:",
                "  mkdir -p .claude/runtime/power-steering && touch .claude/runtime/power-steering/.disabled",
            ]
        )

        return "\n".join(prompt_parts)

    def _generate_summary(
        self, transcript: list[dict], analysis: ConsiderationAnalysis, session_id: str
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
            summary_path = summary_dir / "summary.md"
            _write_with_retry(summary_path, summary, mode="w")
            summary_path.chmod(0o644)  # Owner read/write, others read
        except OSError:
            pass  # Fail-open: Continue even if summary writing fails

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
                self._log(f"Compaction validation error: {e}", "WARNING")
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
        except Exception:
            return True  # Fail-open

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
            self._log(f"Compaction validation error: {e}", "WARNING")
            return True  # Fail-open on errors

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

            # Use retry-enabled write for cloud sync resilience
            log_entry = f"[{timestamp}] {level}: {message}\n"
            _write_with_retry(log_file, log_entry, mode="a")

            # Set permissions on new files
            if is_new:
                log_file.chmod(0o600)  # Owner read/write only for security
        except OSError:
            pass  # Fail silently on logging errors


# ============================================================================
# Module Interface
# ============================================================================


def check_session(
    transcript_path: Path, session_id: str, project_root: Path | None = None
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
