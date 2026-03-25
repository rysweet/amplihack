# File: src/amplihack/session.py
"""Session lifecycle management: staging, auto mode, instruction append.

Extracted from cli.py (issue #2845). Contains:
- launch_command: Handle the launch command entry point
- _launch_command_impl: Internal launch with session tracking
- handle_auto_mode: Handle --auto flag for claude/copilot/codex
- handle_append_instruction: Handle --append flag for running auto sessions
- _fix_global_statusline_path: Fix statusline path in ~/.claude/settings.json
- _ensure_amplihack_staged: Stage .claude/ files to ~/.amplihack/.claude/ in UVX mode
"""

import argparse
import json
import logging
import os
import platform
import sys
from pathlib import Path

from . import copytree_manifest
from .docker import DockerManager
from .launcher import ClaudeLauncher
from .launcher.session_tracker import SessionTracker
from .staging_cleanup import cleanup_legacy_skills
from .utils import is_uvx_deployment

logger = logging.getLogger(__name__)

# Platform-specific emoji support (redefined locally to avoid importing from cli.py)
_IS_WINDOWS = platform.system() == "Windows"
EMOJI = {
    "check": "[OK]" if _IS_WINDOWS else "✓",
}

# Cached at import time — AMPLIHACK_DEBUG is set before process start, never mutated at runtime.
_DEBUG: bool = os.environ.get("AMPLIHACK_DEBUG", "").lower() == "true"


def launch_command(args: argparse.Namespace, claude_args: list[str] | None = None) -> int:
    """Handle the launch command.

    Args:
        args: Parsed command line arguments.
        claude_args: Additional arguments to forward to Claude.

    Returns:
        Exit code.
    """
    # --subprocess-safe: skip all staging/env mutations to avoid concurrent
    # write races when running as a delegate from another amplihack process
    # (e.g. multitask workstreams).  See issue #2567.
    subprocess_safe = getattr(args, "subprocess_safe", False)

    from .launcher.session_tracker import (
        SessionTracker,
    )

    # Detect nesting BEFORE any .claude/ operations
    original_cwd = None
    nesting_result = None

    if not subprocess_safe:
        from .launcher.auto_stager import AutoStager
        from .launcher.nesting_detector import NestingDetector

        detector = NestingDetector()
        nesting_result = detector.detect_nesting(Path.cwd(), sys.argv)

        # Auto-stage if nested execution in source repo detected
        if nesting_result.requires_staging:
            print("\n🚨 SELF-MODIFICATION PROTECTION ACTIVATED")
            print("   Running nested in amplihack source repository")
            print("   Auto-staging .claude/ to temp directory for safety")

            stager = AutoStager()
            original_cwd = Path.cwd()
            staging_result = stager.stage_for_nested_execution(
                original_cwd, f"nested-{os.getpid()}"
            )

            print(f"   📁 Staged to: {staging_result.temp_root}")
            print("   Your original .claude/ files are protected")

            # CRITICAL: Change to temp directory so all .claude/ operations happen there
            os.chdir(staging_result.temp_root)
            print(f"   📂 CWD changed to: {staging_result.temp_root}\n")

        # Ensure amplihack framework is staged to ~/.amplihack/.claude/
        _ensure_amplihack_staged()

        # Auto-install missing SDK dependencies (e.g. agent-framework-core)
        # Uses --python sys.executable to target the running interpreter,
        # critical when launched via uvx (ephemeral venv != project .venv).
        from .dep_check import ensure_sdk_deps

        try:
            ensure_sdk_deps()
        except ImportError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)

        # Prompt to re-enable power-steering if disabled (#2544)
        try:
            from .power_steering.re_enable_prompt import prompt_re_enable_if_disabled

            prompt_re_enable_if_disabled()
        except Exception as e:
            # Fail-open: log error but continue
            logger.debug(f"Error checking power-steering re-enable prompt: {e}")

    # Start session tracking
    tracker = SessionTracker()
    is_auto_mode = getattr(args, "auto", False)

    session_id = tracker.start_session(
        pid=os.getpid(),
        launch_dir=str(Path.cwd()),
        argv=sys.argv,
        is_auto_mode=is_auto_mode,
        is_nested=nesting_result.is_nested if nesting_result else False,
        parent_session_id=nesting_result.parent_session_id if nesting_result else None,
    )

    # Wrap execution in try/finally to ensure session is marked complete/crashed
    try:
        result = _launch_command_impl(args, claude_args, session_id, tracker)
        tracker.complete_session(session_id)
        return result
    except Exception as e:
        logger.debug(f"Session {session_id} ended with error: {type(e).__name__}: {e}")
        try:
            tracker.crash_session(session_id)
        except Exception as crash_err:
            logger.debug(f"crash_session also failed: {crash_err}")
        raise
    finally:
        # Restore original CWD if we staged
        if original_cwd is not None:
            try:
                os.chdir(original_cwd)
            except Exception as e:
                # Best effort - log error but don't fail on CWD restore
                logging.debug(f"Failed to restore CWD to {original_cwd}: {e}")


def _launch_command_impl(
    args: argparse.Namespace,
    claude_args: list[str] | None,
    session_id: str,
    tracker: SessionTracker,
) -> int:
    """Internal implementation of launch_command with session tracking.

    Args:
        args: Parsed command line arguments.
        claude_args: Additional arguments to forward to Claude.
        session_id: Session ID from tracker
        tracker: SessionTracker instance

    Returns:
        Exit code.
    """
    # Neo4j flags removed (Week 7 cleanup) - Kuzu is now the only backend

    # Check if Docker should be used (CLI flag takes precedence over env var)
    use_docker = getattr(args, "docker", False) or DockerManager.should_use_docker()

    # Handle --no-reflection flag (disable always wins priority)
    if getattr(args, "no_reflection", False):
        os.environ["AMPLIHACK_SKIP_REFLECTION"] = "1"

    # Handle --auto flag
    if getattr(args, "auto", False):
        os.environ["AMPLIHACK_AUTO_MODE"] = "1"

    if use_docker:
        print(
            "Docker mode enabled"
            + (
                " via --docker flag"
                if getattr(args, "docker", False)
                else " via AMPLIHACK_USE_DOCKER"
            )
        )
        docker_manager = DockerManager()

        # Build command arguments for Docker
        docker_args = ["launch"]
        if getattr(args, "checkout_repo", None):
            docker_args.extend(["--checkout-repo", args.checkout_repo])
        if claude_args:
            docker_args.append("--")
            docker_args.extend(claude_args)

        return docker_manager.run_command(docker_args)

    # In UVX mode, Claude uses --add-dir for both project directory and plugin directory

    # Launch Claude with checkout repo if specified
    launcher = ClaudeLauncher(
        checkout_repo=getattr(args, "checkout_repo", None),
        claude_args=claude_args,
        verbose=False,  # Interactive mode does not use --verbose
    )

    # Check if claude_args contains a prompt (-p) - if so, use non-interactive mode
    has_prompt = claude_args and ("-p" in claude_args)
    if has_prompt:
        exit_code = launcher.launch()
    else:
        exit_code = launcher.launch_interactive()

    # Mark session as complete
    tracker.complete_session(session_id)
    return exit_code


def handle_auto_mode(
    sdk: str, args: argparse.Namespace, cmd_args: list[str] | None
) -> "int | None":
    """Handle auto mode for claude, copilot, or codex commands.

    Args:
        sdk: "claude", "copilot", or "codex"
        args: Parsed arguments
        cmd_args: Command arguments (for extracting prompt)

    Returns:
        Exit code if auto mode, None if not auto mode
    """
    if not getattr(args, "auto", False):
        return None

    # Disable reflection in auto mode (Issue #1146)
    # Reflection is interactive and blocks autonomous execution
    # Note: --no-reflection flag (Issue #1147) is also handled in non-auto mode paths
    os.environ["AMPLIHACK_SKIP_REFLECTION"] = "1"

    from .launcher.auto_mode import AutoMode

    # Extract prompt from args
    prompt = None
    if cmd_args and "-p" in cmd_args:
        idx = cmd_args.index("-p")
        if idx + 1 < len(cmd_args):
            prompt = cmd_args[idx + 1]

    if not prompt:
        print(f'Error: --auto requires a prompt. Use: amplihack {sdk} --auto -- -p "your prompt"')
        return 1

    # Check if UI mode is enabled
    ui_mode = getattr(args, "ui", False)

    auto = AutoMode(sdk, prompt, args.max_turns, ui_mode=ui_mode)
    return auto.run()


def handle_append_instruction(args: argparse.Namespace) -> int:
    """Handle --append flag to inject instructions into running auto mode.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0=success, 1=error)
    """
    if not getattr(args, "append", None):
        return 0

    from .launcher.append_handler import AppendError, append_instructions

    instruction = args.append

    try:
        result = append_instructions(instruction)

        # Print success message
        print(f"{EMOJI['check']} Instruction appended to session: {result.session_id}")
        print(f"  File: {result.filename}")
        print("  The auto mode session will process this on its next turn.")
        return 0

    except ValueError as e:
        print(f"Error: {e}")
        return 1

    except AppendError as e:
        print(f"Error: {e}")
        return 1

    except Exception as e:
        print(f"Error: Failed to append instruction: {e}")
        return 1


def _fix_global_statusline_path() -> None:
    """Fix the global ~/.claude/settings.json statusline path to use ~/.amplihack/.claude/tools/statusline.sh.

    This ensures the statusline works in all directories, not just projects with amplihack installed locally.
    """
    global_settings_path = Path.home() / ".claude" / "settings.json"

    # Only proceed if settings.json exists
    if not global_settings_path.exists():
        return

    try:
        # Read current settings
        with open(global_settings_path, encoding="utf-8") as f:
            settings = json.load(f)

        # Check if statusLine needs updating
        statusline_config = settings.get("statusLine", {})
        current_command = statusline_config.get("command", "")
        correct_command = "~/.amplihack/.claude/tools/statusline.sh"

        # Only update project-relative paths (all variants end with .claude/tools/statusline.sh)
        if current_command != correct_command and current_command.endswith(
            ".claude/tools/statusline.sh"
        ):
            statusline_config["command"] = correct_command
            settings["statusLine"] = statusline_config

            # Write updated settings (atomic to prevent data loss)
            from .settings import write_json_atomic

            write_json_atomic(str(global_settings_path), settings)

            if _DEBUG:
                print(f"✓ Updated statusline path in {global_settings_path}")

    except (json.JSONDecodeError, OSError) as e:
        # Fail silently - don't break amplihack commands over this
        if _DEBUG:
            print(f"Warning: Could not update global statusline path: {e}")


def _ensure_amplihack_staged() -> None:
    """Ensure .claude/ files are staged to ~/.amplihack/.claude/ for non-Claude commands.

    This function populates the unified staging directory used by copilot, amplifier,
    rustyclawd, and codex commands. Only runs in UVX deployment mode.

    The staging process:
    1. Creates ~/.amplihack/.claude/ if it doesn't exist
    2. Copies essential framework files using copytree_manifest()
    3. Exits with code 1 if staging fails

    Raises:
        SystemExit: With code 1 if staging fails
    """
    # Only run in UVX deployment mode
    if not is_uvx_deployment():
        return

    # Clean up legacy skill directories before staging
    try:
        result = cleanup_legacy_skills()

        # Report cleaned directories (user-visible in debug mode)
        if result.cleaned:
            if _DEBUG:
                print(f"✓ Cleaned up {len(result.cleaned)} legacy skill directories")
                for cleaned_dir in result.cleaned:
                    logger.debug(f"  Removed: {cleaned_dir}")

        # Report skipped directories (user-visible, not just debug)
        if result.skipped:
            for skipped_dir, reason in result.skipped:
                logger.info(f"Skipped cleanup of {skipped_dir}: {reason}")

        # Report errors (user-visible, not just debug)
        if result.errors:
            for error_dir, error_msg in result.errors:
                logger.error(f"Failed to clean up {error_dir}: {error_msg}")

    except Exception as e:
        # Log error but don't fail staging
        logger.warning(f"Legacy skills cleanup failed: {e}")

    # Debug logging
    if _DEBUG:
        print("📦 Staging amplihack framework to ~/.amplihack/.claude/")

    # Determine source directory (package installation)
    import amplihack

    amplihack_src = Path(amplihack.__file__).parent

    # Unified staging directory for all commands
    staging_dir = Path.home() / ".amplihack" / ".claude"
    staging_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(staging_dir, 0o700)

    # Copy .claude/ files to staging directory
    copied = copytree_manifest(str(amplihack_src), str(staging_dir), ".claude")

    if not copied:
        print("❌ Failed to stage amplihack framework to ~/.amplihack/.claude/")
        print("   This is required for amplihack commands to work in UVX mode.")
        sys.exit(1)

    # Debug logging
    if _DEBUG:
        print(f"✓ Staged {len(copied)} directories to {staging_dir}")

    # Configure Claude Code hooks in ~/.claude/settings.json
    from .settings import ensure_settings_json

    ensure_settings_json()

    # Fix global ~/.claude/settings.json statusline path if needed
    _fix_global_statusline_path()
