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

import json
import logging
import select
import subprocess
import sys
import termios
import time
import tty
from dataclasses import dataclass, field
from pathlib import Path

from amplihack.fleet._defaults import DEFAULT_EXCLUDE_VMS, get_azlin_path
from amplihack.fleet._tui_render import (
    HIDE_CURSOR,
    SHOW_CURSOR,
    render_dashboard,
)

__all__ = ["FleetTUI", "run_tui"]


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

    azlin_path: str = field(default_factory=get_azlin_path)
    refresh_interval: int = 60
    exclude_vms: set[str] = field(default_factory=lambda: set(DEFAULT_EXCLUDE_VMS))

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
                if key == "r":
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
        return list(self.refresh_iter())

    def refresh_iter(self, *, exclude: bool = True):
        """Yield VMView objects one at a time as each VM is polled.

        Args:
            exclude: If True, skip VMs in self.exclude_vms.

        Yields:
            VMView for each polled VM (sessions populated for running VMs).
        """
        vm_list = self._get_vm_list()

        for vm_name, region, is_running in sorted(vm_list, key=lambda x: x[0]):
            if exclude and vm_name in self.exclude_vms:
                continue

            vm_view = VMView(name=vm_name, region=region, is_running=is_running)

            if is_running:
                vm_view.sessions = self._poll_vm(vm_name)

            yield vm_view

    def render(self, vms: list[VMView]) -> None:
        """Render the dashboard to terminal using ANSI codes."""
        output = render_dashboard(vms, self.refresh_interval)
        sys.stdout.write(output)
        sys.stdout.flush()

    def _wait_with_keypress(self, seconds: int) -> str | None:
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
        return list(self.refresh_iter(exclude=False))

    # ------------------------------------------------------------------
    # Data gathering: azlin + tmux polling
    # ------------------------------------------------------------------

    def _get_vm_list(self) -> list[tuple[str, str, bool]]:
        """Get VM list from azlin.

        Returns list of (name, region, is_running) tuples.

        Strategy:
        1. Try azlin Python API (VMManager.list_vms) -- most reliable
        2. Strategy 2: azlin CLI text output parsed from table
        """
        # Strategy 1: az vm list (Azure CLI with JSON -- fast, no Bastion tunnels)
        try:
            rg = self._read_azlin_resource_group()
            result = subprocess.run(
                ["az", "vm", "list", "--resource-group", rg, "--show-details", "--output", "json"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                vms_data = json.loads(result.stdout)
                return [
                    (
                        vm.get("name", ""),
                        vm.get("location", ""),
                        "running" in (vm.get("powerState", "") or "").lower(),
                    )
                    for vm in vms_data
                    if vm.get("name")
                ]
        except ValueError:
            pass  # No resource group configured -- fall through to azlin CLI
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as exc:
            logging.getLogger(__name__).debug("az vm list failed: %s", exc)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logging.getLogger(__name__).debug("az vm list parse error: %s", exc)

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
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as exc:
            logging.getLogger(__name__).debug("azlin list failed: %s", exc)

        logging.getLogger(__name__).warning("All VM polling strategies failed")
        return []

    def _read_azlin_resource_group(self) -> str:
        """Read the default resource group from ~/.azlin/config.toml.

        Raises:
            ValueError: If no resource group is configured.
        """
        config_path = Path.home() / ".azlin" / "config.toml"
        if config_path.exists():
            for line in config_path.read_text().splitlines():
                if line.startswith("default_resource_group"):
                    # Parse: default_resource_group = "value"
                    _, _, value = line.partition("=")
                    return value.strip().strip('"').strip("'")
        raise ValueError(
            "No resource group configured. Set default_resource_group in ~/.azlin/config.toml"
        )

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
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as exc:
            logging.getLogger(__name__).debug("Poll VM %s failed: %s", vm_name, exc)

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
            rest = part[header_end + 3 :]

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
        # NOTE: This is a simplified status classifier for TUI display purposes.
        # The canonical status classifier is infer_agent_status() in fleet_session_reasoner.py.
        # These two systems return different value sets -- unification is tracked in issue #2799.
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
            if "\u273b" in stripped and ("for" in stripped.lower() or "saut" in stripped.lower()):
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
