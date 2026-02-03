"""Tests for automatic dependency installer."""

import subprocess
from unittest.mock import Mock, patch

import pytest

from amplihack.memory.kuzu.indexing.dependency_installer import (
    DependencyInstaller,
    InstallResult,
)


class TestDependencyInstaller:
    """Test automatic dependency installation."""

    @pytest.fixture
    def installer(self):
        """Create installer instance (quiet mode for tests)."""
        return DependencyInstaller(quiet=True)

    def test_scip_python_already_installed(self, installer):
        """Test scip-python detection when already installed."""
        with patch("shutil.which", return_value="/usr/local/bin/scip-python"):
            result = installer.install_scip_python()

            assert result.tool == "scip-python"
            assert result.success is True
            assert result.already_installed is True
            assert result.error_message is None

    def test_scip_python_install_success(self, installer):
        """Test successful scip-python installation via npm."""

        def mock_which(cmd):
            if cmd == "scip-python":
                return None
            if cmd == "npm":
                return "/usr/bin/npm"
            return None

        with (
            patch("shutil.which", side_effect=mock_which),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = Mock(returncode=0)

            result = installer.install_scip_python()

            assert result.tool == "scip-python"
            assert result.success is True
            assert result.already_installed is False
            assert result.error_message is None

            # Verify npm install was called with correct package
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "npm" in args
            assert "install" in args
            assert "@sourcegraph/scip-python" in args

    def test_scip_python_install_failure_no_npm(self, installer):
        """Test scip-python installation failure when npm is missing."""
        with patch("shutil.which", return_value=None):
            result = installer.install_scip_python()

            assert result.tool == "scip-python"
            assert result.success is False
            assert result.already_installed is False
            assert "npm not found" in result.error_message

    def test_scip_python_install_failure_npm_error(self, installer):
        """Test scip-python installation failure when npm install fails."""

        def mock_which(cmd):
            if cmd == "scip-python":
                return None
            if cmd == "npm":
                return "/usr/bin/npm"
            return None

        with (
            patch("shutil.which", side_effect=mock_which),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = Mock(returncode=1, stderr="Error")

            result = installer.install_scip_python()

            assert result.tool == "scip-python"
            assert result.success is False
            assert result.already_installed is False
            assert result.error_message == "npm install failed"

    def test_typescript_language_server_already_installed(self, installer):
        """Test typescript-language-server detection when already installed."""
        with patch("shutil.which", return_value="/usr/local/bin/typescript-language-server"):
            result = installer.install_typescript_language_server()

            assert result.tool == "typescript-language-server"
            assert result.success is True
            assert result.already_installed is True

    def test_typescript_language_server_no_npm(self, installer):
        """Test typescript-language-server installation when npm missing."""
        with patch("shutil.which", return_value=None):
            result = installer.install_typescript_language_server()

            assert result.tool == "typescript-language-server"
            assert result.success is False
            assert result.already_installed is False
            assert "npm not found" in result.error_message

    def test_typescript_language_server_install_success(self, installer):
        """Test successful typescript-language-server installation."""

        def mock_which(cmd):
            if cmd == "npm":
                return "/usr/bin/npm"
            if cmd == "typescript-language-server":
                return None
            return None

        with (
            patch("shutil.which", side_effect=mock_which),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = Mock(returncode=0)

            result = installer.install_typescript_language_server()

            assert result.tool == "typescript-language-server"
            assert result.success is True
            assert result.already_installed is False

            # Verify npm install was called
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "npm" in args
            assert "install" in args
            assert "typescript-language-server" in args

    def test_install_python_dependencies_scip_success(self, installer):
        """Test Python dependency installation with scip-python success."""

        def mock_which(cmd):
            if cmd == "scip-python":
                return None
            if cmd == "npm":
                return "/usr/bin/npm"
            return None

        with (
            patch("shutil.which", side_effect=mock_which),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.return_value = Mock(returncode=0)

            results = installer.install_python_dependencies()

            assert len(results) == 1  # Only scip-python
            assert results[0].tool == "scip-python"
            assert results[0].success is True

    def test_install_python_dependencies_scip_fails(self, installer):
        """Test Python dependency installation when scip-python fails (no fallback)."""
        with patch("shutil.which", return_value=None):
            results = installer.install_python_dependencies()

            assert len(results) == 1  # Only scip-python (failed)
            assert results[0].tool == "scip-python"
            assert results[0].success is False
            assert "npm not found" in results[0].error_message

    def test_install_all_auto_installable(self, installer):
        """Test installing all auto-installable dependencies."""
        with (
            patch.object(installer, "install_python_dependencies") as mock_python,
            patch.object(installer, "install_typescript_language_server") as mock_ts,
        ):
            mock_python.return_value = [
                InstallResult("scip-python", True, False),
            ]
            mock_ts.return_value = InstallResult("typescript-language-server", True, False)

            results = installer.install_all_auto_installable()

            assert len(results) == 2
            assert "scip-python" in results
            assert "typescript-language-server" in results
            assert all(r.success for r in results.values())

    def test_show_system_dependency_help_no_tools(self, installer, capsys):
        """Test system dependency help when no tools are installed."""
        with patch("shutil.which", return_value=None):
            # Enable output for this test
            installer.quiet = False
            installer.show_system_dependency_help()

            captured = capsys.readouterr()
            assert "C# support" in captured.err
            assert "Go support" in captured.err
            assert "Java support" in captured.err
            assert "PHP support" in captured.err
            assert "Ruby support" in captured.err

    def test_show_system_dependency_help_all_installed(self, installer, capsys):
        """Test system dependency help when all tools are installed."""
        with patch("shutil.which", return_value="/usr/bin/tool"):
            installer.quiet = False
            installer.show_system_dependency_help()

            captured = capsys.readouterr()
            assert captured.err == ""  # No messages when all installed

    def test_install_timeout_handling(self, installer):
        """Test handling of installation timeout during npm install."""

        def mock_which(cmd):
            if cmd == "scip-python":
                return None
            if cmd == "npm":
                return "/usr/bin/npm"
            return None

        with (
            patch("shutil.which", side_effect=mock_which),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 300)),
        ):
            result = installer.install_scip_python()

            assert result.success is False
            assert result.error_message == "npm install failed"
