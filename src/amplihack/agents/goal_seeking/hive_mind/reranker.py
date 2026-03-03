"""Cross-encoder reranking and Reciprocal Rank Fusion for the hive mind.

Provides second-stage reranking using cross-encoder models and RRF merge
for combining results from multiple retrieval sources (keyword, vector,
federated).

Philosophy:
- Single responsibility: rerank and merge result lists
- Graceful degradation: falls back to confidence-based ranking when
  sentence-transformers/cross-encoder unavailable
- RRF is dependency-free and works with any scored result list

Public API (the "studs"):
    CrossEncoderReranker: Rerank facts using cross-encoder model
    hybrid_score: Combine keyword and vector scores
    hybrid_score_weighted: Multi-signal scoring (semantic + confirmation + trust)
    trust_weighted_score: Score combining similarity, trust, and confidence
    rrf_merge: Reciprocal Rank Fusion for merging ranked lists
    HAS_CROSS_ENCODER: Feature flag for availability checks
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

from .constants import (
    CONFIRMATION_NORMALIZATION_DIVISOR,
    DEFAULT_CONFIRMATION_WEIGHT,
    DEFAULT_CROSS_ENCODER_MODEL,
    DEFAULT_KEYWORD_WEIGHT,
    DEFAULT_SEMANTIC_WEIGHT,
    DEFAULT_TRUST_WEIGHT,
    DEFAULT_VECTOR_WEIGHT,
    RRF_K,
    TRUST_NORMALIZATION_DIVISOR,
)

# ---------------------------------------------------------------------------
# Optional dependency: sentence-transformers CrossEncoder
# ---------------------------------------------------------------------------

try:
    from sentence_transformers import CrossEncoder  # type: ignore[import-untyped]

    HAS_CROSS_ENCODER = True
except ImportError:
    CrossEncoder = None  # type: ignore[assignment,misc]
    HAS_CROSS_ENCODER = False


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class ScoredFact:
    """A fact with an associated relevance score.

    Attributes:
        fact: The fact object (HiveFact or dict).
        score: Relevance score (higher is better).
        source: Which retrieval method produced this result.
    """

    fact: Any
    score: float
    source: str = "unknown"


# ---------------------------------------------------------------------------
# Cross-encoder reranker
# ---------------------------------------------------------------------------


class CrossEncoderReranker:
    """Rerank facts using a cross-encoder model.

    Cross-encoders jointly encode query+document pairs, producing more
    accurate relevance scores than bi-encoder similarity. Slower but
    more precise -- intended for reranking a small candidate set.

    Falls back to confidence-based ranking when unavailable.

    Args:
        model_name: HuggingFace cross-encoder model identifier.

    Example:
        >>> reranker = CrossEncoderReranker()
        >>> if reranker.available:
        ...     scored = reranker.rerank("DNA info", [fact1, fact2])
    """

    def __init__(self, model_name: str = DEFAULT_CROSS_ENCODER_MODEL) -> None:
        self._model_name = model_name
        self._model: CrossEncoder | None = None

        if HAS_CROSS_ENCODER:
            try:
                self._model = CrossEncoder(model_name)
                logger.info("Loaded cross-encoder model %s", model_name)
            except Exception:
                logger.warning("Failed to load cross-encoder model %s", model_name, exc_info=True)
                self._model = None

    @property
    def available(self) -> bool:
        """Whether the cross-encoder model is loaded and ready."""
        return self._model is not None

    def rerank(
        self,
        query: str,
        facts: list[Any],
        limit: int = 20,
    ) -> list[ScoredFact]:
        """Rerank facts by cross-encoder relevance to query.

        Args:
            query: The search query.
            facts: List of HiveFact objects (must have .content attribute).
            limit: Maximum results to return.

        Returns:
            List of ScoredFact sorted by cross-encoder score descending.
            Falls back to confidence-based ranking if model unavailable.
        """
        if not facts:
            return []

        if self._model is None:
            # Fallback: sort by confidence
            return sorted(
                [
                    ScoredFact(
                        fact=f,
                        score=getattr(f, "confidence", 0.5),
                        source="confidence_fallback",
                    )
                    for f in facts
                ],
                key=lambda sf: -sf.score,
            )[:limit]

        pairs = [(query, getattr(f, "content", str(f))) for f in facts]
        scores = self._model.predict(pairs)

        scored = [
            ScoredFact(fact=f, score=float(s), source="cross_encoder")
            for f, s in zip(facts, scores, strict=False)
        ]
        scored.sort(key=lambda sf: -sf.score)
        return scored[:limit]


# ---------------------------------------------------------------------------
# Hybrid scoring
# ---------------------------------------------------------------------------


def hybrid_score(
    keyword_score: float,
    vector_score: float,
    keyword_weight: float = DEFAULT_KEYWORD_WEIGHT,
    vector_weight: float = DEFAULT_VECTOR_WEIGHT,
) -> float:
    """Combine keyword and vector retrieval scores.

    Args:
        keyword_score: Score from keyword matching (0.0+).
        vector_score: Score from vector similarity (0.0-1.0).
        keyword_weight: Weight for keyword score.
        vector_weight: Weight for vector score.

    Returns:
        Weighted combined score.
    """
    return keyword_score * keyword_weight + vector_score * vector_weight


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion
# ---------------------------------------------------------------------------

# Standard RRF constant (Cormack et al., 2009)
_RRF_K = RRF_K


def rrf_merge(
    *ranked_lists: list[Any],
    key: str = "fact_id",
    k: int = _RRF_K,
    limit: int = 20,
) -> list[ScoredFact]:
    """Merge multiple ranked lists using Reciprocal Rank Fusion.

    RRF score = sum(1 / (k + rank_i)) across all lists where the item appears.
    This is robust to score scale differences between retrieval methods.

    Args:
        *ranked_lists: Variable number of ranked fact lists.
            Each list contains objects with a `key` attribute for dedup.
        key: Attribute name used to identify unique facts.
        k: RRF constant (default 60).
        limit: Maximum results.

    Returns:
        Merged list of ScoredFact sorted by RRF score descending.
    """
    scores: dict[str, float] = {}
    facts_by_id: dict[str, Any] = {}

    for ranked_list in ranked_lists:
        for rank, fact in enumerate(ranked_list):
            fact_key = getattr(fact, key, None) or str(id(fact))
            rrf_score = 1.0 / (k + rank + 1)  # +1 for 1-based ranking
            scores[fact_key] = scores.get(fact_key, 0.0) + rrf_score
            if fact_key not in facts_by_id:
                facts_by_id[fact_key] = fact

    result = [
        ScoredFact(fact=facts_by_id[fid], score=score, source="rrf")
        for fid, score in scores.items()
    ]
    result.sort(key=lambda sf: -sf.score)
    return result[:limit]


def trust_weighted_score(
    similarity: float,
    trust: float,
    confidence: float,
    *,
    w_similarity: float = DEFAULT_SEMANTIC_WEIGHT,
    w_trust: float = DEFAULT_CONFIRMATION_WEIGHT,
    w_confidence: float = DEFAULT_TRUST_WEIGHT,
) -> float:
    """Score combining similarity, source trust, and fact confidence.

    Weights default to similarity-heavy (0.5) with trust (0.3) as a strong
    secondary signal and confidence (0.2) as a tiebreaker.

    Args:
        similarity: Semantic similarity score (0.0-1.0).
        trust: Source agent's trust score (0.0-2.0).
        confidence: Fact's confidence score (0.0-1.0).
        w_similarity: Weight for similarity.
        w_trust: Weight for trust.
        w_confidence: Weight for confidence.

    Returns:
        Combined trust-weighted score.
    """
    # Normalize trust from [0.0, 2.0] to [0.0, 1.0]
    trust_norm = min(1.0, max(0.0, trust) / TRUST_NORMALIZATION_DIVISOR)
    confidence_norm = min(1.0, max(0.0, confidence))
    similarity_norm = min(1.0, max(0.0, similarity))
    return w_similarity * similarity_norm + w_trust * trust_norm + w_confidence * confidence_norm


def hybrid_score_weighted(
    semantic_similarity: float = 0.0,
    confirmation_count: int = 0,
    source_trust: float = 1.0,
    *,
    w_semantic: float = DEFAULT_SEMANTIC_WEIGHT,
    w_confirmation: float = DEFAULT_CONFIRMATION_WEIGHT,
    w_trust: float = DEFAULT_TRUST_WEIGHT,
) -> float:
    """Compute a hybrid relevance score combining multiple signals.

    Default weights: semantic_similarity (0.5) + confirmation_count (0.3)
    + source_trust (0.2).

    Args:
        semantic_similarity: Cosine similarity score (0.0-1.0).
        confirmation_count: Number of confirming agents (0+).
        source_trust: Trust score of the source agent (0.0-2.0).
        w_semantic: Weight for semantic similarity.
        w_confirmation: Weight for confirmation count.
        w_trust: Weight for source trust.

    Returns:
        Combined score.
    """
    conf_score = (
        min(1.0, confirmation_count / CONFIRMATION_NORMALIZATION_DIVISOR)
        if confirmation_count > 0
        else 0.0
    )
    trust_score = min(1.0, source_trust / TRUST_NORMALIZATION_DIVISOR)
    return w_semantic * semantic_similarity + w_confirmation * conf_score + w_trust * trust_score


__all__ = [
    "CrossEncoderReranker",
    "ScoredFact",
    "hybrid_score",
    "hybrid_score_weighted",
    "trust_weighted_score",
    "rrf_merge",
    "HAS_CROSS_ENCODER",
    "DEFAULT_CROSS_ENCODER_MODEL",
]
