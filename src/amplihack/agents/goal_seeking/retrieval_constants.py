"""Named constants for retrieval path configuration.

Centralises all magic numbers used in knowledge-base size checks,
tier boundaries, search candidate multipliers, and scoring weights
so they can be reasoned about and tuned in one place.
"""

# ---------------------------------------------------------------------------
# Core retrieval limits
# ---------------------------------------------------------------------------

# Maximum number of facts to pull from the store in a single get_all_facts()
# call.  Raising this above ~15 000 has caused >89 GB RSS during long evals.
MAX_RETRIEVAL_LIMIT: int = 15_000

# KB size at or below which the agent skips search entirely and returns all
# facts verbatim, letting the LLM decide relevance.
SIMPLE_RETRIEVAL_THRESHOLD: int = 500

# KB size at or below which _all_ facts are returned verbatim (no tier
# compression).  Above this the tiered-summarisation path is used.
VERBATIM_RETRIEVAL_THRESHOLD: int = 1_000

# Tier 1 of _tiered_retrieval: the N most-recent facts are kept verbatim.
TIER1_VERBATIM_SIZE: int = 200

# Tier 2 boundary: facts ranked VERBATIM_RETRIEVAL_THRESHOLD+1 down to
# TIER1_VERBATIM_SIZE+1 receive entity-level summarisation.
# (Tier 3 covers everything older than VERBATIM_RETRIEVAL_THRESHOLD.)
TIER2_ENTITY_SIZE: int = VERBATIM_RETRIEVAL_THRESHOLD  # == 1 000

# How many extra search candidates to fetch before n-gram re-ranking.
SEARCH_CANDIDATE_MULTIPLIER: int = 3

# Multiplier for the broad full-scan fallback when keyword search returns
# nothing.
FALLBACK_SCAN_MULTIPLIER: int = 5

# ---------------------------------------------------------------------------
# OODA / orient
# ---------------------------------------------------------------------------

# Number of facts to recall in orient() to contextualise the input.
ORIENT_SEARCH_LIMIT: int = 15

# ---------------------------------------------------------------------------
# Memory agent strategy selector
# ---------------------------------------------------------------------------

# KB size threshold below (or equal to) which the strategy selector picks
# SIMPLE_ALL (dump everything) vs TWO_PHASE.  Kept separate from
# SIMPLE_RETRIEVAL_THRESHOLD (500) which governs learning_agent / cognitive
# adapter paths; this tighter value (150) is used by MemoryAgent's own
# strategy selector.
MEMORY_AGENT_SMALL_KB_THRESHOLD: int = 150

# Hard cap on the broad-search candidate set inside _two_phase_retrieve.
TWO_PHASE_BROAD_CAP: int = 200

# Default limit for simple retrieve-all in memory agent.
SIMPLE_RETRIEVE_DEFAULT_LIMIT: int = 50

# Display limits in aggregation results.
ENTITY_DISPLAY_LIMIT: int = 30
CONCEPT_DISPLAY_LIMIT: int = 20
AGGREGATION_FACTS_LIMIT: int = 20

# Default temporal index for facts with unknown ordering.
DEFAULT_TEMPORAL_INDEX: int = 999_999

# ---------------------------------------------------------------------------
# Entity & concept retrieval
# ---------------------------------------------------------------------------

# Max phrases used in concept-based retrieval.
CONCEPT_PHRASE_LIMIT: int = 8

# Limit for concept search results.
CONCEPT_SEARCH_LIMIT: int = 15

# Limit for exact concept matching.
CONCEPT_EXACT_SEARCH_LIMIT: int = 50

# Standard entity search limit.
ENTITY_SEARCH_LIMIT: int = 100

# Deeper retrieval limit for CVE/incident-style queries.
INCIDENT_QUERY_SEARCH_LIMIT: int = 200

# Per-entity fact limit in entity_retrieval.
ENTITY_FACT_LIMIT: int = 80

# Facts per entity in multi-entity queries.
MULTI_ENTITY_LIMIT: int = 40

# Text search limit for structured entity IDs.
ENTITY_ID_TEXT_SEARCH_LIMIT: int = 20

# Topics shown from conflicting-information analysis.
CONFLICTING_TOPICS_LIMIT: int = 20

# ---------------------------------------------------------------------------
# Scoring weights
# ---------------------------------------------------------------------------

# N-gram overlap scoring weights (must sum to 1.0).
UNIGRAM_WEIGHT: float = 0.65
BIGRAM_WEIGHT: float = 0.35

# Per-rank decrement in position-based scoring for shard responses.
POSITION_SCORE_DECREMENT: float = 0.01

# ---------------------------------------------------------------------------
# Distributed hive
# ---------------------------------------------------------------------------

# Multiplier for hive search broad-fetch (fetch extra for merge headroom).
HIVE_SEARCH_MULTIPLIER: int = 3

# Max keywords used when building a hive query string from concept keywords.
QUERY_KEYWORD_LIMIT: int = 4

# Expected items for BloomFilter sizing in shard stores.
BLOOMFILTER_EXPECTED_ITEMS: int = 500

# Fact limit for contradiction-detection queries.
CONTRADICTION_CHECK_LIMIT: int = 50

# Overlap threshold for contradiction detection between facts.
CONTRADICTION_OVERLAP_THRESHOLD: float = 0.4

# Minimum peer agents queried in gossip fan-out.
MIN_PEER_FANOUT: int = 2

# Top-N experts to query in federation routing.
TOP_EXPERTS_COUNT: int = 3

# Confidence discount applied to facts received from peer agents.
PEER_CONFIDENCE_DISCOUNT: float = 0.9
