"""Tests for fleet _projects -- Project dataclass and projects.toml I/O.

Testing pyramid:
- 60% Unit: Project dataclass, add/remove objective
- 30% Integration: load/save/merge roundtrip
- 10% E2E: CLI commands via CliRunner
"""

from __future__ import annotations

from pathlib import Path

import pytest

from amplihack.fleet._projects import (
    Project,
    load_projects,
    merge_projects,
    save_projects,
    validate_repo_url,
)
from amplihack.utils.logging_utils import log_call

# ────────────────────────────────────────────
# UNIT TESTS (60%) — Project dataclass
# ────────────────────────────────────────────


class TestProject:
    """Unit tests for Project dataclass."""

    @log_call
    def test_minimal_construction(self):
        proj = Project(name="myapp")
        assert proj.name == "myapp"
        assert proj.repo_url == ""
        assert proj.identity == ""
        assert proj.priority == "medium"
        assert proj.objectives == []

    @log_call
    def test_full_construction(self):
        proj = Project(
            name="myapp",
            repo_url="https://github.com/org/myapp",
            identity="user1",
            priority="high",
            objectives=[{"number": 1, "title": "Fix login", "state": "open", "url": ""}],
        )
        assert proj.repo_url == "https://github.com/org/myapp"
        assert proj.priority == "high"
        assert len(proj.objectives) == 1

    @log_call
    def test_add_objective(self):
        proj = Project(name="myapp")
        obj = proj.add_objective(number=42, title="Add auth", state="open")
        assert obj["number"] == 42
        assert obj["title"] == "Add auth"
        assert len(proj.objectives) == 1

    @log_call
    def test_add_objective_updates_existing(self):
        proj = Project(name="myapp")
        proj.add_objective(number=42, title="Add auth", state="open")
        proj.add_objective(number=42, title="Add auth (updated)", state="closed")
        assert len(proj.objectives) == 1
        assert proj.objectives[0]["title"] == "Add auth (updated)"
        assert proj.objectives[0]["state"] == "closed"

    @log_call
    def test_remove_objective(self):
        proj = Project(name="myapp")
        proj.add_objective(number=1, title="A")
        proj.add_objective(number=2, title="B")
        assert proj.remove_objective(1) is True
        assert len(proj.objectives) == 1
        assert proj.objectives[0]["number"] == 2

    @log_call
    def test_remove_objective_not_found(self):
        proj = Project(name="myapp")
        assert proj.remove_objective(999) is False

    @log_call
    def test_open_objectives(self):
        proj = Project(name="myapp")
        proj.add_objective(number=1, title="Open", state="open")
        proj.add_objective(number=2, title="Closed", state="closed")
        proj.add_objective(number=3, title="Also open", state="open")
        opens = proj.open_objectives()
        assert len(opens) == 2
        assert all(o["state"] == "open" for o in opens)

    @log_call
    def test_to_dict_roundtrip(self):
        proj = Project(
            name="myapp",
            repo_url="https://github.com/org/myapp",
            identity="user1",
            priority="high",
            objectives=[{"number": 1, "title": "Fix it", "state": "open", "url": ""}],
        )
        d = proj.to_dict()
        restored = Project.from_dict("myapp", d)
        assert restored.name == proj.name
        assert restored.repo_url == proj.repo_url
        assert restored.identity == proj.identity
        assert restored.priority == proj.priority
        assert restored.objectives == proj.objectives

    @log_call
    def test_from_dict_missing_optional_fields(self):
        d = {"repo_url": "https://github.com/org/x"}
        proj = Project.from_dict("x", d)
        assert proj.identity == ""
        assert proj.priority == "medium"
        assert proj.objectives == []

    @log_call
    def test_validate_repo_url(self):
        assert validate_repo_url("https://github.com/org/repo") is True
        assert validate_repo_url("https://github.com/org/repo.git") is True
        assert validate_repo_url("org/repo") is True
        assert validate_repo_url("not a url") is False
        assert validate_repo_url("ftp://example.com/repo") is False
        assert validate_repo_url("") is False
        assert validate_repo_url("https://github.com/org/repo; rm -rf /") is False

    @log_call
    def test_objectives_default_independent(self):
        """Each instance gets its own objectives list."""
        p1 = Project(name="a")
        p2 = Project(name="b")
        p1.add_objective(number=1, title="X")
        assert p2.objectives == []


# ────────────────────────────────────────────
# INTEGRATION TESTS (30%) — load/save/merge
# ────────────────────────────────────────────


class TestProjectsIO:
    """Integration tests for projects.toml I/O."""

    @log_call
    def test_save_and_load_roundtrip(self, tmp_path: Path):
        path = tmp_path / "projects.toml"
        projects = {
            "myapp": Project(
                name="myapp",
                repo_url="https://github.com/org/myapp",
                identity="user1",
                priority="high",
                objectives=[{"number": 42, "title": "Fix login", "state": "open", "url": ""}],
            ),
            "lib": Project(
                name="lib",
                repo_url="https://github.com/org/lib",
                priority="low",
            ),
        }
        save_projects(projects, path)

        loaded = load_projects(path)
        assert len(loaded) == 2
        assert "myapp" in loaded
        assert "lib" in loaded
        assert loaded["myapp"].repo_url == "https://github.com/org/myapp"
        assert loaded["myapp"].identity == "user1"
        assert loaded["myapp"].priority == "high"
        assert len(loaded["myapp"].objectives) == 1
        assert loaded["myapp"].objectives[0]["number"] == 42
        assert loaded["lib"].priority == "low"

    @log_call
    def test_load_nonexistent_returns_empty(self, tmp_path: Path):
        path = tmp_path / "nonexistent.toml"
        assert load_projects(path) == {}

    @log_call
    def test_save_creates_parent_dirs(self, tmp_path: Path):
        path = tmp_path / "sub" / "dir" / "projects.toml"
        save_projects({"x": Project(name="x", repo_url="u")}, path)
        assert path.exists()

    @log_call
    def test_save_empty_projects(self, tmp_path: Path):
        path = tmp_path / "projects.toml"
        save_projects({}, path)
        loaded = load_projects(path)
        assert loaded == {}

    @log_call
    def test_toml_special_characters_roundtrip(self, tmp_path: Path):
        """Titles with quotes, backslashes, and equals signs survive roundtrip."""
        path = tmp_path / "projects.toml"
        tricky_titles = [
            'Fix "quoted" strings',
            "Backslash \\ in path",
            "Equals = sign",
            "Newline \\n literal",
            "Tab\\there",
            'Mixed "quotes" and = signs',
        ]
        projects = {
            "myapp": Project(
                name="myapp",
                repo_url="https://github.com/org/myapp",
                objectives=[
                    {"number": i + 1, "title": t, "state": "open", "url": ""}
                    for i, t in enumerate(tricky_titles)
                ],
            ),
        }
        save_projects(projects, path)
        loaded = load_projects(path)
        assert len(loaded["myapp"].objectives) == len(tricky_titles)
        for orig, loaded_obj in zip(tricky_titles, loaded["myapp"].objectives, strict=False):
            assert loaded_obj["title"] == orig, f"Mismatch for {orig!r}"

    @log_call
    def test_load_corrupt_toml_returns_empty(self, tmp_path: Path):
        """Corrupt TOML file returns empty dict instead of crashing."""
        path = tmp_path / "projects.toml"
        path.write_text("this is not valid toml [[[")
        loaded = load_projects(path)
        assert loaded == {}

    @log_call
    def test_invalid_project_name_rejected(self):
        """Project names must match ^[a-zA-Z0-9][a-zA-Z0-9_-]*$."""
        with pytest.raises(ValueError, match="Invalid project name"):
            Project(name="bad name with spaces")
        with pytest.raises(ValueError, match="Invalid project name"):
            Project(name="-starts-with-dash")
        with pytest.raises(ValueError, match="Invalid project name"):
            Project(name="has/slash")

    @log_call
    def test_save_rejects_invalid_project_name(self, tmp_path: Path):
        """save_projects validates names even when bypassing __post_init__."""
        path = tmp_path / "projects.toml"
        proj = Project.__new__(Project)
        proj.name = "bad name"
        proj.repo_url = ""
        proj.identity = ""
        proj.priority = "medium"
        proj.objectives = []
        with pytest.raises(ValueError, match="Invalid project name"):
            save_projects({"bad name": proj}, path)


class TestMergeProjects:
    """Tests for merge_projects."""

    @log_call
    def test_merge_adds_new_objectives(self):
        local = {
            "myapp": Project(name="myapp", repo_url="u"),
        }
        remote = {
            "myapp": [
                {"number": 1, "title": "Fix A", "state": "open", "url": ""},
                {"number": 2, "title": "Fix B", "state": "open", "url": ""},
            ],
        }
        result = merge_projects(local, remote)
        assert len(result["myapp"].objectives) == 2

    @log_call
    def test_merge_updates_existing_objectives(self):
        local = {
            "myapp": Project(
                name="myapp",
                repo_url="u",
                objectives=[{"number": 1, "title": "Old title", "state": "open", "url": ""}],
            ),
        }
        remote = {
            "myapp": [
                {"number": 1, "title": "New title", "state": "closed", "url": ""},
            ],
        }
        result = merge_projects(local, remote)
        assert len(result["myapp"].objectives) == 1
        assert result["myapp"].objectives[0]["title"] == "New title"
        assert result["myapp"].objectives[0]["state"] == "closed"

    @log_call
    def test_merge_ignores_unknown_projects(self):
        local = {"myapp": Project(name="myapp", repo_url="u")}
        remote = {
            "unknown": [{"number": 1, "title": "X", "state": "open", "url": ""}],
        }
        result = merge_projects(local, remote)
        assert "unknown" not in result
        assert len(result["myapp"].objectives) == 0


# ────────────────────────────────────────────
# E2E TESTS (10%) — CLI commands
# ────────────────────────────────────────────


class TestProjectCLI:
    """CLI tests for project add-issue and track-issue commands."""

    @log_call
    def test_add_issue_project_not_found(self, tmp_path: Path, monkeypatch):
        """add-issue with unknown project shows error."""

        from click.testing import CliRunner

        from amplihack.fleet.fleet_cli import fleet_cli

        # Point load_projects to an empty file
        empty_path = tmp_path / "projects.toml"
        monkeypatch.setattr("amplihack.fleet._projects.DEFAULT_PROJECTS_PATH", empty_path)

        runner = CliRunner()
        result = runner.invoke(
            fleet_cli,
            ["project", "add-issue", "nonexistent", "42"],
            catch_exceptions=False,
        )
        assert "Project not found" in result.output

    @log_call
    def test_add_issue_success(self, tmp_path: Path, monkeypatch):
        """add-issue adds objective to existing project."""
        from click.testing import CliRunner

        from amplihack.fleet.fleet_cli import fleet_cli

        # Set up projects.toml with a project
        projects_path = tmp_path / "projects.toml"
        projects = {"myapp": Project(name="myapp", repo_url="https://github.com/org/myapp")}
        save_projects(projects, projects_path)

        monkeypatch.setattr("amplihack.fleet._projects.DEFAULT_PROJECTS_PATH", projects_path)

        runner = CliRunner()
        result = runner.invoke(
            fleet_cli,
            ["project", "add-issue", "myapp", "42", "--title", "Fix login"],
            catch_exceptions=False,
        )
        assert "Added objective" in result.output
        assert "#42" in result.output

        # Verify it was saved
        loaded = load_projects(projects_path)
        assert len(loaded["myapp"].objectives) == 1
        assert loaded["myapp"].objectives[0]["number"] == 42

    @log_call
    def test_track_issue_project_not_found(self, tmp_path: Path, monkeypatch):
        """track-issue with unknown project shows error."""
        from click.testing import CliRunner

        from amplihack.fleet.fleet_cli import fleet_cli

        empty_path = tmp_path / "projects.toml"
        monkeypatch.setattr("amplihack.fleet._projects.DEFAULT_PROJECTS_PATH", empty_path)

        runner = CliRunner()
        result = runner.invoke(
            fleet_cli,
            ["project", "track-issue", "nonexistent"],
            catch_exceptions=False,
        )
        assert "Project not found" in result.output
