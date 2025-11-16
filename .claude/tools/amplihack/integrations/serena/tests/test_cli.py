"""Unit tests for Serena CLI."""

import argparse
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ..cli import SerenaCLI
from ..configurator import SerenaConfig, SerenaConfigurator
from ..detector import SerenaDetectionResult, SerenaDetector
from ..errors import ConfigurationError, SerenaNotFoundError, UvNotFoundError


class TestSerenaCLI:
    """Tests for SerenaCLI class."""

    @pytest.fixture
    def mock_detector(self):
        """Create a mock SerenaDetector."""
        detector = Mock(spec=SerenaDetector)
        return detector

    @pytest.fixture
    def mock_configurator(self):
        """Create a mock SerenaConfigurator."""
        configurator = Mock(spec=SerenaConfigurator)
        return configurator

    @pytest.fixture
    def cli(self, mock_detector, mock_configurator):
        """Create a SerenaCLI with mocks."""
        return SerenaCLI(detector=mock_detector, configurator=mock_configurator)

    def test_initialization_with_mocks(self, mock_detector, mock_configurator):
        """Test CLI initializes with provided detector and configurator."""
        cli = SerenaCLI(detector=mock_detector, configurator=mock_configurator)
        assert cli.detector is mock_detector
        assert cli.configurator is mock_configurator

    def test_initialization_without_mocks(self):
        """Test CLI creates detector and configurator when not provided."""
        cli = SerenaCLI()
        assert isinstance(cli.detector, SerenaDetector)
        assert isinstance(cli.configurator, SerenaConfigurator)

    def test_setup_parser_creates_subcommands(self, cli):
        """Test setup_parser creates all expected subcommands."""
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        cli.setup_parser(subparsers)

        # Parse each command to verify they exist
        args = parser.parse_args(["serena", "status"])
        assert args.serena_command == "status"

        args = parser.parse_args(["serena", "setup"])
        assert args.serena_command == "setup"

        args = parser.parse_args(["serena", "remove"])
        assert args.serena_command == "remove"

        args = parser.parse_args(["serena", "export"])
        assert args.serena_command == "export"

        args = parser.parse_args(["serena", "diagnose"])
        assert args.serena_command == "diagnose"

    def test_cmd_status_all_ready(self, cli, mock_detector, mock_configurator):
        """Test cmd_status shows ready status when all prerequisites met."""
        mock_result = SerenaDetectionResult(
            uv_available=True,
            uv_path=Path("/usr/bin/uv"),
            serena_available=True,
            serena_path="uvx --from git+https://github.com/oraios/serena serena",
            platform="linux",
            mcp_config_path=Path("/home/user/.config/Claude/claude_desktop_config.json"),
            config_exists=True,
        )
        mock_detector.detect_all.return_value = mock_result
        mock_configurator.is_configured.return_value = True

        args = argparse.Namespace()
        with patch("builtins.print") as mock_print:
            exit_code = cli.cmd_status(args)
            assert exit_code == 0
            # Verify status output
            calls = [str(call) for call in mock_print.call_args_list]
            output = " ".join(calls)
            assert "Yes" in output  # uv available
            assert "linux" in output

    def test_cmd_status_not_ready(self, cli, mock_detector, mock_configurator):
        """Test cmd_status shows not ready when prerequisites missing."""
        mock_result = SerenaDetectionResult(
            uv_available=False,
            uv_path=None,
            serena_available=False,
            serena_path=None,
            platform="linux",
            mcp_config_path=None,
            config_exists=False,
        )
        mock_detector.detect_all.return_value = mock_result
        mock_configurator.is_configured.return_value = False

        args = argparse.Namespace()
        with patch("builtins.print") as mock_print:
            exit_code = cli.cmd_status(args)
            assert exit_code == 0
            calls = [str(call) for call in mock_print.call_args_list]
            output = " ".join(calls)
            assert "Prerequisites not met" in output

    def test_cmd_setup_success(self, cli, mock_detector, mock_configurator):
        """Test cmd_setup successfully configures Serena."""
        mock_result = SerenaDetectionResult(
            uv_available=True,
            uv_path=Path("/usr/bin/uv"),
            serena_available=True,
            serena_path="uvx --from git+https://github.com/oraios/serena serena",
            platform="linux",
            mcp_config_path=Path("/home/user/.config/Claude/claude_desktop_config.json"),
            config_exists=False,
        )
        mock_detector.detect_all.return_value = mock_result
        mock_configurator.is_configured.return_value = False
        mock_configurator.add_to_mcp_servers.return_value = True

        args = argparse.Namespace(force=False)
        with patch("builtins.print") as mock_print:
            exit_code = cli.cmd_setup(args)
            assert exit_code == 0
            calls = [str(call) for call in mock_print.call_args_list]
            output = " ".join(calls)
            assert "Success" in output

    def test_cmd_setup_already_configured(self, cli, mock_detector, mock_configurator):
        """Test cmd_setup when Serena is already configured."""
        mock_result = SerenaDetectionResult(
            uv_available=True,
            uv_path=Path("/usr/bin/uv"),
            serena_available=True,
            serena_path="uvx --from git+https://github.com/oraios/serena serena",
            platform="linux",
            mcp_config_path=Path("/home/user/.config/Claude/claude_desktop_config.json"),
            config_exists=True,
        )
        mock_detector.detect_all.return_value = mock_result
        mock_configurator.is_configured.return_value = True

        args = argparse.Namespace(force=False)
        with patch("builtins.print") as mock_print:
            exit_code = cli.cmd_setup(args)
            assert exit_code == 0
            calls = [str(call) for call in mock_print.call_args_list]
            output = " ".join(calls)
            assert "already configured" in output

    def test_cmd_setup_force(self, cli, mock_detector, mock_configurator):
        """Test cmd_setup with force flag."""
        mock_result = SerenaDetectionResult(
            uv_available=True,
            uv_path=Path("/usr/bin/uv"),
            serena_available=True,
            serena_path="uvx --from git+https://github.com/oraios/serena serena",
            platform="linux",
            mcp_config_path=Path("/home/user/.config/Claude/claude_desktop_config.json"),
            config_exists=True,
        )
        mock_detector.detect_all.return_value = mock_result
        mock_configurator.is_configured.return_value = True
        mock_configurator.add_to_mcp_servers.return_value = False

        args = argparse.Namespace(force=True)
        with patch("builtins.print") as mock_print:
            exit_code = cli.cmd_setup(args)
            assert exit_code == 0
            mock_configurator.add_to_mcp_servers.assert_called_once()

    def test_cmd_setup_missing_uv(self, cli, mock_detector, mock_configurator):
        """Test cmd_setup raises error when uv is not available."""
        mock_result = SerenaDetectionResult(
            uv_available=False,
            uv_path=None,
            serena_available=True,
            serena_path="uvx --from git+https://github.com/oraios/serena serena",
            platform="linux",
            mcp_config_path=Path("/home/user/.config/Claude/claude_desktop_config.json"),
            config_exists=False,
        )
        mock_detector.detect_all.return_value = mock_result

        args = argparse.Namespace(force=False)
        with pytest.raises(UvNotFoundError):
            cli.cmd_setup(args)

    def test_cmd_setup_missing_serena(self, cli, mock_detector, mock_configurator):
        """Test cmd_setup raises error when Serena is not available."""
        mock_result = SerenaDetectionResult(
            uv_available=True,
            uv_path=Path("/usr/bin/uv"),
            serena_available=False,
            serena_path=None,
            platform="linux",
            mcp_config_path=Path("/home/user/.config/Claude/claude_desktop_config.json"),
            config_exists=False,
        )
        mock_detector.detect_all.return_value = mock_result

        args = argparse.Namespace(force=False)
        with pytest.raises(SerenaNotFoundError):
            cli.cmd_setup(args)

    def test_cmd_remove_success(self, cli, mock_detector, mock_configurator):
        """Test cmd_remove successfully removes Serena configuration."""
        mock_configurator.remove_from_mcp_servers.return_value = True

        args = argparse.Namespace()
        with patch("builtins.print") as mock_print:
            exit_code = cli.cmd_remove(args)
            assert exit_code == 0
            calls = [str(call) for call in mock_print.call_args_list]
            output = " ".join(calls)
            assert "Success" in output

    def test_cmd_remove_not_configured(self, cli, mock_detector, mock_configurator):
        """Test cmd_remove when Serena is not configured."""
        mock_configurator.remove_from_mcp_servers.return_value = False

        args = argparse.Namespace()
        with patch("builtins.print") as mock_print:
            exit_code = cli.cmd_remove(args)
            assert exit_code == 0
            calls = [str(call) for call in mock_print.call_args_list]
            output = " ".join(calls)
            assert "not configured" in output

    def test_cmd_export_success(self, cli, mock_detector, mock_configurator):
        """Test cmd_export successfully exports configuration."""
        output_path = Path("serena_config.json")
        mock_result = SerenaDetectionResult(
            uv_available=True,
            uv_path=Path("/usr/bin/uv"),
            serena_available=True,
            serena_path="uvx --from git+https://github.com/oraios/serena serena",
            platform="linux",
            mcp_config_path=Path("/home/user/.config/Claude/claude_desktop_config.json"),
            config_exists=True,
        )
        mock_detector.detect_all.return_value = mock_result
        mock_configurator.export_to_claude_desktop.return_value = True

        args = argparse.Namespace(output=output_path)
        with patch("builtins.print") as mock_print:
            exit_code = cli.cmd_export(args)
            assert exit_code == 0
            mock_configurator.export_to_claude_desktop.assert_called_once_with(output_path)
            calls = [str(call) for call in mock_print.call_args_list]
            output = " ".join(calls)
            assert "Success" in output

    def test_cmd_export_error(self, cli, mock_detector, mock_configurator):
        """Test cmd_export raises error on export failure."""
        output_path = Path("serena_config.json")
        mock_detector.detect_all.return_value = Mock()
        mock_configurator.export_to_claude_desktop.side_effect = ConfigurationError("Export failed")

        args = argparse.Namespace(output=output_path)
        with pytest.raises(ConfigurationError):
            cli.cmd_export(args)

    def test_cmd_diagnose_success(self, cli, mock_detector, mock_configurator):
        """Test cmd_diagnose shows detailed diagnostic information."""
        mock_result = SerenaDetectionResult(
            uv_available=True,
            uv_path=Path("/usr/bin/uv"),
            serena_available=True,
            serena_path="uvx --from git+https://github.com/oraios/serena serena",
            platform="linux",
            mcp_config_path=Path("/home/user/.config/Claude/claude_desktop_config.json"),
            config_exists=True,
        )
        mock_detector.detect_all.return_value = mock_result
        mock_config = SerenaConfig()
        mock_configurator.get_current_config.return_value = mock_config

        args = argparse.Namespace()
        with patch("builtins.print") as mock_print:
            exit_code = cli.cmd_diagnose(args)
            assert exit_code == 0
            calls = [str(call) for call in mock_print.call_args_list]
            output = " ".join(calls)
            assert "Diagnostics" in output

    def test_cmd_diagnose_no_config(self, cli, mock_detector, mock_configurator):
        """Test cmd_diagnose when config file doesn't exist."""
        mock_result = SerenaDetectionResult(
            uv_available=True,
            uv_path=Path("/usr/bin/uv"),
            serena_available=True,
            serena_path="uvx --from git+https://github.com/oraios/serena serena",
            platform="linux",
            mcp_config_path=Path("/home/user/.config/Claude/claude_desktop_config.json"),
            config_exists=False,
        )
        mock_detector.detect_all.return_value = mock_result

        args = argparse.Namespace()
        with patch("builtins.print") as mock_print:
            exit_code = cli.cmd_diagnose(args)
            assert exit_code == 0
            calls = [str(call) for call in mock_print.call_args_list]
            output = " ".join(calls)
            assert "does not exist" in output

    def test_execute_with_func(self, cli):
        """Test execute calls the function attached to args."""
        mock_func = Mock(return_value=0)
        args = argparse.Namespace(func=mock_func)
        exit_code = cli.execute(args)
        assert exit_code == 0
        mock_func.assert_called_once_with(args)

    def test_execute_no_func(self, cli):
        """Test execute returns 1 when no function is attached."""
        args = argparse.Namespace()
        with patch("builtins.print"):
            exit_code = cli.execute(args)
            assert exit_code == 1

    def test_execute_handles_integration_error(self, cli):
        """Test execute handles SerenaIntegrationError."""
        from ..errors import SerenaIntegrationError

        mock_func = Mock(side_effect=SerenaIntegrationError("Test error"))
        args = argparse.Namespace(func=mock_func)
        with patch("builtins.print"):
            exit_code = cli.execute(args)
            assert exit_code == 1

    def test_execute_handles_unexpected_error(self, cli):
        """Test execute handles unexpected exceptions."""
        mock_func = Mock(side_effect=RuntimeError("Unexpected error"))
        args = argparse.Namespace(func=mock_func)
        with patch("builtins.print"):
            exit_code = cli.execute(args)
            assert exit_code == 2
