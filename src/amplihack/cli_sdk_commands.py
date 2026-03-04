"""SDK launch command handlers for copilot, codex, and amplifier.

Public API:
    handle_copilot_command: Handle copilot launch command
    handle_codex_command: Handle codex launch command
    handle_amplifier_command: Handle amplifier launch command
"""

import argparse
import os

from .cli_launcher import handle_append_instruction, handle_auto_mode
from .cli_staging import ensure_amplihack_staged


def handle_copilot_command(
    args: argparse.Namespace, claude_args: list[str] | None
) -> int:
    """Handle copilot launch command.

    Args:
        args: Parsed command line arguments
        claude_args: Additional arguments to forward

    Returns:
        Exit code
    """
    from .launcher.copilot import launch_copilot

    # Handle append mode FIRST (before any other initialization)
    if getattr(args, "append", None):
        return handle_append_instruction(args)

    # Ensure amplihack framework is staged (skip in subprocess-safe mode)
    if not getattr(args, "subprocess_safe", False):
        ensure_amplihack_staged()

    # Handle auto mode
    exit_code = handle_auto_mode("copilot", args, claude_args)
    if exit_code is not None:
        return exit_code

    # Handle --no-reflection flag (disable always wins priority)
    if getattr(args, "no_reflection", False):
        os.environ["AMPLIHACK_SKIP_REFLECTION"] = "1"

    # Normal copilot launch
    has_prompt = claude_args and "-p" in claude_args
    return launch_copilot(claude_args, interactive=not has_prompt)


def handle_codex_command(
    args: argparse.Namespace, claude_args: list[str] | None
) -> int:
    """Handle codex launch command.

    Args:
        args: Parsed command line arguments
        claude_args: Additional arguments to forward

    Returns:
        Exit code
    """
    from .launcher.codex import launch_codex

    # Handle append mode FIRST (before any other initialization)
    if getattr(args, "append", None):
        return handle_append_instruction(args)

    # Ensure amplihack framework is staged (skip in subprocess-safe mode)
    if not getattr(args, "subprocess_safe", False):
        ensure_amplihack_staged()

    # Handle auto mode
    exit_code = handle_auto_mode("codex", args, claude_args)
    if exit_code is not None:
        return exit_code

    # Handle --no-reflection flag (disable always wins priority)
    if getattr(args, "no_reflection", False):
        os.environ["AMPLIHACK_SKIP_REFLECTION"] = "1"

    # Normal codex launch
    has_prompt = claude_args and "-p" in claude_args
    return launch_codex(claude_args, interactive=not has_prompt)


def handle_amplifier_command(
    args: argparse.Namespace, claude_args: list[str] | None
) -> int:
    """Handle amplifier launch command.

    Args:
        args: Parsed command line arguments
        claude_args: Additional arguments to forward

    Returns:
        Exit code
    """
    from .launcher.amplifier import launch_amplifier, launch_amplifier_auto

    # Early exit: append mode
    if getattr(args, "append", None):
        return handle_append_instruction(args)

    # Ensure amplihack framework is staged (skip in subprocess-safe mode)
    if not getattr(args, "subprocess_safe", False):
        ensure_amplihack_staged()

    # Environment setup
    if getattr(args, "no_reflection", False):
        os.environ["AMPLIHACK_SKIP_REFLECTION"] = "1"

    # All amplifier args come after -- separator (claude_args)
    # Extract prompt from args if present (for auto mode check)
    prompt = None
    if claude_args and "-p" in claude_args:
        idx = claude_args.index("-p")
        if idx + 1 < len(claude_args):
            prompt = claude_args[idx + 1]

    # Auto mode - Amplifier manages its own execution loop
    if getattr(args, "auto", False):
        if not prompt:
            print('Error: --auto requires a prompt via -- -p "prompt"')
            return 1
        return launch_amplifier_auto(prompt)

    # Normal launch - pass all args after -- directly to amplifier
    return launch_amplifier(args=claude_args or [])


__all__ = [
    "handle_amplifier_command",
    "handle_codex_command",
    "handle_copilot_command",
]
