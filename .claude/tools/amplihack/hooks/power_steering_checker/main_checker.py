#!/usr/bin/env python3
"""Power-Steering Mode: Main orchestrator class and module interface.

This module defines PowerSteeringChecker which inherits from all four
mixin classes, plus module-level interface functions.
"""

import json
import logging
import os
import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

# Package imports must be done relative to avoid issues when this module
# is the entry point
_hook_dir = str(Path(__file__).parent.parent)
if _hook_dir not in sys.path:
    sys.path.insert(0, _hook_dir)

# Import git utilities for worktree detection
try:
    from git_utils import get_shared_runtime_dir
except ImportError as e:
    print(f"FATAL: Required dependency missing: {e}", file=sys.stderr)
    raise


from .considerations import (
    CheckerResult,
    ConsiderationAnalysis,
    ConsiderationsMixin,
    PowerSteeringResult,
    _env_int,
)
from .transcript_parser import parse_transcript
from .progress_tracking import (
    MAX_LINE_BYTES,
    ProgressTrackingMixin,
    _validate_session_id,
)
from .result_formatting import (
    TURN_STATE_AVAILABLE,
    ResultFormattingMixin,
)
from .sdk_calls import (
    EVIDENCE_AVAILABLE,
    SDK_AVAILABLE,
    SdkCallsMixin,
    _timeout,
)

# Import turn-aware state management (needed by check() method directly)
try:
    from power_steering_state import (  # type: ignore[import-not-found]
        DeltaAnalysisResult,
        DeltaAnalyzer,
        PowerSteeringTurnState,
        TurnStateManager,
    )
    TURN_STATE_AVAILABLE = True
except ImportError:
    TURN_STATE_AVAILABLE = False
    print("WARNING: power_steering_state not available - turn-aware analysis disabled", file=sys.stderr)

# Import SDK functions needed by check() (analyze_claims_sync etc.)
try:
    from claude_power_steering import (  # type: ignore[import-not-found]
        analyze_claims_sync,
        analyze_if_addressed_sync,
    )
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    print("WARNING: claude_power_steering not available - SDK analysis disabled", file=sys.stderr)

# Import CompletionEvidenceChecker for check() method
try:
    from completion_evidence import (  # type: ignore[import-not-found]
        CompletionEvidenceChecker,
        EvidenceType,
    )
    EVIDENCE_AVAILABLE = True
except ImportError:
    EVIDENCE_AVAILABLE = False
    print("WARNING: completion_evidence not available - evidence checking disabled", file=sys.stderr)

logger = logging.getLogger(__name__)

# Security: Maximum transcript size to prevent memory exhaustion
MAX_TRANSCRIPT_LINES = _env_int("PSC_MAX_TRANSCRIPT_LINES", 50000)

# Maximum AskUserQuestion invocations before flagging as over-questioning
MAX_ASK_USER_QUESTIONS = _env_int("PSC_MAX_ASK_USER_QUESTIONS", 3)

# Minimum tests passed threshold for local testing check
MIN_TESTS_PASSED_THRESHOLD = _env_int("PSC_MIN_TESTS_PASSED_THRESHOLD", 10)

# Public API (the "studs" for this brick)
__all__ = [
    "PowerSteeringChecker",
    "PowerSteeringResult",
    "CheckerResult",
    "ConsiderationAnalysis",
    "SDK_AVAILABLE",
    "_timeout",
    "check_session",
    "is_disabled",
]


class PowerSteeringChecker(
    ConsiderationsMixin,
    SdkCallsMixin,
    ProgressTrackingMixin,
    ResultFormattingMixin,
):
    """Analyzes session completeness using consideration checkers.

    Phase 2 Implementation:
    - All 21 considerations from YAML file
    - User customization support
    - Generic analyzer for flexible considerations
    - Backward compatible with Phase 1
    - Fail-open error handling
    """

    def __init__(self, project_root: Path | None = None):
        """Initialize power-steering checker.

        Args:
            project_root: Project root directory (auto-detected if None)
        """
        # Auto-detect project root if not provided
        if project_root is None:
            project_root = self._detect_project_root()

        self.project_root = project_root

        # Use shared runtime directory for worktree support
        # In worktrees, this resolves to main repo's .claude/runtime
        # In main repos, this resolves to project_root/.claude/runtime
        shared_runtime = get_shared_runtime_dir(str(project_root))
        self.runtime_dir = Path(shared_runtime) / "power-steering"

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

        # Check-time state (reset each call to check())
        self._state_verification_passed: bool = False
        self._evidence_results: list = []

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
                script_dir = Path(__file__).parent.parent.parent  # up from pkg subdir to amplihack/
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
            self._log(f"State verification failed: {e}", "WARNING", exc_info=True)

        return results

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

        # Reset per-call state
        self._state_verification_passed = False
        self._evidence_results = []

        # Initialize turn state tracking (outside try block for fail-open)
        turn_state: "PowerSteeringTurnState | None" = None
        turn_state_manager: "TurnStateManager | None" = None

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
                    log=lambda msg, level="INFO": self._log(msg, level),
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

                # Display escalation warning if approaching threshold (Issue #2196)
                if escalation_msg:
                    self._log(escalation_msg, "WARNING")
                    self._emit_progress(
                        progress_callback,
                        "escalation_warning",
                        escalation_msg,
                        {
                            "blocks": turn_state.consecutive_blocks,
                            "threshold": PowerSteeringTurnState.MAX_CONSECUTIVE_BLOCKS,
                        },
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
                    self._log(
                        f"Evidence checking failed (non-critical): {e}", "WARNING", exc_info=True
                    )
                    self._evidence_results = []

            # 5. Analyze against considerations (filtered by session type)
            analysis = self._analyze_considerations(
                transcript, session_id, session_type, progress_callback
            )

            # 5a. Deterministic override: run heuristics for considerations where the
            # heuristic is more reliable than SDK (e.g. todos_complete).
            # If heuristic returns False for a consideration that SDK passed (True),
            # override the result. This prevents SDK fail-open from masking real failures.
            # Note: This is done AFTER _analyze_considerations (not inside it) so that
            # the SDK-first architecture is preserved in _check_single_consideration_async.
            for cid, result in list(analysis.results.items()):
                if result.satisfied:
                    checker_name = ""
                    # Find the checker for this consideration
                    for c in self.considerations:
                        if c.get("id") == cid:
                            checker_name = c.get("checker", "")
                            break
                    if checker_name and hasattr(self, checker_name) and callable(
                        getattr(self, checker_name)
                    ):
                        try:
                            heuristic_func = getattr(self, checker_name)
                            heuristic_satisfied = heuristic_func(transcript, session_id)
                            if not heuristic_satisfied:
                                # Heuristic says NOT satisfied - override SDK result
                                from .considerations import CheckerResult as _CheckerResult
                                overridden = _CheckerResult(
                                    consideration_id=cid,
                                    satisfied=False,
                                    reason="Deterministic heuristic: not satisfied",
                                    severity=result.severity,
                                    recovery_steps=result.recovery_steps,
                                )
                                # Remove old result and add overridden one
                                del analysis.results[cid]
                                analysis.results[cid] = overridden
                                if result.severity == "blocker":
                                    analysis.failed_blockers.append(overridden)
                                else:
                                    analysis.failed_warnings.append(overridden)
                        except Exception as e:
                            # Fail-open: keep SDK result on any heuristic error
                            self._log(
                                f"Deterministic override error for '{cid}' (fail-open): {e}",
                                "WARNING",
                                exc_info=True,
                            )

            # 5b. Delta analysis: Check if NEW content addresses previous failures
            addressed_concerns: dict[str, str] = {}
            user_claims: list[str] = []
            delta_result: "DeltaAnalysisResult | None" = None

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
                elif compaction_detected and self._state_verification_passed and remaining_blockers:
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

                        # Issue #2196: Generate failure fingerprint for loop detection
                        failed_ids = [r.consideration_id for r in blockers_to_record]
                        current_fingerprint = turn_state.generate_failure_fingerprint(failed_ids)  # type: ignore[attr-defined]

                        # Add fingerprint to history
                        turn_state.failure_fingerprints.append(current_fingerprint)  # type: ignore[attr-defined]

                        # Check for loop (same failures repeating 3+ times)
                        if turn_state.detect_loop(current_fingerprint, threshold=3):  # type: ignore[attr-defined]
                            self._log(
                                f"Loop detected: Same failures repeating (fingerprint={current_fingerprint})",
                                "WARNING",
                            )
                            self._emit_progress(
                                progress_callback,
                                "loop_detected",
                                f"Same issues repeating {turn_state.failure_fingerprints.count(current_fingerprint)} times",  # type: ignore[attr-defined]
                                {"fingerprint": current_fingerprint, "failed_ids": failed_ids},
                            )

                            # Auto-approve to break loop (fail-open design)
                            turn_state = turn_state_manager.record_approval(turn_state)
                            turn_state_manager.save_state(turn_state)

                            return PowerSteeringResult(
                                decision="approve",
                                reasons=["loop_detected"],
                                continuation_prompt=None,
                                summary=f"Loop detected: Same {len(failed_ids)} issues repeating. Auto-approved to prevent infinite loop.",
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
                # Mark results shown AND complete immediately.
                # Defense-in-depth for Issue #2548: if session_id lookup fails on the next stop,
                # _already_ran() returning True prevents the visibility block from re-triggering.
                self._mark_results_shown(session_id)
                self._mark_complete(session_id)
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
            if self._evidence_results:
                result.evidence_results = self._evidence_results

            return result

        except Exception as e:
            # Fail-open: On any error, approve and log
            self._log(f"Power-steering error (fail-open): {e}", "ERROR", exc_info=True)
            return PowerSteeringResult(
                decision="approve",
                reasons=["error_failopen"],
                continuation_prompt=None,
                summary=None,
            )

    def _is_disabled(self) -> bool:
        """Check if power-steering is disabled.

        Four-layer disable system (priority order):
        1. Semaphore file in CWD (highest - for worktree-specific disabling)
        2. Semaphore file in shared runtime (for disabling across all worktrees)
        3. Environment variable (medium)
        4. Config file (lowest)

        Returns:
            True if disabled, False if enabled
        """
        try:
            # Check 1: Semaphore file directly in current working directory
            cwd_disabled = Path.cwd() / ".disabled"
            if cwd_disabled.exists():
                return True
        except (OSError, RuntimeError):
            pass

        try:
            # Check 2: Semaphore file in shared runtime directory
            shared_runtime = Path(get_shared_runtime_dir(self.project_root))
            disabled_file = shared_runtime / "power-steering" / ".disabled"
            if disabled_file.exists():
                return True
        except (OSError, RuntimeError):
            pass

        # Check 3: Environment variable
        if os.getenv("AMPLIHACK_SKIP_POWER_STEERING"):
            return True

        # Check 4: Config file
        if not self.config.get("enabled", False):
            return True

        return False

    def _validate_path(self, path: Path, allowed_parent: Path) -> bool:
        """Validate path is safe to read (permissive for user files).

        Args:
            path: Path to validate
            allowed_parent: Parent directory path must be under

        Returns:
            True if path is safe, False otherwise
        """
        import tempfile

        try:
            path_resolved = path.resolve()
            parent_resolved = allowed_parent.resolve()

            # Check 1: Path is within allowed parent (project root)
            try:
                path_resolved.relative_to(parent_resolved)
                self._log("Path validated: within project root", "DEBUG")
                return True
            except ValueError:
                pass

            # Check 2: Path is within user's home directory
            try:
                home = Path.home().resolve()
                path_resolved.relative_to(home)
                self._log("Path validated: within user home directory", "DEBUG")
                return True
            except ValueError:
                pass

            # Check 3: Path is in common temp directories (for testing)
            temp_dirs = [
                Path("/tmp"),
                Path("/var/tmp"),
                Path(tempfile.gettempdir()),
            ]

            for temp_dir in temp_dirs:
                try:
                    path_resolved.relative_to(temp_dir.resolve())
                    self._log(f"Path validated: within temp directory {temp_dir}", "DEBUG")
                    return True
                except ValueError:
                    continue

            self._log(
                f"Path validation failed: {path_resolved} not in project root, "
                f"home directory, or temp directories",
                "WARNING",
            )
            return False

        except (OSError, RuntimeError) as e:
            self._log(f"Path validation error: {e}", "ERROR")
            return False

    def _load_transcript(self, transcript_path: Path) -> list[dict]:
        """Load transcript from JSONL file with size limits and format auto-detection.

        Supports both Claude Code JSONL format (~/.claude/projects/*/*.jsonl) and
        GitHub Copilot CLI events.jsonl format (~/.copilot/session-state/{id}/events.jsonl).
        The format is auto-detected from the first line; Copilot events are normalized
        into the same list[dict] shape expected by all checker methods.

        Args:
            transcript_path: Path to transcript file

        Returns:
            List of message dictionaries (truncated if exceeds MAX_TRANSCRIPT_LINES)

        Raises:
            OSError: If file cannot be read
            ValueError: If transcript path is outside project root (security check)
        """
        # Security: Validate transcript path is within project root
        if not self._validate_path(transcript_path, self.project_root):
            raise ValueError(
                f"Transcript path {transcript_path} is outside project root {self.project_root}"
            )

        lines = []
        truncated = False
        line_num = 0

        with open(transcript_path) as f:
            for line_num, line in enumerate(f, 1):
                # Security: Enforce maximum transcript size
                if line_num > MAX_TRANSCRIPT_LINES:
                    truncated = True
                    break

                stripped = line.strip()
                if not stripped:
                    continue
                # REQ-SEC-3: Skip oversized lines to prevent memory exhaustion
                if len(stripped.encode("utf-8")) > MAX_LINE_BYTES:
                    self._log(
                        f"Skipping oversized transcript line {line_num} "
                        f"({len(stripped)} chars, limit {MAX_LINE_BYTES} bytes)",
                        "WARNING",
                    )
                    continue
                lines.append(stripped)

        if truncated:
            self._log(
                f"Transcript truncated at {MAX_TRANSCRIPT_LINES} lines (original: {line_num})",
                "WARNING",
            )

        # Auto-detect format and parse (normalizes Copilot events if needed)
        fmt, messages = parse_transcript(lines)
        if fmt == "copilot":
            self._log(
                f"Copilot transcript format detected in {transcript_path.name}; "
                f"normalized {len(messages)} events to Claude Code format",
                "INFO",
            )

        return messages

    def _log_violation(self, consideration_id: str, details: dict, session_id: str) -> None:
        """Log violation details to session logs.

        Args:
            consideration_id: ID of failed consideration
            details: Violation details
            session_id: Session identifier
        """
        if not _validate_session_id(session_id):
            self._log(f"Invalid session_id rejected in _log_violation: {session_id!r}", "WARNING")
            return
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

            log_file.write_text(json.dumps(violations, indent=2), encoding="utf-8")
        except Exception as e:
            self._log(
                f"Could not write violation log (non-critical): {e}", "WARNING", exc_info=True
            )


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


def is_disabled(project_root: Path | None = None) -> bool:
    """Standalone function to check if power-steering is disabled.

    This function exists primarily for testing purposes, allowing tests
    to check the disabled status without creating a full PowerSteeringChecker
    instance.

    Args:
        project_root: Project root directory (auto-detected if None)

    Returns:
        True if power-steering is disabled, False if enabled
    """
    try:
        checker = PowerSteeringChecker(project_root)
        return checker._is_disabled()
    except Exception as e:
        # Fail-open: If checker creation fails, assume not disabled
        logger.warning(
            "PowerSteeringChecker creation failed, assuming not disabled: %s", e, exc_info=True
        )
        return False


if __name__ == "__main__":
    # For testing: Allow running directly
    if len(sys.argv) < 3:
        print("Usage: main_checker.py <transcript_path> <session_id>")
        sys.exit(1)

    transcript_path = Path(sys.argv[1])
    session_id = sys.argv[2]

    result = check_session(transcript_path, session_id)
    print(json.dumps({"decision": result.decision, "reasons": result.reasons}, indent=2))
