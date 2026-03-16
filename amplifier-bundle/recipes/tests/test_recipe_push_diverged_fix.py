# File: amplifier-bundle/recipes/tests/test_recipe_push_diverged_fix.py
"""
TDD tests for issue #3194: recipe runner push steps fail when remote has
diverged during multi-step workflow execution.

Fix: replace bare 'git push' with 'git pull --rebase ... && / ; git push'
in all push steps that occur AFTER the initial branch-tracking push.

Test structure
--------------
- TestDefaultWorkflowInitialPush        — invariant: initial push kept as-is
- TestDefaultWorkflowStep15CommitPush   — Pattern A: step-15 rev-list guard
- TestDefaultWorkflowStep16bOutsideIn   — Pattern B: step-16b agent prompt
- TestDefaultWorkflowStep18cFeedbackPush — Pattern A: step-18c feedback push
- TestDefaultWorkflowStep20bCleanupPush — Pattern A variant: step-20b subshell
- TestConsensusWorkflowStep9CommitPush  — Pattern C: step-9 commit + push
- TestConsensusWorkflowStep12PushUpdates — Pattern C: step-12 push-updates
- TestCrossWorkflowPatternConsistency   — global invariants across both files
- TestEdgeCases                         — force-push absent, YAML structure
"""
import re

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lines_containing(lines, fragment):
    """Return list of (1-based line number, text) for lines containing fragment."""
    return [(i + 1, line) for i, line in enumerate(lines) if fragment in line]


def _assert_no_bare_push(lines, context_description):
    """Assert no line is a bare 'git push' (without -u origin or pull --rebase prefix)."""
    bare_push_pattern = re.compile(r"^\s*git push\s*$")
    violations = [(i + 1, line) for i, line in enumerate(lines) if bare_push_pattern.match(line)]
    assert violations == [], (
        f"{context_description}: found bare 'git push' lines: {violations}"
    )


# ===========================================================================
# TestDefaultWorkflowInitialPush
# ===========================================================================

class TestDefaultWorkflowInitialPush:
    """The initial branch-tracking push must NOT be modified (no divergence possible)."""

    def test_initial_push_uses_u_origin(self, default_workflow_content):
        assert "git push -u origin" in default_workflow_content, (
            "default-workflow.yaml: initial 'git push -u origin' must be present"
        )

    def test_initial_push_not_prefixed_with_pull_rebase(self, default_workflow_lines):
        u_push_lines = _lines_containing(default_workflow_lines, "git push -u origin")
        assert len(u_push_lines) >= 1, "Must have at least one 'git push -u origin' line"
        for lineno, line in u_push_lines:
            assert "pull --rebase" not in line, (
                f"Line {lineno}: initial push must not be prefixed with pull --rebase: {line!r}"
            )


# ===========================================================================
# TestDefaultWorkflowStep15CommitPush  (Pattern A)
# ===========================================================================

class TestDefaultWorkflowStep15CommitPush:
    """Step 15 (commit and push) inside rev-list guard uses Pattern A."""

    def test_step15_has_rev_list_guard(self, default_workflow_content):
        assert "rev-list --count @{u}..HEAD" in default_workflow_content, (
            "Step 15 must use rev-list guard before push"
        )

    def test_step15_push_has_pull_rebase_prefix(self, default_workflow_content):
        # Pattern A: the push inside the rev-list guard must be prefixed
        pattern = re.compile(
            r"git pull --rebase 2>/dev/null\s*;\s*git push\s*;"
        )
        assert pattern.search(default_workflow_content), (
            "default-workflow.yaml step 15: push inside rev-list guard must use "
            "'git pull --rebase 2>/dev/null ; git push ;' (Pattern A)"
        )

    def test_step15_no_bare_push_in_guard_block(self, default_workflow_lines):
        # Find lines inside rev-list guard context; bare 'git push ;' without rebase is forbidden
        bare = re.compile(r"^\s*git push\s*;\s*\\?\s*$")
        violations = [(i + 1, l) for i, l in enumerate(default_workflow_lines) if bare.match(l)]
        assert violations == [], (
            f"Found bare 'git push ;' lines (should be preceded by pull --rebase): {violations}"
        )

    def test_step15_commit_and_push_complete_message_present(self, default_workflow_content):
        assert "Commit and Push Complete" in default_workflow_content, (
            "Step 15 completion message must remain after fix"
        )


# ===========================================================================
# TestDefaultWorkflowStep16bOutsideIn  (Pattern B)
# ===========================================================================

class TestDefaultWorkflowStep16bOutsideIn:
    """Step 16b outside-in fix loop agent prompt uses Pattern B (&&)."""

    def test_step16b_agent_prompt_has_pull_rebase_and(self, default_workflow_content):
        assert "git pull --rebase && git push" in default_workflow_content, (
            "default-workflow.yaml step 16b agent prompt must contain "
            "'git pull --rebase && git push' (Pattern B)"
        )

    def test_step16b_agent_prompt_no_bare_push_after_commit(self, default_workflow_lines):
        # In agent prompt markdown blocks the pattern must be 'git pull --rebase && git push'
        # No line should be just 'git push' in a markdown code block
        in_code_block = False
        for i, line in enumerate(default_workflow_lines):
            stripped = line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
            if in_code_block and re.match(r"^git push\s*$", stripped):
                pytest.fail(
                    f"Line {i + 1}: bare 'git push' found in markdown code block — "
                    f"should be 'git pull --rebase && git push': {line!r}"
                )

    def test_step16b_commit_message_template_present(self, default_workflow_content):
        assert "fix: <describe the fix found during outside-in testing>" in default_workflow_content, (
            "Step 16b commit message template must remain unchanged"
        )


# ===========================================================================
# TestDefaultWorkflowStep18cFeedbackPush  (Pattern A)
# ===========================================================================

class TestDefaultWorkflowStep18cFeedbackPush:
    """Step 18c (push feedback changes) uses Pattern A — the primary failure point."""

    def test_step18c_output_key_present(self, default_workflow_content):
        assert "feedback_push_result" in default_workflow_content, (
            "Step 18c output key 'feedback_push_result' must be present"
        )

    def test_step18c_push_has_pull_rebase_prefix(self, default_workflow_content):
        # The push associated with 'feedback_push_result' must be Pattern A
        # Verify the content block around feedback_push_result contains pull --rebase
        idx = default_workflow_content.find("feedback_push_result")
        assert idx != -1, "feedback_push_result output key not found"
        # Look backwards ~500 chars for the push command
        block = default_workflow_content[max(0, idx - 500):idx]
        assert "git pull --rebase" in block, (
            "Step 18c: push before 'feedback_push_result' output must have "
            "'git pull --rebase' prefix"
        )

    def test_step18c_push_complete_message_present(self, default_workflow_content):
        assert "Changes Pushed" in default_workflow_content, (
            "Step 18c completion message must remain after fix"
        )

    def test_step18c_feedback_warning_message_present(self, default_workflow_content):
        assert "Nothing to push - branch is up to date with remote" in default_workflow_content, (
            "Step 18c warning message must remain unchanged"
        )


# ===========================================================================
# TestDefaultWorkflowStep20bCleanupPush  (Pattern A variant)
# ===========================================================================

class TestDefaultWorkflowStep20bCleanupPush:
    """Step 20b final cleanup uses Pattern A variant inside subshell."""

    def test_step20b_output_key_present(self, default_workflow_content):
        assert "cleanup_push_result" in default_workflow_content, (
            "Step 20b output key 'cleanup_push_result' must be present"
        )

    def test_step20b_push_has_pull_rebase_prefix(self, default_workflow_content):
        idx = default_workflow_content.find("cleanup_push_result")
        assert idx != -1, "cleanup_push_result output key not found"
        block = default_workflow_content[max(0, idx - 400):idx]
        assert "git pull --rebase" in block, (
            "Step 20b: cleanup subshell push must have 'git pull --rebase' prefix"
        )

    def test_step20b_commit_message_present(self, default_workflow_content):
        assert "final cleanup pass" in default_workflow_content, (
            "Step 20b commit message 'final cleanup pass' must remain unchanged"
        )

    def test_step20b_cleanup_complete_message_present(self, default_workflow_content):
        assert "Cleanup Complete" in default_workflow_content, (
            "Step 20b 'Cleanup Complete' message must remain after fix"
        )


# ===========================================================================
# TestConsensusWorkflowStep9CommitPush  (Pattern C)
# ===========================================================================

class TestConsensusWorkflowStep9CommitPush:
    """Consensus workflow step 9 (commit + push) uses Pattern C."""

    def test_consensus_initial_push_uses_u_origin(self, consensus_workflow_content):
        assert "git push -u origin" in consensus_workflow_content, (
            "consensus-workflow.yaml: initial 'git push -u origin' must be present"
        )

    def test_step9_push_has_pull_rebase_prefix(self, consensus_workflow_content):
        # The "Push prepared" fallback line must be preceded by pull --rebase
        idx = consensus_workflow_content.find('echo "Push prepared"')
        assert idx != -1, "Step 9 'Push prepared' fallback not found"
        block = consensus_workflow_content[max(0, idx - 200):idx]
        assert "git pull --rebase" in block, (
            "consensus-workflow.yaml step 9: push must be prefixed with 'git pull --rebase'"
        )

    def test_step9_push_preserves_error_suppression(self, consensus_workflow_content):
        assert "git pull --rebase 2>/dev/null ; git push 2>/dev/null || echo" in consensus_workflow_content, (
            "consensus-workflow.yaml step 9: Pattern C must preserve '2>/dev/null' and "
            "'|| echo' fallback exactly"
        )

    def test_step9_commit_result_output_key_present(self, consensus_workflow_content):
        assert "commit_result" in consensus_workflow_content, (
            "consensus-workflow.yaml step 9 output key 'commit_result' must be present"
        )


# ===========================================================================
# TestConsensusWorkflowStep12PushUpdates  (Pattern C)
# ===========================================================================

class TestConsensusWorkflowStep12PushUpdates:
    """Consensus workflow step 12 (push review updates) uses Pattern C."""

    def test_step12_output_key_present(self, consensus_workflow_content):
        assert "review_updates" in consensus_workflow_content, (
            "consensus-workflow.yaml step 12 output key 'review_updates' must be present"
        )

    def test_step12_push_has_pull_rebase_prefix(self, consensus_workflow_content):
        idx = consensus_workflow_content.find("review_updates")
        assert idx != -1, "review_updates output key not found"
        block = consensus_workflow_content[max(0, idx - 400):idx]
        assert "git pull --rebase" in block, (
            "consensus-workflow.yaml step 12: push must be prefixed with 'git pull --rebase'"
        )

    def test_step12_preserves_or_true_fallback(self, consensus_workflow_content):
        assert "git pull --rebase 2>/dev/null ; git push 2>/dev/null || true" in consensus_workflow_content, (
            "consensus-workflow.yaml step 12: Pattern C must preserve '|| true' fallback"
        )

    def test_step12_commit_message_present(self, consensus_workflow_content):
        assert "Address PR review feedback" in consensus_workflow_content, (
            "Step 12 commit message must remain unchanged"
        )


# ===========================================================================
# TestCrossWorkflowPatternConsistency
# ===========================================================================

class TestCrossWorkflowPatternConsistency:
    """Global invariants: no bare git push anywhere in either file."""

    def test_default_workflow_no_bare_git_push(self, default_workflow_lines):
        bare = re.compile(r"^\s*git push\s*$")
        violations = [(i + 1, l) for i, l in enumerate(default_workflow_lines) if bare.match(l)]
        assert violations == [], (
            f"default-workflow.yaml: bare 'git push' lines remain unfixed: {violations}"
        )

    def test_consensus_workflow_no_bare_git_push(self, consensus_workflow_lines):
        bare = re.compile(r"^\s*git push\s*$")
        violations = [(i + 1, l) for i, l in enumerate(consensus_workflow_lines) if bare.match(l)]
        assert violations == [], (
            f"consensus-workflow.yaml: bare 'git push' lines remain unfixed: {violations}"
        )

    def test_default_workflow_exactly_one_initial_push(self, default_workflow_lines):
        initial = _lines_containing(default_workflow_lines, "git push -u origin")
        assert len(initial) == 1, (
            f"default-workflow.yaml: expected exactly 1 'git push -u origin' line, "
            f"found {len(initial)}: {initial}"
        )

    def test_consensus_workflow_exactly_one_initial_push(self, consensus_workflow_lines):
        initial = _lines_containing(consensus_workflow_lines, "git push -u origin")
        assert len(initial) == 1, (
            f"consensus-workflow.yaml: expected exactly 1 'git push -u origin' line, "
            f"found {len(initial)}: {initial}"
        )

    def test_default_workflow_pull_rebase_count_matches_subsequent_pushes(
        self, default_workflow_content
    ):
        # 4 subsequent push locations need pull --rebase (steps 15, 16b, 18c, 20b)
        count = default_workflow_content.count("git pull --rebase")
        assert count == 4, (
            f"default-workflow.yaml: expected 4 'git pull --rebase' occurrences "
            f"(steps 15, 16b, 18c, 20b), found {count}"
        )

    def test_consensus_workflow_pull_rebase_count_matches_subsequent_pushes(
        self, consensus_workflow_content
    ):
        # 2 subsequent push locations need pull --rebase (steps 9, 12)
        count = consensus_workflow_content.count("git pull --rebase")
        assert count == 2, (
            f"consensus-workflow.yaml: expected 2 'git pull --rebase' occurrences "
            f"(steps 9, 12), found {count}"
        )


# ===========================================================================
# TestEdgeCases
# ===========================================================================

class TestEdgeCases:
    """Edge case guards: no force-push, correct separators, YAML syntax."""

    def test_default_workflow_no_force_push(self, default_workflow_content):
        assert "git push --force" not in default_workflow_content, (
            "default-workflow.yaml must not contain 'git push --force'"
        )
        assert "git push -f " not in default_workflow_content, (
            "default-workflow.yaml must not contain 'git push -f'"
        )

    def test_consensus_workflow_no_force_push(self, consensus_workflow_content):
        assert "git push --force" not in consensus_workflow_content, (
            "consensus-workflow.yaml must not contain 'git push --force'"
        )
        assert "git push -f " not in consensus_workflow_content, (
            "consensus-workflow.yaml must not contain 'git push -f'"
        )

    def test_agent_prompt_push_uses_double_ampersand(self, default_workflow_content):
        # Pattern B: agent prompts must use && (not ;) so push is skipped if rebase fails
        assert "git pull --rebase && git push" in default_workflow_content, (
            "Agent prompt push must use '&&' separator (Pattern B)"
        )

    def test_bash_guard_push_uses_semicolon_separator(self, default_workflow_content):
        # Pattern A: bash rev-list guard uses ; so push runs even if nothing to rebase
        assert "git pull --rebase 2>/dev/null ; git push ;" in default_workflow_content, (
            "Bash guard push must use ';' separator (Pattern A)"
        )

    def test_consensus_pattern_c_semicolon_before_push(self, consensus_workflow_content):
        # Pattern C: must use ; to separate pull from push
        assert "git pull --rebase 2>/dev/null ; git push 2>/dev/null" in consensus_workflow_content, (
            "consensus-workflow.yaml Pattern C must use ';' separator between pull and push"
        )

    def test_default_workflow_is_valid_yaml(self, default_workflow_path):
        try:
            import yaml  # type: ignore
        except ImportError:
            pytest.skip("PyYAML not installed; skipping YAML syntax validation")
        with open(default_workflow_path, encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
        assert docs, "default-workflow.yaml must parse as valid YAML"

    def test_consensus_workflow_is_valid_yaml(self, consensus_workflow_path):
        try:
            import yaml  # type: ignore
        except ImportError:
            pytest.skip("PyYAML not installed; skipping YAML syntax validation")
        with open(consensus_workflow_path, encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
        assert docs, "consensus-workflow.yaml must parse as valid YAML"

    def test_default_workflow_file_exists(self, default_workflow_path):
        assert default_workflow_path.exists(), (
            f"default-workflow.yaml not found at {default_workflow_path}"
        )

    def test_consensus_workflow_file_exists(self, consensus_workflow_path):
        assert consensus_workflow_path.exists(), (
            f"consensus-workflow.yaml not found at {consensus_workflow_path}"
        )
