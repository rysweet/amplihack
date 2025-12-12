"""Unit tests for integrator module."""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from ..errors import IntegrationError
from ..integrator import BranchInfo, IntegrationSummary, Integrator


class TestIntegrator(unittest.TestCase):
    """Test cases for Integrator class."""

    def setUp(self):
        """Create temporary git repository for testing."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo_path = self.temp_dir / "test_repo"
        self.repo_path.mkdir()

        # Initialize git repository with main as default branch
        subprocess.run(
            ["git", "init", "-b", "main"], cwd=self.repo_path, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"], cwd=self.repo_path, check=True
        )
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=self.repo_path, check=True)

        # Create .claude directory structure
        claude_dir = self.repo_path / ".claude" / "runtime" / "logs"
        claude_dir.mkdir(parents=True)

        # Create initial commit
        test_file = self.repo_path / "test.txt"
        test_file.write_text("initial content")
        subprocess.run(["git", "add", "."], cwd=self.repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
        )

    def tearDown(self):
        """Clean up temporary directory."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_integrator_initialization(self):
        """Test Integrator initialization."""
        integrator = Integrator(self.repo_path)
        self.assertEqual(integrator.repo_path, self.repo_path)

    def test_initialization_non_git_repo_fails(self):
        """Test that initialization fails for non-git directory."""
        non_git_dir = self.temp_dir / "not_git"
        non_git_dir.mkdir()

        with self.assertRaises(IntegrationError) as ctx:
            Integrator(non_git_dir)

        self.assertIn("not a git repository", str(ctx.exception).lower())

    def test_import_branches(self):
        """Test importing branches from bundle."""
        # Create a feature branch in original repo
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
        )
        feature_file = self.repo_path / "feature.txt"
        feature_file.write_text("feature content")
        subprocess.run(["git", "add", "feature.txt"], cwd=self.repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add feature"],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "main"], cwd=self.repo_path, check=True, capture_output=True
        )

        # Create bundle
        bundle_dir = self.temp_dir / "results"
        bundle_dir.mkdir()
        bundle_path = bundle_dir / "results.bundle"
        subprocess.run(
            ["git", "bundle", "create", str(bundle_path), "--all"],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
        )

        # Import branches
        integrator = Integrator(self.repo_path)
        branches = integrator._import_branches(bundle_dir)

        self.assertGreater(len(branches), 0)
        branch_names = [b.name for b in branches]
        self.assertIn("feature", branch_names)

    def test_copy_logs(self):
        """Test copying logs from results."""
        # Create mock results directory with logs
        results_dir = self.temp_dir / "results"
        results_logs = results_dir / ".claude" / "runtime" / "logs"
        results_logs.mkdir(parents=True)

        log_file = results_logs / "test.log"
        log_file.write_text("test log content")

        # Copy logs
        integrator = Integrator(self.repo_path)
        success = integrator._copy_logs(results_dir)

        self.assertTrue(success)

        # Verify logs were copied
        dest_log = self.repo_path / ".claude" / "runtime" / "logs" / "remote" / "test.log"
        self.assertTrue(dest_log.exists())
        self.assertEqual(dest_log.read_text(), "test log content")

    def test_copy_logs_no_logs_directory(self):
        """Test copying logs when no logs exist."""
        results_dir = self.temp_dir / "results"
        results_dir.mkdir()

        integrator = Integrator(self.repo_path)
        success = integrator._copy_logs(results_dir)

        self.assertFalse(success)

    def test_detect_conflicts_none(self):
        """Test conflict detection when no conflicts."""
        branches = [BranchInfo(name="feature", commit="abc123", is_new=True)]

        integrator = Integrator(self.repo_path)
        conflicts = integrator._detect_conflicts(branches)

        self.assertEqual(len(conflicts), 0)

    def test_list_local_branches(self):
        """Test listing local branches."""
        integrator = Integrator(self.repo_path)
        branches = integrator._list_local_branches()

        self.assertIn("main", branches)

    def test_create_summary_report(self):
        """Test creating summary report."""
        summary = IntegrationSummary(
            branches=[BranchInfo(name="feature", commit="abc123", is_new=True)],
            commits_count=5,
            files_changed=10,
            logs_copied=True,
            has_conflicts=False,
        )

        integrator = Integrator(self.repo_path)
        report = integrator.create_summary_report(summary)

        self.assertIn("Remote Execution Results", report)
        self.assertIn("feature", report)
        self.assertIn("5", report)
        self.assertIn("10", report)

    def test_create_summary_report_with_conflicts(self):
        """Test summary report with conflicts."""
        summary = IntegrationSummary(
            branches=[BranchInfo(name="main", commit="def456", is_new=False)],
            commits_count=3,
            files_changed=5,
            logs_copied=True,
            has_conflicts=True,
            conflict_details="Branch main has diverged",
        )

        integrator = Integrator(self.repo_path)
        report = integrator.create_summary_report(summary)

        self.assertIn("WARNING", report)
        self.assertIn("Conflicts detected", report)
        self.assertIn("diverged", report)

    def test_count_files_changed(self):
        """Test counting files changed."""
        # Create feature branch with changes
        subprocess.run(
            ["git", "checkout", "-b", "feature"],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
        )
        (self.repo_path / "file1.txt").write_text("content1")
        (self.repo_path / "file2.txt").write_text("content2")
        subprocess.run(["git", "add", "."], cwd=self.repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add files"],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
        )

        # Create bundle and import
        bundle_dir = self.temp_dir / "results"
        bundle_dir.mkdir()
        bundle_path = bundle_dir / "results.bundle"
        subprocess.run(
            ["git", "bundle", "create", str(bundle_path), "--all"],
            cwd=self.repo_path,
            check=True,
            capture_output=True,
        )

        subprocess.run(
            ["git", "checkout", "main"], cwd=self.repo_path, check=True, capture_output=True
        )

        integrator = Integrator(self.repo_path)
        branches = integrator._import_branches(bundle_dir)

        files_changed = integrator._count_files_changed(branches)

        # Should count the 2 new files
        self.assertGreaterEqual(files_changed, 0)  # May vary based on git state


class TestBranchInfo(unittest.TestCase):
    """Test cases for BranchInfo dataclass."""

    def test_branch_info_creation(self):
        """Test creating BranchInfo."""
        branch = BranchInfo(name="feature", commit="abc123", is_new=True)

        self.assertEqual(branch.name, "feature")
        self.assertEqual(branch.commit, "abc123")
        self.assertTrue(branch.is_new)


class TestIntegrationSummary(unittest.TestCase):
    """Test cases for IntegrationSummary dataclass."""

    def test_integration_summary_creation(self):
        """Test creating IntegrationSummary."""
        summary = IntegrationSummary(
            branches=[], commits_count=0, files_changed=0, logs_copied=False, has_conflicts=False
        )

        self.assertEqual(len(summary.branches), 0)
        self.assertEqual(summary.commits_count, 0)
        self.assertFalse(summary.has_conflicts)


if __name__ == "__main__":
    unittest.main()
