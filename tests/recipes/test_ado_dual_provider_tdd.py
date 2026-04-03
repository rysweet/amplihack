"""TDD tests for issue #4205 — dual-provider (GitHub + ADO) workflow gaps.

These tests define the CONTRACT for behaviors not yet fully implemented.
They FAIL against the current codebase and PASS once the implementation is complete.

Missing behaviors covered:
  1. step-16 ADO PR must link work item via --work-items $ISSUE_NUM
  2. ADO steps must run a pre-flight az auth check (az account show) before
     making API calls — prevents silent failures with unhelpful error output
  3. step-16 --target-branch must be configurable via a variable or recipe
     context, not hardcoded to "main"
  4. detect_git_provider must handle SSH ADO remote format
     (git@ssh.dev.azure.com:v3/org/project/repo)

Edge-case / security tests (some PASS, some FAIL) also included:
  5. step-16 exit code must propagate AZ_STATUS (not masked by || echo '')
  6. step-03 WIQL search title must strip WIQL-significant operators (not just '')
  7. step-03b must extract numeric ID from ssh-style ADO branch-push URLs
  8. step-16 heredoc delimiters must be quoted (security: prevent bash expansion)
  9. step-03 heredoc delimiters must be quoted
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml


@pytest.fixture(scope="module")
def workflow_steps():
    """Load and return step commands from default-workflow.yaml."""
    workflow_path = Path("amplifier-bundle/recipes/default-workflow.yaml")
    if not workflow_path.exists():
        pytest.skip("default-workflow.yaml not found")
    with open(workflow_path) as f:
        data = yaml.safe_load(f)
    return {s["id"]: s for s in data["steps"]}


def _run_bash(script: str, timeout: int = 15) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["/bin/bash", "-c", script],
        capture_output=True,
        text=True,
        timeout=timeout,
    )


# =============================================================================
# 1. MISSING: --work-items flag in step-16 ADO PR creation
#    Contract: az repos pr create MUST include --work-items $ISSUE_NUM so the
#    ADO PR is linked to the work item created in step-03.
#    STATUS: FAILING — --work-items is not in the current implementation.
# =============================================================================


class TestStep16AdoWorkItemLinking:
    """step-16 ADO path must link the PR to the originating work item."""

    def test_step_16_ado_uses_work_items_flag(self, workflow_steps):
        """--work-items flag must appear in the az repos pr create invocation."""
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        assert "--work-items" in cmd, (
            "step-16 ADO path must pass --work-items to az repos pr create to link "
            "the PR to the ADO work item created in step-03. "
            'Fix: add --work-items "$ISSUE_NUM" to the az repos pr create call.'
        )

    def test_step_16_ado_work_items_references_issue_num(self, workflow_steps):
        """The --work-items value must be the numeric ISSUE_NUM variable."""
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        # Acceptable forms: --work-items "$ISSUE_NUM", --work-items $ISSUE_NUM
        has_flag = "--work-items" in cmd
        references_issue = (
            "ISSUE_NUM" in cmd.split("--work-items", 1)[-1][:40] if has_flag else False
        )
        assert has_flag and references_issue, (
            "step-16 --work-items must reference ISSUE_NUM. "
            "Found command fragment: "
            + (cmd.split("--work-items", 1)[-1][:80] if has_flag else "(--work-items absent)")
        )


# =============================================================================
# 2. MISSING: Pre-flight az auth check before ADO API calls
#    Contract: Both step-03 (ADO path) and step-16 (ADO path) must call
#    `az account show` before attempting ADO API operations so that the user
#    gets a clear "not logged in" error rather than a cryptic API failure.
#    STATUS: FAILING — no az account show in either step.
# =============================================================================


class TestAdoPreflightAuthCheck:
    """ADO steps must validate az CLI authentication before making API calls."""

    def test_step_03_ado_path_runs_az_account_show(self, workflow_steps):
        """step-03 ADO path must call az account show to verify auth."""
        cmd = workflow_steps["step-03-create-issue"]["command"]
        assert "az account show" in cmd, (
            "step-03 ADO path must run 'az account show' as a pre-flight check "
            "so that unauthenticated users get a clear error. "
            "Fix: add an az account show check in the ADO branch before api calls."
        )

    def test_step_16_ado_path_runs_az_account_show(self, workflow_steps):
        """step-16 ADO path must call az account show to verify auth."""
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        assert "az account show" in cmd, (
            "step-16 ADO path must run 'az account show' as a pre-flight check "
            "before calling az repos pr create. "
            "Fix: add an az account show check in the ADO branch before api calls."
        )

    def test_step_03_ado_auth_check_exits_on_failure(self, workflow_steps):
        """The auth check must cause the step to fail if the user is not logged in."""
        cmd = workflow_steps["step-03-create-issue"]["command"]
        # Must have az account show AND a failure handler (exit 1 or error message)
        ado_section = cmd.split("ado", 1)[-1] if "ado" in cmd else cmd
        has_auth_check = "az account show" in ado_section
        has_failure_path = "exit 1" in ado_section or "ERROR" in ado_section
        assert has_auth_check and has_failure_path, (
            f"step-03 ADO auth check must abort with exit 1 when az account show fails. "
            f"Current state: auth_check={has_auth_check!r}, failure_path={has_failure_path!r}"
        )


# =============================================================================
# 3. MISSING: Configurable --target-branch (not hardcoded "main")
#    Contract: step-16 --target-branch must use a variable (defaulting to main)
#    so that repos with different default branch names (master, develop, trunk)
#    work correctly without recipe changes.
#    STATUS: FAILING — currently hardcoded as --target-branch "main"
# =============================================================================


class TestStep16ConfigurableTargetBranch:
    """step-16 ADO PR target branch must be configurable, not hardcoded."""

    def test_step_16_target_branch_not_hardcoded_main(self, workflow_steps):
        """--target-branch should reference a variable, not a literal "main"."""
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        # Check the whole command — the hardcoded "main" appears in the ADO path
        # regardless of how we split the string.
        assert '--target-branch "main"' not in cmd and "--target-branch 'main'" not in cmd, (
            "step-16 ADO --target-branch must use a variable (e.g. $BASE_BRANCH or "
            '${base_branch:-main}) rather than the literal string "main". '
            "Repos using master/develop/trunk will break with the hardcoded value. "
            "Fix: set BASE_BRANCH=$(git remote show origin | grep 'HEAD branch' | awk '{print $NF}') "
            "or accept a recipe context variable."
        )

    def test_step_16_ado_target_branch_uses_variable(self, workflow_steps):
        """The --target-branch value in the ADO path must reference a shell variable."""
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        # Acceptable: $BASE_BRANCH, ${BASE_BRANCH}, ${base_branch:-main}, $DEFAULT_BRANCH
        variable_pattern = re.compile(r"--target-branch\s+[\"\']?\$\{?[A-Z_a-z]")
        assert variable_pattern.search(cmd), (
            "step-16 --target-branch must use a shell variable (e.g. $BASE_BRANCH). "
            "Current value is a hardcoded literal."
        )


# =============================================================================
# 4. EDGE CASE: SSH ADO remote format detection
#    Contract: detect_git_provider must return "ado" for SSH ADO remotes:
#    git@ssh.dev.azure.com:v3/org/project/repo
#    STATUS: PASSES — "dev.azure.com" substring match covers SSH format.
#    Included to guard against future regressions.
# =============================================================================

DETECT_FUNC = r"""
detect_git_provider() {
  local remote_url
  remote_url=$(git remote get-url origin 2>/dev/null || echo '')
  if [[ "$remote_url" == *"dev.azure.com"* ]] || [[ "$remote_url" == *"visualstudio.com"* ]]; then
    echo "ado"
  else
    echo "github"
  fi
}
"""


class TestSshAdoRemoteDetection:
    """SSH-format ADO remotes must be detected as 'ado'."""

    def test_ssh_dev_azure_com_v3_returns_ado(self, tmp_path):
        """git@ssh.dev.azure.com:v3/org/project/repo → 'ado'."""
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(tmp_path),
                "remote",
                "add",
                "origin",
                "git@ssh.dev.azure.com:v3/myorg/myproject/myrepo",
            ],
            check=True,
            capture_output=True,
        )
        script = f"cd {tmp_path}\n{DETECT_FUNC}\ndetect_git_provider"
        result = _run_bash(script)
        assert result.returncode == 0
        assert result.stdout.strip() == "ado", (
            "SSH ADO remote 'git@ssh.dev.azure.com:v3/...' must return 'ado'"
        )

    def test_ssh_visualstudio_com_returns_ado(self, tmp_path):
        """SSH-style visualstudio.com remote must return 'ado'."""
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(tmp_path),
                "remote",
                "add",
                "origin",
                "myorg@vs-ssh.visualstudio.com:v3/myorg/myproject/myrepo",
            ],
            check=True,
            capture_output=True,
        )
        script = f"cd {tmp_path}\n{DETECT_FUNC}\ndetect_git_provider"
        result = _run_bash(script)
        assert result.returncode == 0
        assert result.stdout.strip() == "ado", (
            "SSH ADO remote (visualstudio.com SSH format) must return 'ado'"
        )

    def test_yaml_detect_func_handles_ssh_dev_azure_com(self, workflow_steps, tmp_path):
        """The detect_git_provider function extracted from the YAML handles SSH ADO remotes."""
        # Extract the function from step-03
        cmd = workflow_steps["step-03-create-issue"]["command"]
        func_match = re.search(r"(detect_git_provider\(\)\s*\{.*?\})", cmd, re.DOTALL)
        assert func_match, "detect_git_provider function not found in step-03"
        func_body = func_match.group(1)

        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(
            [
                "git",
                "-C",
                str(tmp_path),
                "remote",
                "add",
                "origin",
                "git@ssh.dev.azure.com:v3/myorg/myproject/myrepo",
            ],
            check=True,
            capture_output=True,
        )
        script = f"cd {tmp_path}\n{func_body}\ndetect_git_provider"
        result = _run_bash(script)
        assert result.returncode == 0
        assert result.stdout.strip() == "ado"


# =============================================================================
# 5. SECURITY: step-16 exit code must NOT be masked by || echo ''
#    Contract: az repos pr create must NOT use || echo '' so that AZ_STATUS
#    captures the real exit code on failure.
#    STATUS: PASSES — the || echo '' was removed in commit 607f41a36.
#    Regression guard included.
# =============================================================================


class TestStep16ExitCodePropagation:
    """step-16 ADO PR creation must propagate real exit codes."""

    def test_step_16_az_repos_pr_create_has_no_echo_pipe(self, workflow_steps):
        """|| echo '' must NOT appear as executable code after az repos pr create."""
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        # Strip shell comments (lines starting with optional whitespace + #) before checking,
        # so that a comment like "# do NOT use || echo ''" does not trigger a false positive.
        non_comment_lines = [line for line in cmd.splitlines() if not line.lstrip().startswith("#")]
        lines = non_comment_lines
        for i, line in enumerate(lines):
            if "az repos pr create" in line:
                # Check the next 5 non-comment lines for || echo ''
                context = "\n".join(lines[i : i + 6])
                assert "|| echo ''" not in context and '|| echo ""' not in context, (
                    "az repos pr create must not be piped with || echo '' which "
                    "would mask the real exit code. "
                    "Context (comments stripped): " + context
                )

    def test_step_16_captures_az_status_after_pr_create(self, workflow_steps):
        """AZ_STATUS=$? must appear immediately after az repos pr create."""
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        assert "AZ_STATUS=$?" in cmd, (
            "step-16 must capture AZ_STATUS=$? immediately after az repos pr create "
            "to preserve the real exit code for error handling."
        )

    def test_step_16_exits_with_az_status_on_failure(self, workflow_steps):
        """exit must use ${AZ_STATUS:-1} not a hardcoded exit 1."""
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        # After the AZ_STATUS capture, the exit should reference that variable
        assert "${AZ_STATUS:-1}" in cmd or "exit $AZ_STATUS" in cmd, (
            "step-16 must exit with ${AZ_STATUS:-1} or $AZ_STATUS to propagate "
            "the real az repos pr create exit code."
        )


# =============================================================================
# 6. SECURITY: WIQL injection — SEARCH_TITLE must strip WIQL operators
#    Contract: The ADO WIQL query in step-03 must sanitize SEARCH_TITLE to
#    prevent WIQL injection via task description content. Currently only
#    single-quotes are escaped; WIQL keywords and brackets are not stripped.
#    STATUS: FAILING — only single-quote escaping is implemented.
# =============================================================================


class TestWiqlInjectionSanitization:
    """SEARCH_TITLE in ADO WIQL query must be sanitized against injection."""

    def test_step_03_ado_strips_wiql_brackets_from_search_title(self, workflow_steps):
        """SEARCH_TITLE must have [ and ] stripped before WIQL interpolation."""
        cmd = workflow_steps["step-03-create-issue"]["command"]
        # Look for bracket stripping in the SEARCH_TITLE area
        search_title_area = cmd
        if "SEARCH_TITLE" in cmd:
            # Extract from first SEARCH_TITLE assignment to WIQL query
            start = cmd.index("SEARCH_TITLE")
            end = cmd.index("WIQL", start) if "WIQL" in cmd[start:] else start + 500
            search_title_area = cmd[start:end]
        # Should strip [ and ] using sed, tr, or bash substitution
        strips_brackets = (
            r"[" in search_title_area
            and (
                "tr -d" in search_title_area
                or "${" in search_title_area
                or "sed" in search_title_area
            )
        ) or (
            "\\[" in search_title_area or "\\]" in search_title_area or "[\\[" in search_title_area
        )
        assert strips_brackets, (
            "step-03 SEARCH_TITLE must strip WIQL-significant bracket characters [ ] "
            "before interpolation into the WIQL WHERE clause. "
            "Currently only single-quotes are escaped, leaving injection surface open. "
            'Fix: add SEARCH_TITLE="${SEARCH_TITLE//[\\[\\]/}" or similar.'
        )

    def test_step_03_ado_wiql_escaping_handles_semicolons(self, workflow_steps):
        """SEARCH_TITLE must strip semicolons which can terminate WIQL statements."""
        cmd = workflow_steps["step-03-create-issue"]["command"]
        if "SEARCH_TITLE" in cmd:
            start = cmd.index("SEARCH_TITLE")
            search_area = cmd[start : start + 600]
        else:
            search_area = cmd

        strips_semicolons = ";" in search_area and (
            "tr -d" in search_area
            or "sed" in search_area
            or "${SEARCH_TITLE//;" in search_area
            or "${SEARCH_TITLE//;/" in search_area
        )
        assert strips_semicolons, (
            "step-03 SEARCH_TITLE must strip semicolons which can terminate WIQL "
            "statements and allow injection of arbitrary WIQL clauses. "
            'Fix: SEARCH_TITLE="${SEARCH_TITLE//;/}" before the WIQL query.'
        )


# =============================================================================
# 7. EDGE CASE: step-03b must handle ADO branch-push style output
#    Contract: When step-03 prints only a bare work item ID (e.g. "12345")
#    without the _workitems/edit/ prefix, step-03b must still extract it.
#    STATUS: FAILING — step-03b regex requires the _workitems/edit/ prefix.
# =============================================================================


class TestStep03bBareIdExtraction:
    """step-03b must extract numeric IDs from bare ADO work item ID output."""

    def test_step_03b_handles_bare_numeric_output(self, workflow_steps):
        """step-03b regex must match bare numeric ID output from az boards."""
        cmd = workflow_steps["step-03b-extract-issue-number"]["command"]
        # The EXTRACTED= line should match a bare number as fallback
        # Currently only matches (issues|_workitems/edit)/[0-9]+
        extracted_line = ""
        for line in cmd.splitlines():
            if "EXTRACTED=" in line and "grep" in line:
                extracted_line = line
                break

        # Check whether a bare number would be matched
        # The current regex is: (issues|_workitems/edit)/[0-9]+
        # A bare "12345" would NOT match this pattern
        current_regex = re.search(r"grep -oE ['\"]([^'\"]+)['\"]", extracted_line)
        if current_regex:
            pattern = current_regex.group(1)
            test_input = "12345"
            matches = re.findall(pattern, test_input)
            assert matches, (
                f"step-03b regex '{pattern}' does not match bare numeric ID '12345'. "
                "When az boards work-item create prints just the numeric ID (no URL prefix), "
                "step-03b fails to extract it. "
                "Fix: extend the regex or add a fallback match for bare numeric IDs."
            )
        else:
            # If no regex found at all, that's a problem
            assert False, (
                "Could not find EXTRACTED= grep pattern in step-03b. "
                "Bare numeric ID extraction cannot be verified."
            )


# =============================================================================
# 8. SECURITY REGRESSION: Heredoc delimiters must be quoted
#    Contract: <<'EOFTASKDESC' and <<'EOFDESIGN' must use quoted delimiters to
#    prevent bash expansion of recipe-substituted content.
#    STATUS: PASSES — both delimiters are now quoted. Regression guard.
# =============================================================================


class TestHeredocSecurity:
    """Heredoc delimiters in ADO-modified steps must be quoted (security fix)."""

    def test_step_16_taskdesc_heredoc_is_quoted(self, workflow_steps):
        """<<'EOFTASKDESC' (quoted) must be used, not <<EOFTASKDESC (unquoted)."""
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        assert "<<'EOFTASKDESC'" in cmd, (
            "step-16 TASK_DESC heredoc must use quoted delimiter <<'EOFTASKDESC' "
            "to prevent bash expansion of $()/backtick sequences in task_description."
        )
        assert "<<EOFTASKDESC" not in cmd.replace("<<'EOFTASKDESC'", ""), (
            "Unquoted <<EOFTASKDESC must not appear in step-16 (security regression)."
        )

    def test_step_16_design_heredoc_is_quoted(self, workflow_steps):
        """<<'EOFDESIGN' (quoted) must be used, not <<EOFDESIGN (unquoted)."""
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        assert "<<'EOFDESIGN'" in cmd, (
            "step-16 PR_DESIGN heredoc must use quoted delimiter <<'EOFDESIGN' "
            "to prevent bash expansion of design_spec content."
        )

    def test_step_03_taskdesc_heredoc_is_quoted(self, workflow_steps):
        """step-03 TASK_DESC heredoc must also use quoted delimiter."""
        cmd = workflow_steps["step-03-create-issue"]["command"]
        assert "<<'EOFTASKDESC'" in cmd, (
            "step-03 TASK_DESC heredoc must use quoted delimiter <<'EOFTASKDESC'."
        )

    def test_step_03_reqs_heredoc_is_quoted(self, workflow_steps):
        """step-03 ISSUE_REQS heredoc must use quoted delimiter."""
        cmd = workflow_steps["step-03-create-issue"]["command"]
        assert "<<'EOFREQS'" in cmd, (
            "step-03 ISSUE_REQS heredoc must use quoted delimiter <<'EOFREQS'."
        )


# =============================================================================
# 9. NUMERIC VALIDATION: NEW_ITEM_ID must be validated before use
#    Contract: After az boards work-item create, the returned ID must be
#    validated as numeric before it is used in shell expansions.
#    STATUS: PASSES — case '*[!0-9]*' guard is implemented. Regression guard.
# =============================================================================


class TestAdoWorkItemIdValidation:
    """ADO work item ID from az boards must be validated as numeric."""

    def test_step_03_validates_new_item_id_is_numeric(self, workflow_steps):
        """NEW_ITEM_ID must have a [!0-9] case guard after az boards work-item create."""
        cmd = workflow_steps["step-03-create-issue"]["command"]
        assert "[!0-9]" in cmd, (
            "step-03 must include a case '*[!0-9]*' guard on NEW_ITEM_ID after "
            "az boards work-item create to reject non-numeric IDs."
        )

    def test_new_item_id_numeric_guard_rejects_non_numeric(self):
        """The [!0-9] case guard must exit 1 on non-numeric input."""
        script = r"""
        NEW_ITEM_ID="abc123"
        case "$NEW_ITEM_ID" in
          ''|*[!0-9]*) echo "REJECTED"; exit 1 ;;
        esac
        echo "ACCEPTED"
        """
        result = _run_bash(script)
        assert result.returncode == 1
        assert "REJECTED" in result.stdout

    def test_new_item_id_numeric_guard_accepts_numeric(self):
        """The [!0-9] case guard must not exit 1 on a pure numeric input."""
        script = r"""
        NEW_ITEM_ID="42"
        case "$NEW_ITEM_ID" in
          ''|*[!0-9]*) echo "REJECTED"; exit 1 ;;
        esac
        echo "ACCEPTED"
        """
        result = _run_bash(script)
        assert result.returncode == 0
        assert "ACCEPTED" in result.stdout

    def test_new_item_id_numeric_guard_rejects_empty(self):
        """The [!0-9] case guard must exit 1 on empty string."""
        script = r"""
        NEW_ITEM_ID=""
        case "$NEW_ITEM_ID" in
          ''|*[!0-9]*) echo "REJECTED"; exit 1 ;;
        esac
        echo "ACCEPTED"
        """
        result = _run_bash(script)
        assert result.returncode == 1
        assert "REJECTED" in result.stdout
