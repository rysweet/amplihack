"""Tests for CLI functionality."""

from unittest.mock import Mock, patch

import pytest

from ..cli import ProfileCLI, main


class TestProfileCLI:
    """Test ProfileCLI functionality."""

    @pytest.fixture
    def cli(self, tmp_path):
        """Create ProfileCLI instance with mocked components."""
        with (
            patch("profile_management.cli.ProfileLoader") as mock_loader,
            patch("profile_management.cli.ProfileParser") as mock_parser,
            patch("profile_management.cli.ConfigManager") as mock_config,
            patch("profile_management.cli.ComponentDiscovery") as mock_discovery,
            patch("profile_management.cli.ComponentFilter") as mock_filter,
        ):
            cli = ProfileCLI()
            cli.loader = mock_loader.return_value
            cli.parser = mock_parser.return_value
            cli.config = mock_config.return_value
            cli.discovery = mock_discovery.return_value
            cli.filter = mock_filter.return_value

            return cli

    def test_list_profiles_displays_table(self, cli, tmp_path):
        """Test that list_profiles displays a table of profiles."""
        # Create test profiles directory
        profiles_dir = tmp_path / ".claude" / "profiles"
        profiles_dir.mkdir(parents=True)

        # Create test profile files
        (profiles_dir / "test1.yaml").write_text("content1")
        (profiles_dir / "test2.yaml").write_text("content2")

        # Mock profile loading
        mock_profile = Mock()
        mock_profile.name = "Test Profile"
        mock_profile.description = "Test description"

        cli.loader.load = Mock(return_value="yaml_content")
        cli.parser.parse = Mock(return_value=mock_profile)

        with patch("profile_management.cli.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.glob.return_value = [
                profiles_dir / "test1.yaml",
                profiles_dir / "test2.yaml",
            ]

            # Capture console output
            with patch("profile_management.cli.console") as mock_console:
                cli.list_profiles()

                # Verify console.print was called
                assert mock_console.print.called

    def test_list_profiles_no_profiles(self, cli):
        """Test list_profiles when no profiles directory exists."""
        with patch("profile_management.cli.Path") as mock_path:
            mock_path.return_value.exists.return_value = False

            with patch("profile_management.cli.console") as mock_console:
                cli.list_profiles()

                # Verify warning message was shown
                mock_console.print.assert_called_once()

    def test_show_profile_displays_details(self, cli):
        """Test that show_profile displays profile details."""
        # Mock profile
        mock_profile = Mock()
        mock_profile.name = "Test Profile"
        mock_profile.description = "Test description"
        mock_profile.version = "1.0"
        mock_profile.components.commands.include_all = True
        mock_profile.components.context.include_all = False
        mock_profile.components.context.include = ["PHILOSOPHY.md"]
        mock_profile.components.agents.include_all = True
        mock_profile.components.skills.include_all = False
        mock_profile.components.skills.include_categories = ["coding"]

        cli.loader.load = Mock(return_value="yaml_content")
        cli.parser.parse = Mock(return_value=mock_profile)

        with patch("profile_management.cli.console") as mock_console:
            cli.show_profile("amplihack://profiles/test")

            # Verify console output
            assert mock_console.print.called

    def test_show_profile_current_when_no_uri(self, cli):
        """Test that show_profile shows current profile when no URI provided."""
        cli.config.get_current_profile = Mock(return_value="amplihack://profiles/all")

        mock_profile = Mock()
        mock_profile.name = "All"
        mock_profile.description = "Complete environment"
        mock_profile.version = "1.0"
        mock_profile.components.commands.include_all = True
        mock_profile.components.context.include_all = True
        mock_profile.components.agents.include_all = True
        mock_profile.components.skills.include_all = True

        cli.loader.load = Mock(return_value="yaml_content")
        cli.parser.parse = Mock(return_value=mock_profile)

        with patch("profile_management.cli.console"):
            cli.show_profile()

            # Verify it loaded from config
            cli.config.get_current_profile.assert_called_once()

    def test_show_profile_handles_error(self, cli):
        """Test that show_profile handles loading errors gracefully."""
        cli.loader.load = Mock(side_effect=Exception("Profile not found"))

        with patch("profile_management.cli.console") as mock_console:
            with pytest.raises(SystemExit):
                cli.show_profile("amplihack://profiles/invalid")

            # Verify error message was shown
            mock_console.print.assert_called()

    def test_switch_profile_success(self, cli):
        """Test successful profile switch."""
        mock_profile = Mock()
        mock_profile.name = "Coding Profile"

        cli.loader.load = Mock(return_value="yaml_content")
        cli.parser.parse = Mock(return_value=mock_profile)
        cli.config.set_current_profile = Mock()

        with patch("profile_management.cli.console") as mock_console:
            cli.switch_profile("amplihack://profiles/coding")

            # Verify profile was saved
            cli.config.set_current_profile.assert_called_once_with("amplihack://profiles/coding")

            # Verify success message
            assert mock_console.print.called

    def test_switch_profile_validates_before_saving(self, cli):
        """Test that switch validates profile before saving."""
        cli.loader.load = Mock(side_effect=Exception("Invalid profile"))

        with patch("profile_management.cli.console"):
            with pytest.raises(SystemExit):
                cli.switch_profile("amplihack://profiles/invalid")

            # Verify config was NOT updated
            cli.config.set_current_profile.assert_not_called()

    def test_current_profile(self, cli):
        """Test showing current profile."""
        cli.config.get_current_profile = Mock(return_value="amplihack://profiles/coding")
        cli.config.is_env_override_active = Mock(return_value=False)

        mock_profile = Mock()
        mock_profile.name = "Coding"
        mock_profile.description = "Development profile"
        mock_profile.version = "1.0"
        mock_profile.components.commands.include_all = True
        mock_profile.components.context.include_all = True
        mock_profile.components.agents.include_all = True
        mock_profile.components.skills.include_all = True

        cli.loader.load = Mock(return_value="yaml_content")
        cli.parser.parse = Mock(return_value=mock_profile)

        with patch("profile_management.cli.console"):
            cli.current_profile()

            # Verify it loaded current profile
            cli.config.get_current_profile.assert_called()

    def test_current_profile_shows_env_warning(self, cli):
        """Test that current_profile shows warning when env override active."""
        cli.config.get_current_profile = Mock(return_value="amplihack://profiles/coding")
        cli.config.is_env_override_active = Mock(return_value=True)

        mock_profile = Mock()
        mock_profile.name = "Coding"
        mock_profile.description = "Development profile"
        mock_profile.version = "1.0"
        mock_profile.components.commands.include_all = True
        mock_profile.components.context.include_all = True
        mock_profile.components.agents.include_all = True
        mock_profile.components.skills.include_all = True

        cli.loader.load = Mock(return_value="yaml_content")
        cli.parser.parse = Mock(return_value=mock_profile)

        with patch("profile_management.cli.console") as mock_console:
            cli.current_profile()

            # Verify environment warning was shown
            assert any(
                "environment variable" in str(call).lower()
                for call in mock_console.print.call_args_list
            )

    def test_validate_profile_success(self, cli):
        """Test successful profile validation."""
        mock_profile = Mock()
        mock_profile.name = "Test Profile"
        mock_profile.components.commands.include_all = True
        mock_profile.components.agents.include_all = True

        cli.loader.load = Mock(return_value="yaml_content")
        cli.parser.parse = Mock(return_value=mock_profile)

        with patch("profile_management.cli.console") as mock_console:
            cli.validate_profile("amplihack://profiles/test")

            # Verify success message
            assert mock_console.print.called

    def test_validate_profile_shows_warnings(self, cli):
        """Test that validate shows warnings for empty specs."""
        mock_profile = Mock()
        mock_profile.name = "Test Profile"
        mock_profile.components.commands.include_all = False
        mock_profile.components.commands.include = []
        mock_profile.components.agents.include_all = False
        mock_profile.components.agents.include = []

        cli.loader.load = Mock(return_value="yaml_content")
        cli.parser.parse = Mock(return_value=mock_profile)

        with patch("profile_management.cli.console") as mock_console:
            cli.validate_profile("amplihack://profiles/test")

            # Verify warnings were shown
            assert any("Warning" in str(call) for call in mock_console.print.call_args_list)

    def test_validate_profile_fails_on_error(self, cli):
        """Test that validate exits on profile error."""
        cli.loader.load = Mock(side_effect=Exception("Invalid YAML"))

        with patch("profile_management.cli.console"):
            with pytest.raises(SystemExit):
                cli.validate_profile("amplihack://profiles/invalid")


class TestMainCLI:
    """Test main CLI entry point."""

    def test_main_no_args(self):
        """Test main with no arguments shows usage."""
        with patch("sys.argv", ["profile"]):
            with patch("profile_management.cli.console") as mock_console:
                with pytest.raises(SystemExit):
                    main()

                # Verify usage message was shown
                assert mock_console.print.called

    def test_main_list_command(self):
        """Test main with list command."""
        with patch("sys.argv", ["profile", "list"]):
            with patch("profile_management.cli.ProfileCLI") as mock_cli:
                main()

                # Verify list_profiles was called
                mock_cli.return_value.list_profiles.assert_called_once()

    def test_main_show_command(self):
        """Test main with show command."""
        with patch("sys.argv", ["profile", "show", "amplihack://profiles/test"]):
            with patch("profile_management.cli.ProfileCLI") as mock_cli:
                main()

                # Verify show_profile was called with URI
                mock_cli.return_value.show_profile.assert_called_once_with(
                    "amplihack://profiles/test"
                )

    def test_main_show_command_no_uri(self):
        """Test main with show command but no URI."""
        with patch("sys.argv", ["profile", "show"]):
            with patch("profile_management.cli.ProfileCLI") as mock_cli:
                main()

                # Verify show_profile was called without URI
                mock_cli.return_value.show_profile.assert_called_once_with(None)

    def test_main_current_command(self):
        """Test main with current command."""
        with patch("sys.argv", ["profile", "current"]):
            with patch("profile_management.cli.ProfileCLI") as mock_cli:
                main()

                # Verify current_profile was called
                mock_cli.return_value.current_profile.assert_called_once()

    def test_main_switch_command(self):
        """Test main with switch command."""
        with patch("sys.argv", ["profile", "switch", "amplihack://profiles/coding"]):
            with patch("profile_management.cli.ProfileCLI") as mock_cli:
                main()

                # Verify switch_profile was called
                mock_cli.return_value.switch_profile.assert_called_once_with(
                    "amplihack://profiles/coding"
                )

    def test_main_switch_command_no_uri(self):
        """Test main with switch command but no URI."""
        with patch("sys.argv", ["profile", "switch"]):
            with patch("profile_management.cli.console") as mock_console:
                with pytest.raises(SystemExit):
                    main()

                # Verify error message was shown
                assert mock_console.print.called

    def test_main_validate_command(self):
        """Test main with validate command."""
        with patch("sys.argv", ["profile", "validate", "amplihack://profiles/test"]):
            with patch("profile_management.cli.ProfileCLI") as mock_cli:
                main()

                # Verify validate_profile was called
                mock_cli.return_value.validate_profile.assert_called_once_with(
                    "amplihack://profiles/test"
                )

    def test_main_validate_command_no_uri(self):
        """Test main with validate command but no URI."""
        with patch("sys.argv", ["profile", "validate"]):
            with patch("profile_management.cli.console") as mock_console:
                with pytest.raises(SystemExit):
                    main()

                # Verify error message was shown
                assert mock_console.print.called

    def test_main_unknown_command(self):
        """Test main with unknown command."""
        with patch("sys.argv", ["profile", "unknown"]):
            with patch("profile_management.cli.console") as mock_console:
                with pytest.raises(SystemExit):
                    main()

                # Verify error message was shown
                assert mock_console.print.called


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
