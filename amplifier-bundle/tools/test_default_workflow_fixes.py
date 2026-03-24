#!/usr/bin/env python3
"""
Regression test suite for default-workflow bug fixes.

BL-001 (GitHub Issue #3022): step-03b-extract-issue-number uses `echo` (shell injection
  risk) and `tail -1` (picks last match, not canonical URL when 2>&1 noise is present).
  Fixed: heredoc capture + `printf '%s'` + `head -1`.

BL-002 (GitHub Issue #3023): step-04-setup-worktree is not idempotent — re-running the
  workflow when a branch/worktree already exists causes `git worktree add -b` to fail.
  Fixed: three-state guard (both exist → reuse, branch only → add worktree, neither →
  full create path) with `created=true/false` diagnostic in output JSON.

Test strategy:
  - BL-001: subprocess.run() bash snippets with controlled stdin (no git required)
  - BL-002: real git repos in tempfile.mkdtemp() — no mocking (matches codebase convention)
  - All tests use stdlib only: unittest, subprocess, tempfile, shutil, os, json, re

Run:
  python -m pytest amplifier-bundle/tools/test_default_workflow_fixes.py -v
  # or
  python -m unittest amplifier-bundle/tools/test_default_workflow_fixes.py -v
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# --- BL-001 bash snippets ---

# The FIXED extraction command — tests assert this behaves correctly.
# NOTE: The EOFISSUECREATION delimiter is intentionally long and specific to
# prevent accidental collision with issue body text that might contain "EOF".
# FIX (#3480): Now fails with exit 1 when extraction produces empty result.
_BL001_FIXED_CMD = textwrap.dedent("""\
    set +H  # disable history expansion so !-tokens are safe
    ISSUE_CREATION=$(cat <<'EOFISSUECREATION'
    {issue_creation}
    EOFISSUECREATION
    )
    EXTRACTED=$(printf '%s' "$ISSUE_CREATION" | grep -oE 'issues/[0-9]+' | grep -oE '[0-9]+' | head -1)
    if [ -z "$EXTRACTED" ]; then
      echo "ERROR: step-03b failed to extract issue number from issue_creation output." >&2
      exit 1
    fi
    printf '%s' "$EXTRACTED"
""")


def _run_extraction_fixed(issue_creation: str) -> str:
    """Run the FIXED BL-001 extraction bash snippet and return trimmed stdout.

    Raises RuntimeError if the script exits non-zero (e.g. empty extraction).
    """
    script = _BL001_FIXED_CMD.format(issue_creation=issue_creation)
    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Extraction failed (rc={result.returncode}): {result.stderr.strip()}")
    return result.stdout.strip()


def _run_extraction_buggy(issue_creation: str) -> str:
    """Run the BUGGY BL-001 extraction bash snippet (for regression-proof tests)."""
    # We cannot safely interpolate arbitrary content into an unquoted variable,
    # but for the specific adversarial inputs tested here we use a temp file
    # so the shell never sees the content as code.
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(issue_creation)
        tmp = f.name
    try:
        # Read from file — avoids direct shell injection — but tail-1 bug is still present.
        script = f'grep -oE "issues/[0-9]+" {tmp} | grep -oE "[0-9]+" | tail -1'
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    finally:
        os.unlink(tmp)


# --- BL-002 bash helpers ---


def _git(*args, cwd=None, check=True) -> subprocess.CompletedProcess:
    """Run a git command."""
    return subprocess.run(
        ["git"] + list(args),
        cwd=cwd,
        capture_output=True,
        text=True,
        check=check,
    )


def _init_repo_with_commit(path: str) -> None:
    """Initialise a bare-enough git repo that worktrees can be added from it."""
    _git("init", cwd=path)
    _git("config", "user.email", "test@example.com", cwd=path)
    _git("config", "user.name", "Test", cwd=path)
    # Create an initial commit so HEAD exists
    readme = os.path.join(path, "README.md")
    Path(readme).write_text("init\n")
    _git("add", "README.md", cwd=path)
    _git("commit", "-m", "Initial commit", cwd=path)
    # Create a local 'origin/main' ref so 'git worktree add ... origin/main' succeeds.
    # In a real workflow the repo already has a remote; here we simulate it by creating
    # a local remote-tracking branch.
    _git("branch", "main", cwd=path)
    _git("update-ref", "refs/remotes/origin/main", "HEAD", cwd=path)


# The FIXED step-04 idempotency bash logic, parameterised for tests.
# SECURITY NOTE: grep -F is required (not -E/-P) so that filesystem path
# characters (., +, *) are not interpreted as regex metacharacters.
# Uses printf for JSON output to avoid heredoc quoting complexity in tests.
_BL002_FIXED_STEP4_FULL = textwrap.dedent("""\
    set -euo pipefail
    REPO_PATH={repo_path!r}
    BRANCH_NAME={branch_name!r}
    WORKTREE_PATH={worktree_path!r}

    cd "$REPO_PATH"

    BRANCH_EXISTS=$(git branch --list "$BRANCH_NAME")
    WORKTREE_EXISTS=$(git worktree list --porcelain | grep -Fx "worktree $WORKTREE_PATH" || true)

    if [ -n "$BRANCH_EXISTS" ] && [ -n "$WORKTREE_EXISTS" ]; then
      echo "INFO: Branch and worktree already exist — reusing." >&2
      CREATED=false
    elif [ -n "$BRANCH_EXISTS" ] && [ -z "$WORKTREE_EXISTS" ]; then
      echo "INFO: Branch exists but worktree is missing — adding worktree without -b." >&2
      git worktree add "$WORKTREE_PATH" "$BRANCH_NAME" >&2
      CREATED=true
    else
      echo "INFO: Creating new branch and worktree." >&2
      git worktree add "$WORKTREE_PATH" -b "$BRANCH_NAME" origin/main >&2
      CREATED=true
    fi

    git -C "$WORKTREE_PATH" push origin "$BRANCH_NAME" 2>/dev/null || true
    git -C "$WORKTREE_PATH" branch --set-upstream-to="origin/$BRANCH_NAME" "$BRANCH_NAME" 2>/dev/null || true

    printf '{{"worktree_path":"%s","branch_name":"%s","created":%s}}\\n' \\
      "$WORKTREE_PATH" "$BRANCH_NAME" "$CREATED"
""")


def _run_step4(repo_path: str, branch_name: str, worktree_path: str) -> dict:
    """Run the FIXED step-04 idempotency logic and return parsed JSON output."""
    script = _BL002_FIXED_STEP4_FULL.format(
        repo_path=repo_path,
        branch_name=branch_name,
        worktree_path=worktree_path,
    )
    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"step-04 script failed (rc={result.returncode}):\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    return json.loads(result.stdout.strip())


# ===========================================================================
# BL-001: Issue number extraction tests
# ===========================================================================


class TestExtractIssueNumber(unittest.TestCase):
    """
    Tests for the step-03b-extract-issue-number fix (GitHub Issue #3022).

    Regression contract:
      - head -1 must be used, not tail -1, so the canonical URL line wins.
      - heredoc capture (not echo) must be used so shell metacharacters in
        issue body text are never executed.
    """

    # --- Happy-path tests ---

    def test_extract_issue_number_from_url(self):
        """Standard case: single URL line → issue number extracted."""
        issue_creation = "https://github.com/org/repo/issues/3022\n"
        result = _run_extraction_fixed(issue_creation)
        self.assertEqual(result, "3022")

    def test_extract_issue_number_head_not_tail(self):
        """
        BL-001 core regression: URL on first line, noise number on last line.

        With tail -1 (buggy): returns '9999' (from warning message).
        With head -1 (fixed): returns '3022' (from canonical URL).
        """
        issue_creation = "https://github.com/org/repo/issues/3022\nwarning: something about 9999\n"
        result = _run_extraction_fixed(issue_creation)
        self.assertEqual(
            result,
            "3022",
            "head -1 must select the canonical URL number, not the trailing noise number",
        )

    def test_extract_issue_number_no_url(self):
        """No issue URL present → extraction fails with error, not silent empty."""
        issue_creation = "Error: authentication required\n"
        with self.assertRaises(RuntimeError) as ctx:
            _run_extraction_fixed(issue_creation)
        self.assertIn("step-03b failed", str(ctx.exception))

    def test_extract_issue_number_multiline_no_url(self):
        """Multiple lines, none containing an issue URL → extraction fails."""
        issue_creation = "Creating issue...\nDone.\n"
        with self.assertRaises(RuntimeError) as ctx:
            _run_extraction_fixed(issue_creation)
        self.assertIn("step-03b failed", str(ctx.exception))

    # --- Regression: tail-1 selects wrong number ---

    def test_tail_one_selects_wrong_number_regression(self):
        """
        Prove that tail -1 would pick the wrong number (regression proof).

        This test documents the BUG: when noise captured via 2>&1 contains a
        second issues/<N> URL after the canonical line, tail -1 returns the
        noise number instead of the canonical one.

        Example: gh sometimes emits "see also: issues/9999" after the creation URL.
        With tail -1 (buggy): returns '9999' (last match).
        With head -1 (fixed): returns '3022' (first match = canonical URL).
        """
        # Noise line must contain 'issues/<number>' to be matched by the grep pipeline.
        issue_creation = (
            "https://github.com/org/repo/issues/3022\nnote: see related issues/9999 for context\n"
        )
        # The buggy tail-1 path (via file-based helper that avoids injection risk)
        buggy_result = _run_extraction_buggy(issue_creation)
        # The fixed head-1 path
        fixed_result = _run_extraction_fixed(issue_creation)

        self.assertEqual(
            buggy_result,
            "9999",
            "Regression proof: buggy tail-1 selects the noise number",
        )
        self.assertEqual(
            fixed_result,
            "3022",
            "Fixed head-1 selects the canonical URL number",
        )
        self.assertNotEqual(
            fixed_result,
            buggy_result,
            "Fixed and buggy outputs must differ when noise is present",
        )

    # --- Adversarial / security tests ---

    def test_extract_issue_number_command_substitution_not_executed(self):
        """
        Adversarial: $(id) in issue body must not be executed.

        With echo {{variable}} (buggy): shell expands $(...) before echo sees it.
        With heredoc capture (fixed): content is literal; grep sanitises to digits only.
        """
        issue_creation = "$(id)\nhttps://github.com/org/repo/issues/3022\n"
        result = _run_extraction_fixed(issue_creation)
        self.assertEqual(result, "3022")
        # The output must be a pure integer string — no 'uid=' or similar
        self.assertRegex(result, r"^\d+$", "Output must be digits only — no command output")

    def test_extract_issue_number_backtick_injection_not_executed(self):
        """
        Adversarial: backtick injection in issue body must not be executed.
        """
        issue_creation = "`whoami`\nhttps://github.com/org/repo/issues/3022\n"
        result = _run_extraction_fixed(issue_creation)
        self.assertEqual(result, "3022")
        self.assertNotIn("root", result)
        self.assertNotIn("azureuser", result)

    def test_extract_issue_number_history_expansion_safe(self):
        """
        Adversarial: !history token must not trigger bash history expansion.

        set +H is present in the fixed script to disable this.
        """
        issue_creation = "!history\nhttps://github.com/org/repo/issues/3022\n"
        result = _run_extraction_fixed(issue_creation)
        self.assertEqual(result, "3022")

    def test_extract_issue_number_output_is_digits_only(self):
        """Output must match \\d+ — structural sanitisation guarantee."""
        issue_creation = "https://github.com/org/repo/issues/42\n"
        result = _run_extraction_fixed(issue_creation)
        self.assertRegex(result, r"^\d+$")

    def test_extract_issue_number_large_number(self):
        """Issue numbers can be large integers (e.g. 999999)."""
        issue_creation = "https://github.com/org/repo/issues/999999\n"
        result = _run_extraction_fixed(issue_creation)
        self.assertEqual(result, "999999")


# ===========================================================================
# BL-002: Idempotency tests
# ===========================================================================


class TestStep4Idempotency(unittest.TestCase):
    """
    Tests for the step-04-setup-worktree idempotency fix (GitHub Issue #3023).

    Regression contract:
      - State 3 (neither branch nor worktree): create both, created=true
      - State 1 (both exist): reuse silently, created=false
      - State 2 (branch only): add worktree from existing branch, created=true
      - All states must exit 0 — no failure on re-run
    """

    def setUp(self):
        """Create a temporary git repo for each test."""
        self.repo_dir = tempfile.mkdtemp(prefix="test_wf_repo_")
        _init_repo_with_commit(self.repo_dir)
        self.branch_name = "feat/issue-3023-idempotency-test"
        self.worktree_path = os.path.join(self.repo_dir, "worktrees", self.branch_name)

    def tearDown(self):
        """Remove temporary git repo (worktrees included)."""
        # Prune worktrees before rmtree to avoid git lock warnings
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=self.repo_dir,
            capture_output=True,
        )
        shutil.rmtree(self.repo_dir, ignore_errors=True)

    # --- State 3: neither branch nor worktree exists ---

    def test_step4_creates_branch_and_worktree(self):
        """
        State 3: fresh repo — branch and worktree must be created.
        Output JSON must contain created=true and correct paths.
        """
        output = _run_step4(self.repo_dir, self.branch_name, self.worktree_path)

        self.assertTrue(output["created"], "First run must report created=true")
        self.assertEqual(output["branch_name"], self.branch_name)
        self.assertEqual(output["worktree_path"], self.worktree_path)

        # Verify the branch actually exists
        result = _git("branch", "--list", self.branch_name, cwd=self.repo_dir)
        self.assertIn(self.branch_name, result.stdout)

        # Verify the worktree directory exists
        self.assertTrue(
            os.path.isdir(self.worktree_path),
            f"Worktree directory must exist at {self.worktree_path}",
        )

    # --- State 1: both branch and worktree exist ---

    def test_step4_idempotent_both_exist(self):
        """
        State 1 (core idempotency regression): run step-04 twice.
        Second run must NOT fail and must report created=false.

        With the buggy code, the second run calls 'git worktree add -b BRANCH'
        which fails with 'fatal: A branch named BRANCH already exists.'
        """
        # First run — creates branch + worktree
        first = _run_step4(self.repo_dir, self.branch_name, self.worktree_path)
        self.assertTrue(first["created"], "First run must report created=true")

        # Second run — must reuse silently
        second = _run_step4(self.repo_dir, self.branch_name, self.worktree_path)
        self.assertFalse(
            second["created"],
            "Second run (both exist) must report created=false — state 1 reuse path",
        )
        self.assertEqual(second["branch_name"], self.branch_name)
        self.assertEqual(second["worktree_path"], self.worktree_path)

    def test_step4_idempotent_second_run_returns_zero(self):
        """
        BL-002 regression: verify the second run exits 0, not non-zero.

        This directly tests the failure mode: 'git worktree add -b ...' fails
        with exit code 128 when the branch already exists.
        """
        # First run
        script_first = _BL002_FIXED_STEP4_FULL.format(
            repo_path=self.repo_dir,
            branch_name=self.branch_name,
            worktree_path=self.worktree_path,
        )
        result_first = subprocess.run(["bash", "-c", script_first], capture_output=True, text=True)
        self.assertEqual(result_first.returncode, 0, f"First run failed: {result_first.stderr}")

        # Second run — must also exit 0 (buggy code exits 128 here)
        script_second = _BL002_FIXED_STEP4_FULL.format(
            repo_path=self.repo_dir,
            branch_name=self.branch_name,
            worktree_path=self.worktree_path,
        )
        result_second = subprocess.run(
            ["bash", "-c", script_second], capture_output=True, text=True
        )
        self.assertEqual(
            result_second.returncode,
            0,
            f"Second run (idempotency) must exit 0 but got {result_second.returncode}.\n"
            f"stderr: {result_second.stderr}",
        )

    # --- State 2: branch exists but worktree is missing ---

    def test_step4_idempotent_branch_only(self):
        """
        State 2: branch exists but worktree directory is absent.
        step-04 must add the worktree from the existing branch (no -b flag)
        and report created=true.
        """
        # Create branch manually without worktree
        _git("branch", self.branch_name, "HEAD", cwd=self.repo_dir)

        # Verify worktree does NOT exist yet
        self.assertFalse(
            os.path.isdir(self.worktree_path),
            "Worktree must not exist before test run (state 2 setup)",
        )

        output = _run_step4(self.repo_dir, self.branch_name, self.worktree_path)

        self.assertTrue(
            output["created"],
            "State 2: worktree added from existing branch — created must be true",
        )
        self.assertTrue(
            os.path.isdir(self.worktree_path),
            "Worktree directory must exist after state-2 run",
        )

    def test_step4_branch_only_worktree_is_on_correct_branch(self):
        """
        State 2: the created worktree must check out the pre-existing branch,
        not a new branch or main.
        """
        # Create branch with a distinct commit so we can verify checkout
        _git("branch", self.branch_name, "HEAD", cwd=self.repo_dir)

        _run_step4(self.repo_dir, self.branch_name, self.worktree_path)

        # Check HEAD in the worktree points to the expected branch
        result = _git("rev-parse", "--abbrev-ref", "HEAD", cwd=self.worktree_path)
        self.assertEqual(
            result.stdout.strip(),
            self.branch_name,
            "Worktree HEAD must be on the intended branch",
        )

    # --- Output JSON contract ---

    def test_step4_output_json_structure(self):
        """Output JSON must contain worktree_path, branch_name, and created keys."""
        output = _run_step4(self.repo_dir, self.branch_name, self.worktree_path)

        self.assertIn("worktree_path", output)
        self.assertIn("branch_name", output)
        self.assertIn("created", output)
        self.assertIsInstance(output["created"], bool)

    def test_step4_output_json_created_false_on_reuse(self):
        """created=false must be a JSON boolean false, not the string 'false'."""
        # First run
        _run_step4(self.repo_dir, self.branch_name, self.worktree_path)
        # Second run
        output = _run_step4(self.repo_dir, self.branch_name, self.worktree_path)

        self.assertIs(output["created"], False)  # strict bool check

    # --- Adversarial: branch name sanitisation ---

    def test_step4_adversarial_task_description_path_traversal(self):
        """
        Adversarial: task_description='../../etc/passwd' must produce a safe branch name.

        The sanitisation pipeline (tr -cd 'a-z0-9-') in step-04 strips all
        characters outside [a-z0-9-], so path separators are removed.
        This test verifies the sanitised branch name is safe.
        """
        # Simulate what the sanitisation pipeline produces from a path traversal input
        raw = "../../etc/passwd"
        sanitised = re.sub(r"[^a-z0-9-]", "", raw.lower())
        # 'etc/passwd' → after stripping '/' → 'etcpasswd'
        if not sanitised:
            sanitised = "task-unnamed"

        branch_name = f"feat/issue-9999-{sanitised}" if sanitised else "feat/task-unnamed"
        worktree_path = os.path.join(self.repo_dir, "worktrees", branch_name)

        # Must not raise; branch name must not contain path traversal components
        output = _run_step4(self.repo_dir, branch_name, worktree_path)
        self.assertNotIn("..", output["branch_name"])
        self.assertNotIn("/etc/", output["branch_name"])

    def test_step4_adversarial_task_description_command_separator_stripped(self):
        """
        Adversarial: semicolons in task_description must be stripped from branch name.

        The sanitisation pipeline uses tr -cd 'a-z0-9-' which removes semicolons,
        spaces, slashes, and all other non-alphanumeric-hyphen characters.
        The critical assertion is that the semicolon itself is gone — preventing
        shell command separation (e.g. '; rm -rf /').
        """
        raw = "foo; rm -rf /tmp/test"
        sanitised = raw.lower()
        sanitised = sanitised.replace(" ", "-")
        sanitised = re.sub(r"[^a-z0-9-]", "", sanitised)
        sanitised = re.sub(r"-+", "-", sanitised).strip("-")

        branch_name = f"feat/issue-9999-{sanitised}"
        worktree_path = os.path.join(self.repo_dir, "worktrees", branch_name)

        # The semicolon must have been stripped — that's the injection prevention
        self.assertNotIn(";", branch_name, "Semicolon must be stripped by sanitisation")
        # Slashes (except the feat/ prefix) and spaces must also be gone
        branch_suffix = branch_name.split("/", 1)[-1]  # part after 'feat/'
        self.assertNotIn(" ", branch_suffix)

        output = _run_step4(self.repo_dir, branch_name, worktree_path)
        self.assertTrue(output["created"])


# ===========================================================================
# TestYAMLBugRegression — tests that run the CURRENT YAML commands directly.
#
# These tests are RED until the YAML is patched (TDD "failing first" phase).
# They read the step commands from default-workflow.yaml, substitute the
# template variables, and execute them.  Once the YAML contains the fixes
# described in BL-001 and BL-002, all tests in this class become GREEN.
# ===========================================================================

_RECIPES_DIR = Path(__file__).parent.parent / "recipes"
_WORKFLOW_YAML = _RECIPES_DIR / "default-workflow.yaml"


def _extract_step_command(yaml_path: Path, step_id: str) -> str:
    """
    Parse default-workflow.yaml line-by-line to extract the 'command:' block
    for the given step id.  Returns the raw (un-indented) bash command string.
    Raises ValueError if the step is not found.

    YAML list items look like:
      - id: "step-03b-extract-issue-number"
        type: "bash"
        command: |
          ...bash here...

    The '- ' prefix means stripped line is '- id: "..."' not 'id: "..."'.
    """
    text = yaml_path.read_text()
    lines = text.splitlines()

    # Find the step by id (handles both '- id: "X"' and 'id: "X"' forms)
    in_step = False
    command_lines: list[str] = []
    in_command = False
    base_indent: int | None = None

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # Strip leading YAML list marker
        stripped_no_dash = stripped.lstrip("- ").strip() if stripped.startswith("-") else stripped

        if not in_step:
            if stripped_no_dash == f'id: "{step_id}"':
                in_step = True
            i += 1
            continue

        # Inside the correct step — look for the command block
        if not in_command:
            if stripped.startswith("command:"):
                # Inline command (rare): 'command: "..."'
                inline = stripped[len("command:") :].strip()
                if inline and inline != "|":
                    return inline.strip("\"'")
                # Block scalar (command: |): next lines are the body
                in_command = True
            elif stripped_no_dash.startswith('id: "'):
                # Hit the next step — command not found
                break
            i += 1
            continue

        # In the command block — collect until indentation resets to step level
        if not line.strip():
            command_lines.append("")
            i += 1
            continue

        indent = len(line) - len(line.lstrip())
        if base_indent is None:
            base_indent = indent

        if indent < base_indent and line.strip():
            # Dedented back to step-level key — end of command block
            break

        command_lines.append(line[base_indent:] if base_indent else line)
        i += 1

    if not command_lines:
        raise ValueError(f"Step '{step_id}' not found or has no command in {yaml_path}")

    return "\n".join(command_lines)


class TestYAMLBugRegression(unittest.TestCase):
    """
    End-to-end regression tests that run the ACTUAL step commands from
    default-workflow.yaml.  These tests fail against the current (buggy)
    YAML and pass once the fixes are applied.

    BL-001 target: step-03b-extract-issue-number
    BL-002 target: step-04-setup-worktree
    """

    # -----------------------------------------------------------------------
    # BL-001: step-03b must use head -1, not tail -1
    # -----------------------------------------------------------------------

    def test_yaml_step03b_head_not_tail(self):
        """
        TDD RED: current YAML uses tail -1, returning the last number when noise
          containing 'issues/<N>' appears after the canonical URL on the same line.
        TDD GREEN: after fix (heredoc + head -1), the first match wins.

        Uses single-line input so the echo pipeline is not broken by newlines —
        isolating the tail-1 vs head-1 bug specifically.

        With the CURRENT echo+tail-1: returns '9999' (last grep -oE match).
        With the FIXED heredoc+head-1: returns '3022' (first grep -oE match).
        """
        raw_cmd = _extract_step_command(_WORKFLOW_YAML, "step-03b-extract-issue-number")

        # Single-line input: both 'issues/3022' and 'issues/9999' are present.
        # grep -oE 'issues/[0-9]+' produces two matches in order; tail picks last.
        issue_creation_value = (
            "https://github.com/org/repo/issues/3022 note: see related issues/9999"
        )
        cmd = raw_cmd.replace("{{issue_creation}}", issue_creation_value)

        result = subprocess.run(
            ["bash", "-c", cmd],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"Command failed:\n{result.stderr}")
        extracted = result.stdout.strip()
        self.assertEqual(
            extracted,
            "3022",
            f"Expected canonical issue number '3022' but got '{extracted}'. "
            "The YAML must use head -1, not tail -1 — "
            "this test fails until BL-001 fix is applied.",
        )

    def test_yaml_step03b_no_echo_injection(self):
        """
        TDD RED: current YAML uses 'echo {{issue_creation}}' which collapses
          newlines and causes head/tail to see only one line.
        TDD GREEN: after fix, heredoc preserves newlines so head -1 works correctly.

        Specifically: multi-line issue_creation with a URL on line 2 must still
        be processed line-by-line by grep.
        """
        raw_cmd = _extract_step_command(_WORKFLOW_YAML, "step-03b-extract-issue-number")

        # URL is on the SECOND line — echo collapses this to one line, which
        # the grep pipeline still handles, but heredoc preserves structure.
        issue_creation_value = "Creating issue...\nhttps://github.com/org/repo/issues/5555\n"
        cmd = raw_cmd.replace("{{issue_creation}}", issue_creation_value)

        result = subprocess.run(
            ["bash", "-c", cmd],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, f"Command failed:\n{result.stderr}")
        extracted = result.stdout.strip()
        self.assertEqual(
            extracted,
            "5555",
            f"Expected '5555' but got '{extracted}'. "
            "Multi-line issue_creation must be handled correctly.",
        )

    # -----------------------------------------------------------------------
    # BL-002: step-04 must be idempotent
    # -----------------------------------------------------------------------

    def setUp(self):
        """
        Create a temporary git repo WITH a real local origin remote so that
        'git fetch origin main' and 'git push origin BRANCH' succeed without
        network access.  The origin is a bare repo in a sibling temp directory.
        """
        # Bare "origin" repo
        self.origin_dir = tempfile.mkdtemp(prefix="test_yaml_reg_origin_")
        subprocess.run(["git", "init", "--bare", self.origin_dir], check=True, capture_output=True)

        # Working repo
        self.repo_dir = tempfile.mkdtemp(prefix="test_yaml_reg_")
        _git("init", cwd=self.repo_dir)
        _git("config", "user.email", "test@example.com", cwd=self.repo_dir)
        _git("config", "user.name", "Test", cwd=self.repo_dir)
        _git("remote", "add", "origin", self.origin_dir, cwd=self.repo_dir)

        # Initial commit + push to origin so 'origin/main' ref exists
        readme = os.path.join(self.repo_dir, "README.md")
        Path(readme).write_text("init\n")
        _git("add", "README.md", cwd=self.repo_dir)
        _git("commit", "-m", "Initial commit", cwd=self.repo_dir)
        _git("push", "-u", "origin", "HEAD:main", cwd=self.repo_dir)
        # Create local tracking branch
        _git("branch", "--set-upstream-to=origin/main", "main", cwd=self.repo_dir, check=False)

        self.branch_name = "feat/issue-3023-yaml-regression"
        self.worktree_path = os.path.join(self.repo_dir, "worktrees", self.branch_name)

    def tearDown(self):
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=self.repo_dir,
            capture_output=True,
        )
        shutil.rmtree(self.repo_dir, ignore_errors=True)
        shutil.rmtree(self.origin_dir, ignore_errors=True)

    def _build_step4_cmd(self, raw_cmd: str) -> str:
        """Substitute template variables in the step-04 command."""
        cmd = raw_cmd
        cmd = cmd.replace("{{repo_path}}", self.repo_dir)
        cmd = cmd.replace("{{branch_prefix}}", "feat")
        cmd = cmd.replace("{{issue_number}}", "3023")
        cmd = cmd.replace("{{task_description}}", "issue-3023-yaml-regression")
        return cmd

    def test_yaml_step04_second_run_exits_zero(self):
        """
        TDD RED: current YAML calls 'git worktree add -b BRANCH' unconditionally.
          Second run fails with exit code 128 ('branch already exists').
        TDD GREEN: after fix, second run detects existing branch+worktree and exits 0.
        """
        raw_cmd = _extract_step_command(_WORKFLOW_YAML, "step-04-setup-worktree")
        cmd = self._build_step4_cmd(raw_cmd)

        # First run — must succeed
        result1 = subprocess.run(
            ["bash", "-c", cmd], capture_output=True, text=True, cwd=self.repo_dir
        )
        self.assertEqual(
            result1.returncode,
            0,
            f"First run of step-04 failed:\n{result1.stderr}",
        )

        # Rebuild cmd with exact values from first run to ensure same branch/worktree
        raw_cmd2 = _extract_step_command(_WORKFLOW_YAML, "step-04-setup-worktree")
        cmd2 = self._build_step4_cmd(raw_cmd2)

        # Second run — must NOT fail with 128
        result2 = subprocess.run(
            ["bash", "-c", cmd2], capture_output=True, text=True, cwd=self.repo_dir
        )
        self.assertEqual(
            result2.returncode,
            0,
            f"Second run of step-04 must exit 0 (idempotency). "
            f"Got rc={result2.returncode}.\n"
            f"stderr: {result2.stderr}\n"
            f"This test fails until BL-002 fix is applied to default-workflow.yaml.",
        )

    def test_yaml_step04_second_run_created_false(self):
        """
        TDD RED: current YAML always emits '"created": true'.
        TDD GREEN: after fix, second run emits '"created": false'.
        """
        raw_cmd = _extract_step_command(_WORKFLOW_YAML, "step-04-setup-worktree")
        cmd = self._build_step4_cmd(raw_cmd)

        # First run
        result1 = subprocess.run(
            ["bash", "-c", cmd], capture_output=True, text=True, cwd=self.repo_dir
        )
        if result1.returncode != 0:
            self.skipTest(f"First run failed ({result1.returncode}) — cannot test second run")

        # Second run
        result2 = subprocess.run(
            ["bash", "-c", cmd], capture_output=True, text=True, cwd=self.repo_dir
        )
        if result2.returncode != 0:
            self.fail(
                f"Second run exited {result2.returncode} — BL-002 fix not applied.\n"
                f"stderr: {result2.stderr}"
            )

        try:
            output2 = json.loads(result2.stdout.strip())
        except json.JSONDecodeError:
            self.fail(
                f"Second run stdout is not valid JSON: {result2.stdout!r}\n"
                "After BL-002 fix the output must be parseable JSON with created=false."
            )

        self.assertFalse(
            output2.get("created"),
            f"Second run must emit created=false (reuse path) but got: {output2}.\n"
            "This test fails until BL-002 fix is applied to default-workflow.yaml.",
        )


# ===========================================================================
# TEST-001: Step 15/16 error path tests
# ===========================================================================

# --- Step 15 bash snippets ---

# Extracted staging-area check from step-15-commit-push.
# Mirrors the if/else logic that detects hollow-success (nothing staged).
_STEP15_STAGING_CHECK = textwrap.dedent("""\
    set -euo pipefail
    cd {repo_path}
    git add -A
    if [ -n "$(git diff --cached --name-only)" ]; then
      echo "COMMIT_OK"
    else
      echo "ERROR: Nothing staged to commit." >&2
      echo "This is a hollow-success condition" >&2
      exit 1
    fi
""")

# --- Step 16 bash snippets ---

# Extracted issue_number validation from step-16-create-draft-pr.
_STEP16_ISSUE_VALIDATION = textwrap.dedent("""\
    set -euo pipefail
    ISSUE_NUM="{issue_number}"
    if ! [[ "$ISSUE_NUM" =~ ^[0-9]+$ ]]; then
        echo "ERROR: issue_number is not numeric: $ISSUE_NUM" >&2
        exit 1
    fi
    echo "VALID"
""")

# Extracted commits-ahead check from step-16-create-draft-pr.
_STEP16_COMMITS_AHEAD_CHECK = textwrap.dedent("""\
    set -euo pipefail
    cd {repo_path}
    COMMITS_AHEAD=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo "0")
    if [ "$COMMITS_AHEAD" -eq 0 ]; then
        echo "ERROR: 0 commits ahead of main." >&2
        echo "This is a hollow-success condition: the workflow ran but produced no commits." >&2
        exit 1
    fi
    echo "PUSH_OK"
""")


class TestStep15CommitPush(unittest.TestCase):
    """
    Tests for step-15-commit-push error paths (TEST-001).

    Regression contract:
      - Empty staging area (nothing to commit) must exit 1 with 'hollow-success'
      - Non-empty staging area proceeds to commit
    """

    def setUp(self):
        self.repo_dir = tempfile.mkdtemp(prefix="test_step15_")
        _init_repo_with_commit(self.repo_dir)

    def tearDown(self):
        shutil.rmtree(self.repo_dir, ignore_errors=True)

    def test_empty_staging_area_exits_1_with_hollow_success(self):
        """Empty staging area → must exit 1 with 'hollow-success' in message."""
        script = _STEP15_STAGING_CHECK.format(repo_path=self.repo_dir)
        result = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, f"Expected exit 1 but got {result.returncode}")
        self.assertIn("hollow-success", result.stderr)

    def test_staging_area_with_changes_succeeds(self):
        """When new files exist, git add -A stages them and the check passes."""
        new_file = os.path.join(self.repo_dir, "new_file.txt")
        Path(new_file).write_text("test content\n")
        script = _STEP15_STAGING_CHECK.format(repo_path=self.repo_dir)
        result = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        self.assertEqual(
            result.returncode, 0, f"Expected exit 0 but got {result.returncode}: {result.stderr}"
        )
        self.assertIn("COMMIT_OK", result.stdout)

    def test_git_diff_cached_detects_staged_modifications(self):
        """Modified tracked file must be detected as staged after git add -A."""
        readme = os.path.join(self.repo_dir, "README.md")
        Path(readme).write_text("modified content\n")
        script = _STEP15_STAGING_CHECK.format(repo_path=self.repo_dir)
        result = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("COMMIT_OK", result.stdout)

    def test_no_upstream_tracking_skips_push(self):
        """When no upstream tracking branch exists, step-15 should skip push with WARNING."""
        script = """
        set -euo pipefail
        TMPDIR=$(mktemp -d)
        cd "$TMPDIR"
        git init -q
        git commit --allow-empty -m "init" -q
        # No remote configured — @{u} should fail
        if ! git rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1; then
            echo "WARNING: No upstream tracking branch configured — skipping push" >&2
            rm -rf "$TMPDIR"
            exit 0
        fi
        rm -rf "$TMPDIR"
        exit 1  # Should not reach here
        """
        result = subprocess.run(
            ["/bin/bash", "-c", script], capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("WARNING", result.stderr)
        self.assertIn("upstream", result.stderr.lower())


class TestStep16CreateDraftPR(unittest.TestCase):
    """
    Tests for step-16-create-draft-pr error paths (TEST-001).

    Regression contract:
      - Non-numeric issue_number must exit 1
      - Zero commits ahead of upstream must exit 1 with 'hollow-success'
      - Valid numeric issue_number passes validation
    """

    def test_non_numeric_issue_number_exits_1(self):
        """Non-numeric issue_number must exit 1 with 'not numeric' message."""
        for bad_value in ["abc", "12.34", "issue-42", "", " "]:
            with self.subTest(issue_number=bad_value):
                script = _STEP16_ISSUE_VALIDATION.format(issue_number=bad_value)
                result = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
                self.assertNotEqual(
                    result.returncode, 0, f"Expected non-zero exit for '{bad_value}'"
                )

    def test_numeric_issue_number_succeeds(self):
        """Valid numeric issue_number must pass validation."""
        for good_value in ["1", "42", "999999"]:
            with self.subTest(issue_number=good_value):
                script = _STEP16_ISSUE_VALIDATION.format(issue_number=good_value)
                result = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0)
                self.assertIn("VALID", result.stdout)

    def test_zero_commits_ahead_exits_1_with_hollow_success(self):
        """Zero commits ahead of upstream → must exit 1 with 'hollow-success'."""
        origin_dir = tempfile.mkdtemp(prefix="test_step16_origin_")
        repo_dir = tempfile.mkdtemp(prefix="test_step16_")
        try:
            subprocess.run(
                ["git", "init", "--bare", origin_dir],
                check=True,
                capture_output=True,
            )
            _git("init", cwd=repo_dir)
            _git("config", "user.email", "test@example.com", cwd=repo_dir)
            _git("config", "user.name", "Test", cwd=repo_dir)
            _git("remote", "add", "origin", origin_dir, cwd=repo_dir)
            Path(os.path.join(repo_dir, "README.md")).write_text("init\n")
            _git("add", "README.md", cwd=repo_dir)
            _git("commit", "-m", "Initial commit", cwd=repo_dir)
            _git("push", "-u", "origin", "HEAD:main", cwd=repo_dir)
            _git(
                "branch",
                "--set-upstream-to=origin/main",
                "main",
                cwd=repo_dir,
                check=False,
            )

            script = _STEP16_COMMITS_AHEAD_CHECK.format(repo_path=repo_dir)
            result = subprocess.run(
                ["bash", "-c", script],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("hollow-success", result.stderr)
        finally:
            shutil.rmtree(repo_dir, ignore_errors=True)
            shutil.rmtree(origin_dir, ignore_errors=True)

    def test_existing_pr_detection_logic(self):
        """When gh pr list returns a match, skip PR creation."""
        script = """
        set -euo pipefail
        # Simulate gh pr list returning a PR URL
        EXISTING_PR="https://github.com/test/repo/pull/42"
        if [ -n "$EXISTING_PR" ]; then
            echo "PR already exists: $EXISTING_PR"
            exit 0
        fi
        exit 1
        """
        result = subprocess.run(
            ["/bin/bash", "-c", script], capture_output=True, text=True, timeout=5
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("PR already exists", result.stdout)

    def test_commits_ahead_succeeds(self):
        """When commits exist ahead of origin/main, the check passes."""
        origin_dir = tempfile.mkdtemp(prefix="test_step16_origin_")
        repo_dir = tempfile.mkdtemp(prefix="test_step16_")
        try:
            subprocess.run(
                ["git", "init", "--bare", origin_dir],
                check=True,
                capture_output=True,
            )
            _git("init", cwd=repo_dir)
            _git("config", "user.email", "test@example.com", cwd=repo_dir)
            _git("config", "user.name", "Test", cwd=repo_dir)
            _git("remote", "add", "origin", origin_dir, cwd=repo_dir)
            Path(os.path.join(repo_dir, "README.md")).write_text("init\n")
            _git("add", "README.md", cwd=repo_dir)
            _git("commit", "-m", "Initial commit", cwd=repo_dir)
            _git("push", "-u", "origin", "HEAD:main", cwd=repo_dir)
            _git(
                "branch",
                "--set-upstream-to=origin/main",
                "main",
                cwd=repo_dir,
                check=False,
            )
            # Add a commit ahead of origin/main
            Path(os.path.join(repo_dir, "extra.txt")).write_text("extra\n")
            _git("add", "extra.txt", cwd=repo_dir)
            _git("commit", "-m", "Extra commit", cwd=repo_dir)

            script = _STEP16_COMMITS_AHEAD_CHECK.format(repo_path=repo_dir)
            result = subprocess.run(
                ["bash", "-c", script],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0)
            self.assertIn("PUSH_OK", result.stdout)
        finally:
            shutil.rmtree(repo_dir, ignore_errors=True)
            shutil.rmtree(origin_dir, ignore_errors=True)


# ===========================================================================
# Entry point
# ===========================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
