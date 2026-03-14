"""SDK calls module - SdkCallsMixin with parallel analysis methods."""

import asyncio
import signal
import sys
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from .considerations import CheckerResult, ConsiderationAnalysis, _env_int

# Module-level constant extracted from inline code
MIN_VERIFIED_EVIDENCE_COUNT = 3

# Timeout hierarchy: HOOK_TIMEOUT (120s) > PARALLEL_TIMEOUT (60s) > CHECKER_TIMEOUT (25s)
# Individual checker execution budget (within parallel execution budget)
CHECKER_TIMEOUT = _env_int("PSC_CHECKER_TIMEOUT", 25)

# Parallel execution budget: All 21 checks complete in ~15-20s typically, 60s provides buffer
# Must be less than HOOK_TIMEOUT (120s) to avoid being killed by framework
PARALLEL_TIMEOUT = _env_int("PSC_PARALLEL_TIMEOUT", 60)

# Try to import Claude SDK integration
try:
    from claude_power_steering import analyze_consideration

    _SDK_IMPORT_OK = True
except ImportError:
    analyze_consideration = None  # type: ignore[assignment]  # Available at module level for test patching
    _SDK_IMPORT_OK = False
    print("WARNING: claude_power_steering not available - SDK analysis disabled", file=sys.stderr)

# Public alias for backward compatibility and test imports
SDK_AVAILABLE = _SDK_IMPORT_OK

# Try to import completion evidence module
try:
    from completion_evidence import EvidenceType

    _EVIDENCE_IMPORT_OK = True
except ImportError:
    _EVIDENCE_IMPORT_OK = False
    print("WARNING: completion_evidence not available - evidence checking disabled", file=sys.stderr)

# Public alias
EVIDENCE_AVAILABLE = _EVIDENCE_IMPORT_OK

# Try to import turn-aware state management
try:
    from power_steering_state import FailureEvidence

    _TURN_STATE_IMPORT_OK = True
except ImportError:
    _TURN_STATE_IMPORT_OK = False
    print("WARNING: power_steering_state not available - turn state tracking disabled", file=sys.stderr)


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


class SdkCallsMixin:
    """Mixin with SDK call methods for parallel analysis."""

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
        if not _EVIDENCE_IMPORT_OK:
            return False

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
        return verified_count >= MIN_VERIFIED_EVIDENCE_COUNT

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
    ) -> list:
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
        if not _TURN_STATE_IMPORT_OK:
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
            # Extract text once; derive lowercase view without a second call
            original_content = self._extract_message_text(msg)
            content = original_content.lower()

            for term in relevant_terms:
                if term in content:
                    # Found relevant content - extract context
                    idx = content.find(term)
                    start = max(0, idx - 30)
                    end = min(len(content), idx + len(term) + 70)

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
            self._log(f"Parallel analysis failed (fail-open): {e}", "ERROR", exc_info=True)
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
        # Use module-level PARALLEL_TIMEOUT constant defined in this module
        parallel_timeout = PARALLEL_TIMEOUT

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
            async with asyncio.timeout(parallel_timeout):
                results = await asyncio.gather(*tasks, return_exceptions=True)
        except TimeoutError:
            self._log(f"Parallel execution timed out after {parallel_timeout}s", "WARNING")
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
            # Look up SDK_AVAILABLE via package namespace so tests can patch 'power_steering_checker.SDK_AVAILABLE'
            import sys as _sys

            _psc = _sys.modules.get("power_steering_checker")
            _sdk_available = (
                getattr(_psc, "SDK_AVAILABLE", SDK_AVAILABLE) if _psc else SDK_AVAILABLE
            )
            if _sdk_available:
                try:
                    # Use async SDK function directly (already awaitable)
                    # Returns tuple: (satisfied, reason)
                    # Look up via package namespace so tests can patch 'power_steering_checker.analyze_consideration'
                    _ac = (
                        getattr(_psc, "analyze_consideration", analyze_consideration)
                        if _psc
                        else analyze_consideration
                    )
                    _sdk_result = await _ac(
                        conversation=transcript,
                        consideration=consideration,
                        project_root=self.project_root,
                    )
                    # Handle both (satisfied, reason) tuple and plain bool return
                    if isinstance(_sdk_result, tuple):
                        satisfied, sdk_reason = _sdk_result
                    else:
                        satisfied = bool(_sdk_result)
                        sdk_reason = "SDK analysis"

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
                    error_msg = f"[Power Steering SDK Error] {consideration['id']}: {e!s}\n"
                    _sys.stderr.write(error_msg)
                    _sys.stderr.flush()

                    self._log(
                        f"SDK error for consideration '{consideration['id']}': {e}",
                        "WARNING",
                        exc_info=True,
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
                exc_info=True,
            )
            return CheckerResult(
                consideration_id=consideration["id"],
                satisfied=True,  # Fail-open
                reason=f"Error (fail-open): {e}",
                severity=consideration["severity"],
            )
