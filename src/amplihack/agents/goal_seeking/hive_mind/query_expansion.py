"""Query expansion for improved hive mind retrieval.

Expands user queries into semantically richer variants using an LLM
(Claude Haiku) to improve recall. Falls back to simple synonym-based
expansion when the API is unavailable.

Philosophy:
- Single responsibility: expand queries, search with expanded queries
- Graceful degradation: works without API access via local expansion
- No persistent state: each call is independent

Public API (the "studs"):
    expand_query: Expand a query into multiple search variants
    search_expanded: Search with expanded queries and merge results
    HAS_ANTHROPIC: Feature flag for API availability
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency: anthropic SDK
# ---------------------------------------------------------------------------

from .constants import DEFAULT_EXPANSION_MODEL

try:
    import anthropic  # type: ignore[import-untyped]

    HAS_ANTHROPIC = True
except ImportError:
    anthropic = None  # type: ignore[assignment]
    HAS_ANTHROPIC = False
    logger.warning(
        "anthropic SDK not available; query_expansion will use local synonym fallback. "
        "Install with: pip install anthropic"
    )

# Honour explicit disablement even when the SDK is installed.
if HAS_ANTHROPIC and os.environ.get("ANTHROPIC_DISABLED", "").strip().lower() == "true":
    HAS_ANTHROPIC = False
    logger.warning(
        "Anthropic is disabled (ANTHROPIC_DISABLED=true); "
        "query_expansion will use local synonym fallback."
    )

# Backward-compatible alias
EXPANSION_MODEL = DEFAULT_EXPANSION_MODEL
_MAX_EXPANSIONS = 4


# ---------------------------------------------------------------------------
# Local synonym expansion (fallback)
# ---------------------------------------------------------------------------

# Common synonyms/related terms for query expansion
_SYNONYM_MAP: dict[str, list[str]] = {
    "error": ["exception", "failure", "bug"],
    "fix": ["repair", "resolve", "patch"],
    "performance": ["speed", "latency", "throughput"],
    "memory": ["storage", "cache", "buffer"],
    "test": ["verify", "validate", "check"],
    "deploy": ["release", "ship", "publish"],
    "config": ["configuration", "settings", "parameters"],
    "auth": ["authentication", "authorization", "login"],
    "api": ["endpoint", "interface", "service"],
    "database": ["db", "storage", "datastore"],
}


def _local_expand(query: str) -> list[str]:
    """Expand query using local synonym map.

    Returns the original query plus up to 2 synonym-expanded variants.
    """
    words = query.lower().split()
    expansions = [query]

    for word in words:
        synonyms = _SYNONYM_MAP.get(word, [])
        for syn in synonyms[:2]:
            expanded = query.replace(word, syn)
            if expanded != query and expanded not in expansions:
                expansions.append(expanded)
                if len(expansions) >= _MAX_EXPANSIONS:
                    return expansions

    return expansions


# ---------------------------------------------------------------------------
# LLM-based expansion
# ---------------------------------------------------------------------------


def expand_query(
    query: str,
    max_expansions: int = _MAX_EXPANSIONS,
    api_key: str | None = None,
) -> list[str]:
    """Expand a query into semantically richer search variants.

    Uses Claude Haiku to generate alternative phrasings that capture
    different aspects of the user's intent. Falls back to local
    synonym expansion when the API is unavailable.

    Args:
        query: Original search query.
        max_expansions: Maximum number of expanded queries (including original).
        api_key: Optional Anthropic API key (uses env var if not provided).

    Returns:
        List of query strings, original first, then expansions.
    """
    if not query or not query.strip():
        return [query] if query else []

    query = query.strip()

    if not HAS_ANTHROPIC:
        logger.debug("Anthropic SDK unavailable, using local expansion")
        return _local_expand(query)[:max_expansions]

    try:
        client_kwargs: dict[str, str] = {}
        if api_key:
            client_kwargs["api_key"] = api_key

        client = anthropic.Anthropic(**client_kwargs)
        response = client.messages.create(
            model=EXPANSION_MODEL,
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Generate {max_expansions - 1} alternative search queries "
                        f"for: '{query}'\n\n"
                        "Each should capture a different aspect or phrasing. "
                        "Return ONLY the queries, one per line, no numbering."
                    ),
                }
            ],
        )

        text = response.content[0].text.strip()
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        # Remove any numbering prefixes (e.g., "1. ", "- ")
        lines = [re.sub(r"^[\d]+[.)]\s*", "", line) for line in lines]
        lines = [re.sub(r"^[-*]\s*", "", line) for line in lines]

        expansions = [query] + [line for line in lines if line and line != query]
        return expansions[:max_expansions]

    except Exception:
        logger.debug("LLM expansion failed, falling back to local", exc_info=True)
        return _local_expand(query)[:max_expansions]


# ---------------------------------------------------------------------------
# Search with expanded queries
# ---------------------------------------------------------------------------


def search_expanded(
    query: str,
    search_fn: Any,
    limit: int = 20,
    api_key: str | None = None,
) -> list[Any]:
    """Search with expanded queries and merge results.

    Expands the query, runs search_fn for each variant, and merges
    results by deduplicating on content.

    Args:
        query: Original search query.
        search_fn: Callable(query, limit) -> list[facts]. The search function.
        limit: Maximum total results.
        api_key: Optional Anthropic API key.

    Returns:
        Merged, deduplicated list of facts.
    """
    expanded = expand_query(query, api_key=api_key)

    seen_content: set[str] = set()
    results: list[Any] = []

    for variant in expanded:
        try:
            facts = search_fn(variant, limit=limit)
            for fact in facts:
                content = getattr(fact, "content", str(fact))
                if content not in seen_content:
                    seen_content.add(content)
                    results.append(fact)
        except Exception:
            logger.debug("Search failed for expanded query: %s", variant, exc_info=True)

    return results[:limit]


__all__ = [
    "expand_query",
    "search_expanded",
    "HAS_ANTHROPIC",
    "EXPANSION_MODEL",
]
