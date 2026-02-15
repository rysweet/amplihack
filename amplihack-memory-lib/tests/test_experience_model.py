"""
Unit tests for Experience dataclass - Model validation and behavior.

All tests are written to FAIL initially (TDD approach).
"""

from datetime import datetime

import pytest
from amplihack_memory import Experience, ExperienceType


class TestExperienceCreation:
    """Test Experience dataclass creation and validation."""

    def test_creates_experience_with_required_fields(self):
        """Experience can be created with all required fields."""
        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Test context",
            outcome="Test outcome",
            confidence=0.85,
            timestamp=datetime.now(),
        )

        assert exp.experience_type == ExperienceType.SUCCESS
        assert exp.context == "Test context"
        assert exp.outcome == "Test outcome"
        assert exp.confidence == 0.85
        assert isinstance(exp.timestamp, datetime)

    def test_generates_unique_experience_id(self):
        """Experience generates unique ID automatically."""
        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Test",
            outcome="Result",
            confidence=0.8,
            timestamp=datetime.now(),
        )

        assert exp.experience_id is not None
        assert exp.experience_id.startswith("exp_")

    def test_experience_id_format_is_correct(self):
        """Experience ID follows format: exp_YYYYMMDD_HHMMSS_hash."""
        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Test",
            outcome="Result",
            confidence=0.8,
            timestamp=datetime.now(),
        )

        parts = exp.experience_id.split("_")
        assert len(parts) == 4
        assert parts[0] == "exp"
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 6  # HHMMSS
        assert len(parts[3]) == 6  # hash

    def test_defaults_timestamp_to_now(self):
        """Experience defaults timestamp to current time if not provided."""
        before = datetime.now()
        exp = Experience(
            experience_type=ExperienceType.SUCCESS, context="Test", outcome="Result", confidence=0.8
        )
        after = datetime.now()

        assert before <= exp.timestamp <= after

    def test_defaults_metadata_to_empty_dict(self):
        """Experience defaults metadata to empty dict."""
        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Test",
            outcome="Result",
            confidence=0.8,
            timestamp=datetime.now(),
        )

        assert exp.metadata == {}

    def test_defaults_tags_to_empty_list(self):
        """Experience defaults tags to empty list."""
        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Test",
            outcome="Result",
            confidence=0.8,
            timestamp=datetime.now(),
        )

        assert exp.tags == []

    def test_accepts_metadata_dict(self):
        """Experience accepts custom metadata dict."""
        metadata = {"runtime_ms": 1250, "files_processed": 47, "issues_found": 5}

        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Test",
            outcome="Result",
            confidence=0.8,
            timestamp=datetime.now(),
            metadata=metadata,
        )

        assert exp.metadata == metadata
        assert exp.metadata["runtime_ms"] == 1250

    def test_accepts_tags_list(self):
        """Experience accepts custom tags list."""
        tags = ["documentation", "quality", "critical"]

        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Test",
            outcome="Result",
            confidence=0.8,
            timestamp=datetime.now(),
            tags=tags,
        )

        assert exp.tags == tags
        assert "documentation" in exp.tags


class TestExperienceValidation:
    """Test Experience field validation."""

    def test_validates_context_not_empty(self):
        """Experience raises ValueError if context is empty."""
        with pytest.raises(ValueError):
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="",
                outcome="Result",
                confidence=0.8,
                timestamp=datetime.now(),
            )

    def test_validates_context_max_length(self):
        """Experience raises ValueError if context exceeds 500 chars."""
        with pytest.raises(ValueError):
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="X" * 501,  # Too long
                outcome="Result",
                confidence=0.8,
                timestamp=datetime.now(),
            )

    def test_validates_outcome_not_empty(self):
        """Experience raises ValueError if outcome is empty."""
        with pytest.raises(ValueError):
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Test",
                outcome="",
                confidence=0.8,
                timestamp=datetime.now(),
            )

    def test_validates_outcome_max_length(self):
        """Experience raises ValueError if outcome exceeds 1000 chars."""
        with pytest.raises(ValueError):
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Test",
                outcome="Y" * 1001,  # Too long
                confidence=0.8,
                timestamp=datetime.now(),
            )

    def test_validates_confidence_range_min(self):
        """Experience raises ValueError if confidence < 0.0."""
        with pytest.raises(ValueError):
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Test",
                outcome="Result",
                confidence=-0.1,
                timestamp=datetime.now(),
            )

    def test_validates_confidence_range_max(self):
        """Experience raises ValueError if confidence > 1.0."""
        with pytest.raises(ValueError):
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Test",
                outcome="Result",
                confidence=1.1,
                timestamp=datetime.now(),
            )

    def test_validates_experience_type_is_enum(self):
        """Experience raises TypeError if experience_type is not ExperienceType enum."""
        with pytest.raises(TypeError):
            Experience(
                experience_type="success",  # String instead of enum
                context="Test",
                outcome="Result",
                confidence=0.8,
                timestamp=datetime.now(),
            )

    def test_validates_timestamp_is_datetime(self):
        """Experience raises TypeError if timestamp is not datetime."""
        with pytest.raises(TypeError):
            Experience(
                experience_type=ExperienceType.SUCCESS,
                context="Test",
                outcome="Result",
                confidence=0.8,
                timestamp="2026-02-14",  # String instead of datetime
            )


class TestExperienceEquality:
    """Test Experience equality and comparison."""

    def test_experiences_equal_by_id(self):
        """Two experiences with same ID are equal."""
        exp1 = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Test",
            outcome="Result",
            confidence=0.8,
            timestamp=datetime.now(),
        )

        exp2 = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Different context",
            outcome="Different result",
            confidence=0.9,
            timestamp=datetime.now(),
        )

        # Manually set same ID
        exp2.experience_id = exp1.experience_id

        assert exp1 == exp2

    def test_experiences_not_equal_different_ids(self):
        """Two experiences with different IDs are not equal."""
        exp1 = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Test",
            outcome="Result",
            confidence=0.8,
            timestamp=datetime.now(),
        )

        exp2 = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Test",
            outcome="Result",
            confidence=0.8,
            timestamp=datetime.now(),
        )

        assert exp1 != exp2


class TestExperienceSerialization:
    """Test Experience serialization and deserialization."""

    def test_converts_to_dict(self):
        """Experience can be converted to dictionary."""
        timestamp = datetime.now()
        exp = Experience(
            experience_type=ExperienceType.PATTERN,
            context="Test pattern",
            outcome="Pattern found",
            confidence=0.92,
            timestamp=timestamp,
            metadata={"count": 5},
            tags=["pattern", "important"],
        )

        exp_dict = exp.to_dict()

        assert exp_dict["experience_type"] == "pattern"
        assert exp_dict["context"] == "Test pattern"
        assert exp_dict["outcome"] == "Pattern found"
        assert exp_dict["confidence"] == 0.92
        assert exp_dict["metadata"] == {"count": 5}
        assert exp_dict["tags"] == ["pattern", "important"]

    def test_creates_from_dict(self):
        """Experience can be created from dictionary."""
        exp_dict = {
            "experience_id": "exp_20260214_102315_a7f3c9",
            "experience_type": "success",
            "context": "Test context",
            "outcome": "Test outcome",
            "confidence": 0.85,
            "timestamp": datetime.now().isoformat(),
            "metadata": {"key": "value"},
            "tags": ["tag1", "tag2"],
        }

        exp = Experience.from_dict(exp_dict)

        assert exp.experience_id == "exp_20260214_102315_a7f3c9"
        assert exp.experience_type == ExperienceType.SUCCESS
        assert exp.context == "Test context"
        assert exp.outcome == "Test outcome"
        assert exp.confidence == 0.85
        assert exp.metadata == {"key": "value"}
        assert exp.tags == ["tag1", "tag2"]

    def test_roundtrip_serialization(self):
        """Experience survives to_dict() -> from_dict() roundtrip."""
        original = Experience(
            experience_type=ExperienceType.INSIGHT,
            context="Original context",
            outcome="Original outcome",
            confidence=0.88,
            timestamp=datetime.now(),
            metadata={"data": "value"},
            tags=["test"],
        )

        # Roundtrip
        exp_dict = original.to_dict()
        restored = Experience.from_dict(exp_dict)

        assert restored.experience_id == original.experience_id
        assert restored.experience_type == original.experience_type
        assert restored.context == original.context
        assert restored.outcome == original.outcome
        assert restored.confidence == original.confidence
        assert restored.metadata == original.metadata
        assert restored.tags == original.tags


class TestExperienceType:
    """Test ExperienceType enum."""

    def test_has_success_type(self):
        """ExperienceType has SUCCESS variant."""
        assert ExperienceType.SUCCESS.value == "success"

    def test_has_failure_type(self):
        """ExperienceType has FAILURE variant."""
        assert ExperienceType.FAILURE.value == "failure"

    def test_has_pattern_type(self):
        """ExperienceType has PATTERN variant."""
        assert ExperienceType.PATTERN.value == "pattern"

    def test_has_insight_type(self):
        """ExperienceType has INSIGHT variant."""
        assert ExperienceType.INSIGHT.value == "insight"

    def test_only_has_four_types(self):
        """ExperienceType has exactly four variants."""
        assert len(list(ExperienceType)) == 4

    def test_can_create_from_string(self):
        """ExperienceType can be created from string value."""
        exp_type = ExperienceType("success")
        assert exp_type == ExperienceType.SUCCESS

        exp_type = ExperienceType("pattern")
        assert exp_type == ExperienceType.PATTERN

    def test_raises_on_invalid_string(self):
        """ExperienceType raises ValueError for invalid string."""
        with pytest.raises(ValueError):
            ExperienceType("invalid_type")


class TestExperienceMetadata:
    """Test Experience metadata handling."""

    def test_stores_custom_metrics(self):
        """Experience metadata can store custom metrics."""
        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Test",
            outcome="Result",
            confidence=0.8,
            timestamp=datetime.now(),
            metadata={"runtime_seconds": 45.2, "memory_mb": 128.5, "cpu_percent": 75.0},
        )

        assert exp.metadata["runtime_seconds"] == 45.2
        assert exp.metadata["memory_mb"] == 128.5
        assert exp.metadata["cpu_percent"] == 75.0

    def test_stores_nested_metadata(self):
        """Experience metadata can store nested structures."""
        exp = Experience(
            experience_type=ExperienceType.PATTERN,
            context="Test",
            outcome="Result",
            confidence=0.9,
            timestamp=datetime.now(),
            metadata={
                "pattern": {
                    "type": "documentation_issue",
                    "severity": "high",
                    "occurrences": [
                        {"file": "doc1.md", "line": 42},
                        {"file": "doc2.md", "line": 18},
                    ],
                }
            },
        )

        assert exp.metadata["pattern"]["type"] == "documentation_issue"
        assert len(exp.metadata["pattern"]["occurrences"]) == 2

    def test_metadata_is_mutable(self):
        """Experience metadata can be modified after creation."""
        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Test",
            outcome="Result",
            confidence=0.8,
            timestamp=datetime.now(),
            metadata={"count": 1},
        )

        # Modify metadata
        exp.metadata["count"] = 2
        exp.metadata["new_field"] = "value"

        assert exp.metadata["count"] == 2
        assert exp.metadata["new_field"] == "value"


class TestExperienceTags:
    """Test Experience tags handling."""

    def test_stores_multiple_tags(self):
        """Experience can store multiple tags."""
        exp = Experience(
            experience_type=ExperienceType.PATTERN,
            context="Test",
            outcome="Result",
            confidence=0.9,
            timestamp=datetime.now(),
            tags=["documentation", "quality", "critical", "tutorial"],
        )

        assert len(exp.tags) == 4
        assert "documentation" in exp.tags
        assert "critical" in exp.tags

    def test_tags_are_mutable(self):
        """Experience tags can be modified after creation."""
        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Test",
            outcome="Result",
            confidence=0.8,
            timestamp=datetime.now(),
            tags=["initial"],
        )

        # Modify tags
        exp.tags.append("added")
        exp.tags.remove("initial")

        assert "added" in exp.tags
        assert "initial" not in exp.tags

    def test_duplicate_tags_allowed(self):
        """Experience allows duplicate tags (implementation may de-duplicate)."""
        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Test",
            outcome="Result",
            confidence=0.8,
            timestamp=datetime.now(),
            tags=["tag", "tag", "other"],
        )

        # Implementation may de-duplicate or allow duplicates
        assert "tag" in exp.tags
        assert "other" in exp.tags
