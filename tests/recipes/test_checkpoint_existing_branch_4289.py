#!/usr/bin/env python3
"""Regression test for issue #4289: step-04-setup-worktree fails on existing branch.

The three-state idempotency guard in step-04 missed two scenarios:
  - Orphaned worktree directories (directory exists but git doesn't track it)
  - Stale worktree references from crashed/interrupted runs

Fix adds `git worktree prune` before state detection and orphaned directory
cleanup before `git worktree add` in States 2 and 3.

Tests verify both the YAML content (static analysis) and live git behaviour.

Run:
  python3 -m pytest tests/recipes/test_checkpoint_existing_branch_4289.py -v
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RECIPE = _REPO_ROOT / "amplifier-bundle" / "recipes" / "default-workflow.yaml"
_CONSENSUS = _REPO_ROOT / "amplifier-bundle" / "recipes" / "consensus-workflow.yaml"


class TestRecipeYAMLContent(unittest.TestCase):
    """Static analysis: verify the recipe YAML contains the idempotency fix."""

    @classmethod
    def setUpClass(cls):
        cls.yaml_text = _RECIPE.read_text(encoding="utf-8")

    def test_has_worktree_prune(self):
        """step-04 must call git worktree prune before state detection."""
        self.assertIn(
            "git worktree prune",
            self.yaml_text,
            "step-04 must prune stale worktree refs before state detection",
        )

    def test_has_orphaned_directory_cleanup_state2(self):
        """State 2 must remove orphaned worktree directories."""
        match = re.search(
            r'elif \[ -n "\$BRANCH_EXISTS" \].*?else',
            self.yaml_text,
            re.DOTALL,
        )
        self.assertIsNotNone(match, "State 2 block must exist")
        state2 = match.group(0)
        self.assertIn(
            'rm -rf "${WORKTREE_PATH}"',
            state2,
            "State 2 must remove orphaned worktree directory",
        )

    def test_has_orphaned_directory_cleanup_state3(self):
        """State 3 must remove orphaned worktree directories."""
        match = re.search(
            r'else\s*\n\s*echo "INFO: Creating new branch',
            self.yaml_text,
        )
        self.assertIsNotNone(match, "State 3 block must exist")
        state3_start = match.start()
        state3_end = self.yaml_text.find("\n      fi", state3_start)
        state3 = self.yaml_text[state3_start:state3_end]
        self.assertIn(
            'rm -rf "${WORKTREE_PATH}"',
            state3,
            "State 3 must remove orphaned worktree directory",
        )

    def test_issue_4289_referenced_in_comment(self):
        """The fix must reference issue #4289 in comments."""
        self.assertIn("4289", self.yaml_text)

    def test_three_state_guard_intact(self):
        """All three states of the idempotency guard must exist."""
        self.assertIn('BRANCH_EXISTS=$(git branch --list', self.yaml_text)
        self.assertIn('WORKTREE_EXISTS=$(git worktree list --porcelain', self.yaml_text)
        self.assertRegex(
            self.yaml_text,
            r'if \[ -n "\$BRANCH_EXISTS" \] && \[ -n "\$WORKTREE_EXISTS" \]',
        )
        self.assertRegex(
            self.yaml_text,
            r'elif \[ -n "\$BRANCH_EXISTS" \] && \[ -z "\$WORKTREE_EXISTS" \]',
        )


class TestConsensusWorkflowYAMLContent(unittest.TestCase):
    """Verify consensus-workflow.yaml also has the fix."""

    @classmethod
    def setUpClass(cls):
        cls.yaml_text = _CONSENSUS.read_text(encoding="utf-8")

    def test_has_worktree_prune(self):
        self.assertIn("git worktree prune", self.yaml_text)

    def test_has_orphaned_directory_cleanup(self):
        self.assertIn("rm -rf", self.yaml_text)


class TestStep04IdempotencyLive(unittest.TestCase):
    """Live git tests for the three-state guard including orphaned directory handling."""

    _GUARD_SCRIPT = """\
set -euo pipefail
cd {repo_path!r}

BRANCH_NAME={branch_name!r}
WORKTREE_PATH={worktree_path!r}

git worktree prune >&2

BRANCH_EXISTS=$(git branch --list "$BRANCH_NAME")
WORKTREE_EXISTS=$(git worktree list --porcelain | grep -Fx "worktree $WORKTREE_PATH" || true)

if [ -n "$BRANCH_EXISTS" ] && [ -n "$WORKTREE_EXISTS" ]; then
  CREATED=false
elif [ -n "$BRANCH_EXISTS" ] && [ -z "$WORKTREE_EXISTS" ]; then
  if [ -d "$WORKTREE_PATH" ]; then
    rm -rf "$WORKTREE_PATH"
  fi
  git worktree add "$WORKTREE_PATH" "$BRANCH_NAME" >&2
  CREATED=true
else
  if [ -d "$WORKTREE_PATH" ]; then
    rm -rf "$WORKTREE_PATH"
  fi
  git worktree add "$WORKTREE_PATH" -b "$BRANCH_NAME" origin/main >&2
  CREATED=true
fi

printf '{{"worktree_path":"%s","branch_name":"%s","created":%s}}\\n' \
  "$WORKTREE_PATH" "$BRANCH_NAME" "$CREATED"
"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="test_4289_")
        self.repo_dir = os.path.join(self.tmpdir, "repo")
        os.makedirs(self.repo_dir)
        self._init_repo()
        self.branch_name = "feat/issue-4289-test"
        self.worktree_path = os.path.join(
            self.repo_dir, "worktrees", self.branch_name
        )

    def tearDown(self):
        subprocess.run(
            ["git", "worktree", "prune"],
            cwd=self.repo_dir,
            capture_output=True,
        )
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _init_repo(self):
        self._git("init")
        self._git("config", "user.email", "test@test.com")
        self._git("config", "user.name", "Test")
        Path(os.path.join(self.repo_dir, "README.md")).write_text("init\n")
        self._git("add", "README.md")
        self._git("commit", "-m", "Initial commit")
        self._git("update-ref", "refs/remotes/origin/main", "HEAD")

    def _git(self, *args):
        return subprocess.run(
            ["git"] + list(args),
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
            check=True,
        )

    def _run_guard(self) -> dict:
        script = self._GUARD_SCRIPT.format(
            repo_path=self.repo_dir,
            branch_name=self.branch_name,
            worktree_path=self.worktree_path,
        )
        result = subprocess.run(
            ["bash", "-c", script], capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Guard failed (rc={result.returncode}): {result.stderr}"
            )
        return json.loads(result.stdout.strip())

    def test_state3_fresh_create(self):
        """State 3: fresh repo - create branch and worktree."""
        output = self._run_guard()
        self.assertTrue(output["created"])
        self.assertTrue(os.path.isdir(self.worktree_path))

    def test_state1_both_exist_reuse(self):
        """State 1: both exist - reuse, created=false."""
        self._run_guard()
        output = self._run_guard()
        self.assertFalse(output["created"])

    def test_state2_branch_only(self):
        """State 2: branch exists, worktree removed - re-add."""
        self._run_guard()
        subprocess.run(
            ["git", "worktree", "remove", "--force", self.worktree_path],
            cwd=self.repo_dir,
            capture_output=True,
        )
        output = self._run_guard()
        self.assertTrue(output["created"])
        self.assertTrue(os.path.isdir(self.worktree_path))

    def test_state2_with_orphaned_directory(self):
        """State 2 + orphan: branch exists, worktree removed from git but dir remains.

        This is the core regression for issue #4289: after a recovery run,
        the worktree directory may exist on disk but git doesn't track it.
        Without the orphan cleanup, git worktree add fails because the
        directory already exists.
        """
        self._run_guard()
        subprocess.run(
            ["git", "worktree", "remove", "--force", self.worktree_path],
            cwd=self.repo_dir,
            capture_output=True,
        )
        os.makedirs(self.worktree_path, exist_ok=True)
        Path(os.path.join(self.worktree_path, "orphan.txt")).write_text("stale")
        output = self._run_guard()
        self.assertTrue(output["created"])
        self.assertTrue(os.path.isdir(self.worktree_path))

    def test_state3_with_orphaned_directory(self):
        """State 3 + orphan: no branch, no worktree in git, but directory exists."""
        os.makedirs(self.worktree_path, exist_ok=True)
        Path(os.path.join(self.worktree_path, "orphan.txt")).write_text("stale")
        output = self._run_guard()
        self.assertTrue(output["created"])
        self.assertTrue(os.path.isdir(self.worktree_path))

    def test_second_run_exits_zero(self):
        """Regression: second run must exit 0, not fail."""
        self._run_guard()
        output = self._run_guard()
        self.assertFalse(output["created"])

    def test_worktree_prune_cleans_stale_refs(self):
        """git worktree prune removes stale references before state detection."""
        self._run_guard()
        shutil.rmtree(self.worktree_path)
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=self.repo_dir,
            capture_output=True,
            text=True,
        )
        self.assertIn(self.worktree_path, result.stdout)
        output = self._run_guard()
        self.assertTrue(output["created"])


if __name__ == "__main__":
    unittest.main()
