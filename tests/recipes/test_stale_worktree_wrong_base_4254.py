#!/usr/bin/env python3
"""Regression test for issue #4254: step-04 reuses worktree created from wrong base.

When a recipe re-run targets the same issue but the upstream base branch has
advanced (e.g., new commits on main), the existing worktree contains stale
diffs from the old base.  The fix verifies that BASE_WORKTREE_REF is an
ancestor of the existing branch tip; if not, the worktree and branch are
removed and recreated from the correct base.

The fix is applied to both States 1 and 2 in:
  - default-workflow.yaml   step-04-setup-worktree
  - consensus-workflow.yaml step3-setup-worktree

Tests include:
  - Static YAML analysis (pattern presence)
  - Live git scenarios (correct recreation behaviour)

Run:
  python3 -m pytest tests/recipes/test_stale_worktree_wrong_base_4254.py -v
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_RECIPE = _REPO_ROOT / "amplifier-bundle" / "recipes" / "default-workflow.yaml"
_CONSENSUS_RECIPE = _REPO_ROOT / "amplifier-bundle" / "recipes" / "consensus-workflow.yaml"


class TestYAMLContainsBaseBranchCheck(unittest.TestCase):
    """Static analysis: verify recipe YAMLs contain the merge-base ancestry check."""

    @classmethod
    def setUpClass(cls):
        cls.default_yaml = _DEFAULT_RECIPE.read_text(encoding="utf-8")
        cls.consensus_yaml = _CONSENSUS_RECIPE.read_text(encoding="utf-8")

    def test_default_workflow_has_merge_base_check(self):
        self.assertIn(
            "merge-base --is-ancestor",
            self.default_yaml,
            "step-04 must verify base branch ancestry before reusing worktree",
        )

    def test_default_workflow_has_wrong_base_warn(self):
        self.assertIn(
            "different base",
            self.default_yaml,
            "step-04 must warn when base branch mismatch detected",
        )

    def test_default_workflow_recreates_on_mismatch(self):
        self.assertIn(
            "git branch -D",
            self.default_yaml,
            "step-04 must delete stale branch when base mismatch detected",
        )

    def test_consensus_workflow_has_merge_base_check(self):
        self.assertIn(
            "merge-base --is-ancestor",
            self.consensus_yaml,
            "consensus step3 must verify base branch ancestry",
        )

    def test_consensus_workflow_recreates_on_mismatch(self):
        self.assertIn(
            "git branch -D",
            self.consensus_yaml,
            "consensus step3 must delete stale branch on base mismatch",
        )

    def test_issue_4254_referenced(self):
        """Both recipes must reference the issue number for traceability."""
        self.assertIn("4254", self.default_yaml)
        self.assertIn("4254", self.consensus_yaml)


class TestLiveWorktreeBaseBranchVerification(unittest.TestCase):
    """Live git tests: verify stale worktrees are detected and recreated."""

    def setUp(self):
        """Create a temporary git repo with an initial commit and a 'main' branch."""
        self.tmpdir = tempfile.mkdtemp(prefix="test_4254_")
        self.repo = os.path.join(self.tmpdir, "repo")
        os.makedirs(self.repo)
        self._run("git init -b main")
        self._run("git commit --allow-empty -m 'initial commit'")
        self.initial_commit = self._run("git rev-parse HEAD").strip()

    def tearDown(self):
        # Clean up worktrees before removing tmpdir
        try:
            self._run("git worktree prune")
        except Exception:
            pass
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run(self, cmd, cwd=None):
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd or self.repo,
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "GIT_AUTHOR_NAME": "test",
                "GIT_AUTHOR_EMAIL": "t@t",
                "GIT_COMMITTER_NAME": "test",
                "GIT_COMMITTER_EMAIL": "t@t",
            },
        )
        if result.returncode != 0:
            raise RuntimeError(f"Command failed: {cmd}\nstderr: {result.stderr}")
        return result.stdout

    def test_worktree_reused_when_base_matches(self):
        """When the base branch hasn't changed, the existing worktree is reused."""
        wt_path = os.path.join(self.tmpdir, "wt1")
        branch = "feat/test-reuse"
        self._run(f"git worktree add {wt_path} -b {branch} HEAD")

        # Verify the branch tip has initial_commit as ancestor
        tip = self._run(f"git rev-parse {branch}").strip()
        result = subprocess.run(
            f"git merge-base --is-ancestor {self.initial_commit} {tip}",
            shell=True,
            cwd=self.repo,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, "Base should be ancestor of branch tip")

    def test_worktree_recreated_when_base_diverges(self):
        """When main advances past the branch's base, the worktree must be recreated."""
        wt_path = os.path.join(self.tmpdir, "wt2")
        branch = "feat/test-diverge"

        # Create worktree from initial commit
        self._run(f"git worktree add {wt_path} -b {branch} HEAD")
        old_tip = self._run(f"git rev-parse {branch}").strip()

        # Advance main with a new commit
        self._run("git commit --allow-empty -m 'advance main'")
        new_main = self._run("git rev-parse HEAD").strip()

        # Verify: new_main is NOT an ancestor of old branch tip (the stale case)
        result = subprocess.run(
            f"git merge-base --is-ancestor {new_main} {old_tip}",
            shell=True,
            cwd=self.repo,
            capture_output=True,
        )
        self.assertNotEqual(
            result.returncode, 0, "Advanced main should NOT be ancestor of old branch tip"
        )

        # Simulate the fix: remove stale worktree/branch, recreate from new base
        self._run(f"git worktree remove --force {wt_path}")
        self._run(f"git branch -D {branch}")
        self._run("git worktree prune")
        self._run(f"git worktree add {wt_path} -b {branch} HEAD")

        # Verify new branch tip has new_main as ancestor
        new_tip = self._run(f"git rev-parse {branch}").strip()
        result = subprocess.run(
            f"git merge-base --is-ancestor {new_main} {new_tip}",
            shell=True,
            cwd=self.repo,
            capture_output=True,
        )
        self.assertEqual(
            result.returncode, 0, "After recreation, new main should be ancestor of branch tip"
        )

    def test_state2_branch_only_wrong_base(self):
        """State 2: Branch exists without worktree, but was from wrong base."""
        wt_path = os.path.join(self.tmpdir, "wt3")
        branch = "feat/test-state2"

        # Create branch from initial commit
        self._run(f"git branch {branch}")

        # Advance main
        self._run("git commit --allow-empty -m 'advance for state2'")
        new_main = self._run("git rev-parse HEAD").strip()

        old_tip = self._run(f"git rev-parse {branch}").strip()

        # Verify mismatch
        result = subprocess.run(
            f"git merge-base --is-ancestor {new_main} {old_tip}",
            shell=True,
            cwd=self.repo,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0, "Should detect base mismatch")

        # Apply the fix: delete branch, recreate with worktree from new base
        self._run(f"git branch -D {branch}")
        self._run(f"git worktree add {wt_path} -b {branch} HEAD")

        new_tip = self._run(f"git rev-parse {branch}").strip()
        result = subprocess.run(
            f"git merge-base --is-ancestor {new_main} {new_tip}",
            shell=True,
            cwd=self.repo,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, "Recreated branch should have correct base")


if __name__ == "__main__":
    unittest.main()
