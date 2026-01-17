"""Integration tests for context-management skill."""

import json
from pathlib import Path

import pytest

from context_management import (
    check_status,
    context_management_skill,
    create_snapshot,
    list_snapshots,
    rehydrate_context,
)


class TestIntegration:
    """Integration test suite for complete workflows."""

    @pytest.fixture
    def temp_snapshot_dir(self, tmp_path):
        """Create temporary snapshot directory."""
        snapshot_dir = tmp_path / "snapshots"
        snapshot_dir.mkdir()
        return snapshot_dir

    @pytest.fixture
    def sample_conversation(self):
        """Load sample conversation fixture."""
        fixture_path = Path(__file__).parent / "fixtures" / "sample_conversation.json"
        with open(fixture_path) as f:
            return json.load(f)

    def test_end_to_end_workflow(self, temp_snapshot_dir, sample_conversation):
        """Test complete workflow: status -> snapshot -> rehydrate -> list."""
        # Step 1: Check status
        status_result = context_management_skill(
            "status", current_tokens=850_000, snapshot_dir=temp_snapshot_dir
        )
        assert status_result["status"] == "recommended"

        # Step 2: Create snapshot
        snapshot_result = context_management_skill(
            "snapshot",
            conversation_data=sample_conversation,
            name="e2e-test",
            snapshot_dir=temp_snapshot_dir,
        )
        assert snapshot_result["status"] == "success"
        snapshot_id = snapshot_result["snapshot"]["snapshot_id"]

        # Step 3: List snapshots
        list_result = context_management_skill("list", snapshot_dir=temp_snapshot_dir)
        assert list_result["count"] == 1
        assert list_result["snapshots"][0]["name"] == "e2e-test"

        # Step 4: Rehydrate at different levels
        for level in ["essential", "standard", "comprehensive"]:
            rehydrate_result = context_management_skill(
                "rehydrate", snapshot_id=snapshot_id, level=level, snapshot_dir=temp_snapshot_dir
            )
            assert rehydrate_result["status"] == "success"
            assert "JWT authentication" in rehydrate_result["context"]

    def test_convenience_functions(self, temp_snapshot_dir, sample_conversation):
        """Test convenience functions work correctly."""
        # Test check_status
        status = check_status(current_tokens=500_000, snapshot_dir=temp_snapshot_dir)
        assert status["status"] == "ok"

        # Test create_snapshot
        snapshot = create_snapshot(
            conversation_data=sample_conversation,
            name="convenience-test",
            snapshot_dir=temp_snapshot_dir,
        )
        assert snapshot["status"] == "success"
        snapshot_id = snapshot["snapshot"]["snapshot_id"]

        # Test list_snapshots
        snapshots = list_snapshots(snapshot_dir=temp_snapshot_dir)
        assert snapshots["count"] == 1

        # Test rehydrate_context
        context = rehydrate_context(
            snapshot_id=snapshot_id, level="standard", snapshot_dir=temp_snapshot_dir
        )
        assert context["status"] == "success"

    def test_multiple_snapshots_workflow(self, temp_snapshot_dir, sample_conversation):
        """Test creating and managing multiple snapshots."""
        snapshot_ids = []

        # Create 3 snapshots with different names
        for i in range(3):
            result = create_snapshot(
                conversation_data=sample_conversation,
                name=f"snapshot-{i}",
                snapshot_dir=temp_snapshot_dir,
            )
            assert result["status"] == "success"
            snapshot_ids.append(result["snapshot"]["snapshot_id"])

        # List all snapshots
        list_result = list_snapshots(snapshot_dir=temp_snapshot_dir)
        assert list_result["count"] == 3

        # Rehydrate each one
        for snapshot_id in snapshot_ids:
            result = rehydrate_context(snapshot_id=snapshot_id, snapshot_dir=temp_snapshot_dir)
            assert result["status"] == "success"

    def test_proactive_management_scenario(self, temp_snapshot_dir, sample_conversation):
        """Test proactive context management scenario."""
        # Monitor usage as it increases
        usage_levels = [400_000, 700_000, 850_000, 950_000]

        for tokens in usage_levels:
            status = check_status(current_tokens=tokens, snapshot_dir=temp_snapshot_dir)

            # At 850k, create snapshot
            if tokens >= 850_000:
                assert status["status"] in ["recommended", "urgent"]

                # Create snapshot
                snapshot = create_snapshot(
                    conversation_data=sample_conversation,
                    name=f"snapshot-at-{tokens}",
                    snapshot_dir=temp_snapshot_dir,
                )
                assert snapshot["status"] == "success"

    def test_snapshot_persistence(self, temp_snapshot_dir, sample_conversation):
        """Test that snapshots persist across orchestrator instances."""
        # Create snapshot with first instance
        snapshot1 = create_snapshot(
            conversation_data=sample_conversation,
            name="persistent-test",
            snapshot_dir=temp_snapshot_dir,
        )
        snapshot_id = snapshot1["snapshot"]["snapshot_id"]

        # Verify with new instance (simulated by new function call)
        list_result = list_snapshots(snapshot_dir=temp_snapshot_dir)
        assert list_result["count"] == 1

        # Rehydrate with new instance
        context = rehydrate_context(snapshot_id=snapshot_id, snapshot_dir=temp_snapshot_dir)
        assert context["status"] == "success"

    def test_error_handling_workflow(self, temp_snapshot_dir):
        """Test error handling throughout workflow."""
        # Try to create snapshot without conversation
        result = create_snapshot(conversation_data=None, snapshot_dir=temp_snapshot_dir)
        assert result["status"] == "error"

        # Try to rehydrate non-existent snapshot
        result = rehydrate_context(snapshot_id="nonexistent", snapshot_dir=temp_snapshot_dir)
        assert result["status"] == "error"

        # List should still work
        result = list_snapshots(snapshot_dir=temp_snapshot_dir)
        assert result["status"] == "success"
        assert result["count"] == 0

    def test_detail_level_differences(self, temp_snapshot_dir, sample_conversation):
        """Test that different detail levels produce different output."""
        # Create snapshot
        snapshot = create_snapshot(
            conversation_data=sample_conversation,
            name="detail-test",
            snapshot_dir=temp_snapshot_dir,
        )
        snapshot_id = snapshot["snapshot"]["snapshot_id"]

        # Rehydrate at all levels
        essential = rehydrate_context(
            snapshot_id=snapshot_id, level="essential", snapshot_dir=temp_snapshot_dir
        )
        standard = rehydrate_context(
            snapshot_id=snapshot_id, level="standard", snapshot_dir=temp_snapshot_dir
        )
        comprehensive = rehydrate_context(
            snapshot_id=snapshot_id, level="comprehensive", snapshot_dir=temp_snapshot_dir
        )

        # Essential should be shortest
        assert len(essential["context"]) < len(standard["context"])
        # Comprehensive should be longest
        assert len(comprehensive["context"]) > len(standard["context"])

        # Essential should NOT have decisions
        assert "Key Decisions" not in essential["context"]
        # Standard should have decisions
        assert "Key Decisions" in standard["context"]
        # Comprehensive should have tools
        assert "Tools Used" in comprehensive["context"]

    def test_snapshot_metadata_accuracy(self, temp_snapshot_dir, sample_conversation):
        """Test that snapshot metadata is accurate."""
        # Create snapshot
        snapshot = create_snapshot(
            conversation_data=sample_conversation,
            name="metadata-test",
            snapshot_dir=temp_snapshot_dir,
        )

        # Verify components
        assert "requirements" in snapshot["snapshot"]["components"]
        assert "decisions" in snapshot["snapshot"]["components"]
        assert "state" in snapshot["snapshot"]["components"]
        assert "open_items" in snapshot["snapshot"]["components"]
        assert "tools_used" in snapshot["snapshot"]["components"]

        # Verify token count is present
        assert snapshot["snapshot"]["token_count"] > 0

        # Verify file exists
        file_path = Path(snapshot["snapshot"]["file_path"])
        assert file_path.exists()
