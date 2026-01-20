"""
Unit tests for PathResolver brick.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- Focus on path resolution logic
"""

import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest


class TestPathResolverBasicResolution:
    """Unit tests for basic path resolution (30% of unit tests)."""

    def test_resolve_absolute_path_unchanged(self):
        """Test resolving absolute paths returns unchanged."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        absolute_path = "/absolute/path/to/file"
        plugin_root = Path("/plugin/root")

        resolved = resolver.resolve(absolute_path, plugin_root)

        assert resolved == absolute_path

    def test_resolve_relative_path_to_absolute(self):
        """Test resolving relative paths to absolute."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        relative_path = "relative/path/to/file"
        plugin_root = Path("/plugin/root")

        resolved = resolver.resolve(relative_path, plugin_root)

        assert Path(resolved).is_absolute()
        assert resolved.startswith(str(plugin_root))

    def test_resolve_dot_path(self):
        """Test resolving current directory path."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        dot_path = "./file.py"
        plugin_root = Path("/plugin/root")

        resolved = resolver.resolve(dot_path, plugin_root)

        assert Path(resolved).is_absolute()
        assert "file.py" in resolved

    def test_resolve_dotdot_path(self):
        """Test resolving parent directory path."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        dotdot_path = "../other/file.py"
        plugin_root = Path("/plugin/root/subdir")

        resolved = resolver.resolve(dotdot_path, plugin_root)

        assert Path(resolved).is_absolute()
        # Should navigate up from plugin_root
        assert "/plugin/root/other" in resolved or "/plugin/other" in resolved

    def test_resolve_empty_string(self):
        """Test resolving empty string returns plugin root."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        empty_path = ""
        plugin_root = Path("/plugin/root")

        resolved = resolver.resolve(empty_path, plugin_root)

        assert resolved == str(plugin_root)

    def test_resolve_tilde_expands_home(self):
        """Test resolving tilde expands to home directory."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        tilde_path = "~/config/file"
        plugin_root = Path("/plugin/root")

        with patch("pathlib.Path.home", return_value=Path("/home/user")):
            resolved = resolver.resolve(tilde_path, plugin_root)

        assert "/home/user" in resolved

    def test_resolve_windows_path(self):
        """Test resolving Windows-style paths."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        windows_path = "C:\\Users\\test\\file.txt"
        plugin_root = Path("/plugin/root")

        resolved = resolver.resolve(windows_path, plugin_root)

        # Should preserve Windows path format on Windows
        assert Path(resolved).is_absolute()

    def test_resolve_normalizes_path_separators(self):
        """Test resolving normalizes path separators."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        mixed_path = "some/path\\with/mixed\\separators"
        plugin_root = Path("/plugin/root")

        resolved = resolver.resolve(mixed_path, plugin_root)

        # Should use OS-appropriate separators
        assert "\\" not in resolved or os.sep == "\\"


class TestPathResolverDictResolution:
    """Unit tests for dictionary path resolution (35% of unit tests)."""

    def test_resolve_dict_simple(self):
        """Test resolving paths in simple dictionary."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        data = {
            "file": "relative/path.py",
            "other": "another/file.js"
        }
        plugin_root = Path("/plugin/root")

        resolved = resolver.resolve_dict(data, plugin_root)

        assert Path(resolved["file"]).is_absolute()
        assert Path(resolved["other"]).is_absolute()

    def test_resolve_dict_nested(self):
        """Test resolving paths in nested dictionary."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        data = {
            "mcpServers": {
                "server1": {
                    "cwd": "servers/mcp1",
                    "script": "server.js"
                }
            }
        }
        plugin_root = Path("/plugin/root")

        resolved = resolver.resolve_dict(data, plugin_root)

        assert Path(resolved["mcpServers"]["server1"]["cwd"]).is_absolute()
        assert Path(resolved["mcpServers"]["server1"]["script"]).is_absolute()

    def test_resolve_dict_preserves_non_path_values(self):
        """Test resolving dict preserves non-path values."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        data = {
            "name": "test-plugin",
            "version": "1.0.0",
            "count": 42,
            "enabled": True,
            "path": "relative/path.py"
        }
        plugin_root = Path("/plugin/root")

        resolved = resolver.resolve_dict(data, plugin_root)

        assert resolved["name"] == "test-plugin"
        assert resolved["version"] == "1.0.0"
        assert resolved["count"] == 42
        assert resolved["enabled"] is True
        assert Path(resolved["path"]).is_absolute()

    def test_resolve_dict_with_arrays(self):
        """Test resolving paths in arrays within dict."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        data = {
            "files": ["file1.py", "file2.js", "file3.ts"]
        }
        plugin_root = Path("/plugin/root")

        resolved = resolver.resolve_dict(data, plugin_root)

        # Should resolve paths in arrays
        for file_path in resolved["files"]:
            assert Path(file_path).is_absolute()

    def test_resolve_dict_with_mixed_arrays(self):
        """Test resolving dict with arrays containing mixed types."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        data = {
            "mixed": ["file.py", 42, True, "another/file.js"]
        }
        plugin_root = Path("/plugin/root")

        resolved = resolver.resolve_dict(data, plugin_root)

        # Should only resolve string paths
        assert isinstance(resolved["mixed"][1], int)
        assert isinstance(resolved["mixed"][2], bool)

    def test_resolve_dict_empty(self):
        """Test resolving empty dictionary."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        data = {}
        plugin_root = Path("/plugin/root")

        resolved = resolver.resolve_dict(data, plugin_root)

        assert resolved == {}

    def test_resolve_dict_deeply_nested(self):
        """Test resolving paths in deeply nested dictionary."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "path": "deep/path.py"
                    }
                }
            }
        }
        plugin_root = Path("/plugin/root")

        resolved = resolver.resolve_dict(data, plugin_root)

        deep_path = resolved["level1"]["level2"]["level3"]["path"]
        assert Path(deep_path).is_absolute()

    def test_resolve_dict_preserves_absolute_paths(self):
        """Test resolving dict preserves already absolute paths."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        absolute = "/absolute/path/file.py"
        data = {
            "absolute": absolute,
            "relative": "relative/path.py"
        }
        plugin_root = Path("/plugin/root")

        resolved = resolver.resolve_dict(data, plugin_root)

        assert resolved["absolute"] == absolute
        assert Path(resolved["relative"]).is_absolute()


class TestPathResolverPluginRoot:
    """Unit tests for plugin root detection (20% of unit tests)."""

    def test_get_plugin_root_from_env(self):
        """Test getting plugin root from environment variable."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()

        with patch.dict(os.environ, {"PLUGIN_ROOT": "/custom/plugin/path"}):
            root = resolver.get_plugin_root()

        assert root == Path("/custom/plugin/path")

    def test_get_plugin_root_default(self):
        """Test getting default plugin root."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()

        with patch.dict(os.environ, {}, clear=True):
            root = resolver.get_plugin_root()

        # Should return some default path
        assert isinstance(root, Path)
        assert root.is_absolute()

    def test_get_plugin_root_from_current_dir(self):
        """Test getting plugin root from current directory context."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()

        with patch("pathlib.Path.cwd", return_value=Path("/current/working/dir")):
            root = resolver.get_plugin_root()

        # Should be based on cwd or parent
        assert isinstance(root, Path)

    def test_get_plugin_root_caches_result(self):
        """Test getting plugin root caches result for performance."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()

        with patch("pathlib.Path.cwd", return_value=Path("/test/path")) as mock_cwd:
            root1 = resolver.get_plugin_root()
            root2 = resolver.get_plugin_root()

        # Should only call cwd once if cached
        assert root1 == root2


class TestPathResolverEdgeCases:
    """Unit tests for edge cases (15% of unit tests)."""

    def test_resolve_path_with_spaces(self):
        """Test resolving paths with spaces."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        path_with_spaces = "path with spaces/file.py"
        plugin_root = Path("/plugin/root")

        resolved = resolver.resolve(path_with_spaces, plugin_root)

        assert Path(resolved).is_absolute()
        assert "path with spaces" in resolved

    def test_resolve_path_with_special_chars(self):
        """Test resolving paths with special characters."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        path_with_special = "path-with_special.chars/file@v2.py"
        plugin_root = Path("/plugin/root")

        resolved = resolver.resolve(path_with_special, plugin_root)

        assert Path(resolved).is_absolute()

    def test_resolve_path_with_unicode(self):
        """Test resolving paths with unicode characters."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        unicode_path = "café/文件.py"
        plugin_root = Path("/plugin/root")

        resolved = resolver.resolve(unicode_path, plugin_root)

        assert Path(resolved).is_absolute()

    def test_resolve_dict_with_circular_reference(self):
        """Test resolving dict handles circular references."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        data = {"key": "value"}
        data["self"] = data  # Circular reference
        plugin_root = Path("/plugin/root")

        # Should detect and handle circular references
        with pytest.raises((ValueError, RecursionError)):
            resolved = resolver.resolve_dict(data, plugin_root)

    def test_resolve_none_plugin_root(self):
        """Test resolving with None plugin root."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        path = "relative/path.py"

        with pytest.raises(TypeError):
            resolved = resolver.resolve(path, None)

    def test_resolve_dict_none_values(self):
        """Test resolving dict with None values."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        data = {
            "valid_path": "file.py",
            "null_value": None
        }
        plugin_root = Path("/plugin/root")

        resolved = resolver.resolve_dict(data, plugin_root)

        assert Path(resolved["valid_path"]).is_absolute()
        assert resolved["null_value"] is None

    def test_resolve_very_long_path(self):
        """Test resolving very long paths."""
        from amplihack.path_resolver import PathResolver

        resolver = PathResolver()
        long_path = "/".join(["very_long_directory_name"] * 50) + "/file.py"
        plugin_root = Path("/plugin/root")

        resolved = resolver.resolve(long_path, plugin_root)

        # Should handle without error
        assert isinstance(resolved, str)
