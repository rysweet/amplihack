"""Tests for multi-source news collector."""

import pytest

from amplihack.eval.multi_source_collector import NewsArticle, collect_news


def test_collect_news_from_websearch_results():
    """Test collecting structured news from WebSearch JSON."""
    websearch_data = {
        "sources": [
            {
                "url": "https://example.com/article1",
                "title": "AI Breakthrough",
                "content": "Researchers announced new model.",
                "published": "2026-02-16T10:00:00Z",
            },
            {
                "url": "https://example.com/article2",
                "title": "Tech Update",
                "content": "Company releases product.",
                "published": "2026-02-16T11:00:00Z",
            },
        ]
    }

    articles = collect_news(websearch_data)

    assert len(articles) == 2
    assert isinstance(articles[0], NewsArticle)
    assert articles[0].url == "https://example.com/article1"
    assert articles[0].title == "AI Breakthrough"
    assert articles[0].content == "Researchers announced new model."


def test_collect_news_extracts_metadata():
    """Test metadata extraction from articles."""
    websearch_data = {
        "sources": [
            {
                "url": "https://example.com/article",
                "title": "News",
                "content": "Content here.",
                "published": "2026-02-16T10:00:00Z",
            }
        ]
    }

    articles = collect_news(websearch_data)

    assert articles[0].published == "2026-02-16T10:00:00Z"


def test_collect_news_handles_empty_sources():
    """Test handling of empty source list."""
    websearch_data = {"sources": []}

    articles = collect_news(websearch_data)

    assert articles == []


def test_collect_news_validates_required_fields():
    """Test validation of required fields."""
    invalid_data = {"sources": [{"url": "https://example.com"}]}

    with pytest.raises(ValueError, match="Missing required field"):
        collect_news(invalid_data)
