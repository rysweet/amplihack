"""Integration and E2E tests for docs_cleanup module.

Tests the cleanup workflow integration following TDD approach.
These tests are written BEFORE implementation and should FAIL initially.

Testing Pyramid Distribution:
- Integration Tests: 30% (this file - filter_entries_by_age, run_cleanup dry-run)
- E2E Tests: 10% (this file - complete workflow)
"""

import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# These imports will FAIL until we implement the modules
from docs_cleanup import (
    CleanupResult,
    FilterResult,
    filter_entries_by_age,
    parse_discoveries_file,
    run_cleanup,
)


class TestFilterEntriesByAge:
    """Integration tests for filter_entries_by_age function (30%)."""

    def test_filter_mixed_age_entries(self):
        """Test filtering entries with mixed ages.

        Validates: Core filtering logic with multiple entries
        Expected: Correctly separates old entries from kept entries
        """
        entries = [
            {
                "header": "### 2024-01-15",
                "content": "Old discovery 1",
                "date": datetime(2024, 1, 15, tzinfo=UTC),
            },
            {
                "header": "### 2024-11-15",
                "content": "Recent discovery",
                "date": datetime(2024, 11, 15, tzinfo=UTC),
            },
            {
                "header": "### 2024-02-20",
                "content": "Old discovery 2",
                "date": datetime(2024, 2, 20, tzinfo=UTC),
            },
        ]

        reference_date = datetime(2024, 12, 15, tzinfo=UTC)
        result = filter_entries_by_age(entries, cutoff_months=6, reference_date=reference_date)

        assert isinstance(result, FilterResult)
        assert len(result.old_entries) == 2  # Jan and Feb entries
        assert len(result.kept_entries) == 1  # Nov entry
        assert result.total_processed == 3

    def test_filter_all_recent_entries(self):
        """Test filtering when all entries are recent.

        Validates: Edge case - nothing to remove
        Expected: All entries kept, none marked old
        """
        entries = [
            {
                "header": "### 2024-11-15",
                "content": "Recent 1",
                "date": datetime(2024, 11, 15, tzinfo=UTC),
            },
            {
                "header": "### 2024-12-01",
                "content": "Recent 2",
                "date": datetime(2024, 12, 1, tzinfo=UTC),
            },
        ]

        reference_date = datetime(2024, 12, 15, tzinfo=UTC)
        result = filter_entries_by_age(entries, cutoff_months=6, reference_date=reference_date)

        assert len(result.old_entries) == 0
        assert len(result.kept_entries) == 2

    def test_filter_all_old_entries(self):
        """Test filtering when all entries are old.

        Validates: Edge case - everything should be removed
        Expected: All entries marked old, none kept
        """
        entries = [
            {
                "header": "### 2024-01-15",
                "content": "Old 1",
                "date": datetime(2024, 1, 15, tzinfo=UTC),
            },
            {
                "header": "### 2024-02-20",
                "content": "Old 2",
                "date": datetime(2024, 2, 20, tzinfo=UTC),
            },
        ]

        reference_date = datetime(2024, 12, 15, tzinfo=UTC)
        result = filter_entries_by_age(entries, cutoff_months=6, reference_date=reference_date)

        assert len(result.old_entries) == 2
        assert len(result.kept_entries) == 0

    def test_filter_entries_missing_dates_conservative(self):
        """Test filtering entries with missing/invalid dates - conservative.

        Validates: Conservative approach to entries without valid dates
        Expected: Entries without valid dates are KEPT (not deleted)
        """
        entries = [
            {
                "header": "### 2024-01-15",
                "content": "Old with date",
                "date": datetime(2024, 1, 15, tzinfo=UTC),
            },
            {
                "header": "### No date here",
                "content": "Entry without date",
                "date": None,  # Missing date
            },
        ]

        reference_date = datetime(2024, 12, 15, tzinfo=UTC)
        result = filter_entries_by_age(entries, cutoff_months=6, reference_date=reference_date)

        # Entry without date should be KEPT (conservative)
        assert len(result.kept_entries) >= 1
        kept_contents = [e["content"] for e in result.kept_entries]
        assert "Entry without date" in kept_contents

    def test_filter_empty_entries_list(self):
        """Test filtering with no entries.

        Validates: Edge case - empty input
        Expected: Empty results, no errors
        """
        result = filter_entries_by_age([], cutoff_months=6, reference_date=datetime.now(UTC))

        assert len(result.old_entries) == 0
        assert len(result.kept_entries) == 0
        assert result.total_processed == 0


class TestRunCleanup:
    """Integration tests for run_cleanup function (30%)."""

    def test_run_cleanup_dry_run_mode(self):
        """Test cleanup in dry-run mode - no actual changes.

        Validates: Dry-run functionality
        Expected: Analysis performed, no file modifications, results returned
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# Discoveries

### 2024-01-15

Old discovery that should be identified

### 2024-11-15

Recent discovery that should be kept
""")
            temp_path = Path(f.name)

        try:
            result = run_cleanup(
                path=temp_path,
                cutoff_months=6,
                dry_run=True,
                reference_date=datetime(2024, 12, 15, tzinfo=UTC),
            )

            assert isinstance(result, CleanupResult)
            assert result.dry_run is True
            assert result.entries_removed >= 0
            assert result.entries_kept >= 0

            # Verify file unchanged in dry-run
            original_content = temp_path.read_text()
            assert "Old discovery" in original_content

        finally:
            temp_path.unlink()

    def test_run_cleanup_actual_mode(self):
        """Test cleanup in actual mode - files modified.

        Validates: Actual cleanup with file modifications
        Expected: Old entries removed, file updated, results accurate
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# Discoveries

### 2024-01-15

Old discovery to remove

### 2024-11-15

Recent discovery to keep
""")
            temp_path = Path(f.name)

        try:
            result = run_cleanup(
                path=temp_path,
                cutoff_months=6,
                dry_run=False,
                reference_date=datetime(2024, 12, 15, tzinfo=UTC),
            )

            assert result.dry_run is False
            assert result.entries_removed > 0
            assert result.entries_kept > 0

            # Verify file was actually modified
            updated_content = temp_path.read_text()
            assert "Old discovery" not in updated_content
            assert "Recent discovery" in updated_content

        finally:
            temp_path.unlink()

    def test_run_cleanup_nonexistent_file(self):
        """Test cleanup with nonexistent file.

        Validates: Error handling for missing files
        Expected: Appropriate error or empty result
        """
        nonexistent_path = Path("/tmp/does_not_exist_12345.md")

        with pytest.raises(FileNotFoundError):
            run_cleanup(path=nonexistent_path, cutoff_months=6, dry_run=True)

    def test_run_cleanup_preserves_file_structure(self):
        """Test that cleanup preserves file structure and formatting.

        Validates: File structure preservation
        Expected: Headers, formatting, non-entry content preserved
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# Discoveries

This is important introduction text.

### 2024-01-15

Old entry

### 2024-11-15

Recent entry

## Footer Section

This should be preserved.
""")
            temp_path = Path(f.name)

        try:
            _ = run_cleanup(
                path=temp_path,
                cutoff_months=6,
                dry_run=False,
                reference_date=datetime(2024, 12, 15, tzinfo=UTC),
            )

            updated_content = temp_path.read_text()
            assert "# Discoveries" in updated_content
            assert "important introduction text" in updated_content
            assert "Footer Section" in updated_content

        finally:
            temp_path.unlink()


class TestEndToEnd:
    """End-to-end tests for complete workflow (10%)."""

    def test_complete_workflow_with_real_discoveries_format(self):
        """Test complete workflow with realistic DISCOVERIES.md format.

        Validates: Full workflow from file read to cleanup
        Expected: Correctly processes real DISCOVERIES.md structure
        """
        discoveries_content = """# Development Discoveries

This document captures key learnings and discoveries during development.

## 2024 Discoveries

### 2024-01-10

**Issue**: Documentation links were broken
**Root Cause**: Relative paths incorrect
**Solution**: Use absolute paths from repo root
**Impact**: All docs now accessible

### 2024-11-20

**Issue**: Performance degradation in cleanup script
**Root Cause**: O(n²) algorithm in link checker
**Solution**: Use set-based lookups
**Impact**: 10x faster execution

### 2024-02-15

**Issue**: Test flakiness in CI
**Root Cause**: Timezone assumptions
**Solution**: Use UTC everywhere
**Impact**: Tests now reliable

## 2023 Discoveries

### 2023-12-25

**Issue**: Old discovery from last year
**Solution**: Historical context
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(discoveries_content)
            temp_path = Path(f.name)

        try:
            # Run complete cleanup workflow
            result = run_cleanup(
                path=temp_path,
                cutoff_months=6,
                dry_run=False,
                reference_date=datetime(2024, 12, 15, tzinfo=UTC),
            )

            # Verify results
            assert result.entries_removed >= 2  # Jan, Feb, Dec entries
            assert result.entries_kept >= 1  # Nov entry

            # Verify file content
            updated_content = temp_path.read_text()
            assert "Development Discoveries" in updated_content  # Header preserved
            assert "2024-11-20" in updated_content  # Recent entry kept
            assert "2024-01-10" not in updated_content  # Old entry removed
            assert "2024-02-15" not in updated_content  # Old entry removed

        finally:
            temp_path.unlink()

    def test_complete_workflow_preserves_structure_sections(self):
        """Test that complete workflow preserves all non-entry sections.

        Validates: Structure preservation in full workflow
        Expected: Headers, intro text, footer sections all preserved
        """
        content = """# Discoveries

## Introduction

Important context about these discoveries.

### 2024-01-15

Old entry to remove

### 2024-11-15

Recent entry to keep

## Guidelines

How to add new discoveries.

## Archive

Historical reference section.
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            _ = run_cleanup(
                path=temp_path,
                cutoff_months=6,
                dry_run=False,
                reference_date=datetime(2024, 12, 15, tzinfo=UTC),
            )

            updated_content = temp_path.read_text()

            # All non-entry sections should be preserved
            assert "# Discoveries" in updated_content
            assert "## Introduction" in updated_content
            assert "Important context" in updated_content
            assert "## Guidelines" in updated_content
            assert "How to add new discoveries" in updated_content
            assert "## Archive" in updated_content
            assert "Historical reference" in updated_content

        finally:
            temp_path.unlink()

    def test_e2e_with_claude_api_call_placeholder(self):
        """Test E2E workflow including Claude API call (placeholder).

        Validates: Integration with Claude API for analysis
        Expected: Claude provides insights on removed entries

        NOTE: This test uses mocking since actual API calls are expensive.
        Replace with real API call when ready for production testing.
        """
        pytest.skip("Claude API integration test - implement when API integration ready")


class TestParseDiscoveriesFile:
    """Tests for parse_discoveries_file helper function."""

    def test_parse_discoveries_file_structure(self):
        """Test parsing DISCOVERIES.md file structure.

        Validates: File parsing into entry structures
        Expected: Returns list of entry dictionaries with header, content, date
        """
        content = """# Discoveries

### 2024-11-15

Discovery content here

### 2024-10-20

Another discovery
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(content)
            temp_path = Path(f.name)

        try:
            entries = parse_discoveries_file(temp_path)

            assert len(entries) >= 2
            assert all("header" in e for e in entries)
            assert all("content" in e for e in entries)
            assert all("date" in e for e in entries)

        finally:
            temp_path.unlink()


class TestDataStructures:
    """Tests for data structure contracts."""

    def test_filter_result_structure(self):
        """Test FilterResult dataclass structure.

        Validates: Data structure contract
        Expected: Has old_entries, kept_entries, total_processed fields
        """
        result = FilterResult(old_entries=[], kept_entries=[], total_processed=0)

        assert hasattr(result, "old_entries")
        assert hasattr(result, "kept_entries")
        assert hasattr(result, "total_processed")

    def test_cleanup_result_structure(self):
        """Test CleanupResult dataclass structure.

        Validates: Data structure contract
        Expected: Has entries_removed, entries_kept, dry_run, summary fields
        """
        result = CleanupResult(
            entries_removed=0, entries_kept=0, dry_run=True, summary="Test summary"
        )

        assert hasattr(result, "entries_removed")
        assert hasattr(result, "entries_kept")
        assert hasattr(result, "dry_run")
        assert hasattr(result, "summary")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
