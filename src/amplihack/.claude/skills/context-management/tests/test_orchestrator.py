"""Unit tests for ContextManagementOrchestrator."""

import json

import pytest

from context_management.orchestrator import ContextManagementOrchestrator


class TestContextManagementOrchestrator:
    """Test suite for ContextManagementOrchestrator class."""

    @pytest.fixture
    def temp_snapshot_dir(self, tmp_path):
        """Create temporary snapshot directory."""
        snapshot_dir = tmp_path / "snapshots"
        snapshot_dir.mkdir()
        return snapshot_dir

    @pytest.fixture
    def orchestrator(self, temp_snapshot_dir):
        """Create orchestrator with temp directory."""
        return ContextManagementOrchestrator(snapshot_dir=temp_snapshot_dir, max_tokens=1_000_000)

    @pytest.fixture
    def sample_conversation(self):
        """Create sample conversation data."""
        return [
            {"role": "user", "content": "Build a JWT authentication system"},
            {
                "role": "assistant",
                "content": "I decided to use RS256 encryption for better security.",
            },
            {"role": "tool_use", "tool_name": "Write", "parameters": {}},
        ]

    def test_initialization(self, temp_snapshot_dir):
        """Test orchestrator initializes components correctly."""
        orch = ContextManagementOrchestrator(snapshot_dir=temp_snapshot_dir, max_tokens=500_000)

        assert orch.monitor is not None
        assert orch.extractor is not None
        assert orch.rehydrator is not None
        assert orch.monitor.max_tokens == 500_000

    def test_handle_status_action(self, orchestrator):
        """Test 'status' action handling."""
        result = orchestrator.handle_action("status", current_tokens=500_000)

        assert result["status"] == "ok"
        assert "usage" in result
        assert result["usage"]["current_tokens"] == 500_000
        assert result["usage"]["percentage"] == 50.0

    def test_handle_status_high_usage(self, orchestrator):
        """Test 'status' action with high token usage."""
        result = orchestrator.handle_action("status", current_tokens=900_000)

        assert result["status"] == "recommended"
        assert result["usage"]["percentage"] == 90.0

    def test_handle_snapshot_action(self, orchestrator, sample_conversation):
        """Test 'snapshot' action handling."""
        result = orchestrator.handle_action(
            "snapshot", conversation_data=sample_conversation, name="test-feature"
        )

        assert result["status"] == "success"
        assert "snapshot" in result
        assert result["snapshot"]["name"] == "test-feature"
        assert "snapshot_id" in result["snapshot"]
        assert "recommendation" in result

    def test_handle_snapshot_without_conversation(self, orchestrator):
        """Test 'snapshot' action without conversation_data."""
        result = orchestrator.handle_action("snapshot")

        assert result["status"] == "error"
        assert "conversation_data is required" in result["error"]

    def test_handle_snapshot_without_name(self, orchestrator, sample_conversation):
        """Test 'snapshot' action without custom name."""
        result = orchestrator.handle_action("snapshot", conversation_data=sample_conversation)

        assert result["status"] == "success"
        assert result["snapshot"]["name"] is None

    def test_handle_rehydrate_action(self, orchestrator, temp_snapshot_dir):
        """Test 'rehydrate' action handling."""
        # First create a snapshot
        snapshot_data = {
            "snapshot_id": "20251116_120000",
            "name": "test",
            "timestamp": "2025-11-16T12:00:00",
            "original_requirements": "Build API",
            "key_decisions": [],
            "implementation_state": "In progress",
            "open_items": [],
            "tools_used": [],
            "token_count": 100,
            "file_path": None,
        }
        snapshot_path = temp_snapshot_dir / "20251116_120000.json"
        with open(snapshot_path, "w") as f:
            json.dump(snapshot_data, f)

        # Now rehydrate
        result = orchestrator.handle_action(
            "rehydrate", snapshot_id="20251116_120000", level="essential"
        )

        assert result["status"] == "success"
        assert "context" in result
        assert "Build API" in result["context"]
        assert result["level"] == "essential"

    def test_handle_rehydrate_missing_snapshot(self, orchestrator):
        """Test 'rehydrate' action with missing snapshot."""
        result = orchestrator.handle_action("rehydrate", snapshot_id="nonexistent")

        assert result["status"] == "error"
        assert "not found" in result["error"]

    def test_handle_rehydrate_without_id(self, orchestrator):
        """Test 'rehydrate' action without snapshot_id."""
        result = orchestrator.handle_action("rehydrate")

        assert result["status"] == "error"
        assert "snapshot_id is required" in result["error"]

    def test_handle_list_action_empty(self, orchestrator):
        """Test 'list' action with no snapshots."""
        result = orchestrator.handle_action("list")

        assert result["status"] == "success"
        assert result["snapshots"] == []
        assert result["count"] == 0

    def test_handle_list_action(self, orchestrator, temp_snapshot_dir):
        """Test 'list' action with snapshots."""
        # Create multiple snapshots
        for i in range(3):
            snapshot_data = {
                "snapshot_id": f"2025111{i}_120000",
                "name": f"snapshot-{i}",
                "timestamp": f"2025-11-1{i}T12:00:00",
                "original_requirements": "Test",
                "key_decisions": [],
                "implementation_state": "",
                "open_items": [],
                "tools_used": [],
                "token_count": 100,
                "file_path": None,
            }
            path = temp_snapshot_dir / f"2025111{i}_120000.json"
            with open(path, "w") as f:
                json.dump(snapshot_data, f)

        result = orchestrator.handle_action("list")

        assert result["status"] == "success"
        assert result["count"] == 3
        assert len(result["snapshots"]) == 3
        assert "total_size" in result

    def test_handle_invalid_action(self, orchestrator):
        """Test handling of invalid action."""
        with pytest.raises(ValueError, match="Invalid action"):
            orchestrator.handle_action("invalid_action")

    def test_integration_status_to_snapshot(self, orchestrator, sample_conversation):
        """Test workflow: check status, then create snapshot."""
        # Check status
        status_result = orchestrator.handle_action("status", current_tokens=850_000)
        assert status_result["status"] == "recommended"

        # Create snapshot based on recommendation
        snapshot_result = orchestrator.handle_action(
            "snapshot", conversation_data=sample_conversation, name="high-usage-snapshot"
        )
        assert snapshot_result["status"] == "success"

    def test_integration_snapshot_to_rehydrate(self, orchestrator, sample_conversation):
        """Test workflow: create snapshot, then rehydrate."""
        # Create snapshot
        snapshot_result = orchestrator.handle_action(
            "snapshot", conversation_data=sample_conversation, name="test"
        )
        snapshot_id = snapshot_result["snapshot"]["snapshot_id"]

        # Rehydrate it
        rehydrate_result = orchestrator.handle_action(
            "rehydrate", snapshot_id=snapshot_id, level="standard"
        )
        assert rehydrate_result["status"] == "success"
        assert "JWT authentication" in rehydrate_result["context"]

    def test_parse_size(self, orchestrator):
        """Test size string parsing."""
        assert orchestrator._parse_size("500B") == 500
        assert orchestrator._parse_size("1.5KB") == 1536
        assert orchestrator._parse_size("1.0MB") == 1048576

    def test_format_size_bytes(self, orchestrator):
        """Test size formatting."""
        assert orchestrator._format_size_bytes(500) == "500B"
        assert "1.5KB" in orchestrator._format_size_bytes(1536)
        assert "1.0MB" in orchestrator._format_size_bytes(1048576)
