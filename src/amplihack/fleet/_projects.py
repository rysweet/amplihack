"""Project and objective tracking for fleet orchestration.

Manages projects.toml — the fleet's project registry with objectives
tracked as GitHub issues labeled 'fleet-objective'.

Public API:
    Project: Dataclass for a fleet project with objectives.
    load_projects: Read projects.toml from disk.
    save_projects: Write projects.toml to disk.
    merge_projects: Merge remote project data into local registry.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from amplihack.fleet._constants import DEFAULT_PROJECTS_PATH

__all__ = [
    "Project",
    "load_projects",
    "save_projects",
    "merge_projects",
    "validate_repo_url",
    "DEFAULT_PROJECTS_PATH",
]

_PROJECT_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
_REPO_URL_RE = re.compile(r"^(https://github\.com/[\w.-]+/[\w.-]+(?:\.git)?|[\w.-]+/[\w.-]+)$")


def validate_repo_url(url: str) -> bool:
    """Check repo_url is a valid GitHub HTTPS URL or owner/repo shorthand."""
    return bool(_REPO_URL_RE.match(url))


@dataclass
class Project:
    """A fleet project with tracked objectives (GitHub issues)."""

    name: str
    repo_url: str = ""
    identity: str = ""  # GitHub identity to use
    priority: str = "medium"  # low, medium, high
    objectives: list[dict] = field(default_factory=list)
    # Each objective: {"number": int, "title": str, "state": str, "url": str}

    def __post_init__(self) -> None:
        if not _PROJECT_NAME_RE.match(self.name):
            raise ValueError(
                f"Invalid project name {self.name!r}: must match ^[a-zA-Z0-9][a-zA-Z0-9_-]*$"
            )

    def add_objective(self, number: int, title: str, state: str = "open", url: str = "") -> dict:
        """Add or update an objective (GitHub issue)."""
        for obj in self.objectives:
            if obj["number"] == number:
                obj["title"] = title
                obj["state"] = state
                if url:
                    obj["url"] = url
                return obj
        entry = {"number": number, "title": title, "state": state, "url": url}
        self.objectives.append(entry)
        return entry

    def remove_objective(self, number: int) -> bool:
        """Remove an objective by issue number. Returns True if found."""
        for i, obj in enumerate(self.objectives):
            if obj["number"] == number:
                self.objectives.pop(i)
                return True
        return False

    def open_objectives(self) -> list[dict]:
        """Return objectives that are still open."""
        return [o for o in self.objectives if o.get("state", "open") == "open"]

    def to_dict(self) -> dict:
        return {
            "repo_url": self.repo_url,
            "identity": self.identity,
            "priority": self.priority,
            "objectives": self.objectives,
        }

    @classmethod
    def from_dict(cls, name: str, data: dict) -> Project:
        return cls(
            name=name,
            repo_url=data.get("repo_url", ""),
            identity=data.get("identity", ""),
            priority=data.get("priority", "medium"),
            objectives=list(data.get("objectives", [])),
        )


def load_projects(path: Path | None = None) -> dict[str, Project]:
    """Load projects from a TOML file. Returns {name: Project}."""
    path = path or DEFAULT_PROJECTS_PATH
    if not path.exists():
        return {}
    try:
        with open(path, "rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        import logging

        logging.getLogger(__name__).warning("Failed to parse %s: %s", path, exc)
        return {}
    projects: dict[str, Project] = {}
    for name, pdata in data.get("project", {}).items():
        projects[name] = Project.from_dict(name, pdata)
    return projects


def save_projects(projects: dict[str, Project], path: Path | None = None) -> None:
    """Write projects to a TOML file."""
    path = path or DEFAULT_PROJECTS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    # Validate all project names before writing
    for name in projects:
        if not _PROJECT_NAME_RE.match(name):
            raise ValueError(
                f"Invalid project name {name!r}: must match ^[a-zA-Z0-9][a-zA-Z0-9_-]*$"
            )

    doc: dict = {"project": {}}
    for name, proj in sorted(projects.items()):
        entry: dict = {
            "repo_url": proj.repo_url,
            "priority": proj.priority,
        }
        if proj.identity:
            entry["identity"] = proj.identity
        if proj.objectives:
            entry["objectives"] = [
                {
                    "number": obj["number"],
                    "title": obj["title"],
                    "state": obj.get("state", "open"),
                    **({"url": obj["url"]} if obj.get("url") else {}),
                }
                for obj in proj.objectives
            ]
        doc["project"][name] = entry

    import tomli_w  # lazy import — keeps module importable without tomli_w installed

    path.write_bytes(tomli_w.dumps(doc).encode())


def merge_projects(
    local: dict[str, Project],
    remote_objectives: dict[str, list[dict]],
) -> dict[str, Project]:
    """Merge remote objective data (from SSH gather) into local projects.

    Args:
        local: Current local project registry.
        remote_objectives: {project_name: [{"number": N, "title": T, "state": S, "url": U}]}

    Returns:
        Updated local dict (mutated in place and returned).
    """
    for name, objectives in remote_objectives.items():
        if name not in local:
            # Don't auto-create projects from remote data — user must register first
            continue
        proj = local[name]
        for obj in objectives:
            # Sanitize remote data
            title = re.sub(r"[\x00-\x1f\x7f]", "", str(obj.get("title", "")))[:256]
            state = str(obj.get("state", "open")).strip().lower()
            if state not in ("open", "closed"):
                state = "open"
            proj.add_objective(
                number=obj["number"],
                title=title,
                state=state,
                url=obj.get("url", ""),
            )
    return local
