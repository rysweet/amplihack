"""Integration tests for the plugin system - TDD approach.

This test file validates the complete plugin system workflow integration.
Following the testing pyramid: these integration tests represent 30% of total test coverage.

Test Coverage:
- Complete plugin lifecycle: discovery → registration → loading → execution
- Multiple plugins working together
- Error handling and resilience
- Thread safety under concurrent access
- Example plugin (HelloPlugin) end-to-end

All tests should FAIL initially as the implementation doesn't exist yet.
"""

import tempfile
import threading
from pathlib import Path
from typing import Any

import pytest

# ============================================================================
# TEST: Complete Plugin Workflow (40% of integration tests)
# ============================================================================


class TestPluginWorkflow:
    """Test complete plugin lifecycle from discovery to execution."""

    def test_complete_plugin_lifecycle(self, temp_plugin_dir):
        """Test full workflow: create → discover → register → load → execute."""
        from src.amplihack.plugins.discovery import discover_plugins
        from src.amplihack.plugins.loader import load_plugin
        from src.amplihack.plugins.registry import PluginRegistry

        # Step 1: Create a plugin file
        plugin_code = """
from src.amplihack.plugins.base import PluginBase
from src.amplihack.plugins.decorator import register_plugin
from typing import Dict, Any

@register_plugin(name="lifecycle_test")
class LifecyclePlugin(PluginBase):
    def execute(self, args: Dict[str, Any]) -> Any:
        return f"Lifecycle: {args.get('message', 'no message')}"
"""
        plugin_file = temp_plugin_dir / "lifecycle_plugin.py"
        plugin_file.write_text(plugin_code)

        # Step 2: Discover plugins
        discovered = discover_plugins(str(temp_plugin_dir))
        assert len(discovered) == 1
        assert str(plugin_file) in discovered

        # Step 3: Import the module (triggers @register_plugin decorator)
        import importlib.util

        spec = importlib.util.spec_from_file_location("lifecycle_plugin", plugin_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Step 4: Verify registration
        registry = PluginRegistry()
        assert "lifecycle_test" in registry.list_plugins()

        # Step 5: Load plugin
        plugin = load_plugin("lifecycle_test")
        assert plugin is not None

        # Step 6: Execute plugin
        result = plugin.execute({"message": "success"})
        assert "Lifecycle: success" in result

    def test_builtin_hello_plugin_workflow(self):
        """Test HelloPlugin from builtin/ directory works end-to-end."""
        from src.amplihack.plugins.registry import PluginRegistry

        # Plugin should auto-register via decorator
        registry = PluginRegistry()
        assert "hello" in registry.list_plugins()

        # Load and execute
        from src.amplihack.plugins.loader import load_plugin

        plugin = load_plugin("hello")
        result = plugin.execute({"name": "World"})

        assert "Hello" in result
        assert "World" in result

    def test_plugin_with_initialization_state(self, temp_plugin_dir):
        """Test plugin maintains state through initialization."""
        plugin_code = """
from src.amplihack.plugins.base import PluginBase
from src.amplihack.plugins.decorator import register_plugin
from typing import Dict, Any

@register_plugin(name="stateful")
class StatefulPlugin(PluginBase):
    def __init__(self):
        self.counter = 0

    def execute(self, args: Dict[str, Any]) -> Any:
        self.counter += 1
        return f"Execution count: {self.counter}"
"""
        plugin_file = temp_plugin_dir / "stateful.py"
        plugin_file.write_text(plugin_code)

        # Import and load
        import importlib.util

        spec = importlib.util.spec_from_file_location("stateful", plugin_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        from src.amplihack.plugins.loader import load_plugin

        plugin = load_plugin("stateful")

        # Execute multiple times
        result1 = plugin.execute({})
        result2 = plugin.execute({})

        assert "count: 1" in result1
        assert "count: 2" in result2

    def test_plugin_error_handling_in_execute(self, temp_plugin_dir):
        """Test plugin execution errors are properly propagated."""
        plugin_code = """
from src.amplihack.plugins.base import PluginBase
from src.amplihack.plugins.decorator import register_plugin
from typing import Dict, Any

@register_plugin(name="error_plugin")
class ErrorPlugin(PluginBase):
    def execute(self, args: Dict[str, Any]) -> Any:
        if args.get("should_fail"):
            raise RuntimeError("Plugin execution failed")
        return "success"
"""
        plugin_file = temp_plugin_dir / "error_plugin.py"
        plugin_file.write_text(plugin_code)

        # Import and load
        import importlib.util

        spec = importlib.util.spec_from_file_location("error_plugin", plugin_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        from src.amplihack.plugins.loader import load_plugin

        plugin = load_plugin("error_plugin")

        # Successful execution
        result = plugin.execute({"should_fail": False})
        assert result == "success"

        # Failed execution
        with pytest.raises(RuntimeError, match="Plugin execution failed"):
            plugin.execute({"should_fail": True})

    def test_discover_and_load_all_plugins(self, temp_plugin_dir):
        """Test discovering and loading all plugins in a directory."""
        # Create multiple plugins
        for i in range(3):
            plugin_code = f"""
from src.amplihack.plugins.base import PluginBase
from src.amplihack.plugins.decorator import register_plugin
from typing import Dict, Any

@register_plugin(name="plugin_{i}")
class Plugin{i}(PluginBase):
    def execute(self, args: Dict[str, Any]) -> Any:
        return "plugin_{i}_result"
"""
            (temp_plugin_dir / f"plugin_{i}.py").write_text(plugin_code)

        # Discover all
        from src.amplihack.plugins.discovery import discover_plugins

        discovered = discover_plugins(str(temp_plugin_dir))
        assert len(discovered) == 3

        # Import all
        import importlib.util

        for plugin_file in discovered:
            spec = importlib.util.spec_from_file_location(Path(plugin_file).stem, plugin_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        # Load all
        from src.amplihack.plugins.loader import load_all_plugins

        all_plugins = load_all_plugins()
        assert len(all_plugins) >= 3
        assert all(f"plugin_{i}" in all_plugins for i in range(3))


# ============================================================================
# TEST: Multiple Plugins Interaction (20% of integration tests)
# ============================================================================


class TestMultiplePlugins:
    """Test multiple plugins coexist and work independently."""

    def test_multiple_plugins_independent_execution(self, temp_plugin_dir):
        """Multiple plugins execute independently without interference."""
        # Create two different plugins
        plugin1_code = """
from src.amplihack.plugins.base import PluginBase
from src.amplihack.plugins.decorator import register_plugin
from typing import Dict, Any

@register_plugin(name="adder")
class AdderPlugin(PluginBase):
    def execute(self, args: Dict[str, Any]) -> Any:
        a = args.get("a", 0)
        b = args.get("b", 0)
        return a + b
"""
        plugin2_code = """
from src.amplihack.plugins.base import PluginBase
from src.amplihack.plugins.decorator import register_plugin
from typing import Dict, Any

@register_plugin(name="multiplier")
class MultiplierPlugin(PluginBase):
    def execute(self, args: Dict[str, Any]) -> Any:
        a = args.get("a", 1)
        b = args.get("b", 1)
        return a * b
"""
        (temp_plugin_dir / "adder.py").write_text(plugin1_code)
        (temp_plugin_dir / "multiplier.py").write_text(plugin2_code)

        # Import both
        import importlib.util

        for name, code in [("adder", plugin1_code), ("multiplier", plugin2_code)]:
            spec = importlib.util.spec_from_file_location(name, temp_plugin_dir / f"{name}.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        # Load and execute both
        from src.amplihack.plugins.loader import load_plugin

        adder = load_plugin("adder")
        multiplier = load_plugin("multiplier")

        result1 = adder.execute({"a": 5, "b": 3})
        result2 = multiplier.execute({"a": 5, "b": 3})

        assert result1 == 8
        assert result2 == 15

    def test_plugins_with_different_state_dont_interfere(self, temp_plugin_dir):
        """Plugins with state don't interfere with each other."""
        counter_code = """
from src.amplihack.plugins.base import PluginBase
from src.amplihack.plugins.decorator import register_plugin
from typing import Dict, Any

@register_plugin(name="counter{n}")
class Counter{n}Plugin(PluginBase):
    def __init__(self):
        self.count = 0

    def execute(self, args: Dict[str, Any]) -> Any:
        self.count += args.get("increment", 1)
        return self.count
"""
        # Create two counter plugins
        for i in range(2):
            code = counter_code.replace("{n}", str(i))
            (temp_plugin_dir / f"counter{i}.py").write_text(code)

        # Import both
        import importlib.util

        for i in range(2):
            spec = importlib.util.spec_from_file_location(
                f"counter{i}", temp_plugin_dir / f"counter{i}.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        # Load both
        from src.amplihack.plugins.loader import load_plugin

        counter0 = load_plugin("counter0")
        counter1 = load_plugin("counter1")

        # Execute with different increments
        r1 = counter0.execute({"increment": 5})
        r2 = counter1.execute({"increment": 10})
        r3 = counter0.execute({"increment": 3})

        assert r1 == 5
        assert r2 == 10
        assert r3 == 8  # counter0 maintains its own state

    def test_plugin_namespace_isolation(self, temp_plugin_dir):
        """Plugins can use same variable names without conflicts."""
        plugin_template = """
from src.amplihack.plugins.base import PluginBase
from src.amplihack.plugins.decorator import register_plugin
from typing import Dict, Any

# Both plugins use "CONSTANT" variable
CONSTANT = "{value}"

@register_plugin(name="isolated_{name}")
class Isolated{name}Plugin(PluginBase):
    def execute(self, args: Dict[str, Any]) -> Any:
        return CONSTANT
"""
        (temp_plugin_dir / "isolated_a.py").write_text(plugin_template.format(value="A", name="A"))
        (temp_plugin_dir / "isolated_b.py").write_text(plugin_template.format(value="B", name="B"))

        # Import both
        import importlib.util

        for name in ["a", "b"]:
            spec = importlib.util.spec_from_file_location(
                f"isolated_{name}", temp_plugin_dir / f"isolated_{name}.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        # Load and execute
        from src.amplihack.plugins.loader import load_plugin

        plugin_a = load_plugin("isolated_A")
        plugin_b = load_plugin("isolated_B")

        assert plugin_a.execute({}) == "A"
        assert plugin_b.execute({}) == "B"


# ============================================================================
# TEST: Error Handling and Resilience (20% of integration tests)
# ============================================================================


class TestPluginErrors:
    """Test error handling and resilient batch processing."""

    def test_one_plugin_failure_doesnt_affect_others(self, temp_plugin_dir):
        """One plugin's failure doesn't prevent other plugins from working."""
        good_plugin = """
from src.amplihack.plugins.base import PluginBase
from src.amplihack.plugins.decorator import register_plugin
from typing import Dict, Any

@register_plugin(name="good_plugin")
class GoodPlugin(PluginBase):
    def execute(self, args: Dict[str, Any]) -> Any:
        return "success"
"""
        bad_plugin = """
from src.amplihack.plugins.base import PluginBase
from src.amplihack.plugins.decorator import register_plugin
from typing import Dict, Any

@register_plugin(name="bad_plugin")
class BadPlugin(PluginBase):
    def execute(self, args: Dict[str, Any]) -> Any:
        raise RuntimeError("I always fail")
"""
        (temp_plugin_dir / "good.py").write_text(good_plugin)
        (temp_plugin_dir / "bad.py").write_text(bad_plugin)

        # Import both
        import importlib.util

        for name in ["good", "bad"]:
            spec = importlib.util.spec_from_file_location(name, temp_plugin_dir / f"{name}.py")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        # Load both
        from src.amplihack.plugins.loader import load_plugin

        good = load_plugin("good_plugin")
        bad = load_plugin("bad_plugin")

        # Good plugin works
        assert good.execute({}) == "success"

        # Bad plugin fails
        with pytest.raises(RuntimeError):
            bad.execute({})

        # Good plugin still works after bad plugin failed
        assert good.execute({}) == "success"

    def test_batch_processing_continues_on_failure(self, temp_plugin_dir):
        """Batch processing continues even if some plugins fail."""
        # Create mix of good and bad plugins
        for i in range(5):
            if i % 2 == 0:
                code = f"""
from src.amplihack.plugins.base import PluginBase
from src.amplihack.plugins.decorator import register_plugin
from typing import Dict, Any

@register_plugin(name="batch_plugin_{i}")
class BatchPlugin{i}(PluginBase):
    def execute(self, args: Dict[str, Any]) -> Any:
        return "success_{i}"
"""
            else:
                code = f"""
from src.amplihack.plugins.base import PluginBase
from src.amplihack.plugins.decorator import register_plugin
from typing import Dict, Any

@register_plugin(name="batch_plugin_{i}")
class BatchPlugin{i}(PluginBase):
    def execute(self, args: Dict[str, Any]) -> Any:
        raise RuntimeError("Plugin {i} fails")
"""
            (temp_plugin_dir / f"batch_{i}.py").write_text(code)

        # Import all
        import importlib.util

        for i in range(5):
            spec = importlib.util.spec_from_file_location(
                f"batch_{i}", temp_plugin_dir / f"batch_{i}.py"
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        # Batch process all plugins
        from src.amplihack.plugins.loader import load_plugin

        results = {"succeeded": [], "failed": []}

        for i in range(5):
            try:
                plugin = load_plugin(f"batch_plugin_{i}")
                result = plugin.execute({})
                results["succeeded"].append((i, result))
            except Exception as e:
                results["failed"].append((i, str(e)))

        # Verify some succeeded and some failed
        assert len(results["succeeded"]) == 3  # plugins 0, 2, 4
        assert len(results["failed"]) == 2  # plugins 1, 3

    def test_invalid_plugin_file_handling(self, temp_plugin_dir):
        """System handles invalid plugin files gracefully."""
        # Create invalid Python file
        invalid_code = """
this is not valid python syntax {][
"""
        (temp_plugin_dir / "invalid.py").write_text(invalid_code)

        # Discovery should find it
        from src.amplihack.plugins.discovery import discover_plugins

        discovered = discover_plugins(str(temp_plugin_dir))
        assert len(discovered) == 1

        # But import should fail gracefully
        import importlib.util

        spec = importlib.util.spec_from_file_location("invalid", temp_plugin_dir / "invalid.py")
        module = importlib.util.module_from_spec(spec)

        with pytest.raises(SyntaxError):
            spec.loader.exec_module(module)


# ============================================================================
# TEST: Thread Safety (20% of integration tests)
# ============================================================================


class TestThreadSafety:
    """Test concurrent access to plugin registry and loader."""

    def test_concurrent_registration_thread_safe(self, temp_plugin_dir):
        """Multiple threads can safely register plugins concurrently."""
        from src.amplihack.plugins.base import PluginBase
        from src.amplihack.plugins.registry import PluginRegistry

        registry = PluginRegistry()
        registry.clear()

        errors = []

        def register_plugin_thread(n):
            try:

                class DynamicPlugin(PluginBase):
                    def execute(self, args: dict[str, Any]) -> Any:
                        return f"plugin_{n}"

                registry.register(f"plugin_{n}", DynamicPlugin)
            except Exception as e:
                errors.append(e)

        # Create 20 threads registering different plugins
        threads = [threading.Thread(target=register_plugin_thread, args=(i,)) for i in range(20)]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify all registered successfully
        assert len(errors) == 0
        assert len(registry.list_plugins()) == 20

    def test_concurrent_loading_thread_safe(self, temp_plugin_dir):
        """Multiple threads can safely load plugins concurrently."""
        plugin_code = """
from src.amplihack.plugins.base import PluginBase
from src.amplihack.plugins.decorator import register_plugin
from typing import Dict, Any
import time

@register_plugin(name="concurrent_load")
class ConcurrentPlugin(PluginBase):
    def execute(self, args: Dict[str, Any]) -> Any:
        time.sleep(0.01)  # Simulate work
        return "loaded"
"""
        (temp_plugin_dir / "concurrent.py").write_text(plugin_code)

        # Import plugin
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "concurrent", temp_plugin_dir / "concurrent.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Load from multiple threads
        from src.amplihack.plugins.loader import load_plugin

        instances = []
        errors = []

        def load_thread():
            try:
                plugin = load_plugin("concurrent_load")
                instances.append(plugin)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=load_thread) for _ in range(10)]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify no errors and caching works
        assert len(errors) == 0
        assert len(instances) == 10
        # All instances should be the same (cached)
        assert all(inst is instances[0] for inst in instances)

    def test_concurrent_execution_thread_safe(self, temp_plugin_dir):
        """Multiple threads can execute same plugin concurrently."""
        plugin_code = """
from src.amplihack.plugins.base import PluginBase
from src.amplihack.plugins.decorator import register_plugin
from typing import Dict, Any
import threading

@register_plugin(name="concurrent_exec")
class ConcurrentExecPlugin(PluginBase):
    def __init__(self):
        self.lock = threading.Lock()
        self.counter = 0

    def execute(self, args: Dict[str, Any]) -> Any:
        with self.lock:
            self.counter += 1
            return self.counter
"""
        (temp_plugin_dir / "concurrent_exec.py").write_text(plugin_code)

        # Import plugin
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "concurrent_exec", temp_plugin_dir / "concurrent_exec.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Execute from multiple threads
        from src.amplihack.plugins.loader import load_plugin

        plugin = load_plugin("concurrent_exec")

        results = []
        errors = []

        def execute_thread():
            try:
                result = plugin.execute({})
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=execute_thread) for _ in range(20)]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # Verify no errors
        assert len(errors) == 0
        assert len(results) == 20
        # Counter should reach 20 (thread-safe increment)
        assert max(results) == 20


# ============================================================================
# TEST FIXTURES
# ============================================================================


@pytest.fixture
def temp_plugin_dir():
    """Fixture providing a temporary directory for test plugins."""
    with tempfile.TemporaryDirectory() as tmpdir:
        plugin_dir = Path(tmpdir) / "test_plugins"
        plugin_dir.mkdir()
        yield plugin_dir


@pytest.fixture
def clean_registry():
    """Fixture ensuring clean registry state."""
    from src.amplihack.plugins.registry import PluginRegistry

    registry = PluginRegistry()
    registry.clear()
    yield registry
    registry.clear()


@pytest.fixture(autouse=True)
def reset_loader_cache():
    """Fixture to reset plugin loader cache between tests."""
    from src.amplihack.plugins import loader

    if hasattr(loader, "_plugin_cache"):
        loader._plugin_cache.clear()
    yield
    if hasattr(loader, "_plugin_cache"):
        loader._plugin_cache.clear()
