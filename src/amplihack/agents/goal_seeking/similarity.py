"""Text similarity computation for knowledge graph edges.

Philosophy:
- Simple, deterministic similarity (no ML embeddings needed)
- Jaccard coefficient on tokenized words minus stop words
- Tag overlap for categorical similarity
- Weighted composite score for graph edge creation

Public API:
    compute_word_similarity(text_a, text_b) -> float
    compute_tag_similarity(tags_a, tags_b) -> float
    compute_similarity(node_a, node_b) -> float
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

# Common English stop words - small set for efficiency
STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "about",
        "like",
        "through",
        "after",
        "over",
        "between",
        "out",
        "against",
        "during",
        "without",
        "before",
        "under",
        "around",
        "among",
        "and",
        "but",
        "or",
        "nor",
        "not",
        "so",
        "yet",
        "both",
        "either",
        "neither",
        "each",
        "every",
        "all",
        "any",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "only",
        "own",
        "same",
        "than",
        "too",
        "very",
        "just",
        "because",
        "if",
        "when",
        "where",
        "how",
        "what",
        "which",
        "who",
        "whom",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "i",
        "me",
        "my",
        "we",
        "our",
        "you",
        "your",
        "he",
        "him",
        "his",
        "she",
        "her",
        "they",
        "them",
        "their",
    }
)


def _tokenize(text: str) -> set[str]:
    """Tokenize text into lowercase words, removing stop words and short tokens.

    Args:
        text: Input text

    Returns:
        Set of meaningful lowercase tokens
    """
    if not text:
        return set()
    words = text.lower().split()
    return {w.strip(".,;:!?()[]{}\"'") for w in words if len(w) > 2} - STOP_WORDS


def compute_word_similarity(text_a: str, text_b: str) -> float:
    """Compute Jaccard similarity on tokenized words minus stop words.

    Args:
        text_a: First text
        text_b: Second text

    Returns:
        Similarity score between 0.0 and 1.0
    """
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b

    return len(intersection) / len(union) if union else 0.0


def compute_tag_similarity(tags_a: list[str], tags_b: list[str]) -> float:
    """Compute Jaccard similarity between two tag lists.

    Args:
        tags_a: First tag list
        tags_b: Second tag list

    Returns:
        Similarity score between 0.0 and 1.0
    """
    if not tags_a or not tags_b:
        return 0.0

    set_a = {t.lower().strip() for t in tags_a if t.strip()}
    set_b = {t.lower().strip() for t in tags_b if t.strip()}

    if not set_a or not set_b:
        return 0.0

    intersection = set_a & set_b
    union = set_a | set_b

    return len(intersection) / len(union) if union else 0.0


def compute_similarity(node_a: dict[str, Any], node_b: dict[str, Any]) -> float:
    """Compute weighted composite similarity between two knowledge nodes.

    Weights: 0.5 * word_similarity + 0.2 * tag_similarity + 0.3 * concept_similarity

    Args:
        node_a: First node dict with keys: content, tags, concept
        node_b: Second node dict with keys: content, tags, concept

    Returns:
        Weighted similarity score between 0.0 and 1.0
    """
    # Word similarity on content
    word_sim = compute_word_similarity(
        node_a.get("content", ""),
        node_b.get("content", ""),
    )

    # Tag similarity
    tag_sim = compute_tag_similarity(
        node_a.get("tags", []),
        node_b.get("tags", []),
    )

    # Concept similarity (word similarity on concept field)
    concept_sim = compute_word_similarity(
        node_a.get("concept", ""),
        node_b.get("concept", ""),
    )

    return 0.5 * word_sim + 0.2 * tag_sim + 0.3 * concept_sim


def rerank_facts_by_query(
    facts: list[dict[str, Any]],
    query: str,
    top_k: int = 0,
) -> list[dict[str, Any]]:
    """Rerank retrieved facts by keyword relevance to a query.

    Uses keyword overlap (Jaccard-like) to score each fact against the query,
    then sorts facts so the most relevant ones appear first. Facts with zero
    relevance are kept but moved to the end to preserve completeness.

    This is a lightweight reranking step that improves synthesis quality
    by putting the most relevant context at the top of the LLM prompt.

    Args:
        facts: List of fact dicts with 'outcome' and/or 'context' keys
        query: The question or search query
        top_k: If > 0, return only the top-k facts. If 0, return all (reranked).

    Returns:
        Reranked list of fact dicts (most relevant first)
    """
    if not facts or not query:
        return facts

    query_tokens = _tokenize(query)
    if not query_tokens:
        return facts

    scored: list[tuple[float, int, dict[str, Any]]] = []
    for idx, fact in enumerate(facts):
        # Combine outcome and context text for matching
        fact_text = f"{fact.get('context', '')} {fact.get('outcome', '')}"
        fact_tokens = _tokenize(fact_text)

        if not fact_tokens:
            scored.append((0.0, idx, fact))
            continue

        # Compute overlap: fraction of query tokens found in fact
        overlap = len(query_tokens & fact_tokens) / len(query_tokens)
        scored.append((overlap, idx, fact))

    # Sort by relevance score descending, then by original order for ties
    scored.sort(key=lambda x: (-x[0], x[1]))

    reranked = [item[2] for item in scored]

    if top_k > 0:
        return reranked[:top_k]
    return reranked


__all__ = [
    "compute_word_similarity",
    "compute_tag_similarity",
    "compute_similarity",
    "rerank_facts_by_query",
]
