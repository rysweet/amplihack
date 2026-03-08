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
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

from amplihack.fleet._constants import AZ_CLI_TIMEOUT_SECONDS, DEFAULT_CAPTURE_LINES, DEFAULT_TUI_REFRESH_SECONDS, MAX_CAPTURE_LINES, SUBPROCESS_TIMEOUT_SECONDS
from amplihack.fleet._defaults import DEFAULT_EXCLUDE_VMS, ensure_azlin_context, get_azlin_path, get_existing_tunnels
from amplihack.fleet._tui_classify import classify_status
from amplihack.fleet._tui_data import SessionView, VMView
from amplihack.fleet._tui_parsers import parse_hostname, parse_session_output, parse_vm_text
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
        self.capture_lines = max(1, min(self.capture_lines, MAX_CAPTURE_LINES))
        ensure_azlin_context(self.azlin_path)
        # Cache existing Bastion tunnels for reuse during polling
        self._tunnels: dict[str, int] = get_existing_tunnels(self.azlin_path)

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
        """Poll all managed VMs (excluding shared-NFS duplicates).

        Uses ThreadPoolExecutor to poll VMs concurrently, reducing
        wall-clock time from O(N * SSH_timeout) to O(SSH_timeout).

        Excludes VMs in ``self.exclude_vms`` because those share NFS home
        directories with other VMs, causing identical tmux sessions to
        appear under multiple VM names.

        Returns a list of VMView objects sorted by VM name.
        """
        vm_list = self._get_vm_list()
        if not vm_list:
            return []

        vms_to_poll: list[tuple[str, str, bool]] = sorted(
            [v for v in vm_list if v[0] not in self.exclude_vms],
            key=lambda x: x[0],
        )
        results: list[VMView] = []

        def _poll_one(entry: tuple[str, str, bool]) -> VMView:
            vm_name, region, is_running = entry
            vm_view = VMView(name=vm_name, region=region, is_running=is_running)
            if is_running:
                vm_view.sessions = self._poll_vm(vm_name)
            return vm_view

        # Poll VMs concurrently — each SSH call is I/O-bound
        with ThreadPoolExecutor(max_workers=min(8, len(vms_to_poll))) as executor:
            futures = {executor.submit(_poll_one, entry): entry for entry in vms_to_poll}
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as exc:
                    entry = futures[future]
                    logging.getLogger(__name__).warning("Failed to poll VM %s: %s", entry[0], exc)
                    results.append(VMView(name=entry[0], region=entry[1], is_running=entry[2]))

        return sorted(self._dedup_sessions(results), key=lambda v: v.name)

    @staticmethod
    def _dedup_sessions(vms: list[VMView]) -> list[VMView]:
        """Detect VMs that returned identical session sets and keep only the first.

        When concurrent Bastion tunnels interfere, multiple VMs may return
        the same tmux session data from a single host.  This pass computes
        a fingerprint per VM (frozenset of session names) and clears
        duplicates.
        """
        seen: dict[frozenset[str], str] = {}  # fingerprint → first vm name
        for vm in vms:
            if not vm.sessions:
                continue
            fingerprint = frozenset(s.session_name for s in vm.sessions)
            if fingerprint in seen:
                logging.getLogger(__name__).warning(
                    "Duplicate session set on %s (same as %s) — clearing sessions",
                    vm.name,
                    seen[fingerprint],
                )
                vm.sessions = []
            else:
                seen[fingerprint] = vm.name
        return vms

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
                timeout=AZ_CLI_TIMEOUT_SECONDS,
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
        # Compound command: list sessions, then capture each pane + git info.
        # IMPORTANT: Every statement ends with `;` so the script works even
        # when newlines are stripped (azlin -> SSH -> bash -c collapses them).
        gather_cmd = (
            'echo "---HOST---"; hostname; '
            'SESSIONS=$(tmux list-sessions -F "#{session_name}" 2>/dev/null); '
            'if [ -z "$SESSIONS" ]; then echo "===NO_SESSIONS==="; exit 0; fi; '
            "for SESS in $SESSIONS; do "
            'echo "===SESSION:${SESS}==="; '
            'echo "---CAPTURE---"; '
            'tmux capture-pane -t "$SESS" -p -S -__CAPTURE_DEPTH__ 2>/dev/null || echo "(empty)"; '
            'echo "---GIT---"; '
            'CWD=$(tmux display-message -t "$SESS" -p "#{pane_current_path}" 2>/dev/null); '
            'if [ -n "$CWD" ] && [ -d "$CWD/.git" ]; then '
            'cd "$CWD" 2>/dev/null; '
            'BRANCH=$(git branch --show-current 2>/dev/null); '
            'echo "BRANCH:${BRANCH}"; '
            "PR=$(git log --oneline -1 --format='%s' 2>/dev/null | grep -oP 'PR #\\K\\d+' || true); "
            'if [ -n "$PR" ]; then echo "PR:#${PR}"; fi; '
            "fi; "
            # Check for live agent process (claude/node) as child of pane
            'echo "---PROC---"; '
            'PANEPID=$(tmux display-message -t "$SESS" -p "#{pane_pid}" 2>/dev/null); '
            'if [ -n "$PANEPID" ]; then '
            'SID=$(ps -o sid= -p $PANEPID 2>/dev/null); '
            'if [ -n "$SID" ]; then '
            'ps --no-headers -o comm -g $SID 2>/dev/null | grep -qE "^(claude|node)$" '
            '&& echo "AGENT:alive" || echo "AGENT:none"; '
            "else echo 'AGENT:none'; fi; "
            "else echo 'AGENT:none'; fi; "
            'echo "---END---"; '
            "done"
        )
        gather_cmd = gather_cmd.replace("__CAPTURE_DEPTH__", str(int(self.capture_lines)))

        # Strategy 0: Reuse existing Bastion tunnel if available (fastest)
        tunnel_port = self._tunnels.get(vm_name)
        if tunnel_port:
            direct_cmd = [
                "ssh", "-p", str(tunnel_port), "-o", "StrictHostKeyChecking=no",
                "-o", "ConnectTimeout=10", "azureuser@localhost", gather_cmd,
            ]
            output = self._run_ssh_cmd(direct_cmd)
            if output is not None:
                return self._parse_and_verify(vm_name, output)

        cmd = [self.azlin_path, "connect", vm_name, "--no-tmux", "--yes", "--", gather_cmd]

        # Strategy 1: standard subprocess (fast when SSH keys are cached)
        output = self._run_ssh_cmd(cmd)
        if output is not None:
            return self._parse_and_verify(vm_name, output)

        # Strategy 2: virtual TTY — Bastion SSH often needs a PTY
        output = self._run_ssh_cmd_pty(cmd)
        if output is not None:
            return self._parse_and_verify(vm_name, output)

        return []

    def _parse_and_verify(self, vm_name: str, output: str) -> list[SessionView]:
        """Parse SSH output and verify the hostname matches the expected VM.

        When Azure Bastion tunnels interfere during concurrent polling,
        multiple VMs can return data from the same host.  The ---HOST---
        section lets us detect and discard misrouted responses.
        """
        host = parse_hostname(output)
        if host is not None and host != vm_name:
            logging.getLogger(__name__).warning(
                "Hostname mismatch for %s: got '%s' — discarding sessions", vm_name, host,
            )
            return []
        return parse_session_output(vm_name, output)

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
        except (OSError, subprocess.SubprocessError) as exc:
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
