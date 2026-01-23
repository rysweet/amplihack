"""Tests for copilot launcher integration with adaptive context."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from amplihack.launcher.copilot import launch_copilot


@pytest.fixture
def mock_project_root(tmp_path):
    """Create a mock project root."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    runtime_dir = claude_dir / "runtime"
    runtime_dir.mkdir()
    return tmp_path


def test_launcher_writes_context_before_launch(mock_project_root):
    """Test that launcher writes context before launching copilot."""
    with (
        patch("amplihack.launcher.copilot.check_copilot", return_value=True),
        patch("amplihack.launcher.copilot.subprocess.run") as mock_run,
        patch("os.getcwd", return_value=str(mock_project_root)),
    ):
        mock_run.return_value.returncode = 0

        # Launch copilot
        result = launch_copilot(args=["test"])

        # Verify success
        assert result == 0

        # Verify context file was written
        context_file = mock_project_root / ".claude" / "runtime" / "launcher_context.json"
        assert context_file.exists()

        # Verify context contents
        context = json.loads(context_file.read_text())
        assert context["launcher_type"] == "copilot"
        assert "amplihack copilot test" in context["command"]
        assert context["environment"]["AMPLIHACK_LAUNCHER"] == "copilot"


def test_launcher_context_includes_timestamp(mock_project_root):
    """Test that launcher context includes timestamp."""
    with (
        patch("amplihack.launcher.copilot.check_copilot", return_value=True),
        patch("amplihack.launcher.copilot.subprocess.run") as mock_run,
        patch("os.getcwd", return_value=str(mock_project_root)),
    ):
        mock_run.return_value.returncode = 0

        # Launch copilot
        launch_copilot(args=[])

        # Verify context has timestamp
        context_file = mock_project_root / ".claude" / "runtime" / "launcher_context.json"
        context = json.loads(context_file.read_text())
        assert "timestamp" in context
        assert context["timestamp"]  # Non-empty


def test_launcher_handles_no_args(mock_project_root):
    """Test launcher handles no arguments gracefully."""
    with (
        patch("amplihack.launcher.copilot.check_copilot", return_value=True),
        patch("amplihack.launcher.copilot.subprocess.run") as mock_run,
        patch("os.getcwd", return_value=str(mock_project_root)),
    ):
        mock_run.return_value.returncode = 0

        # Launch without args
        result = launch_copilot()

        # Verify context file was written
        context_file = mock_project_root / ".claude" / "runtime" / "launcher_context.json"
        assert context_file.exists()

        context = json.loads(context_file.read_text())
        assert context["launcher_type"] == "copilot"
        assert result == 0


def test_launcher_context_survives_copilot_failure(mock_project_root):
    """Test that context is written even if copilot fails."""
    with (
        patch("amplihack.launcher.copilot.check_copilot", return_value=True),
        patch("amplihack.launcher.copilot.subprocess.run") as mock_run,
        patch("os.getcwd", return_value=str(mock_project_root)),
    ):
        mock_run.return_value.returncode = 1  # Copilot fails

        # Launch copilot
        result = launch_copilot(args=["test"])

        # Verify failure returned
        assert result == 1

        # But context was still written
        context_file = mock_project_root / ".claude" / "runtime" / "launcher_context.json"
        assert context_file.exists()


def test_launcher_creates_runtime_dir_if_missing(mock_project_root):
    """Test launcher creates runtime dir if it doesn't exist."""
    # Remove runtime directory
    runtime_dir = mock_project_root / ".claude" / "runtime"
    runtime_dir.rmdir()

    with (
        patch("amplihack.launcher.copilot.check_copilot", return_value=True),
        patch("amplihack.launcher.copilot.subprocess.run") as mock_run,
        patch("os.getcwd", return_value=str(mock_project_root)),
    ):
        mock_run.return_value.returncode = 0

        # Launch copilot
        launch_copilot(args=["test"])

        # Verify runtime dir was created
        assert runtime_dir.exists()

        # And context file exists
        context_file = runtime_dir / "launcher_context.json"
        assert context_file.exists()


class TestMcpServerDisabling:
    """Tests for GitHub MCP server disabling functionality."""

    def test_disable_github_mcp_server_creates_config(self, tmp_path, monkeypatch):
        """Test that disable_github_mcp_server creates MCP config."""
        from amplihack.launcher.copilot import disable_github_mcp_server

        # Point HOME to temp directory
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        result = disable_github_mcp_server()

        assert result is True
        mcp_config = tmp_path / ".copilot" / "github-copilot" / "mcp.json"
        assert mcp_config.exists()

        config = json.loads(mcp_config.read_text())
        assert config["mcpServers"]["github-mcp-server"]["disabled"] is True

    def test_disable_github_mcp_server_preserves_existing_config(self, tmp_path, monkeypatch):
        """Test that disabling preserves other MCP server configs."""
        from amplihack.launcher.copilot import disable_github_mcp_server

        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create existing config with other servers
        mcp_dir = tmp_path / ".copilot" / "github-copilot"
        mcp_dir.mkdir(parents=True)
        existing_config = {
            "mcpServers": {
                "other-server": {"some": "config"},
            }
        }
        (mcp_dir / "mcp.json").write_text(json.dumps(existing_config))

        result = disable_github_mcp_server()

        assert result is True
        config = json.loads((mcp_dir / "mcp.json").read_text())
        # Verify other server config preserved
        assert config["mcpServers"]["other-server"]["some"] == "config"
        # And github-mcp-server is disabled
        assert config["mcpServers"]["github-mcp-server"]["disabled"] is True


class TestGhAuthCheck:
    """Tests for gh CLI authentication checking."""

    def test_get_gh_auth_account_when_authenticated(self):
        """Test parsing gh auth status when authenticated."""
        from amplihack.launcher.copilot import get_gh_auth_account

        with patch("amplihack.launcher.copilot.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = (
                "github.com\n  ✓ Logged in to github.com account testuser (/path/to/config)\n"
            )
            mock_run.return_value.stderr = ""

            result = get_gh_auth_account()

            assert result == "testuser"

    def test_get_gh_auth_account_from_stderr(self):
        """Test parsing gh auth status from stderr (some environments)."""
        from amplihack.launcher.copilot import get_gh_auth_account

        with patch("amplihack.launcher.copilot.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = (
                "github.com\n  ✓ Logged in to github.com account testuser2 (/path)\n"
            )

            result = get_gh_auth_account()

            assert result == "testuser2"

    def test_get_gh_auth_account_when_not_authenticated(self):
        """Test returns None when not authenticated."""
        from amplihack.launcher.copilot import get_gh_auth_account

        with patch("amplihack.launcher.copilot.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = "You are not logged into any GitHub hosts."

            result = get_gh_auth_account()

            assert result is None

    def test_get_gh_auth_account_when_gh_not_installed(self):
        """Test returns None when gh CLI is not installed."""
        from amplihack.launcher.copilot import get_gh_auth_account

        with patch("amplihack.launcher.copilot.subprocess.run", side_effect=FileNotFoundError):
            result = get_gh_auth_account()

            assert result is None


class TestLauncherMcpIntegration:
    """Tests for MCP disabling in launcher."""

    def test_launcher_disables_mcp_server(self, mock_project_root, tmp_path, monkeypatch):
        """Test that launcher disables GitHub MCP server on startup."""
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        with (
            patch("amplihack.launcher.copilot.check_copilot", return_value=True),
            patch("amplihack.launcher.copilot.subprocess.run") as mock_run,
            patch("os.getcwd", return_value=str(mock_project_root)),
            patch("amplihack.launcher.copilot.get_gh_auth_account", return_value="testuser"),
        ):
            mock_run.return_value.returncode = 0

            launch_copilot(args=[])

            # Verify MCP config was created
            mcp_config = tmp_path / ".copilot" / "github-copilot" / "mcp.json"
            assert mcp_config.exists()
            config = json.loads(mcp_config.read_text())
            assert config["mcpServers"]["github-mcp-server"]["disabled"] is True
