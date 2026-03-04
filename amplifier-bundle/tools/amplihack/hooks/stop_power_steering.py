"""
Power-steering module for the stop hook.

Handles power-steering check, counter tracking, and related decisions.
"""

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hook_processor import HookProcessor


def should_run_power_steering(hook: "HookProcessor") -> bool:
    """Check if power-steering should run based on config and environment.

    Args:
        hook: The HookProcessor instance (for logging/metrics)

    Returns:
        True if power-steering should run, False otherwise
    """
    try:
        from power_steering_checker import PowerSteeringChecker

        checker = PowerSteeringChecker(hook.project_root)
        is_disabled = checker._is_disabled()

        if is_disabled:
            hook.log("Power-steering is disabled - skipping", "WARNING")
            hook.save_metric("power_steering_disabled_checks", 1)
            return False

        ps_dir = hook.project_root / ".claude" / "runtime" / "power-steering"
        ps_lock = ps_dir / ".power_steering_lock"

        if ps_lock.exists():
            hook.log("Power-steering already running - skipping", "WARNING")
            hook.save_metric("power_steering_concurrent_skips", 1)
            return False

        return True

    except (ImportError, AttributeError, OSError) as e:
        hook.log(
            f"[CAUSE] Exception during power-steering status check. [IMPACT] Power-steering will not run this session. [ACTION] Failing open to allow normal stop. Error: {e}",
            "WARNING",
        )
        hook.save_metric("power_steering_check_errors", 1)
        return False


def increment_power_steering_counter(hook: "HookProcessor", session_id: str) -> int:
    """Increment power-steering invocation counter for statusline display.

    Writes counter to .claude/runtime/power-steering/{session_id}/session_count
    for statusline to read.

    Args:
        hook: The HookProcessor instance (for logging/metrics)
        session_id: Session identifier

    Returns:
        New count value
    """
    try:
        counter_file = (
            hook.project_root
            / ".claude"
            / "runtime"
            / "power-steering"
            / session_id
            / "session_count"
        )
        counter_file.parent.mkdir(parents=True, exist_ok=True)

        current_count = 0
        if counter_file.exists():
            try:
                current_count = int(counter_file.read_text().strip())
            except (ValueError, OSError):
                current_count = 0

        new_count = current_count + 1
        counter_file.write_text(str(new_count))
        return new_count

    except (OSError, ValueError) as e:
        hook.log(f"Failed to update power-steering counter: {e}", "WARNING")
        return 0


def run_power_steering_check(
    hook: "HookProcessor", input_data: dict, session_id: str
) -> dict | None:
    """Run power-steering analysis and return a block/approve decision.

    Args:
        hook: The HookProcessor instance (for logging/metrics)
        input_data: Input from Claude Code (must contain transcript_path)
        session_id: Current session identifier

    Returns:
        Block decision dict if power-steering triggers, None to continue
    """
    try:
        from power_steering_checker import PowerSteeringChecker
        from power_steering_progress import ProgressTracker

        ps_checker = PowerSteeringChecker(hook.project_root)
        transcript_path_str = input_data.get("transcript_path")

        if not transcript_path_str:
            hook.log(
                "[CAUSE] Missing transcript_path in input_data. [IMPACT] Power-steering cannot analyze session without transcript. [ACTION] Skipping power-steering check.",
                "WARNING",
            )
            hook.save_metric("power_steering_missing_transcript", 1)
            return None

        transcript_path = Path(transcript_path_str)

        progress_tracker = ProgressTracker(project_root=hook.project_root)

        hook.log("Running power-steering analysis...")
        ps_result = ps_checker.check(
            transcript_path, session_id, progress_callback=progress_tracker.emit
        )

        increment_power_steering_counter(hook, session_id)

        if ps_result.decision == "block":
            if ps_result.is_first_stop and ps_result.analysis:
                hook.log(
                    "First stop - displaying all consideration results for visibility"
                )
                progress_tracker.display_all_results(
                    analysis=ps_result.analysis,
                    considerations=ps_checker.considerations,
                    is_first_stop=True,
                )
                hook.save_metric("power_steering_first_stop_visibility", 1)
            else:
                hook.log("Power-steering blocking stop - work incomplete")
                hook.save_metric("power_steering_blocks", 1)
                progress_tracker.display_summary()

            hook.log("=== STOP HOOK ENDED (decision: block - power-steering) ===")
            return {
                "decision": "block",
                "reason": ps_result.continuation_prompt or "Session appears incomplete",
            }

        hook.log(f"Power-steering approved stop: {ps_result.reasons}")
        hook.save_metric("power_steering_approves", 1)

        progress_tracker.display_summary()

        if ps_result.summary:
            hook.log("Power-steering summary generated")

        return None

    except (ImportError, AttributeError, OSError) as e:
        # Fail-open: Continue to normal flow on import/OS errors
        hook.log(f"Power-steering error (fail-open): {e}", "WARNING")
        hook.save_metric("power_steering_errors", 1)

        print("\n⚠️  Power-Steering Warning", file=sys.stderr)
        print(f"Power-steering encountered an error and was skipped: {e}", file=sys.stderr)
        print(
            "Check .claude/runtime/power-steering/power_steering.log for details",
            file=sys.stderr,
        )
        return None
