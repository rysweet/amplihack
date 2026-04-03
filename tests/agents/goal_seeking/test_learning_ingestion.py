"""Tests for LearningIngestionMixin methods.

Tests content truncation, source label extraction, fact kwargs building,
temporal metadata detection, and summary concept map generation.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amplihack.agents.goal_seeking import LearningAgent


class TestLearningIngestion:
    """Tests for learning ingestion mixin methods."""

    @pytest.fixture
    def temp_storage(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def agent(self, temp_storage):
        agent = LearningAgent(agent_name="test_ingest", storage_path=str(temp_storage))
        yield agent
        agent.close()

    # --- _truncate_learning_content ---

    def test_truncate_short_content_unchanged(self):
        content = "Hello world"
        assert LearningAgent._truncate_learning_content(content) == content

    def test_truncate_long_content(self):
        content = "x" * 60_000
        result = LearningAgent._truncate_learning_content(content)
        assert len(result) == 50_000

    # --- _extract_source_label ---

    def test_extract_source_label_from_title(self):
        content = "Title: My Great Article\nBody text here."
        assert LearningAgent._extract_source_label(content) == "My Great Article"

    def test_extract_source_label_fallback(self):
        content = "Some plain text content without a title header."
        result = LearningAgent._extract_source_label(content)
        assert len(result) <= 60

    def test_extract_source_label_title_no_newline(self):
        content = "Title: Short"
        # No newline, so title_end would be -1, falls through to fallback
        result = LearningAgent._extract_source_label(content)
        assert len(result) <= 60

    # --- _build_store_fact_kwargs ---

    def test_build_store_fact_kwargs_basic(self, agent):
        fact = {
            "context": "Science",
            "fact": "Water boils at 100C",
            "confidence": 0.9,
            "tags": ["chemistry"],
        }
        result = agent._build_store_fact_kwargs(fact, {}, "article1")
        assert result["context"] == "Science"
        assert result["fact"] == "Water boils at 100C"
        assert result["confidence"] == 0.9
        assert "chemistry" in result["tags"]

    def test_build_store_fact_kwargs_adds_date_tag(self, agent):
        fact = {"context": "News", "fact": "Event happened", "tags": ["current"]}
        temporal_meta = {"source_date": "2026-01-15"}
        result = agent._build_store_fact_kwargs(fact, temporal_meta, "news")
        assert "date:2026-01-15" in result["tags"]

    def test_build_store_fact_kwargs_adds_temporal_order_tag(self, agent):
        fact = {"context": "Log", "fact": "Step completed", "tags": []}
        temporal_meta = {"temporal_order": "Day 3"}
        result = agent._build_store_fact_kwargs(fact, temporal_meta, "log")
        assert "time:Day 3" in result["tags"]

    def test_build_store_fact_kwargs_hierarchical_metadata(self, agent):
        agent.use_hierarchical = True
        fact = {"context": "X", "fact": "Y", "tags": []}
        temporal_meta = {"source_date": "2026-03-01", "temporal_order": "March 1"}
        result = agent._build_store_fact_kwargs(fact, temporal_meta, "src")
        assert "temporal_metadata" in result
        assert result["temporal_metadata"]["source_label"] == "src"

    def test_build_store_fact_kwargs_default_tags(self, agent):
        fact = {"context": "X", "fact": "Y"}
        result = agent._build_store_fact_kwargs(fact, {}, "")
        assert result["tags"] == ["learned"]

    # --- _detect_temporal_metadata_fast ---

    def test_detect_temporal_metadata_fast_timestamp(self):
        content = "Timestamp: 2026-03-15 14:30:00\nData follows."
        result = LearningAgent._detect_temporal_metadata_fast(content)
        assert result is not None
        assert result["source_date"] == "2026-03-15"
        assert "14:30" in result["temporal_order"]

    def test_detect_temporal_metadata_fast_iso_date(self):
        content = "Report from 2026-01-20 with findings."
        result = LearningAgent._detect_temporal_metadata_fast(content)
        assert result is not None
        assert result["source_date"] == "2026-01-20"

    def test_detect_temporal_metadata_fast_day_marker(self):
        content = "Day 7 observations show improvement."
        result = LearningAgent._detect_temporal_metadata_fast(content)
        assert result is not None
        assert result["temporal_order"] == "Day 7"
        assert result["temporal_index"] == 7

    def test_detect_temporal_metadata_fast_no_temporal(self):
        content = "No dates or time markers here."
        assert LearningAgent._detect_temporal_metadata_fast(content) is None

    # --- _store_summary_concept_map ---

    @pytest.mark.asyncio
    async def test_store_summary_concept_map_stores_fact(self, agent):
        agent.memory.store_fact = MagicMock()
        with patch(
            "amplihack.agents.goal_seeking.learning_agent._llm_completion",
            new_callable=AsyncMock,
            return_value="Overview: key concepts are X and Y",
        ):
            await agent._store_summary_concept_map(
                "content", [{"context": "A", "fact": "B"}], episode_id=""
            )
        agent.memory.store_fact.assert_called_once()
        call_kwargs = agent.memory.store_fact.call_args[1]
        assert call_kwargs["context"] == "SUMMARY"

    @pytest.mark.asyncio
    async def test_store_summary_concept_map_handles_llm_error(self, agent):
        agent.memory.store_fact = MagicMock()
        with patch(
            "amplihack.agents.goal_seeking.learning_agent._llm_completion",
            new_callable=AsyncMock,
            side_effect=RuntimeError("LLM error"),
        ):
            # Should not raise
            await agent._store_summary_concept_map("content", [{"context": "A", "fact": "B"}])
        agent.memory.store_fact.assert_not_called()

    # --- prepare_fact_batch ---

    @pytest.mark.asyncio
    async def test_prepare_fact_batch_empty_content(self, agent):
        result = await agent.prepare_fact_batch("")
        assert result["facts_extracted"] == 0
        assert result["facts"] == []

    @pytest.mark.asyncio
    async def test_prepare_fact_batch_extracts_facts(self, agent):
        with patch(
            "amplihack.agents.goal_seeking.learning_agent._llm_completion",
            new_callable=AsyncMock,
            side_effect=[
                # _detect_temporal_metadata LLM call
                '{"source_date": "", "temporal_order": "", "temporal_index": 0}',
                # _extract_facts_with_llm call
                '[{"context": "Test", "fact": "Fact one", "confidence": 0.9, "tags": ["test"]}]',
                # _build_summary_store_kwargs call
                "Summary of the content",
            ],
        ):
            result = await agent.prepare_fact_batch("Some learning content")
        assert result["facts_extracted"] == 1
        assert len(result["facts"]) == 1
