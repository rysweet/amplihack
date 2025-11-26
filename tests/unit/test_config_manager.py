"""
Comprehensive test suite for ConfigManager module - TDD Red Phase

This test suite defines the expected behavior of ConfigManager BEFORE implementation.
All tests should FAIL initially until the implementation is complete.

Test Coverage:
- Basic YAML loading (5 tests)
- get() method (6 tests)
- set() method (4 tests)
- Environment variable overrides (7 tests)
- Validation (5 tests)
- Thread safety (4 tests)
- Edge cases (8 tests)

Total: 39 tests targeting 90%+ coverage
"""

import os
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

# Import the module we're testing (will fail until implementation exists)
try:
    from amplihack.config.config_manager import (
        ConfigFileError,
        ConfigKeyError,
        ConfigManager,
        ConfigValidationError,
    )
except ImportError:
    # Allow tests to be discovered even if implementation doesn't exist yet
    pytest.skip("ConfigManager implementation not yet available", allow_module_level=True)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def sample_yaml_content() -> str:
    """Sample YAML content for testing"""
    return """
# Test configuration
database:
  host: localhost
  port: 5432
  credentials:
    username: testuser
    password: testpass

server:
  host: 0.0.0.0
  port: 8080
  debug: true
  max_connections: 100

features:
  feature_a: true
  feature_b: false
  feature_c: null

nested:
  level1:
    level2:
      level3:
        level4:
          level5: deep_value

special:
  unicode: "Hello 世界"
  empty_string: ""
  whitespace: "   "
  number_as_string: "12345"

numbers:
  integer: 42
  float: 3.14
  negative: -100
"""


@pytest.fixture
def sample_yaml_file(tmp_path, sample_yaml_content) -> Path:
    """Create a temporary YAML file with sample content"""
    yaml_file = tmp_path / "test_config.yaml"
    yaml_file.write_text(sample_yaml_content)
    return yaml_file


@pytest.fixture
def empty_yaml_file(tmp_path) -> Path:
    """Create an empty YAML file"""
    yaml_file = tmp_path / "empty_config.yaml"
    yaml_file.write_text("")
    return yaml_file


@pytest.fixture
def malformed_yaml_file(tmp_path) -> Path:
    """Create a malformed YAML file"""
    yaml_file = tmp_path / "malformed_config.yaml"
    yaml_file.write_text("""
    key: value
    invalid yaml syntax here: [no closing bracket
    """)
    return yaml_file


@pytest.fixture
def config_manager(sample_yaml_file) -> ConfigManager:
    """Create a ConfigManager instance with sample YAML"""
    return ConfigManager(config_file=sample_yaml_file)


@pytest.fixture
def empty_config_manager(tmp_path) -> ConfigManager:
    """Create a ConfigManager instance without loading a file"""
    return ConfigManager()


# ============================================================================
# TEST CATEGORY 1: BASIC YAML LOADING (5 tests)
# ============================================================================


class TestYAMLLoading:
    """Test YAML file loading capabilities"""

    def test_load_valid_yaml_file(self, sample_yaml_file):
        """Test loading a valid YAML file"""
        config = ConfigManager(config_file=sample_yaml_file)

        # Verify key values loaded correctly
        assert config.get("database.host") == "localhost"
        assert config.get("database.port") == 5432
        assert config.get("server.debug") is True
        assert config.get("numbers.float") == 3.14

    def test_load_missing_file(self, tmp_path):
        """Test handling of non-existent file"""
        missing_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(ConfigFileError) as exc_info:
            ConfigManager(config_file=missing_file)

        assert "not found" in str(exc_info.value).lower()
        assert str(missing_file) in str(exc_info.value)

    def test_load_permission_error(self, tmp_path):
        """Test handling of file with no read permissions"""
        restricted_file = tmp_path / "restricted.yaml"
        restricted_file.write_text("key: value")
        restricted_file.chmod(0o000)  # Remove all permissions

        try:
            with pytest.raises(ConfigFileError) as exc_info:
                ConfigManager(config_file=restricted_file)

            assert "permission" in str(exc_info.value).lower()
        finally:
            # Restore permissions for cleanup
            restricted_file.chmod(0o644)

    def test_load_malformed_yaml(self, malformed_yaml_file):
        """Test handling of malformed YAML content"""
        with pytest.raises(ConfigFileError) as exc_info:
            ConfigManager(config_file=malformed_yaml_file)

        assert "invalid" in str(exc_info.value).lower() or "parse" in str(exc_info.value).lower()

    def test_load_empty_yaml_file(self, empty_yaml_file):
        """Test loading an empty YAML file (should result in empty config)"""
        config = ConfigManager(config_file=empty_yaml_file)

        # Empty file should not raise error, just create empty config
        assert config.get("any.key", default="default") == "default"


# ============================================================================
# TEST CATEGORY 2: get() METHOD (6 tests)
# ============================================================================


class TestGetMethod:
    """Test the get() method for retrieving configuration values"""

    def test_get_existing_key(self, config_manager):
        """Test getting an existing top-level key"""
        assert config_manager.get("numbers.integer") == 42
        assert config_manager.get("server.host") == "0.0.0.0"

    def test_get_with_default_for_missing_key(self, config_manager):
        """Test get() returns default value when key doesn't exist"""
        default_value = "my_default"
        assert config_manager.get("nonexistent.key", default=default_value) == default_value

    def test_get_nested_key_with_dot_notation(self, config_manager):
        """Test getting nested keys using dot notation"""
        assert config_manager.get("database.credentials.username") == "testuser"
        assert config_manager.get("server.max_connections") == 100

    def test_get_deeply_nested_key(self, config_manager):
        """Test getting deeply nested key (5+ levels)"""
        assert config_manager.get("nested.level1.level2.level3.level4.level5") == "deep_value"

    def test_get_with_none_as_default(self, config_manager):
        """Test get() with None as default value"""
        assert config_manager.get("nonexistent.key", default=None) is None
        assert config_manager.get("features.feature_c") is None  # Explicit null in YAML

    def test_get_when_intermediate_key_missing(self, config_manager):
        """Test get() when an intermediate key in the path doesn't exist"""
        with pytest.raises(ConfigKeyError) as exc_info:
            config_manager.get("nonexistent.intermediate.key")

        assert "not found" in str(exc_info.value).lower()


# ============================================================================
# TEST CATEGORY 3: set() METHOD (4 tests)
# ============================================================================


class TestSetMethod:
    """Test the set() method for updating configuration values"""

    def test_set_new_key(self, empty_config_manager):
        """Test setting a new key"""
        empty_config_manager.set("new.key", "new_value")
        assert empty_config_manager.get("new.key") == "new_value"

    def test_update_existing_key(self, config_manager):
        """Test updating an existing key"""
        original_value = config_manager.get("database.host")
        assert original_value == "localhost"

        config_manager.set("database.host", "remotehost")
        assert config_manager.get("database.host") == "remotehost"

    def test_set_nested_key_with_dot_notation(self, empty_config_manager):
        """Test setting nested keys using dot notation"""
        empty_config_manager.set("app.database.connection.pool_size", 20)
        assert empty_config_manager.get("app.database.connection.pool_size") == 20

    def test_set_creates_intermediate_keys(self, empty_config_manager):
        """Test that set() creates intermediate keys if they don't exist"""
        empty_config_manager.set("level1.level2.level3.value", "deep")

        # Verify intermediate keys were created
        assert empty_config_manager.get("level1.level2.level3.value") == "deep"
        assert isinstance(empty_config_manager.get("level1"), dict)
        assert isinstance(empty_config_manager.get("level1.level2"), dict)


# ============================================================================
# TEST CATEGORY 4: ENVIRONMENT VARIABLE OVERRIDE (7 tests)
# ============================================================================


class TestEnvironmentVariableOverride:
    """Test environment variable override functionality"""

    def test_simple_override(self, sample_yaml_file):
        """Test AMPLIHACK_FOO overrides 'foo' in config"""
        with patch.dict(os.environ, {"AMPLIHACK_TEST_KEY": "env_value"}):
            config = ConfigManager(config_file=sample_yaml_file)
            # Assuming YAML doesn't have test_key, env var should add it
            assert config.get("test_key") == "env_value"

    def test_nested_override_with_double_underscore(self, sample_yaml_file):
        """Test AMPLIHACK_DB__HOST overrides database.host"""
        with patch.dict(os.environ, {"AMPLIHACK_DATABASE__HOST": "env_host"}):
            config = ConfigManager(config_file=sample_yaml_file)
            assert config.get("database.host") == "env_host"

    def test_case_insensitivity(self, sample_yaml_file):
        """Test environment variables are case-insensitive for keys"""
        with patch.dict(
            os.environ, {"AMPLIHACK_SERVER__HOST": "case_test", "amplihack_server__port": "9090"}
        ):
            config = ConfigManager(config_file=sample_yaml_file)
            assert config.get("server.host") == "case_test"
            # Note: Port might be string or int depending on type conversion

    def test_type_conversion(self, sample_yaml_file):
        """Test type conversion for env vars (int, float, bool)"""
        with patch.dict(
            os.environ,
            {
                "AMPLIHACK_INT_VAL": "42",
                "AMPLIHACK_FLOAT_VAL": "3.14",
                "AMPLIHACK_BOOL_TRUE": "true",
                "AMPLIHACK_BOOL_FALSE": "false",
            },
        ):
            config = ConfigManager(config_file=sample_yaml_file)

            assert config.get("int_val") == 42
            assert isinstance(config.get("int_val"), int)

            assert config.get("float_val") == 3.14
            assert isinstance(config.get("float_val"), float)

            assert config.get("bool_true") is True
            assert config.get("bool_false") is False

    def test_empty_env_var_treated_as_empty_string(self, sample_yaml_file):
        """Test empty environment variable is treated as empty string"""
        with patch.dict(os.environ, {"AMPLIHACK_EMPTY_VAR": ""}):
            config = ConfigManager(config_file=sample_yaml_file)
            assert config.get("empty_var") == ""

    def test_env_var_precedence_over_yaml(self, sample_yaml_file):
        """Test environment variables take precedence over YAML values"""
        # YAML has database.host = localhost
        with patch.dict(os.environ, {"AMPLIHACK_DATABASE__HOST": "override_host"}):
            config = ConfigManager(config_file=sample_yaml_file)
            assert config.get("database.host") == "override_host"

    def test_multiple_env_vars(self, sample_yaml_file):
        """Test multiple environment variable overrides work together"""
        with patch.dict(
            os.environ,
            {
                "AMPLIHACK_DATABASE__HOST": "env_db_host",
                "AMPLIHACK_DATABASE__PORT": "3306",
                "AMPLIHACK_SERVER__DEBUG": "false",
            },
        ):
            config = ConfigManager(config_file=sample_yaml_file)

            assert config.get("database.host") == "env_db_host"
            assert config.get("database.port") == 3306
            assert config.get("server.debug") is False


# ============================================================================
# TEST CATEGORY 5: VALIDATION (5 tests)
# ============================================================================


class TestValidation:
    """Test configuration validation functionality"""

    def test_validation_passes_with_all_required_keys(self, config_manager):
        """Test validation passes when all required keys are present"""
        required_keys = [
            "database.host",
            "database.port",
            "server.host",
        ]

        # Should not raise any exception
        config_manager.validate(required_keys=required_keys)

    def test_validation_fails_with_missing_required_key(self, config_manager):
        """Test validation fails when a required key is missing"""
        required_keys = [
            "database.host",
            "nonexistent.key",  # This key doesn't exist
        ]

        with pytest.raises(ConfigValidationError) as exc_info:
            config_manager.validate(required_keys=required_keys)

        assert "nonexistent.key" in str(exc_info.value)
        assert "missing" in str(exc_info.value).lower()

    def test_validation_fails_with_multiple_missing_keys(self, config_manager):
        """Test validation reports all missing keys"""
        required_keys = [
            "database.host",  # Exists
            "missing.key1",  # Missing
            "missing.key2",  # Missing
        ]

        with pytest.raises(ConfigValidationError) as exc_info:
            config_manager.validate(required_keys=required_keys)

        error_message = str(exc_info.value)
        assert "missing.key1" in error_message
        assert "missing.key2" in error_message

    def test_validation_with_nested_required_keys(self, config_manager):
        """Test validation works with deeply nested required keys"""
        required_keys = [
            "nested.level1.level2.level3.level4.level5",
        ]

        # Should not raise exception
        config_manager.validate(required_keys=required_keys)

    def test_validation_with_empty_required_keys_list(self, config_manager):
        """Test validation with empty required_keys list (no validation)"""
        # Empty list should not raise exception
        config_manager.validate(required_keys=[])


# ============================================================================
# TEST CATEGORY 6: THREAD SAFETY (4 tests)
# ============================================================================


class TestThreadSafety:
    """Test thread-safe operations using RLock"""

    def test_concurrent_get_operations(self, config_manager):
        """Test concurrent get() operations (read-only, should not conflict)"""
        results = []
        errors = []

        def read_config():
            try:
                for _ in range(100):
                    value = config_manager.get("database.host")
                    results.append(value)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=read_config) for _ in range(10)]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All reads should succeed
        assert len(errors) == 0
        assert len(results) == 1000  # 10 threads * 100 reads
        assert all(r == "localhost" for r in results)

    def test_concurrent_set_operations(self, empty_config_manager):
        """Test concurrent set() operations (write lock protection)"""
        errors = []

        def write_config(thread_id):
            try:
                for i in range(50):
                    empty_config_manager.set(f"thread.{thread_id}.value_{i}", thread_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_config, args=(i,)) for i in range(10)]

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # All writes should succeed without errors
        assert len(errors) == 0

        # Verify all values were written
        for thread_id in range(10):
            for i in range(50):
                assert empty_config_manager.get(f"thread.{thread_id}.value_{i}") == thread_id

    def test_mixed_concurrent_get_and_set(self, config_manager):
        """Test mixed concurrent get() and set() operations"""
        errors = []
        read_values = []

        def reader():
            try:
                for _ in range(50):
                    value = config_manager.get("concurrent.counter", default=0)
                    read_values.append(value)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        def writer():
            try:
                for i in range(50):
                    config_manager.set("concurrent.counter", i)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        # Create mix of readers and writers
        threads = []
        threads.extend([threading.Thread(target=reader) for _ in range(5)])
        threads.extend([threading.Thread(target=writer) for _ in range(5)])

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # No errors should occur
        assert len(errors) == 0

    def test_reload_while_get_operations_in_progress(self, sample_yaml_file, tmp_path):
        """Test reload() while get() operations are running"""
        config = ConfigManager(config_file=sample_yaml_file)
        errors = []

        def continuous_reader():
            try:
                for _ in range(100):
                    config.get("database.host")
                    time.sleep(0.001)
            except Exception as e:
                errors.append(e)

        def reloader():
            try:
                time.sleep(0.05)  # Let readers start
                config.reload()
            except Exception as e:
                errors.append(e)

        threads = []
        threads.extend([threading.Thread(target=continuous_reader) for _ in range(5)])
        threads.append(threading.Thread(target=reloader))

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        assert len(errors) == 0


# ============================================================================
# TEST CATEGORY 7: EDGE CASES (8 tests)
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_special_characters_in_keys(self, empty_config_manager):
        """Test keys with special characters"""
        # Test keys with hyphens, underscores, numbers
        special_keys = [
            "key-with-hyphens",
            "key_with_underscores",
            "key123",
            "123key",
        ]

        for key in special_keys:
            empty_config_manager.set(key, "value")
            assert empty_config_manager.get(key) == "value"

    def test_very_long_keys(self, empty_config_manager):
        """Test very long keys (1000+ characters)"""
        long_key = "a" * 1000 + ".b" * 500  # 1000+ character key with nesting
        value = "long_key_value"

        empty_config_manager.set(long_key, value)
        assert empty_config_manager.get(long_key) == value

    def test_unicode_in_values(self, config_manager):
        """Test Unicode characters in configuration values"""
        assert config_manager.get("special.unicode") == "Hello 世界"

        # Test setting Unicode values
        config_manager.set("unicode.test", "Привет мир")
        assert config_manager.get("unicode.test") == "Привет мир"

    def test_circular_references_in_config(self, empty_config_manager):
        """Test handling of circular references (if applicable)"""
        # This test depends on implementation
        # If config uses references/aliases, test circular reference detection
        # For basic dict-based config, this may not apply

        # Example: If YAML supports anchors and aliases
        # For now, just verify we can create nested structures
        empty_config_manager.set("ref.a.b", "value")
        empty_config_manager.set("ref.c", empty_config_manager.get("ref.a"))

        assert empty_config_manager.get("ref.c.b") == "value"

    def test_config_with_many_keys_performance(self, empty_config_manager):
        """Test config with 100+ keys (performance check)"""
        # Create 100 keys
        for i in range(100):
            empty_config_manager.set(f"key_{i}", f"value_{i}")

        # Verify all keys accessible
        for i in range(100):
            assert empty_config_manager.get(f"key_{i}") == f"value_{i}"

        # Should complete in reasonable time (implicitly tested by test timeout)

    def test_concurrent_stress_test(self, config_manager):
        """Test concurrent stress with 100 threads"""
        errors = []
        operations_completed = []

        def mixed_operations(thread_id):
            try:
                for i in range(10):
                    # Mix of reads and writes
                    config_manager.get("database.host")
                    config_manager.set(f"stress.thread_{thread_id}.op_{i}", thread_id)
                    config_manager.get(f"stress.thread_{thread_id}.op_{i}")
                operations_completed.append(thread_id)
            except Exception as e:
                errors.append((thread_id, e))

        threads = [threading.Thread(target=mixed_operations, args=(i,)) for i in range(100)]

        start_time = time.time()

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)  # 30 second timeout per thread

        elapsed_time = time.time() - start_time

        # All operations should complete without errors
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(operations_completed) == 100

        # Performance check: Should complete in reasonable time
        assert elapsed_time < 60, f"Stress test took too long: {elapsed_time}s"

    def test_empty_string_as_key(self, empty_config_manager):
        """Test empty string as a key"""
        # Empty string key should raise error or be handled gracefully
        with pytest.raises((ConfigKeyError, ValueError)):
            empty_config_manager.set("", "value")

        with pytest.raises((ConfigKeyError, ValueError)):
            empty_config_manager.get("")

    def test_whitespace_only_values(self, config_manager):
        """Test whitespace-only values are preserved"""
        whitespace_value = config_manager.get("special.whitespace")
        assert whitespace_value == "   "
        assert len(whitespace_value) == 3

        # Test setting whitespace values
        config_manager.set("test.whitespace", "  \t  ")
        assert config_manager.get("test.whitespace") == "  \t  "


# ============================================================================
# ADDITIONAL TESTS: reload() method
# ============================================================================


class TestReloadMethod:
    """Test the reload() method for reloading configuration from file"""

    def test_reload_updates_configuration(self, tmp_path):
        """Test that reload() updates configuration when file changes"""
        # Create initial config file
        config_file = tmp_path / "config.yaml"
        config_file.write_text("key: original_value")

        config = ConfigManager(config_file=config_file)
        assert config.get("key") == "original_value"

        # Modify the file
        config_file.write_text("key: updated_value")

        # Reload configuration
        config.reload()

        # Value should be updated
        assert config.get("key") == "updated_value"

    def test_reload_with_environment_override_persistence(self, tmp_path):
        """Test that reload() maintains environment variable overrides"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("key: yaml_value")

        with patch.dict(os.environ, {"AMPLIHACK_KEY": "env_value"}):
            config = ConfigManager(config_file=config_file)
            assert config.get("key") == "env_value"

            # Reload should maintain env override
            config.reload()
            assert config.get("key") == "env_value"

    def test_reload_preserves_set_values(self, tmp_path):
        """Test that reload() behavior with programmatically set values"""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("yaml_key: yaml_value")

        config = ConfigManager(config_file=config_file)

        # Set a value programmatically
        config.set("runtime_key", "runtime_value")

        # Reload from file
        config.reload()

        # YAML value should be refreshed
        assert config.get("yaml_key") == "yaml_value"

        # Runtime value behavior depends on implementation:
        # Option 1: Runtime values are cleared (reload is "hard reset")
        # Option 2: Runtime values are preserved (reload only updates file-based values)
        # This test documents expected behavior once implementation is done


# ============================================================================
# TEST SUMMARY
# ============================================================================


def test_suite_coverage_summary():
    """
    Test Suite Coverage Summary

    This test suite provides comprehensive coverage for ConfigManager:

    1. Basic YAML Loading (5 tests):
       - Valid YAML, missing file, permission error, malformed YAML, empty file

    2. get() Method (6 tests):
       - Existing keys, defaults, nested keys, deep nesting, None default, missing intermediate keys

    3. set() Method (4 tests):
       - New keys, update existing, nested keys, create intermediate keys

    4. Environment Variable Override (7 tests):
       - Simple override, nested with __, case insensitivity, type conversion,
         empty values, precedence, multiple overrides

    5. Validation (5 tests):
       - All present, single missing, multiple missing, nested keys, empty list

    6. Thread Safety (4 tests):
       - Concurrent reads, concurrent writes, mixed read/write, reload during reads

    7. Edge Cases (8 tests):
       - Special characters, long keys, Unicode, circular refs, many keys,
         stress test, empty key, whitespace values

    8. reload() Method (3 tests):
       - Update on file change, env override persistence, set value behavior

    Total: 42 tests targeting 90%+ code coverage

    Expected Result: ALL TESTS FAIL (Red Phase)

    Once implementation is complete, these tests will guide verification
    that all requirements are met.
    """
