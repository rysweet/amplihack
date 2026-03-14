"""Shared constants for the hive mind modules.

Centralizes magic numbers, strings, and default values used across
hive_graph, reranker, quality, gossip, fact_lifecycle, embeddings,
query_expansion, distributed, controller, and cognitive_adapter.

Philosophy:
- Single source of truth for all shared magic values
- Grouped by category for discoverability
- Import from here instead of scattering literals across modules
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Tag prefixes (used in promote_fact, gossip, federation)
# ---------------------------------------------------------------------------

BROADCAST_TAG_PREFIX = "broadcast_from:"
ESCALATION_TAG_PREFIX = "escalated_from:"
GOSSIP_TAG_PREFIX = "gossip_from:"

# ---------------------------------------------------------------------------
# Scoring weights (hybrid scoring in hive_graph and reranker)
# ---------------------------------------------------------------------------

DEFAULT_SEMANTIC_WEIGHT = 0.5
DEFAULT_CONFIRMATION_WEIGHT = 0.3
DEFAULT_TRUST_WEIGHT = 0.2
DEFAULT_KEYWORD_WEIGHT = 0.4
DEFAULT_VECTOR_WEIGHT = 0.6
CONFIDENCE_SCORE_BOOST = 0.01

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

DEFAULT_BROADCAST_THRESHOLD = 0.9
DEFAULT_QUALITY_THRESHOLD = 0.3
DEFAULT_CONFIDENCE_GATE = 0.3
DEFAULT_CONTRADICTION_OVERLAP = 0.4
GOSSIP_MIN_CONFIDENCE = 0.3
PEER_CONFIDENCE_DISCOUNT = 0.9  # Peer-received facts get 10% confidence discount

# ---------------------------------------------------------------------------
# Trust
# ---------------------------------------------------------------------------

MAX_TRUST_SCORE = 2.0
DEFAULT_TRUST_SCORE = 1.0
TRUST_NORMALIZATION_DIVISOR = 2.0
CONFIRMATION_NORMALIZATION_DIVISOR = 5.0

# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------

FEDERATED_QUERY_LIMIT_MULTIPLIER = 10
FEDERATED_QUERY_MIN_LIMIT = 200
DOMAIN_ROUTING_PRIORITY_MULTIPLIER = 3
RRF_K = 60
FACT_ID_HEX_LENGTH = 12

# ---------------------------------------------------------------------------
# Fact lifecycle
# ---------------------------------------------------------------------------

DEFAULT_FACT_TTL_SECONDS = 86400.0
DEFAULT_CONFIDENCE_DECAY_RATE = 0.01
DEFAULT_MAX_AGE_HOURS = 24.0
SECONDS_PER_HOUR = 3600.0

# ---------------------------------------------------------------------------
# Gossip
# ---------------------------------------------------------------------------

DEFAULT_GOSSIP_TOP_K = 10
DEFAULT_GOSSIP_FANOUT = 2
GOSSIP_RELAY_AGENT_PREFIX = "__gossip_"

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
DEFAULT_CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEFAULT_EXPANSION_MODEL = "claude-haiku-4-5-20251001"


__all__ = [
    "BROADCAST_TAG_PREFIX",
    "CONFIDENCE_SCORE_BOOST",
    "CONFIRMATION_NORMALIZATION_DIVISOR",
    "DEFAULT_BROADCAST_THRESHOLD",
    "DEFAULT_CONFIDENCE_DECAY_RATE",
    "DEFAULT_CONFIDENCE_GATE",
    "DEFAULT_CONFIRMATION_WEIGHT",
    "DEFAULT_CONTRADICTION_OVERLAP",
    "DEFAULT_CROSS_ENCODER_MODEL",
    "DEFAULT_EMBEDDING_MODEL",
    "DEFAULT_EXPANSION_MODEL",
    "DEFAULT_FACT_TTL_SECONDS",
    "DEFAULT_GOSSIP_FANOUT",
    "DEFAULT_GOSSIP_TOP_K",
    "DEFAULT_KEYWORD_WEIGHT",
    "DEFAULT_MAX_AGE_HOURS",
    "DEFAULT_QUALITY_THRESHOLD",
    "DEFAULT_SEMANTIC_WEIGHT",
    "DEFAULT_TRUST_SCORE",
    "DEFAULT_TRUST_WEIGHT",
    "DEFAULT_VECTOR_WEIGHT",
    "DOMAIN_ROUTING_PRIORITY_MULTIPLIER",
    "ESCALATION_TAG_PREFIX",
    "FACT_ID_HEX_LENGTH",
    "FEDERATED_QUERY_LIMIT_MULTIPLIER",
    "FEDERATED_QUERY_MIN_LIMIT",
    "GOSSIP_MIN_CONFIDENCE",
    "GOSSIP_RELAY_AGENT_PREFIX",
    "GOSSIP_TAG_PREFIX",
    "MAX_TRUST_SCORE",
    "PEER_CONFIDENCE_DISCOUNT",
    "RRF_K",
    "SECONDS_PER_HOUR",
    "TRUST_NORMALIZATION_DIVISOR",
]
