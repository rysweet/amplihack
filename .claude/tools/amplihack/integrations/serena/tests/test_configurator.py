"""Unit tests for Serena configurator."""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from ..configurator import SerenaConfig, SerenaConfigurator
from ..detector import SerenaDetector
from ..errors import ConfigurationError


class TestSerenaConfig:
    """Tests for SerenaConfig dataclass."""

    def test_default_initialization(self):
        """Test SerenaConfig initializes with correct defaults."""
        config = SerenaConfig()
        assert config.name == "serena"
        assert config.command == "uvx"
        assert config.args == [
            "--from",
            "git+https://github.com/oraios/serena",
            "serena",
        ]
        assert config.env == {}

    def test_custom_initialization(self):
        """Test SerenaConfig with custom values."""
        config = SerenaConfig(
            name="serena",
            command="custom-uvx",
            args=["--custom", "arg"],
            env={"VAR": "value"},
        )
        assert config.command == "custom-uvx"
        assert config.args == ["--custom", "arg"]
        assert config.env == {"VAR": "value"}

    def test_to_dict(self):
        """Test to_dict converts config to dictionary."""
        config = SerenaConfig()
        config_dict = config.to_dict()
        assert config_dict == {
            "command": "uvx",
            "args": [
                "--from",
                "git+https://github.com/oraios/serena",
                "serena",
            ],
            "env": {},
        }

    def test_from_dict(self):
        """Test from_dict creates config from dictionary."""
        data = {
            "command": "uvx",
            "args": ["--from", "git+https://github.com/oraios/serena", "serena"],
            "env": {"KEY": "value"},
        }
        config = SerenaConfig.from_dict(data)
        assert config.command == "uvx"
        assert config.args == data["args"]
        assert config.env == {"KEY": "value"}


class TestSerenaConfigurator:
    """Tests for SerenaConfigurator class."""

    @pytest.fixture
    def mock_detector(self):
        """Create a mock SerenaDetector."""
        detector = Mock(spec=SerenaDetector)
        detector.get_mcp_config_path.return_value = Path(
            "/home/user/.config/Claude/claude_desktop_config.json"
        )
        return detector

    @pytest.fixture
    def configurator(self, mock_detector):
        """Create a SerenaConfigurator with mock detector."""
        return SerenaConfigurator(detector=mock_detector)

    def test_initialization_with_detector(self, mock_detector):
        """Test configurator initializes with provided detector."""
        configurator = SerenaConfigurator(detector=mock_detector)
        assert configurator.detector is mock_detector

    def test_initialization_without_detector(self):
        """Test configurator creates detector when not provided."""
        configurator = SerenaConfigurator()
        assert isinstance(configurator.detector, SerenaDetector)

    def test_is_configured_true(self, configurator, mock_detector):
        """Test is_configured returns True when Serena is present."""
        config_data = {"mcpServers": {"serena": {"command": "uvx"}}}
        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(
                configurator, "_read_config", return_value=config_data
            ):
                assert configurator.is_configured() is True

    def test_is_configured_false_missing_serena(self, configurator, mock_detector):
        """Test is_configured returns False when Serena is not present."""
        config_data = {"mcpServers": {"other": {"command": "other-cmd"}}}
        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(
                configurator, "_read_config", return_value=config_data
            ):
                assert configurator.is_configured() is False

    def test_is_configured_false_no_config_file(self, configurator, mock_detector):
        """Test is_configured returns False when config file doesn't exist."""
        assert configurator.is_configured() is False

    def test_is_configured_false_no_config_path(self, configurator):
        """Test is_configured returns False when config path is None."""
        configurator.detector.get_mcp_config_path.return_value = None
        assert configurator.is_configured() is False

    def test_is_configured_read_error(self, configurator, mock_detector):
        """Test is_configured raises ConfigurationError on read failure."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(
                configurator, "_read_config", side_effect=Exception("Read failed")
            ):
                with pytest.raises(ConfigurationError):
                    configurator.is_configured()

    def test_add_to_mcp_servers_success_new_file(self, configurator, mock_detector):
        """Test add_to_mcp_servers creates new config file."""
        with patch("pathlib.Path.exists", return_value=False):
            with patch.object(configurator, "_write_config") as mock_write:
                result = configurator.add_to_mcp_servers()
                assert result is True
                mock_write.assert_called_once()
                # Verify the config contains serena
                written_config = mock_write.call_args[0][1]
                assert "mcpServers" in written_config
                assert "serena" in written_config["mcpServers"]

    def test_add_to_mcp_servers_success_existing_file(
        self, configurator, mock_detector
    ):
        """Test add_to_mcp_servers adds to existing config."""
        existing_config = {"mcpServers": {"other": {"command": "other-cmd"}}}
        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(
                configurator, "_read_config", return_value=existing_config
            ):
                with patch.object(configurator, "_write_config") as mock_write:
                    result = configurator.add_to_mcp_servers()
                    assert result is True
                    # Verify existing server is preserved
                    written_config = mock_write.call_args[0][1]
                    assert "other" in written_config["mcpServers"]
                    assert "serena" in written_config["mcpServers"]

    def test_add_to_mcp_servers_already_configured(
        self, configurator, mock_detector
    ):
        """Test add_to_mcp_servers returns False when already configured."""
        existing_config = {
            "mcpServers": {
                "serena": {"command": "uvx"},
            }
        }
        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(
                configurator, "_read_config", return_value=existing_config
            ):
                result = configurator.add_to_mcp_servers()
                assert result is False

    def test_add_to_mcp_servers_no_config_path(self, configurator):
        """Test add_to_mcp_servers raises error when config path is None."""
        configurator.detector.get_mcp_config_path.return_value = None
        with pytest.raises(ConfigurationError):
            configurator.add_to_mcp_servers()

    def test_add_to_mcp_servers_read_error(self, configurator, mock_detector):
        """Test add_to_mcp_servers raises error on read failure."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(
                configurator, "_read_config", side_effect=Exception("Read failed")
            ):
                with pytest.raises(ConfigurationError):
                    configurator.add_to_mcp_servers()

    def test_add_to_mcp_servers_write_error(self, configurator, mock_detector):
        """Test add_to_mcp_servers raises error on write failure."""
        with patch("pathlib.Path.exists", return_value=False):
            with patch.object(
                configurator, "_write_config", side_effect=Exception("Write failed")
            ):
                with pytest.raises(ConfigurationError):
                    configurator.add_to_mcp_servers()

    def test_remove_from_mcp_servers_success(self, configurator, mock_detector):
        """Test remove_from_mcp_servers removes Serena configuration."""
        existing_config = {
            "mcpServers": {
                "serena": {"command": "uvx"},
                "other": {"command": "other-cmd"},
            }
        }
        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(
                configurator, "_read_config", return_value=existing_config
            ):
                with patch.object(configurator, "_write_config") as mock_write:
                    result = configurator.remove_from_mcp_servers()
                    assert result is True
                    # Verify serena is removed but other is preserved
                    written_config = mock_write.call_args[0][1]
                    assert "serena" not in written_config["mcpServers"]
                    assert "other" in written_config["mcpServers"]

    def test_remove_from_mcp_servers_not_configured(
        self, configurator, mock_detector
    ):
        """Test remove_from_mcp_servers returns False when not configured."""
        existing_config = {"mcpServers": {"other": {"command": "other-cmd"}}}
        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(
                configurator, "_read_config", return_value=existing_config
            ):
                result = configurator.remove_from_mcp_servers()
                assert result is False

    def test_remove_from_mcp_servers_no_config_file(
        self, configurator, mock_detector
    ):
        """Test remove_from_mcp_servers returns False when config doesn't exist."""
        assert configurator.remove_from_mcp_servers() is False

    def test_remove_from_mcp_servers_read_error(self, configurator, mock_detector):
        """Test remove_from_mcp_servers raises error on read failure."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(
                configurator, "_read_config", side_effect=Exception("Read failed")
            ):
                with pytest.raises(ConfigurationError):
                    configurator.remove_from_mcp_servers()

    def test_remove_from_mcp_servers_write_error(self, configurator, mock_detector):
        """Test remove_from_mcp_servers raises error on write failure."""
        existing_config = {"mcpServers": {"serena": {"command": "uvx"}}}
        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(
                configurator, "_read_config", return_value=existing_config
            ):
                with patch.object(
                    configurator, "_write_config", side_effect=Exception("Write failed")
                ):
                    with pytest.raises(ConfigurationError):
                        configurator.remove_from_mcp_servers()

    def test_get_current_config_exists(self, configurator, mock_detector):
        """Test get_current_config returns config when it exists."""
        config_data = {
            "mcpServers": {
                "serena": {
                    "command": "uvx",
                    "args": ["--from", "git+https://github.com/oraios/serena", "serena"],
                    "env": {},
                }
            }
        }
        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(
                configurator, "_read_config", return_value=config_data
            ):
                config = configurator.get_current_config()
                assert config is not None
                assert config.command == "uvx"
                assert config.name == "serena"

    def test_get_current_config_not_exists(self, configurator, mock_detector):
        """Test get_current_config returns None when Serena not configured."""
        config_data = {"mcpServers": {"other": {"command": "other-cmd"}}}
        with patch("pathlib.Path.exists", return_value=True):
            with patch.object(
                configurator, "_read_config", return_value=config_data
            ):
                config = configurator.get_current_config()
                assert config is None

    def test_get_current_config_no_file(self, configurator, mock_detector):
        """Test get_current_config returns None when config file doesn't exist."""
        assert configurator.get_current_config() is None

    def test_export_to_claude_desktop_success(self, configurator, mock_detector):
        """Test export_to_claude_desktop writes config snippet."""
        output_path = Path("/tmp/serena_config.json")
        with patch.object(configurator, "_write_config") as mock_write:
            result = configurator.export_to_claude_desktop(output_path)
            assert result is True
            mock_write.assert_called_once()
            written_config = mock_write.call_args[0][1]
            assert "mcpServers" in written_config
            assert "serena" in written_config["mcpServers"]

    def test_export_to_claude_desktop_write_error(self, configurator, mock_detector):
        """Test export_to_claude_desktop raises error on write failure."""
        output_path = Path("/tmp/serena_config.json")
        with patch.object(
            configurator, "_write_config", side_effect=Exception("Write failed")
        ):
            with pytest.raises(ConfigurationError):
                configurator.export_to_claude_desktop(output_path)

    def test_read_config_success(self, configurator):
        """Test _read_config parses JSON correctly."""
        config_data = {"mcpServers": {"serena": {"command": "uvx"}}}
        json_content = json.dumps(config_data)
        m = mock_open(read_data=json_content)
        with patch("builtins.open", m):
            result = configurator._read_config(Path("/tmp/config.json"))
            assert result == config_data

    def test_write_config_success(self, configurator):
        """Test _write_config writes JSON with proper formatting."""
        config_data = {"mcpServers": {"serena": {"command": "uvx"}}}
        m = mock_open()
        with patch("builtins.open", m):
            with patch("pathlib.Path.mkdir"):
                configurator._write_config(Path("/tmp/config.json"), config_data)
                # Verify write was called
                m.assert_called_once()
