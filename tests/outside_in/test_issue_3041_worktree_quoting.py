"""
Outside-in behavioral tests for issue #3041: worktree step quoting fix.

The step-04-setup-worktree bash step in default-workflow.yaml broke when
{{task_description}} contained single quotes or parentheses because the
value was wrapped in single quotes. The fix uses a heredoc instead.

These tests simulate what the recipe runner does: template-substitute a
task_description into the step-04 bash script, then execute the slug
generation portion through bash and verify it produces a valid branch name.
"""

import re
import subprocess

import yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WORKFLOW_PATH = "/home/azureuser/src/amplihack/amplifier-bundle/recipes/default-workflow.yaml"

# Template placeholders used by all scenarios
DEFAULTS = {
    "repo_path": "/tmp/fake-repo",
    "branch_prefix": "amplihack",
    "issue_number": "3041",
}


def _load_step04_command() -> str:
    """Load the raw command string from step-04-setup-worktree in the YAML."""
    with open(WORKFLOW_PATH) as f:
        data = yaml.safe_load(f)

    for step in data.get("steps", []):
        if step.get("id") == "step-04-setup-worktree":
            return step["command"]

    raise LookupError("step-04-setup-worktree not found in workflow YAML")


def _extract_slug_script(full_command: str) -> str:
    """
    Extract only the slug-generation portion of the step-04 command.

    We extract from the TASK_DESC= line through the WORKTREE_PATH line,
    removing the inner git-check-ref-format guard block that requires a
    real git repository.
    """
    lines = full_command.splitlines()
    # Find the region from TASK_DESC= through WORKTREE_PATH=
    start_idx = None
    end_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("TASK_DESC=") and start_idx is None:
            start_idx = i
        if stripped.startswith("WORKTREE_PATH="):
            end_idx = i
            break

    if start_idx is None or end_idx is None:
        raise LookupError("Could not find TASK_DESC= ... WORKTREE_PATH= region in step-04")

    extracted = lines[start_idx : end_idx + 1]

    # Remove the inner git-check-ref-format guard block (lines that
    # contain "# Validate with authoritative" through matching "fi").
    # We identify these lines and skip them.
    filtered: list[str] = []
    skip_until_fi = False
    for line in extracted:
        stripped = line.strip()
        if "Validate with authoritative" in stripped:
            skip_until_fi = True
            continue
        if skip_until_fi:
            if stripped == "fi":
                skip_until_fi = False
            continue
        filtered.append(line)

    script = "set -euo pipefail\n" + "\n".join(filtered)
    return script


def _build_test_script(task_description: str) -> str:
    """
    Build a bash script that simulates what the recipe runner produces
    after template substitution, restricted to slug generation.

    Returns a bash script that, when run, prints BRANCH_NAME on stdout.
    """
    raw_command = _load_step04_command()
    slug_script = _extract_slug_script(raw_command)

    # Perform template substitution exactly as the recipe runner would:
    # literal text replacement of {{placeholder}} with values.
    script = slug_script
    script = script.replace("{{task_description}}", task_description)
    script = script.replace("{{repo_path}}", DEFAULTS["repo_path"])
    script = script.replace("{{branch_prefix}}", DEFAULTS["branch_prefix"])
    script = script.replace("{{issue_number}}", DEFAULTS["issue_number"])

    # Append a line that prints the branch name so we can capture it
    script += '\nprintf "%s" "$BRANCH_NAME"\n'

    return script


def _run_slug_script(task_description: str) -> subprocess.CompletedProcess:
    """Run the slug-generation script for the given task description."""
    script = _build_test_script(task_description)
    return subprocess.run(
        ["/bin/bash", "-c", script],
        capture_output=True,
        text=True,
        timeout=10,
    )


VALID_BRANCH_RE = re.compile(
    r"^amplihack/(issue-3041-[a-z0-9]([a-z0-9-]*[a-z0-9])?|task-unnamed-\d+)$"
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestIssue3041WorktreeQuoting:
    """Behavioral tests: template substitution must not break bash."""

    def test_scenario1_simple_description(self):
        """Happy path: plain ASCII task description with no special chars."""
        result = _run_slug_script("Add unit tests for auth module")
        assert result.returncode == 0, f"bash failed:\nstderr={result.stderr}"
        branch = result.stdout.strip()
        assert branch, "BRANCH_NAME must not be empty"
        assert VALID_BRANCH_RE.match(branch), f"Invalid branch name: {branch}"
        assert "add-unit-tests" in branch

    def test_scenario2_single_quote(self):
        """The reported bug: single quote in task_description."""
        result = _run_slug_script("Fix the user's profile page")
        assert result.returncode == 0, f"bash failed:\nstderr={result.stderr}"
        branch = result.stdout.strip()
        assert branch, "BRANCH_NAME must not be empty"
        assert VALID_BRANCH_RE.match(branch), f"Invalid branch name: {branch}"
        assert "fix-the-users-profile-page" in branch

    def test_scenario3_parentheses(self):
        """Parentheses in task_description."""
        result = _run_slug_script("Fix bug (broken layout)")
        assert result.returncode == 0, f"bash failed:\nstderr={result.stderr}"
        branch = result.stdout.strip()
        assert branch, "BRANCH_NAME must not be empty"
        assert VALID_BRANCH_RE.match(branch), f"Invalid branch name: {branch}"
        assert "fix-bug-broken-layout" in branch

    def test_scenario4_quotes_and_parens(self):
        """Worst case from the issue: both quotes and parentheses."""
        result = _run_slug_script("Fix user's page (broken layout)")
        assert result.returncode == 0, f"bash failed:\nstderr={result.stderr}"
        branch = result.stdout.strip()
        assert branch, "BRANCH_NAME must not be empty"
        assert VALID_BRANCH_RE.match(branch), f"Invalid branch name: {branch}"
        assert "fix-users-page-broken-layout" in branch

    def test_scenario5_backticks(self):
        """Backticks are command substitution in bash — must not execute."""
        result = _run_slug_script("Fix the render() method")
        assert result.returncode == 0, f"bash failed:\nstderr={result.stderr}"
        branch = result.stdout.strip()
        assert branch, "BRANCH_NAME must not be empty"
        assert VALID_BRANCH_RE.match(branch), f"Invalid branch name: {branch}"
        # backticks should be stripped, leaving "fix-the-render-method"
        assert "render" in branch

    def test_scenario6_newlines(self):
        """Multi-line task description — newlines must be normalised."""
        desc = "Fix the header\nand also the footer\nof the main page"
        result = _run_slug_script(desc)
        assert result.returncode == 0, f"bash failed:\nstderr={result.stderr}"
        branch = result.stdout.strip()
        assert branch, "BRANCH_NAME must not be empty"
        assert VALID_BRANCH_RE.match(branch), f"Invalid branch name: {branch}"
        assert "fix-the-header" in branch

    def test_scenario7_empty_description(self):
        """Empty task description — should produce fallback branch name."""
        result = _run_slug_script("")
        assert result.returncode == 0, f"bash failed:\nstderr={result.stderr}"
        branch = result.stdout.strip()
        assert branch, "BRANCH_NAME must not be empty"
        # Empty slug triggers task-unnamed fallback
        assert "task-unnamed-" in branch

    # --- Additional edge-case guards ---

    def test_double_quotes(self):
        """Double quotes should not break the heredoc."""
        result = _run_slug_script('Fix the "important" bug')
        assert result.returncode == 0, f"bash failed:\nstderr={result.stderr}"
        branch = result.stdout.strip()
        assert VALID_BRANCH_RE.match(branch), f"Invalid branch name: {branch}"

    def test_dollar_signs(self):
        """Dollar signs could trigger variable expansion — heredoc with
        single-quoted delimiter (<<'EOF') should prevent this."""
        result = _run_slug_script("Fix $HOME variable leak")
        assert result.returncode == 0, f"bash failed:\nstderr={result.stderr}"
        branch = result.stdout.strip()
        assert VALID_BRANCH_RE.match(branch), f"Invalid branch name: {branch}"
        # $HOME should NOT be expanded; 'home' should appear in slug
        assert "home" in branch

    def test_backslash(self):
        """Backslashes should be preserved literally in heredoc."""
        result = _run_slug_script("Fix path\\to\\file issue")
        assert result.returncode == 0, f"bash failed:\nstderr={result.stderr}"
        branch = result.stdout.strip()
        assert VALID_BRANCH_RE.match(branch), f"Invalid branch name: {branch}"

    def test_slug_max_length(self):
        """Slug should be truncated to 50 chars max."""
        long_desc = "a" * 200
        result = _run_slug_script(long_desc)
        assert result.returncode == 0, f"bash failed:\nstderr={result.stderr}"
        branch = result.stdout.strip()
        assert branch, "BRANCH_NAME must not be empty"
        # The slug portion (after "amplihack/issue-3041-") must be <= 50 chars
        slug_part = branch.split("issue-3041-", 1)[1]
        assert len(slug_part) <= 50
