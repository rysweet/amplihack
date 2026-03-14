"""Named constants for retrieval path configuration.

Centralises all magic numbers used in knowledge-base size checks,
tier boundaries, and search candidate multipliers so they can be
reasoned about and tuned in one place.
"""

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
