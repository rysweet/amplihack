"""Regression tests for step-03-create-issue shell-quoting safety (issue #4206).

Verifies:
1. SEARCH_TITLE single-quote escaping uses exactly 2-char replacement ('' not ''')
   — correct SQL-safe escaping for the ADO WIQL query.
2. The pattern is ``${var//\'/\'\'}`` (2 replacement chars), not the buggy
   ``${var//\'/\'\''}`` (3 replacement chars) that caused #4206.
3. ISSUE_TITLE newline/carriage-return normalisation uses bash builtins
   (``$'\\n'``/``$'\\r'`` parameter expansion) rather than spawning tr/cut.
4. TASK_DESC and ISSUE_REQS are captured via single-quoted heredoc to prevent
   shell-metacharacter injection (CWE-78).
5. The SEARCH_TITLE replacement, when executed in bash, converts a string with
   single quotes to the SQL-safe doubled-single-quote form.
6. ISSUE_TITLE is truncated to 200 chars via ``${var:0:200}``.
7. SEARCH_TITLE is truncated to 100 chars via ``${var:0:100}``.
8. Idempotency Guard 1 (task_description reference extraction) uses a POSIX
   case statement for numeric validation before interpolation into gh/az commands.
9. The ADO WIQL query embeds SEARCH_TITLE inside single quotes — the 2-char
   replacement keeps that string syntactically valid even when the title contains
   single quotes.
10. The GitHub path uses ``--search "$SEARCH_QUERY"`` (double-quoted) without
    additional escaping, as gh CLI handles it safely.
11. SEARCH_QUERY (GitHub path) does NOT apply the SQL single-quote escaping —
    gh CLI accepts raw title text and its own quoting rules differ from WIQL.
12. The SEARCH_TITLE replacement expression is exactly the 2-char form at the
    byte level: ``${SEARCH_TITLE//\\'\\'/\\'\\'}`` — validated by direct string
    containment, not just regex absence.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml

RECIPE_PATH = Path("amplifier-bundle/recipes/default-workflow.yaml")
STEP_ID = "step-03-create-issue"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_step_command() -> str:
    with RECIPE_PATH.open() as f:
        recipe = yaml.safe_load(f)
    for step in recipe.get("steps", []):
        if step.get("id") == STEP_ID:
            return step.get("command", "")
    pytest.fail(f"Step '{STEP_ID}' not found in {RECIPE_PATH}")


@pytest.fixture(scope="module")
def step_command() -> str:
    return _load_step_command()


# ---------------------------------------------------------------------------
# Test 1-2: SEARCH_TITLE 2-char replacement (the bug from #4206)
# ---------------------------------------------------------------------------


class TestSearchTitleQuoting:
    def test_search_title_replacement_is_2char(self, step_command: str) -> None:
        """The SEARCH_TITLE single-quote replacement must produce '' (2 chars), not ''' (3)."""
        # Look for the SEARCH_TITLE parameter expansion pattern
        # Correct:  ${SEARCH_TITLE//\'/\'\'}
        # Buggy:    ${SEARCH_TITLE//\'/\'\''}   (extra trailing quote)
        match = re.search(r"SEARCH_TITLE=\"\$\{SEARCH_TITLE//([^}]+)\}\"", step_command)
        assert match, "SEARCH_TITLE replacement pattern not found in step-03 command"
        full_expr = match.group(0)
        assert "SEARCH_TITLE//\\'/" in full_expr or r"SEARCH_TITLE//\'" in full_expr, (
            f"Expected single-quote escape pattern, got: {full_expr!r}"
        )
        # The buggy 3-char pattern always has \'\'' (backslash-quote-backslash-quote-quote)
        assert r"\'\''" not in full_expr, (
            f"Buggy 3-char replacement detected in: {full_expr!r}\n"
            "This causes triple-quote output (''') instead of double-quote ('').\n"
            "Fix: use ${{SEARCH_TITLE//\\'/\\'\\'}}"
        )

    def test_search_title_bash_2char_produces_sql_safe_output(self) -> None:
        """Bash execution: single quotes are doubled to '' (SQL-safe), not tripled to '''."""
        script = r"""
set -eu
SEARCH_TITLE="Ryan's test with O'Brien"
SEARCH_TITLE="${SEARCH_TITLE//\'/\'\'}"
printf '%s\n' "$SEARCH_TITLE"
"""
        result = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, f"bash error: {result.stderr}"
        assert result.stdout.strip() == "Ryan''s test with O''Brien", (
            f"Expected SQL-safe doubled quotes, got: {result.stdout.strip()!r}"
        )

    def test_search_title_no_triple_quote_in_bash(self) -> None:
        """Confirm the buggy 3-char pattern produces the wrong output."""
        script = r"""
set -eu
SEARCH_TITLE="it's a test"
# Buggy 3-char replacement (what issue #4206 was about)
RESULT_BUGGY="${SEARCH_TITLE//\'/\'\'\'}"
# Correct 2-char replacement
RESULT_FIXED="${SEARCH_TITLE//\'/\'\'}"
echo "buggy:$RESULT_BUGGY"
echo "fixed:$RESULT_FIXED"
"""
        result = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0
        lines = dict(line.split(":", 1) for line in result.stdout.strip().splitlines())
        assert lines["buggy"] == "it'''s a test", "sanity: buggy pattern should produce '''"
        assert lines["fixed"] == "it''s a test", "fixed pattern must produce SQL-safe ''"


# ---------------------------------------------------------------------------
# Test 3: Newline normalisation uses bash builtins
# ---------------------------------------------------------------------------


class TestIssueTitle:
    def test_issue_title_newline_normalisation_uses_builtins(self, step_command: str) -> None:
        """ISSUE_TITLE normalisation must use $'\\n'/$'\\r' builtins, not tr/cut subprocesses."""
        # Look for the normalisation pattern
        assert "$'\\n'" in step_command or r"$'\n'" in step_command, (
            "ISSUE_TITLE newline normalisation must use bash $'\\n' builtin, not tr subprocess"
        )
        assert "$'\\r'" in step_command or r"$'\r'" in step_command, (
            "ISSUE_TITLE carriage-return normalisation must use bash $'\\r' builtin"
        )
        # Must NOT use tr subprocess for this
        # (tr is only prohibited inside the title normalisation block itself)
        title_block_match = re.search(
            r'ISSUE_TITLE="\$\{TASK_DESC.*?\}".*?ISSUE_TITLE="\$\{ISSUE_TITLE.*?\}".*?'
            r'ISSUE_TITLE="\$\{ISSUE_TITLE:0:200\}"',
            step_command,
            re.DOTALL,
        )
        assert title_block_match, (
            "Expected three-step ISSUE_TITLE normalisation block "
            "(newline replace, carriage-return replace, truncate to 200)"
        )

    def test_issue_title_truncated_to_200(self, step_command: str) -> None:
        """ISSUE_TITLE must be truncated to 200 characters."""
        assert 'ISSUE_TITLE="${ISSUE_TITLE:0:200}"' in step_command, (
            "ISSUE_TITLE truncation to 200 chars not found"
        )

    def test_search_title_truncated_to_100(self, step_command: str) -> None:
        """SEARCH_TITLE must be truncated to 100 characters before escaping."""
        assert 'SEARCH_TITLE="${ISSUE_TITLE:0:100}"' in step_command, (
            "SEARCH_TITLE truncation to 100 chars not found"
        )

    def test_issue_title_newline_bash_execution(self) -> None:
        """Bash execution: multiline task_description becomes a single-line title."""
        script = r"""
set -eu
TASK_DESC="first line
second line
third line"
ISSUE_TITLE="${TASK_DESC//$'\n'/ }"
ISSUE_TITLE="${ISSUE_TITLE//$'\r'/ }"
ISSUE_TITLE="${ISSUE_TITLE:0:200}"
printf '%s\n' "$ISSUE_TITLE"
"""
        result = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, f"bash error: {result.stderr}"
        assert result.stdout.strip() == "first line second line third line"


# ---------------------------------------------------------------------------
# Test 4: Heredoc capture prevents injection
# ---------------------------------------------------------------------------


class TestHeredocCapture:
    def test_task_desc_uses_single_quoted_heredoc(self, step_command: str) -> None:
        """TASK_DESC must be captured via <<'EOFTASKDESC' (quoted heredoc) for injection safety."""
        assert "<<'EOFTASKDESC'" in step_command, (
            "TASK_DESC must use single-quoted heredoc <<'EOFTASKDESC' "
            "to prevent shell metacharacter injection (CWE-78)"
        )

    def test_issue_reqs_uses_single_quoted_heredoc(self, step_command: str) -> None:
        """ISSUE_REQS must be captured via <<'EOFREQS' (quoted heredoc)."""
        assert "<<'EOFREQS'" in step_command, (
            "ISSUE_REQS must use single-quoted heredoc <<'EOFREQS'"
        )

    def test_heredoc_prevents_backtick_injection(self) -> None:
        """Quoted heredoc must not expand backtick/subshell metacharacters."""
        script = r"""
set -eu
TASK_DESC=$(cat <<'EOFTASKDESC'
$(touch /tmp/injected_4206_test)
`touch /tmp/injected_4206_backtick`
EOFTASKDESC
)
# Verify the dangerous strings are captured literally, not executed
printf '%s\n' "$TASK_DESC"
"""
        result = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, f"bash error: {result.stderr}"
        assert "$(touch" in result.stdout, "Subshell syntax should appear literally"
        assert "`touch" in result.stdout, "Backtick syntax should appear literally"
        import os

        assert not os.path.exists("/tmp/injected_4206_test"), (
            "Shell injection executed! /tmp/injected_4206_test was created."
        )
        assert not os.path.exists("/tmp/injected_4206_backtick"), (
            "Backtick injection executed! /tmp/injected_4206_backtick was created."
        )


# ---------------------------------------------------------------------------
# Test 5: Idempotency guard numeric validation
# ---------------------------------------------------------------------------


class TestIdempotencyGuard:
    def test_ref_issue_num_uses_case_validation(self, step_command: str) -> None:
        """REF_ISSUE_NUM / REF_ITEM_NUM must use POSIX case for numeric validation."""
        assert "''|*[!0-9]*)" in step_command, (
            "Numeric validation for REF_ISSUE_NUM/REF_ITEM_NUM must use "
            "POSIX case: ''|*[!0-9]*) REF_ISSUE_NUM=\"\""
        )

    def test_numeric_validation_bash(self) -> None:
        """Case-statement numeric validation: only pure digits pass."""
        script = r"""
set -eu
check_numeric() {
  local val="$1"
  case "$val" in
    ''|*[!0-9]*) echo "invalid" ;;
    *) echo "valid" ;;
  esac
}
check_numeric "1234"
check_numeric "0"
check_numeric ""
check_numeric "12a4"
check_numeric "12;rm -rf /"
"""
        result = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0
        lines = result.stdout.strip().splitlines()
        # 1234 → valid, 0 → valid, "" → invalid, 12a4 → invalid, "12;rm..." → invalid
        assert lines == ["valid", "valid", "invalid", "invalid", "invalid"], (
            f"Unexpected validation results: {lines}"
        )


# ---------------------------------------------------------------------------
# Test 6: ADO WIQL SQL-safety end-to-end
# ---------------------------------------------------------------------------


class TestAdoWiqlSafety:
    def test_wiql_query_with_escaped_title_is_valid_bash(self) -> None:
        """ADO WIQL query with SQL-escaped title must not cause bash syntax error."""
        script = r"""
set -eu
ISSUE_TITLE="Ryan's O'Brien: it's a test"
SEARCH_TITLE="${ISSUE_TITLE:0:100}"
SEARCH_TITLE="${SEARCH_TITLE//\'/\'\'}"
# Construct the WIQL query (do not actually run az)
WIQL="SELECT [System.Id] FROM WorkItems WHERE [System.Title] = '$SEARCH_TITLE' AND [System.State] <> 'Closed'"
printf '%s\n' "$WIQL"
"""
        result = subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=10)
        assert result.returncode == 0, f"bash error: {result.stderr}"
        output = result.stdout.strip()
        # Verify the title is SQL-safe doubled quotes
        assert "Ryan''s O''Brien: it''s a test" in output, (
            f"Expected SQL-safe doubled quotes in WIQL, got: {output!r}"
        )
        # Verify the query structure is intact
        assert output.startswith("SELECT [System.Id]"), (
            f"WIQL query structure corrupted: {output!r}"
        )


# ---------------------------------------------------------------------------
# Test 7: GitHub path uses double-quoted --search (point 10 in docstring)
# ---------------------------------------------------------------------------


class TestGitHubSearchPath:
    def test_github_search_uses_double_quoted_arg(self, step_command: str) -> None:
        """GitHub path must use double-quoted --search "$SEARCH_QUERY", not single-quoted."""
        assert '--search "$SEARCH_QUERY"' in step_command, (
            'GitHub path must use double-quoted --search "$SEARCH_QUERY" — '
            "gh CLI handles shell-special chars in the search string safely. "
            "Single-quoting would prevent variable expansion."
        )

    def test_search_query_has_no_sql_escaping(self, step_command: str) -> None:
        """SEARCH_QUERY (GitHub path) must NOT apply the SQL single-quote escaping.

        gh CLI does not require ADO-style SQL escaping; the raw title is correct.
        Applying ``//\\'/'\\''\\''`` to SEARCH_QUERY would corrupt the query.
        """
        # Find SEARCH_QUERY assignment block in the command
        # It should set SEARCH_QUERY from ISSUE_TITLE truncation only, no quote replacement
        lines = step_command.splitlines()
        search_query_lines = [
            line for line in lines if "SEARCH_QUERY" in line and "SEARCH_TITLE" not in line
        ]
        # Verify none of the SEARCH_QUERY lines apply the SQL-escaping pattern
        for line in search_query_lines:
            assert "//\\'/\\'\\'\"" not in line and r"//\'/\'\'" not in line, (
                f"SEARCH_QUERY must not apply SQL single-quote escaping.\n"
                f"Offending line: {line!r}\n"
                "GitHub's --search uses a different query language — raw text is correct."
            )

    def test_github_path_search_query_set_from_issue_title(self, step_command: str) -> None:
        """SEARCH_QUERY must be derived from ISSUE_TITLE with truncation only."""
        assert 'SEARCH_QUERY="${ISSUE_TITLE:0:100}"' in step_command, (
            'SEARCH_QUERY must be set as SEARCH_QUERY="${ISSUE_TITLE:0:100}" '
            "(truncated to 100 chars, no SQL escaping)"
        )


# ---------------------------------------------------------------------------
# Test 8: Exact byte-level check for SEARCH_TITLE replacement (point 12)
# ---------------------------------------------------------------------------


class TestSearchTitleExactPattern:
    def test_search_title_replacement_exact_2char_literal(self, step_command: str) -> None:
        r"""The SEARCH_TITLE line must contain the exact 2-char replacement literal.

        The correct bash parameter expansion is:
            SEARCH_TITLE="${SEARCH_TITLE//\'/\'\'}"

        Byte-level: the replacement part is backslash-quote backslash-quote
        (2 output chars: two single-quotes '' in the result).
        The buggy 3-char form would be: backslash-quote backslash-quote backslash-quote
        which produces ''' (three single-quotes) in the result.
        """
        # The exact literal that MUST appear in the command
        correct_literal_notrim = r"""SEARCH_TITLE="${SEARCH_TITLE//\'/\'\'}" """.strip()
        assert correct_literal_notrim in step_command, (
            f"Exact 2-char replacement literal not found.\n"
            f"Expected to find: {correct_literal_notrim!r}\n"
            "This is the canonical fix for issue #4206. "
            "The buggy form was: SEARCH_TITLE=\"${SEARCH_TITLE//\\'/\\'\\''}\""
        )

    def test_search_title_replacement_absent_3char_literal(self, step_command: str) -> None:
        r"""The 3-char buggy replacement literal must NOT appear anywhere.

        The buggy form ``${SEARCH_TITLE//\'/\'\'\'}`` is the root cause of #4206.
        It produces ''' (three quotes) instead of '' (two quotes).
        """
        # Three consecutive escaped-quote patterns in the replacement position
        buggy_literal = r"${SEARCH_TITLE//\'/\'\'\'}"
        assert buggy_literal not in step_command, (
            f"Buggy 3-char replacement found: {buggy_literal!r}\n"
            "This is the root cause of issue #4206. "
            r"Fix: change \'\'\' → \'\' (remove the trailing backslash-quote)"
        )
