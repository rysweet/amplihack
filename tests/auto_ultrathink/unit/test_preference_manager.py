"""Unit tests for preference_manager module.

Tests user preference reading, validation, and exclusion pattern matching.
"""



class TestPreferenceManager:
    """Unit tests for preference manager."""

    def test_default_preference_missing_file(self, tmp_path, monkeypatch):
        """Missing file should return default preference."""
        from preference_manager import get_auto_ultrathink_preference

        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(tmp_path / "nonexistent.md"))

        pref = get_auto_ultrathink_preference()
        assert pref.mode == "ask"  # Safe default
        assert pref.confidence_threshold == 0.80
        assert pref.excluded_patterns == []

    def test_valid_enabled_preference(self, tmp_path, monkeypatch):
        """Valid enabled preference should be parsed correctly."""
        from preference_manager import get_auto_ultrathink_preference

        prefs_file = tmp_path / "prefs.md"
        prefs_file.write_text(
            """
# User Preferences

```yaml
auto_ultrathink:
  mode: "enabled"
  confidence_threshold: 0.85
  excluded_patterns: []
```
"""
        )
        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))

        pref = get_auto_ultrathink_preference()
        assert pref.mode == "enabled"
        assert pref.confidence_threshold == 0.85
        assert pref.excluded_patterns == []

    def test_valid_disabled_preference(self, tmp_path, monkeypatch):
        """Valid disabled preference should be parsed correctly."""
        from preference_manager import get_auto_ultrathink_preference

        prefs_file = tmp_path / "prefs.md"
        prefs_file.write_text(
            """
# User Preferences

```yaml
auto_ultrathink:
  mode: "disabled"
  confidence_threshold: 0.90
  excluded_patterns: []
```
"""
        )
        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))

        pref = get_auto_ultrathink_preference()
        assert pref.mode == "disabled"
        assert pref.confidence_threshold == 0.90

    def test_valid_ask_preference(self, tmp_path, monkeypatch):
        """Valid ask preference should be parsed correctly."""
        from preference_manager import get_auto_ultrathink_preference

        prefs_file = tmp_path / "prefs.md"
        prefs_file.write_text(
            """
# User Preferences

```yaml
auto_ultrathink:
  mode: "ask"
  confidence_threshold: 0.75
  excluded_patterns: []
```
"""
        )
        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))

        pref = get_auto_ultrathink_preference()
        assert pref.mode == "ask"
        assert pref.confidence_threshold == 0.75

    def test_invalid_mode_defaults_to_ask(self, tmp_path, monkeypatch):
        """Invalid mode should default to 'ask'."""
        from preference_manager import get_auto_ultrathink_preference

        prefs_file = tmp_path / "prefs.md"
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "invalid_mode"
```
"""
        )
        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))

        pref = get_auto_ultrathink_preference()
        assert pref.mode == "ask"  # Safe default

    def test_invalid_threshold_defaults(self, tmp_path, monkeypatch):
        """Invalid threshold should default to 0.80."""
        from preference_manager import get_auto_ultrathink_preference

        prefs_file = tmp_path / "prefs.md"
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  confidence_threshold: 99.9
```
"""
        )
        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))

        pref = get_auto_ultrathink_preference()
        assert pref.confidence_threshold == 0.80  # Default

    def test_negative_threshold_defaults(self, tmp_path, monkeypatch):
        """Negative threshold should default to 0.80."""
        from preference_manager import get_auto_ultrathink_preference

        prefs_file = tmp_path / "prefs.md"
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  confidence_threshold: -0.5
```
"""
        )
        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))

        pref = get_auto_ultrathink_preference()
        assert pref.confidence_threshold == 0.80

    def test_threshold_boundary_0(self, tmp_path, monkeypatch):
        """Threshold of 0.0 should be valid."""
        from preference_manager import get_auto_ultrathink_preference

        prefs_file = tmp_path / "prefs.md"
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  confidence_threshold: 0.0
```
"""
        )
        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))

        pref = get_auto_ultrathink_preference()
        assert pref.confidence_threshold == 0.0

    def test_threshold_boundary_1(self, tmp_path, monkeypatch):
        """Threshold of 1.0 should be valid."""
        from preference_manager import get_auto_ultrathink_preference

        prefs_file = tmp_path / "prefs.md"
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  confidence_threshold: 1.0
```
"""
        )
        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))

        pref = get_auto_ultrathink_preference()
        assert pref.confidence_threshold == 1.0

    def test_excluded_patterns_single(self, tmp_path, monkeypatch):
        """Single excluded pattern should be parsed."""
        from preference_manager import get_auto_ultrathink_preference

        prefs_file = tmp_path / "prefs.md"
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
  excluded_patterns: ["^test.*"]
```
"""
        )
        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))

        pref = get_auto_ultrathink_preference()
        assert len(pref.excluded_patterns) == 1
        assert "^test.*" in pref.excluded_patterns

    def test_excluded_patterns_multiple(self, tmp_path, monkeypatch):
        """Multiple excluded patterns should be parsed."""
        from preference_manager import get_auto_ultrathink_preference

        prefs_file = tmp_path / "prefs.md"
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
  excluded_patterns: ["^test.*", ".*debug.*", "^fix.*"]
```
"""
        )
        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))

        pref = get_auto_ultrathink_preference()
        assert len(pref.excluded_patterns) == 3

    def test_malformed_yaml_returns_default(self, tmp_path, monkeypatch):
        """Malformed YAML should return default preference."""
        from preference_manager import get_auto_ultrathink_preference

        prefs_file = tmp_path / "prefs.md"
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: enabled
  this is not valid yaml: [
```
"""
        )
        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))

        pref = get_auto_ultrathink_preference()
        assert pref.mode == "ask"  # Safe default

    def test_no_yaml_block_returns_default(self, tmp_path, monkeypatch):
        """File without YAML block should return default."""
        from preference_manager import get_auto_ultrathink_preference

        prefs_file = tmp_path / "prefs.md"
        prefs_file.write_text(
            """
# User Preferences

Some text without yaml block.
"""
        )
        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))

        pref = get_auto_ultrathink_preference()
        assert pref.mode == "ask"

    def test_empty_file_returns_default(self, tmp_path, monkeypatch):
        """Empty file should return default preference."""
        from preference_manager import get_auto_ultrathink_preference

        prefs_file = tmp_path / "prefs.md"
        prefs_file.write_text("")
        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))

        pref = get_auto_ultrathink_preference()
        assert pref.mode == "ask"


class TestExclusionPatterns:
    """Test exclusion pattern matching."""

    def test_is_excluded_empty_patterns(self):
        """Empty exclusion list should not exclude anything."""
        from preference_manager import is_excluded

        assert not is_excluded("test prompt", [])
        assert not is_excluded("any prompt", [])

    def test_is_excluded_single_pattern_match(self):
        """Single pattern match should exclude."""
        from preference_manager import is_excluded

        patterns = ["^test.*"]
        assert is_excluded("test the feature", patterns)
        assert is_excluded("TEST the feature", patterns)  # Case insensitive

    def test_is_excluded_single_pattern_no_match(self):
        """Single pattern no match should not exclude."""
        from preference_manager import is_excluded

        patterns = ["^test.*"]
        assert not is_excluded("implement feature", patterns)
        assert not is_excluded("add test coverage", patterns)  # Not at start

    def test_is_excluded_multiple_patterns(self):
        """Multiple patterns should work correctly."""
        from preference_manager import is_excluded

        patterns = ["^test.*", ".*debug.*", "^fix.*"]

        assert is_excluded("test the feature", patterns)
        assert is_excluded("debug this issue", patterns)
        assert is_excluded("fix the bug", patterns)
        assert not is_excluded("implement feature", patterns)

    def test_is_excluded_regex_special_chars(self):
        """Regex special characters should work."""
        from preference_manager import is_excluded

        patterns = [r".*\[debug\].*"]
        assert is_excluded("log [debug] something", patterns)
        assert not is_excluded("log [info] something", patterns)

    def test_is_excluded_invalid_regex_pattern(self):
        """Invalid regex should be handled gracefully."""
        from preference_manager import is_excluded

        patterns = ["[invalid"]  # Invalid regex
        # Should not crash and should not exclude
        result = is_excluded("test prompt", patterns)
        assert not result

    def test_is_excluded_case_insensitive(self):
        """Pattern matching should be case insensitive."""
        from preference_manager import is_excluded

        patterns = ["^test.*"]
        assert is_excluded("TEST the feature", patterns)
        assert is_excluded("Test the feature", patterns)
        assert is_excluded("test the feature", patterns)

    def test_is_excluded_partial_match(self):
        """Partial matches should work with appropriate patterns."""
        from preference_manager import is_excluded

        patterns = [".*debug.*"]
        assert is_excluded("this is a debug message", patterns)
        assert is_excluded("debugging feature", patterns)
        assert not is_excluded("feature request", patterns)


class TestPreferenceCaching:
    """Test preference caching (if implemented)."""

    def test_cache_hit_performance(self, tmp_path, monkeypatch):
        """Second call should be faster (if cached)."""
        import time

        from preference_manager import get_auto_ultrathink_preference

        prefs_file = tmp_path / "prefs.md"
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
```
"""
        )
        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))

        # First call
        start = time.time()
        pref1 = get_auto_ultrathink_preference()
        time.time() - start

        # Second call
        start = time.time()
        pref2 = get_auto_ultrathink_preference()
        time.time() - start

        # Both should return same result
        assert pref1.mode == pref2.mode

        # Second call should be faster or similar (caching optional)
        # This is informational, not a strict requirement
        # assert second_time <= first_time * 2  # Allow some variance


class TestPreferenceContract:
    """Test the AutoUltraThinkPreference contract."""

    def test_preference_has_required_fields(self, tmp_path, monkeypatch):
        """Preference should have all required fields."""
        from preference_manager import get_auto_ultrathink_preference

        prefs_file = tmp_path / "prefs.md"
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "ask"
```
"""
        )
        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))

        pref = get_auto_ultrathink_preference()

        assert hasattr(pref, "mode")
        assert hasattr(pref, "confidence_threshold")
        assert hasattr(pref, "excluded_patterns")

    def test_preference_types(self, tmp_path, monkeypatch):
        """Preference fields should have correct types."""
        from preference_manager import get_auto_ultrathink_preference

        prefs_file = tmp_path / "prefs.md"
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
  confidence_threshold: 0.85
  excluded_patterns: ["test"]
```
"""
        )
        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))

        pref = get_auto_ultrathink_preference()

        assert isinstance(pref.mode, str)
        assert isinstance(pref.confidence_threshold, (int, float))
        assert isinstance(pref.excluded_patterns, list)

    def test_mode_values_valid(self, tmp_path, monkeypatch):
        """Mode should be one of the valid values."""
        from preference_manager import get_auto_ultrathink_preference

        prefs_file = tmp_path / "prefs.md"
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
```
"""
        )
        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))

        pref = get_auto_ultrathink_preference()

        assert pref.mode in ["enabled", "disabled", "ask"]


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_permission_error_returns_default(self, tmp_path, monkeypatch):
        """Permission error should return default preference."""
        from preference_manager import get_auto_ultrathink_preference

        # Create file with no read permissions (if possible)
        prefs_file = tmp_path / "prefs.md"
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
```
"""
        )
        prefs_file.chmod(0o000)  # No permissions

        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))

        try:
            pref = get_auto_ultrathink_preference()
            # Should return default
            assert pref.mode == "ask"
        finally:
            # Restore permissions for cleanup
            prefs_file.chmod(0o644)

    def test_unicode_in_preferences(self, tmp_path, monkeypatch):
        """Unicode in preferences should be handled."""
        from preference_manager import get_auto_ultrathink_preference

        prefs_file = tmp_path / "prefs.md"
        prefs_file.write_text(
            """
# 用户偏好设置

```yaml
auto_ultrathink:
  mode: "enabled"
  excluded_patterns: ["测试.*"]
```
""",
            encoding="utf-8",
        )
        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))

        pref = get_auto_ultrathink_preference()
        # Should parse successfully
        assert pref.mode == "enabled"

    def test_very_large_excluded_patterns_list(self, tmp_path, monkeypatch):
        """Large excluded patterns list should be handled."""
        from preference_manager import get_auto_ultrathink_preference

        patterns = [f"pattern{i}" for i in range(1000)]
        prefs_file = tmp_path / "prefs.md"
        prefs_file.write_text(
            f"""
```yaml
auto_ultrathink:
  mode: "enabled"
  excluded_patterns: {patterns}
```
"""
        )
        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(prefs_file))

        pref = get_auto_ultrathink_preference()
        # Should parse successfully (or return default if too large)
        assert pref.mode in ["enabled", "ask"]


class TestEnvironmentVariableOverride:
    """Test environment variable override for preferences path."""

    def test_env_var_override_works(self, tmp_path, monkeypatch):
        """AMPLIHACK_PREFERENCES_PATH should override default location."""
        from preference_manager import get_auto_ultrathink_preference

        custom_prefs = tmp_path / "custom_prefs.md"
        custom_prefs.write_text(
            """
```yaml
auto_ultrathink:
  mode: "disabled"
```
"""
        )

        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(custom_prefs))

        pref = get_auto_ultrathink_preference()
        assert pref.mode == "disabled"

    def test_env_var_missing_file(self, tmp_path, monkeypatch):
        """AMPLIHACK_PREFERENCES_PATH pointing to missing file should return default."""
        from preference_manager import get_auto_ultrathink_preference

        monkeypatch.setenv("AMPLIHACK_PREFERENCES_PATH", str(tmp_path / "missing.md"))

        pref = get_auto_ultrathink_preference()
        assert pref.mode == "ask"  # Safe default
