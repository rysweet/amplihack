"""Fleet TUI Dashboard -- live terminal view of all fleet sessions.

Public API:
    FleetTUI: The dashboard application
    run_tui: Entry point function
    SessionView / VMView: Re-exported from _tui_data
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

from amplihack.fleet._constants import DEFAULT_CAPTURE_LINES, DEFAULT_TUI_REFRESH_SECONDS, SUBPROCESS_TIMEOUT_SECONDS
from amplihack.fleet._defaults import DEFAULT_EXCLUDE_VMS, ensure_azlin_context, get_azlin_path
from amplihack.fleet._tui_classify import classify_status
from amplihack.fleet._tui_data import SessionView, VMView
from amplihack.fleet._tui_parsers import parse_session_output, parse_vm_text
from amplihack.fleet._tui_render import (
    HIDE_CURSOR,
    SHOW_CURSOR,
    render_dashboard,
)

__all__ = ["FleetTUI", "run_tui", "SessionView", "VMView"]


@dataclass
class FleetTUI:
    """Live terminal dashboard for fleet sessions.

    Polls VMs via azlin, classifies session status, and renders
    a box-drawn dashboard with auto-refresh and keyboard control.
    """

    azlin_path: str = field(default_factory=get_azlin_path)
    refresh_interval: int = DEFAULT_TUI_REFRESH_SECONDS
    capture_lines: int = DEFAULT_CAPTURE_LINES
    exclude_vms: set[str] = field(default_factory=lambda: set(DEFAULT_EXCLUDE_VMS))

    def __post_init__(self) -> None:
        ensure_azlin_context(self.azlin_path)

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
            except (OSError, ValueError) as exc:
                # stdin closed or invalid fd -- fall back to sleeping
                logging.getLogger(__name__).warning("stdin select failed, falling back to sleep: %s", exc)
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
        1. Try az vm list (Azure CLI with JSON -- fast, no Bastion tunnels)
        2. Fallback: azlin CLI text output parsed from table
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
            logging.getLogger(__name__).warning("az vm list failed: %s", exc)
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logging.getLogger(__name__).warning("az vm list parse error: %s", exc)

        # Strategy 2: azlin CLI text output
        try:
            result = subprocess.run(
                [self.azlin_path, "list"],
                capture_output=True,
                text=True,
                timeout=SUBPROCESS_TIMEOUT_SECONDS,
            )
            if result.returncode == 0:
                return parse_vm_text(result.stdout)
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as exc:
            logging.getLogger(__name__).warning("azlin list failed: %s", exc)

        logging.getLogger(__name__).warning("All VM polling strategies failed")
        print(
            "ERROR: Could not retrieve VM list. Both 'az vm list' and 'azlin list' failed.\n"
            "Check: az CLI login ('az login'), azlin config, and network connectivity.",
            file=sys.stderr,
        )
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

    def _poll_vm(self, vm_name: str) -> list[SessionView]:
        """Poll a single VM for its tmux sessions and capture status info.

        Uses a single SSH call with a compound command to minimize latency.
        Falls back to a pseudo-TTY (virtual TTY) when standard subprocess
        fails — Bastion-tunnelled SSH often requires a TTY to complete.
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

    # Capture pane output
    echo "---CAPTURE---"
    tmux capture-pane -t "$SESS" -p -S -__CAPTURE_DEPTH__ 2>/dev/null || echo "(empty)"

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
        gather_cmd = gather_cmd.replace("__CAPTURE_DEPTH__", str(int(self.capture_lines)))
        cmd = [self.azlin_path, "connect", vm_name, "--no-tmux", "--", gather_cmd]

        # Strategy 1: standard subprocess (fast when SSH keys are cached)
        output = self._run_ssh_cmd(cmd)
        if output is not None:
            return parse_session_output(vm_name, output)

        # Strategy 2: virtual TTY — Bastion SSH often needs a PTY
        output = self._run_ssh_cmd_pty(cmd)
        if output is not None:
            return parse_session_output(vm_name, output)

        return []

    def _run_ssh_cmd(self, cmd: list[str]) -> str | None:
        """Run SSH command with standard subprocess. Returns output or None."""
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=SUBPROCESS_TIMEOUT_SECONDS,
            )
            if "===SESSION:" in result.stdout or "===NO_SESSIONS===" in result.stdout:
                return result.stdout
            if result.returncode != 0:
                logging.getLogger(__name__).debug(
                    "SSH cmd returned %d (no session markers)", result.returncode,
                )
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as exc:
            logging.getLogger(__name__).debug("SSH subprocess failed: %s", exc)
        return None

    def _run_ssh_cmd_pty(self, cmd: list[str]) -> str | None:
        """Run SSH command with a virtual PTY (for Bastion-tunnelled SSH).

        Azure Bastion SSH tunnelling requires a pseudo-terminal to
        complete the connection handshake.  This method allocates a PTY,
        auto-accepts the Bastion confirmation prompt, and captures output.
        """
        import os as _os
        import pty as _pty

        try:
            master_fd, slave_fd = _pty.openpty()
            proc = subprocess.Popen(
                cmd,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                close_fds=True,
            )
            _os.close(slave_fd)

            output_chunks: list[bytes] = []
            deadline = time.monotonic() + SUBPROCESS_TIMEOUT_SECONDS
            bastion_answered = False

            while time.monotonic() < deadline:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                try:
                    ready, _, _ = select.select([master_fd], [], [], min(2.0, remaining))
                    if ready:
                        chunk = _os.read(master_fd, 4096)
                        if not chunk:
                            break
                        output_chunks.append(chunk)

                        # Auto-accept Bastion confirmation prompt
                        if not bastion_answered and b"[Y/n]" in chunk:
                            _os.write(master_fd, b"y\n")
                            bastion_answered = True

                    elif proc.poll() is not None:
                        # Process exited, drain remaining output
                        while True:
                            try:
                                ready2, _, _ = select.select([master_fd], [], [], 0.5)
                                if ready2:
                                    chunk = _os.read(master_fd, 4096)
                                    if not chunk:
                                        break
                                    output_chunks.append(chunk)
                                else:
                                    break
                            except OSError:
                                break
                        break
                except OSError:
                    break

            _os.close(master_fd)

            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)

            text = b"".join(output_chunks).decode("utf-8", errors="replace")
            if "===SESSION:" in text or "===NO_SESSIONS===" in text:
                return text
            logging.getLogger(__name__).debug(
                "PTY SSH returned no session markers (%d bytes)", len(text),
            )
        except Exception as exc:
            logging.getLogger(__name__).warning("PTY SSH failed: %s", exc)
        return None



def run_tui(interval: int = DEFAULT_TUI_REFRESH_SECONDS, once: bool = False) -> None:
    """Entry point for the TUI dashboard.

    Args:
        interval: Refresh interval in seconds.
        once: If True, render one snapshot and exit.
    """
    app = FleetTUI(refresh_interval=interval)
    app.run(once=once)
