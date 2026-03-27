"""Result formatting and output generation for power-steering.

Pure output generation — no I/O, no external calls.
Transforms data into formatted strings for display.
"""

import logging
import sys
from datetime import datetime
from typing import Optional

from .considerations import ConsiderationAnalysis, _env_int

logger = logging.getLogger(__name__)

# Fallback max consecutive blocks when TurnState is unavailable
DEFAULT_MAX_CONSECUTIVE_BLOCKS = _env_int("PSC_MAX_CONSECUTIVE_BLOCKS", 10)

# Try to import turn-aware state management with delta analysis
try:
    from power_steering_state import (  # type: ignore[import-not-found]
        PowerSteeringTurnState,
    )

    TURN_STATE_AVAILABLE = True
except ImportError:
    TURN_STATE_AVAILABLE = False
    print("WARNING: power_steering_state not available - turn-aware formatting disabled", file=sys.stderr)


class ResultFormattingMixin:
    """Mixin for output generation — formats data into display strings.

    All methods access self.considerations, self._log(), etc.
    inherited from PowerSteeringChecker.
    """

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
        threshold = (
            PowerSteeringTurnState.MAX_CONSECUTIVE_BLOCKS
            if TURN_STATE_AVAILABLE
            else DEFAULT_MAX_CONSECUTIVE_BLOCKS
        )

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
