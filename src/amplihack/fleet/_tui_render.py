"""Fleet TUI rendering -- ANSI dashboard drawing extracted from FleetTUI.

Standalone rendering functions that take data and return strings.
No I/O, no subprocess calls, no terminal state -- pure formatting.

Public API:
    render_dashboard: Build the full dashboard string from VM data
    boxline: Wrap content in box-drawing vertical lines
    format_session: Format a single session line with icon and color
"""

from __future__ import annotations

import shutil
from datetime import datetime

__all__ = ["render_dashboard", "boxline", "format_session"]

# ---------------------------------------------------------------------------
# ANSI escape codes
# ---------------------------------------------------------------------------
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BLUE = "\033[34m"
CYAN = "\033[36m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"
CLEAR = "\033[2J\033[H"  # Clear screen, cursor to top
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

# Box drawing characters (Unicode)
TL = "\u2554"  # top-left double
TR = "\u2557"  # top-right double
BL = "\u255a"  # bottom-left double
BR = "\u255d"  # bottom-right double
HL = "\u2550"  # horizontal double
VL = "\u2551"  # vertical double
ML = "\u2560"  # middle-left junction
MR = "\u2563"  # middle-right junction

# Status icons and their ANSI colors
STATUS_MAP = {
    "thinking": ("@", GREEN, "thinking"),
    "working": ("@", GREEN, "working"),
    "running": ("@", GREEN, "running"),
    "waiting_input": ("@", GREEN, "waiting"),
    "idle": ("*", YELLOW, "idle"),
    "shell": ("o", DIM, "shell"),
    "empty": ("o", DIM, "empty"),
    "no_session": ("o", DIM, "empty"),
    "unknown": ("o", DIM, "unknown"),
    "error": ("x", RED, "error"),
    "completed": ("v", BLUE, "done"),
}

# Mapping for UTF-8 capable terminals
STATUS_ICONS_UTF8 = {
    "thinking": "\u25c9",  # filled circle with dot
    "working": "\u25c9",
    "running": "\u25c9",
    "waiting_input": "\u25c9",
    "idle": "\u25cf",  # filled circle
    "shell": "\u25cb",  # empty circle
    "empty": "\u25cb",
    "no_session": "\u25cb",
    "unknown": "\u25cb",
    "error": "\u2717",  # ballot x
    "completed": "\u2713",  # check mark
}


def boxline(content: str, inner: int, width: int, raw_len: int = 0) -> str:
    """Wrap content in box-drawing vertical lines with right-padding.

    Args:
        content: The formatted content (may contain ANSI codes).
        inner: The usable character width inside the box.
        width: Total box width.
        raw_len: Length of the visible (non-ANSI) text. If 0, uses len(content).
    """
    if raw_len == 0:
        raw_len = len(content)
    pad = inner - raw_len
    if pad < 0:
        pad = 0
    return f"{BOLD}{VL}{RESET} {content}{' ' * pad} {BOLD}{VL}{RESET}"


def format_session(sess, inner: int) -> tuple[str, int]:
    """Format a single session line with icon and color.

    Args:
        sess: A SessionView instance (or any object with .status, .session_name,
              .pr, .branch, .last_line attributes).
        inner: The usable character width inside the box.

    Returns (formatted_string, raw_visible_length).
    """
    icon_char = STATUS_ICONS_UTF8.get(sess.status, "\u25cb")
    _ascii_icon, color, label = STATUS_MAP.get(sess.status, ("o", DIM, sess.status))

    # Build the right-side info: status label + branch/PR + last_line
    status_label = label.upper()
    info_parts = [status_label]

    if sess.pr:
        info_parts.append(f"PR {sess.pr}")
    if sess.branch:
        # Truncate long branch names
        branch_display = sess.branch
        if len(branch_display) > 24:
            branch_display = branch_display[:21] + "..."
        info_parts.append(branch_display)
    if sess.last_line:
        # Truncate last line to fit
        max_last = inner - len(sess.session_name) - len(" ".join(info_parts)) - 12
        if max_last < 10:
            max_last = 10
        last_display = sess.last_line[:max_last]
        if len(sess.last_line) > max_last:
            last_display += "..."
        info_parts.append(last_display)

    info = "  ".join(info_parts)

    # Truncate session name if needed
    name = sess.session_name
    if len(name) > 18:
        name = name[:15] + "..."

    formatted = f"    {color}{icon_char}{RESET} {BOLD}{name}{RESET}  {DIM}{info}{RESET}"
    raw_len = 4 + 1 + 1 + len(name) + 2 + len(info)  # icon + space + name + gap + info

    return formatted, raw_len


def render_dashboard(vms: list, refresh_interval: int, cols: int = 0) -> str:
    """Build the full dashboard string from VM data.

    Args:
        vms: List of VMView objects.
        refresh_interval: Seconds between refreshes (shown in footer).
        cols: Terminal width override. If 0, auto-detects.

    Returns the complete dashboard string ready for sys.stdout.write().
    """
    if cols <= 0:
        cols = shutil.get_terminal_size().columns
    width = min(cols - 2, 80)  # cap at 80 for readability
    inner = width - 4  # inside the box border + padding

    now = datetime.now().strftime("%H:%M:%S")
    total_vms = len(vms)
    total_sessions = sum(len(v.sessions) for v in vms)

    # Classify sessions for footer summary
    active_count = 0
    idle_count = 0
    shell_count = 0
    error_count = 0
    for v in vms:
        for s in v.sessions:
            if s.status in ("thinking", "working", "running", "waiting_input"):
                active_count += 1
            elif s.status == "idle":
                idle_count += 1
            elif s.status in ("error",):
                error_count += 1
            else:
                shell_count += 1

    lines: list[str] = []

    # Build the screen
    lines.append(CLEAR)

    # Top border
    lines.append(f"{BOLD}{TL}{HL * (width - 2)}{TR}{RESET}")

    # Title bar
    title = "FLEET DASHBOARD"
    stats = f"Updated: {now}    [{total_vms} VMs / {total_sessions} sessions]"
    title_line = f"  {BOLD}{title}{RESET}"
    # Pad the stats to the right
    padding = inner - len(title) - 2 - len(stats)
    if padding < 1:
        padding = 1
    title_line += " " * padding + f"{DIM}{stats}{RESET}"
    lines.append(f"{BOLD}{VL}{RESET}{title_line}{BOLD}{VL}{RESET}")

    # Separator
    lines.append(f"{BOLD}{ML}{HL * (width - 2)}{MR}{RESET}")

    # Empty line
    lines.append(boxline("", inner, width))

    # VM sections
    for vm in vms:
        if not vm.is_running:
            vm_header = f"  {DIM}[{vm.name}] {vm.region} (stopped){RESET}"
            lines.append(
                boxline(
                    vm_header, inner, width, raw_len=len(f"  [{vm.name}] {vm.region} (stopped)")
                )
            )
            continue

        # VM header line with a dashed separator
        dash_len = inner - len(f"  [{vm.name}] {vm.region} ") - 2
        if dash_len < 4:
            dash_len = 4
        dashes = "\u2500" * dash_len
        vm_header = f"  {BOLD}[{vm.name}]{RESET} {DIM}{vm.region}{RESET} {DIM}{dashes}{RESET}"
        raw_header_len = len(f"  [{vm.name}] {vm.region} ") + dash_len
        lines.append(boxline(vm_header, inner, width, raw_len=raw_header_len))

        if not vm.sessions:
            empty_line = f"    {DIM}(no sessions){RESET}"
            lines.append(boxline(empty_line, inner, width, raw_len=len("    (no sessions)")))
        else:
            for sess in vm.sessions:
                sess_line, raw_len = format_session(sess, inner)
                lines.append(boxline(sess_line, inner, width, raw_len=raw_len))

        # Blank line between VMs
        lines.append(boxline("", inner, width))

    # Footer separator
    lines.append(f"{BOLD}{ML}{HL * (width - 2)}{MR}{RESET}")

    # Footer: status summary
    summary_parts = []
    if active_count:
        summary_parts.append(f"{GREEN}\u25c9 active: {active_count}{RESET}")
    if idle_count:
        summary_parts.append(f"{YELLOW}\u25cf idle: {idle_count}{RESET}")
    if shell_count:
        summary_parts.append(f"{DIM}\u25cb shell/empty: {shell_count}{RESET}")
    if error_count:
        summary_parts.append(f"{RED}\u2717 error: {error_count}{RESET}")
    if summary_parts:
        summary = "  " + "  ".join(summary_parts)
        raw_summary_len = 2 + sum(
            len(f"X {label}: {count}  ")
            for label, count in [
                ("active", active_count),
                ("idle", idle_count),
                ("shell/empty", shell_count),
                ("error", error_count),
            ]
            if count
        )
    else:
        summary = f"  {DIM}(no sessions){RESET}"
        raw_summary_len = len("  (no sessions)")
    lines.append(boxline(summary, inner, width, raw_len=raw_summary_len))

    # Footer: controls
    controls = (
        f"  {DIM}Next refresh in {refresh_interval}s    Press q to quit, r to refresh now{RESET}"
    )
    raw_controls_len = len(
        f"  Next refresh in {refresh_interval}s    Press q to quit, r to refresh now"
    )
    lines.append(boxline(controls, inner, width, raw_len=raw_controls_len))

    # Bottom border
    lines.append(f"{BOLD}{BL}{HL * (width - 2)}{BR}{RESET}")

    return "\n".join(lines)
