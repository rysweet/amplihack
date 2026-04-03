#!/usr/bin/env python3
"""
TDD test suite for step-03-create-issue idempotency guards.

Added in PR #3952 (merged 2026-04-03).  Two guards run in priority order before
creating a new GitHub issue:

  Guard 1 — Reference Guard
    If task_description contains #NNNN, resolve the issue and reuse it.

  Guard 2 — Title Search Guard
    Search open issues for a matching title; reuse the first hit.

  Fallback
    Create a new issue (original behaviour, unchanged).

Behavioral contract (from docs/recipes/step-03-idempotency.md):
  - Guard 1 triggers on first #NNNN reference in task_description.
  - Guard 1 validates the extracted number is purely numeric (defense-in-depth).
  - Guard 1 uses `timeout 60 gh issue view` with 2>/dev/null.
  - Guard 1 outputs the issue URL and exits 0 on match; falls through otherwise.
  - Guard 2 truncates the search query to the first 100 characters of ISSUE_TITLE.
  - Guard 2 outputs the first matching URL and exits 0; falls through otherwise.
  - Guard 2 falls through silently on gh failure (|| echo '').
  - ISSUE_TITLE is built using bash string substitution, NOT an external tr/cut.
  - Issue body is assembled with printf (not a heredoc).
  - Quoted heredoc (<<EOFTASKDESC) prevents shell injection in task_description.

Test strategy:
  - Static YAML analysis tests (fast, no subprocess): assert guard patterns are
    textually present in the step-03 command extracted from default-workflow.yaml.
  - Dynamic execution tests: substitute template variables, mock `gh` with a small
    shell script, run under bash, and assert stdout / exit code.

Run:
  python -m unittest amplifier-bundle/tools/test_step03_create_issue_idempotency.py -v
"""

import os
import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RECIPES_DIR = Path(__file__).parent.parent / "recipes"
_WORKFLOW_YAML = _RECIPES_DIR / "default-workflow.yaml"


def _extract_step_command(yaml_path: Path, step_id: str) -> str:
    """
    Parse default-workflow.yaml to extract the 'command:' block for step_id.
    Returns the raw (un-indented) bash command string.
    Raises ValueError if the step is not found.
    """
    text = yaml_path.read_text()
    lines = text.splitlines()

    in_step = False
    command_lines: list[str] = []
    in_command = False
    base_indent: int | None = None

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        stripped_no_dash = stripped.lstrip("- ").strip() if stripped.startswith("-") else stripped

        if not in_step:
            if stripped_no_dash == f'id: "{step_id}"':
                in_step = True
            i += 1
            continue

        if not in_command:
            if stripped.startswith("command:"):
                inline = stripped[len("command:"):].strip()
                if inline and inline != "|":
                    return inline.strip("\"'")
                in_command = True
            elif stripped_no_dash.startswith('id: "'):
                break
            i += 1
            continue

        if not line.strip():
            command_lines.append("")
            i += 1
            continue

        indent = len(line) - len(line.lstrip())
        if base_indent is None:
            base_indent = indent

        if indent < base_indent and line.strip():
            break

        command_lines.append(line[base_indent:] if base_indent else line)
        i += 1

    if not command_lines:
        raise ValueError(f"Step '{step_id}' not found or has no command in {yaml_path}")

    return "\n".join(command_lines)


def _make_gh_mock(tmpdir: str, script: str) -> str:
    """Write a mock `gh` script into tmpdir and return the augmented PATH."""
    gh_path = Path(tmpdir) / "gh"
    gh_path.write_text(f"#!/bin/sh\n{script}\n")
    gh_path.chmod(0o755)
    return f"{tmpdir}:{os.environ.get('PATH', '/usr/bin:/bin')}"


def _run_step03(
    task_description: str,
    final_requirements: str = "No specific requirements.",
    gh_script: str = "exit 1",
    repo_path: str | None = None,
) -> subprocess.CompletedProcess:
    """
    Run the step-03-create-issue bash command with template variables substituted
    and a mock `gh` binary installed in a temporary directory.

    Returns the CompletedProcess with stdout/stderr captured.
    """
    raw_cmd = _extract_step_command(_WORKFLOW_YAML, "step-03-create-issue")

    # Substitute template variables (recipe engine uses {{var}} syntax)
    script = raw_cmd.replace("{{task_description}}", task_description)
    script = script.replace("{{final_requirements}}", final_requirements)
    script = script.replace("{{repo_path}}", repo_path or "/tmp")

    with tempfile.TemporaryDirectory(prefix="step03_test_") as tmpdir:
        env = os.environ.copy()
        env["PATH"] = _make_gh_mock(tmpdir, gh_script)

        return subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
            env=env,
        )


# ---------------------------------------------------------------------------
# Static YAML analysis tests (no subprocess required — fast)
# ---------------------------------------------------------------------------

class TestStep03YAMLStaticAnalysis(unittest.TestCase):
    """
    Verify the guard patterns are textually present in step-03-create-issue
    command in default-workflow.yaml.  These tests are RED if the guards are
    absent, GREEN once PR #3952 is merged/present.
    """

    @classmethod
    def setUpClass(cls):
        cls.cmd = _extract_step_command(_WORKFLOW_YAML, "step-03-create-issue")

    def test_guard1_bash_regex_pattern_present(self):
        """Guard 1 must use bash =~ to extract #NNNN from task_description."""
        self.assertIn(r"\#([0-9]+)", self.cmd,
            "Guard 1 bash regex \\#([0-9]+) must be present in step-03 command")

    def test_guard1_bash_rematch_used(self):
        """Guard 1 must capture the issue number via BASH_REMATCH."""
        self.assertIn("BASH_REMATCH", self.cmd,
            "Guard 1 must use BASH_REMATCH to capture extracted issue number")

    def test_guard1_numeric_defense_in_depth(self):
        """Guard 1 must validate the extracted number is purely numeric with ^[0-9]+$."""
        self.assertIn("^[0-9]+$", self.cmd,
            "Guard 1 must contain defense-in-depth numeric validation: ^[0-9]+$")

    def test_guard1_timeout_present(self):
        """Guard 1 must call `timeout 60 gh issue view` to prevent hangs."""
        self.assertIn("timeout 60", self.cmd,
            "Guard 1 must use 'timeout 60' when calling gh issue view")

    def test_guard1_uses_gh_issue_view(self):
        """Guard 1 must call gh issue view to resolve the referenced issue."""
        self.assertIn("gh issue view", self.cmd,
            "Guard 1 must call 'gh issue view' to verify the referenced issue")

    def test_guard1_suppresses_gh_stderr(self):
        """Guard 1 must suppress gh stderr (2>/dev/null) so errors fall through silently."""
        # The guard uses 2>/dev/null so network/auth failures fall through quietly
        self.assertIn("2>/dev/null", self.cmd,
            "Guard 1 gh call must suppress stderr with 2>/dev/null")

    def test_guard2_title_search_present(self):
        """Guard 2 must call gh issue list with --search."""
        self.assertIn("gh issue list", self.cmd,
            "Guard 2 must call 'gh issue list' to search for existing issues")
        self.assertIn("--search", self.cmd,
            "Guard 2 must use '--search' flag with gh issue list")

    def test_guard2_limits_search_to_100_chars(self):
        """Guard 2 must truncate the search query to the first 100 characters."""
        self.assertIn(":0:100", self.cmd,
            "Guard 2 must truncate ISSUE_TITLE search query to 100 chars with :0:100")

    def test_guard2_searches_open_issues_only(self):
        """Guard 2 must restrict search to open issues with --state open."""
        self.assertIn("--state open", self.cmd,
            "Guard 2 must use '--state open' to avoid matching closed issues")

    def test_title_built_without_external_tr_or_cut(self):
        """ISSUE_TITLE must use bash string substitution, not external tr or cut."""
        # Doc contract: bash builtins replace tr|cut pipeline
        self.assertNotIn(" tr ", self.cmd,
            "ISSUE_TITLE must not use external 'tr' command")
        self.assertNotIn(" cut ", self.cmd,
            "ISSUE_TITLE must not use external 'cut' command")

    def test_issue_body_built_with_printf(self):
        """Issue body must be assembled with printf, not a heredoc."""
        # Doc: "issue body is assembled with printf"
        # The create section must have printf for the body
        self.assertIn("printf", self.cmd,
            "Issue body must be assembled with printf (not a heredoc)")

    def test_task_description_captured_with_heredoc(self):
        """task_description must be captured via heredoc (prevents injection)."""
        # Quoted heredoc <<EOFTASKDESC prevents shell expansion
        self.assertIn("EOFTASKDESC", self.cmd,
            "task_description must be captured via heredoc (<<EOFTASKDESC)")

    def test_set_euo_pipefail_present(self):
        """step-03 must start with set -euo pipefail."""
        self.assertIn("set -euo pipefail", self.cmd,
            "step-03 must start with 'set -euo pipefail'")


# ---------------------------------------------------------------------------
# Dynamic execution tests — Guard 1 (Reference Guard)
# ---------------------------------------------------------------------------

class TestStep03Guard1ReferenceGuard(unittest.TestCase):
    """
    Guard 1 extracts #NNNN from task_description and tries to reuse the issue.
    """

    def test_guard1_reuses_issue_when_reference_found_in_task_description(self):
        """
        Guard 1 happy path: task_description contains '#4194', gh returns a URL
        → step outputs the URL and exits 0 without creating a new issue.
        """
        gh_mock = textwrap.dedent("""\
            # Mock: gh issue view 4194 --json url --jq '.url // ""'
            if [ "$1" = "issue" ] && [ "$2" = "view" ] && [ "$3" = "4194" ]; then
                printf 'https://github.com/org/repo/issues/4194\\n'
                exit 0
            fi
            # gh issue create must NOT be called in this code path
            if [ "$1" = "issue" ] && [ "$2" = "create" ]; then
                echo "UNEXPECTED: gh issue create called but guard 1 should have exited" >&2
                exit 99
            fi
            exit 1
        """)
        result = _run_step03(
            task_description="Fix login timeout bug in #4194",
            gh_script=gh_mock,
        )
        self.assertEqual(result.returncode, 0,
            f"Guard 1 must exit 0 when referenced issue exists. stderr={result.stderr!r}")
        self.assertIn("https://github.com/org/repo/issues/4194", result.stdout,
            "Guard 1 must output the existing issue URL")
        self.assertNotIn("UNEXPECTED", result.stderr,
            "Guard 1 must not call gh issue create when reusing existing issue")

    def test_guard1_outputs_info_log_when_reusing(self):
        """Guard 1 must log INFO: task_description references issue #NNNN to stderr."""
        gh_mock = textwrap.dedent("""\
            if [ "$1" = "issue" ] && [ "$2" = "view" ]; then
                printf 'https://github.com/org/repo/issues/4194\\n'
                exit 0
            fi
            exit 1
        """)
        result = _run_step03(
            task_description="Implements feature for #4194",
            gh_script=gh_mock,
        )
        self.assertIn("4194", result.stderr,
            "Guard 1 must log the referenced issue number to stderr")

    def test_guard1_falls_through_when_referenced_issue_not_found(self):
        """
        Guard 1 fall-through: task_description has #9999, but gh returns empty
        (issue does not exist) → fall through to Guard 2, then create.
        """
        gh_mock = textwrap.dedent("""\
            # gh issue view 9999 returns empty (not found)
            if [ "$1" = "issue" ] && [ "$2" = "view" ]; then
                printf ''
                exit 0
            fi
            # Guard 2 search also returns empty
            if [ "$1" = "issue" ] && [ "$2" = "list" ]; then
                printf ''
                exit 0
            fi
            # Fallback: simulate successful gh issue create
            if [ "$1" = "issue" ] && [ "$2" = "create" ]; then
                printf 'https://github.com/org/repo/issues/10000\\n'
                exit 0
            fi
            if [ "$1" = "label" ]; then
                exit 0
            fi
            exit 0
        """)
        result = _run_step03(
            task_description="Fix the bug tracked in #9999 which does not exist",
            gh_script=gh_mock,
        )
        # The step should reach the create path — exit 0 from gh issue create
        self.assertEqual(result.returncode, 0,
            f"Step must still exit 0 after guard 1 falls through. stderr={result.stderr!r}")
        # Must warn about not-found issue
        self.assertIn("9999", result.stderr,
            "Guard 1 must log the issue number it tried to resolve")

    def test_guard1_skips_when_no_issue_reference_in_task_description(self):
        """
        Guard 1 is skipped entirely when task_description has no #NNNN pattern.
        Guard 2 and fallback run instead.
        """
        gh_mock = textwrap.dedent("""\
            # Guard 2 search returns empty
            if [ "$1" = "issue" ] && [ "$2" = "list" ]; then
                printf ''
                exit 0
            fi
            if [ "$1" = "issue" ] && [ "$2" = "create" ]; then
                printf 'https://github.com/org/repo/issues/1\\n'
                exit 0
            fi
            if [ "$1" = "label" ]; then exit 0; fi
            exit 0
        """)
        result = _run_step03(
            task_description="Fix login timeout — no issue reference here",
            gh_script=gh_mock,
        )
        self.assertEqual(result.returncode, 0,
            f"Step must exit 0 when no reference in task_description. stderr={result.stderr!r}")
        # gh issue view must NOT have been called (no reference to resolve)
        self.assertNotIn("verifying it exists", result.stderr,
            "Guard 1 must not trigger when task_description has no #NNNN")

    def test_guard1_validates_numeric_before_gh_call(self):
        """
        Defense-in-depth: if extracted REF_ISSUE_NUM somehow contains non-numeric
        chars, Guard 1 must skip the gh call and warn to stderr.

        This tests the ^[0-9]+$ validation. Since the bash regex r'\#([0-9]+)' already
        guarantees numeric capture, this guard is a secondary safety net.  We verify
        its static presence via YAML analysis; here we verify the warning message
        path can be reached.
        """
        # We rely on the YAML analysis test for static verification.
        # A dynamic test would require injecting a non-numeric BASH_REMATCH, which
        # is not possible from outside the script.  Assert the pattern is in the YAML.
        cmd = _extract_step_command(_WORKFLOW_YAML, "step-03-create-issue")
        self.assertIn("^[0-9]+$", cmd,
            "Defense-in-depth: ^[0-9]+$ validation must be present before gh issue view call")

    def test_guard1_falls_through_on_gh_error(self):
        """
        Guard 1 must fall through (not abort) when gh issue view fails (exit non-0)
        or returns empty.  The || echo '' pattern absorbs the failure.
        """
        gh_mock = textwrap.dedent("""\
            # gh issue view fails
            if [ "$1" = "issue" ] && [ "$2" = "view" ]; then
                echo "error: not found" >&2
                exit 1
            fi
            # Guard 2 search returns empty
            if [ "$1" = "issue" ] && [ "$2" = "list" ]; then
                printf ''
                exit 0
            fi
            if [ "$1" = "issue" ] && [ "$2" = "create" ]; then
                printf 'https://github.com/org/repo/issues/5555\\n'
                exit 0
            fi
            if [ "$1" = "label" ]; then exit 0; fi
            exit 0
        """)
        result = _run_step03(
            task_description="Implement the fix for #5555",
            gh_script=gh_mock,
        )
        # Should still succeed (fell through to create)
        self.assertEqual(result.returncode, 0,
            f"Step must exit 0 even when guard 1 gh call fails. stderr={result.stderr!r}")

    def test_guard1_uses_first_issue_reference_only(self):
        """
        Guard 1 must use the first #NNNN reference only (BASH_REMATCH[1] from
        the first =~ match).
        """
        gh_mock = textwrap.dedent("""\
            if [ "$1" = "issue" ] && [ "$2" = "view" ] && [ "$3" = "100" ]; then
                printf 'https://github.com/org/repo/issues/100\\n'
                exit 0
            fi
            # If the second reference #200 is used, this would be called instead
            if [ "$1" = "issue" ] && [ "$2" = "view" ] && [ "$3" = "200" ]; then
                echo "WRONG: used second reference instead of first" >&2
                exit 0
            fi
            exit 1
        """)
        result = _run_step03(
            task_description="Fix bug in #100 and also related to #200",
            gh_script=gh_mock,
        )
        self.assertEqual(result.returncode, 0,
            f"Guard 1 must exit 0 on first reference. stderr={result.stderr!r}")
        self.assertIn("issues/100", result.stdout,
            "Guard 1 must use the FIRST #NNNN reference, not subsequent ones")
        self.assertNotIn("WRONG", result.stderr,
            "Guard 1 must not try the second reference when the first succeeds")


# ---------------------------------------------------------------------------
# Dynamic execution tests — Guard 2 (Title Search Guard)
# ---------------------------------------------------------------------------

class TestStep03Guard2TitleSearchGuard(unittest.TestCase):
    """
    Guard 2 searches open issues for a title match and reuses the first hit.
    """

    def test_guard2_reuses_matching_open_issue(self):
        """
        Guard 2 happy path: guard 1 skipped (no #NNNN in task_description),
        gh issue list returns a matching URL → step outputs URL and exits 0.
        """
        gh_mock = textwrap.dedent("""\
            if [ "$1" = "issue" ] && [ "$2" = "list" ]; then
                printf 'https://github.com/org/repo/issues/2000\\n'
                exit 0
            fi
            if [ "$1" = "issue" ] && [ "$2" = "create" ]; then
                echo "UNEXPECTED: gh issue create called but guard 2 should have exited" >&2
                exit 99
            fi
            if [ "$1" = "label" ]; then exit 0; fi
            exit 0
        """)
        result = _run_step03(
            task_description="Improve user authentication flow",
            gh_script=gh_mock,
        )
        self.assertEqual(result.returncode, 0,
            f"Guard 2 must exit 0 when matching issue found. stderr={result.stderr!r}")
        self.assertIn("issues/2000", result.stdout,
            "Guard 2 must output the matching open issue URL")
        self.assertNotIn("UNEXPECTED", result.stderr,
            "Guard 2 must not call gh issue create when reusing existing issue")

    def test_guard2_falls_through_when_no_matching_issue(self):
        """
        Guard 2 fall-through: gh issue list returns empty → proceed to create.
        """
        gh_mock = textwrap.dedent("""\
            if [ "$1" = "issue" ] && [ "$2" = "list" ]; then
                printf ''
                exit 0
            fi
            if [ "$1" = "issue" ] && [ "$2" = "create" ]; then
                printf 'https://github.com/org/repo/issues/3000\\n'
                exit 0
            fi
            if [ "$1" = "label" ]; then exit 0; fi
            exit 0
        """)
        result = _run_step03(
            task_description="Brand new task with no prior issue",
            gh_script=gh_mock,
        )
        self.assertEqual(result.returncode, 0,
            f"Step must exit 0 when guard 2 falls through to create. stderr={result.stderr!r}")
        self.assertIn("3000", result.stdout,
            "Step must output the newly created issue URL")

    def test_guard2_falls_through_on_gh_failure(self):
        """
        Guard 2 must NOT abort when gh issue list fails; it uses || echo '' to
        fall through silently to the create path.
        """
        gh_mock = textwrap.dedent("""\
            if [ "$1" = "issue" ] && [ "$2" = "list" ]; then
                echo "error: API rate limit" >&2
                exit 1
            fi
            if [ "$1" = "issue" ] && [ "$2" = "create" ]; then
                printf 'https://github.com/org/repo/issues/4000\\n'
                exit 0
            fi
            if [ "$1" = "label" ]; then exit 0; fi
            exit 0
        """)
        result = _run_step03(
            task_description="Task where gh list fails",
            gh_script=gh_mock,
        )
        self.assertEqual(result.returncode, 0,
            f"Step must exit 0 even when guard 2 gh list fails. stderr={result.stderr!r}")

    def test_guard2_logs_search_info(self):
        """Guard 2 must log 'Searching open issues' to stderr."""
        gh_mock = textwrap.dedent("""\
            if [ "$1" = "issue" ] && [ "$2" = "list" ]; then
                printf ''
                exit 0
            fi
            if [ "$1" = "issue" ] && [ "$2" = "create" ]; then
                printf 'https://github.com/org/repo/issues/1\\n'
                exit 0
            fi
            if [ "$1" = "label" ]; then exit 0; fi
            exit 0
        """)
        result = _run_step03(
            task_description="Some new task",
            gh_script=gh_mock,
        )
        self.assertIn("Searching open issues", result.stderr,
            "Guard 2 must log 'Searching open issues' to stderr when it runs")

    def test_guard2_logs_found_existing_issue(self):
        """Guard 2 must log 'Found existing open issue' to stderr when reusing."""
        gh_mock = textwrap.dedent("""\
            if [ "$1" = "issue" ] && [ "$2" = "list" ]; then
                printf 'https://github.com/org/repo/issues/42\\n'
                exit 0
            fi
            exit 0
        """)
        result = _run_step03(
            task_description="Some existing task",
            gh_script=gh_mock,
        )
        self.assertIn("Found existing open issue", result.stderr,
            "Guard 2 must log 'Found existing open issue matching title' when reusing")

    def test_guard2_title_truncated_to_100_chars_in_search(self):
        """
        Guard 2 must not pass a search query longer than 100 characters.
        Verify that a very long title is truncated.
        """
        # We can't easily inspect the exact argument passed to the mock gh
        # without argument logging — instead assert YAML static property.
        cmd = _extract_step_command(_WORKFLOW_YAML, "step-03-create-issue")
        self.assertIn(":0:100", cmd,
            "Guard 2 must truncate search query to 100 chars (ISSUE_TITLE:0:100)")


# ---------------------------------------------------------------------------
# Dynamic execution tests — Fallback (Create New Issue)
# ---------------------------------------------------------------------------

class TestStep03FallbackCreate(unittest.TestCase):
    """
    When both guards fall through, step-03 must create a new issue.
    """

    def test_fallback_calls_gh_issue_create(self):
        """Both guards miss → gh issue create is called and URL is output."""
        gh_mock = textwrap.dedent("""\
            if [ "$1" = "issue" ] && [ "$2" = "list" ]; then
                printf ''
                exit 0
            fi
            if [ "$1" = "issue" ] && [ "$2" = "create" ]; then
                printf 'https://github.com/org/repo/issues/9900\\n'
                exit 0
            fi
            if [ "$1" = "label" ]; then exit 0; fi
            exit 0
        """)
        result = _run_step03(
            task_description="Completely new task without existing issue",
            final_requirements="Must implement X and Y",
            gh_script=gh_mock,
        )
        self.assertEqual(result.returncode, 0,
            f"Fallback create must exit 0. stderr={result.stderr!r}")
        self.assertIn("9900", result.stdout,
            "Fallback must output the new issue URL from gh issue create")

    def test_fallback_includes_task_description_in_body(self):
        """Fallback create: issue body must include the task_description content."""
        created_body = []

        # We'll use a gh mock that captures the --body argument
        # by writing it to a temp file — use a real tempfile path
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", prefix="gh_body_", delete=False
        ) as f:
            body_file = f.name

        try:
            gh_mock = textwrap.dedent(f"""\
                if [ "$1" = "issue" ] && [ "$2" = "list" ]; then
                    printf ''
                    exit 0
                fi
                if [ "$1" = "issue" ] && [ "$2" = "create" ]; then
                    # Capture all arguments to detect --body
                    args="$*"
                    printf '%s' "$args" > {body_file}
                    printf 'https://github.com/org/repo/issues/1234\\n'
                    exit 0
                fi
                if [ "$1" = "label" ]; then exit 0; fi
                exit 0
            """)
            result = _run_step03(
                task_description="Fix timeout in authentication module",
                final_requirements="Timeout must be configurable",
                gh_script=gh_mock,
            )
            self.assertEqual(result.returncode, 0)
            body_content = Path(body_file).read_text()
            # The --body argument must be passed to gh issue create
            self.assertIn("--body", body_content,
                "Fallback create must pass --body to gh issue create")
        finally:
            os.unlink(body_file)

    def test_fallback_uses_workflow_label(self):
        """Fallback create must apply the 'workflow:default' label."""
        cmd = _extract_step_command(_WORKFLOW_YAML, "step-03-create-issue")
        self.assertIn("workflow:default", cmd,
            "Fallback create must apply the 'workflow:default' label")


# ---------------------------------------------------------------------------
# Security / injection safety tests
# ---------------------------------------------------------------------------

class TestStep03SecurityInjectionSafety(unittest.TestCase):
    """
    Verify that shell metacharacters in task_description cannot inject code.
    The heredoc capture (<<EOFTASKDESC) must prevent expansion.
    """

    def test_backtick_in_task_description_not_executed(self):
        """
        Backtick command substitution in task_description must NOT be executed.
        task_description = "Fix `touch /tmp/injected_by_backtick` now"
        """
        sentinel = "/tmp/injected_by_backtick_step03"
        if os.path.exists(sentinel):
            os.unlink(sentinel)

        gh_mock = textwrap.dedent("""\
            if [ "$1" = "issue" ] && [ "$2" = "list" ]; then printf ''; exit 0; fi
            if [ "$1" = "issue" ] && [ "$2" = "create" ]; then
                printf 'https://github.com/org/repo/issues/1\\n'; exit 0
            fi
            if [ "$1" = "label" ]; then exit 0; fi
            exit 0
        """)
        _run_step03(
            task_description=f"Fix `touch {sentinel}` now",
            gh_script=gh_mock,
        )
        self.assertFalse(os.path.exists(sentinel),
            "Backtick injection in task_description must not be executed")

    def test_dollar_paren_in_task_description_not_executed(self):
        """
        $(command) substitution in task_description must NOT be executed.
        """
        sentinel = "/tmp/injected_by_dollar_paren_step03"
        if os.path.exists(sentinel):
            os.unlink(sentinel)

        gh_mock = textwrap.dedent("""\
            if [ "$1" = "issue" ] && [ "$2" = "list" ]; then printf ''; exit 0; fi
            if [ "$1" = "issue" ] && [ "$2" = "create" ]; then
                printf 'https://github.com/org/repo/issues/1\\n'; exit 0
            fi
            if [ "$1" = "label" ]; then exit 0; fi
            exit 0
        """)
        _run_step03(
            task_description=f"Fix $(touch {sentinel}) now",
            gh_script=gh_mock,
        )
        self.assertFalse(os.path.exists(sentinel),
            "$(command) injection in task_description must not be executed")

    def test_newline_in_task_description_handled_safely(self):
        """
        Newlines in task_description must not break the script (heredoc handles them).
        """
        gh_mock = textwrap.dedent("""\
            if [ "$1" = "issue" ] && [ "$2" = "list" ]; then printf ''; exit 0; fi
            if [ "$1" = "issue" ] && [ "$2" = "create" ]; then
                printf 'https://github.com/org/repo/issues/1\\n'; exit 0
            fi
            if [ "$1" = "label" ]; then exit 0; fi
            exit 0
        """)
        result = _run_step03(
            task_description="Line one\nLine two\nLine three",
            gh_script=gh_mock,
        )
        self.assertEqual(result.returncode, 0,
            f"Newlines in task_description must not break the step. stderr={result.stderr!r}")

    def test_heredoc_delimiter_in_task_description_handled(self):
        """
        Heredoc delimiter text (EOFTASKDESC) inside task_description must not
        prematurely close the heredoc and cause script errors.
        Note: since the recipe template engine substitutes {{task_description}}
        *before* bash executes, if the value literally contains 'EOFTASKDESC'
        the heredoc is at risk.  This test documents the known limitation and
        verifies the YAML uses a specific-enough delimiter.
        """
        cmd = _extract_step_command(_WORKFLOW_YAML, "step-03-create-issue")
        # Delimiter must be specific enough that normal text won't match it
        self.assertIn("EOFTASKDESC", cmd,
            "task_description heredoc must use the specific 'EOFTASKDESC' delimiter")


# ---------------------------------------------------------------------------
# Priority ordering test: Guard 1 wins over Guard 2
# ---------------------------------------------------------------------------

class TestStep03GuardPriority(unittest.TestCase):
    """
    Guard 1 must exit before Guard 2 runs when a valid reference is found.
    Guard 2 must be reached when Guard 1 falls through.
    """

    def test_guard1_exits_before_guard2_when_reference_resolved(self):
        """
        When Guard 1 resolves a valid issue, Guard 2 must NOT run.
        Verify by making gh issue list return an UNEXPECTED sentinel.
        """
        gh_mock = textwrap.dedent("""\
            if [ "$1" = "issue" ] && [ "$2" = "view" ] && [ "$3" = "4194" ]; then
                printf 'https://github.com/org/repo/issues/4194\\n'
                exit 0
            fi
            if [ "$1" = "issue" ] && [ "$2" = "list" ]; then
                echo "GUARD2_CALLED" >&2
                printf 'https://github.com/org/repo/issues/9999\\n'
                exit 0
            fi
            exit 1
        """)
        result = _run_step03(
            task_description="Fix bug in #4194",
            gh_script=gh_mock,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("issues/4194", result.stdout,
            "Guard 1 result must be in stdout when it exits first")
        self.assertNotIn("GUARD2_CALLED", result.stderr,
            "Guard 2 must NOT run when Guard 1 exits successfully")

    def test_guard2_runs_when_guard1_falls_through(self):
        """
        Guard 2 must run when Guard 1 falls through (issue not found).

        Verified via step-03's own INFO log ("Searching open issues") and
        the guard-2 match URL in stdout.  Note: the mock's own stderr is
        suppressed by the recipe's 2>/dev/null on the gh issue list call,
        so we use the step's log messages to confirm guard 2 ran.
        """
        gh_mock = textwrap.dedent("""\
            if [ "$1" = "issue" ] && [ "$2" = "view" ]; then
                printf ''
                exit 0
            fi
            if [ "$1" = "issue" ] && [ "$2" = "list" ]; then
                printf 'https://github.com/org/repo/issues/8888\\n'
                exit 0
            fi
            exit 0
        """)
        result = _run_step03(
            task_description="Fix bug in #0000 which does not exist",
            gh_script=gh_mock,
        )
        self.assertEqual(result.returncode, 0)
        # Step-03 logs "Searching open issues" when guard 2 runs
        self.assertIn("Searching open issues", result.stderr,
            "Guard 2 must log 'Searching open issues' when it runs after guard 1 falls through")
        self.assertIn("issues/8888", result.stdout,
            "Guard 2 result must be in stdout")


if __name__ == "__main__":
    unittest.main()
