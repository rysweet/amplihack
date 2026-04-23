#!/usr/bin/env python3
"""Regression test for issue #4394: re-prune after rm -rf of orphan worktree dirs.

When a worktree directory is deleted out-of-band (rm -rf, cleanup script,
interrupted run), git's internal .git/worktrees/<name> registration survives.
A subsequent `git worktree add` for the same path fails with:

    fatal: '<path>' is a missing but already registered worktree;
    use 'add -f' to override, or 'prune' or 'remove' to clear

The fix inserts `git worktree prune` immediately after every `rm -rf`
of orphan directories in step-04-setup-worktree, for both State 2
(branch exists, worktree missing) and State 3 (new branch, orphan dir).

Tests include:
  - Static YAML analysis (prune-after-rm-rf pattern present in both states)
  - Live git scenarios (prune enables successful re-add after rm -rf)
  - Edge cases (no stale registration, concurrent worktree operations)

Run:
  python3 -m pytest tests/recipes/test_worktree_reattach_prune_4394.py -v
"""

import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_RECIPE = _REPO_ROOT / "amplifier-bundle" / "recipes" / "default-workflow.yaml"

# Cached env dict — avoids copying os.environ on every subprocess call
_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "test",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "test",
    "GIT_COMMITTER_EMAIL": "t@t",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _git(cmd: str, cwd: str) -> subprocess.CompletedProcess:
    """Run a git command in a temp repo with deterministic author config."""
    return subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
        env=_GIT_ENV,
    )


def _git_ok(cmd: str, cwd: str) -> str:
    """Run a git command, assert success, return stdout."""
    r = _git(cmd, cwd)
    if r.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\nstderr: {r.stderr}")
    return r.stdout


# ===========================================================================
# Part 1: Static YAML Analysis
# ===========================================================================


class TestYAMLPruneAfterRmRf(unittest.TestCase):
    """Verify default-workflow.yaml contains prune calls after rm -rf in both states."""

    @classmethod
    def setUpClass(cls):
        if not _DEFAULT_RECIPE.exists():
            raise unittest.SkipTest("default-workflow.yaml not found")
        cls.yaml_text = _DEFAULT_RECIPE.read_text(encoding="utf-8")

    def test_state2_has_prune_after_rm_rf(self):
        """State 2 (branch exists, worktree missing): prune must follow rm -rf."""
        # The State 2 block contains 'Removing orphaned worktree directory'
        # followed by rm -rf and then git worktree prune.
        # Use a relaxed pattern: rm -rf ... followed by worktree prune within ~5 lines.
        state2_pattern = re.compile(
            r'rm -rf "\$\{WORKTREE_PATH\}".*?git worktree prune',
            re.DOTALL,
        )
        matches = list(state2_pattern.finditer(self.yaml_text))
        self.assertGreaterEqual(
            len(matches),
            2,
            "Expected at least 2 'rm -rf → prune' sequences (State 2 and State 3)",
        )

    def test_state3_has_prune_after_rm_rf(self):
        """State 3 (new branch, orphan dir): prune must follow rm -rf."""
        # State 3 marker is "Creating new branch and worktree." (no "from correct base")
        # The exact string distinguishes it from the wrong-base recreation path.
        state3_marker = 'Creating new branch and worktree."'
        idx = self.yaml_text.find(state3_marker)
        self.assertNotEqual(idx, -1, "State 3 marker not found in YAML")

        state3_block = self.yaml_text[idx : idx + 500]
        self.assertIn("rm -rf", state3_block, "State 3 must rm -rf orphan dir")
        self.assertIn(
            "git worktree prune",
            state3_block,
            "State 3 must prune after rm -rf",
        )

    def test_prune_comment_documents_reason(self):
        """Each post-rm-rf prune should have an explanatory comment."""
        self.assertIn(
            "Re-prune in case the path is still registered",
            self.yaml_text,
            "Post-rm-rf prune calls should be documented with a comment",
        )

    def test_issue_4394_fix_does_not_use_force_flag(self):
        """The fix uses prune, NOT --force flag on worktree add."""
        # Within the rm-rf + prune blocks, worktree add should not use -f/--force
        # (except the wrong-base-branch removal which uses `remove --force`)
        state2_start = self.yaml_text.find("Branch '${BRANCH_NAME}' exists but worktree is missing")
        state3_end = self.yaml_text.find("CREATED=true", state2_start + 100)
        if state2_start != -1 and state3_end != -1:
            block = self.yaml_text[state2_start:state3_end]
            # git worktree add -f or --force should NOT appear
            force_pattern = re.compile(r"git worktree add\s+.*(-f|--force)")
            match = force_pattern.search(block)
            self.assertIsNone(
                match,
                "Fix should use 'prune' not '--force' for worktree add",
            )

    def test_total_prune_count(self):
        """step-04 should have at least 4 prune points (doc says exactly 4)."""
        count = self.yaml_text.count("git worktree prune")
        self.assertGreaterEqual(
            count,
            4,
            f"Expected >= 4 prune calls in step-04, found {count}",
        )


# ===========================================================================
# Part 2: Live Git Scenarios
# ===========================================================================


class TestLivePruneAfterOrphanCleanup(unittest.TestCase):
    """Live git tests: verify prune enables worktree add after rm -rf."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp(prefix="test_4394_")
        cls.repo = os.path.join(cls.tmpdir, "repo")
        os.makedirs(cls.repo)
        _git_ok("git init -b main", cls.repo)
        _git_ok("git commit --allow-empty -m 'initial'", cls.repo)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def tearDown(self):
        _git("git worktree prune", self.repo)

    # --- State 2: branch exists, worktree removed by rm -rf ---

    def test_state2_rm_rf_then_prune_allows_readd(self):
        """State 2: After rm -rf of worktree dir, prune enables worktree add."""
        wt_path = os.path.join(self.tmpdir, "wt-state2")
        branch = "feat/state2-prune"

        # Create worktree normally
        _git_ok(f"git worktree add {wt_path} -b {branch} HEAD", self.repo)
        self.assertTrue(os.path.isdir(wt_path))

        # Simulate out-of-band deletion (cleanup script, interrupted run)
        shutil.rmtree(wt_path)
        self.assertFalse(os.path.isdir(wt_path))

        # Without prune, worktree add should fail
        r = _git(f"git worktree add {wt_path} {branch}", self.repo)
        self.assertNotEqual(
            r.returncode,
            0,
            "git worktree add should fail when stale registration exists",
        )
        self.assertIn("already registered", r.stderr)

        # Apply the fix: prune then add
        _git_ok("git worktree prune", self.repo)
        _git_ok(f"git worktree add {wt_path} {branch}", self.repo)
        self.assertTrue(os.path.isdir(wt_path), "Worktree should exist after prune + add")

    def test_state2_rm_rf_without_prune_fails(self):
        """Confirm the bug: rm -rf alone leaves stale registration that blocks add."""
        wt_path = os.path.join(self.tmpdir, "wt-noproune")
        branch = "feat/no-prune"

        _git_ok(f"git worktree add {wt_path} -b {branch} HEAD", self.repo)
        shutil.rmtree(wt_path)

        r = _git(f"git worktree add {wt_path} {branch}", self.repo)
        self.assertNotEqual(r.returncode, 0, "Without prune, add must fail")
        self.assertIn("already registered", r.stderr)

    # --- State 3: new branch, orphan directory present ---

    def test_state3_orphan_dir_prune_allows_new_branch(self):
        """State 3: Stale path registration blocks new branch worktree add."""
        wt_path = os.path.join(self.tmpdir, "wt-state3")
        branch = "feat/state3-new"

        # Create a worktree at wt_path, then rm -rf to leave stale registration
        _git_ok(f"git worktree add {wt_path} -b stale-reg HEAD", self.repo)
        shutil.rmtree(wt_path)

        # Without prune, the stale registration blocks worktree add at same path
        r = _git(f"git worktree add {wt_path} -b {branch} HEAD", self.repo)
        self.assertNotEqual(r.returncode, 0, "Stale registration should block new branch add")

        # Clean up the branch that may have been partially created by the failed attempt
        _git("git branch -D " + branch, self.repo)

        # Apply fix: prune then add -b
        _git_ok("git worktree prune", self.repo)
        _git_ok("git branch -D stale-reg", self.repo)
        _git_ok(f"git worktree add {wt_path} -b {branch} HEAD", self.repo)
        self.assertTrue(os.path.isdir(wt_path))

        # Verify it's the correct new branch
        tip = _git_ok(f"git rev-parse {branch}", self.repo).strip()
        head = _git_ok("git rev-parse HEAD", self.repo).strip()
        self.assertEqual(tip, head, "New branch should be at HEAD")

    # --- Edge cases ---

    def test_prune_is_idempotent_no_stale_refs(self):
        """Prune when there are no stale refs is a no-op (shouldn't error)."""
        _git_ok("git worktree prune", self.repo)
        # Second prune also fine
        _git_ok("git worktree prune", self.repo)

    def test_prune_does_not_affect_healthy_worktrees(self):
        """Prune must not remove registrations for worktrees that still exist."""
        wt1 = os.path.join(self.tmpdir, "wt-healthy")
        _git_ok(f"git worktree add {wt1} -b feat/healthy HEAD", self.repo)

        # Create and rm -rf a second worktree (stale)
        wt2 = os.path.join(self.tmpdir, "wt-stale")
        _git_ok(f"git worktree add {wt2} -b feat/stale HEAD", self.repo)
        shutil.rmtree(wt2)

        # Prune should clear wt2's registration but keep wt1
        _git_ok("git worktree prune", self.repo)

        # wt1 should still be listed
        listing = _git_ok("git worktree list", self.repo)
        self.assertIn("wt-healthy", listing, "Healthy worktree must survive prune")
        self.assertNotIn("wt-stale", listing, "Stale worktree should be pruned")

    def test_double_rm_rf_then_single_prune(self):
        """Multiple orphaned paths are all cleared by a single prune."""
        wt_a = os.path.join(self.tmpdir, "wt-a")
        wt_b = os.path.join(self.tmpdir, "wt-b")
        _git_ok(f"git worktree add {wt_a} -b feat/a HEAD", self.repo)
        _git_ok(f"git worktree add {wt_b} -b feat/b HEAD", self.repo)

        shutil.rmtree(wt_a)
        shutil.rmtree(wt_b)

        _git_ok("git worktree prune", self.repo)

        # Both should be re-addable
        _git_ok(f"git worktree add {wt_a} feat/a", self.repo)
        _git_ok(f"git worktree add {wt_b} feat/b", self.repo)
        self.assertTrue(os.path.isdir(wt_a))
        self.assertTrue(os.path.isdir(wt_b))

    def test_state2_full_sequence_matches_yaml(self):
        """Simulate the exact sequence from default-workflow.yaml State 2.

        1. Check if dir exists → yes → rm -rf
        2. git worktree prune
        3. git worktree add <path> <branch>
        """
        wt_path = os.path.join(self.tmpdir, "wt-yaml-s2")
        branch = "feat/yaml-s2"

        _git_ok(f"git worktree add {wt_path} -b {branch} HEAD", self.repo)
        shutil.rmtree(wt_path)

        # Recreate orphan dir (simulating partial cleanup or crashed run)
        os.makedirs(wt_path)

        # Step sequence from YAML:
        if os.path.isdir(wt_path):
            shutil.rmtree(wt_path)
        _git_ok("git worktree prune", self.repo)
        _git_ok(f"git worktree add {wt_path} {branch}", self.repo)

        self.assertTrue(os.path.isdir(wt_path))
        # Verify it's a valid git worktree
        self.assertTrue(
            os.path.isfile(os.path.join(wt_path, ".git")),
            "Worktree should have .git file (not directory)",
        )

    def test_state3_full_sequence_matches_yaml(self):
        """Simulate the exact sequence from default-workflow.yaml State 3.

        1. Check if dir exists → yes → rm -rf
        2. git worktree prune
        3. git worktree add <path> -b <branch> <base-ref>
        """
        wt_path = os.path.join(self.tmpdir, "wt-yaml-s3")
        branch = "feat/yaml-s3"

        # Create orphan dir (not a real worktree, just leftover directory)
        os.makedirs(wt_path)

        # Step sequence from YAML:
        if os.path.isdir(wt_path):
            shutil.rmtree(wt_path)
        _git_ok("git worktree prune", self.repo)
        _git_ok(f"git worktree add {wt_path} -b {branch} HEAD", self.repo)

        self.assertTrue(os.path.isdir(wt_path))
        tip = _git_ok(f"git rev-parse {branch}", self.repo).strip()
        head = _git_ok("git rev-parse HEAD", self.repo).strip()
        self.assertEqual(tip, head)


if __name__ == "__main__":
    unittest.main()
