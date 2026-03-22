"""Tests for the multitask orchestrator."""

import json
import os

# Import the module under test
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

try:
    import pytest
except ImportError:
    raise SystemExit("pytest is required to run tests: pip install pytest")

sys.path.insert(0, str(Path(__file__).parent))
from orchestrator import ParallelOrchestrator, Workstream, run


class TestWorkstream:
    """Tests for the Workstream dataclass."""

    def test_is_running_no_pid(self):
        ws = Workstream(issue=1, branch="feat/test", description="test", task="test task")
        assert ws.is_running is False

    def test_is_running_with_dead_pid(self):
        ws = Workstream(issue=1, branch="feat/test", description="test", task="test task")
        ws.pid = 999999999  # Very unlikely to be a real PID
        assert ws.is_running is False

    def test_runtime_no_start(self):
        ws = Workstream(issue=1, branch="feat/test", description="test", task="test task")
        assert ws.runtime_seconds is None

    def test_runtime_with_start(self):
        ws = Workstream(issue=1, branch="feat/test", description="test", task="test task")
        ws.start_time = 100.0
        ws.end_time = 160.0
        assert ws.runtime_seconds == 60.0


class TestParallelOrchestrator:
    """Tests for the ParallelOrchestrator class."""

    def test_init_recipe_mode(self):
        orch = ParallelOrchestrator(repo_url="https://example.com/repo.git", mode="recipe")
        assert orch.mode == "recipe"
        assert orch.workstreams == []

    def test_init_classic_mode(self):
        orch = ParallelOrchestrator(repo_url="https://example.com/repo.git", mode="classic")
        assert orch.mode == "classic"

    def test_setup_creates_directory(self, tmp_path):
        base = tmp_path / "workstreams"
        orch = ParallelOrchestrator(repo_url="https://example.com/repo.git", tmp_base=str(base))
        orch.setup()
        assert base.exists()

    def test_setup_cleans_existing(self, tmp_path):
        base = tmp_path / "workstreams"
        base.mkdir()
        (base / "old_file.txt").write_text("old")
        orch = ParallelOrchestrator(repo_url="https://example.com/repo.git", tmp_base=str(base))
        orch.setup()
        assert not (base / "old_file.txt").exists()

    @patch("orchestrator.subprocess.run")
    def test_add_recipe_mode(self, mock_run, tmp_path):
        """Test that add() creates proper recipe launcher files."""
        mock_run.return_value = MagicMock(returncode=0)
        base = tmp_path / "workstreams"
        base.mkdir()

        orch = ParallelOrchestrator(
            repo_url="https://example.com/repo.git",
            tmp_base=str(base),
            mode="recipe",
        )

        # Create the expected work dir since git clone is mocked
        ws_dir = base / "ws-42"
        ws_dir.mkdir()

        result = orch.add(
            issue=42,
            branch="feat/test-feature",
            description="Test feature",
            task="Implement test feature",
        )

        assert result.issue == 42
        assert result.branch == "feat/test-feature"
        assert (ws_dir / "launcher.py").exists()
        assert (ws_dir / "run.sh").exists()

        # Verify launcher.py contains recipe runner import
        launcher_content = (ws_dir / "launcher.py").read_text()
        assert "run_recipe_by_name" in launcher_content
        assert "CLISubprocessAdapter" in launcher_content
        assert "default-workflow" in launcher_content

        # Verify run.sh sets session tree vars
        run_content = (ws_dir / "run.sh").read_text()
        assert "AMPLIHACK_TREE_ID" in run_content

    @patch("orchestrator.subprocess.run")
    def test_add_classic_mode(self, mock_run, tmp_path):
        """Test that add() creates proper classic launcher files."""
        mock_run.return_value = MagicMock(returncode=0)
        base = tmp_path / "workstreams"
        base.mkdir()

        orch = ParallelOrchestrator(
            repo_url="https://example.com/repo.git",
            tmp_base=str(base),
            mode="classic",
        )

        ws_dir = base / "ws-42"
        ws_dir.mkdir()

        orch.add(
            issue=42,
            branch="feat/test-feature",
            description="Test feature",
            task="Implement test feature",
        )

        assert (ws_dir / "TASK.md").exists()
        assert (ws_dir / "run.sh").exists()

        # Verify TASK.md contains task instructions
        task_content = (ws_dir / "TASK.md").read_text()
        assert "Issue #42" in task_content
        assert "Implement test feature" in task_content

        # Verify run.sh uses amplihack claude
        run_content = (ws_dir / "run.sh").read_text()
        assert "amplihack claude" in run_content

    @patch("orchestrator.subprocess.run")
    def test_add_custom_recipe(self, mock_run, tmp_path):
        """Test custom recipe selection per workstream."""
        mock_run.return_value = MagicMock(returncode=0)
        base = tmp_path / "workstreams"
        base.mkdir()
        (base / "ws-42").mkdir()

        orch = ParallelOrchestrator(
            repo_url="https://example.com/repo.git",
            tmp_base=str(base),
            mode="recipe",
        )

        ws = orch.add(
            issue=42,
            branch="feat/investigate",
            description="Investigation",
            task="Investigate performance",
            recipe="investigation-workflow",
        )

        launcher_content = (ws.work_dir / "launcher.py").read_text()
        assert "investigation-workflow" in launcher_content

    def test_get_status_empty(self):
        orch = ParallelOrchestrator(repo_url="https://example.com/repo.git")
        status = orch.get_status()
        assert status == {"running": [], "completed": [], "failed": []}

    def test_report_empty(self):
        orch = ParallelOrchestrator(
            repo_url="https://example.com/repo.git",
            tmp_base="/tmp/test-report",
        )
        Path("/tmp/test-report").mkdir(parents=True, exist_ok=True)
        report = orch.report()
        assert "PARALLEL WORKSTREAM REPORT" in report
        assert "recipe" in report  # Default mode


class TestRunFunction:
    """Tests for the run() entry point."""

    def test_run_with_invalid_config(self, tmp_path):
        """Test that run() fails gracefully with invalid JSON."""
        config_file = tmp_path / "bad.json"
        config_file.write_text("not json")

        with pytest.raises(json.JSONDecodeError):
            run(str(config_file))

    @patch("orchestrator.subprocess.run")
    def test_run_no_repo_url(self, mock_run, tmp_path):
        """Test that run() fails when no repo URL is available."""
        mock_run.return_value = MagicMock(returncode=1, stdout="")

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps([{"issue": 1, "branch": "feat/test", "task": "test"}]))

        with pytest.raises(SystemExit):
            run(str(config_file))


class TestLauncherGeneration:
    """Tests for generated launcher file content."""

    def test_recipe_launcher_escapes_quotes(self, tmp_path):
        """Verify task text with quotes is properly escaped in launcher."""
        base = tmp_path / "ws"
        base.mkdir()
        (base / "ws-1").mkdir()

        orch = ParallelOrchestrator(
            repo_url="https://example.com/repo.git",
            tmp_base=str(base),
            mode="recipe",
        )

        with patch("orchestrator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            ws = orch.add(
                issue=1,
                branch="feat/test",
                description="test",
                task="Task with 'single quotes' and special chars",
            )

        launcher = (ws.work_dir / "launcher.py").read_text()
        # Should not have unescaped single quotes that break Python
        assert "single quotes" in launcher

    def test_run_sh_is_executable(self, tmp_path):
        """Verify run.sh has execute permission."""
        base = tmp_path / "ws"
        base.mkdir()
        (base / "ws-1").mkdir()

        orch = ParallelOrchestrator(
            repo_url="https://example.com/repo.git",
            tmp_base=str(base),
            mode="recipe",
        )

        with patch("orchestrator.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            ws = orch.add(issue=1, branch="feat/t", description="t", task="t")

        run_sh = ws.work_dir / "run.sh"
        assert os.access(run_sh, os.X_OK)


class TestClassicLauncherNoMultilineArg:
    """Tests that classic launcher -p argument is on a single line.

    Regression test for issue #2946: multi-line -p argument causes the shell
    to split the command at newlines, making amplihack claude wait on stdin
    indefinitely.
    """

    def _create_classic_launcher(self, tmp_path, task="Implement feature"):
        """Helper to create a classic launcher and return run.sh content."""
        base = tmp_path / "ws"
        base.mkdir()

        orch = ParallelOrchestrator(
            repo_url="https://example.com/repo.git",
            tmp_base=str(base),
            mode="classic",
        )

        ws_dir = base / "ws-1"

        def _mock_run(*args, **kwargs):
            # Simulate git clone by creating the work directory
            cmd = args[0] if args else kwargs.get("args", [])
            if isinstance(cmd, list) and "clone" in cmd:
                ws_dir.mkdir(exist_ok=True)
            return MagicMock(returncode=0, stdout="ref: refs/heads/main\tHEAD\n")

        with patch("orchestrator.subprocess.run", side_effect=_mock_run):
            ws = orch.add(issue=1, branch="feat/test", description="test", task=task)

        return (ws.work_dir / "run.sh").read_text()

    def test_p_flag_on_single_line(self, tmp_path):
        """The -p argument and its value must be on the same line."""
        content = self._create_classic_launcher(tmp_path)
        for line in content.splitlines():
            if "-p " in line:
                # The line with -p must also contain the closing quote
                assert line.count('"') >= 2, (
                    f"The -p argument is split across lines, which causes "
                    f"the shell to break the command. Line: {line!r}"
                )
                break
        else:
            raise AssertionError("No line with -p flag found in run.sh")

    def test_no_bare_newline_in_p_argument(self, tmp_path):
        """Ensure no unescaped newlines between -p and closing quote."""
        content = self._create_classic_launcher(tmp_path)
        # Find everything after '-p ' up to end of script
        import re

        match = re.search(r'-p\s+"([^"]*)"', content, re.DOTALL)
        assert match is not None, "Could not find -p argument in run.sh"
        p_value = match.group(1)
        assert "\n" not in p_value, (
            f"The -p argument value contains a newline, which will cause "
            f"the shell to split the command: {p_value!r}"
        )

    def test_amplihack_claude_command_complete(self, tmp_path):
        """The amplihack claude command must have all parts on one line."""
        content = self._create_classic_launcher(tmp_path)
        # Find the line with the amplihack claude command
        cmd_lines = [l.strip() for l in content.splitlines() if "amplihack claude" in l]
        assert len(cmd_lines) == 1, f"Expected 1 amplihack claude line, got {len(cmd_lines)}"
        cmd = cmd_lines[0]
        assert "@TASK.md" in cmd, "Command must reference @TASK.md"
        assert cmd.endswith('"'), f"Command must end with closing quote, got: {cmd!r}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
