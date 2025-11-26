"""Comprehensive unit tests for the plugin system - TDD approach.

This test file defines the expected behavior of the plugin system before implementation.
Following the testing pyramid: these unit tests represent 60% of total test coverage.

Test Coverage:
- PluginBase abstract class behavior
- PluginRegistry singleton pattern and thread safety
- @register_plugin decorator functionality
- Plugin discovery with security validation
- Plugin loading with validation and caching

All tests should FAIL initially as the implementation doesn't exist yet.
"""

import tempfile
import threading
from pathlib import Path
from typing import Any

import pytest

# ============================================================================
# TEST: PluginBase Abstract Class (10% of unit tests)
# ============================================================================


class TestPluginBase:
    """Test the PluginBase abstract class contract."""

    def test_cannot_instantiate_abstract_base(self):
        """PluginBase cannot be instantiated directly."""
        from src.amplihack.plugins.base import PluginBase

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            PluginBase()

    def test_must_implement_execute_method(self):
        """Subclasses must implement execute() method."""
        from src.amplihack.plugins.base import PluginBase

        # Create a class that doesn't implement execute()
        class IncompletePlugin(PluginBase):
            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompletePlugin()

    def test_valid_plugin_implements_execute(self):
        """Valid plugins must implement execute() method with correct signature."""
        from src.amplihack.plugins.base import PluginBase

        class ValidPlugin(PluginBase):
            def execute(self, args: dict[str, Any]) -> Any:
                return "success"

        plugin = ValidPlugin()
        result = plugin.execute({"test": "data"})
        assert result == "success"

    def test_plugin_name_property_defaults_to_class_name(self):
        """Plugin name defaults to class name if not overridden."""
        from src.amplihack.plugins.base import PluginBase

        class MyCustomPlugin(PluginBase):
            def execute(self, args: dict[str, Any]) -> Any:
                return "result"

        plugin = MyCustomPlugin()
        assert plugin.name == "MyCustomPlugin"

    def test_plugin_name_can_be_overridden(self):
        """Plugin name can be customized via property override."""
        from src.amplihack.plugins.base import PluginBase

        class MyPlugin(PluginBase):
            @property
            def name(self) -> str:
                return "custom_name"

            def execute(self, args: dict[str, Any]) -> Any:
                return "result"

        plugin = MyPlugin()
        assert plugin.name == "custom_name"


# ============================================================================
# TEST: PluginRegistry Singleton (20% of unit tests)
# ============================================================================


class TestPluginRegistry:
    """Test the PluginRegistry singleton pattern and thread safety."""

    def test_registry_is_singleton(self):
        """PluginRegistry implements singleton pattern."""
        from src.amplihack.plugins.registry import PluginRegistry

        registry1 = PluginRegistry()
        registry2 = PluginRegistry()
        assert registry1 is registry2

    def test_registry_thread_safe_singleton(self):
        """PluginRegistry singleton is thread-safe."""
        from src.amplihack.plugins.registry import PluginRegistry

        instances = []

        def create_instance():
            instances.append(PluginRegistry())

        threads = [threading.Thread(target=create_instance) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All instances should be the same object
        assert all(instance is instances[0] for instance in instances)

    def test_register_plugin_stores_class(self):
        """Registry stores plugin class with name as key."""
        from src.amplihack.plugins.base import PluginBase
        from src.amplihack.plugins.registry import PluginRegistry

        class TestPlugin(PluginBase):
            def execute(self, args: dict[str, Any]) -> Any:
                return "test"

        registry = PluginRegistry()
        registry.register("test_plugin", TestPlugin)

        assert "test_plugin" in registry._plugins
        assert registry._plugins["test_plugin"] is TestPlugin

    def test_register_duplicate_plugin_raises_error(self):
        """Registering a duplicate plugin name raises ValueError."""
        from src.amplihack.plugins.base import PluginBase
        from src.amplihack.plugins.registry import PluginRegistry

        class Plugin1(PluginBase):
            def execute(self, args: dict[str, Any]) -> Any:
                return "1"

        class Plugin2(PluginBase):
            def execute(self, args: dict[str, Any]) -> Any:
                return "2"

        registry = PluginRegistry()
        registry.register("duplicate", Plugin1)

        with pytest.raises(ValueError, match="already registered"):
            registry.register("duplicate", Plugin2)

    def test_get_plugin_returns_registered_class(self):
        """Registry returns correct plugin class by name."""
        from src.amplihack.plugins.base import PluginBase
        from src.amplihack.plugins.registry import PluginRegistry

        class MyPlugin(PluginBase):
            def execute(self, args: dict[str, Any]) -> Any:
                return "my_result"

        registry = PluginRegistry()
        registry.register("my_plugin", MyPlugin)

        retrieved = registry.get("my_plugin")
        assert retrieved is MyPlugin

    def test_get_nonexistent_plugin_returns_none(self):
        """Registry returns None for nonexistent plugins."""
        from src.amplihack.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        assert registry.get("nonexistent") is None

    def test_list_plugins_returns_all_names(self):
        """Registry can list all registered plugin names."""
        from src.amplihack.plugins.base import PluginBase
        from src.amplihack.plugins.registry import PluginRegistry

        class Plugin1(PluginBase):
            def execute(self, args: dict[str, Any]) -> Any:
                return "1"

        class Plugin2(PluginBase):
            def execute(self, args: dict[str, Any]) -> Any:
                return "2"

        registry = PluginRegistry()
        registry.register("plugin1", Plugin1)
        registry.register("plugin2", Plugin2)

        names = registry.list_plugins()
        assert set(names) == {"plugin1", "plugin2"}

    def test_clear_registry_removes_all_plugins(self):
        """Registry can be cleared for testing purposes."""
        from src.amplihack.plugins.base import PluginBase
        from src.amplihack.plugins.registry import PluginRegistry

        class TestPlugin(PluginBase):
            def execute(self, args: dict[str, Any]) -> Any:
                return "test"

        registry = PluginRegistry()
        registry.register("test", TestPlugin)
        assert len(registry.list_plugins()) > 0

        registry.clear()
        assert len(registry.list_plugins()) == 0


# ============================================================================
# TEST: @register_plugin Decorator (15% of unit tests)
# ============================================================================


class TestRegisterPluginDecorator:
    """Test the @register_plugin decorator functionality."""

    def test_decorator_registers_plugin_with_default_name(self):
        """Decorator registers plugin using class name by default."""
        from src.amplihack.plugins.base import PluginBase
        from src.amplihack.plugins.decorator import register_plugin
        from src.amplihack.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        registry.clear()

        @register_plugin()
        class AutoNamedPlugin(PluginBase):
            def execute(self, args: dict[str, Any]) -> Any:
                return "auto"

        assert "AutoNamedPlugin" in registry.list_plugins()

    def test_decorator_registers_plugin_with_custom_name(self):
        """Decorator can register plugin with custom name."""
        from src.amplihack.plugins.base import PluginBase
        from src.amplihack.plugins.decorator import register_plugin
        from src.amplihack.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        registry.clear()

        @register_plugin(name="custom_name")
        class MyPlugin(PluginBase):
            def execute(self, args: dict[str, Any]) -> Any:
                return "custom"

        assert "custom_name" in registry.list_plugins()
        assert registry.get("custom_name") is MyPlugin

    def test_decorator_preserves_class_functionality(self):
        """Decorator doesn't break class functionality."""
        from src.amplihack.plugins.base import PluginBase
        from src.amplihack.plugins.decorator import register_plugin

        @register_plugin()
        class FunctionalPlugin(PluginBase):
            def __init__(self):
                self.state = "initialized"

            def execute(self, args: dict[str, Any]) -> Any:
                return f"state: {self.state}, args: {args}"

        plugin = FunctionalPlugin()
        assert plugin.state == "initialized"
        result = plugin.execute({"test": "data"})
        assert "state: initialized" in result
        assert "test" in result

    def test_decorator_validates_plugin_base(self):
        """Decorator rejects classes that don't inherit from PluginBase."""
        from src.amplihack.plugins.decorator import register_plugin

        with pytest.raises(TypeError, match="must inherit from PluginBase"):

            @register_plugin()
            class InvalidPlugin:
                def execute(self, args: dict[str, Any]) -> Any:
                    return "invalid"

    def test_decorator_stores_metadata(self):
        """Decorator stores metadata about the plugin."""
        from src.amplihack.plugins.base import PluginBase
        from src.amplihack.plugins.decorator import register_plugin

        @register_plugin(name="meta_plugin", description="Test plugin with metadata")
        class MetaPlugin(PluginBase):
            def execute(self, args: dict[str, Any]) -> Any:
                return "meta"

        # Metadata should be accessible
        assert hasattr(MetaPlugin, "_plugin_metadata")
        assert MetaPlugin._plugin_metadata["name"] == "meta_plugin"
        assert "Test plugin" in MetaPlugin._plugin_metadata["description"]


# ============================================================================
# TEST: Plugin Discovery (25% of unit tests)
# ============================================================================


class TestPluginDiscovery:
    """Test plugin discovery with security validation."""

    def test_discover_plugins_finds_python_files(self):
        """Discovery finds all .py files in plugin directory."""
        from src.amplihack.plugins.discovery import discover_plugins

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "plugins"
            plugin_dir.mkdir()

            # Create test plugin files
            (plugin_dir / "plugin1.py").write_text("# Plugin 1")
            (plugin_dir / "plugin2.py").write_text("# Plugin 2")
            (plugin_dir / "__init__.py").write_text("# Init")

            files = discover_plugins(str(plugin_dir))
            plugin_files = [f for f in files if not f.endswith("__init__.py")]

            assert len(plugin_files) == 2
            assert any("plugin1.py" in f for f in plugin_files)
            assert any("plugin2.py" in f for f in plugin_files)

    def test_discover_plugins_validates_path_traversal(self):
        """Discovery prevents path traversal attacks."""
        from src.amplihack.plugins.discovery import discover_plugins

        with pytest.raises(ValueError, match="path traversal"):
            discover_plugins("../../../etc/passwd")

        with pytest.raises(ValueError, match="path traversal"):
            discover_plugins("/tmp/plugins/../../etc")

    def test_discover_plugins_validates_file_size(self):
        """Discovery rejects files exceeding size limit."""
        from src.amplihack.plugins.discovery import discover_plugins

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "plugins"
            plugin_dir.mkdir()

            # Create oversized file (> 1MB)
            large_file = plugin_dir / "large_plugin.py"
            large_file.write_text("# " + "x" * (1024 * 1024 + 1))

            with pytest.raises(ValueError, match="exceeds maximum size"):
                discover_plugins(str(plugin_dir))

    def test_discover_plugins_handles_missing_directory(self):
        """Discovery handles missing directory gracefully."""
        from src.amplihack.plugins.discovery import discover_plugins

        result = discover_plugins("/nonexistent/directory")
        assert result == []

    def test_discover_plugins_ignores_non_python_files(self):
        """Discovery ignores non-.py files."""
        from src.amplihack.plugins.discovery import discover_plugins

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "plugins"
            plugin_dir.mkdir()

            (plugin_dir / "plugin.py").write_text("# Valid")
            (plugin_dir / "readme.txt").write_text("Not a plugin")
            (plugin_dir / "data.json").write_text('{"key": "value"}')

            files = discover_plugins(str(plugin_dir))
            assert len(files) == 1
            assert files[0].endswith("plugin.py")

    def test_discover_plugins_recursive_search(self):
        """Discovery searches subdirectories recursively."""
        from src.amplihack.plugins.discovery import discover_plugins

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "plugins"
            plugin_dir.mkdir()

            # Create nested structure
            (plugin_dir / "plugin1.py").write_text("# Root plugin")
            subdir = plugin_dir / "subdir"
            subdir.mkdir()
            (subdir / "plugin2.py").write_text("# Nested plugin")

            files = discover_plugins(str(plugin_dir))
            assert len(files) == 2

    def test_discover_plugins_validates_file_permissions(self):
        """Discovery checks file is readable."""
        from src.amplihack.plugins.discovery import discover_plugins

        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "plugins"
            plugin_dir.mkdir()

            plugin_file = plugin_dir / "plugin.py"
            plugin_file.write_text("# Plugin")
            plugin_file.chmod(0o000)  # Remove all permissions

            try:
                files = discover_plugins(str(plugin_dir))
                # Should either skip unreadable files or raise error
                assert plugin_file.name not in [Path(f).name for f in files]
            finally:
                plugin_file.chmod(0o644)  # Restore for cleanup


# ============================================================================
# TEST: Plugin Loading (30% of unit tests)
# ============================================================================


class TestPluginLoading:
    """Test plugin loading with validation and caching."""

    def test_load_plugin_by_name_returns_instance(self):
        """Loading a plugin by name returns an instance."""
        from src.amplihack.plugins.base import PluginBase
        from src.amplihack.plugins.loader import load_plugin
        from src.amplihack.plugins.registry import PluginRegistry

        class LoadablePlugin(PluginBase):
            def execute(self, args: dict[str, Any]) -> Any:
                return "loaded"

        registry = PluginRegistry()
        registry.register("loadable", LoadablePlugin)

        instance = load_plugin("loadable")
        assert isinstance(instance, LoadablePlugin)
        assert instance.execute({}) == "loaded"

    def test_load_nonexistent_plugin_raises_error(self):
        """Loading nonexistent plugin raises PluginNotFoundError."""
        from src.amplihack.plugins.loader import PluginNotFoundError, load_plugin

        with pytest.raises(PluginNotFoundError, match="not found"):
            load_plugin("nonexistent_plugin")

    def test_load_plugin_validates_plugin_base(self):
        """Loader validates plugin implements PluginBase."""
        from src.amplihack.plugins.loader import load_plugin
        from src.amplihack.plugins.registry import PluginRegistry

        class NotAPlugin:
            pass

        registry = PluginRegistry()
        # Bypass normal registration to test validation
        registry._plugins["invalid"] = NotAPlugin

        with pytest.raises(TypeError, match="must inherit from PluginBase"):
            load_plugin("invalid")

    def test_load_plugin_with_init_args(self):
        """Loader can pass initialization arguments."""
        from src.amplihack.plugins.base import PluginBase
        from src.amplihack.plugins.loader import load_plugin
        from src.amplihack.plugins.registry import PluginRegistry

        class ConfigurablePlugin(PluginBase):
            def __init__(self, config: str):
                self.config = config

            def execute(self, args: dict[str, Any]) -> Any:
                return self.config

        registry = PluginRegistry()
        registry.register("configurable", ConfigurablePlugin)

        instance = load_plugin("configurable", init_args={"config": "test_config"})
        assert instance.execute({}) == "test_config"

    def test_load_plugin_caching_returns_same_instance(self):
        """Loader caches instances by default."""
        from src.amplihack.plugins.base import PluginBase
        from src.amplihack.plugins.loader import load_plugin
        from src.amplihack.plugins.registry import PluginRegistry

        class CacheablePlugin(PluginBase):
            def execute(self, args: dict[str, Any]) -> Any:
                return "cached"

        registry = PluginRegistry()
        registry.register("cacheable", CacheablePlugin)

        instance1 = load_plugin("cacheable")
        instance2 = load_plugin("cacheable")

        assert instance1 is instance2

    def test_load_plugin_no_cache_returns_new_instance(self):
        """Loader can skip cache to return new instances."""
        from src.amplihack.plugins.base import PluginBase
        from src.amplihack.plugins.loader import load_plugin
        from src.amplihack.plugins.registry import PluginRegistry

        class FreshPlugin(PluginBase):
            def execute(self, args: dict[str, Any]) -> Any:
                return "fresh"

        registry = PluginRegistry()
        registry.register("fresh", FreshPlugin)

        instance1 = load_plugin("fresh", use_cache=False)
        instance2 = load_plugin("fresh", use_cache=False)

        assert instance1 is not instance2

    def test_load_plugin_handles_init_errors(self):
        """Loader handles plugin initialization errors gracefully."""
        from src.amplihack.plugins.base import PluginBase
        from src.amplihack.plugins.loader import PluginLoadError, load_plugin
        from src.amplihack.plugins.registry import PluginRegistry

        class BrokenPlugin(PluginBase):
            def __init__(self):
                raise RuntimeError("Init failed")

            def execute(self, args: dict[str, Any]) -> Any:
                return "never"

        registry = PluginRegistry()
        registry.register("broken", BrokenPlugin)

        with pytest.raises(PluginLoadError, match="Failed to initialize"):
            load_plugin("broken")

    def test_load_plugin_validates_execute_method(self):
        """Loader validates execute method exists and is callable."""
        from src.amplihack.plugins.base import PluginBase
        from src.amplihack.plugins.loader import load_plugin
        from src.amplihack.plugins.registry import PluginRegistry

        class NoExecutePlugin(PluginBase):
            # This should be caught at class definition, but test loader validation
            pass

        registry = PluginRegistry()

        # This should fail during registration or loading
        with pytest.raises((TypeError, AttributeError)):
            registry.register("no_execute", NoExecutePlugin)
            load_plugin("no_execute")

    def test_load_all_plugins_returns_dict(self):
        """Loader can load all registered plugins at once."""
        from src.amplihack.plugins.base import PluginBase
        from src.amplihack.plugins.loader import load_all_plugins
        from src.amplihack.plugins.registry import PluginRegistry

        class Plugin1(PluginBase):
            def execute(self, args: dict[str, Any]) -> Any:
                return "1"

        class Plugin2(PluginBase):
            def execute(self, args: dict[str, Any]) -> Any:
                return "2"

        registry = PluginRegistry()
        registry.clear()
        registry.register("plugin1", Plugin1)
        registry.register("plugin2", Plugin2)

        all_plugins = load_all_plugins()

        assert isinstance(all_plugins, dict)
        assert "plugin1" in all_plugins
        assert "plugin2" in all_plugins
        assert isinstance(all_plugins["plugin1"], Plugin1)
        assert isinstance(all_plugins["plugin2"], Plugin2)


# ============================================================================
# TEST FIXTURES
# ============================================================================


@pytest.fixture
def clean_registry():
    """Fixture to ensure clean registry state for each test."""
    from src.amplihack.plugins.registry import PluginRegistry

    registry = PluginRegistry()
    registry.clear()
    yield registry
    registry.clear()


@pytest.fixture
def sample_plugin_class():
    """Fixture providing a sample plugin class for testing."""
    from src.amplihack.plugins.base import PluginBase

    class SamplePlugin(PluginBase):
        def execute(self, args: dict[str, Any]) -> Any:
            return f"Sample executed with {args}"

    return SamplePlugin


@pytest.fixture
def temp_plugin_dir():
    """Fixture providing a temporary plugin directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = Path(tmpdir) / "test_plugins"
        plugin_dir.mkdir()
        yield plugin_dir
