"""Tests for amplifier command UVX deployment behavior.

This test suite ensures that the amplifier command correctly skips Claude Code
plugin installation when running in UVX mode, while still copying necessary files
to ~/.amplihack/.claude for the Amplifier bundle system.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch


class TestAmplifierUVXDeployment:
    """Test that amplifier command skips plugin installation in UVX mode."""

    @patch("src.amplihack.cli.is_uvx_deployment")
    @patch("src.amplihack.cli.copytree_manifest")
    @patch("src.amplihack.cli.get_claude_cli_path")
    @patch("src.amplihack.cli._configure_amplihack_marketplace")
    @patch("src.amplihack.launcher.amplifier.launch_amplifier")
    def test_amplifier_command_skips_plugin_installation(
        self,
        mock_launch_amplifier,
        mock_configure_marketplace,
        mock_get_claude_cli,
        mock_copytree,
        mock_is_uvx,
    ):
        """Test that 'amplihack amplifier' skips Claude Code plugin installation.

        This is the core fix: when running 'amplihack amplifier', we should NOT
        attempt to install the Claude Code plugin since Amplifier uses its own
        bundle system.
        """
        from src.amplihack.cli import main

        # Simulate UVX deployment mode
        mock_is_uvx.return_value = True
        mock_launch_amplifier.return_value = 0
        mock_copytree.return_value = True  # Simulate successful file copy

        # Run amplifier command
        with patch("sys.argv", ["amplihack", "amplifier"]):
            exit_code = main(["amplifier"])

        # Verify that Claude Code plugin installation was NOT attempted
        # Neither marketplace configuration nor plugin install should be called
        mock_configure_marketplace.assert_not_called()
        mock_get_claude_cli.assert_not_called()

        # Verify that amplifier launcher was called
        mock_launch_amplifier.assert_called_once()
        assert exit_code == 0

    @patch("src.amplihack.cli.is_uvx_deployment")
    @patch("src.amplihack.cli.copytree_manifest")
    @patch("src.amplihack.launcher.amplifier.launch_amplifier")
    def test_amplifier_command_copies_files_to_claude_dir(
        self,
        mock_launch_amplifier,
        mock_copytree,
        mock_is_uvx,
    ):
        """Test that amplifier command still copies files to ~/.amplihack/.claude.

        Even though we skip plugin installation, we still need to copy the files
        to ~/.amplihack/.claude where the Amplifier bundle expects them.
        """
        from src.amplihack.cli import main

        # Simulate UVX deployment mode
        mock_is_uvx.return_value = True
        mock_launch_amplifier.return_value = 0
        mock_copytree.return_value = True

        # Run amplifier command
        exit_code = main(["amplifier"])

        # Verify files were copied to ~/.amplihack/.claude
        expected_target = str(Path.home() / ".amplihack" / ".claude")
        mock_copytree.assert_called_once()
        call_args = mock_copytree.call_args
        assert expected_target in str(call_args)

        assert exit_code == 0

    @patch("src.amplihack.cli.is_uvx_deployment")
    @patch("src.amplihack.cli.copytree_manifest")
    @patch("src.amplihack.cli.get_claude_cli_path")
    @patch("src.amplihack.cli._configure_amplihack_marketplace")
    @patch("src.amplihack.cli.subprocess.run")
    def test_launch_command_still_attempts_plugin_installation(
        self,
        mock_subprocess_run,
        mock_configure_marketplace,
        mock_get_claude_cli,
        mock_copytree,
        mock_is_uvx,
    ):
        """Test that 'amplihack launch' still attempts plugin installation.

        This ensures we haven't broken the normal plugin installation flow for
        the launch command and other commands.
        """
        from src.amplihack.cli import main

        # Simulate UVX deployment mode
        mock_is_uvx.return_value = True
        mock_copytree.return_value = True  # Simulate successful file copy
        mock_configure_marketplace.return_value = True
        mock_get_claude_cli.return_value = "/usr/local/bin/claude"

        # Mock successful plugin installation
        mock_subprocess_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        # Run launch command - we'll let it fail after plugin installation
        # We just want to verify the plugin installation logic runs
        try:
            main(["launch", "--", "-p", "test"])
        except SystemExit:
            pass  # Expected to fail when trying to launch Claude
        except Exception:
            pass  # Any other error is also fine for this test

        # Verify that plugin installation WAS attempted for launch command
        mock_configure_marketplace.assert_called_once()
        mock_get_claude_cli.assert_called_once_with(auto_install=True)

        # Verify subprocess.run was called for plugin installation
        assert mock_subprocess_run.called
        install_call = None
        for call_obj in mock_subprocess_run.call_args_list:
            args = call_obj[0][0] if call_obj[0] else []
            if "plugin" in args and "install" in args:
                install_call = call_obj
                break

        assert install_call is not None, "Expected 'claude plugin install' to be called"

    @patch("src.amplihack.cli.is_uvx_deployment")
    @patch("src.amplihack.cli.copytree_manifest")
    @patch("src.amplihack.cli.get_claude_cli_path")
    @patch("src.amplihack.cli._configure_amplihack_marketplace")
    @patch("src.amplihack.launcher.amplifier.launch_amplifier")
    def test_amplifier_command_no_error_messages(
        self,
        mock_launch_amplifier,
        mock_configure_marketplace,
        mock_get_claude_cli,
        mock_copytree,
        mock_is_uvx,
        capsys,
    ):
        """Test that amplifier command produces no plugin-related error messages.

        This validates the user experience - no confusing warnings or errors about
        plugin installation when running the amplifier command.
        """
        from src.amplihack.cli import main

        # Simulate UVX deployment mode
        mock_is_uvx.return_value = True
        mock_launch_amplifier.return_value = 0
        mock_copytree.return_value = True  # Simulate successful file copy

        # Run amplifier command
        exit_code = main(["amplifier"])

        # Capture output
        captured = capsys.readouterr()

        # Verify no plugin-related error messages
        assert "Plugin installation failed" not in captured.out
        assert "Plugin installation failed" not in captured.err
        assert "not found in any configured marketplace" not in captured.out
        assert "not found in any configured marketplace" not in captured.err
        assert "Falling back to directory copy mode" not in captured.out
        assert "Falling back to directory copy mode" not in captured.err

        assert exit_code == 0

    @patch("src.amplihack.cli.is_uvx_deployment")
    def test_amplifier_command_non_uvx_mode(self, mock_is_uvx):
        """Test that amplifier command works correctly in non-UVX mode.

        When not in UVX mode, the plugin installation logic should be skipped
        entirely (not just for amplifier, but for all commands).
        """
        from src.amplihack.cli import main

        # Simulate non-UVX mode
        mock_is_uvx.return_value = False

        with patch("src.amplihack.launcher.amplifier.launch_amplifier") as mock_launch:
            mock_launch.return_value = 0
            exit_code = main(["amplifier"])

        # Verify amplifier was launched
        mock_launch.assert_called_once()
        assert exit_code == 0


class TestAmplifierCommandArgParsing:
    """Test that argument parsing happens before UVX plugin installation."""

    @patch("src.amplihack.cli.is_uvx_deployment")
    @patch("src.amplihack.cli.copytree_manifest")
    @patch("src.amplihack.cli.parse_args_with_passthrough")
    @patch("src.amplihack.launcher.amplifier.launch_amplifier")
    def test_args_parsed_before_plugin_decision(
        self,
        mock_launch_amplifier,
        mock_parse_args,
        mock_copytree,
        mock_is_uvx,
    ):
        """Test that arguments are parsed to determine command before plugin logic.

        This is a key architectural requirement: we need to know which command
        is being run BEFORE deciding whether to install the Claude Code plugin.
        """
        import argparse

        from src.amplihack.cli import main

        # Simulate UVX deployment mode
        mock_is_uvx.return_value = True
        mock_launch_amplifier.return_value = 0
        mock_copytree.return_value = True  # Simulate successful file copy

        # Mock parse_args to return amplifier command
        mock_args = argparse.Namespace(command="amplifier")
        mock_parse_args.return_value = (mock_args, [])

        # Run amplifier command
        with patch("src.amplihack.cli._configure_amplihack_marketplace") as mock_config:
            exit_code = main(["amplifier"])

            # Verify args were parsed
            mock_parse_args.assert_called_once()

            # Verify plugin installation was NOT attempted
            mock_config.assert_not_called()

        assert exit_code == 0
