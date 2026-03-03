"""TUI output parsers -- parse tmux and VM list output into view models.

Public API:
    parse_session_output: Parse compound tmux output into SessionView list.
    parse_vm_text: Parse azlin text table into VM tuples.
"""

from __future__ import annotations

from amplihack.fleet._tui_classify import classify_status
from amplihack.fleet._tui_data import SessionView


def parse_session_output(vm_name: str, output: str) -> list[SessionView]:
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
                view.status = classify_status(capture)
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


def parse_vm_text(text: str) -> list[tuple[str, str, bool]]:
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
