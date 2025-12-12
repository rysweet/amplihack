"""Unit tests for ContextRehydrator brick."""

import json

import pytest

from context_management.context_rehydrator import ContextRehydrator


class TestContextRehydrator:
    """Test suite for ContextRehydrator class."""

    @pytest.fixture
    def temp_snapshot_dir(self, tmp_path):
        """Create temporary snapshot directory."""
        snapshot_dir = tmp_path / "snapshots"
        snapshot_dir.mkdir()
        return snapshot_dir

    @pytest.fixture
    def rehydrator(self, temp_snapshot_dir):
        """Create ContextRehydrator with temp directory."""
        return ContextRehydrator(snapshot_dir=temp_snapshot_dir)

    @pytest.fixture
    def sample_snapshot_path(self, temp_snapshot_dir):
        """Create a sample snapshot file."""
        snapshot_data = {
            "snapshot_id": "20251116_120000",
            "name": "test-snapshot",
            "timestamp": "2025-11-16T12:00:00",
            "original_requirements": "Build a JWT authentication system",
            "key_decisions": [
                {
                    "decision": "Use RS256 encryption",
                    "rationale": "Better security",
                    "alternatives": "HS256",
                }
            ],
            "implementation_state": "JWT handler created",
            "open_items": ["Add refresh token rotation", "Handle expired tokens"],
            "tools_used": ["Write", "Edit"],
            "token_count": 1250,
            "file_path": None,
        }

        path = temp_snapshot_dir / "20251116_120000.json"
        with open(path, "w") as f:
            json.dump(snapshot_data, f)

        return path

    def test_initialization_default(self):
        """Test ContextRehydrator initializes with default directory."""
        rehydrator = ContextRehydrator()
        assert rehydrator.snapshot_dir is not None

    def test_initialization_custom(self, temp_snapshot_dir):
        """Test ContextRehydrator initializes with custom directory."""
        rehydrator = ContextRehydrator(snapshot_dir=temp_snapshot_dir)
        assert rehydrator.snapshot_dir == temp_snapshot_dir

    def test_rehydrate_essential_level(self, rehydrator, sample_snapshot_path):
        """Test rehydration at essential detail level."""
        context = rehydrator.rehydrate(sample_snapshot_path, level="essential")

        assert "Original Requirements" in context
        assert "Current State" in context
        assert "JWT authentication" in context
        # Essential should NOT include decisions or open items
        assert "Key Decisions" not in context

    def test_rehydrate_standard_level(self, rehydrator, sample_snapshot_path):
        """Test rehydration at standard detail level."""
        context = rehydrator.rehydrate(sample_snapshot_path, level="standard")

        assert "Original Requirements" in context
        assert "Current State" in context
        assert "Key Decisions" in context
        assert "Open Items" in context
        assert "RS256" in context

    def test_rehydrate_comprehensive_level(self, rehydrator, sample_snapshot_path):
        """Test rehydration at comprehensive detail level."""
        context = rehydrator.rehydrate(sample_snapshot_path, level="comprehensive")

        assert "Original Requirements" in context
        assert "Current State" in context
        assert "Key Decisions" in context
        assert "Open Items" in context
        assert "Tools Used" in context
        assert "Estimated tokens" in context

    def test_rehydrate_invalid_level(self, rehydrator, sample_snapshot_path):
        """Test rehydration with invalid level raises ValueError."""
        with pytest.raises(ValueError, match="Invalid level"):
            rehydrator.rehydrate(sample_snapshot_path, level="invalid")

    def test_rehydrate_missing_file(self, rehydrator, temp_snapshot_dir):
        """Test rehydration with missing file raises FileNotFoundError."""
        missing_path = temp_snapshot_dir / "nonexistent.json"
        with pytest.raises(FileNotFoundError):
            rehydrator.rehydrate(missing_path)

    def test_rehydrate_corrupted_json(self, rehydrator, temp_snapshot_dir):
        """Test rehydration with corrupted JSON raises error."""
        corrupted_path = temp_snapshot_dir / "corrupted.json"
        with open(corrupted_path, "w") as f:
            f.write("{invalid json")

        with pytest.raises(json.JSONDecodeError):
            rehydrator.rehydrate(corrupted_path)

    def test_list_snapshots_empty(self, rehydrator):
        """Test listing snapshots in empty directory."""
        snapshots = rehydrator.list_snapshots()
        assert snapshots == []

    def test_list_snapshots(self, rehydrator, sample_snapshot_path):
        """Test listing snapshots."""
        snapshots = rehydrator.list_snapshots()

        assert len(snapshots) == 1
        assert snapshots[0]["id"] == "20251116_120000"
        assert snapshots[0]["name"] == "test-snapshot"
        assert "timestamp" in snapshots[0]
        assert "size" in snapshots[0]

    def test_list_snapshots_multiple(self, rehydrator, temp_snapshot_dir):
        """Test listing multiple snapshots."""
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

        snapshots = rehydrator.list_snapshots()
        assert len(snapshots) == 3

    def test_list_snapshots_skips_corrupted(self, rehydrator, temp_snapshot_dir):
        """Test that list_snapshots skips corrupted files."""
        # Create valid snapshot
        valid_data = {
            "snapshot_id": "20251116_120000",
            "name": "valid",
            "timestamp": "2025-11-16T12:00:00",
            "original_requirements": "Test",
            "key_decisions": [],
            "implementation_state": "",
            "open_items": [],
            "tools_used": [],
            "token_count": 100,
            "file_path": None,
        }
        valid_path = temp_snapshot_dir / "20251116_120000.json"
        with open(valid_path, "w") as f:
            json.dump(valid_data, f)

        # Create corrupted snapshot
        corrupted_path = temp_snapshot_dir / "20251116_130000.json"
        with open(corrupted_path, "w") as f:
            f.write("{invalid}")

        snapshots = rehydrator.list_snapshots()
        # Should only return valid snapshot
        assert len(snapshots) == 1
        assert snapshots[0]["id"] == "20251116_120000"

    def test_get_snapshot_path_exists(self, rehydrator, sample_snapshot_path):
        """Test getting path to existing snapshot."""
        path = rehydrator.get_snapshot_path("20251116_120000")
        assert path is not None
        assert path.exists()

    def test_get_snapshot_path_not_exists(self, rehydrator):
        """Test getting path to non-existent snapshot."""
        path = rehydrator.get_snapshot_path("20990101_000000")
        assert path is None

    def test_format_size(self, rehydrator):
        """Test file size formatting."""
        assert rehydrator._format_size(500) == "500B"
        assert rehydrator._format_size(1536) == "1.5KB"
        assert rehydrator._format_size(1048576) == "1.0MB"

    def test_rehydrate_with_empty_decisions(self, rehydrator, temp_snapshot_dir):
        """Test rehydration when snapshot has no decisions."""
        snapshot_data = {
            "snapshot_id": "20251116_140000",
            "name": "empty-decisions",
            "timestamp": "2025-11-16T14:00:00",
            "original_requirements": "Test",
            "key_decisions": [],
            "implementation_state": "In progress",
            "open_items": [],
            "tools_used": [],
            "token_count": 50,
            "file_path": None,
        }

        path = temp_snapshot_dir / "20251116_140000.json"
        with open(path, "w") as f:
            json.dump(snapshot_data, f)

        context = rehydrator.rehydrate(path, level="standard")
        # Should not crash, should handle empty lists gracefully
        assert "Original Requirements" in context

    def test_rehydrate_with_empty_state(self, rehydrator, temp_snapshot_dir):
        """Test rehydration when implementation_state is empty."""
        snapshot_data = {
            "snapshot_id": "20251116_150000",
            "name": "empty-state",
            "timestamp": "2025-11-16T15:00:00",
            "original_requirements": "Test",
            "key_decisions": [],
            "implementation_state": "",
            "open_items": [],
            "tools_used": [],
            "token_count": 50,
            "file_path": None,
        }

        path = temp_snapshot_dir / "20251116_150000.json"
        with open(path, "w") as f:
            json.dump(snapshot_data, f)

        context = rehydrator.rehydrate(path, level="essential")
        assert "No state recorded" in context

    def test_levels_constant(self):
        """Test that LEVELS constant is correctly defined."""
        assert ContextRehydrator.LEVELS == ["essential", "standard", "comprehensive"]
