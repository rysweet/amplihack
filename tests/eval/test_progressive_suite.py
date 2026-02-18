"""Tests for progressive test suite infrastructure.

Philosophy: Test the test infrastructure, not the actual evaluation results.
"""

import json

import pytest

from amplihack.eval.test_levels import (
    ALL_LEVELS,
    LEVEL_1,
    LEVEL_2,
    LEVEL_3,
    LEVEL_4,
    LEVEL_5,
    LEVEL_6,
    get_level_by_id,
)


def test_all_levels_defined():
    """Verify all 6 levels are defined."""
    assert len(ALL_LEVELS) == 6
    level_ids = [lvl.level_id for lvl in ALL_LEVELS]
    assert level_ids == ["L1", "L2", "L3", "L4", "L5", "L6"]


def test_level_1_baseline():
    """Verify L1 is properly configured as baseline."""
    assert LEVEL_1.level_id == "L1"
    assert LEVEL_1.level_name == "Single Source Direct Recall"
    assert len(LEVEL_1.articles) == 1
    assert len(LEVEL_1.questions) >= 3
    assert not LEVEL_1.requires_temporal_ordering
    assert not LEVEL_1.requires_update_handling


def test_level_2_multi_source():
    """Verify L2 has multiple sources."""
    assert LEVEL_2.level_id == "L2"
    assert len(LEVEL_2.articles) == 3
    assert len(LEVEL_2.questions) >= 3
    assert not LEVEL_2.requires_temporal_ordering
    assert not LEVEL_2.requires_update_handling


def test_level_3_temporal():
    """Verify L3 is configured for temporal reasoning."""
    assert LEVEL_3.level_id == "L3"
    assert len(LEVEL_3.articles) == 3
    assert LEVEL_3.requires_temporal_ordering
    assert not LEVEL_3.requires_update_handling

    # Verify articles have day metadata
    for article in LEVEL_3.articles:
        assert article.metadata is not None
        assert "day" in article.metadata


def test_level_4_procedural():
    """Verify L4 has procedural content."""
    assert LEVEL_4.level_id == "L4"
    assert len(LEVEL_4.articles) >= 1
    assert len(LEVEL_4.questions) >= 4

    # Verify content mentions steps/procedures
    content = LEVEL_4.articles[0].content
    assert "Step" in content or "step" in content


def test_level_5_contradictions():
    """Verify L5 has conflicting sources."""
    assert LEVEL_5.level_id == "L5"
    assert len(LEVEL_5.articles) == 2
    assert len(LEVEL_5.questions) >= 3

    # Verify different viewership numbers in content
    content_a = LEVEL_5.articles[0].content
    content_b = LEVEL_5.articles[1].content
    assert "1.2 billion" in content_a or "1.2B" in content_a
    assert "800 million" in content_b or "800M" in content_b


def test_level_6_incremental():
    """Verify L6 is configured for incremental learning."""
    assert LEVEL_6.level_id == "L6"
    assert LEVEL_6.requires_update_handling
    assert len(LEVEL_6.articles) == 2

    # Verify articles have phase metadata
    phases = [a.metadata.get("phase") for a in LEVEL_6.articles]
    assert "initial" in phases
    assert "update" in phases


def test_get_level_by_id():
    """Test level retrieval by ID."""
    level = get_level_by_id("L1")
    assert level is not None
    assert level.level_id == "L1"

    level = get_level_by_id("L6")
    assert level is not None
    assert level.level_id == "L6"

    level = get_level_by_id("L99")
    assert level is None


def test_all_questions_have_required_fields():
    """Verify all questions have required fields."""
    for level in ALL_LEVELS:
        for question in level.questions:
            assert question.question
            assert question.expected_answer
            assert question.level
            assert question.reasoning_type


def test_all_articles_have_required_fields():
    """Verify all articles have required fields."""
    for level in ALL_LEVELS:
        for article in level.articles:
            assert article.title
            assert article.content
            assert article.url
            assert article.published


def test_february_2026_content():
    """Verify most content is from February 2026 (not in training data)."""
    # Check that content mentions 2026 (except L4 which is timeless procedural)
    for level in ALL_LEVELS:
        if level.level_id == "L4":
            # L4 is procedural content, timeless by design
            continue
        for article in level.articles:
            # Either title, content, or published date should mention 2026/Feb
            combined = article.title + article.content + article.published
            assert "2026" in combined or "Feb" in combined or "February" in combined


def test_level_descriptions():
    """Verify all levels have descriptions."""
    for level in ALL_LEVELS:
        assert level.description
        assert len(level.description) > 10


def test_reasoning_types():
    """Verify reasoning types are properly categorized."""
    expected_reasoning_types = {
        "L1": ["direct_recall"],
        "L2": ["cross_source_synthesis"],
        "L3": ["temporal_difference", "temporal_comparison", "temporal_trend"],
        "L4": ["procedural_recall", "procedural_troubleshooting", "procedural_sequence", "procedural_application"],
        "L5": ["contradiction_detection", "contradiction_reasoning", "source_credibility"],
        "L6": ["incremental_update", "incremental_tracking", "incremental_synthesis"]
    }

    for level in ALL_LEVELS:
        reasoning_types = [q.reasoning_type for q in level.questions]
        # At least one question should use an expected reasoning type for this level
        assert any(rt in expected_reasoning_types[level.level_id] for rt in reasoning_types)


def test_urls_are_unique():
    """Verify article URLs are unique within each level."""
    for level in ALL_LEVELS:
        urls = [a.url for a in level.articles]
        assert len(urls) == len(set(urls)), f"Duplicate URLs in {level.level_id}"


def test_published_dates_are_valid():
    """Verify published dates are in ISO format."""
    for level in ALL_LEVELS:
        for article in level.articles:
            # Check ISO 8601 format (basic validation)
            assert "T" in article.published
            assert "Z" in article.published or "+" in article.published or "-" in article.published[-6:]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
