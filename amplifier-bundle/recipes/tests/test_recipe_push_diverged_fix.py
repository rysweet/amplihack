# File: amplifier-bundle/recipes/tests/test_recipe_push_diverged_fix.py
"""
Tests for issue #3194: recipe runner push steps fail when remote has diverged.

Fix: replace bare 'git push' with 'git pull --rebase ... && / ; git push'
in all push steps that occur AFTER the initial branch-tracking push.

Coverage:
- Initial push (-u origin) untouched
- Each of the 4 fixed push sites in default-workflow.yaml
- Each of the 2 fixed push sites in consensus-workflow.yaml
- Global: no bare 'git push' anywhere in either file
- Global: exact count of 'git pull --rebase' occurrences
- Pattern correctness: separators (&&, ;) and error suppression preserved
- YAML syntax validity for both files
"""
import re

import pytest


# ===========================================================================
# Initial push guard — must stay as-is (no rebase possible before first push)
# ===========================================================================

class TestInitialPush:
    def test_default_initial_push_unchanged(self, default_workflow_lines):
        lines = [l for l in default_workflow_lines if "git push -u origin" in l]
        assert len(lines) == 1, f"expected exactly 1 'git push -u origin', got {len(lines)}: {lines}"
        assert "pull --rebase" not in lines[0]

    def test_consensus_initial_push_unchanged(self, consensus_workflow_lines):
        lines = [l for l in consensus_workflow_lines if "git push -u origin" in l]
        assert len(lines) == 1, f"expected exactly 1 'git push -u origin', got {len(lines)}: {lines}"
        assert "pull --rebase" not in lines[0]


# ===========================================================================
# default-workflow.yaml — per-site fix verification
# ===========================================================================

class TestDefaultWorkflowFixes:
    """Each fixed push site uses the correct pattern."""

    def test_step15_pattern_a(self, default_workflow_content):
        # Pattern A: bash rev-list guard — semicolon separator, stderr suppressed
        assert re.search(r"git pull --rebase 2>/dev/null\s*;\s*git push\s*;", default_workflow_content), (
            "step 15: must match 'git pull --rebase 2>/dev/null ; git push ;' (Pattern A)"
        )

    def test_step16b_pattern_b(self, default_workflow_content):
        # Pattern B: agent prompt — && so push is skipped if rebase fails
        assert "git pull --rebase && git push" in default_workflow_content, (
            "step 16b: agent prompt must use 'git pull --rebase && git push' (Pattern B)"
        )

    def test_step18c_pattern_a(self, default_workflow_content):
        # feedback_push_result block must be preceded within 500 chars by pull --rebase
        idx = default_workflow_content.find("feedback_push_result")
        assert idx != -1, "feedback_push_result output key not found"
        assert "git pull --rebase" in default_workflow_content[max(0, idx - 500):idx], (
            "step 18c: push before feedback_push_result must be prefixed with pull --rebase"
        )

    def test_step20b_pattern_a(self, default_workflow_content):
        # cleanup_push_result block must be preceded within 400 chars by pull --rebase
        idx = default_workflow_content.find("cleanup_push_result")
        assert idx != -1, "cleanup_push_result output key not found"
        assert "git pull --rebase" in default_workflow_content[max(0, idx - 400):idx], (
            "step 20b: cleanup subshell push must be prefixed with pull --rebase"
        )


# ===========================================================================
# consensus-workflow.yaml — per-site fix verification
# ===========================================================================

class TestConsensusWorkflowFixes:
    """Each fixed push site uses Pattern C (semicolon, 2>/dev/null preserved)."""

    def test_step9_pattern_c(self, consensus_workflow_content):
        assert "git pull --rebase 2>/dev/null ; git push 2>/dev/null || echo" in consensus_workflow_content, (
            "step 9: must match Pattern C with '2>/dev/null' and '|| echo' fallback"
        )

    def test_step12_pattern_c(self, consensus_workflow_content):
        assert "git pull --rebase 2>/dev/null ; git push 2>/dev/null || true" in consensus_workflow_content, (
            "step 12: must match Pattern C with '2>/dev/null' and '|| true' fallback"
        )


# ===========================================================================
# Global invariants
# ===========================================================================

class TestGlobalInvariants:
    """No bare push anywhere; pull --rebase count matches expected fix sites."""

    def test_default_no_bare_git_push(self, default_workflow_lines):
        bare = re.compile(r"^\s*git push\s*$")
        violations = [(i + 1, l) for i, l in enumerate(default_workflow_lines) if bare.match(l)]
        assert violations == [], f"default-workflow.yaml: bare 'git push' lines: {violations}"

    def test_consensus_no_bare_git_push(self, consensus_workflow_lines):
        bare = re.compile(r"^\s*git push\s*$")
        violations = [(i + 1, l) for i, l in enumerate(consensus_workflow_lines) if bare.match(l)]
        assert violations == [], f"consensus-workflow.yaml: bare 'git push' lines: {violations}"

    def test_default_pull_rebase_count(self, default_workflow_content):
        count = default_workflow_content.count("git pull --rebase")
        assert count == 4, (
            f"default-workflow.yaml: expected 4 'git pull --rebase' occurrences "
            f"(steps 15, 16b, 18c, 20b), found {count}"
        )

    def test_consensus_pull_rebase_count(self, consensus_workflow_content):
        count = consensus_workflow_content.count("git pull --rebase")
        assert count == 2, (
            f"consensus-workflow.yaml: expected 2 'git pull --rebase' occurrences "
            f"(steps 9, 12), found {count}"
        )

    def test_default_no_force_push(self, default_workflow_content):
        assert "git push --force" not in default_workflow_content
        assert "git push -f " not in default_workflow_content

    def test_consensus_no_force_push(self, consensus_workflow_content):
        assert "git push --force" not in consensus_workflow_content
        assert "git push -f " not in consensus_workflow_content


# ===========================================================================
# YAML validity
# ===========================================================================

class TestYamlValidity:
    def test_default_workflow_is_valid_yaml(self, default_workflow_path):
        try:
            import yaml  # type: ignore
        except ImportError:
            pytest.skip("PyYAML not installed")
        docs = list(yaml.safe_load_all(default_workflow_path.open(encoding="utf-8")))
        assert docs

    def test_consensus_workflow_is_valid_yaml(self, consensus_workflow_path):
        try:
            import yaml  # type: ignore
        except ImportError:
            pytest.skip("PyYAML not installed")
        docs = list(yaml.safe_load_all(consensus_workflow_path.open(encoding="utf-8")))
        assert docs
