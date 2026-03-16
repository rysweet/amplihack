"""Content quality scoring and gating for the hive mind.

Provides quality assessment for facts entering or being retrieved from
the hive, preventing low-quality content from polluting the shared
knowledge base.

Philosophy:
- Single responsibility: score content quality, gate promotions/retrieval
- No external dependencies: uses heuristic scoring (length, structure, specificity)
- Configurable thresholds for different deployment scenarios

Public API (the "studs"):
    score_content_quality: Score a fact's content quality (0.0-1.0)
    QualityGate: Configurable gate for promotion and retrieval
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field

from amplihack.utils.logging_utils import log_call

from .constants import DEFAULT_BROADCAST_THRESHOLD, DEFAULT_QUALITY_THRESHOLD

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Quality scoring heuristics
# ---------------------------------------------------------------------------

# Minimum content length for a meaningful fact
_MIN_CONTENT_LENGTH = 10
# Ideal content length range
_IDEAL_MIN_LENGTH = 30
_IDEAL_MAX_LENGTH = 500

# Words that indicate low-quality, vague content
_VAGUE_WORDS = frozenset(
    {
        "something",
        "stuff",
        "things",
        "whatever",
        "maybe",
        "probably",
        "idk",
        "dunno",
        "etc",
        "somehow",
    }
)

# Patterns indicating structured, specific content
_SPECIFIC_PATTERNS = [
    re.compile(r"\d+(\.\d+)?"),  # Contains numbers
    re.compile(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)+\b"),  # Proper nouns
    re.compile(r"\b(?:because|therefore|since|due to|caused by)\b", re.I),  # Causal
    re.compile(r"\b(?:always|never|must|requires|ensures)\b", re.I),  # Definitive
]


@log_call
def score_content_quality(content: str, concept: str = "") -> float:
    """Score the quality of a fact's content.

    Evaluates:
    - Length: too short or too long penalized
    - Specificity: vague words penalized, specific patterns rewarded
    - Structure: sentences, punctuation rewarded
    - Concept alignment: content mentioning the concept rewarded

    Args:
        content: The fact text to score.
        concept: Optional concept/topic for alignment scoring.

    Returns:
        Quality score between 0.0 and 1.0.
    """
    if not content or not content.strip():
        return 0.0

    content = content.strip()
    score = 0.0
    max_score = 0.0

    # --- Length score (0-0.3) ---
    max_score += 0.3
    length = len(content)
    if length < _MIN_CONTENT_LENGTH:
        score += 0.05  # Penalize very short content
    elif _IDEAL_MIN_LENGTH <= length <= _IDEAL_MAX_LENGTH:
        score += 0.3
    elif length < _IDEAL_MIN_LENGTH:
        score += 0.15
    else:  # too long
        score += 0.2

    # --- Specificity score (0-0.3) ---
    max_score += 0.3
    words = content.lower().split()
    if len(words) >= 3:  # Need at least 3 words for meaningful specificity
        vague_ratio = len([w for w in words if w in _VAGUE_WORDS]) / len(words)
        specificity = max(0.0, 1.0 - vague_ratio * 5)  # Penalize vagueness
        pattern_bonus = sum(0.05 for p in _SPECIFIC_PATTERNS if p.search(content))
        score += min(0.3, specificity * 0.2 + pattern_bonus)

    # --- Structure score (0-0.2) ---
    max_score += 0.2
    sentences = [s.strip() for s in re.split(r"[.!?]", content) if s.strip()]
    if len(sentences) >= 1:
        score += 0.1
    if len(sentences) >= 2:
        score += 0.05
    if any(c in content for c in ",:;()-"):
        score += 0.05

    # --- Concept alignment (0-0.2) ---
    max_score += 0.2
    if concept and concept.strip():
        concept_words = {w.lower() for w in concept.split() if len(w) > 1}
        content_words = {w.lower() for w in words if len(w) > 1}
        if concept_words & content_words:
            overlap = len(concept_words & content_words) / len(concept_words)
            score += min(0.2, overlap * 0.2)

    return min(1.0, score / max_score) if max_score > 0 else 0.0


# ---------------------------------------------------------------------------
# Quality gate
# ---------------------------------------------------------------------------


@dataclass
class QualityGate:
    """Configurable quality gate for hive mind operations.

    Controls:
    - promotion_threshold: Minimum quality for facts entering the hive
    - retrieval_confidence_threshold: Minimum confidence for facts returned in queries
    - broadcast_threshold: Minimum confidence for cross-group replication

    Args:
        promotion_threshold: Quality score threshold for promotion (0.0-1.0).
        retrieval_confidence_threshold: Confidence threshold for retrieval (0.0-1.0).
        broadcast_threshold: Confidence threshold for broadcast (0.0-1.0).

    Example:
        >>> gate = QualityGate(promotion_threshold=0.3)
        >>> gate.should_promote("DNA stores genetic information", "genetics")
        True
        >>> gate.should_promote("stuff", "genetics")
        False
    """

    promotion_threshold: float = DEFAULT_QUALITY_THRESHOLD
    retrieval_confidence_threshold: float = 0.0
    broadcast_threshold: float = DEFAULT_BROADCAST_THRESHOLD
    _quality_scores: dict[str, float] = field(default_factory=dict, repr=False)

    @log_call
    def should_promote(self, content: str, concept: str = "") -> bool:
        """Check if content meets quality threshold for promotion.

        Returns:
            True if quality score >= promotion_threshold.
        """
        quality = score_content_quality(content, concept)
        return quality >= self.promotion_threshold

    @log_call
    def should_retrieve(self, confidence: float) -> bool:
        """Check if a fact meets confidence threshold for retrieval.

        Args:
            confidence: Fact confidence score (0.0-1.0).

        Returns:
            True if confidence >= retrieval_confidence_threshold.
        """
        return confidence >= self.retrieval_confidence_threshold

    @log_call
    def should_broadcast(self, confidence: float) -> bool:
        """Check if a fact meets threshold for cross-group broadcast.

        Args:
            confidence: Fact confidence score (0.0-1.0).

        Returns:
            True if confidence >= broadcast_threshold.
        """
        return confidence >= self.broadcast_threshold

    @log_call
    def score(self, content: str, concept: str = "") -> float:
        """Score content quality (cached by content+concept hash).

        Returns:
            Quality score between 0.0 and 1.0.
        """
        key = hashlib.sha256(f"{content}:{concept}".encode()).hexdigest()[:16]
        if key not in self._quality_scores:
            self._quality_scores[key] = score_content_quality(content, concept)
        return self._quality_scores[key]


__all__ = ["QualityGate", "score_content_quality"]
