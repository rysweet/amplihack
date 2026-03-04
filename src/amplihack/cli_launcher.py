"""Launcher, session management, and auto mode handling for the amplihack CLI.

This module handles launching Claude/Copilot/Codex sessions, session tracking,
auto mode dispatch, and the append-instruction workflow.

Public API:
    launch_command: Handle the launch command with session tracking
    handle_auto_mode: Handle auto mode for claude, copilot, or codex commands
    handle_append_instruction: Handle --append flag to inject instructions
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from .cli_parser import EMOJI
from .docker import DockerManager
from .launcher import ClaudeLauncher
from .launcher.session_tracker import SessionTracker
from .proxy import ProxyConfig, ProxyManager

logger = logging.getLogger(__name__)


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

    from .launcher.session_tracker import SessionTracker

    # Detect nesting BEFORE any .claude/ operations
    original_cwd = None
    nesting_result = None

    if not subprocess_safe:
        from .cli_staging import ensure_amplihack_staged
        from .launcher.auto_stager import AutoStager
        from .launcher.nesting_detector import NestingDetector

        detector = NestingDetector()
        nesting_result = detector.detect_nesting(Path.cwd(), sys.argv)

        # Auto-stage if nested execution in source repo detected
        if nesting_result.requires_staging:
            print("\n\U0001f6a8 SELF-MODIFICATION PROTECTION ACTIVATED")
            print("   Running nested in amplihack source repository")
            print("   Auto-staging .claude/ to temp directory for safety")

            stager = AutoStager()
            original_cwd = Path.cwd()
            staging_result = stager.stage_for_nested_execution(
                original_cwd, f"nested-{os.getpid()}"
            )

            print(f"   \U0001f4c1 Staged to: {staging_result.temp_root}")
            print("   Your original .claude/ files are protected")

            # CRITICAL: Change to temp directory so all .claude/ operations happen there
            os.chdir(staging_result.temp_root)
            print(f"   \U0001f4c2 CWD changed to: {staging_result.temp_root}\n")

        # Ensure amplihack framework is staged to ~/.amplihack/.claude/
        ensure_amplihack_staged()

        # Auto-install missing SDK dependencies (e.g. agent-framework)
        # Uses --python sys.executable to target the running interpreter,
        # critical when launched via uvx (ephemeral venv != project .venv).
        try:
            from .dep_check import ensure_sdk_deps

            dep_result = ensure_sdk_deps()
            if not dep_result.all_ok:
                logger.warning("Some SDK deps could not be installed: %s", dep_result.missing)
        except Exception as e:
            logger.debug("SDK dep check skipped: %s", e)

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
        tracker.crash_session(session_id)
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
        if getattr(args, "with_proxy_config", None):
            docker_args.extend(["--with-proxy-config", args.with_proxy_config])
        if getattr(args, "checkout_repo", None):
            docker_args.extend(["--checkout-repo", args.checkout_repo])
        if claude_args:
            docker_args.append("--")
            docker_args.extend(claude_args)

        return docker_manager.run_command(docker_args)

    # In UVX mode, Claude uses --add-dir for both project directory and plugin directory

    proxy_manager = None
    system_prompt_path = None

    # Set up proxy if configuration provided
    if args.with_proxy_config:
        # For UVX mode, resolve relative paths from original directory
        if not Path(args.with_proxy_config).is_absolute():
            original_cwd = os.environ.get("AMPLIHACK_ORIGINAL_CWD", os.getcwd())
            config_path = Path(original_cwd) / args.with_proxy_config
            config_path = config_path.resolve()
        else:
            config_path = Path(args.with_proxy_config).resolve()

        if not config_path.exists():
            print(f"Error: Proxy configuration file not found: {config_path}")
            return 1

        print(f"Loading proxy configuration from: {config_path}")
        proxy_config = ProxyConfig(config_path)

        if not proxy_config.validate():
            print(
                "Error: Invalid proxy configuration. Check that OPENAI_API_KEY is set in your .env file"
            )
            return 1

        proxy_manager = ProxyManager(proxy_config)

        # When using proxy, automatically use Azure persistence prompt
        default_prompt = Path(__file__).parent / "prompts" / "azure_persistence.md"
        if default_prompt.exists():
            system_prompt_path = default_prompt
            print("Auto-appending Azure persistence prompt for proxy integration")

    # Launch Claude with checkout repo if specified
    launcher = ClaudeLauncher(
        proxy_manager=proxy_manager,
        append_system_prompt=system_prompt_path,
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


def handle_auto_mode(sdk: str, args: argparse.Namespace, cmd_args: list[str] | None) -> int | None:
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


__all__ = [
    "launch_command",
    "handle_auto_mode",
    "handle_append_instruction",
]
