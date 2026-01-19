"""
TDD Tests for Smart Memory Management (Issue #1953)

Test Strategy:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)

These tests be written FIRST (TDD) and will FAIL until implementation be complete.

Formula: N = max(8192, total_ram_mb // 4) capped at 32GB
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Dict, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest


# =============================================================================
# UNIT TESTS (60%)
# =============================================================================


class TestDetectSystemRAM:
    """Test system RAM detection across platforms."""

    def test_detect_ram_linux_with_meminfo(self):
        """Test RAM detection on Linux using /proc/meminfo."""
        mock_meminfo = "MemTotal:       16384000 kB\nMemFree:        8000000 kB"

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=mock_meminfo):
                from amplihack.launcher.memory_config import detect_system_ram_gb

                ram_gb = detect_system_ram_gb()
                assert ram_gb == 16  # 16384000 KB ≈ 16 GB

    def test_detect_ram_macos_with_sysctl(self):
        """Test RAM detection on macOS using sysctl."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "17179869184"  # 16 GB in bytes

        with patch("platform.system", return_value="Darwin"):
            with patch("subprocess.run", return_value=mock_result):
                from amplihack.launcher.memory_config import detect_system_ram_gb

                ram_gb = detect_system_ram_gb()
                assert ram_gb == 16

    def test_detect_ram_windows_with_wmic(self):
        """Test RAM detection on Windows using wmic."""
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "TotalPhysicalMemory\n17179869184"  # 16 GB

        with patch("platform.system", return_value="Windows"):
            with patch("subprocess.run", return_value=mock_result):
                from amplihack.launcher.memory_config import detect_system_ram_gb

                ram_gb = detect_system_ram_gb()
                assert ram_gb == 16

    def test_detect_ram_insufficient_system(self):
        """Test detection on systems with less than 4GB RAM."""
        mock_meminfo = "MemTotal:       2048000 kB\n"  # 2 GB

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=mock_meminfo):
                from amplihack.launcher.memory_config import detect_system_ram_gb

                ram_gb = detect_system_ram_gb()
                assert ram_gb == 2

    def test_detect_ram_command_failure(self):
        """Test graceful handling when RAM detection fails."""
        with patch("platform.system", return_value="Linux"):
            with patch("pathlib.Path.exists", return_value=False):
                with patch("subprocess.run", side_effect=Exception("Command failed")):
                    from amplihack.launcher.memory_config import detect_system_ram_gb

                    # Should return None or raise appropriate error
                    ram_gb = detect_system_ram_gb()
                    assert ram_gb is None or ram_gb == 0


class TestCalculateRecommendedLimit:
    """Test memory limit calculation with max() formula."""

    def test_calculate_limit_small_system_uses_minimum(self):
        """Test that small systems get minimum 8GB limit."""
        from amplihack.launcher.memory_config import calculate_recommended_limit

        # 16 GB system: 16 * 1024 / 4 = 4096 MB, but max(8192, 4096) = 8192
        limit_mb = calculate_recommended_limit(16)
        assert limit_mb == 8192

    def test_calculate_limit_medium_system_uses_quarter(self):
        """Test that medium systems get 1/4 of RAM."""
        from amplihack.launcher.memory_config import calculate_recommended_limit

        # 64 GB system: 64 * 1024 / 4 = 16384 MB, max(8192, 16384) = 16384
        limit_mb = calculate_recommended_limit(64)
        assert limit_mb == 16384

    def test_calculate_limit_large_system_capped_at_32gb(self):
        """Test that large systems are capped at 32GB."""
        from amplihack.launcher.memory_config import calculate_recommended_limit

        # 256 GB system: would be 64 GB, but capped at 32 GB
        limit_mb = calculate_recommended_limit(256)
        assert limit_mb == 32768  # 32 GB

    def test_calculate_limit_exact_boundary_32gb(self):
        """Test calculation at exact 32GB boundary."""
        from amplihack.launcher.memory_config import calculate_recommended_limit

        # 128 GB system: 128 * 1024 / 4 = 32768 MB (exactly 32 GB)
        limit_mb = calculate_recommended_limit(128)
        assert limit_mb == 32768

    def test_calculate_limit_edge_cases(self):
        """Test edge cases for limit calculation."""
        from amplihack.launcher.memory_config import calculate_recommended_limit

        # Test various RAM sizes
        test_cases = [
            (4, 8192),    # 4 GB → 8 GB minimum
            (8, 8192),    # 8 GB → 8 GB minimum
            (32, 8192),   # 32 GB → 8 GB (32*1024/4 = 8192)
            (48, 12288),  # 48 GB → 12 GB
            (96, 24576),  # 96 GB → 24 GB
            (192, 32768), # 192 GB → 32 GB (capped)
        ]

        for ram_gb, expected_mb in test_cases:
            assert calculate_recommended_limit(ram_gb) == expected_mb


class TestParseNodeOptions:
    """Test parsing of existing NODE_OPTIONS."""

    def test_parse_empty_options(self):
        """Test parsing when NODE_OPTIONS is empty."""
        from amplihack.launcher.memory_config import parse_node_options

        result = parse_node_options("")
        assert result == {}

    def test_parse_single_memory_flag(self):
        """Test parsing single --max-old-space-size flag."""
        from amplihack.launcher.memory_config import parse_node_options

        result = parse_node_options("--max-old-space-size=4096")
        assert result["max-old-space-size"] == 4096

    def test_parse_multiple_flags(self):
        """Test parsing multiple flags."""
        from amplihack.launcher.memory_config import parse_node_options

        options = "--max-old-space-size=4096 --no-warnings --expose-gc"
        result = parse_node_options(options)

        assert result["max-old-space-size"] == 4096
        assert result["no-warnings"] is True
        assert result["expose-gc"] is True

    def test_parse_mixed_format_flags(self):
        """Test parsing flags with different formats."""
        from amplihack.launcher.memory_config import parse_node_options

        options = "--max-old-space-size=8192 --no-deprecation --stack-size=2048"
        result = parse_node_options(options)

        assert result["max-old-space-size"] == 8192
        assert result["no-deprecation"] is True
        assert result["stack-size"] == 2048

    def test_parse_invalid_format(self):
        """Test handling of invalid option formats."""
        from amplihack.launcher.memory_config import parse_node_options

        # Should handle gracefully or raise clear error
        result = parse_node_options("invalid-format --max-old-space-size")
        # Implementation should define behavior


class TestMergeNodeOptions:
    """Test merging new memory limit with existing options."""

    def test_merge_into_empty_options(self):
        """Test merging into empty existing options."""
        from amplihack.launcher.memory_config import merge_node_options

        result = merge_node_options({}, 8192)
        assert "--max-old-space-size=8192" in result

    def test_merge_replaces_existing_limit(self):
        """Test that new limit replaces existing one."""
        from amplihack.launcher.memory_config import merge_node_options

        existing = {"max-old-space-size": 4096, "no-warnings": True}
        result = merge_node_options(existing, 16384)

        assert "--max-old-space-size=16384" in result
        assert "--no-warnings" in result

    def test_merge_preserves_other_flags(self):
        """Test that non-memory flags are preserved."""
        from amplihack.launcher.memory_config import merge_node_options

        existing = {
            "max-old-space-size": 4096,
            "expose-gc": True,
            "no-deprecation": True,
            "stack-size": 2048
        }
        result = merge_node_options(existing, 8192)

        assert "--max-old-space-size=8192" in result
        assert "--expose-gc" in result
        assert "--no-deprecation" in result
        assert "--stack-size=2048" in result

    def test_merge_output_format(self):
        """Test that merged output is valid NODE_OPTIONS format."""
        from amplihack.launcher.memory_config import merge_node_options

        existing = {"no-warnings": True}
        result = merge_node_options(existing, 8192)

        # Should be space-separated flags
        assert result.startswith("--")
        assert " --" in result or len(result.split()) == 1


class TestShouldWarnAboutLimit:
    """Test warning logic for insufficient memory."""

    def test_warn_below_minimum_8gb(self):
        """Test warning when limit is below 8GB minimum."""
        from amplihack.launcher.memory_config import should_warn_about_limit

        assert should_warn_about_limit(4096) is True  # 4 GB
        assert should_warn_about_limit(6144) is True  # 6 GB

    def test_no_warn_at_minimum_8gb(self):
        """Test no warning at exactly 8GB."""
        from amplihack.launcher.memory_config import should_warn_about_limit

        assert should_warn_about_limit(8192) is False

    def test_no_warn_above_minimum(self):
        """Test no warning above 8GB."""
        from amplihack.launcher.memory_config import should_warn_about_limit

        assert should_warn_about_limit(16384) is False
        assert should_warn_about_limit(32768) is False

    def test_warn_zero_or_negative(self):
        """Test warning for invalid values."""
        from amplihack.launcher.memory_config import should_warn_about_limit

        assert should_warn_about_limit(0) is True
        assert should_warn_about_limit(-1) is True


class TestPromptUserConsent:
    """Test user consent prompting."""

    def test_prompt_displays_current_and_recommended(self):
        """Test that prompt shows both current and recommended limits."""
        from amplihack.launcher.memory_config import prompt_user_consent

        config = {
            "current_limit_mb": 4096,
            "recommended_limit_mb": 8192,
            "system_ram_gb": 32
        }

        with patch("builtins.input", return_value="y"):
            result = prompt_user_consent(config)
            assert result is True

    def test_prompt_accepts_yes_variants(self):
        """Test that prompt accepts various 'yes' inputs."""
        from amplihack.launcher.memory_config import prompt_user_consent

        config = {"current_limit_mb": 4096, "recommended_limit_mb": 8192}

        for response in ["y", "Y", "yes", "YES", "Yes"]:
            with patch("sys.stdin.isatty", return_value=True):
                with patch("builtins.input", return_value=response):
                    assert prompt_user_consent(config) is True

    def test_prompt_rejects_no_variants(self):
        """Test that prompt rejects 'no' inputs."""
        from amplihack.launcher.memory_config import prompt_user_consent

        config = {"current_limit_mb": 4096, "recommended_limit_mb": 8192}

        for response in ["n", "N", "no", "NO", "No"]:
            with patch("sys.stdin.isatty", return_value=True):
                with patch("builtins.input", return_value=response):
                    assert prompt_user_consent(config) is False

    def test_prompt_handles_empty_input(self):
        """Test that prompt handles empty input (default to no)."""
        from amplihack.launcher.memory_config import prompt_user_consent

        config = {"current_limit_mb": 4096, "recommended_limit_mb": 8192}

        with patch("sys.stdin.isatty", return_value=True):
            with patch("builtins.input", return_value=""):
                result = prompt_user_consent(config, default_response=False)
                assert result is False


# =============================================================================
# INTEGRATION TESTS (30%)
# =============================================================================


class TestMemoryConfigIntegration:
    """Integration tests combining multiple functions."""

    def test_full_detection_and_calculation_workflow(self):
        """Test complete workflow from detection to calculation."""
        mock_meminfo = "MemTotal:       65536000 kB\n"  # 64 GB

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=mock_meminfo):
                from amplihack.launcher.memory_config import (
                    detect_system_ram_gb,
                    calculate_recommended_limit
                )

                ram_gb = detect_system_ram_gb()
                limit_mb = calculate_recommended_limit(ram_gb)

                assert ram_gb == 64
                assert limit_mb == 16384  # 64 GB / 4

    def test_parse_and_merge_workflow(self):
        """Test parsing existing options and merging new limit."""
        from amplihack.launcher.memory_config import (
            parse_node_options,
            merge_node_options
        )

        original = "--max-old-space-size=4096 --no-warnings"
        parsed = parse_node_options(original)
        merged = merge_node_options(parsed, 16384)

        assert "--max-old-space-size=16384" in merged
        assert "--no-warnings" in merged

    def test_detection_calculation_warning_workflow(self):
        """Test workflow with warning for insufficient memory."""
        mock_meminfo = "MemTotal:       8192000 kB\n"  # 8 GB

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=mock_meminfo):
                from amplihack.launcher.memory_config import (
                    detect_system_ram_gb,
                    calculate_recommended_limit,
                    should_warn_about_limit
                )

                ram_gb = detect_system_ram_gb()
                limit_mb = calculate_recommended_limit(ram_gb)
                needs_warning = should_warn_about_limit(limit_mb)

                assert ram_gb == 8
                assert limit_mb == 8192  # max(8192, 2048) = 8192
                assert needs_warning is False

    def test_environment_variable_update_workflow(self):
        """Test updating environment variable with new limit."""
        from amplihack.launcher.memory_config import (
            parse_node_options,
            merge_node_options
        )

        # Simulate existing environment
        existing = os.environ.get("NODE_OPTIONS", "")
        parsed = parse_node_options(existing)
        new_options = merge_node_options(parsed, 8192)

        # Verify format is valid for environment variable
        assert isinstance(new_options, str)
        assert new_options.startswith("--")


# =============================================================================
# E2E TESTS (10%)
# =============================================================================


class TestGetMemoryConfigE2E:
    """End-to-end tests for main entry point."""

    def test_get_memory_config_normal_system(self):
        """Test complete flow on normal system (16+ GB)."""
        mock_meminfo = "MemTotal:       32768000 kB\n"  # 32 GB

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=mock_meminfo):
                with patch("builtins.input", return_value="y"):
                    from amplihack.launcher.memory_config import get_memory_config

                    config = get_memory_config()

                    assert config is not None
                    assert "system_ram_gb" in config
                    assert "recommended_limit_mb" in config
                    assert "node_options" in config
                    assert config["system_ram_gb"] == 32
                    assert config["recommended_limit_mb"] == 8192

    def test_get_memory_config_with_existing_node_options(self):
        """Test complete flow with existing NODE_OPTIONS."""
        mock_meminfo = "MemTotal:       65536000 kB\n"  # 64 GB

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=mock_meminfo):
                with patch.dict(os.environ, {"NODE_OPTIONS": "--no-warnings"}):
                    with patch("builtins.input", return_value="y"):
                        from amplihack.launcher.memory_config import get_memory_config

                        config = get_memory_config()

                        assert "--max-old-space-size=16384" in config["node_options"]
                        assert "--no-warnings" in config["node_options"]

    def test_get_memory_config_user_declines(self):
        """Test complete flow when user declines update."""
        mock_meminfo = "MemTotal:       32768000 kB\n"  # 32 GB

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=mock_meminfo):
                with patch("sys.stdin.isatty", return_value=True):
                    with patch("builtins.input", return_value="n"):
                        from amplihack.launcher.memory_config import get_memory_config

                        config = get_memory_config()

                        # Should return config but indicate user declined
                        assert config is not None
                        assert config.get("user_consent") is False

    def test_get_memory_config_insufficient_memory_warning(self):
        """Test complete flow with insufficient memory warning."""
        mock_meminfo = "MemTotal:       4096000 kB\n"  # 4 GB

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value=mock_meminfo):
                from amplihack.launcher.memory_config import get_memory_config

                config = get_memory_config()

                # Should still provide config with warning
                assert config is not None
                assert config["recommended_limit_mb"] == 8192  # minimum
                assert config.get("warning") is not None

    def test_get_memory_config_detection_failure(self):
        """Test complete flow when RAM detection fails."""
        with patch("pathlib.Path.exists", return_value=False):
            with patch("subprocess.run", side_effect=Exception("Detection failed")):
                from amplihack.launcher.memory_config import get_memory_config

                config = get_memory_config()

                # Should handle gracefully with fallback or error
                assert config is None or "error" in config


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_maximum_possible_ram(self):
        """Test with extremely large RAM (1TB+)."""
        from amplihack.launcher.memory_config import calculate_recommended_limit

        # 1 TB system
        limit_mb = calculate_recommended_limit(1024)
        assert limit_mb == 32768  # Capped at 32 GB

    def test_very_small_ram(self):
        """Test with very small RAM (< 4GB)."""
        from amplihack.launcher.memory_config import calculate_recommended_limit

        limit_mb = calculate_recommended_limit(2)
        assert limit_mb == 8192  # Still minimum 8 GB

    def test_fractional_ram_values(self):
        """Test with fractional GB values."""
        from amplihack.launcher.memory_config import calculate_recommended_limit

        # Should handle or round appropriately
        limit_mb = calculate_recommended_limit(15.5)
        assert limit_mb >= 8192

    def test_node_options_with_quotes(self):
        """Test parsing NODE_OPTIONS with quoted values."""
        from amplihack.launcher.memory_config import parse_node_options

        options = '--max-old-space-size=4096 --require="./setup.js"'
        result = parse_node_options(options)

        # Should handle quoted values correctly
        assert result["max-old-space-size"] == 4096

    def test_concurrent_modifications_to_node_options(self):
        """Test handling of concurrent NODE_OPTIONS modifications."""
        from amplihack.launcher.memory_config import (
            parse_node_options,
            merge_node_options
        )

        # Simulate race condition scenario
        original = "--max-old-space-size=4096"
        parsed1 = parse_node_options(original)
        parsed2 = parse_node_options(original)

        merged1 = merge_node_options(parsed1, 8192)
        merged2 = merge_node_options(parsed2, 16384)

        # Both should be valid independently
        assert "--max-old-space-size" in merged1
        assert "--max-old-space-size" in merged2


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


class TestErrorHandling:
    """Test error handling and recovery."""

    def test_invalid_ram_gb_input(self):
        """Test handling of invalid RAM GB values."""
        from amplihack.launcher.memory_config import calculate_recommended_limit

        # Should handle gracefully or raise appropriate error
        with pytest.raises((ValueError, TypeError)):
            calculate_recommended_limit(-1)

        with pytest.raises((ValueError, TypeError)):
            calculate_recommended_limit("invalid")

    def test_parse_malformed_node_options(self):
        """Test parsing completely malformed NODE_OPTIONS."""
        from amplihack.launcher.memory_config import parse_node_options

        malformed = "not--a=valid format at all"
        # Should return empty dict or raise clear error
        result = parse_node_options(malformed)
        assert isinstance(result, dict)

    def test_permission_denied_reading_meminfo(self):
        """Test handling when /proc/meminfo cannot be read."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", side_effect=PermissionError()):
                from amplihack.launcher.memory_config import detect_system_ram_gb

                # Should fallback to alternative method or return None
                ram_gb = detect_system_ram_gb()
                assert ram_gb is None or ram_gb > 0

    def test_subprocess_timeout_on_detection(self):
        """Test handling of subprocess timeout during detection."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 5)):
            from amplihack.launcher.memory_config import detect_system_ram_gb

            # Should handle timeout gracefully
            ram_gb = detect_system_ram_gb()
            assert ram_gb is None or ram_gb > 0


# =============================================================================
# PLATFORM-SPECIFIC TESTS
# =============================================================================


class TestPlatformSpecifics:
    """Test platform-specific behaviors."""

    def test_linux_meminfo_parsing_variants(self):
        """Test parsing different /proc/meminfo formats."""
        test_cases = [
            "MemTotal:       16384000 kB",
            "MemTotal:  16384000 kB",
            "MemTotal:\t16384000 kB",
        ]

        for meminfo in test_cases:
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.read_text", return_value=meminfo):
                    from amplihack.launcher.memory_config import detect_system_ram_gb

                    ram_gb = detect_system_ram_gb()
                    assert ram_gb == 16

    def test_macos_sysctl_bytes_parsing(self):
        """Test macOS sysctl output parsing."""
        from amplihack.launcher.memory_config import detect_system_ram_gb

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "17179869184"  # 16 GB in bytes

        with patch("platform.system", return_value="Darwin"):
            with patch("subprocess.run", return_value=mock_result):
                ram_gb = detect_system_ram_gb()
                assert ram_gb == 16

    def test_windows_wmic_output_parsing(self):
        """Test Windows wmic output parsing."""
        from amplihack.launcher.memory_config import detect_system_ram_gb

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "TotalPhysicalMemory  \n17179869184  \n"

        with patch("platform.system", return_value="Windows"):
            with patch("subprocess.run", return_value=mock_result):
                ram_gb = detect_system_ram_gb()
                assert ram_gb == 16


# =============================================================================
# FORMULA VERIFICATION TESTS
# =============================================================================


class TestFormulaCorrectness:
    """Verify the formula N = max(8192, total_ram_mb // 4) capped at 32GB."""

    def test_formula_minimum_enforcement(self):
        """Verify formula enforces 8GB minimum."""
        from amplihack.launcher.memory_config import calculate_recommended_limit

        # Systems where 1/4 RAM < 8GB should get 8GB
        test_cases = [
            (4, 8192),   # 4GB / 4 = 1GB → 8GB minimum
            (8, 8192),   # 8GB / 4 = 2GB → 8GB minimum
            (16, 8192),  # 16GB / 4 = 4GB → 8GB minimum
            (31, 8192),  # 31GB / 4 = 7.75GB → 8GB minimum
        ]

        for ram_gb, expected_mb in test_cases:
            actual_mb = calculate_recommended_limit(ram_gb)
            assert actual_mb == expected_mb, \
                f"RAM {ram_gb}GB should yield {expected_mb}MB, got {actual_mb}MB"

    def test_formula_quarter_calculation(self):
        """Verify formula correctly calculates 1/4 of RAM."""
        from amplihack.launcher.memory_config import calculate_recommended_limit

        # Systems where 1/4 RAM > 8GB and < 32GB
        test_cases = [
            (64, 16384),   # 64GB / 4 = 16GB
            (96, 24576),   # 96GB / 4 = 24GB
            (120, 30720),  # 120GB / 4 = 30GB
        ]

        for ram_gb, expected_mb in test_cases:
            actual_mb = calculate_recommended_limit(ram_gb)
            assert actual_mb == expected_mb, \
                f"RAM {ram_gb}GB should yield {expected_mb}MB, got {actual_mb}MB"

    def test_formula_maximum_cap(self):
        """Verify formula caps at 32GB."""
        from amplihack.launcher.memory_config import calculate_recommended_limit

        # Systems where 1/4 RAM > 32GB should be capped
        test_cases = [
            (128, 32768),  # 128GB / 4 = 32GB (exactly at cap)
            (256, 32768),  # 256GB / 4 = 64GB → 32GB cap
            (512, 32768),  # 512GB / 4 = 128GB → 32GB cap
            (1024, 32768), # 1TB / 4 = 256GB → 32GB cap
        ]

        for ram_gb, expected_mb in test_cases:
            actual_mb = calculate_recommended_limit(ram_gb)
            assert actual_mb == expected_mb, \
                f"RAM {ram_gb}GB should be capped at {expected_mb}MB, got {actual_mb}MB"

    def test_formula_exact_boundaries(self):
        """Test formula at exact boundary conditions."""
        from amplihack.launcher.memory_config import calculate_recommended_limit

        # Boundary: 32GB RAM → exactly 8GB limit (32 * 1024 / 4 = 8192)
        assert calculate_recommended_limit(32) == 8192

        # Boundary: 128GB RAM → exactly 32GB limit
        assert calculate_recommended_limit(128) == 32768

        # Just above minimum boundary: 33GB → 8.25GB → 8448MB
        assert calculate_recommended_limit(33) == 8448

        # Just below cap boundary: 127GB → 31.75GB → 32512MB
        assert calculate_recommended_limit(127) == 32512


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
