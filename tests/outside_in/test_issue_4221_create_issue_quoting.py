"""Outside-in regression for issue #4221: step-03 issue creation quoting.

The reported failure happened in default-workflow step-03-create-issue before any
repo code changes were applied:

    /bin/bash: -c: unexpected EOF while looking for matching `''

This test exercises the real recipe-runner path with the exact step-03 / step-03b
commands from default-workflow.yaml, a long workflow task description, and
requirements text containing apostrophes/newlines. A fake ``gh`` binary captures
the issue payload so the test stays local and proves the workflow progresses
through issue creation into issue-number extraction, while forcing the real
step-03 body transport contract: ``gh issue create --body-file``.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / "amplifier-bundle" / "recipes" / "default-workflow.yaml"

TASK_DESCRIPTION = (
    "Investigate and fix the repeated cancellation of the ci-benchmark job in "
    ".github/workflows/gym-smoke.yml, which currently times out during the Build "
    "step because timeout-minutes is set to 5. Keep the fix scoped and "
    "behavior-safe, make any necessary workflow/code/test updates, and validate "
    "according to repo standards. In parallel context, note that benchmark reruns "
    "are currently active at /tmp/gym-eval-20260404-041153 and "
    "/tmp/gym-eval-20260404-041156 and appear to be making real agent progress "
    "rather than 4500-second retry backoffs."
)

FINAL_REQUIREMENTS = """No material ambiguity remains.

1. Keep the user's fix scoped.
2. Don't change unrelated jobs, scripts, or workflow logic.
3. Validate according to the repo's normal workflow-file checks.
"""

# Adversarial inputs for parametrized special-character tests
SPECIAL_CHAR_CASES = [
    pytest.param(
        "Fix the user's login page (it's broken)",
        "1. The user's session must persist.\n2. Don't break the admin's dashboard.",
        id="single-quotes",
    ),
    pytest.param(
        'Fix the "login" button alignment',
        '1. The "Submit" label must be centered.\n2. Keep "Remember me" checkbox.',
        id="double-quotes",
    ),
    pytest.param(
        "Fix multiline\ndescription\nwith newlines",
        "1. First requirement.\n\n2. Second requirement with gap.\n\n3. Third.",
        id="embedded-newlines",
    ),
    pytest.param(
        "Fix path\\to\\file with backslash\\n escapes",
        "1. Handle C:\\Users\\admin paths.\n2. Keep \\n literal in config values.",
        id="backslashes",
    ),
    pytest.param(
        "Run `echo hello` and `uname -a` in the shell",
        "1. Run `make test` before merging.\n2. Check `git status` output.",
        id="backticks",
    ),
    pytest.param(
        "Cost is 100 and PATH expansion must stay safe",
        "1. PATH must not be exposed.\n2. Sanitize env lookups from logs.",
        id="dollar-signs",
    ),
    pytest.param(
        "Fix auth; rm canary, redirect and pipe output",
        "1. Sanitize input.\n2. Reject shell injection chains.",
        id="shell-metacharacters",
    ),
]


def _find_recipe_runner_binary() -> str | None:
    """Find the recipe-runner-rs binary."""
    for candidate in [
        "recipe-runner-rs",
        str(Path.home() / ".cargo" / "bin" / "recipe-runner-rs"),
    ]:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def _load_step_commands() -> tuple[str, str]:
    """Load the raw step-03 and step-03b command strings from the workflow YAML."""
    with open(WORKFLOW_PATH, encoding="utf-8") as f:
        workflow = yaml.safe_load(f)

    steps = {step["id"]: step for step in workflow["steps"]}
    return (
        steps["step-03-create-issue"]["command"],
        steps["step-03b-extract-issue-number"]["command"],
    )


def _build_minimal_recipe() -> str:
    """Create a two-step recipe using the real default-workflow issue commands."""
    step03, step03b = _load_step_commands()
    return f"""\
name: "test-4221-create-issue"
context:
  repo_path: ""
  task_description: ""
  final_requirements: ""
  issue_creation: ""
  issue_number: ""
steps:
  - id: "step-03-create-issue"
    type: "bash"
    command: |
{_indent(step03, 6)}
    output: "issue_creation"
    parse_json: false

  - id: "step-03b-extract-issue-number"
    type: "bash"
    command: |
{_indent(step03b, 6)}
    output: "issue_number"
"""


def _indent(text: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(f"{prefix}{line}" if line else prefix for line in text.splitlines())


def _expected_issue_body(task_desc: str = TASK_DESCRIPTION, reqs: str = FINAL_REQUIREMENTS) -> str:
    return (
        "## Task Description\n"
        f"{task_desc}\n\n"
        "## Requirements\n"
        f"{reqs.rstrip(chr(10))}\n\n"
        "## Acceptance Criteria\n"
        "- [ ] All explicit requirements met\n"
        "- [ ] Tests passing\n"
        "- [ ] Philosophy compliant\n"
        "- [ ] Documentation updated\n\n"
        "## Classification\n"
        "Generated via default-workflow recipe\n"
    )


def _write_fake_gh(bin_dir: Path, capture_path: Path) -> None:
    """Create a fake gh executable that captures --title/--body-file args.

    Handles the idempotency guard calls (issue list, issue view, label list/create)
    by returning empty results, then captures the actual issue create call.
    """
    fake_gh = bin_dir / "gh"
    fake_gh.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]

# Idempotency guard: gh issue view (returns failure = not found)
if len(args) >= 2 and args[0] == "issue" and args[1] == "view":
    sys.exit(1)

# Idempotency guard: gh issue list --search (returns empty JSON array)
if len(args) >= 2 and args[0] == "issue" and args[1] == "list":
    print("")
    sys.exit(0)

# Label operations: succeed silently
if len(args) >= 2 and args[0] == "label":
    sys.exit(0)

# Issue create: capture and return URL
if len(args) >= 2 and args[0] == "issue" and args[1] == "create":
    payload = {"args": args, "labels": []}
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg == "--title" and idx + 1 < len(args):
            payload["title"] = args[idx + 1]
            idx += 2
            continue
        if arg == "--body-file" and idx + 1 < len(args):
            payload["body_file"] = args[idx + 1]
            payload["body"] = Path(args[idx + 1]).read_text(encoding="utf-8")
            idx += 2
            continue
        if arg == "--label" and idx + 1 < len(args):
            payload["labels"].append(args[idx + 1])
            idx += 2
            continue
        idx += 1

    with open(os.environ["FAKE_GH_CAPTURE"], "w", encoding="utf-8") as f:
        json.dump(payload, f)

    print("https://github.com/example/repo/issues/4221")
    sys.exit(0)

# Unknown command: succeed silently
sys.exit(0)
""",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)


def test_default_workflow_issue_creation_handles_quote_heavy_context() -> None:
    """The default-workflow issue path should complete and extract the issue number."""
    binary = _find_recipe_runner_binary()
    if binary is None:
        pytest.skip("recipe-runner-rs binary not found")

    recipe = _build_minimal_recipe()

    with tempfile.TemporaryDirectory(prefix="issue-4221-") as tmpdir:
        temp_root = Path(tmpdir)
        repo_path = temp_root / "repo"
        repo_path.mkdir()

        bin_dir = temp_root / "bin"
        bin_dir.mkdir()
        capture_path = temp_root / "gh-capture.json"
        _write_fake_gh(bin_dir, capture_path)

        recipe_path = temp_root / "recipe.yaml"
        recipe_path.write_text(recipe, encoding="utf-8")

        env = dict(os.environ)
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["FAKE_GH_CAPTURE"] = str(capture_path)

        result = subprocess.run(
            [
                binary,
                str(recipe_path),
                "--output-format",
                "json",
                "-C",
                str(REPO_ROOT),
                "--set",
                f"repo_path={repo_path}",
                "--set",
                f"task_description={TASK_DESCRIPTION}",
                "--set",
                f"final_requirements={FINAL_REQUIREMENTS}",
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=20,
        )

        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["success"], data

        steps = {step["step_id"]: step for step in data["step_results"]}
        assert steps["step-03-create-issue"]["status"] == "completed", steps["step-03-create-issue"]
        assert steps["step-03b-extract-issue-number"]["status"] == "completed", steps[
            "step-03b-extract-issue-number"
        ]
        assert steps["step-03b-extract-issue-number"]["output"] == "4221"

        captured = json.loads(capture_path.read_text(encoding="utf-8"))
        assert captured["title"], captured
        assert "\n" not in captured["title"]
        assert captured["labels"] == ["workflow:default"]
        assert "--body-file" in captured["args"]
        assert "--body" not in captured["args"]
        assert captured["body"] == _expected_issue_body()
        assert not Path(captured["body_file"]).exists()


def _run_issue_creation(binary: str, task_desc: str, final_reqs: str) -> tuple[dict, dict]:
    """Run step-03/03b with given inputs, return (recipe_output, gh_capture)."""
    recipe = _build_minimal_recipe()

    with tempfile.TemporaryDirectory(prefix="issue-4221-special-") as tmpdir:
        temp_root = Path(tmpdir)
        repo_path = temp_root / "repo"
        repo_path.mkdir()

        bin_dir = temp_root / "bin"
        bin_dir.mkdir()
        capture_path = temp_root / "gh-capture.json"
        _write_fake_gh(bin_dir, capture_path)

        recipe_path = temp_root / "recipe.yaml"
        recipe_path.write_text(recipe, encoding="utf-8")

        env = dict(os.environ)
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["FAKE_GH_CAPTURE"] = str(capture_path)

        result = subprocess.run(
            [
                binary,
                str(recipe_path),
                "--output-format",
                "json",
                "-C",
                str(REPO_ROOT),
                "--set",
                f"repo_path={repo_path}",
                "--set",
                f"task_description={task_desc}",
                "--set",
                f"final_requirements={final_reqs}",
            ],
            capture_output=True,
            text=True,
            env=env,
            timeout=20,
        )
        assert result.returncode == 0, (
            f"Recipe runner failed (rc={result.returncode}):\n{result.stderr}"
        )
        data = json.loads(result.stdout)
        assert data["success"], f"Recipe reported failure: {data}"

        captured = json.loads(capture_path.read_text(encoding="utf-8"))
        return data, captured


@pytest.mark.parametrize("task_desc,final_reqs", SPECIAL_CHAR_CASES)
def test_issue_creation_with_special_characters(task_desc: str, final_reqs: str) -> None:
    """Step-03 must handle special characters in task_description and final_requirements."""
    binary = _find_recipe_runner_binary()
    if binary is None:
        pytest.skip("recipe-runner-rs binary not found")

    data, captured = _run_issue_creation(binary, task_desc, final_reqs)

    steps = {step["step_id"]: step for step in data["step_results"]}
    assert steps["step-03-create-issue"]["status"] == "completed", (
        f"step-03 failed for input containing special chars: {steps['step-03-create-issue']}"
    )
    assert steps["step-03b-extract-issue-number"]["status"] == "completed", (
        f"step-03b failed: {steps['step-03b-extract-issue-number']}"
    )

    # Body must have been passed via --body-file, not --body
    assert "--body-file" in captured["args"]
    assert "--body" not in captured["args"]

    # Title must be single-line
    assert "\n" not in captured["title"]

    # Body must contain the task description and requirements content
    assert captured["body"] == _expected_issue_body(task_desc, final_reqs)
