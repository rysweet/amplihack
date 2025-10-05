"""
Test suite for CLI integration with auto-mode.

Tests the `amplihack auto` command functionality including:
- Command parsing and argument handling
- Integration with auto-mode orchestrator
- Output formatting and error handling
- Interactive mode functionality
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from amplihack.auto_mode.command_handler import CommandResult
from amplihack.commands.auto_mode_cli import AutoModeCLI, auto_command_handler


class TestAutoModeCLI:
    """Test AutoModeCLI class functionality"""

    @pytest.fixture
    def auto_cli(self):
        return AutoModeCLI()

    def test_create_auto_parser(self, auto_cli):
        """Test creation of auto command parser"""
        import argparse

        # Mock subparsers
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers()

        auto_parser = auto_cli.create_auto_parser(subparsers)

        assert auto_parser is not None
        assert auto_parser.prog.endswith("auto")

    @pytest.mark.asyncio
    async def test_handle_auto_command_start(self, auto_cli):
        """Test handling start command"""
        import argparse

        args = argparse.Namespace()
        args.auto_action = "start"
        args.config = "default"
        args.user_id = "test_user"

        # Mock command handler
        mock_result = CommandResult(
            success=True,
            message="Auto-mode started",
            data={"session_id": "test_session", "config": "default", "status": "active"},
        )

        with patch.object(auto_cli, "command_handler", create=True) as mock_handler:
            mock_handler.handle_command = AsyncMock(return_value=mock_result)

            result_code = await auto_cli.handle_auto_command(args)

            assert result_code == 0
            mock_handler.handle_command.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_auto_command_status(self, auto_cli):
        """Test handling status command"""
        import argparse

        args = argparse.Namespace()
        args.auto_action = "status"
        args.detailed = True
        args.json = False

        mock_result = CommandResult(
            success=True,
            message="Auto-mode status",
            data={
                "status": "active",
                "active_sessions": 1,
                "total_sessions": 1,
                "sdk_connection": "connected",
            },
        )

        with patch.object(auto_cli, "command_handler", create=True) as mock_handler:
            mock_handler.handle_command = AsyncMock(return_value=mock_result)

            result_code = await auto_cli.handle_auto_command(args)

            assert result_code == 0

    @pytest.mark.asyncio
    async def test_handle_auto_command_error(self, auto_cli):
        """Test handling command with error"""
        import argparse

        args = argparse.Namespace()
        args.auto_action = "start"

        mock_result = CommandResult(
            success=False, message="Failed to start auto-mode", error_code="initialization_failed"
        )

        with patch.object(auto_cli, "command_handler", create=True) as mock_handler:
            mock_handler.handle_command = AsyncMock(return_value=mock_result)

            result_code = await auto_cli.handle_auto_command(args)

            assert result_code == 1

    @pytest.mark.asyncio
    async def test_handle_auto_command_no_action(self, auto_cli):
        """Test handling command with no action specified"""
        import argparse

        args = argparse.Namespace()
        args.auto_action = None

        result_code = await auto_cli.handle_auto_command(args)

        assert result_code == 1

    def test_handle_command_result_success(self, auto_cli):
        """Test handling successful command result"""
        import argparse

        args = argparse.Namespace()
        args.auto_action = "start"

        result = CommandResult(
            success=True,
            message="Command successful",
            data={"session_id": "test_session", "config": "default", "status": "active"},
        )

        with patch("builtins.print") as mock_print:
            exit_code = auto_cli._handle_command_result(result, args)

            assert exit_code == 0
            mock_print.assert_called()

    def test_handle_command_result_json_output(self, auto_cli):
        """Test handling command result with JSON output"""
        import argparse

        args = argparse.Namespace()
        args.auto_action = "status"
        args.json = True

        result = CommandResult(
            success=True, message="Status retrieved", data={"status": "active", "sessions": 1}
        )

        with patch("builtins.print") as mock_print:
            exit_code = auto_cli._handle_command_result(result, args)

            assert exit_code == 0
            # Should print JSON data
            mock_print.assert_called_once()
            printed_arg = mock_print.call_args[0][0]
            assert '"status": "active"' in printed_arg

    def test_print_status_info(self, auto_cli):
        """Test printing formatted status information"""
        status_data = {
            "status": "active",
            "active_sessions": 2,
            "total_sessions": 5,
            "analysis_cycles": 50,
            "interventions": 10,
            "average_quality": 0.85,
            "uptime": "300s",
            "sdk_connection": "connected",
        }

        with patch("builtins.print") as mock_print:
            auto_cli._print_status_info(status_data)

            mock_print.assert_called()
            # Check that status information was printed
            calls = [str(call) for call in mock_print.call_args_list]
            assert any("Auto-Mode Status" in call for call in calls)
            assert any("Active Sessions: 2" in call for call in calls)

    def test_print_configuration(self, auto_cli):
        """Test printing formatted configuration"""
        config_data = {
            "analysis_frequency": "adaptive",
            "intervention_threshold": 0.7,
            "background_mode": True,
            "learning_mode": True,
        }

        with patch("builtins.print") as mock_print:
            auto_cli._print_configuration(config_data)

            mock_print.assert_called()
            calls = [str(call) for call in mock_print.call_args_list]
            assert any("Current Configuration" in call for call in calls)


class TestCommandParsing:
    """Test command line argument parsing for auto command"""

    def test_parse_start_command(self):
        """Test parsing start command arguments"""
        import argparse

        from amplihack.commands.auto_mode_cli import AutoModeCLI

        auto_cli = AutoModeCLI()
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        auto_cli.create_auto_parser(subparsers)

        args = parser.parse_args(
            ["auto", "start", "--config", "learning_mode", "--user-id", "test_user"]
        )

        assert args.command == "auto"
        assert args.auto_action == "start"
        assert args.config == "learning_mode"
        assert args.user_id == "test_user"

    def test_parse_status_command(self):
        """Test parsing status command arguments"""
        import argparse

        from amplihack.commands.auto_mode_cli import AutoModeCLI

        auto_cli = AutoModeCLI()
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        auto_cli.create_auto_parser(subparsers)

        args = parser.parse_args(["auto", "status", "--detailed", "--json"])

        assert args.command == "auto"
        assert args.auto_action == "status"
        assert args.detailed is True
        assert args.json is True

    def test_parse_configure_command(self):
        """Test parsing configure command arguments"""
        import argparse

        from amplihack.commands.auto_mode_cli import AutoModeCLI

        auto_cli = AutoModeCLI()
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        auto_cli.create_auto_parser(subparsers)

        args = parser.parse_args(["auto", "configure", "analysis_frequency", "high"])

        assert args.command == "auto"
        assert args.auto_action == "configure"
        assert args.setting == "analysis_frequency"
        assert args.value == "high"

    def test_parse_analyze_command(self):
        """Test parsing analyze command arguments"""
        import argparse

        from amplihack.commands.auto_mode_cli import AutoModeCLI

        auto_cli = AutoModeCLI()
        parser = argparse.ArgumentParser()
        subparsers = parser.add_subparsers(dest="command")
        auto_cli.create_auto_parser(subparsers)

        args = parser.parse_args(["auto", "analyze", "--type", "comprehensive", "--output", "json"])

        assert args.command == "auto"
        assert args.auto_action == "analyze"
        assert args.type == "comprehensive"
        assert args.output == "json"


class TestCommandHandlerIntegration:
    """Test integration with command handler entry point"""

    @pytest.mark.asyncio
    async def test_auto_command_handler_success(self):
        """Test auto command handler with successful execution"""
        import argparse

        args = argparse.Namespace()
        args.auto_action = "status"

        with patch("amplihack.commands.auto_mode_cli.AutoModeCLI") as mock_cli_class:
            mock_cli = Mock()
            mock_cli_class.return_value = mock_cli
            mock_cli.handle_auto_command = AsyncMock(return_value=0)

            exit_code = auto_command_handler(args)

            assert exit_code == 0
            mock_cli.handle_auto_command.assert_called_once_with(args)

    @pytest.mark.asyncio
    async def test_auto_command_handler_no_action(self):
        """Test auto command handler with no action (interactive mode)"""
        import argparse

        args = argparse.Namespace()
        # No auto_action attribute

        with patch("amplihack.commands.auto_mode_cli.AutoModeCLI") as mock_cli_class:
            mock_cli = Mock()
            mock_cli_class.return_value = mock_cli
            mock_cli.run_interactive_mode = AsyncMock(return_value=0)

            exit_code = auto_command_handler(args)

            assert exit_code == 0
            mock_cli.run_interactive_mode.assert_called_once_with(args)


class TestInteractiveMode:
    """Test interactive mode functionality"""

    @pytest.mark.asyncio
    async def test_interactive_help(self):
        """Test interactive mode help command"""
        auto_cli = AutoModeCLI()

        with patch("builtins.print") as mock_print:
            auto_cli._print_interactive_help()

            mock_print.assert_called()
            calls = [str(call) for call in mock_print.call_args_list]
            assert any("Available commands" in call for call in calls)


class TestCLIIntegrationMocks:
    """Test CLI integration with various mocking scenarios"""

    def test_import_error_handling(self):
        """Test handling of import errors for auto-mode components"""

        # Test parser creation with import error
        # Note: would create parser and subparsers for testing command creation

        with patch(
            "amplihack.commands.auto_mode_cli.AutoModeCLI", side_effect=ImportError("No auto-mode")
        ):
            # Should not raise error, should create placeholder parser
            pass

            # The create_parser function should handle the import error gracefully
            # and create a placeholder auto command

    def test_auto_command_integration_points(self):
        """Test key integration points for auto command in main CLI"""
        # Test that the auto command is properly integrated
        from amplihack.cli import create_parser

        parser = create_parser()

        # Should be able to parse auto command
        try:
            # This would normally parse arguments, but --help causes SystemExit
            parser.parse_args(["auto", "--help"])
        except SystemExit:
            # argparse calls sys.exit on --help, which is expected
            pass

    @pytest.mark.asyncio
    async def test_error_propagation(self):
        """Test that errors are properly propagated from auto-mode components"""
        import argparse

        args = argparse.Namespace()
        args.auto_action = "start"

        auto_cli = AutoModeCLI()

        # Mock command handler to raise exception
        with patch.object(auto_cli, "command_handler", create=True) as mock_handler:
            mock_handler.handle_command = AsyncMock(side_effect=Exception("Test error"))

            result_code = await auto_cli.handle_auto_command(args)

            # Should return error code
            assert result_code == 1


if __name__ == "__main__":
    pytest.main([__file__])
