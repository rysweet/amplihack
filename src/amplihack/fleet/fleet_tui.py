"""Fleet TUI Dashboard -- live terminal view of all fleet sessions.

A standalone auto-refreshing dashboard showing VM status, session states,
and agent activity. Designed to run in its own tmux session.

Uses ONLY Python standard library -- ANSI escape codes for terminal control,
select() for non-blocking input, termios for raw mode.

Usage:
    fleet tui                    # Interactive TUI
    fleet tui --interval 30      # Refresh every 30 seconds
    fleet tui --once             # Single snapshot then exit

Public API:
    FleetTUI: The dashboard application
    run_tui: Entry point function
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import select
import termios
import time
import tty
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

__all__ = ["FleetTUI", "run_tui"]

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
    "thinking":      ("@", GREEN,  "thinking"),
    "working":       ("@", GREEN,  "working"),
    "running":       ("@", GREEN,  "running"),
    "waiting_input": ("@", GREEN,  "waiting"),
    "idle":          ("*", YELLOW, "idle"),
    "shell":         ("o", DIM,    "shell"),
    "empty":         ("o", DIM,    "empty"),
    "no_session":    ("o", DIM,    "empty"),
    "unknown":       ("o", DIM,    "unknown"),
    "error":         ("x", RED,    "error"),
    "completed":     ("v", BLUE,   "done"),
}

# Mapping for UTF-8 capable terminals
STATUS_ICONS_UTF8 = {
    "thinking":      "\u25c9",  # filled circle with dot
    "working":       "\u25c9",
    "running":       "\u25c9",
    "waiting_input": "\u25c9",
    "idle":          "\u25cf",  # filled circle
    "shell":         "\u25cb",  # empty circle
    "empty":         "\u25cb",
    "no_session":    "\u25cb",
    "unknown":       "\u25cb",
    "error":         "\u2717",  # ballot x
    "completed":     "\u2713",  # check mark
}


@dataclass
class SessionView:
    """Display-oriented view of a single session."""

    vm_name: str
    session_name: str
    status: str = "unknown"  # thinking, working, idle, shell, empty, error, completed
    branch: str = ""
    pr: str = ""
    last_line: str = ""
    repo: str = ""


@dataclass
class VMView:
    """Display-oriented view of a single VM."""

    name: str
    region: str = ""
    is_running: bool = True
    sessions: list[SessionView] = field(default_factory=list)


@dataclass
class FleetTUI:
    """Live terminal dashboard for fleet sessions.

    Polls VMs via azlin, classifies session status, and renders
    a box-drawn dashboard with auto-refresh and keyboard control.
    """

    azlin_path: str = field(
        default_factory=lambda: os.environ.get(
            "AZLIN_PATH",
            shutil.which("azlin") or "/home/azureuser/src/azlin/.venv/bin/azlin",
        )
    )
    refresh_interval: int = 60
    exclude_vms: set[str] = field(
        default_factory=lambda: {"fleet-exp-1", "fleet-exp-2"}
    )

    def run(self, once: bool = False) -> None:
        """Main TUI loop with non-blocking keyboard input.

        Args:
            once: If True, render one snapshot and exit.
        """
        # Store original terminal settings so we can restore on exit
        if sys.stdin.isatty():
            old_settings = termios.tcgetattr(sys.stdin)
        else:
            old_settings = None

        try:
            if old_settings is not None:
                tty.setcbreak(sys.stdin.fileno())
                sys.stdout.write(HIDE_CURSOR)
                sys.stdout.flush()

            while True:
                vms = self.refresh()
                self.render(vms)

                if once:
                    break

                key = self._wait_with_keypress(self.refresh_interval)
                if key == "q":
                    break
                elif key == "r":
                    continue  # immediate refresh
                # else: timeout expired, auto-refresh

        except KeyboardInterrupt:
            pass
        finally:
            if old_settings is not None:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                sys.stdout.write(SHOW_CURSOR)
                sys.stdout.flush()
            # Print a newline so the shell prompt starts clean
            print()

    def refresh(self) -> list[VMView]:
        """Poll all VMs and collect session status.

        Returns a list of VMView objects sorted by VM name.
        """
        vm_list = self._get_vm_list()
        result: list[VMView] = []

        for vm_name, region, is_running in vm_list:
            if vm_name in self.exclude_vms:
                continue

            vm_view = VMView(name=vm_name, region=region, is_running=is_running)

            if is_running:
                vm_view.sessions = self._poll_vm(vm_name)

            result.append(vm_view)

        result.sort(key=lambda v: v.name)
        return result

    def render(self, vms: list[VMView]) -> None:
        """Render the dashboard to terminal using ANSI codes."""
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
        lines.append(self._boxline("", inner, width))

        # VM sections
        for vm in vms:
            if not vm.is_running:
                vm_header = f"  {DIM}[{vm.name}] {vm.region} (stopped){RESET}"
                lines.append(self._boxline(vm_header, inner, width, raw_len=len(f"  [{vm.name}] {vm.region} (stopped)")))
                continue

            # VM header line with a dashed separator
            dash_len = inner - len(f"  [{vm.name}] {vm.region} ") - 2
            if dash_len < 4:
                dash_len = 4
            dashes = "\u2500" * dash_len
            vm_header = f"  {BOLD}[{vm.name}]{RESET} {DIM}{vm.region}{RESET} {DIM}{dashes}{RESET}"
            raw_header_len = len(f"  [{vm.name}] {vm.region} ") + dash_len
            lines.append(self._boxline(vm_header, inner, width, raw_len=raw_header_len))

            if not vm.sessions:
                empty_line = f"    {DIM}(no sessions){RESET}"
                lines.append(self._boxline(empty_line, inner, width, raw_len=len("    (no sessions)")))
            else:
                for sess in vm.sessions:
                    sess_line, raw_len = self._format_session(sess, inner)
                    lines.append(self._boxline(sess_line, inner, width, raw_len=raw_len))

            # Blank line between VMs
            lines.append(self._boxline("", inner, width))

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
        lines.append(self._boxline(summary, inner, width, raw_len=raw_summary_len))

        # Footer: controls
        controls = f"  {DIM}Next refresh in {self.refresh_interval}s    Press q to quit, r to refresh now{RESET}"
        raw_controls_len = len(f"  Next refresh in {self.refresh_interval}s    Press q to quit, r to refresh now")
        lines.append(self._boxline(controls, inner, width, raw_len=raw_controls_len))

        # Bottom border
        lines.append(f"{BOLD}{BL}{HL * (width - 2)}{BR}{RESET}")

        sys.stdout.write("\n".join(lines))
        sys.stdout.flush()

    def _boxline(
        self, content: str, inner: int, width: int, raw_len: int = 0
    ) -> str:
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

    def _format_session(self, sess: SessionView, inner: int) -> tuple[str, int]:
        """Format a single session line with icon and color.

        Returns (formatted_string, raw_visible_length).
        """
        icon_char = STATUS_ICONS_UTF8.get(sess.status, "\u25cb")
        _fallback, color, label = STATUS_MAP.get(
            sess.status, ("o", DIM, sess.status)
        )

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

    def _wait_with_keypress(self, seconds: int) -> Optional[str]:
        """Wait for N seconds, returning early if a key is pressed.

        Returns the key character if pressed, or None on timeout.
        Uses select() for non-blocking stdin polling.
        """
        if not sys.stdin.isatty():
            time.sleep(seconds)
            return None

        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                ready, _, _ = select.select([sys.stdin], [], [], min(1.0, remaining))
                if ready:
                    ch = sys.stdin.read(1)
                    return ch
            except (OSError, ValueError):
                # stdin closed or invalid fd
                time.sleep(min(1.0, remaining))
        return None

    def refresh_all(self) -> list[VMView]:
        """Poll all VMs including excluded ones (for 'All Sessions' tab).

        Returns a list of VMView objects sorted by VM name.
        """
        vm_list = self._get_vm_list()
        result: list[VMView] = []

        for vm_name, region, is_running in vm_list:
            # No exclude filter -- show everything
            vm_view = VMView(name=vm_name, region=region, is_running=is_running)

            if is_running:
                vm_view.sessions = self._poll_vm(vm_name)

            result.append(vm_view)

        result.sort(key=lambda v: v.name)
        return result

    # ------------------------------------------------------------------
    # Data gathering: azlin + tmux polling
    # ------------------------------------------------------------------

    def _get_vm_list(self) -> list[tuple[str, str, bool]]:
        """Get VM list from azlin.

        Returns list of (name, region, is_running) tuples.

        Strategy:
        1. Try azlin Python API (VMManager.list_vms) -- most reliable
        2. Fallback: azlin CLI text output parsed from table
        """
        # Strategy 1: az vm list (Azure CLI with JSON — fast, no Bastion tunnels)
        try:
            import json as _json
            rg = self._read_azlin_resource_group()
            result = subprocess.run(
                ["az", "vm", "list", "--resource-group", rg, "--show-details", "--output", "json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                vms_data = _json.loads(result.stdout)
                return [
                    (
                        vm.get("name", ""),
                        vm.get("location", ""),
                        "running" in (vm.get("powerState", "") or "").lower(),
                    )
                    for vm in vms_data
                    if vm.get("name")
                ]
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
        except Exception:
            pass

        # Strategy 2: azlin CLI text output
        try:
            result = subprocess.run(
                [self.azlin_path, "list"],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                return self._parse_vm_text(result.stdout)
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass

        return []

    def _read_azlin_resource_group(self) -> str:
        """Read the default resource group from ~/.azlin/config.toml."""
        config_path = Path.home() / ".azlin" / "config.toml"
        if config_path.exists():
            for line in config_path.read_text().splitlines():
                if line.startswith("default_resource_group"):
                    # Parse: default_resource_group = "value"
                    _, _, value = line.partition("=")
                    return value.strip().strip('"').strip("'")
        return "rysweet-linux-vm-pool"  # sensible default

    def _parse_vm_text(self, text: str) -> list[tuple[str, str, bool]]:
        """Parse text table from azlin list."""
        vms = []
        lines = text.strip().split("\n")
        in_table = False

        for line in lines:
            if "Session" in line and ("Tmux" in line or "Status" in line):
                in_table = True
                continue
            if line.startswith(("\u2523", "\u2521", "\u2514", "+")):
                continue
            if not in_table:
                continue

            if "\u2502" in line or "|" in line:
                sep = "\u2502" if "\u2502" in line else "|"
                parts = [p.strip() for p in line.split(sep) if p.strip()]
                if len(parts) >= 4:
                    name = parts[0]
                    if not name:
                        continue
                    status = parts[3] if len(parts) > 3 else ""
                    region = parts[5] if len(parts) > 5 else ""
                    is_running = "run" in status.lower()
                    vms.append((name, region, is_running))

        return vms

    def _poll_vm(self, vm_name: str) -> list[SessionView]:
        """Poll a single VM for its tmux sessions and capture status info.

        Uses a single SSH call with a compound command to minimize latency.
        """
        # Compound command: list sessions, then capture each pane + git info
        gather_cmd = r"""
# List tmux sessions
SESSIONS=$(tmux list-sessions -F '#{session_name}' 2>/dev/null)
if [ -z "$SESSIONS" ]; then
    echo '===NO_SESSIONS==='
    exit 0
fi

for SESS in $SESSIONS; do
    echo "===SESSION:${SESS}==="

    # Capture last 15 lines of the pane
    echo "---CAPTURE---"
    tmux capture-pane -t "$SESS" -p -S -15 2>/dev/null || echo "(empty)"

    # Get working directory and git info
    echo "---GIT---"
    CWD=$(tmux display-message -t "$SESS" -p '#{pane_current_path}' 2>/dev/null)
    if [ -n "$CWD" ] && [ -d "$CWD/.git" ]; then
        cd "$CWD" 2>/dev/null
        BRANCH=$(git branch --show-current 2>/dev/null)
        echo "BRANCH:${BRANCH}"
        # Check for open PR
        PR=$(git log --oneline -1 --format='%s' 2>/dev/null | grep -oP 'PR #\K\d+' || true)
        if [ -n "$PR" ]; then
            echo "PR:#${PR}"
        fi
    fi
    echo "---END---"
done
"""
        try:
            result = subprocess.run(
                [self.azlin_path, "connect", vm_name, "--no-tmux", "--", gather_cmd],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode == 0:
                return self._parse_session_output(vm_name, result.stdout)
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass

        return []

    def _parse_session_output(self, vm_name: str, output: str) -> list[SessionView]:
        """Parse the compound tmux output for a VM into SessionView objects."""
        sessions: list[SessionView] = []

        if "===NO_SESSIONS===" in output:
            return sessions

        # Split by session markers
        parts = output.split("===SESSION:")
        for part in parts[1:]:  # skip everything before first marker
            if "===" not in part:
                continue

            # Extract session name
            header_end = part.index("===")
            session_name = part[:header_end].strip()
            rest = part[header_end + 3:]

            view = SessionView(vm_name=vm_name, session_name=session_name)

            # Extract capture
            if "---CAPTURE---" in rest and "---GIT---" in rest:
                capture_start = rest.index("---CAPTURE---") + len("---CAPTURE---")
                capture_end = rest.index("---GIT---")
                capture = rest[capture_start:capture_end].strip()

                if capture and capture != "(empty)":
                    view.status = self._classify_status(capture)
                    # Get last meaningful line for display
                    meaningful_lines = [
                        l.strip()
                        for l in capture.split("\n")
                        if l.strip() and not l.strip().startswith("\u2509")
                    ]
                    if meaningful_lines:
                        view.last_line = meaningful_lines[-1][:60]
                else:
                    view.status = "empty"

            # Extract git info
            if "---GIT---" in rest:
                git_start = rest.index("---GIT---") + len("---GIT---")
                git_end = rest.index("---END---") if "---END---" in rest else len(rest)
                git_section = rest[git_start:git_end].strip()

                for line in git_section.split("\n"):
                    line = line.strip()
                    if line.startswith("BRANCH:"):
                        view.branch = line[7:]
                    elif line.startswith("PR:"):
                        view.pr = line[3:]

            sessions.append(view)

        return sessions

    def _classify_status(self, tmux_text: str) -> str:
        """Classify session status from tmux capture text.

        Reuses patterns from fleet_session_reasoner._infer_status:
        - Active tool indicators (filled circle, streaming) = thinking
        - Processing markers = thinking
        - Claude Code prompt with status bar = idle/waiting
        - Shell prompt = shell
        - Error markers = error
        - Completion markers = completed
        - Substantial output = running
        """
        last_lines = tmux_text.strip().split("\n")[-10:]
        combined = "\n".join(last_lines)
        combined_lower = combined.lower()
        last_line = last_lines[-1].strip() if last_lines else ""

        # --- THINKING/WORKING (highest priority) ---
        for line in reversed(last_lines):
            stripped = line.strip()
            if not stripped:
                continue
            # Active Claude Code tool call
            if stripped.startswith("\u25cf") and not stripped.startswith("\u25cf Bash("):
                return "thinking"
            # Streaming output
            if stripped.startswith("\u23bf"):
                return "thinking"
            # Processing timer
            if "\u273b" in stripped and (
                "for" in stripped.lower() or "saut" in stripped.lower()
            ):
                return "thinking"
            break

        # Copilot thinking indicators
        if any(p in combined_lower for p in ["thinking...", "running:", "loading"]):
            return "thinking"

        # Claude Code tool call with output
        tool_prefixes = [
            "\u25cf Bash(",
            "\u25cf Read(",
            "\u25cf Write(",
            "\u25cf Edit(",
        ]
        if any(p in combined for p in tool_prefixes):
            if "\u23f5\u23f5" in last_line:
                return "idle"
            return "thinking"

        # --- ERROR ---
        if any(p in combined_lower for p in ["error:", "traceback", "fatal:", "panic:"]):
            return "error"

        # --- COMPLETED ---
        if any(p in combined for p in ["GOAL_STATUS: ACHIEVED", "Workflow Complete"]):
            return "completed"
        if any(p in combined for p in ["gh pr create", "PR #", "pull request"]):
            if any(p in combined_lower for p in ["created", "opened", "merged"]):
                return "completed"

        # --- IDLE (shell prompt, no agent) ---
        if last_line.endswith("$ ") or last_line.endswith("$"):
            return "shell"

        # Claude Code idle prompt
        if last_line.strip() == "\u276f" or last_line.strip().endswith("\u276f"):
            if not any("\u23f5\u23f5" in l for l in last_lines[-3:]):
                return "shell"
            else:
                return "idle"

        # --- Default: running if there is substantial output ---
        if len(combined.strip()) > 50:
            return "running"

        return "unknown"


def run_tui(interval: int = 60, once: bool = False) -> None:
    """Entry point for the TUI dashboard.

    Args:
        interval: Refresh interval in seconds.
        once: If True, render one snapshot and exit.
    """
    app = FleetTUI(refresh_interval=interval)
    app.run(once=once)
