"""Regression tests for Issue Classifier workflow timeout wiring (#3963).

Some tests here are INTENTIONALLY FAILING (red phase) because they specify
behaviour not yet present in the compiled lockfile:

  - test_issue_classifier_lockfile_requires_gh_aw_github_token_or_fail
      The lockfile currently falls back to GITHUB_TOKEN (broader scope) rather
      than hard-failing.  Design spec risk: 'GITHUB_TOKEN fallback is
      broader-scoped; prefer hard-failing if GH_AW_GITHUB_TOKEN unset.'
"""

from __future__ import annotations

from pathlib import Path

import pytest
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


# ---------------------------------------------------------------------------
# Additional structural tests (PASSING — lockfile already correct)
# ---------------------------------------------------------------------------


def test_issue_classifier_lockfile_has_toplevel_deny_all_permissions() -> None:
    """Top-level permissions must be empty dict (deny-all) to follow least-privilege."""
    workflow = _load_lock_workflow()
    assert "permissions" in workflow, "Lockfile must declare top-level permissions"
    assert workflow["permissions"] == {}, (
        "Top-level permissions must be {} (deny-all); "
        "jobs should only grant the minimum scopes they need"
    )


def test_issue_classifier_lockfile_has_secret_redaction_step() -> None:
    """A secret-redaction step must exist to scrub tokens from CI logs."""
    workflow = _load_lock_workflow()
    all_steps: list[dict] = []
    for job in workflow.get("jobs", {}).values():
        all_steps.extend(job.get("steps", []))

    redaction_steps = [
        step
        for step in all_steps
        if "redact" in (step.get("name") or "").lower()
        or "redact_secrets" in str(step.get("uses") or "")
        or "redact_secrets" in str(step.get("run") or "")
    ]
    assert redaction_steps, (
        "No secret-redaction step found in any job. "
        "Add a step that calls redact_secrets to prevent token leakage in CI logs."
    )


def test_issue_classifier_lockfile_secret_redaction_covers_anthropic_key() -> None:
    """The redaction step must list ANTHROPIC_API_KEY among the secret names to scrub."""
    workflow = _load_lock_workflow()
    all_steps: list[dict] = []
    for job in workflow.get("jobs", {}).values():
        all_steps.extend(job.get("steps", []))

    secret_names_values: list[str] = []
    for step in all_steps:
        env = step.get("env") or {}
        if "GH_AW_SECRET_NAMES" in env:
            secret_names_values.append(str(env["GH_AW_SECRET_NAMES"]))

    assert secret_names_values, (
        "No step sets GH_AW_SECRET_NAMES env var for redaction. "
        "The redaction step needs to know which secrets to scrub."
    )
    combined = ",".join(secret_names_values)
    assert "ANTHROPIC_API_KEY" in combined, (
        f"ANTHROPIC_API_KEY must appear in GH_AW_SECRET_NAMES; got: {combined!r}"
    )


# ---------------------------------------------------------------------------
# FAILING test — hard-fail on missing GH_AW_GITHUB_TOKEN (not implemented)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason=(
        "The lockfile currently falls back to GITHUB_TOKEN (broader scope) rather than "
        "hard-failing when GH_AW_GITHUB_TOKEN is unset. "
        "Design spec risk: 'prefer hard-failing if GH_AW_GITHUB_TOKEN unset'."
    ),
    strict=True,
)
def test_issue_classifier_lockfile_requires_gh_aw_github_token_or_fail() -> None:
    """Workflow steps must not fall back to GITHUB_TOKEN (broader scope).

    The 'Checkout PR branch' step currently uses:
        GH_TOKEN: ${{ secrets.GH_AW_GITHUB_MCP_SERVER_TOKEN ||
                       secrets.GH_AW_GITHUB_TOKEN ||
                       secrets.GITHUB_TOKEN }}

    Using GITHUB_TOKEN as a fallback grants broader repository scope than
    GH_AW_GITHUB_TOKEN, violating the least-privilege design requirement.
    Steps should hard-fail with a clear error message when GH_AW_GITHUB_TOKEN
    is absent rather than silently using a broader-scoped token.
    """
    workflow = _load_lock_workflow()
    all_steps: list[dict] = []
    for job in workflow.get("jobs", {}).values():
        all_steps.extend(job.get("steps", []))

    violations: list[str] = []
    for step in all_steps:
        env = step.get("env") or {}
        inputs = step.get("with") or {}
        all_vals = {**env, **inputs}
        for key, value in all_vals.items():
            val_str = str(value)
            # Detect expressions that use GITHUB_TOKEN as a final fallback when
            # a narrower token (GH_AW_GITHUB_TOKEN) is also present in the chain.
            if (
                "secrets.GITHUB_TOKEN" in val_str
                and "GH_AW_GITHUB_TOKEN" in val_str
                and key in ("GH_TOKEN", "GITHUB_TOKEN", "github-token")
            ):
                violations.append(f"Step {step.get('name')!r} key {key!r}: {val_str!r}")

    assert not violations, (
        "The following steps use GITHUB_TOKEN as a broad-scope fallback.\n"
        "Replace with hard-fail logic when GH_AW_GITHUB_TOKEN is unset:\n"
        + "\n".join(f"  • {v}" for v in violations)
    )
