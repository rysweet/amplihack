from __future__ import annotations

"""Temporal state tracking, transition chains, and chronological reasoning."""

import itertools
import logging
import re
from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class TemporalReasoningMixin:
    """Mixin providing temporal reasoning for LearningAgent."""

    # Keyword-to-index mapping for temporal state resolution
    _TEMPORAL_KEYWORDS: dict[str, str] = {
        "first": "0",
        "original": "0",
        "initial": "0",
        "second": "1",
        "third": "2",
        "intermediate": "len(transitions) // 2",
        "middle": "len(transitions) // 2",
        "between": "len(transitions) // 2",
        "latest": "-1",
        "current": "-1",
        "final": "-1",
        "last": "-1",
    }

    # Temporal pattern constants
    _TEMPORAL_DATE_VALUE_PATTERN = re.compile(
        r"\b("
        r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{1,2}(?:,\s+\d{4})?"
        r")\b"
    )
    _DEADLINE_DIRECT_VALUE_PATTERNS = (
        re.compile(
            r"\b(?:current|latest|final|last|original|initial)\s+deadline\s+"
            r"(?:is|was|of)\s+(?P<fragment>.+)$",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bdeadline\s+(?:is|was|of)\s+(?P<fragment>.+)$",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bdeadline\s+(?:has\s+been\s+)?(?:changed|moved|pushed|extended|updated)"
            r"(?:\s+again)?\s+to\s+(?P<fragment>.+)$",
            re.IGNORECASE,
        ),
        re.compile(
            r"\btarget\s+(?:delivery\s+)?date\s+(?:is|was|of)\s+(?P<fragment>.+)$",
            re.IGNORECASE,
        ),
    )
    _DIRECT_TEMPORAL_LOOKUP_PATTERN = re.compile(
        r"^\s*(?:what|who)\s+(?:is|was)\s+the\s+"
        r"(?P<qualifier>current|latest|original|initial|previous|final|last)\s+"
        r"(?P<field>.+?)\s+(?:for|of)\s+(?P<entity>.+?)\s*\??\s*$",
        re.IGNORECASE,
    )
    _DIRECT_TEMPORAL_ENTITY_TRAIL_PATTERN = re.compile(
        r"\s+\b(?:before|after|when|as of)\b.*$",
        re.IGNORECASE,
    )

    def _transition_chain_from_facts(
        self, entity: str, field: str, facts: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Extract a temporal transition chain from candidate facts."""
        entity_lower = entity.lower()
        field_lower = field.lower()
        chain: list[dict[str, Any]] = []
        seen_keys: set[tuple[str, str, int, str, bool]] = set()

        for fact_index, fact in enumerate(facts):
            context = fact.get("context", "").lower()
            outcome = fact.get("outcome", fact.get("fact", ""))
            combined = f"{context} {str(outcome).lower()}"
            if entity_lower not in combined or field_lower not in combined:
                continue

            meta = fact.get("metadata", {}) or {}
            timestamp = fact.get("timestamp", "")
            temporal_index = int(meta.get("temporal_index", 0) or 0)
            experience_id = str(fact.get("experience_id", "") or fact.get("id", "") or "")
            if not experience_id:
                experience_id = f"fact-{fact_index}"
            extracted_values = self._extract_temporal_state_values(str(outcome), field)

            if len(extracted_values) > 1:
                for offset, state_value in enumerate(extracted_values):
                    state_superseded = offset < len(extracted_values) - 1 or bool(
                        meta.get("superseded", False)
                    )
                    dedupe_key = (
                        experience_id,
                        state_value.casefold(),
                        temporal_index,
                        timestamp,
                        state_superseded,
                    )
                    if dedupe_key in seen_keys:
                        continue
                    seen_keys.add(dedupe_key)
                    chain.append(
                        {
                            "value": state_value,
                            "timestamp": timestamp,
                            "temporal_index": temporal_index,
                            "experience_id": experience_id,
                            "sequence_position": offset,
                            "superseded": state_superseded,
                            "metadata": {
                                **meta,
                                "experience_id": experience_id,
                                "temporal_index": temporal_index,
                                "sequence_position": offset,
                                "superseded": state_superseded,
                            },
                        }
                    )
                continue

            if not extracted_values and field_lower in {"date", "deadline"}:
                continue

            atomic_value = extracted_values[0] if extracted_values else str(outcome)
            superseded = bool(meta.get("superseded", False))
            dedupe_key = (
                experience_id,
                atomic_value.casefold(),
                temporal_index,
                timestamp,
                superseded,
            )
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)
            chain.append(
                {
                    "value": atomic_value,
                    "timestamp": timestamp,
                    "temporal_index": temporal_index,
                    "experience_id": experience_id,
                    "sequence_position": 0,
                    "superseded": superseded,
                    "metadata": meta,
                }
            )

        chain.sort(
            key=lambda x: (x.get("timestamp", ""), x["temporal_index"], x["sequence_position"])
        )
        return chain

    def retrieve_transition_chain(
        self, entity: str, field: str, candidate_facts: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """Retrieve all SUPERSEDED states for an entity/field from memory.

        Queries memory for all facts related to the entity and field,
        filters to those with superseded metadata, and returns them
        in chronological order (oldest first, current last).

        Args:
            entity: Entity name (e.g., "Atlas project")
            field: Field name (e.g., "deadline")

        Returns:
            List of state dicts ordered chronologically, each with
            'value', 'timestamp', and 'metadata' keys.
        """
        if candidate_facts:
            chain = self._transition_chain_from_facts(entity, field, candidate_facts)
            if chain:
                return chain

        if not hasattr(self.memory, "search"):
            return []

        # Use targeted search instead of get_all_facts to avoid memory leak
        # (get_all_facts with limit=15000 caused 89GB RAM usage during 5000-turn eval)
        query = f"{entity} {field}"
        matching_facts = self.memory.search(query=query, limit=100)
        return self._transition_chain_from_facts(entity, field, matching_facts)

    @classmethod
    def _extract_temporal_state_values(cls, value: str, field: str) -> list[str]:
        cleaned_value = re.sub(r"\*+", "", value).strip()
        if not cleaned_value:
            return []

        field_lower = field.casefold()
        if field_lower in {"date", "deadline"}:
            from_to_match = re.search(r"\bfrom\s+(.+?)\s+to\s+(.+)", cleaned_value, re.IGNORECASE)
            if from_to_match:
                ordered: list[str] = []
                seen: set[str] = set()
                sequence = re.sub(r"(?i)^from\s+", "", from_to_match.group(0))
                for part in re.split(r"\s+to\s+", sequence):
                    match = cls._TEMPORAL_DATE_VALUE_PATTERN.search(part)
                    if not match:
                        continue
                    candidate = match.group(0)
                    key = candidate.casefold()
                    if key in seen:
                        continue
                    seen.add(key)
                    ordered.append(candidate)
                if len(ordered) > 1:
                    return ordered

            if field_lower == "deadline":
                for pattern in cls._DEADLINE_DIRECT_VALUE_PATTERNS:
                    direct_match = pattern.search(cleaned_value)
                    if not direct_match:
                        continue
                    fragment = direct_match.group("fragment")
                    date_match = cls._TEMPORAL_DATE_VALUE_PATTERN.search(fragment)
                    if date_match:
                        return [date_match.group(0)]

            matches = cls._TEMPORAL_DATE_VALUE_PATTERN.findall(cleaned_value)
            if len(matches) == 1:
                ordered: list[str] = []
                seen: set[str] = set()
                for match in matches:
                    key = match.casefold()
                    if key in seen:
                        continue
                    seen.add(key)
                    ordered.append(match)
                return ordered
            return []

        return [cleaned_value]

    def _collapse_change_count_transitions(
        self, transitions: list[dict[str, Any]], field: str
    ) -> list[dict[str, Any]]:
        seen_values: set[str] = set()
        collapsed_transitions: list[dict[str, Any]] = []

        for transition in transitions:
            state_values = self._extract_temporal_state_values(transition.get("value", ""), field)
            if not state_values:
                continue

            for state_value in state_values:
                key = state_value.casefold()
                if key in seen_values:
                    continue
                seen_values.add(key)
                collapsed_transitions.append({**transition, "value": state_value})

        return collapsed_transitions or transitions

    @staticmethod
    def _collapse_temporal_lookup_transitions(
        transitions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        representatives: dict[str, dict[str, Any]] = {}
        first_seen: dict[str, int] = {}
        adjacency: dict[str, set[str]] = defaultdict(set)
        indegree: dict[str, int] = {}
        grouped_sequences: dict[str, list[tuple[int, int, str]]] = defaultdict(list)

        for index, transition in enumerate(transitions):
            state_value = str(transition.get("value", "")).strip()
            if not state_value:
                continue

            key = state_value.casefold()
            if key not in representatives:
                representatives[key] = transition
                first_seen[key] = index
            indegree.setdefault(key, 0)

            experience_id = str(
                transition.get("experience_id")
                or transition.get("metadata", {}).get("experience_id")
                or f"transition-{index}"
            )
            grouped_sequences[experience_id].append(
                (int(transition.get("sequence_position", 0) or 0), index, key)
            )

        for sequence in grouped_sequences.values():
            ordered_keys: list[str] = []
            for _, _, key in sorted(sequence):
                if ordered_keys and ordered_keys[-1] == key:
                    continue
                ordered_keys.append(key)

            for previous_key, next_key in itertools.pairwise(ordered_keys):
                if previous_key == next_key or next_key in adjacency[previous_key]:
                    continue
                adjacency[previous_key].add(next_key)
                indegree[next_key] = indegree.get(next_key, 0) + 1

        ready = sorted(
            (key for key, degree in indegree.items() if degree == 0),
            key=lambda key: first_seen[key],
        )
        ordered_keys: list[str] = []
        while ready:
            key = ready.pop(0)
            ordered_keys.append(key)
            for next_key in sorted(
                adjacency.get(key, ()), key=lambda candidate: first_seen[candidate]
            ):
                indegree[next_key] -= 1
                if indegree[next_key] == 0:
                    insert_at = 0
                    while (
                        insert_at < len(ready)
                        and first_seen[ready[insert_at]] <= first_seen[next_key]
                    ):
                        insert_at += 1
                    ready.insert(insert_at, next_key)

        if len(ordered_keys) != len(indegree):
            ordered_keys = sorted(representatives, key=lambda key: first_seen[key])

        return [representatives[key] for key in ordered_keys] or transitions

    @classmethod
    def _format_temporal_lookup_answer(
        cls,
        question: str,
        temporal_code: dict[str, Any] | None,
    ) -> str:
        result = str((temporal_code or {}).get("result", "")).strip()
        if not result:
            return result

        match = cls._DIRECT_TEMPORAL_LOOKUP_PATTERN.match(question.strip())
        if not match:
            return result

        field = re.sub(r"\s+", " ", match.group("field")).strip(" .?!")
        entity = cls._DIRECT_TEMPORAL_ENTITY_TRAIL_PATTERN.sub("", match.group("entity"))
        entity = re.sub(r"\s+", " ", entity).strip(" .?!")
        qualifier = match.group("qualifier").lower()
        transitions = list((temporal_code or {}).get("transitions") or [])
        history_clause = ""

        if qualifier in {"current", "latest", "final", "last"}:
            descriptor = "current"
            verb = "is"
            unique_values: list[str] = []
            seen_values: set[str] = set()
            for transition in transitions:
                value = str(transition.get("value", "")).strip()
                if not value:
                    continue
                key = value.casefold()
                if key in seen_values:
                    continue
                seen_values.add(key)
                unique_values.append(value)
            if unique_values and unique_values[-1].casefold() != result.casefold():
                unique_values.append(result)
            history_values = list(reversed(unique_values[:-1]))
            if history_values:
                history_parts = [
                    ("changed from " if index == 0 else "which was changed from ") + value
                    for index, value in enumerate(history_values)
                ]
                history_clause = f" ({', '.join(history_parts)})"
        elif qualifier in {"original", "initial"}:
            descriptor = "original"
            verb = "was"
        else:
            descriptor = qualifier
            verb = "was"

        return f"The {descriptor} {field} for {entity} {verb} {result}{history_clause}."

    def _parse_temporal_index(self, question: str) -> str:
        """Parse a temporal question to determine which state index is requested.

        Scans the question for temporal keywords and maps them to a
        Python index expression.

        Args:
            question: The temporal question text

        Returns:
            A Python index expression string (e.g., "0", "-1",
            "len(transitions) // 2").
        """
        question_lower = question.lower()

        # Check "AFTER first BUT BEFORE second" pattern -> index 1
        after_before = re.search(
            r"after\s+(?:the\s+)?first.*?(?:but\s+)?before\s+(?:the\s+)?(?:second|final|last)",
            question_lower,
        )
        if after_before:
            return "1"

        # Check "BEFORE the first" / "BEFORE any" -> index 0 (original)
        before_first = re.search(
            r"before\s+(?:the\s+)?(?:first|any)\s+(?:change|update|modification)",
            question_lower,
        )
        if before_first:
            return "0"

        # Check "AFTER the Nth" pattern
        after_nth = re.search(r"after\s+(?:the\s+)?(\w+)\s+(?:change|update)", question_lower)
        if after_nth:
            ordinal = after_nth.group(1)
            ordinal_map = {"first": "1", "second": "2", "third": "3"}
            if ordinal in ordinal_map:
                return ordinal_map[ordinal]

        # Check "BEFORE the final/last" -> second-to-last
        before_final = re.search(
            r"before\s+(?:the\s+)?(?:final|last|latest)\s+(?:change|update|value)",
            question_lower,
        )
        if before_final:
            return "-2"

        # Simple keyword match
        for keyword, index_expr in self._TEMPORAL_KEYWORDS.items():
            if keyword in question_lower:
                return index_expr

        # Default: latest value
        return "-1"

    @classmethod
    def _heuristic_temporal_entity_field(cls, question: str) -> tuple[str, str] | None:
        """Extract entity/field from direct temporal lookup questions without an LLM."""
        match = cls._DIRECT_TEMPORAL_LOOKUP_PATTERN.match(question.strip())
        if not match:
            return None

        field = re.sub(r"\s+", " ", match.group("field")).strip(" .?!")
        entity = cls._DIRECT_TEMPORAL_ENTITY_TRAIL_PATTERN.sub("", match.group("entity"))
        entity = re.sub(r"\s+", " ", entity).strip(" .?!")
        if not entity or not field:
            return None

        return entity, field

    @classmethod
    def _should_short_circuit_temporal_answer(
        cls, question: str, temporal_code: dict[str, Any] | None
    ) -> bool:
        """Return direct deterministic temporal lookups instead of re-synthesizing."""
        if not temporal_code or temporal_code.get("result") is None:
            return False
        if temporal_code.get("operation") != "state_lookup":
            return False
        return bool(cls._DIRECT_TEMPORAL_LOOKUP_PATTERN.match(question.strip()))
