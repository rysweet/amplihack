from __future__ import annotations

"""Content ingestion, fact extraction, and storage logic."""

import json
import logging
import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from .prompt_utils import _get_llm_completion, _load_prompt
from .prompts import load_prompt

logger = logging.getLogger(__name__)


class LearningIngestionMixin:
    """Mixin providing content ingestion for LearningAgent."""

    async def learn_from_content(self, content: str) -> dict[str, Any]:
        """Learn from content by extracting and storing facts.

        When use_hierarchical=True, stores the raw content as an episode first,
        then extracts facts with source_id pointing to the episode for provenance.
        Detects temporal markers in content and attaches temporal metadata to facts.

        Args:
            content: Article or content text

        Returns:
            Dictionary with learning results:
                - facts_extracted: Number of facts extracted
                - facts_stored: Number of facts stored
                - content_summary: Summary of content

        Example:
            >>> agent = LearningAgent()
            >>> result = agent.learn_from_content(
            ...     "Photosynthesis converts light into chemical energy."
            ... )
            >>> print(result['facts_extracted'])  # 1
        """
        batch = await self.prepare_fact_batch(content)
        return self.store_fact_batch(batch, record_learning=True)

    @staticmethod
    def _truncate_learning_content(content: str) -> str:
        """Trim oversized learning content to the safe maximum length."""
        max_content_length = 50_000
        if len(content) > max_content_length:
            logger.warning(
                "Content truncated from %d to %d chars", len(content), max_content_length
            )
            return content[:max_content_length]
        return content

    @staticmethod
    def _extract_source_label(content: str) -> str:
        """Derive a stable source label from content title or leading text."""
        if content.startswith("Title: "):
            title_end = content.find("\n")
            if title_end > 0:
                return content[7:title_end].strip()
        return content[:60].strip()

    def _build_store_fact_kwargs(
        self,
        fact: dict[str, Any],
        temporal_meta: dict[str, Any],
        source_label: str,
    ) -> dict[str, Any]:
        """Build the final store_fact kwargs for one extracted fact."""
        tags = fact.get("tags", ["learned"])
        if temporal_meta.get("source_date"):
            tags = list(tags) + [f"date:{temporal_meta['source_date']}"]
        if temporal_meta.get("temporal_order"):
            tags = list(tags) + [f"time:{temporal_meta['temporal_order']}"]

        store_kwargs: dict[str, Any] = {
            "context": fact["context"],
            "fact": fact["fact"],
            "confidence": fact.get("confidence", 0.8),
            "tags": tags,
        }

        if self.use_hierarchical:
            fact_metadata = {}
            if temporal_meta:
                fact_metadata.update(temporal_meta)
            if source_label:
                fact_metadata["source_label"] = source_label
            if fact_metadata:
                store_kwargs["temporal_metadata"] = fact_metadata

        return store_kwargs

    async def _build_summary_store_kwargs(
        self, facts: list[dict[str, Any]]
    ) -> dict[str, Any] | None:
        """Generate SUMMARY-node store kwargs for a learned fact batch."""
        fact_list = "\n".join(
            f"- [{f.get('context', 'General')}] {f.get('fact', '')}" for f in facts[:15]
        )

        prompt = _load_prompt("concept_map_user", fact_list=fact_list)
        try:
            summary = (
                await _get_llm_completion()(
                    [
                        {
                            "role": "system",
                            "content": load_prompt("concept_map_system"),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    model=self.model,
                    temperature=0.2,
                )
            ).strip()
            return {
                "context": "SUMMARY",
                "fact": summary,
                "confidence": 0.95,
                "tags": ["summary", "concept_map"],
            }
        except Exception as e:
            logger.debug("Failed to generate summary concept map: %s", e)
            return None

    async def prepare_fact_batch(
        self, content: str, include_summary: bool = True
    ) -> dict[str, Any]:
        """Extract a content batch once so peers can store facts directly.

        The returned payload contains only direct-storage kwargs plus enough
        provenance metadata for each receiving agent to store its own episode.
        """
        if not content or not content.strip():
            return {
                "facts_extracted": 0,
                "facts": [],
                "summary_fact": None,
                "content_summary": "Empty content",
                "perception": "",
                "episode_content": "",
                "source_label": "",
            }

        content = self._truncate_learning_content(content)
        temporal_meta = await self._detect_temporal_metadata(content)
        source_label = self._extract_source_label(content)
        facts = await self._extract_facts_with_llm(content, temporal_meta)

        prepared_facts: list[dict[str, Any]] = []
        for fact in facts:
            try:
                prepared_facts.append(
                    self._build_store_fact_kwargs(fact, temporal_meta, source_label)
                )
            except Exception as e:
                logger.warning("Failed to prepare fact for storage: %s", e)
                continue

        summary_store_kwargs = None
        if include_summary and facts and prepared_facts:
            summary_store_kwargs = await self._build_summary_store_kwargs(facts)

        return {
            "facts_extracted": len(facts),
            "facts": prepared_facts,
            "summary_fact": summary_store_kwargs,
            "content_summary": content[:200],
            "perception": content[:500],
            "episode_content": content[:2000]
            if self.use_hierarchical and hasattr(self.memory, "store_episode")
            else "",
            "source_label": source_label,
        }

    def store_fact_batch(
        self, batch: dict[str, Any], record_learning: bool = False
    ) -> dict[str, Any]:
        """Store a prepared fact batch without re-running extraction LLM calls."""
        prepared_facts = [dict(fact) for fact in batch.get("facts", []) if isinstance(fact, dict)]
        summary_fact = batch.get("summary_fact")
        summary_store_kwargs = dict(summary_fact) if isinstance(summary_fact, dict) else None

        if record_learning:
            perception = str(batch.get("perception", ""))[:500]
            if perception:
                self.loop.observe(perception)

        episode_id = ""
        if self.use_hierarchical and hasattr(self.memory, "store_episode"):
            episode_content = str(batch.get("episode_content", ""))
            if episode_content:
                try:
                    episode_id = self.memory.store_episode(
                        content=episode_content,
                        source_label=str(batch.get("source_label", "")),
                    )
                except Exception as e:
                    logger.warning("Failed to store episode for provenance: %s", e)

        stored_count = 0
        for store_kwargs in prepared_facts:
            try:
                if self.use_hierarchical and episode_id and "source_id" not in store_kwargs:
                    store_kwargs["source_id"] = episode_id
                self.memory.store_fact(**store_kwargs)
                stored_count += 1
            except Exception as e:
                logger.warning("Failed to store fact: %s", e)
                continue

        if summary_store_kwargs:
            try:
                if self.use_hierarchical and episode_id and "source_id" not in summary_store_kwargs:
                    summary_store_kwargs["source_id"] = episode_id
                self.memory.store_fact(**summary_store_kwargs)
            except Exception as e:
                logger.debug("Failed to store summary concept map: %s", e)

        if record_learning:
            self.loop.learn(
                perception=str(batch.get("perception", ""))[:500],
                reasoning="Extracted facts from content",
                action={"action": "learn", "params": {"stored": stored_count}},
                outcome=(
                    f"Extracted {int(batch.get('facts_extracted', len(prepared_facts)))} "
                    f"facts, stored {stored_count}"
                ),
            )

        return {
            "facts_extracted": int(batch.get("facts_extracted", len(prepared_facts))),
            "facts_stored": stored_count,
            "content_summary": str(batch.get("content_summary", "")),
        }

    async def _store_summary_concept_map(
        self, content: str, facts: list[dict], episode_id: str = ""
    ) -> None:
        """Generate and store a summary concept map for knowledge organization.

        Uses one LLM call to create a brief organizational overview of what
        was learned from the content. Stored as a SUMMARY node to help the
        agent explain the overall structure of its knowledge.

        Args:
            content: Original content that was learned
            facts: List of extracted fact dicts
            episode_id: Optional source episode ID
        """
        del content  # Summary depends only on extracted facts, not raw text.
        store_kwargs = await self._build_summary_store_kwargs(facts)
        if store_kwargs is None:
            return
        try:
            if self.use_hierarchical and episode_id:
                store_kwargs["source_id"] = episode_id
            self.memory.store_fact(**store_kwargs)
            logger.debug("Stored summary concept map: %s", store_kwargs["fact"][:100])
        except Exception as e:
            logger.debug("Failed to store summary concept map: %s", e)

    @staticmethod
    def _detect_temporal_metadata_fast(content: str) -> dict[str, Any] | None:
        """Extract obvious temporal metadata directly from the source text."""
        timestamp_match = re.search(
            r"\bTimestamp:\s*(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?",
            content,
            re.IGNORECASE,
        )
        if timestamp_match:
            source_date = timestamp_match.group(1)
            hour = timestamp_match.group(2) or "00"
            minute = timestamp_match.group(3) or "00"
            second = timestamp_match.group(4) or "00"
            temporal_order = f"{source_date} {hour}:{minute}:{second}"
            temporal_index = int(f"{source_date.replace('-', '')}{hour}{minute}{second}")
            return {
                "source_date": source_date,
                "temporal_order": temporal_order,
                "temporal_index": temporal_index,
            }

        iso_date_match = re.search(
            r"\b(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}):(\d{2})(?::(\d{2}))?)?\b",
            content,
        )
        if iso_date_match:
            source_date = iso_date_match.group(1)
            hour = iso_date_match.group(2) or "00"
            minute = iso_date_match.group(3) or "00"
            second = iso_date_match.group(4) or "00"
            temporal_order = (
                f"{source_date} {hour}:{minute}:{second}"
                if iso_date_match.group(2)
                else source_date
            )
            temporal_index = int(f"{source_date.replace('-', '')}{hour}{minute}{second}")
            return {
                "source_date": source_date,
                "temporal_order": temporal_order,
                "temporal_index": temporal_index,
            }

        day_match = re.search(r"\bDay\s+(\d{1,4})\b", content, re.IGNORECASE)
        if day_match:
            day = int(day_match.group(1))
            return {
                "source_date": "",
                "temporal_order": f"Day {day}",
                "temporal_index": day,
            }

        return None

    async def _detect_temporal_metadata(self, content: str) -> dict[str, Any]:
        """Detect dates and temporal markers in content using LLM.

        Makes a single LLM call to extract temporal context from content.

        Args:
            content: Text content to analyze

        Returns:
            Dictionary with temporal metadata:
                - source_date: Date string if found (e.g., "2026-02-15")
                - temporal_order: Ordering label (e.g., "Day 7", "February 13")
                - temporal_index: Numeric index for sorting (e.g., 7 for Day 7)
        """
        fast_metadata = self._detect_temporal_metadata_fast(content)
        if fast_metadata is not None:
            return fast_metadata

        prompt = _load_prompt("temporal_detection_user", content=content[:500])
        try:
            response_text = (
                await self._llm_completion_with_retry(
                    messages=[
                        {"role": "system", "content": load_prompt("temporal_detection_system")},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.0,
                )
            ).strip()

            # Parse JSON response
            try:
                result = json.loads(response_text)
                if isinstance(result, dict):
                    return {
                        "source_date": result.get("source_date", ""),
                        "temporal_order": result.get("temporal_order", ""),
                        "temporal_index": result.get("temporal_index", 0),
                    }
            except json.JSONDecodeError:
                # Try extracting from markdown code block
                if "```json" in response_text:
                    json_start = response_text.find("```json") + 7
                    json_end = response_text.find("```", json_start)
                    json_str = response_text[json_start:json_end].strip()
                    result = json.loads(json_str)
                    if isinstance(result, dict):
                        return {
                            "source_date": result.get("source_date", ""),
                            "temporal_order": result.get("temporal_order", ""),
                            "temporal_index": result.get("temporal_index", 0),
                        }
        except Exception as e:
            logger.debug("Temporal metadata detection failed: %s", e)

        return {"source_date": "", "temporal_order": "", "temporal_index": 0}
