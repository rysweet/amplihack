"""Integration tests for quality module."""

from pathlib import Path

import pytest

from amplihack.quality import QualityChecker, QualityConfig


@pytest.mark.integration
class TestQualityIntegration:
    """Integration tests for quality checking."""

    def test_end_to_end_json_validation(self, tmp_path):
        """Test end-to-end JSON validation."""
        # Create test file
        json_file = tmp_path / "test.json"
        json_file.write_text('{"valid": true}')

        # Create checker and validate
        checker = QualityChecker()
        result = checker.check_file(json_file)

        assert result is not None
        assert result.passed is True
        assert result.validator == "json"

    def test_end_to_end_invalid_json(self, tmp_path):
        """Test end-to-end invalid JSON detection."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text('{"invalid": }')

        checker = QualityChecker()
        result = checker.check_file(json_file)

        assert result is not None
        assert result.passed is False
        assert len(result.issues) > 0
        assert result.error_count > 0

    def test_batch_validation(self, tmp_path):
        """Test validating multiple files."""
        files = []
        for i in range(5):
            json_file = tmp_path / f"test{i}.json"
            json_file.write_text(f'{{"file": {i}}}')
            files.append(json_file)

        checker = QualityChecker()
        results = checker.check_files(files)

        assert len(results) == 5
        assert all(r.passed for r in results)

    def test_mixed_file_types(self, tmp_path):
        """Test validating mixed file types."""
        # Create different file types
        json_file = tmp_path / "test.json"
        json_file.write_text('{"type": "json"}')

        py_file = tmp_path / "test.py"
        py_file.write_text('print("hello")')

        checker = QualityChecker()
        results = checker.check_files([json_file, py_file])

        # At minimum, JSON should be validated
        assert len(results) >= 1
        json_results = [r for r in results if r.validator == "json"]
        assert len(json_results) == 1
        assert json_results[0].passed is True

    def test_exclusion_patterns(self, tmp_path):
        """Test that exclusion patterns work."""
        # Create file in excluded directory
        pycache = tmp_path / "__pycache__"
        pycache.mkdir()
        excluded_file = pycache / "test.json"
        excluded_file.write_text('{"excluded": true}')

        checker = QualityChecker()
        result = checker.check_file(excluded_file)

        assert result is None  # Should be excluded

    def test_config_override(self, tmp_path):
        """Test configuration overrides."""
        config = QualityConfig(
            validators=["json"],
            fast_mode_timeout=2
        )

        json_file = tmp_path / "test.json"
        json_file.write_text('{"configured": true}')

        checker = QualityChecker(config)
        result = checker.check_file(json_file)

        assert result is not None
        assert result.passed is True
        assert config.timeout == 2

    def test_summary_generation(self, tmp_path):
        """Test summary generation from multiple results."""
        files = []
        for i in range(3):
            json_file = tmp_path / f"valid{i}.json"
            json_file.write_text(f'{{"valid": {i}}}')
            files.append(json_file)

        invalid = tmp_path / "invalid.json"
        invalid.write_text('{"invalid": }')
        files.append(invalid)

        checker = QualityChecker()
        results = checker.check_files(files)
        summary = checker.get_summary(results)

        assert summary["total_files"] == 4
        assert summary["passed"] == 3
        assert summary["failed"] == 1
        assert summary["total_errors"] > 0

    def test_graceful_degradation_missing_tool(self, tmp_path):
        """Test graceful degradation when validator tool is missing."""
        # Python validator may not have ruff available
        py_file = tmp_path / "test.py"
        py_file.write_text('print("test")')

        checker = QualityChecker()
        result = checker.check_file(py_file)

        # Should either validate or skip gracefully
        if result:
            if result.skipped:
                assert result.skip_reason is not None
            else:
                assert isinstance(result.passed, bool)

    @pytest.mark.performance
    def test_fast_mode_performance(self, tmp_path):
        """Test that fast mode completes quickly."""
        import time

        config = QualityConfig(fast_mode=True, fast_mode_timeout=5)
        checker = QualityChecker(config)

        # Create multiple test files
        files = []
        for i in range(10):
            json_file = tmp_path / f"test{i}.json"
            json_file.write_text(f'{{"file": {i}}}')
            files.append(json_file)

        start = time.time()
        results = checker.check_files(files)
        duration = time.time() - start

        # Should complete in less than 5 seconds for 10 small files
        assert duration < 5.0
        assert len(results) == 10
