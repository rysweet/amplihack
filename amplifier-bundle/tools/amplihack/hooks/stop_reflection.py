"""
Reflection module for the stop hook.

Handles reflection config checks, running Claude-based reflection,
and producing block decisions with findings.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hook_processor import HookProcessor


def should_run_reflection(hook: "HookProcessor") -> bool:
    """Check if reflection should run based on config and environment.

    Args:
        hook: The HookProcessor instance (for logging/metrics)

    Returns:
        True if reflection should run, False otherwise
    """
    if os.environ.get("AMPLIHACK_SKIP_REFLECTION"):
        hook.log("AMPLIHACK_SKIP_REFLECTION is set - skipping reflection", "WARNING")
        hook.save_metric("reflection_env_skips", 1)
        return False

    config_path = (
        hook.project_root / ".claude" / "tools" / "amplihack" / ".reflection_config"
    )
    if not config_path.exists():
        hook.log("Reflection config not found - skipping reflection", "WARNING")
        hook.save_metric("reflection_no_config", 1)
        return False

    try:
        with open(config_path) as f:
            config = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        hook.log(
            f"[CAUSE] Cannot read or parse reflection config file. [IMPACT] Reflection will not run. [ACTION] Check config file format and permissions. Error: {e}",
            "WARNING",
        )
        hook.save_metric("reflection_config_errors", 1)
        return False

    if not config.get("enabled", False):
        hook.log("Reflection is disabled - skipping", "WARNING")
        hook.save_metric("reflection_disabled_checks", 1)
        return False

    reflection_dir = hook.project_root / ".claude" / "runtime" / "reflection"
    reflection_lock = reflection_dir / ".reflection_lock"

    if reflection_lock.exists():
        hook.log("Reflection already running - skipping", "WARNING")
        hook.save_metric("reflection_concurrent_skips", 1)
        return False

    return True


def run_reflection(
    hook: "HookProcessor", input_data: dict, session_id: str
) -> dict:
    """Run full reflection flow: check semaphore, run analysis, return decision.

    Args:
        hook: The HookProcessor instance (for logging/metrics)
        input_data: Input from Claude Code (may contain transcript_path)
        session_id: Current session identifier

    Returns:
        Decision dict (approve or block with findings)
    """
    semaphore_file = (
        hook.project_root
        / ".claude"
        / "runtime"
        / "reflection"
        / f".reflection_presented_{session_id}"
    )

    if semaphore_file.exists():
        hook.log(
            f"Reflection already presented for session {session_id} - removing semaphore and allowing stop"
        )
        try:
            semaphore_file.unlink()
        except OSError as e:
            hook.log(
                f"[CAUSE] Cannot remove semaphore file {semaphore_file}. [IMPACT] Reflection may incorrectly skip on next stop. [ACTION] Continuing anyway (non-critical). Error: {e}",
                "WARNING",
            )
            hook.save_metric("semaphore_cleanup_errors", 1)
        hook.log("=== STOP HOOK ENDED (decision: approve - reflection already shown) ===")
        return {"decision": "approve"}

    try:
        _announce_reflection_start()
        transcript_path = input_data.get("transcript_path")
        filled_template = _run_reflection_sync(hook, transcript_path, session_id)

        if not filled_template or not filled_template.strip():
            hook.log("No reflection result - allowing stop")
            hook.log("=== STOP HOOK ENDED (decision: approve - no reflection) ===")
            return {"decision": "approve"}

        reflection_filename = _generate_reflection_filename(filled_template)
        reflection_path = (
            hook.project_root
            / ".claude"
            / "runtime"
            / "reflection"
            / reflection_filename
        )

        try:
            reflection_path.parent.mkdir(parents=True, exist_ok=True)
            reflection_path.write_text(filled_template)
            hook.log(f"Reflection saved to: {reflection_path}")
        except (OSError, PermissionError) as e:
            hook.log(f"Warning: Could not save reflection file: {e}", "WARNING")

        try:
            current_findings = (
                hook.project_root
                / ".claude"
                / "runtime"
                / "reflection"
                / "current_findings.md"
            )
            current_findings.write_text(filled_template)
        except (OSError, PermissionError) as e:
            hook.log(
                f"[CAUSE] Cannot write backward-compatibility file current_findings.md. [IMPACT] Legacy tools may not find reflection results. [ACTION] Primary reflection file still saved. Error: {e}",
                "WARNING",
            )
            hook.save_metric("backward_compat_write_errors", 1)

        hook.log("Reflection complete - blocking with presentation instructions")
        result = _block_with_findings(hook, filled_template, str(reflection_path))

        try:
            semaphore_file.parent.mkdir(parents=True, exist_ok=True)
            semaphore_file.touch()
            hook.log(f"Created reflection semaphore: {semaphore_file}")
        except OSError as e:
            hook.log(f"Warning: Could not create semaphore file: {e}", "WARNING")

        hook.log("=== STOP HOOK ENDED (decision: block - reflection complete) ===")
        return result

    except (ImportError, AttributeError, OSError) as e:
        hook.log(f"Reflection error: {e}", "ERROR")
        hook.save_metric("reflection_errors", 1)
        hook.log("=== STOP HOOK ENDED (decision: approve - error occurred) ===")
        return {"decision": "approve"}


def _run_reflection_sync(
    hook: "HookProcessor", transcript_path: str | None, session_id: str
) -> str | None:
    """Run Claude SDK-based reflection synchronously.

    Args:
        hook: The HookProcessor instance (for logging/metrics)
        transcript_path: Optional path to JSONL transcript file from Claude Code
        session_id: Current session identifier

    Returns:
        Filled FEEDBACK_SUMMARY template as string, or None if failed
    """
    try:
        from claude_reflection import run_claude_reflection
    except ImportError as e:
        hook.log(
            f"[CAUSE] Cannot import claude_reflection module. [IMPACT] Reflection functionality unavailable. [ACTION] Check if claude_reflection.py exists and is accessible. Error: {e}",
            "WARNING",
        )
        hook.save_metric("reflection_import_errors", 1)
        return None

    hook.log(f"Running Claude-powered reflection for session: {session_id}")

    conversation = None
    if transcript_path:
        transcript_file = Path(transcript_path)
        hook.log(f"Using transcript from Claude Code: {transcript_file}")

        try:
            conversation = []
            with open(transcript_file) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    if entry.get("type") in ["user", "assistant"] and "message" in entry:
                        msg = entry["message"]
                        content = msg.get("content", "")
                        if isinstance(content, list):
                            text_parts = []
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    text_parts.append(block.get("text", ""))
                            content = "\n".join(text_parts)

                        conversation.append(
                            {
                                "role": msg.get("role", entry.get("type", "user")),
                                "content": content,
                            }
                        )
            hook.log(f"Loaded {len(conversation)} conversation turns from transcript")
        except (OSError, json.JSONDecodeError) as e:
            hook.log(
                f"[CAUSE] Failed to parse transcript file. [IMPACT] Reflection will run without transcript context. [ACTION] Check transcript file format. Error: {e}",
                "WARNING",
            )
            hook.save_metric("transcript_parse_errors", 1)
            conversation = None

    session_dir = hook.project_root / ".claude" / "runtime" / "logs" / session_id

    if not session_dir.exists():
        hook.log(
            f"[CAUSE] Session directory not found at expected path. [IMPACT] Cannot run reflection without session logs. [ACTION] Check session ID detection logic. Path: {session_dir}",
            "WARNING",
        )
        hook.save_metric("session_dir_not_found", 1)
        return None

    try:
        filled_template = run_claude_reflection(session_dir, hook.project_root, conversation)

        if not filled_template:
            hook.log(
                "[CAUSE] Claude reflection returned empty or None result. [IMPACT] No reflection findings to present. [ACTION] Check reflection implementation and Claude API connectivity.",
                "WARNING",
            )
            hook.save_metric("reflection_empty_results", 1)
            return None

        output_path = session_dir / "FEEDBACK_SUMMARY.md"
        output_path.write_text(filled_template)
        hook.log(f"Feedback summary saved to: {output_path}")

        findings_path = (
            hook.project_root / ".claude" / "runtime" / "reflection" / "current_findings.md"
        )
        findings_path.parent.mkdir(parents=True, exist_ok=True)
        findings_path.write_text(filled_template)

        hook.save_metric("reflection_success", 1)

        return filled_template

    except (ImportError, AttributeError, OSError) as e:
        hook.log(
            f"[CAUSE] Claude reflection execution failed with exception. [IMPACT] No reflection analysis available this session. [ACTION] Check Claude SDK configuration and API status. Error: {e}",
            "ERROR",
        )
        hook.save_metric("reflection_execution_errors", 1)
        return None


def _announce_reflection_start() -> None:
    """Announce that reflection is starting."""
    print(f"\n{'=' * 70}", file=sys.stderr)
    print("🔍 BEGINNING SELF-REFLECTION ON SESSION", file=sys.stderr)
    print(f"{'=' * 70}\n", file=sys.stderr)
    print("Analyzing the conversation using Claude SDK...", file=sys.stderr)
    print("This will take 10-60 seconds.", file=sys.stderr)
    print("\nWhat reflection analyzes:", file=sys.stderr)
    print("  • Task complexity and workflow adherence", file=sys.stderr)
    print("  • User interactions and satisfaction", file=sys.stderr)
    print("  • Subagent usage and efficiency", file=sys.stderr)
    print("  • Learning opportunities and improvements", file=sys.stderr)
    print(f"\n{'=' * 70}\n", file=sys.stderr)


def _generate_reflection_filename(filled_template: str) -> str:
    """Generate descriptive filename for this session's reflection.

    Args:
        filled_template: The reflection content (used to extract task summary)

    Returns:
        Filename like: reflection-system-investigation-20251104_165432.md
    """
    task_slug = "session"
    try:
        if "## Task Summary" in filled_template:
            import re

            summary_section = filled_template.split("## Task Summary")[1].split("\n\n")[1]
            first_sentence = summary_section.split(".")[0][:100]
            task_slug = re.sub(r"[^a-z0-9]+", "-", first_sentence.lower()).strip("-")
            task_slug = task_slug[:50]
    except (IndexError, AttributeError):
        task_slug = "session"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    return f"reflection-{task_slug}-{timestamp}.md"


def _block_with_findings(
    hook: "HookProcessor", filled_template: str, reflection_file_path: str
) -> dict:
    """Block stop with instructions to read and present reflection.

    Args:
        hook: The HookProcessor instance (for metrics)
        filled_template: Filled FEEDBACK_SUMMARY template from Claude
        reflection_file_path: Path where reflection was saved

    Returns:
        Block decision dict with presentation instructions
    """
    reason = f"""📋 SESSION REFLECTION COMPLETE

The reflection system has analyzed this session and saved the findings to:

**{reflection_file_path}**

**YOUR TASK:**

1. Read the reflection file using the Read tool
2. Parse the findings and present them to the user following this structure:

   a) **Executive Summary** (2-3 sentences)
      - What was accomplished
      - Key insight from reflection

   b) **Key Findings** (Be verbose!)
      - What Worked Well: Highlight 2-3 top successes with specific examples
      - Areas for Improvement: Highlight 2-3 main issues with context

   c) **Top Recommendations** (Be verbose!)
      - Present 3-5 recommendations in priority order
      - For each: Problem → Solution → Impact → Why it matters

   d) **Action Options** - Give the user these choices:
      • Create GitHub Issues (work on NOW or save for LATER)
      • Start Auto Mode (if concrete improvements can be implemented)
      • Discuss Specific Improvements (explore recommendations in detail)
      • Just Stop (next stop will succeed - semaphore prevents re-run)

After presenting the findings and getting the user's decision, you may proceed accordingly."""

    hook.save_metric("reflection_blocked", 1)

    return {"decision": "block", "reason": reason}
