"""Unit tests for date_parser module.

Tests the date parsing and age checking functionality following TDD approach.
These tests are written BEFORE implementation and should FAIL initially.

Testing Pyramid Distribution:
- Unit Tests: 60% (this file)
- Integration Tests: 30% (test_docs_cleanup.py)
- E2E Tests: 10% (test_docs_cleanup.py)
"""

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

# Add parent directory to path to import date_parser
sys.path.insert(0, str(Path(__file__).parent.parent))

# This import will FAIL until we implement date_parser.py
from date_parser import DateParseResult, is_old_enough, parse_discovery_date


class TestParseDiscoveryDate:
    """Unit tests for parse_discovery_date function (7 scenarios)."""

    def test_parse_valid_iso_date(self):
        """Test parsing a valid ISO 8601 date from header.

        Validates: Happy path with properly formatted date
        Expected: Successfully parsed datetime object with valid=True
        """
        header = "### 2024-06-15 10:30:00"
        result = parse_discovery_date(header)

        assert result.valid is True
        assert result.date is not None
        assert result.date.year == 2024
        assert result.date.month == 6
        assert result.date.day == 15
        assert result.error is None

    def test_parse_valid_iso_date_date_only(self):
        """Test parsing ISO date without time component.

        Validates: Date-only format (no time)
        Expected: Successfully parsed with midnight time
        """
        header = "### 2024-06-15"
        result = parse_discovery_date(header)

        assert result.valid is True
        assert result.date is not None
        assert result.date.year == 2024
        assert result.date.month == 6
        assert result.date.day == 15

    def test_parse_missing_date_conservative(self):
        """Test parsing header with no date - conservative approach.

        Validates: Missing date handling
        Expected: valid=False (conservative - don't delete without date)
        """
        header = "### Some discovery without date"
        result = parse_discovery_date(header)

        assert result.valid is False
        assert result.date is None
        assert "no date" in result.error.lower() or "missing" in result.error.lower()

    def test_parse_malformed_date_conservative(self):
        """Test parsing malformed date - conservative approach.

        Validates: Invalid date format handling
        Expected: valid=False (conservative - don't delete with bad date)
        """
        header = "### 2024-13-45 99:99:99"  # Invalid month and day
        result = parse_discovery_date(header)

        assert result.valid is False
        assert result.date is None
        assert result.error is not None

    def test_parse_future_date_marks_invalid(self):
        """Test parsing future date - should be marked invalid.

        Validates: Future date detection
        Expected: valid=False (discoveries can't be in future)
        """
        future_date = "2099-12-31"
        header = f"### {future_date}"
        result = parse_discovery_date(header)

        assert result.valid is False
        assert "future" in result.error.lower()

    def test_parse_various_header_formats(self):
        """Test parsing dates with various header format variations.

        Validates: Robustness to whitespace and formatting
        Expected: Successfully extracts date regardless of spacing
        """
        test_cases = [
            "###2024-06-15",  # No space after ###
            "### 2024-06-15",  # One space
            "###  2024-06-15",  # Two spaces
            "### 2024-06-15 Some text after",  # Text after date
        ]

        for header in test_cases:
            result = parse_discovery_date(header)
            assert result.valid is True, f"Failed for: {header}"
            assert result.date.year == 2024

    def test_parse_empty_header(self):
        """Test parsing empty or whitespace-only header.

        Validates: Edge case - empty input
        Expected: valid=False with appropriate error
        """
        result = parse_discovery_date("   ")

        assert result.valid is False
        assert result.date is None
        assert result.error is not None


class TestIsOldEnough:
    """Unit tests for is_old_enough function (3 scenarios)."""

    def test_exactly_six_months_old(self):
        """Test entry that is exactly 6 months old.

        Validates: Boundary condition - exactly cutoff age
        Expected: True (6 months >= 6 months cutoff)
        """
        reference_date = datetime(2024, 12, 15, tzinfo=UTC)
        entry_date = datetime(2024, 6, 15, tzinfo=UTC)  # Exactly 6 months

        result = is_old_enough(entry_date, cutoff_months=6, reference_date=reference_date)

        assert result is True

    def test_five_point_nine_months_not_old_enough(self):
        """Test entry that is 5.9 months old (just under cutoff).

        Validates: Boundary condition - just under cutoff
        Expected: False (5.9 months < 6 months cutoff)
        """
        reference_date = datetime(2024, 12, 15, tzinfo=UTC)
        entry_date = datetime(2024, 6, 18, tzinfo=UTC)  # ~5.9 months

        result = is_old_enough(entry_date, cutoff_months=6, reference_date=reference_date)

        assert result is False

    def test_seven_months_old_enough(self):
        """Test entry that is 7 months old (well past cutoff).

        Validates: Happy path - clearly old enough
        Expected: True (7 months > 6 months cutoff)
        """
        reference_date = datetime(2024, 12, 15, tzinfo=UTC)
        entry_date = datetime(2024, 5, 15, tzinfo=UTC)  # 7 months

        result = is_old_enough(entry_date, cutoff_months=6, reference_date=reference_date)

        assert result is True

    def test_one_year_old(self):
        """Test entry that is 1 year old.

        Validates: Well past cutoff
        Expected: True (12 months > 6 months cutoff)
        """
        reference_date = datetime(2024, 12, 15, tzinfo=UTC)
        entry_date = datetime(2023, 12, 15, tzinfo=UTC)  # 12 months

        result = is_old_enough(entry_date, cutoff_months=6, reference_date=reference_date)

        assert result is True

    def test_timezone_aware_dates(self):
        """Test that timezone-aware dates are handled correctly.

        Validates: Timezone handling
        Expected: Correct age calculation regardless of timezone
        """
        reference_date = datetime(2024, 12, 15, 12, 0, tzinfo=UTC)
        entry_date = datetime(2024, 6, 15, 12, 0, tzinfo=UTC)

        result = is_old_enough(entry_date, cutoff_months=6, reference_date=reference_date)

        assert result is True


class TestDateParseResultDataclass:
    """Tests for DateParseResult dataclass structure."""

    def test_date_parse_result_has_required_fields(self):
        """Test that DateParseResult has all required fields.

        Validates: Data structure contract
        Expected: Dataclass with valid, date, error fields
        """
        # This will fail until DateParseResult is implemented
        result = DateParseResult(valid=True, date=datetime.now(), error=None)

        assert hasattr(result, "valid")
        assert hasattr(result, "date")
        assert hasattr(result, "error")

    def test_date_parse_result_invalid_state(self):
        """Test DateParseResult in invalid state.

        Validates: Invalid state representation
        Expected: valid=False, date=None, error message present
        """
        result = DateParseResult(valid=False, date=None, error="Test error")

        assert result.valid is False
        assert result.date is None
        assert result.error == "Test error"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
