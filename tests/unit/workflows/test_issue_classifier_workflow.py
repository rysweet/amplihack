"""Regression tests for Issue Classifier workflow timeout wiring (#3963)."""

from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_WORKFLOW = REPO_ROOT / ".github/workflows/issue-classifier.md"
LOCK_WORKFLOW = REPO_ROOT / ".github/workflows/issue-classifier.lock.yml"


def _load_source_frontmatter() -> dict:
    text = SOURCE_WORKFLOW.read_text(encoding="utf-8")
    _, frontmatter, _ = text.split("---", 2)
    data = yaml.safe_load(frontmatter)
    assert isinstance(data, dict), "workflow frontmatter must deserialize to a mapping"
    return data


def _load_lock_workflow() -> dict:
    data = yaml.safe_load(LOCK_WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "compiled lock workflow must deserialize to a mapping"
    return data


def _find_step(steps: list[dict], name: str) -> dict:
    for step in steps:
        if step.get("name") == name:
            return step
    raise AssertionError(f"Could not find step named {name!r}")


def test_issue_classifier_timeout_budget_has_ten_minute_floor() -> None:
    source_timeout = _load_source_frontmatter()["timeout-minutes"]
    assert source_timeout >= 10, (
        "Issue Classifier must allow at least 10 minutes for Claude retries"
    )


def test_issue_classifier_source_declares_required_github_read_permissions() -> None:
    permissions = _load_source_frontmatter()["permissions"]

    assert permissions["contents"] == "read"
    assert permissions["issues"] == "read"
    assert permissions["pull-requests"] == "read"


def test_issue_classifier_lockfile_matches_source_timeout_budget() -> None:
    source_timeout = _load_source_frontmatter()["timeout-minutes"]
    workflow = _load_lock_workflow()

    execute_step = _find_step(workflow["jobs"]["agent"]["steps"], "Execute Claude Code CLI")
    assert execute_step["timeout-minutes"] == source_timeout

    handle_failure_step = _find_step(
        workflow["jobs"]["conclusion"]["steps"], "Handle Agent Failure"
    )
    assert handle_failure_step["env"]["GH_AW_TIMEOUT_MINUTES"] == str(source_timeout)


def test_issue_classifier_lockfile_grants_required_agent_read_permissions() -> None:
    workflow = _load_lock_workflow()
    permissions = workflow["jobs"]["agent"]["permissions"]

    assert permissions["contents"] == "read"
    assert permissions["issues"] == "read"
    assert permissions["pull-requests"] == "read"
