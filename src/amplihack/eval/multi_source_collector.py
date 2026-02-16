"""Multi-source news collector.

Transforms WebSearch results into structured news articles.
Philosophy: Simple data transformer, no external API calls.
"""

from dataclasses import dataclass


@dataclass
class NewsArticle:
    """Structured news article from WebSearch."""

    url: str
    title: str
    content: str
    published: str


def collect_news(websearch_data: dict) -> list[NewsArticle]:
    """Collect and structure news from WebSearch results.

    Args:
        websearch_data: WebSearch JSON with "sources" list

    Returns:
        List of structured NewsArticle objects

    Raises:
        ValueError: If required fields are missing
    """
    sources = websearch_data.get("sources", [])

    articles = []
    for source in sources:
        # Validate required fields
        required = ["url", "title", "content", "published"]
        missing = [field for field in required if field not in source]
        if missing:
            raise ValueError(f"Missing required field(s): {', '.join(missing)}")

        article = NewsArticle(
            url=source["url"],
            title=source["title"],
            content=source["content"],
            published=source["published"],
        )
        articles.append(article)

    return articles


__all__ = ["collect_news", "NewsArticle"]
