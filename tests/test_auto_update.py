"""Comprehensive test suite for auto_update module.

Tests cover:
- Version comparison logic
- Cache operations (load, save, expiry)
- GitHub API calls (success, timeout, errors)
- Update check workflows
- User prompt and upgrade flow
- CLI restart mechanism
- Error handling and graceful failures
"""

import subprocess
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, patch

from amplihack.auto_update import (
    UpdateCache,
    UpdateCheckResult,
    _compare_versions,
    _fetch_latest_version,
    _load_cache,
    _run_upgrade,
    _save_cache,
    check_for_updates,
    prompt_and_upgrade,
)


class TestUpdateCache:
    """Tests for UpdateCache dataclass."""

    def test_is_expired_true(self):
        """Cache should be expired when past TTL."""
        # Create cache from 48 hours ago
        past_time = datetime.now(UTC) - timedelta(hours=48)
        cache = UpdateCache(
            last_check=past_time.isoformat(),
            latest_version="0.2.0",
            check_interval_hours=24,
        )

        assert cache.is_expired() is True

    def test_is_expired_false(self):
        """Cache should not be expired within TTL."""
        # Create cache from 1 hour ago
        recent_time = datetime.now(UTC) - timedelta(hours=1)
        cache = UpdateCache(
            last_check=recent_time.isoformat(),
            latest_version="0.2.0",
            check_interval_hours=24,
        )

        assert cache.is_expired() is False

    def test_is_expired_invalid_timestamp(self):
        """Invalid timestamp should be treated as expired."""
        cache = UpdateCache(
            last_check="not-a-timestamp",
            latest_version="0.2.0",
            check_interval_hours=24,
        )

        assert cache.is_expired() is True

    def test_to_dict(self):
        """Should serialize to dict correctly."""
        cache = UpdateCache(
            last_check="2024-01-01T00:00:00Z",
            latest_version="0.2.1",
            check_interval_hours=48,
        )

        result = cache.to_dict()

        assert result == {
            "last_check": "2024-01-01T00:00:00Z",
            "latest_version": "0.2.1",
            "check_interval_hours": 48,
        }

    def test_from_dict(self):
        """Should deserialize from dict correctly."""
        data = {
            "last_check": "2024-01-01T00:00:00Z",
            "latest_version": "0.2.1",
            "check_interval_hours": 48,
        }

        cache = UpdateCache.from_dict(data)

        assert cache.last_check == "2024-01-01T00:00:00Z"
        assert cache.latest_version == "0.2.1"
        assert cache.check_interval_hours == 48

    def test_from_dict_missing_fields(self):
        """Should handle missing fields with defaults."""
        data = {}

        cache = UpdateCache.from_dict(data)

        assert cache.last_check == ""
        assert cache.latest_version == ""
        assert cache.check_interval_hours == 24


class TestVersionComparison:
    """Tests for _compare_versions function."""

    def test_newer_version(self):
        """Should return True when latest > current."""
        assert _compare_versions("0.2.0", "0.2.1") is True
        assert _compare_versions("0.2.0", "0.3.0") is True
        assert _compare_versions("0.2.0", "1.0.0") is True

    def test_older_version(self):
        """Should return False when latest < current."""
        assert _compare_versions("0.2.1", "0.2.0") is False
        assert _compare_versions("1.0.0", "0.2.0") is False

    def test_same_version(self):
        """Should return False when versions are equal."""
        assert _compare_versions("0.2.0", "0.2.0") is False

    def test_prerelease_versions(self):
        """Should handle prerelease versions correctly."""
        assert _compare_versions("0.2.0", "0.2.1-alpha") is True
        assert _compare_versions("0.2.0-beta", "0.2.0") is True

    @patch("amplihack.auto_update.parse_version", None)
    def test_fallback_string_comparison(self):
        """Should fall back to string comparison if packaging not available."""
        # String comparison: "0.2.1" > "0.2.0"
        assert _compare_versions("0.2.0", "0.2.1") is True

    def test_invalid_version_format(self):
        """Should return False for invalid versions."""
        assert _compare_versions("invalid", "0.2.0") is False
        assert _compare_versions("0.2.0", "invalid") is False


class TestCacheOperations:
    """Tests for cache load/save operations."""

    def test_save_and_load_cache(self, tmp_path):
        """Should save and load cache correctly."""
        cache_file = tmp_path / "update_check.json"
        cache = UpdateCache(
            last_check="2024-01-01T00:00:00Z",
            latest_version="0.2.1",
            check_interval_hours=24,
        )

        # Save cache
        result = _save_cache(cache_file, cache)
        assert result is True
        assert cache_file.exists()

        # Load cache
        loaded = _load_cache(cache_file)
        assert loaded is not None
        assert loaded.last_check == cache.last_check
        assert loaded.latest_version == cache.latest_version
        assert loaded.check_interval_hours == cache.check_interval_hours

    def test_load_cache_not_exists(self, tmp_path):
        """Should return None when cache file doesn't exist."""
        cache_file = tmp_path / "nonexistent.json"

        result = _load_cache(cache_file)

        assert result is None

    def test_load_cache_invalid_json(self, tmp_path):
        """Should return None when cache file has invalid JSON."""
        cache_file = tmp_path / "invalid.json"
        cache_file.write_text("not valid json{")

        result = _load_cache(cache_file)

        assert result is None

    def test_save_cache_creates_directory(self, tmp_path):
        """Should create parent directories if they don't exist."""
        cache_file = tmp_path / "nested" / "dir" / "cache.json"
        cache = UpdateCache(
            last_check="2024-01-01T00:00:00Z",
            latest_version="0.2.1",
        )

        result = _save_cache(cache_file, cache)

        assert result is True
        assert cache_file.exists()

    def test_save_cache_permission_error(self, tmp_path):
        """Should return False on permission errors."""
        cache_file = tmp_path / "cache.json"

        # Create read-only directory
        cache_file.parent.mkdir(exist_ok=True)
        cache_file.parent.chmod(0o444)

        cache = UpdateCache(
            last_check="2024-01-01T00:00:00Z",
            latest_version="0.2.1",
        )

        result = _save_cache(cache_file, cache)

        assert result is False

        # Cleanup: restore permissions
        cache_file.parent.chmod(0o755)


class TestFetchLatestVersion:
    """Tests for _fetch_latest_version function."""

    @patch("amplihack.auto_update.requests")
    def test_fetch_success(self, mock_requests):
        """Should fetch and parse version correctly."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "tag_name": "v0.2.1",
            "html_url": "https://github.com/rysweet/amplihack/releases/tag/v0.2.1",
        }
        mock_response.raise_for_status = Mock()
        mock_requests.get.return_value = mock_response

        result = _fetch_latest_version(timeout=5)

        assert result is not None
        version, url = result
        assert version == "0.2.1"  # 'v' prefix stripped
        assert url == "https://github.com/rysweet/amplihack/releases/tag/v0.2.1"

    @patch("amplihack.auto_update.requests")
    def test_fetch_timeout(self, mock_requests):
        """Should return None on timeout."""
        mock_requests.get.side_effect = mock_requests.Timeout("Timeout")

        result = _fetch_latest_version(timeout=5)

        assert result is None

    @patch("amplihack.auto_update.requests")
    def test_fetch_network_error(self, mock_requests):
        """Should return None on network errors."""
        mock_requests.get.side_effect = mock_requests.RequestException("Network error")

        result = _fetch_latest_version(timeout=5)

        assert result is None

    @patch("amplihack.auto_update.requests")
    def test_fetch_invalid_response(self, mock_requests):
        """Should return None when API returns invalid data."""
        mock_response = Mock()
        mock_response.json.return_value = {}  # Missing tag_name
        mock_response.raise_for_status = Mock()
        mock_requests.get.return_value = mock_response

        result = _fetch_latest_version(timeout=5)

        assert result is None

    @patch("amplihack.auto_update.requests", None)
    def test_fetch_no_requests_library(self):
        """Should return None when requests library not available."""
        result = _fetch_latest_version(timeout=5)

        assert result is None


class TestCheckForUpdates:
    """Tests for check_for_updates function."""

    def test_update_available_fresh_check(self, tmp_path):
        """Should detect update on fresh check (no cache)."""
        with patch("amplihack.auto_update._fetch_latest_version") as mock_fetch:
            mock_fetch.return_value = ("0.3.0", "https://github.com/...")

            result = check_for_updates(
                current_version="0.2.0",
                cache_dir=tmp_path,
                check_interval_hours=24,
                timeout_seconds=5,
            )

        assert result is not None
        assert result.current_version == "0.2.0"
        assert result.latest_version == "0.3.0"
        assert result.is_newer is True

        # Cache should be created
        cache_file = tmp_path / "update_check.json"
        assert cache_file.exists()

    def test_no_update_available(self, tmp_path):
        """Should return None when no update available."""
        with patch("amplihack.auto_update._fetch_latest_version") as mock_fetch:
            mock_fetch.return_value = ("0.2.0", "https://github.com/...")

            result = check_for_updates(
                current_version="0.2.0",
                cache_dir=tmp_path,
                check_interval_hours=24,
                timeout_seconds=5,
            )

        assert result is None

    def test_use_cached_result_not_expired(self, tmp_path):
        """Should use cached result when not expired."""
        # Create valid cache
        cache_file = tmp_path / "update_check.json"
        cache = UpdateCache(
            last_check=datetime.now(UTC).isoformat(),
            latest_version="0.3.0",
            check_interval_hours=24,
        )
        _save_cache(cache_file, cache)

        with patch("amplihack.auto_update._fetch_latest_version") as mock_fetch:
            result = check_for_updates(
                current_version="0.2.0",
                cache_dir=tmp_path,
                check_interval_hours=24,
                timeout_seconds=5,
            )

            # Should not call API (cache hit)
            mock_fetch.assert_not_called()

        assert result is not None
        assert result.latest_version == "0.3.0"

    def test_ignore_expired_cache(self, tmp_path):
        """Should fetch fresh data when cache expired."""
        # Create expired cache
        cache_file = tmp_path / "update_check.json"
        old_time = datetime.now(UTC) - timedelta(hours=48)
        cache = UpdateCache(
            last_check=old_time.isoformat(),
            latest_version="0.2.5",
            check_interval_hours=24,
        )
        _save_cache(cache_file, cache)

        with patch("amplihack.auto_update._fetch_latest_version") as mock_fetch:
            mock_fetch.return_value = ("0.3.0", "https://github.com/...")

            result = check_for_updates(
                current_version="0.2.0",
                cache_dir=tmp_path,
                check_interval_hours=24,
                timeout_seconds=5,
            )

            # Should call API (cache expired)
            mock_fetch.assert_called_once()

        assert result is not None
        assert result.latest_version == "0.3.0"  # Fresh data, not cached 0.2.5

    def test_api_failure_returns_none(self, tmp_path):
        """Should return None when API call fails."""
        with patch("amplihack.auto_update._fetch_latest_version") as mock_fetch:
            mock_fetch.return_value = None  # API failure

            result = check_for_updates(
                current_version="0.2.0",
                cache_dir=tmp_path,
                check_interval_hours=24,
                timeout_seconds=5,
            )

        assert result is None

    def test_older_version_installed(self, tmp_path):
        """Should return None when current version is newer than latest."""
        with patch("amplihack.auto_update._fetch_latest_version") as mock_fetch:
            mock_fetch.return_value = ("0.1.0", "https://github.com/...")

            result = check_for_updates(
                current_version="0.2.0",
                cache_dir=tmp_path,
                check_interval_hours=24,
                timeout_seconds=5,
            )

        assert result is None


class TestRunUpgrade:
    """Tests for _run_upgrade function."""

    @patch("amplihack.auto_update.subprocess.run")
    def test_upgrade_success(self, mock_run):
        """Should return True on successful upgrade."""
        mock_run.return_value = Mock(returncode=0, stderr="")

        result = _run_upgrade(timeout=60)

        assert result is True
        mock_run.assert_called_once_with(
            ["uv", "tool", "upgrade", "amplihack"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )

    @patch("amplihack.auto_update.subprocess.run")
    def test_upgrade_failure(self, mock_run):
        """Should return False when upgrade command fails."""
        mock_run.return_value = Mock(returncode=1, stderr="Error message")

        result = _run_upgrade(timeout=60)

        assert result is False

    @patch("amplihack.auto_update.subprocess.run")
    def test_upgrade_timeout(self, mock_run):
        """Should return False on timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("uv", 60)

        result = _run_upgrade(timeout=60)

        assert result is False

    @patch("amplihack.auto_update.subprocess.run")
    def test_upgrade_uv_not_found(self, mock_run):
        """Should return False when uv command not found."""
        mock_run.side_effect = FileNotFoundError("uv not found")

        result = _run_upgrade(timeout=60)

        assert result is False


class TestPromptAndUpgrade:
    """Tests for prompt_and_upgrade function."""

    def test_user_accepts_upgrade_success(self, capsys):
        """Should upgrade and restart when user accepts."""
        update_info = UpdateCheckResult(
            current_version="0.2.0",
            latest_version="0.3.0",
            is_newer=True,
            release_url="https://github.com/rysweet/amplihack/releases/tag/v0.3.0",
        )

        with patch("builtins.input", return_value="y"):
            with patch("amplihack.auto_update._run_upgrade", return_value=True):
                with patch("amplihack.auto_update._restart_cli") as mock_restart:
                    result = prompt_and_upgrade(update_info, ["claude"])

                    mock_restart.assert_called_once_with(["claude"])

        assert result is True

    def test_user_accepts_empty_response(self):
        """Should treat empty response as 'yes'."""
        update_info = UpdateCheckResult(
            current_version="0.2.0",
            latest_version="0.3.0",
            is_newer=True,
            release_url="https://github.com/...",
        )

        with patch("builtins.input", return_value=""):
            with patch("amplihack.auto_update._run_upgrade", return_value=True):
                with patch("amplihack.auto_update._restart_cli"):
                    result = prompt_and_upgrade(update_info, ["claude"])

        assert result is True

    def test_user_declines_upgrade(self, capsys):
        """Should return False when user declines."""
        update_info = UpdateCheckResult(
            current_version="0.2.0",
            latest_version="0.3.0",
            is_newer=True,
            release_url="https://github.com/...",
        )

        with patch("builtins.input", return_value="n"):
            result = prompt_and_upgrade(update_info, ["claude"])

        assert result is False

        # Should print upgrade instructions
        captured = capsys.readouterr()
        assert "uv tool upgrade amplihack" in captured.out

    def test_upgrade_fails(self, capsys):
        """Should return False and show instructions when upgrade fails."""
        update_info = UpdateCheckResult(
            current_version="0.2.0",
            latest_version="0.3.0",
            is_newer=True,
            release_url="https://github.com/...",
        )

        with patch("builtins.input", return_value="y"):
            with patch("amplihack.auto_update._run_upgrade", return_value=False):
                result = prompt_and_upgrade(update_info, ["claude"])

        assert result is False

        # Should print error and manual instructions
        captured = capsys.readouterr()
        assert "Upgrade failed" in captured.out
        assert "uv tool upgrade amplihack" in captured.out

    def test_keyboard_interrupt(self, capsys):
        """Should handle Ctrl+C gracefully."""
        update_info = UpdateCheckResult(
            current_version="0.2.0",
            latest_version="0.3.0",
            is_newer=True,
            release_url="https://github.com/...",
        )

        with patch("builtins.input", side_effect=KeyboardInterrupt):
            result = prompt_and_upgrade(update_info, ["claude"])

        assert result is False

        captured = capsys.readouterr()
        assert "cancelled" in captured.out.lower()

    def test_display_format(self, capsys):
        """Should display update info with clean formatting."""
        update_info = UpdateCheckResult(
            current_version="0.2.0",
            latest_version="0.3.0",
            is_newer=True,
            release_url="https://github.com/rysweet/amplihack/releases/tag/v0.3.0",
        )

        with patch("builtins.input", return_value="n"):
            prompt_and_upgrade(update_info, ["claude"])

        captured = capsys.readouterr()
        assert "0.2.0" in captured.out  # Current version
        assert "0.3.0" in captured.out  # Latest version
        assert "github.com" in captured.out  # Release URL
        assert "─" in captured.out  # Separator line


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_complete_update_workflow(self, tmp_path):
        """Test complete workflow: check -> prompt -> upgrade -> restart."""
        # Step 1: Check for updates
        with patch("amplihack.auto_update._fetch_latest_version") as mock_fetch:
            mock_fetch.return_value = ("0.3.0", "https://github.com/...")

            result = check_for_updates(
                current_version="0.2.0",
                cache_dir=tmp_path,
                check_interval_hours=24,
                timeout_seconds=5,
            )

        assert result is not None
        assert result.is_newer is True

        # Step 2: Prompt and upgrade
        with patch("builtins.input", return_value="y"):
            with patch("amplihack.auto_update._run_upgrade", return_value=True):
                with patch("amplihack.auto_update._restart_cli") as mock_restart:
                    upgrade_result = prompt_and_upgrade(result, ["claude"])
                    mock_restart.assert_called_once()

        assert upgrade_result is True

    def test_offline_graceful_degradation(self, tmp_path):
        """Should fail gracefully when offline."""
        with patch("amplihack.auto_update._fetch_latest_version") as mock_fetch:
            mock_fetch.return_value = None  # Simulate offline

            result = check_for_updates(
                current_version="0.2.0",
                cache_dir=tmp_path,
                check_interval_hours=24,
                timeout_seconds=5,
            )

        # Should return None, not raise exception
        assert result is None

    def test_cache_reduces_api_calls(self, tmp_path):
        """Should use cache to avoid redundant API calls."""
        with patch("amplihack.auto_update._fetch_latest_version") as mock_fetch:
            mock_fetch.return_value = ("0.3.0", "https://github.com/...")

            # First call - should fetch
            check_for_updates(
                current_version="0.2.0",
                cache_dir=tmp_path,
                check_interval_hours=24,
                timeout_seconds=5,
            )

            # Second call - should use cache
            check_for_updates(
                current_version="0.2.0",
                cache_dir=tmp_path,
                check_interval_hours=24,
                timeout_seconds=5,
            )

        # Only one API call despite two check_for_updates calls
        assert mock_fetch.call_count == 1
