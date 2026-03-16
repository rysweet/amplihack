"""TUI output parsers -- parse tmux and VM list output into view models.

Public API:
    parse_session_output: Parse compound tmux output into SessionView list.
    parse_vm_text: Parse azlin text table into VM tuples.
"""

from __future__ import annotations

import logging

from amplihack.fleet._tui_classify import classify_status
from amplihack.fleet._tui_data import SessionView
from amplihack.utils.logging_utils import log_call

__all__ = ["parse_hostname", "parse_session_output", "parse_vm_text"]

logger = logging.getLogger(__name__)


@log_call
def parse_hostname(output: str) -> str | None:
    """Extract the hostname from a ---HOST--- section in SSH output.

    Returns the hostname string, or None if the section is missing.
    """
    marker = "---HOST---"
    if marker not in output:
        return None
    start = output.index(marker) + len(marker)
    # Hostname ends at the next marker (---) or end of output
    rest = output[start:]
    # Take text up to the next section marker
    for end_marker in ("===SESSION:", "===NO_SESSIONS==="):
        if end_marker in rest:
            rest = rest[: rest.index(end_marker)]
            break
    hostname = rest.strip().split("\n")[0].strip()
    return hostname if hostname else None


@log_call
def parse_session_output(vm_name: str, output: str) -> list[SessionView]:
    """Parse the compound tmux output for a VM into SessionView objects.

    Handles noisy PTY output where captured tmux pane content may contain
    marker strings from previous test runs.  Deduplicates by session name,
    keeping the first (most complete) occurrence.
    """
    sessions: list[SessionView] = []

    # Only treat as "no sessions" when there are no real session markers.
    # PTY output can include marker text from captured terminal content.
    if "===NO_SESSIONS===" in output and "===SESSION:" not in output:
        return sessions

    seen_names: set[str] = set()

    # Split by session markers
    parts = output.split("===SESSION:")
    for part in parts[1:]:  # skip everything before first marker
        if "===" not in part:
            continue

        # Extract session name
        header_end = part.index("===")
        session_name = part[:header_end].strip()
        rest = part[header_end + 3 :]

        # Filter out invalid session names.  PTY output captures pane content
        # which may contain literal marker text like ===SESSION:${SESS}===.
        # Names with $, {, }, or other shell metacharacters are noise.
        if not session_name or any(c in session_name for c in "${}\\`"):
            continue

        # Skip duplicates — PTY output captures pane content which may
        # contain ===SESSION:name=== markers from previous test runs.
        if session_name in seen_names:
            continue
        seen_names.add(session_name)

        view = SessionView(vm_name=vm_name, session_name=session_name)

        # Parse capture and git sections if markers are present.
        has_capture = "---CAPTURE---" in rest
        has_git = "---GIT---" in rest
        has_end = "---END---" in rest

        if has_capture and has_git:
            capture_start = rest.index("---CAPTURE---") + len("---CAPTURE---")
            capture_end = rest.index("---GIT---")
            capture = rest[capture_start:capture_end].strip()

            if capture and capture != "(empty)":
                view.status = classify_status(capture)
                view.tmux_capture = capture  # Cache for Phase 3 reasoning
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

            # Extract git info (between ---GIT--- and ---PROC--- or ---END---)
            git_start = rest.index("---GIT---") + len("---GIT---")
            has_proc = "---PROC---" in rest
            if has_proc:
                git_end = rest.index("---PROC---")
            elif has_end:
                git_end = rest.index("---END---")
            else:
                git_end = len(rest)
            git_section = rest[git_start:git_end].strip()

            for line in git_section.split("\n"):
                line = line.strip()
                if line.startswith("BRANCH:"):
                    view.branch = line[7:]
                elif line.startswith("PR:"):
                    view.pr = line[3:]

            # Extract agent process status
            if has_proc:
                proc_start = rest.index("---PROC---") + len("---PROC---")
                proc_end = rest.index("---END---") if has_end else len(rest)
                proc_section = rest[proc_start:proc_end].strip()
                view.agent_alive = "AGENT:alive" in proc_section

        elif not has_capture and not has_git:
            # No markers at all — likely noise from captured pane content.
            view.status = "unknown"

        sessions.append(view)

    return sessions


@log_call
def parse_vm_text(text: str) -> list[tuple[str, str, bool, list[str]]]:
    """Parse text table from azlin list.

    Returns list of (name, region, is_running, session_names) tuples.
    Session names come from the 'Tmux Sessions' column — comma-separated,
    possibly spanning multiple rows (continuation rows have empty column 1).
    """
    vms: list[tuple[str, str, bool, list[str]]] = []
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
            parts = [p.strip() for p in line.split(sep)]
            # Filter empty edge cells but keep internal empty cells
            # The split produces: ['', 'devr', 'mem', 'Ubuntu', 'Ru…', '10.0.0.10', 'we…', '', '', '']
            # We need to work with positional indices, not filter empties
            non_edge = [p for i, p in enumerate(parts) if i > 0 and i < len(parts) - 1]
            if len(non_edge) >= 4:
                name = non_edge[0].strip()
                tmux_col = non_edge[1].strip() if len(non_edge) > 1 else ""

                if name:
                    # New VM row
                    status = non_edge[3] if len(non_edge) > 3 else ""
                    region = non_edge[5] if len(non_edge) > 5 else ""
                    is_running = status.lower().startswith("ru")
                    sessions = [
                        s.strip().rstrip(",")
                        for s in tmux_col.split(",")
                        if s.strip() and s.strip().rstrip(",")
                    ]
                    vms.append((name, region, is_running, sessions))
                elif tmux_col and vms:
                    # Continuation row — append session names to last VM
                    prev_name, prev_region, prev_running, prev_sessions = vms[-1]
                    extra = [
                        s.strip().rstrip(",")
                        for s in tmux_col.split(",")
                        if s.strip() and s.strip().rstrip(",")
                    ]
                    vms[-1] = (prev_name, prev_region, prev_running, prev_sessions + extra)

    return vms
