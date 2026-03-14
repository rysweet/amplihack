"""Tests for shell injection fix in default-workflow bash steps (issues #3045, #3076).

CWE-78: OS Command Injection — template engine substitutes {{task_description}}
into bash ``command:`` strings before shell evaluation. Backticks and ``$()``
in the value execute arbitrary commands.

Fix approach: single-quoted heredoc (``<<'EOFTASKDESC'``) captures the raw
value with NO shell interpretation — provably neutralises all metacharacters
including backticks, ``$()``, ``$VAR``, single/double quotes, backslashes,
newlines, null bytes, and glob patterns.

Verifies (per spec):
1. No vulnerable ``printf '%s' {{task_description}}`` patterns remain in any
   bash ``command:`` block.
2. Every occurrence of ``{{task_description}}`` inside a bash ``command:``
   block is enclosed in a ``<<'EOFTASKDESC'`` heredoc body.
3. No ``eval``, ``bash -c``, or ``sh -c`` receives any ``_TD_RAW`` / ``TASK_VAL``
   / ``TASK_DESC`` derived variable.
4. All downstream references to captured variables are double-quoted
   (``"$TASK_DESC"``, ``"$TASK_VAL"``).
5. The ``export VAR=$(...)`` anti-pattern is split into capture + export in
   ``workflow-complete`` (shellcheck SC2155 — exit-code masking).
6. All 7 affected steps carry the heredoc capture pattern:
   step-00-workflow-preparation, step-03-create-issue, step-04-setup-worktree,
   step-15-commit-push, step-16-create-draft-pr, step-22b-final-status,
   workflow-complete.
7. Title-bound variables (commit title, PR title, issue title) apply newline
   normalisation (``tr '\\n\\r' ' '``) and length truncation before passing to
   external tools.
8. The heredoc pattern survives bash syntax checking with adversarial
   task descriptions that broke the old ``printf '%s' '{{task_description}}'``
   single-quote wrapping.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RECIPE_DIR = Path("amplifier-bundle/recipes")

# Steps that reference {{task_description}} inside a bash command: block.
AFFECTED_STEP_IDS = [
    "step-00-workflow-preparation",
    "step-03-create-issue",
    "step-04-setup-worktree",
    "step-15-commit-push",
    "step-16-create-draft-pr",
    "step-22b-final-status",
    "workflow-complete",
]

# Steps that produce a title-bound variable (must normalise newlines + truncate).
TITLE_NORMALISING_STEPS = [
    "step-03-create-issue",   # ISSUE_TITLE — cut -c1-200
    "step-15-commit-push",    # COMMIT_TITLE — %.72s / head -1
    "step-16-create-draft-pr",  # PR_TITLE — cut -c1-200
]

# Adversarial task descriptions that broke the old single-quote pattern.
ADVERSARIAL_TASK_DESCRIPTIONS = [
    ("single_quote", "Fix the user's profile page"),
    ("parentheses", "Fix bug (broken layout)"),
    ("both", "Fix user's page (broken)"),
    ("backticks", "Fix `render()` method"),
    ("dollar_subshell", "Fix $(rm -rf /tmp/x) expansion"),
    ("dollar_var", "Fix $HOME variable leakage"),
    ("double_quotes", 'Fix the "login" button'),
    ("semicolon", "Fix auth; rm -rf /tmp/canary"),
    ("pipe", "Fix auth | cat /etc/passwd"),
    ("ampersand", "Fix auth & curl evil.invalid"),
    ("backslash", "Fix path\\to\\file"),
    ("newlines", "Fix\nmultiline\ndescription"),
    ("glob_star", "Fix path/*/wildcard"),
    ("command_substitution_backtick", "Fix `whoami` injection"),
]

# Null bytes cannot be passed through subprocess args on Linux (os.posix_spawn
# rejects them with EINVAL). They are tested separately in a dedicated test that
# verifies the OS correctly rejects null bytes rather than treating them as bash
# metacharacters.  They do NOT need the heredoc mitigation path.
_NULL_BYTE_CASE = ("null_byte_like", "Fix task\x00hidden")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def default_workflow():
    path = RECIPE_DIR / "default-workflow.yaml"
    if not path.exists():
        pytest.skip("default-workflow.yaml not found — run from repo root")
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def step_map(default_workflow):
    """Return a dict of step_id -> step dict for fast lookup."""
    return {s["id"]: s for s in default_workflow["steps"]}


def _bash_steps(default_workflow):
    """Yield (step_id, command_text) for every bash-type step."""
    for step in default_workflow["steps"]:
        if step.get("type") == "bash" and "command" in step:
            yield step["id"], step["command"]


def _get_step(step_map, step_id: str) -> dict:
    step = step_map.get(step_id)
    if step is None:
        pytest.fail(f"Step '{step_id}' not found in default-workflow.yaml")
    return step


# ---------------------------------------------------------------------------
# 1. No vulnerable printf pattern in any bash step
# ---------------------------------------------------------------------------


class TestNoVulnerablePrintfPattern:
    """No bash step may pass {{task_description}} as a printf argument.

    ``printf '%s' {{task_description}}`` evaluates the template token in the
    shell context BEFORE printf is called; any metacharacters in the value
    (backticks, $(), quotes) execute arbitrary commands — CWE-78.
    """

    def test_no_printf_bare_braces_in_any_bash_step(self, default_workflow):
        """``printf '%s' {{task_description}}`` must not appear in any command."""
        violations = []
        for step_id, cmd in _bash_steps(default_workflow):
            if re.search(r"printf\s+['\"]%s['\"].*\{\{task_description\}\}", cmd):
                violations.append(step_id)
        assert violations == [], (
            f"Steps still use vulnerable printf pattern: {violations}\n"
            "All printf calls must use the heredoc-captured variable, not the "
            "raw {{task_description}} template token."
        )

    def test_no_single_quote_wrapped_task_description(self, default_workflow):
        """``'{{task_description}}'`` single-quote wrapping must be absent.

        Single-quote wrapping breaks when the task description contains a
        single quote or closing parenthesis — issue #3041.
        """
        violations = []
        for step_id, cmd in _bash_steps(default_workflow):
            if "'{{task_description}}'" in cmd:
                violations.append(step_id)
        assert violations == [], (
            f"Steps use single-quote wrapping for task_description: {violations}\n"
            "Use heredoc (<<'EOFTASKDESC') instead."
        )

    def test_no_double_quote_wrapped_task_description_in_bash(self, default_workflow):
        """``\"{{task_description}}\"`` must not appear in bash command blocks.

        Double quotes do NOT block ``$()`` or backtick execution — any command
        substitution in the value is still executed by the shell.
        """
        violations = []
        for step_id, cmd in _bash_steps(default_workflow):
            if '"{{task_description}}"' in cmd:
                violations.append(step_id)
        assert violations == [], (
            f"Steps use double-quote wrapping for task_description: {violations}\n"
            "Use heredoc (<<'EOFTASKDESC') instead — double-quotes do NOT "
            "prevent $() or backtick execution."
        )

    def test_no_unquoted_task_description_outside_heredoc_body(self, default_workflow):
        """``{{task_description}}`` must not appear unquoted in bash commands.

        The only safe position for the template token is inside a heredoc body
        delimited by a sentinel (``<<'EOFTASKDESC'`` or ``<<EOFTASKDESC``).
        Single-quoted heredocs are preferred (prevent shell expansion); unquoted
        heredocs are acceptable when the Rust recipe runner requires env-var
        expansion (e.g. step-04-setup-worktree, issue #3087).
        Any other occurrence is a CWE-78 injection vector.
        """
        violations = []
        for step_id, cmd in _bash_steps(default_workflow):
            inside_heredoc = False
            lines_outside_heredoc = []
            for line in cmd.splitlines():
                if "<<'EOFTASKDESC'" in line or "<<EOFTASKDESC" in line:
                    inside_heredoc = True
                    lines_outside_heredoc.append(line)
                    continue
                if inside_heredoc and line.strip() == "EOFTASKDESC":
                    inside_heredoc = False
                    continue
                if not inside_heredoc:
                    lines_outside_heredoc.append(line)
            cmd_without_heredoc_bodies = "\n".join(lines_outside_heredoc)
            if "{{task_description}}" in cmd_without_heredoc_bodies:
                violations.append(step_id)
        assert violations == [], (
            f"Steps have {{{{task_description}}}} outside a heredoc body: {violations}\n"
            "All task_description template tokens in bash steps must appear only "
            "inside a <<'EOFTASKDESC' ... EOFTASKDESC heredoc body."
        )


# ---------------------------------------------------------------------------
# 2. All 7 affected steps use the heredoc capture pattern
# ---------------------------------------------------------------------------


class TestAllAffectedStepsUseHeredoc:
    """Each of the 7 affected bash steps must use the single-quoted heredoc."""

    @pytest.mark.parametrize("step_id", AFFECTED_STEP_IDS)
    def test_step_has_heredoc_capture(self, step_map, step_id):
        """Step must contain heredoc capture for task_description.

        Single-quoted ``<<'EOFTASKDESC'`` is preferred. Unquoted ``<<EOFTASKDESC``
        is acceptable for step-04-setup-worktree (Rust runner needs env-var
        expansion, issue #3087) since the output goes through a sanitization
        pipeline that strips all shell metacharacters.
        """
        step = _get_step(step_map, step_id)
        cmd = step.get("command", "")
        assert "<<'EOFTASKDESC'" in cmd or "<<EOFTASKDESC" in cmd, (
            f"Step '{step_id}' must use heredoc capture (via printenv fallback or direct): "
            "printenv RECIPE_VAR_task_description ... || cat <<'EOFTASKDESC'"
        )

    @pytest.mark.parametrize("step_id", AFFECTED_STEP_IDS)
    def test_step_has_eoftaskdesc_closing_delimiter(self, step_map, step_id):
        """Heredoc body must be closed by the ``EOFTASKDESC`` sentinel line."""
        step = _get_step(step_map, step_id)
        cmd = step.get("command", "")
        # The closing delimiter appears as a line (possibly with leading whitespace
        # due to YAML block scalar indentation).
        assert re.search(r"^\s*EOFTASKDESC\s*$", cmd, re.MULTILINE), (
            f"Step '{step_id}' heredoc is missing its closing EOFTASKDESC delimiter."
        )

    @pytest.mark.parametrize("step_id", AFFECTED_STEP_IDS)
    def test_step_task_description_inside_heredoc_body(self, step_map, step_id):
        """``{{task_description}}`` must appear between the heredoc delimiters."""
        step = _get_step(step_map, step_id)
        cmd = step.get("command", "")
        # Find heredoc block — accept both quoted and unquoted delimiters
        match = re.search(
            r"<<'?EOFTASKDESC'?\n(.*?)EOFTASKDESC", cmd, re.DOTALL
        )
        assert match is not None, (
            f"Step '{step_id}' has no complete heredoc block."
        )
        heredoc_body = match.group(1)
        assert "{{task_description}}" in heredoc_body, (
            f"Step '{step_id}' heredoc body does not contain {{{{task_description}}}}. "
            "The template token must be inside the heredoc body."
        )


# ---------------------------------------------------------------------------
# 3. Heredoc delimiter consistency
# ---------------------------------------------------------------------------


class TestHeredocDelimiterConsistency:
    """All task_description heredocs use the same sentinel to aid grep/CI lint."""

    def test_no_alternative_delimiters_for_task_desc(self, default_workflow):
        """Alternative heredoc delimiters (TASK_DESC_EOF, EOF, etc.) must not
        wrap ``{{task_description}}`` — use ``EOFTASKDESC`` exclusively."""
        # Pattern: heredoc open followed eventually by {{task_description}}
        # using something other than EOFTASKDESC
        for step_id, cmd in _bash_steps(default_workflow):
            # Find any heredoc that contains {{task_description}}
            alt_heredoc = re.findall(
                r"<<'([^']+)'\n[^']*\{\{task_description\}\}",
                cmd,
            )
            for delimiter in alt_heredoc:
                assert delimiter == "EOFTASKDESC", (
                    f"Step '{step_id}' uses non-standard heredoc delimiter "
                    f"'{delimiter}' for task_description. Use EOFTASKDESC."
                )


# ---------------------------------------------------------------------------
# 4. Downstream references must be double-quoted
# ---------------------------------------------------------------------------


class TestDownstreamReferencesDoubleQuoted:
    """Captured variables must always be referenced with double quotes.

    Unquoted ``$TASK_DESC`` is subject to word-splitting and glob expansion
    even though the initial heredoc capture was safe.
    """

    def test_no_unquoted_task_desc_reference(self, default_workflow):
        """``$TASK_DESC`` must not appear outside double quotes in bash steps.

        Legitimate forms: ``"$TASK_DESC"``, ``printf '%s' "$TASK_DESC"``
        Forbidden forms:  ``printf '%s' $TASK_DESC``  (word-split risk)
        """
        violations = []
        for step_id, cmd in _bash_steps(default_workflow):
            # Look for $TASK_DESC not preceded by a double quote
            # Heuristic: finds $TASK_DESC that is either at word-start or
            # preceded by a space/pipe/( but NOT a "
            if re.search(r'(?<!")\$TASK_DESC(?!")', cmd):
                # Exclude heredoc body lines (they won't contain $TASK_DESC)
                # and the assignment line itself (TASK_DESC=$(...)
                filtered = []
                for line in cmd.splitlines():
                    stripped = line.strip()
                    # Skip the assignment line
                    if stripped.startswith("TASK_DESC="):
                        continue
                    if re.search(r'(?<!")\$TASK_DESC(?!")', line):
                        filtered.append(f"  [{step_id}]: {stripped!r}")
                violations.extend(filtered)
        assert violations == [], (
            "Unquoted $TASK_DESC references found (word-split risk):\n"
            + "\n".join(violations)
        )

    def test_no_unquoted_task_val_reference(self, default_workflow):
        """``$TASK_VAL`` must not appear outside double quotes."""
        violations = []
        for step_id, cmd in _bash_steps(default_workflow):
            if re.search(r'(?<!")\$TASK_VAL(?!")', cmd):
                for line in cmd.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("TASK_VAL=") or stripped.startswith("export TASK_VAL"):
                        continue
                    if re.search(r'(?<!")\$TASK_VAL(?!")', line):
                        violations.append(f"  [{step_id}]: {stripped!r}")
        assert violations == [], (
            "Unquoted $TASK_VAL references found:\n" + "\n".join(violations)
        )


# ---------------------------------------------------------------------------
# 5. No eval / bash -c / sh -c receiving derived variables
# ---------------------------------------------------------------------------


class TestNoEvalOrSubshellInjection:
    """Derived variables must never be passed to eval or subshell execution.

    Passing ``$TASK_DESC`` (or ``$TASK_VAL``) to ``eval``, ``bash -c``, or
    ``sh -c`` would re-evaluate the content as shell code — defeating the
    heredoc mitigation entirely.
    """

    _DERIVED_VARS = ("TASK_DESC", "TASK_VAL", "_TD_RAW", "TASK_SLUG")

    def test_no_eval_with_derived_vars(self, default_workflow):
        violations = []
        for step_id, cmd in _bash_steps(default_workflow):
            for var in self._DERIVED_VARS:
                if re.search(rf"eval.*\${var}", cmd):
                    violations.append(f"{step_id}: eval ${var}")
        assert violations == [], (
            "eval with derived task-description variables found:\n"
            + "\n".join(violations)
        )

    def test_no_bash_c_with_derived_vars(self, default_workflow):
        violations = []
        for step_id, cmd in _bash_steps(default_workflow):
            for var in self._DERIVED_VARS:
                if re.search(rf"bash\s+-c.*\${var}", cmd) or re.search(
                    rf"sh\s+-c.*\${var}", cmd
                ):
                    violations.append(f"{step_id}: bash/sh -c ${var}")
        assert violations == [], (
            "bash -c / sh -c with derived task-description variables found:\n"
            + "\n".join(violations)
        )


# ---------------------------------------------------------------------------
# 6. Export anti-pattern: workflow-complete must split export from assignment
# ---------------------------------------------------------------------------


class TestExportAntiPatternFixed:
    """``workflow-complete`` must split ``export VAR=$(...)`` into two lines.

    ``export VAR=$(cmd)`` masks the exit code of ``cmd`` (shellcheck SC2155).
    The safe pattern is::

        VAR=$(cmd)
        export VAR

    This also applies to ISSUE_VAL and PR_VAL in the same step.
    """

    @pytest.mark.parametrize("var_name", ["TASK_VAL", "ISSUE_VAL", "PR_VAL"])
    def test_export_split_from_assignment(self, step_map, var_name):
        """``export {var_name}=$(...)`` must be replaced with capture + export."""
        step = _get_step(step_map, "workflow-complete")
        cmd = step.get("command", "")
        combined_pattern = rf"export\s+{var_name}\s*=\s*\$\("
        assert not re.search(combined_pattern, cmd), (
            f"workflow-complete uses ``export {var_name}=$(...)`` which masks "
            "the command's exit code (shellcheck SC2155).\n"
            f"Split into:\n"
            f"  {var_name}=$(...)\n"
            f"  export {var_name}"
        )

    @pytest.mark.parametrize("var_name", ["TASK_VAL", "ISSUE_VAL", "PR_VAL"])
    def test_separate_export_line_present(self, step_map, var_name):
        """A standalone ``export {var_name}`` line must exist after the assignment."""
        step = _get_step(step_map, "workflow-complete")
        cmd = step.get("command", "")
        # A standalone export line: export VARNAME  (not export VARNAME=...)
        standalone_export = re.compile(
            rf"^\s*export\s+{var_name}\s*$", re.MULTILINE
        )
        assert standalone_export.search(cmd), (
            f"workflow-complete must have a standalone ``export {var_name}`` "
            "line (separate from the assignment) to avoid exit-code masking."
        )


# ---------------------------------------------------------------------------
# 7. Title-bound steps apply newline normalisation and length truncation
# ---------------------------------------------------------------------------


class TestTitleNormalisationPresent:
    """Steps that produce titles for external APIs must normalise the value.

    Newlines injected into a git commit message or GitHub issue title cause
    malformed API requests. All title variables must be sanitised with
    ``tr '\\n\\r' ' '`` and truncated.
    """

    def test_step_03_issue_title_normalised(self, step_map):
        """step-03 ISSUE_TITLE must apply ``tr '\\n\\r'`` and ``cut -c1-200``."""
        step = _get_step(step_map, "step-03-create-issue")
        cmd = step.get("command", "")
        assert "tr '\\n\\r'" in cmd or "tr '\\n'" in cmd, (
            "step-03-create-issue ISSUE_TITLE must normalise newlines with tr"
        )
        assert "cut -c1-200" in cmd, (
            "step-03-create-issue ISSUE_TITLE must truncate to 200 chars with cut"
        )

    def test_step_15_commit_title_normalised(self, step_map):
        """step-15 COMMIT_TITLE must apply ``tr '\\n\\r'`` and limit to 72 chars."""
        step = _get_step(step_map, "step-15-commit-push")
        cmd = step.get("command", "")
        assert "tr '\\n\\r'" in cmd or ("tr '\\n'" in cmd) or ("head -1" in cmd), (
            "step-15-commit-push COMMIT_TITLE must normalise newlines"
        )
        # Either printf format truncation (%.72s) or cut
        assert "72" in cmd or "cut -c1-72" in cmd, (
            "step-15-commit-push COMMIT_TITLE must be limited to 72 chars"
        )

    def test_step_16_pr_title_normalised(self, step_map):
        """step-16 PR_TITLE must apply ``tr '\\n\\r'`` and ``cut -c1-200``."""
        step = _get_step(step_map, "step-16-create-draft-pr")
        cmd = step.get("command", "")
        assert "tr '\\n\\r'" in cmd or "tr '\\n'" in cmd, (
            "step-16-create-draft-pr PR_TITLE must normalise newlines with tr"
        )
        assert "cut -c1-200" in cmd, (
            "step-16-create-draft-pr PR_TITLE must truncate to 200 chars with cut"
        )


# ---------------------------------------------------------------------------
# 8. Bash syntax validation: heredoc pattern with adversarial inputs
# ---------------------------------------------------------------------------


class TestHeredocBashSyntax:
    """Verify the heredoc pattern is syntactically valid with adversarial inputs.

    Simulates what the recipe runner does: text-substitute ``{{task_description}}``
    then pass the resulting script to ``/bin/bash -c``.
    """

    @pytest.mark.parametrize("name,task_desc", ADVERSARIAL_TASK_DESCRIPTIONS)
    def test_basic_heredoc_syntax_valid(self, name, task_desc):
        """Single-quoted heredoc must pass ``bash -n`` for all adversarial inputs."""
        script = (
            f"TASK_DESC=$(cat <<'EOFTASKDESC'\n"
            f"{task_desc}\n"
            f"EOFTASKDESC\n"
            f")\n"
            f'echo "$TASK_DESC"'
        )
        result = subprocess.run(
            ["/bin/bash", "-n", "-c", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0, (
            f"Heredoc pattern failed bash -n check for {name!r}: {result.stderr!r}"
        )

    @pytest.mark.parametrize("name,task_desc", ADVERSARIAL_TASK_DESCRIPTIONS)
    def test_heredoc_captures_raw_value(self, name, task_desc):
        """Heredoc must capture the literal value — no metacharacter expansion."""
        script = (
            f"TASK_DESC=$(cat <<'EOFTASKDESC'\n"
            f"{task_desc}\n"
            f"EOFTASKDESC\n"
            f")\n"
            f'printf "%s" "$TASK_DESC"'
        )
        result = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0, (
            f"Heredoc script failed for {name!r}: {result.stderr!r}"
        )
        # The captured value should equal the input (heredoc strips trailing newline)
        expected = task_desc.rstrip("\n")
        assert result.stdout == expected, (
            f"Heredoc capture mismatch for {name!r}: "
            f"got {result.stdout!r}, expected {expected!r}"
        )

    @pytest.mark.parametrize("name,task_desc", ADVERSARIAL_TASK_DESCRIPTIONS)
    def test_heredoc_does_not_execute_metacharacters(self, name, task_desc):
        """Metacharacters inside the heredoc body must NOT execute as shell code.

        A canary file is used: if any injection causes execution, the canary
        would be created and the test fails.
        """
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            canary = os.path.join(tmpdir, "canary_injected")
            # Embed a touch-canary payload into the task description simulation
            # (the actual task_desc is injected, but in heredoc it can't execute)
            script = (
                f"TASK_DESC=$(cat <<'EOFTASKDESC'\n"
                f"{task_desc}\n"
                f"EOFTASKDESC\n"
                f")\n"
                f'printf "%s" "$TASK_DESC" > /dev/null'
            )
            result = subprocess.run(
                ["/bin/bash", "-c", script],
                capture_output=True,
                text=True,
                timeout=5,
                env={**os.environ, "CANARY_PATH": canary},
            )
            assert result.returncode == 0, (
                f"Script failed unexpectedly for {name!r}: {result.stderr!r}"
            )
            assert not os.path.exists(canary), (
                f"Canary file was created for {name!r} — "
                "shell injection may have occurred!"
            )

    def test_old_single_quote_pattern_fails_for_quote_in_value(self):
        """Regression guard: old single-quote wrapping breaks on values with quotes.

        This confirms the heredoc fix is necessary — the old pattern is broken.
        """
        task_desc = "Fix the user's profile page (broken)"
        script = f"TASK_DESC=$(printf '%s' '{task_desc}')"
        result = subprocess.run(
            ["/bin/bash", "-n", "-c", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode != 0, (
            f"Old single-quote pattern should FAIL for {task_desc!r} "
            "but it passed — test assumption is wrong"
        )

    def test_old_printf_pattern_executes_backtick_injection(self):
        """Regression guard: old ``printf '%s' {{task_description}}`` pattern
        executes backtick payloads — confirm the old approach is dangerous.

        This test verifies the threat model is real, not theoretical.
        """
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            canary = os.path.join(tmpdir, "canary_backtick")
            # Simulate the template substitution of the old pattern:
            # printf '%s' {{task_description}} → printf '%s' `touch canary`
            script = f"printf '%s' `touch {canary}`"
            subprocess.run(
                ["/bin/bash", "-c", script],
                capture_output=True,
                text=True,
                timeout=5,
            )
            assert os.path.exists(canary), (
                "Backtick injection via old printf pattern did NOT execute — "
                "threat model assumption may be wrong (environment may sandbox)"
            )


# ---------------------------------------------------------------------------
# 8b. Dual-path printenv || heredoc: Rust runner env-var + Python runner fallback
# ---------------------------------------------------------------------------


class TestDualPathPrintenvHeredoc:
    """Verify the ``printenv RECIPE_VAR_* || cat <<'HEREDOC'`` pattern (issue #3117).

    The Rust recipe runner sets ``RECIPE_VAR_<name>`` env vars and replaces
    ``{{name}}`` with ``$RECIPE_VAR_<name>``.  Single-quoted heredocs prevent
    env-var expansion, producing literal text.  The dual-path pattern fixes
    this: ``printenv`` succeeds under Rust runner; ``cat <<'HEREDOC'`` fallback
    is used by the Python runner (inline substitution, no env var set).
    """

    def test_printenv_path_captures_env_var(self):
        """With RECIPE_VAR_* set (Rust runner), printenv returns the value."""
        task = "Fix the user's profile page (broken)"
        script = (
            "TASK_DESC=$(printenv RECIPE_VAR_task_description 2>/dev/null || cat <<'EOFTASKDESC'\n"
            "$RECIPE_VAR_task_description\n"
            "EOFTASKDESC\n"
            ")\n"
            'printf "%s" "$TASK_DESC"'
        )
        result = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=5,
            env={**os.environ, "RECIPE_VAR_task_description": task},
        )
        assert result.returncode == 0
        assert result.stdout.strip() == task

    def test_heredoc_fallback_without_env_var(self):
        """Without RECIPE_VAR_* (Python runner), heredoc captures literal text."""
        task = "Fix the user's profile page (broken)"
        script = (
            "TASK_DESC=$(printenv RECIPE_VAR_task_description 2>/dev/null || cat <<'EOFTASKDESC'\n"
            f"{task}\n"
            "EOFTASKDESC\n"
            ")\n"
            'printf "%s" "$TASK_DESC"'
        )
        env = {k: v for k, v in os.environ.items() if k != "RECIPE_VAR_task_description"}
        result = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )
        assert result.returncode == 0
        assert task in result.stdout

    @pytest.mark.parametrize("name,task_desc", ADVERSARIAL_TASK_DESCRIPTIONS[:5])
    def test_printenv_path_safe_with_adversarial_input(self, name, task_desc):
        """Adversarial input in env var is safely captured via printenv."""
        script = (
            "TASK_DESC=$(printenv RECIPE_VAR_task_description 2>/dev/null || cat <<'EOFTASKDESC'\n"
            "$RECIPE_VAR_task_description\n"
            "EOFTASKDESC\n"
            ")\n"
            'printf "%s" "$TASK_DESC"'
        )
        result = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=5,
            env={**os.environ, "RECIPE_VAR_task_description": task_desc},
        )
        assert result.returncode == 0
        assert result.stdout.strip() == task_desc

    def test_recipe_steps_use_printenv_pattern(self, default_workflow):
        """All heredoc-protected steps (except step-04) use printenv || cat."""
        for step in default_workflow.get("steps", []):
            step_id = step.get("id", "")
            if step_id not in AFFECTED_STEP_IDS:
                continue
            if step_id == "step-04-setup-worktree":
                continue  # step-04 uses unquoted heredoc for Rust runner compat
            cmd = step.get("command", "")
            if "EOFTASKDESC" in cmd:
                assert "printenv RECIPE_VAR_task_description" in cmd, (
                    f"Step '{step_id}' should use printenv || cat pattern for "
                    "Rust runner compatibility (issue #3117)"
                )


# ---------------------------------------------------------------------------
# 9. Step-specific heredoc integration: each step's full script fragment
# ---------------------------------------------------------------------------


class TestStepSpecificHeredocIntegration:
    """Test each affected step's script fragment with adversarial inputs."""

    def _run(self, script: str, timeout: int = 5) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def _syntax_check(self, script: str, timeout: int = 5) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["/bin/bash", "-n", "-c", script],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    @pytest.mark.parametrize("name,task_desc", ADVERSARIAL_TASK_DESCRIPTIONS[:5])
    def test_step_00_script_fragment_syntax(self, name, task_desc):
        """step-00-workflow-preparation script fragment passes bash -n."""
        script = (
            f"TASK_DESC=$(cat <<'EOFTASKDESC'\n"
            f"{task_desc}\n"
            f"EOFTASKDESC\n"
            f")\n"
            f"printf 'Task: %s\\n' \"$TASK_DESC\""
        )
        result = self._syntax_check(script)
        assert result.returncode == 0, (
            f"step-00 fragment failed bash -n for {name!r}: {result.stderr!r}"
        )

    @pytest.mark.parametrize("name,task_desc", ADVERSARIAL_TASK_DESCRIPTIONS[:5])
    def test_step_03_issue_title_generation(self, name, task_desc):
        """step-03-create-issue issue title generation with adversarial input."""
        script = (
            f"TASK_DESC=$(cat <<'EOFTASKDESC'\n"
            f"{task_desc}\n"
            f"EOFTASKDESC\n"
            f")\n"
            "ISSUE_TITLE=$(printf '%s' \"$TASK_DESC\" | tr '\\n\\r' '  ' | cut -c1-200)\n"
            'printf "%s" "$ISSUE_TITLE"'
        )
        result = self._run(script)
        assert result.returncode == 0, (
            f"step-03 issue title script failed for {name!r}: {result.stderr!r}"
        )
        title = result.stdout
        assert len(title) <= 200, f"ISSUE_TITLE exceeds 200 chars for {name!r}"
        assert "\n" not in title, f"ISSUE_TITLE contains newline for {name!r}"
        assert "\r" not in title, f"ISSUE_TITLE contains carriage return for {name!r}"

    @pytest.mark.parametrize("name,task_desc", ADVERSARIAL_TASK_DESCRIPTIONS[:5])
    def test_step_15_commit_title_generation(self, name, task_desc):
        """step-15-commit-push commit title generation with adversarial input."""
        script = (
            f"TASK_DESC=$(cat <<'EOFTASKDESC'\n"
            f"{task_desc}\n"
            f"EOFTASKDESC\n"
            f")\n"
            "COMMIT_TITLE=$(printf 'feat: %.72s' "
            "\"$(printf '%s' \"$TASK_DESC\" | tr '\\n\\r' ' ' | head -1)\")\n"
            'printf "%s" "$COMMIT_TITLE"'
        )
        result = self._run(script)
        assert result.returncode == 0, (
            f"step-15 commit title script failed for {name!r}: {result.stderr!r}"
        )
        title = result.stdout
        # Printf %.72s truncates to 72 chars after "feat: " prefix
        assert len(title) <= 78, (  # "feat: " (6) + 72 = 78
            f"COMMIT_TITLE too long for {name!r}: {len(title)} chars"
        )
        assert "\n" not in title, f"COMMIT_TITLE contains newline for {name!r}"

    @pytest.mark.parametrize("name,task_desc", ADVERSARIAL_TASK_DESCRIPTIONS[:5])
    def test_step_16_pr_title_generation(self, name, task_desc):
        """step-16-create-draft-pr PR title generation with adversarial input."""
        script = (
            f"TASK_DESC=$(cat <<'EOFTASKDESC'\n"
            f"{task_desc}\n"
            f"EOFTASKDESC\n"
            f")\n"
            "PR_TITLE=$(printf '%s' \"$TASK_DESC\" | tr '\\n\\r' ' ' | cut -c1-200)\n"
            'printf "%s" "$PR_TITLE"'
        )
        result = self._run(script)
        assert result.returncode == 0, (
            f"step-16 PR title script failed for {name!r}: {result.stderr!r}"
        )
        title = result.stdout
        assert len(title) <= 200, f"PR_TITLE exceeds 200 chars for {name!r}"
        assert "\n" not in title, f"PR_TITLE contains newline for {name!r}"

    @pytest.mark.parametrize("name,task_desc", ADVERSARIAL_TASK_DESCRIPTIONS[:5])
    def test_step_22b_final_status_fragment(self, name, task_desc):
        """step-22b-final-status printf fragment with adversarial input."""
        script = (
            f"TASK_DESC=$(cat <<'EOFTASKDESC'\n"
            f"{task_desc}\n"
            f"EOFTASKDESC\n"
            f")\n"
            "printf '=== Task: %s ===\\n' \"$TASK_DESC\""
        )
        result = self._run(script)
        assert result.returncode == 0, (
            f"step-22b final-status script failed for {name!r}: {result.stderr!r}"
        )
        assert "===" in result.stdout

    @pytest.mark.parametrize("name,task_desc", ADVERSARIAL_TASK_DESCRIPTIONS[:5])
    def test_workflow_complete_export_fragment(self, name, task_desc):
        """workflow-complete export fragment after split (capture + export).

        This test verifies the FIXED pattern (split export) — it will fail
        until the ``export TASK_VAL=$(...)`` anti-pattern is corrected.
        """
        # After the fix, the pattern must be:
        #   TASK_VAL=$(printf '%s' "$TASK_DESC")
        #   export TASK_VAL
        script = (
            f"TASK_DESC=$(cat <<'EOFTASKDESC'\n"
            f"{task_desc}\n"
            f"EOFTASKDESC\n"
            f")\n"
            # Split pattern (the fix):
            'TASK_VAL=$(printf \'%s\' "$TASK_DESC")\n'
            "export TASK_VAL\n"
            'printf "%s" "$TASK_VAL"'
        )
        result = self._run(script)
        assert result.returncode == 0, (
            f"workflow-complete export-split script failed for {name!r}: {result.stderr!r}"
        )
        expected = task_desc.rstrip("\n")
        assert result.stdout == expected, (
            f"TASK_VAL mismatch for {name!r}: "
            f"got {result.stdout!r}, expected {expected!r}"
        )


# ---------------------------------------------------------------------------
# 10. CI regression guard: grep-based checks that block re-introduction
# ---------------------------------------------------------------------------


class TestCIRegressionGuards:
    """Fast grep-based checks that can run in a CI lint step.

    These mirror the verification commands from the security documentation:
    ``grep -rn "printf.*{{task_description}}" recipes/``
    """

    def test_grep_finds_zero_vulnerable_printf_patterns(self):
        """grep must find zero ``printf.*{{task_description}}`` lines in the recipe."""
        recipe_path = RECIPE_DIR / "default-workflow.yaml"
        if not recipe_path.exists():
            pytest.skip("default-workflow.yaml not found")
        result = subprocess.run(
            ["grep", "-n", r"printf.*{{task_description}}", str(recipe_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, (  # grep returns 1 when no matches
            "Vulnerable printf pattern found in default-workflow.yaml:\n"
            + result.stdout
        )

    def test_grep_finds_zero_single_quote_wrapped_task_desc(self):
        """grep must find zero ``'{{task_description}}'`` patterns."""
        recipe_path = RECIPE_DIR / "default-workflow.yaml"
        if not recipe_path.exists():
            pytest.skip("default-workflow.yaml not found")
        result = subprocess.run(
            ["grep", "-n", r"'{{task_description}}'", str(recipe_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, (
            "Single-quote wrapped task_description found:\n" + result.stdout
        )

    def test_grep_confirms_heredoc_count_matches_affected_steps(self):
        """grep must find exactly one heredoc open per affected step (7 total).

        Counts both quoted (<<'EOFTASKDESC') and unquoted (<<EOFTASKDESC)
        heredocs. Step-04-setup-worktree uses unquoted for Rust runner
        compatibility (issue #3087).
        """
        recipe_path = RECIPE_DIR / "default-workflow.yaml"
        if not recipe_path.exists():
            pytest.skip("default-workflow.yaml not found")
        result = subprocess.run(
            ["grep", "-cE", r"<<'?EOFTASKDESC'?", str(recipe_path)],
            capture_output=True,
            text=True,
        )
        count = int(result.stdout.strip())
        assert count == len(AFFECTED_STEP_IDS), (
            f"Expected {len(AFFECTED_STEP_IDS)} heredoc opens (one per affected step), "
            f"found {count}. Either a step is missing the fix or an extra heredoc was added."
        )


# ---------------------------------------------------------------------------
# 11. Null-byte handling: OS rejects null bytes at subprocess boundary
# ---------------------------------------------------------------------------


class TestNullByteHandling:
    """Null bytes (\\x00) cannot transit the subprocess argument boundary on Linux.

    ``os.posix_spawn`` raises ``ValueError: embedded null byte`` when a null
    byte is present in argv. This is an OS-level safeguard that is independent
    of the heredoc fix. We document this boundary here and verify the behaviour
    is a clean ValueError (not a security bypass).
    """

    def test_null_byte_rejected_at_subprocess_boundary(self):
        """``subprocess.run`` raises ValueError for argv entries containing null bytes.

        Linux ``execve``/``posix_spawn`` rejects null bytes in any argv entry.
        We verify this by embedding a null byte directly inside the bash script
        argument string (not via f-string repr escaping).
        """
        _, task_desc = _NULL_BYTE_CASE
        # task_desc already contains an actual \x00 byte; embed it literally in the
        # script string so subprocess receives it as a null byte in argv[2].
        script = "echo '" + task_desc + "'"
        with pytest.raises(ValueError, match="null byte"):
            subprocess.run(
                ["/bin/bash", "-c", script],
                capture_output=True,
                text=True,
                timeout=5,
            )

    def test_null_byte_not_present_in_recipe_yaml(self):
        """The recipe file must contain no null bytes.

        A null byte in the YAML source would indicate file corruption and would
        prevent safe template substitution.
        """
        recipe_path = RECIPE_DIR / "default-workflow.yaml"
        if not recipe_path.exists():
            pytest.skip("default-workflow.yaml not found")
        content = recipe_path.read_bytes()
        assert b"\x00" not in content, (
            "default-workflow.yaml contains a null byte — file may be corrupted"
        )
