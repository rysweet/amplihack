from __future__ import annotations

"""All memory retrieval strategies (simple, tiered, aggregation, entity, etc.)."""

import json
import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from .prompt_utils import _get_llm_completion, _load_prompt
from .prompts import load_prompt
from .retrieval_constants import (
    CONCEPT_EXACT_SEARCH_LIMIT,
    CONCEPT_PHRASE_LIMIT,
    CONCEPT_SEARCH_LIMIT,
    CONFLICTING_TOPICS_LIMIT,
    ENTITY_FACT_LIMIT,
    ENTITY_ID_TEXT_SEARCH_LIMIT,
    ENTITY_SEARCH_LIMIT,
    INCIDENT_QUERY_SEARCH_LIMIT,
    MAX_RETRIEVAL_LIMIT,
    MULTI_ENTITY_LIMIT,
    TIER1_VERBATIM_SIZE,
    TIER2_ENTITY_SIZE,
    VERBATIM_RETRIEVAL_THRESHOLD,
)

logger = logging.getLogger(__name__)


class RetrievalStrategiesMixin:
    """Mixin providing retrieval strategies for LearningAgent."""

    # Intent classification constants
    SIMPLE_INTENTS = {
        "simple_recall",
        "incremental_update",
        "contradiction_resolution",
        "multi_source_synthesis",
        "causal_counterfactual",
    }

    # Aggregation intents: routed to Cypher graph queries instead of text search
    AGGREGATION_INTENTS = {"meta_memory"}

    # Stop words for concept retrieval
    _STOP_WORDS = frozenset(
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
            "between",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "and",
            "but",
            "or",
            "not",
            "no",
            "if",
            "then",
            "than",
            "that",
            "this",
            "these",
            "those",
            "it",
            "its",
            "he",
            "she",
            "they",
            "we",
            "you",
            "i",
            "my",
            "your",
            "his",
            "her",
            "their",
            "our",
            "what",
            "which",
            "who",
            "whom",
            "how",
            "when",
            "where",
            "why",
            "all",
            "each",
            "every",
            "both",
            "few",
            "more",
            "most",
            "other",
            "some",
            "such",
            "any",
            "many",
            "much",
            "own",
            "same",
            "so",
            "too",
            "very",
            "just",
            "also",
        }
    )

    # Infrastructure relation patterns
    _INFRASTRUCTURE_RELATION_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
        "subnet": (
            re.compile(r"subnet\s+named\s+['\"]?([A-Za-z0-9_.-]+)['\"]?", re.IGNORECASE),
            re.compile(r"\b([A-Za-z0-9_.-]+)\s+subnet\b", re.IGNORECASE),
        ),
    }

    # Entity ID pattern
    _ENTITY_ID_PATTERN = re.compile(r"\b([A-Z]{2,5}-\d{4}-\d{2,5})\b")

    def _simple_retrieval(
        self, question: str, force_verbatim: bool = False
    ) -> list[dict[str, Any]]:
        """Single-pass retrieval with progressive summarization for large KBs.

        For small KBs (<=500 facts): returns all facts verbatim.
        For medium KBs (501-1000 facts): returns all facts verbatim.
        For large KBs (1000+ facts): uses tiered summarization:
            - Tier 1 (recent 200 facts): verbatim
            - Tier 2 (facts 201-1000): entity-level summaries
            - Tier 3 (facts 1000+): topic-level summaries

        Args:
            question: The question to retrieve facts for
            force_verbatim: (Solution C/D) When True, bypass tiered summarization
                and return all facts verbatim regardless of KB size. Use in agentic
                context or when pre-snapshot is available to prevent early-stored
                facts from being lost in Tier 3 compression.

        Returns:
            List of fact dicts
        """
        self._thread_local._last_simple_retrieval_exhaustive = False

        if not hasattr(self.memory, "get_all_facts"):
            return []

        # Solution D: Use pre-snapshot if available (set by eval harness before
        # parallel evaluation to give all threads a consistent view of facts).
        if self._pre_snapshot_facts is not None:
            logger.debug(
                "Using pre-snapshot facts (%d) for thread-safe retrieval",
                len(self._pre_snapshot_facts),
            )
            exhaustive = (
                force_verbatim or len(self._pre_snapshot_facts) <= VERBATIM_RETRIEVAL_THRESHOLD
            )
            self._thread_local._last_simple_retrieval_exhaustive = exhaustive
            if exhaustive:
                return list(self._pre_snapshot_facts)
            return self._tiered_retrieval(question, self._pre_snapshot_facts)

        # Solution A: Reuse thread-local cached snapshot from answer_question.
        # Thread-local storage prevents data races when multiple threads share
        # one LearningAgent instance (e.g. --parallel-workers 10 in eval harness).
        cached = getattr(self._thread_local, "_cached_all_facts", None)
        if cached is not None:
            all_facts = cached
            self._thread_local._cached_all_facts = None  # consume; one-shot per question
        else:
            all_facts = self.memory.get_all_facts(limit=MAX_RETRIEVAL_LIMIT, query=question)
        kb_size = len(all_facts)

        total_fact_count = self._estimate_total_fact_count()
        distributed_partial = (
            hasattr(self.memory, "search_local")
            and total_fact_count is not None
            and kb_size > total_fact_count
        )
        if distributed_partial:
            logger.info(
                "Simple retrieval treating query-bearing distributed results as partial "
                "(retrieved=%d local_total=%d) for '%s'",
                kb_size,
                total_fact_count,
                question[:60],
            )

        exhaustive = force_verbatim or (
            not distributed_partial
            and (
                (
                    total_fact_count is not None
                    and total_fact_count <= VERBATIM_RETRIEVAL_THRESHOLD
                    and kb_size >= total_fact_count
                )
                or (
                    total_fact_count is None
                    and not hasattr(self.memory, "search_local")
                    and kb_size <= VERBATIM_RETRIEVAL_THRESHOLD
                )
            )
        )
        self._thread_local._last_simple_retrieval_exhaustive = exhaustive
        if exhaustive:
            return all_facts

        # Large KB: use progressive summarization tiers
        return self._tiered_retrieval(question, all_facts)

    def _estimate_total_fact_count(self) -> int | None:
        """Estimate total locally stored facts without using query-filtered retrieval."""
        if self._pre_snapshot_facts is not None:
            return len(self._pre_snapshot_facts)

        if not hasattr(self.memory, "get_statistics"):
            return None

        try:
            stats = self.memory.get_statistics()
        except Exception as exc:
            logger.debug("Unable to estimate total fact count from memory stats: %s", exc)
            return None

        def _extract_total(mapping: Any) -> int | None:
            if not isinstance(mapping, dict):
                return None

            for key in ("total_experiences", "total", "total_facts", "semantic"):
                value = mapping.get(key)
                if isinstance(value, int) and value >= 0:
                    return value

            semantic_nodes = mapping.get("semantic_nodes")
            episodic_nodes = mapping.get("episodic_nodes")
            if isinstance(semantic_nodes, int) and semantic_nodes >= 0:
                if isinstance(episodic_nodes, int) and episodic_nodes >= 0:
                    return semantic_nodes + episodic_nodes
                return semantic_nodes

            return None

        total = _extract_total(stats)
        if total is not None:
            return total

        return _extract_total(stats.get("adapter_stats"))

    def _preserve_exact_id_facts(
        self, question: str, all_facts: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Keep question-matching structured-ID facts verbatim before tiering.

        Large distributed retrieval already fans out across the whole hive and can
        return the relevant exact-ID facts in its first pass. The quality loss came
        from compressing those older campaign/incident facts into summaries, which
        then forced a second distributed exact-ID search. Preserve those exact-ID
        matches here so the first distributed pass is sufficient.
        """
        entity_ids = {entity_id.lower() for entity_id in self._ENTITY_ID_PATTERN.findall(question)}
        if not entity_ids:
            return [], all_facts

        q_lower = question.lower()
        is_incident_query = any(
            kw in q_lower for kw in ("incident", "cve", "vulnerability", "security")
        )
        exact_limit = INCIDENT_QUERY_SEARCH_LIMIT if is_incident_query else ENTITY_SEARCH_LIMIT

        exact_id_facts: list[dict[str, Any]] = []
        remaining_facts: list[dict[str, Any]] = []
        seen_exact: set[str] = set()

        for fact in all_facts:
            fact_text = (
                f"{fact.get('context', '')} {fact.get('outcome', fact.get('content', ''))}"
            ).lower()
            if any(entity_id in fact_text for entity_id in entity_ids):
                dedupe_key = fact.get("experience_id", "") or fact_text
                if dedupe_key not in seen_exact:
                    seen_exact.add(dedupe_key)
                    exact_id_facts.append(fact)
            else:
                remaining_facts.append(fact)

        if exact_limit and len(exact_id_facts) > exact_limit:
            exact_id_facts = exact_id_facts[-exact_limit:]

        if exact_id_facts:
            logger.info(
                "Tiered retrieval preserved %d exact-ID facts verbatim for '%s'",
                len(exact_id_facts),
                question[:60],
            )

        return exact_id_facts, remaining_facts

    def _tiered_retrieval(
        self, question: str, all_facts: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Tiered retrieval with progressive summarization for large KBs.

        Tier 1 (most recent 200): verbatim.
        Tier 2 (201-1000): entity-level summaries.
        Tier 3 (1000+): topic-level summaries.

        Summaries preserve key details: numbers, names, dates, status values.
        """

        def _sort_key(f: dict) -> tuple:
            ts = f.get("timestamp", "")
            meta = f.get("metadata", {})
            t_idx = meta.get("temporal_index", 0) if meta else 0
            return (t_idx, ts)

        sorted_facts = sorted(all_facts, key=_sort_key)
        exact_id_facts, remaining_facts = self._preserve_exact_id_facts(question, sorted_facts)
        kb_size = len(sorted_facts)
        result: list[dict[str, Any]] = list(exact_id_facts)

        # Tier 1: Most recent TIER1_VERBATIM_SIZE facts - verbatim
        tier1_facts = remaining_facts[max(0, len(remaining_facts) - TIER1_VERBATIM_SIZE) :]
        result.extend(tier1_facts)

        # Tier 2: Facts TIER1_VERBATIM_SIZE+1 to TIER2_ENTITY_SIZE - entity-level summaries
        tier2_start = max(0, len(remaining_facts) - TIER2_ENTITY_SIZE)
        tier2_end = max(0, len(remaining_facts) - TIER1_VERBATIM_SIZE)
        if tier2_end > tier2_start:
            tier2_facts = remaining_facts[tier2_start:tier2_end]
            tier2_summaries = self._summarize_old_facts(tier2_facts, level="entity")
            result.extend(tier2_summaries)

        # Tier 3: Facts 1000+ - topic-level summaries
        if tier2_start > 0:
            tier3_facts = remaining_facts[:tier2_start]
            tier3_summaries = self._summarize_old_facts(tier3_facts, level="topic")
            result.extend(tier3_summaries)

        logger.info(
            "Tiered retrieval: %d total -> %d exact-ID + %d tier1 verbatim + %d summarized items",
            kb_size,
            len(exact_id_facts),
            len(tier1_facts),
            len(result) - len(exact_id_facts) - len(tier1_facts),
        )
        return result

    def _summarize_old_facts(
        self, facts: list[dict[str, Any]], level: str = "entity"
    ) -> list[dict[str, Any]]:
        """Deterministic summarization grouping facts by entity or topic.

        Preserves all numbers, proper names, dates, and status values.
        No LLM calls -- fast enough for retrieval path.
        """
        if not facts:
            return []

        groups: dict[str, list[dict[str, Any]]] = {}
        for f in facts:
            if level == "entity":
                key = f.get("context", "General")
            else:
                ctx = f.get("context", "General")
                key = ctx.split(":")[0].strip() if ":" in ctx else ctx.split(".")[0].strip()
            groups.setdefault(key, []).append(f)

        summaries: list[dict[str, Any]] = []
        for group_key, group_facts in groups.items():
            if len(group_facts) <= 2:
                summaries.extend(group_facts)
                continue

            fact_texts = []
            for f in group_facts[:30]:
                outcome = f.get("outcome", f.get("fact", ""))
                if outcome:
                    fact_texts.append(outcome[:200])

            if not fact_texts:
                continue

            combined = "; ".join(fact_texts)
            if len(combined) > 500:
                truncate_at = combined.rfind(".", 0, 500)
                if truncate_at > 100:
                    combined = combined[: truncate_at + 1]
                else:
                    combined = combined[:500] + "..."

            summaries.append(
                {
                    "context": f"SUMMARY ({group_key})",
                    "outcome": f"[Summary of {len(group_facts)} facts about {group_key}]: {combined}",
                    "confidence": 0.7,
                    "tags": ["summary", level],
                    "metadata": {"is_summary": True, "source_count": len(group_facts)},
                }
            )

        return summaries

    def _aggregation_retrieval(self, question: str, intent: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle meta-memory questions via Cypher aggregation.

        Routes "how many", "list all", "count" questions to graph aggregation
        queries instead of text search. Returns synthetic fact dicts containing
        the aggregation results so the LLM can synthesize an answer.

        Args:
            question: The meta-memory question
            intent: Intent classification dict

        Returns:
            List of fact dicts with aggregation results
        """
        if not (self.use_hierarchical and hasattr(self.memory, "execute_aggregation")):
            # Fall back to simple retrieval if not using hierarchical memory
            return self._simple_retrieval(question)

        q_lower = question.lower()
        results: list[dict[str, Any]] = []

        # Detect the entity type being asked about
        entity_type = ""
        for kw in ("project", "people", "person", "team", "member"):
            if kw in q_lower:
                entity_type = kw
                break

        # Execute appropriate aggregation
        if entity_type == "project":
            agg = self.memory.execute_aggregation("list_concepts", entity_filter="project")
            if agg.get("items"):
                # Filter to likely project names (not generic concepts)
                items = agg["items"]
                results.append(
                    {
                        "context": "Meta-memory: Project count",
                        "outcome": f"There are {len(items)} distinct project-related concepts: {', '.join(items)}",
                        "confidence": 1.0,
                        "timestamp": "",
                        "tags": ["meta_memory"],
                        "metadata": {"aggregation": True},
                    }
                )

        if entity_type in ("people", "person", "member", "team"):
            agg = self.memory.execute_aggregation("list_entities")
            if agg.get("items"):
                items = agg["items"]
                results.append(
                    {
                        "context": "Meta-memory: Entity list",
                        "outcome": f"There are {len(items)} distinct entities: {', '.join(items)}",
                        "confidence": 1.0,
                        "timestamp": "",
                        "tags": ["meta_memory"],
                        "metadata": {"aggregation": True},
                    }
                )

        # Conflicting/contradicting topic queries: use SUPERSEDES edges
        if any(kw in q_lower for kw in ("conflict", "contradict", "disagree", "different sources")):
            if hasattr(self.memory, "execute_aggregation"):
                superseded = self.memory.execute_aggregation("list_superseded")
                if superseded.get("items"):
                    topics = list(set(superseded["items"]))
                    results.append(
                        {
                            "context": "Meta-memory: Conflicting topics",
                            "outcome": f"Topics with conflicting/updated information: {', '.join(topics[:CONFLICTING_TOPICS_LIMIT])}",
                            "confidence": 1.0,
                            "timestamp": "",
                            "tags": ["meta_memory", "contradictions"],
                            "metadata": {"aggregation": True},
                        }
                    )

        # CVE/incident cross-reference queries: use graph JOIN to find ALL
        # facts mentioning CVE or incident IDs, including edge-linked facts
        if "cve" in q_lower or "vulnerabilit" in q_lower or "incident" in q_lower:
            if hasattr(self.memory, "execute_aggregation"):
                incident_cve_agg = self.memory.execute_aggregation("list_incident_cves")
                if incident_cve_agg.get("contents"):
                    for content_text in incident_cve_agg["contents"]:
                        results.append(
                            {
                                "context": "Graph JOIN: Incident/CVE cross-reference",
                                "outcome": content_text,
                                "confidence": 0.9,
                                "timestamp": "",
                                "tags": ["incident_cve", "graph_join"],
                                "metadata": {"aggregation": True},
                            }
                        )
                if incident_cve_agg.get("items"):
                    topics = list(set(incident_cve_agg["items"]))
                    results.append(
                        {
                            "context": "Meta-memory: Incident/CVE topics",
                            "outcome": f"Incident/CVE related topics ({len(topics)}): {', '.join(topics[:30])}",
                            "confidence": 1.0,
                            "timestamp": "",
                            "tags": ["meta_memory", "incident_cve"],
                            "metadata": {"aggregation": True},
                        }
                    )
            # Also do text search as fallback/supplement
            if hasattr(self.memory, "search"):
                cve_facts = self.memory.search(query="CVE incident", limit=50)
                existing_outcomes = {r.get("outcome", "") for r in results}
                for f in cve_facts:
                    if f.get("outcome", f.get("fact", "")) not in existing_outcomes:
                        results.append(f)

        # General aggregation: count all entities and concepts
        if not results:
            entity_agg = self.memory.execute_aggregation("list_entities")
            concept_agg = self.memory.execute_aggregation("count_by_concept")
            total_agg = self.memory.execute_aggregation("count_total")

            summary_parts = []
            if total_agg.get("count"):
                summary_parts.append(f"Total facts stored: {total_agg['count']}")
            if entity_agg.get("items"):
                summary_parts.append(
                    f"Distinct entities ({len(entity_agg['items'])}): "
                    f"{', '.join(entity_agg['items'][:30])}"
                )
            if concept_agg.get("items"):
                top_concepts = list(concept_agg["items"].items())[:20]
                concept_str = ", ".join(f"{c} ({n} facts)" for c, n in top_concepts)
                summary_parts.append(f"Top concepts: {concept_str}")

            if summary_parts:
                results.append(
                    {
                        "context": "Meta-memory: Knowledge summary",
                        "outcome": ". ".join(summary_parts),
                        "confidence": 1.0,
                        "timestamp": "",
                        "tags": ["meta_memory"],
                        "metadata": {"aggregation": True},
                    }
                )

        # Also get regular facts for context -- include ALL tiered results
        # (tiered retrieval already summarizes, so this is compact enough).
        # meta_memory needs broad coverage to enumerate entities/projects.
        regular_facts = self._simple_retrieval(question)
        results.extend(regular_facts)

        return results

    def _apt_attribution_retrieval(
        self,
        question: str,
        existing_facts: list[dict[str, Any]],
        local_only: bool = False,
    ) -> list[dict[str, Any]]:
        question_lower = question.lower()
        if not self._is_apt_attribution_question(question):
            return []

        candidate_ids = list(self._ENTITY_ID_PATTERN.findall(question))
        relevant_fact_texts: list[str] = []
        for fact in existing_facts[: self._APT_ATTRIBUTION_FACT_SCAN_LIMIT]:
            text = f"{fact.get('context', '')} {fact.get('outcome', fact.get('fact', ''))}"
            text_lower = text.lower()
            if any(cue in text_lower for cue in self._APT_ATTRIBUTION_FACT_CUES):
                relevant_fact_texts.append(text)
                candidate_ids.extend(self._ENTITY_ID_PATTERN.findall(text))

        unique_candidate_ids = list(dict.fromkeys(candidate_ids))[
            : self._APT_ATTRIBUTION_MAX_ENTITY_IDS
        ]
        search_terms = [f"{entity_id} APT" for entity_id in unique_candidate_ids]
        relevant_fact_text = " ".join(relevant_fact_texts)
        relevant_fact_text_lower = relevant_fact_text.lower()
        if not unique_candidate_ids:
            for hint in self._APT_ATTRIBUTION_HINT_TERMS:
                if hint in question_lower or hint in relevant_fact_text_lower:
                    search_terms.append(hint)
        if local_only and not unique_candidate_ids:
            search_terms.extend(self._APT_ATTRIBUTION_SEARCH_TERMS)

        deduped_terms = list(dict.fromkeys(term for term in search_terms if term))[
            : self._APT_ATTRIBUTION_MAX_SEARCH_TERMS
        ]
        new_facts: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for term in deduped_terms:
            results = self._search_memory(
                term, self._APT_ATTRIBUTION_SEARCH_LIMIT, local_only=local_only
            )
            for fact in results:
                if not isinstance(fact, dict):
                    continue
                key = (
                    fact.get("experience_id")
                    or f"{fact.get('context', '')}::{fact.get('outcome', '')}"
                )
                if key in seen_ids:
                    continue
                seen_ids.add(key)
                new_facts.append(fact)
            if self._facts_contain_specific_apt(new_facts):
                break

        has_specific_apt = self._facts_contain_specific_apt(new_facts)

        if local_only and not has_specific_apt:
            logger.info(
                "APT attribution retrieval lacked a specific APT match locally; retrying distributed search "
                "for '%s'",
                question[:60],
            )
            distributed_facts = self._apt_attribution_retrieval(
                question, existing_facts, local_only=False
            )
            for fact in distributed_facts:
                key = (
                    fact.get("experience_id")
                    or f"{fact.get('context', '')}::{fact.get('outcome', '')}"
                )
                if key in seen_ids:
                    continue
                seen_ids.add(key)
                new_facts.append(fact)

        if new_facts:
            logger.info(
                "APT attribution retrieval: %d search terms -> %d facts for '%s'",
                len(deduped_terms),
                len(new_facts),
                question[:60],
            )

        return new_facts

    def _deterministic_meta_memory_answer(
        self, question: str, facts: list[dict[str, Any]]
    ) -> str | None:
        question_lower = question.lower()
        count_like_query = "how many different" in question_lower
        if not count_like_query:
            return None

        if "project" in question_lower:
            projects = self._extract_project_names(facts)
            if projects and len(projects) <= 10:
                logger.info(
                    "Meta-memory deterministic project resolution: %d projects for '%s'",
                    len(projects),
                    question[:60],
                )
                return (
                    f"You told me about {len(projects)} different projects: "
                    f"{self._format_distinct_item_list(projects)}."
                )
            if len(projects) > 10:
                logger.warning(
                    "Skipping deterministic project resolution with suspicious count=%d for '%s'",
                    len(projects),
                    question[:60],
                )

        if "personal details" in question_lower and any(
            token in question_lower for token in ("people", "person")
        ):
            people = self._extract_personal_detail_people(facts)
            if people and len(people) <= 20:
                logger.info(
                    "Meta-memory deterministic people resolution: %d people for '%s'",
                    len(people),
                    question[:60],
                )
                return (
                    f"You shared personal details about {len(people)} people: "
                    f"{self._format_distinct_item_list(people)}."
                )
            if len(people) > 20:
                logger.warning(
                    "Skipping deterministic people resolution with suspicious count=%d for '%s'",
                    len(people),
                    question[:60],
                )

        return None

    def _entity_retrieval(self, question: str, local_only: bool = False) -> list[dict[str, Any]]:
        """Try entity-centric retrieval for questions about specific people/projects.

        Extracts entity names from the question and uses the entity_name index
        for targeted retrieval. Returns empty list if no entities found,
        triggering fallback to iterative retrieval.

        Args:
            question: The question text

        Returns:
            List of fact dicts, or empty list if no entity match
        """
        if not (self.use_hierarchical and hasattr(self.memory, "retrieve_by_entity")):
            return []

        import re

        # Extract proper nouns from question
        # Handles: "Sarah Chen", "O'Brien", "Al-Hassan Ahmed"
        candidates = re.findall(
            r"\b("
            r"[A-Z][a-z]*(?:['\u2019\-][A-Z]?[a-z]+)+(?:\s+(?:[A-Z][a-z]+(?:['\u2019\-][A-Z]?[a-z]+)?))*"
            r"|"
            r"[A-Z][a-z]+(?:\s+(?:[A-Z][a-z]+(?:['\u2019\-][A-Z]?[a-z]+)?))+)"
            r"\b",
            question,
        )

        # Single proper nouns that aren't common words
        if not candidates:
            words = question.split()
            for w in words:
                cleaned = w.strip(".,;:!?()[]{}\"'")
                if cleaned and cleaned[0].isupper() and len(cleaned) > 2:
                    candidates.append(cleaned)

        # Also handle possessives: "Fatima's hobby", "O'Brien's work" -> "Fatima", "O'Brien"
        possessive_matches = re.findall(
            r"\b("
            r"[A-Z][a-z]*(?:['\u2019\-][A-Z]?[a-z]+)+(?:\s+(?:[A-Z][a-z]+(?:['\u2019\-][A-Z]?[a-z]+)?))*"
            r"|"
            r"[A-Z][a-z]+(?:\s+(?:[A-Z][a-z]+(?:['\u2019\-][A-Z]?[a-z]+)?))*"
            r")'s\b",
            question,
        )
        candidates.extend(possessive_matches)

        if not candidates:
            return []

        all_facts: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for candidate in candidates:
            entity_facts = self._retrieve_by_entity_memory(
                candidate,
                ENTITY_FACT_LIMIT,
                local_only=local_only,
            )
            for fact in entity_facts:
                fid = fact.get("experience_id", "")
                if fid not in seen_ids:
                    seen_ids.add(fid)
                    all_facts.append(fact)

        return all_facts if all_facts else []

    def _concept_retrieval(self, question: str, local_only: bool = False) -> list[dict[str, Any]]:
        """Concept-based retrieval fallback for questions without proper nouns.

        Extracts key noun phrases (not proper nouns) from the question using
        stop-word filtering, then searches memory with 2-word and 1-word
        phrases. Returns merged, deduplicated results.

        Args:
            question: The question text

        Returns:
            List of fact dicts, or empty list if no concept matches found
        """
        if not self.use_hierarchical:
            return []

        # Extract content words (non-stop-words, length > 2)
        words = [
            w.strip(".,;:!?()[]{}\"'").lower()
            for w in question.split()
            if w.strip(".,;:!?()[]{}\"'").lower() not in self._STOP_WORDS
            and len(w.strip(".,;:!?()[]{}\"'")) > 2
        ]

        if not words:
            return []

        # Build search phrases: 2-word bigrams first, then individual words
        phrases: list[str] = []
        for i in range(len(words) - 1):
            phrases.append(f"{words[i]} {words[i + 1]}")
        phrases.extend(words)

        all_facts: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        # Try search_by_concept on HierarchicalMemory if available
        if hasattr(self.memory, "search_by_concept"):
            for phrase in phrases[:CONCEPT_PHRASE_LIMIT]:
                concept_facts = self._search_by_concept_memory(
                    keywords=[phrase],
                    limit=CONCEPT_SEARCH_LIMIT,
                    local_only=local_only,
                )
                for fact in concept_facts:
                    fid = fact.get("experience_id", "")
                    if fid and fid not in seen_ids:
                        seen_ids.add(fid)
                        all_facts.append(fact)
        else:
            # Fall back to regular search
            for phrase in phrases[:CONCEPT_PHRASE_LIMIT]:
                results = self._search_memory(
                    phrase,
                    CONCEPT_SEARCH_LIMIT,
                    local_only=local_only,
                )
                for fact in results:
                    fid = fact.get("experience_id", "")
                    if fid and fid not in seen_ids:
                        seen_ids.add(fid)
                        all_facts.append(fact)

        logger.debug(
            "Concept retrieval: %d phrases -> %d facts from question '%s'",
            len(phrases),
            len(all_facts),
            question[:80],
        )
        return all_facts

    def _supplement_simple_retrieval(
        self,
        question: str,
        existing_facts: list[dict[str, Any]],
        local_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Add focused entity/concept hits back into large simple retrievals."""
        existing_keys = {
            f.get("experience_id") or f"{f.get('context', '')}::{f.get('outcome', '')}"
            for f in existing_facts
        }
        supplemented = list(existing_facts)
        added = 0
        is_apt_attribution = self._is_apt_attribution_question(question)

        if is_apt_attribution:
            targeted_facts = self._apt_attribution_retrieval(
                question, existing_facts, local_only=local_only
            )
        else:
            targeted_facts = self._entity_retrieval(question, local_only=local_only)
            targeted_facts.extend(self._concept_retrieval(question, local_only=local_only))
            targeted_facts.extend(
                self._apt_attribution_retrieval(question, existing_facts, local_only=local_only)
            )
            targeted_facts.extend(
                self._infrastructure_relation_retrieval(
                    question,
                    existing_facts + targeted_facts,
                    local_only=local_only,
                )
            )

        if not targeted_facts and local_only:
            logger.info(
                "Simple retrieval supplements empty locally; retrying distributed targeted retrieval "
                "for '%s'",
                question[:60],
            )
            if is_apt_attribution:
                targeted_facts = self._apt_attribution_retrieval(
                    question, existing_facts, local_only=False
                )
            else:
                targeted_facts = self._entity_retrieval(question, local_only=False)
                targeted_facts.extend(self._concept_retrieval(question, local_only=False))
                targeted_facts.extend(
                    self._apt_attribution_retrieval(question, existing_facts, local_only=False)
                )

        for fact in targeted_facts:
            key = (
                fact.get("experience_id") or f"{fact.get('context', '')}::{fact.get('outcome', '')}"
            )
            if key in existing_keys:
                continue
            existing_keys.add(key)
            supplemented.append(fact)
            added += 1

        if added:
            logger.info(
                "Simple retrieval supplements: added %d targeted facts for '%s'",
                added,
                question[:60],
            )

        return supplemented

    def _infrastructure_relation_retrieval(
        self,
        question: str,
        existing_facts: list[dict[str, Any]],
        local_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Follow infrastructure relation targets (e.g. subnet -> CIDR) for specificity."""
        q_lower = question.lower()
        relation_patterns: tuple[re.Pattern[str], ...] = ()
        if "subnet" in q_lower:
            relation_patterns = self._INFRASTRUCTURE_RELATION_PATTERNS["subnet"]

        if not relation_patterns:
            return []

        existing_ids = {
            f.get("experience_id") or f"{f.get('context', '')}::{f.get('outcome', '')}"
            for f in existing_facts
        }
        candidate_names: list[str] = []
        seen_candidates: set[str] = set()

        for fact in existing_facts:
            fact_text = f"{fact.get('context', '')} {fact.get('outcome', '')}"
            for pattern in relation_patterns:
                for match in pattern.finditer(fact_text):
                    candidate = match.group(1).strip(" '\".,:;()")
                    if not candidate or candidate.casefold() in seen_candidates:
                        continue
                    if candidate.casefold() in {"subnet", "named", "in", "the", "on", "for"}:
                        continue
                    seen_candidates.add(candidate.casefold())
                    candidate_names.append(candidate)

        new_facts: list[dict[str, Any]] = []
        for candidate in candidate_names:
            results = self._retrieve_by_entity_memory(
                candidate,
                ENTITY_SEARCH_LIMIT,
                local_only=local_only,
            )
            if not results and local_only:
                results = self._retrieve_by_entity_memory(
                    candidate,
                    ENTITY_SEARCH_LIMIT,
                    local_only=False,
                )
            for fact in results:
                key = (
                    fact.get("experience_id")
                    or f"{fact.get('context', '')}::{fact.get('outcome', '')}"
                )
                if key in existing_ids:
                    continue
                existing_ids.add(key)
                new_facts.append(fact)

        if new_facts:
            logger.info(
                "Infrastructure relation retrieval: %d related facts for '%s'",
                len(new_facts),
                question[:60],
            )

        return new_facts

    def _search_memory(
        self, query: str, limit: int, local_only: bool = False
    ) -> list[dict[str, Any]]:
        """Search memory, optionally forcing a local-only path."""
        if local_only and hasattr(self.memory, "search_local"):
            return self.memory.search_local(query=query, limit=limit)
        if hasattr(self.memory, "search"):
            return self.memory.search(query=query, limit=limit)
        return []

    def _search_by_concept_memory(
        self, keywords: list[str], limit: int, local_only: bool = False
    ) -> list[Any]:
        """Search by concept, optionally forcing a local-only path."""
        if local_only and hasattr(self.memory, "search_by_concept_local"):
            return self.memory.search_by_concept_local(keywords=keywords, limit=limit)
        if hasattr(self.memory, "search_by_concept"):
            return self.memory.search_by_concept(keywords=keywords, limit=limit)
        return []

    def _retrieve_by_entity_memory(
        self, entity_name: str, limit: int, local_only: bool = False
    ) -> list[dict[str, Any]]:
        """Retrieve entity-linked facts, optionally forcing a local-only path."""
        if local_only and hasattr(self.memory, "retrieve_by_entity_local"):
            return self.memory.retrieve_by_entity_local(entity_name=entity_name, limit=limit)
        if hasattr(self.memory, "retrieve_by_entity"):
            return self.memory.retrieve_by_entity(entity_name=entity_name, limit=limit)
        return []

    def _entity_linked_retrieval(
        self,
        question: str,
        existing_facts: list[dict[str, Any]],
        local_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Retrieve all facts linked to entity IDs found in the question.

        When the question mentions structured IDs like INC-2024-001 or
        CVE-2024-3094, searches memory for ALL facts containing those IDs.
        This catches related facts stored under different context tags
        (e.g. CVE details stored separately from incident timeline).

        For incident/CVE questions, uses deeper retrieval limits (200 instead
        of 30) and performs a second targeted search per entity ID to capture
        ALL associated facts that may be stored under different contexts.

        Args:
            question: The question text
            existing_facts: Already-retrieved facts to merge with

        Returns:
            Merged, deduplicated list of facts including entity-linked ones
        """
        entity_ids = self._ENTITY_ID_PATTERN.findall(question)
        if not entity_ids:
            return existing_facts

        existing_ids = {
            f.get("experience_id", "") for f in existing_facts if f.get("experience_id")
        }
        new_facts: list[dict[str, Any]] = []

        # Deeper limits for incident/CVE queries to capture ALL associations
        q_lower = question.lower()
        is_incident_query = any(
            kw in q_lower for kw in ("incident", "cve", "vulnerability", "security")
        )
        search_limit = INCIDENT_QUERY_SEARCH_LIMIT if is_incident_query else ENTITY_SEARCH_LIMIT

        for entity_id in entity_ids:
            # Search by text content for any fact mentioning the entity ID
            results = self._search_memory(entity_id, search_limit, local_only=local_only)
            for fact in results:
                fid = fact.get("experience_id", "")
                if fid and fid not in existing_ids:
                    existing_ids.add(fid)
                    new_facts.append(fact)

            # Also try entity retrieval if available (different index path)
            results = self._retrieve_by_entity_memory(
                entity_id,
                search_limit,
                local_only=local_only,
            )
            for fact in results:
                fid = fact.get("experience_id", "")
                if fid and fid not in existing_ids:
                    existing_ids.add(fid)
                    new_facts.append(fact)

            # Second targeted search: search for JUST the entity ID as an
            # exact string to find facts where the ID appears in a different
            # field (e.g., a CVE referenced in an incident fact's outcome).
            # This catches cross-entity associations that the first search
            # may miss due to embedding-based similarity ranking.
            if is_incident_query:
                # Use concept search if available for exact matching
                concept_results = self._search_by_concept_memory(
                    keywords=[entity_id],
                    limit=CONCEPT_EXACT_SEARCH_LIMIT,
                    local_only=local_only,
                )
                for node in concept_results:
                    if isinstance(node, dict):
                        fid = node.get("experience_id", "")
                        if fid and fid not in existing_ids:
                            existing_ids.add(fid)
                            new_facts.append(node)
                        continue

                    fid = getattr(node, "node_id", "")
                    if fid and fid not in existing_ids:
                        existing_ids.add(fid)
                        new_facts.append(
                            {
                                "context": getattr(node, "concept", ""),
                                "outcome": getattr(node, "content", ""),
                                "confidence": getattr(node, "confidence", 0.8),
                                "experience_id": fid,
                                "tags": getattr(node, "tags", []),
                                "metadata": getattr(node, "metadata", {}),
                            }
                        )

        if new_facts:
            logger.info(
                "Entity-linked retrieval: %d IDs -> %d new facts (limit=%d) for '%s'",
                len(entity_ids),
                len(new_facts),
                search_limit,
                question[:60],
            )
        elif local_only:
            logger.info(
                "Entity-linked retrieval empty locally; retrying distributed ID search for '%s'",
                question[:60],
            )
            return self._entity_linked_retrieval(question, existing_facts, local_only=False)

        return existing_facts + new_facts

    def _multi_entity_retrieval(
        self,
        question: str,
        existing_facts: list[dict[str, Any]],
        local_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Chain-aware retrieval for questions mentioning multiple entities.

        When a question references 2+ named entities or structured IDs,
        runs separate retrieval for each entity and merges results. This
        ensures multi-hop questions get facts from all relevant entities
        rather than only the first one matched.

        Args:
            question: The question text
            existing_facts: Already-retrieved facts

        Returns:
            Merged, deduplicated facts from all entities
        """
        # Collect entity names (proper nouns)
        name_candidates = re.findall(
            r"\b("
            r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+"
            r")\b",
            question,
        )
        # Collect structured IDs
        id_candidates = self._ENTITY_ID_PATTERN.findall(question)

        all_entities = list(set(name_candidates + id_candidates))
        if len(all_entities) < 2:
            return existing_facts

        existing_ids = {
            f.get("experience_id", "") for f in existing_facts if f.get("experience_id")
        }
        new_facts: list[dict[str, Any]] = []

        for entity in all_entities:
            # Try entity retrieval
            results = self._retrieve_by_entity_memory(
                entity,
                MULTI_ENTITY_LIMIT,
                local_only=local_only,
            )
            for fact in results:
                fid = fact.get("experience_id", "")
                if fid and fid not in existing_ids:
                    existing_ids.add(fid)
                    new_facts.append(fact)

            # Also try text search for IDs
            if self._ENTITY_ID_PATTERN.match(entity):
                results = self._search_memory(
                    entity,
                    ENTITY_ID_TEXT_SEARCH_LIMIT,
                    local_only=local_only,
                )
                for fact in results:
                    fid = fact.get("experience_id", "")
                    if fid and fid not in existing_ids:
                        existing_ids.add(fid)
                        new_facts.append(fact)

        if new_facts:
            logger.info(
                "Multi-entity retrieval: %d entities -> %d new facts for '%s'",
                len(all_entities),
                len(new_facts),
                question[:60],
            )

        return existing_facts + new_facts

    def _filter_facts_by_source_reference(
        self, question: str, facts: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Filter facts to those from a specific source referenced in the question.

        When a question mentions a specific article (e.g., "mentioned in the athlete
        achievements article"), extract the source name and filter facts that have
        a matching source_label in their metadata.

        Args:
            question: The question text
            facts: List of all retrieved fact dicts

        Returns:
            Filtered list of facts from the referenced source, or empty list
            if no specific source is referenced in the question.
        """
        q_lower = question.lower()
        # Common patterns: "mentioned in the X article", "from the X article", "in the X"
        source_keywords = []
        for pattern in ("mentioned in the ", "from the ", "in the ", "according to the "):
            idx = q_lower.find(pattern)
            if idx >= 0:
                after = q_lower[idx + len(pattern) :]
                # Extract until "article", "report", "source", or end of phrase
                for end_word in ("article", "report", "source", "piece", "?"):
                    end_idx = after.find(end_word)
                    if end_idx > 0:
                        source_keywords.append(after[:end_idx].strip())
                        break

        if not source_keywords:
            return []

        # Find facts whose source_label matches any keyword
        matched = []
        for fact in facts:
            meta = fact.get("metadata", {})
            source = (meta.get("source_label", "") or "").lower()
            if any(kw in source for kw in source_keywords if kw):
                matched.append(fact)

        logger.debug(
            "Source filter: keywords=%s, matched %d/%d facts",
            source_keywords,
            len(matched),
            len(facts),
        )
        return matched

    def _get_summary_nodes(self) -> list[dict[str, Any]]:
        """Retrieve SUMMARY concept map nodes from memory.

        Returns:
            List of summary fact dicts with context and outcome fields.
        """
        if not (self.use_hierarchical and hasattr(self.memory, "memory")):
            return []

        try:
            result = self.memory.memory.connection.execute(
                """
                MATCH (m:SemanticMemory)
                WHERE m.agent_id = $agent_id AND m.concept = 'SUMMARY'
                RETURN m.memory_id, m.concept, m.content, m.confidence
                ORDER BY m.created_at DESC
                LIMIT 5
                """,
                {"agent_id": self.agent_name},
            )

            summaries = []
            while result.has_next():
                row = result.get_next()
                summaries.append(
                    {
                        "context": row[1],
                        "outcome": row[2],
                        "confidence": row[3],
                    }
                )
            return summaries

        except Exception as e:
            logger.debug("Failed to retrieve summary nodes: %s", e)
            return []

    async def _keyword_expanded_retrieval(
        self,
        question: str,
        existing_facts: list[dict[str, Any]],
        local_only: bool = False,
    ) -> list[dict[str, Any]]:
        """Expand retrieval with LLM-generated keyword phrases when initial retrieval is sparse.

        For large KBs (>500 facts), if the initial retrieval returned <3 facts,
        use the LLM to generate alternative search phrases and search memory for
        each, merging results with existing facts.

        Args:
            question: The user's question
            existing_facts: Facts already retrieved

        Returns:
            Merged list of facts (existing + newly found), deduplicated by experience_id.
        """
        prompt = _load_prompt("keyword_expansion_user", question=question)

        try:
            response_text = (
                await _get_llm_completion()(
                    [
                        {
                            "role": "system",
                            "content": load_prompt("keyword_expansion_system"),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    model=self.model,
                    temperature=0.0,
                )
            ).strip()
            try:
                phrases = json.loads(response_text)
            except json.JSONDecodeError:
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    phrases = json.loads(response_text[json_start:json_end].strip())
                else:
                    return existing_facts

            if not isinstance(phrases, list):
                return existing_facts

            # Collect existing experience_ids for deduplication
            seen_ids: set[str] = set()
            for f in existing_facts:
                eid = f.get("experience_id", "")
                if eid:
                    seen_ids.add(eid)

            new_facts = list(existing_facts)
            for phrase in phrases[:5]:
                if not isinstance(phrase, str) or not phrase.strip():
                    continue
                results = self._search_memory(phrase.strip(), limit=10, local_only=local_only)
                for fact in results:
                    eid = fact.get("experience_id", "")
                    if eid and eid not in seen_ids:
                        seen_ids.add(eid)
                        new_facts.append(fact)

            logger.debug(
                "Keyword expansion: %d phrases, %d->%d facts",
                len(phrases),
                len(existing_facts),
                len(new_facts),
            )
            return new_facts

        except Exception as e:
            logger.debug("_keyword_expanded_retrieval failed: %s", e)
            return existing_facts

