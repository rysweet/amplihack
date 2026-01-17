"""Unit tests for ContextExtractor brick."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from context_management.context_extractor import ContextExtractor


class TestContextExtractor:
    """Test suite for ContextExtractor class."""

    @pytest.fixture
    def temp_snapshot_dir(self, tmp_path):
        """Create temporary snapshot directory."""
        snapshot_dir = tmp_path / "snapshots"
        snapshot_dir.mkdir()
        return snapshot_dir

    @pytest.fixture
    def extractor(self, temp_snapshot_dir):
        """Create ContextExtractor with temp directory."""
        return ContextExtractor(snapshot_dir=temp_snapshot_dir)

    @pytest.fixture
    def sample_conversation(self):
        """Load sample conversation fixture."""
        fixture_path = Path(__file__).parent / "fixtures" / "sample_conversation.json"
        with open(fixture_path) as f:
            return json.load(f)

    def test_initialization_default(self):
        """Test ContextExtractor initializes with default directory."""
        extractor = ContextExtractor()
        assert extractor.snapshot_dir is not None

    def test_initialization_custom(self, temp_snapshot_dir):
        """Test ContextExtractor initializes with custom directory."""
        extractor = ContextExtractor(snapshot_dir=temp_snapshot_dir)
        assert extractor.snapshot_dir == temp_snapshot_dir
        assert extractor.snapshot_dir.exists()

    def test_extract_original_requirements(self, extractor, sample_conversation):
        """Test extraction of original requirements from conversation."""
        context = extractor.extract_from_conversation(sample_conversation)
        assert "JWT authentication" in context["original_requirements"]
        assert "API" in context["original_requirements"]

    def test_extract_original_requirements_empty(self, extractor):
        """Test extraction with empty conversation."""
        context = extractor.extract_from_conversation([])
        assert "No user requirements found" in context["original_requirements"]

    def test_extract_key_decisions(self, extractor, sample_conversation):
        """Test extraction of key decisions."""
        context = extractor.extract_from_conversation(sample_conversation)
        assert isinstance(context["key_decisions"], list)
        # Should find decisions like "decided to use"
        assert len(context["key_decisions"]) > 0

    def test_extract_implementation_state(self, extractor, sample_conversation):
        """Test extraction of implementation state."""
        context = extractor.extract_from_conversation(sample_conversation)
        assert "Tools invoked:" in context["implementation_state"]

    def test_extract_open_items(self, extractor, sample_conversation):
        """Test extraction of open items and questions."""
        context = extractor.extract_from_conversation(sample_conversation)
        open_items = context["open_items"]
        assert isinstance(open_items, list)
        # Should find "TODO" items and questions
        assert any("TODO" in item or "?" in item for item in open_items)

    def test_extract_tools_used(self, extractor, sample_conversation):
        """Test extraction of tools used."""
        context = extractor.extract_from_conversation(sample_conversation)
        tools = context["tools_used"]
        assert "Write" in tools
        assert "Edit" in tools

    def test_create_snapshot(self, extractor):
        """Test snapshot creation."""
        context = {
            "original_requirements": "Build an API",
            "key_decisions": [
                {"decision": "Use FastAPI", "rationale": "Speed", "alternatives": "Flask"}
            ],
            "implementation_state": "In progress",
            "open_items": ["Add tests"],
            "tools_used": ["Write"],
        }

        path = extractor.create_snapshot(context, name="test-snapshot")

        assert path.exists()
        assert path.suffix == ".json"
        assert path.stem != "test-snapshot"  # Should use timestamp ID

    def test_create_snapshot_without_name(self, extractor):
        """Test snapshot creation without custom name."""
        context = {
            "original_requirements": "Test",
            "key_decisions": [],
            "implementation_state": "",
            "open_items": [],
            "tools_used": [],
        }

        path = extractor.create_snapshot(context)
        assert path.exists()

        # Verify snapshot content
        with open(path) as f:
            data = json.load(f)
            assert data["name"] is None
            assert data["original_requirements"] == "Test"

    def test_create_snapshot_with_name(self, extractor):
        """Test snapshot creation with custom name."""
        context = {
            "original_requirements": "Build feature",
            "key_decisions": [],
            "implementation_state": "",
            "open_items": [],
            "tools_used": [],
        }

        path = extractor.create_snapshot(context, name="my-feature")

        with open(path) as f:
            data = json.load(f)
            assert data["name"] == "my-feature"

    def test_snapshot_id_format(self, extractor):
        """Test snapshot ID follows YYYYMMDD_HHMMSS format."""
        context = {
            "original_requirements": "Test",
            "key_decisions": [],
            "implementation_state": "",
            "open_items": [],
            "tools_used": [],
        }

        path = extractor.create_snapshot(context)
        snapshot_id = path.stem

        # Should match YYYYMMDD_HHMMSS pattern
        assert len(snapshot_id) == 15
        assert snapshot_id[8] == "_"

        # Should be parseable as datetime
        datetime.strptime(snapshot_id, "%Y%m%d_%H%M%S")

    def test_snapshot_token_estimation(self, extractor):
        """Test token count estimation in snapshot."""
        context = {
            "original_requirements": "A" * 400,  # ~100 tokens
            "key_decisions": [{"decision": "B" * 400, "rationale": "", "alternatives": ""}],
            "implementation_state": "C" * 400,
            "open_items": ["D" * 400],
            "tools_used": [],
        }

        path = extractor.create_snapshot(context)

        with open(path) as f:
            data = json.load(f)
            # Should estimate roughly (400*4)/4 = 400 tokens
            assert data["token_count"] > 0

    def test_extract_from_conversation_comprehensive(self, extractor, sample_conversation):
        """Test complete extraction produces all expected fields."""
        context = extractor.extract_from_conversation(sample_conversation)

        assert "original_requirements" in context
        assert "key_decisions" in context
        assert "implementation_state" in context
        assert "open_items" in context
        assert "tools_used" in context

        assert isinstance(context["key_decisions"], list)
        assert isinstance(context["open_items"], list)
        assert isinstance(context["tools_used"], list)

    def test_extract_limits_decisions_to_five(self, extractor):
        """Test that only top 5 decisions are extracted."""
        # Create conversation with many decisions
        conversation = []
        for i in range(10):
            conversation.append(
                {
                    "role": "assistant",
                    "content": f"I decided to use approach {i} because it is better.",
                }
            )

        context = extractor.extract_from_conversation(conversation)
        assert len(context["key_decisions"]) <= 5

    def test_extract_limits_open_items_to_ten(self, extractor):
        """Test that only top 10 open items are extracted."""
        # Create conversation with many questions
        conversation = []
        for i in range(20):
            conversation.append({"role": "user", "content": f"Question {i}?"})

        context = extractor.extract_from_conversation(conversation)
        assert len(context["open_items"]) <= 10

    def test_extract_truncates_long_requirements(self, extractor):
        """Test that very long requirements are truncated."""
        conversation = [
            {
                "role": "user",
                "content": "A" * 1000,  # Very long requirement
            }
        ]

        context = extractor.extract_from_conversation(conversation)
        # Should be truncated to 500 chars + "..."
        assert len(context["original_requirements"]) <= 503
        if len(conversation[0]["content"]) > 500:
            assert context["original_requirements"].endswith("...")
