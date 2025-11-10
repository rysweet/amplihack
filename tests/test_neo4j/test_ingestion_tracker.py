"""Tests for ingestion tracker."""

from pathlib import Path

import pytest
from neo4j import Driver

from amplihack.memory.neo4j.identifier import CodebaseIdentifier
from amplihack.memory.neo4j.ingestion_tracker import IngestionTracker
from amplihack.memory.neo4j.models import CodebaseIdentity, IngestionStatus


class TestIngestionTracker:
    """Test IngestionTracker functionality."""

    def test_initialization(self, neo4j_driver: Driver):
        """Test tracker initialization."""
        tracker = IngestionTracker(neo4j_driver, auto_initialize=True)

        assert tracker.driver == neo4j_driver
        assert tracker.schema.verify_schema()

    def test_initialization_without_auto_init(self, neo4j_driver: Driver):
        """Test tracker initialization without auto schema init."""
        tracker = IngestionTracker(neo4j_driver, auto_initialize=False)

        assert tracker.driver == neo4j_driver
        # Schema should not be initialized
        assert not tracker.schema.verify_schema()

    def test_track_ingestion_new_codebase(self, neo4j_driver: Driver, temp_git_repo: Path):
        """Test tracking a new codebase ingestion."""
        tracker = IngestionTracker(neo4j_driver)

        result = tracker.track_ingestion(temp_git_repo)

        assert result.status == IngestionStatus.NEW
        assert result.is_new()
        assert not result.is_update()
        assert not result.is_error()
        assert result.ingestion_metadata.ingestion_counter == 1
        assert result.previous_ingestion_id is None
        assert result.error_message is None

    def test_track_ingestion_update_existing(self, neo4j_driver: Driver, temp_git_repo: Path):
        """Test tracking an update to existing codebase."""
        tracker = IngestionTracker(neo4j_driver)

        # First ingestion
        result1 = tracker.track_ingestion(temp_git_repo)
        assert result1.is_new()
        assert result1.ingestion_metadata.ingestion_counter == 1

        # Second ingestion (update)
        result2 = tracker.track_ingestion(temp_git_repo)
        assert result2.is_update()
        assert result2.ingestion_metadata.ingestion_counter == 2
        assert result2.previous_ingestion_id == result1.ingestion_metadata.ingestion_id

    def test_track_ingestion_multiple_updates(self, neo4j_driver: Driver, temp_git_repo: Path):
        """Test multiple updates to same codebase."""
        tracker = IngestionTracker(neo4j_driver)

        results = []
        for i in range(5):
            result = tracker.track_ingestion(temp_git_repo)
            results.append(result)

        # First should be NEW
        assert results[0].is_new()
        assert results[0].ingestion_metadata.ingestion_counter == 1

        # Rest should be UPDATEs with incrementing counters
        for i in range(1, 5):
            assert results[i].is_update()
            assert results[i].ingestion_metadata.ingestion_counter == i + 1
            assert results[i].previous_ingestion_id == results[i - 1].ingestion_metadata.ingestion_id

    def test_track_ingestion_invalid_path(self, neo4j_driver: Driver):
        """Test error handling for invalid path."""
        tracker = IngestionTracker(neo4j_driver)

        result = tracker.track_ingestion(Path("/nonexistent/path"))

        assert result.status == IngestionStatus.ERROR
        assert result.is_error()
        assert result.error_message is not None

    def test_track_ingestion_not_git_repo(self, neo4j_driver: Driver, tmp_path: Path):
        """Test error handling for non-Git directory."""
        tracker = IngestionTracker(neo4j_driver)

        result = tracker.track_ingestion(tmp_path)

        assert result.status == IngestionStatus.ERROR
        assert result.is_error()
        assert "Git repository" in result.error_message

    def test_track_ingestion_with_metadata(self, neo4j_driver: Driver, temp_git_repo: Path):
        """Test tracking with custom metadata."""
        tracker = IngestionTracker(neo4j_driver)
        custom_metadata = {"source": "test", "user": "pytest"}

        result = tracker.track_ingestion(temp_git_repo, metadata=custom_metadata)

        assert result.status == IngestionStatus.NEW
        assert result.ingestion_metadata.metadata == custom_metadata

    def test_track_manual_ingestion_new(self, neo4j_driver: Driver, sample_codebase_identity: CodebaseIdentity):
        """Test tracking manual ingestion for new codebase."""
        tracker = IngestionTracker(neo4j_driver)

        result = tracker.track_manual_ingestion(sample_codebase_identity)

        assert result.status == IngestionStatus.NEW
        assert result.is_new()
        assert result.ingestion_metadata.ingestion_counter == 1

    def test_track_manual_ingestion_update(self, neo4j_driver: Driver, sample_codebase_identity: CodebaseIdentity):
        """Test tracking manual ingestion for existing codebase."""
        tracker = IngestionTracker(neo4j_driver)

        # First ingestion
        result1 = tracker.track_manual_ingestion(sample_codebase_identity)
        assert result1.is_new()

        # Update with different commit
        updated_identity = CodebaseIdentity(
            remote_url=sample_codebase_identity.remote_url,
            branch=sample_codebase_identity.branch,
            commit_sha="b" * 40,
            unique_key=sample_codebase_identity.unique_key,
        )

        result2 = tracker.track_manual_ingestion(updated_identity)
        assert result2.is_update()
        assert result2.ingestion_metadata.ingestion_counter == 2
        assert result2.previous_ingestion_id == result1.ingestion_metadata.ingestion_id

    def test_track_manual_ingestion_invalid_identity(self, neo4j_driver: Driver):
        """Test error handling for invalid identity."""
        tracker = IngestionTracker(neo4j_driver)

        invalid_identity = CodebaseIdentity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="invalid",  # Invalid SHA
            unique_key="b" * 64,
        )

        result = tracker.track_manual_ingestion(invalid_identity)

        assert result.status == IngestionStatus.ERROR
        assert result.is_error()

    def test_get_ingestion_history(self, neo4j_driver: Driver, sample_codebase_identity: CodebaseIdentity):
        """Test getting ingestion history."""
        tracker = IngestionTracker(neo4j_driver)

        # Create multiple ingestions
        identities = []
        for i in range(3):
            identity = CodebaseIdentity(
                remote_url=sample_codebase_identity.remote_url,
                branch=sample_codebase_identity.branch,
                commit_sha=f"{i:040d}",
                unique_key=sample_codebase_identity.unique_key,
            )
            identities.append(identity)
            tracker.track_manual_ingestion(identity)

        # Get history
        history = tracker.get_ingestion_history(sample_codebase_identity.unique_key)

        assert len(history) == 3
        # Should be in chronological order
        for i, record in enumerate(history):
            assert record["ingestion_counter"] == i + 1

    def test_get_ingestion_history_empty(self, neo4j_driver: Driver):
        """Test getting history for non-existent codebase."""
        tracker = IngestionTracker(neo4j_driver)

        history = tracker.get_ingestion_history("nonexistent-key")

        assert history == []

    def test_get_codebase_info(self, neo4j_driver: Driver, sample_codebase_identity: CodebaseIdentity):
        """Test getting codebase information."""
        tracker = IngestionTracker(neo4j_driver)

        # Track ingestion
        tracker.track_manual_ingestion(sample_codebase_identity)

        # Get info
        info = tracker.get_codebase_info(sample_codebase_identity.unique_key)

        assert info is not None
        assert info["unique_key"] == sample_codebase_identity.unique_key
        assert info["remote_url"] == sample_codebase_identity.remote_url
        assert info["branch"] == sample_codebase_identity.branch
        assert info["ingestion_count"] == 1

    def test_get_codebase_info_nonexistent(self, neo4j_driver: Driver):
        """Test getting info for non-existent codebase."""
        tracker = IngestionTracker(neo4j_driver)

        info = tracker.get_codebase_info("nonexistent-key")

        assert info is None

    def test_get_codebase_info_after_update(self, neo4j_driver: Driver, sample_codebase_identity: CodebaseIdentity):
        """Test that codebase info reflects updates."""
        tracker = IngestionTracker(neo4j_driver)

        # First ingestion
        tracker.track_manual_ingestion(sample_codebase_identity)

        # Update
        updated_identity = CodebaseIdentity(
            remote_url=sample_codebase_identity.remote_url,
            branch=sample_codebase_identity.branch,
            commit_sha="b" * 40,
            unique_key=sample_codebase_identity.unique_key,
        )
        tracker.track_manual_ingestion(updated_identity)

        # Get info
        info = tracker.get_codebase_info(sample_codebase_identity.unique_key)

        assert info["ingestion_count"] == 2
        assert info["commit_sha"] == "b" * 40

    def test_different_branches_different_codebases(self, neo4j_driver: Driver):
        """Test that different branches are tracked separately."""
        tracker = IngestionTracker(neo4j_driver)

        # Create identities for different branches
        identity_main = CodebaseIdentifier.create_manual_identity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="a" * 40,
        )

        identity_dev = CodebaseIdentifier.create_manual_identity(
            remote_url="https://github.com/test/repo.git",
            branch="dev",
            commit_sha="b" * 40,
        )

        # Track both
        result_main = tracker.track_manual_ingestion(identity_main)
        result_dev = tracker.track_manual_ingestion(identity_dev)

        # Both should be NEW (different unique_keys)
        assert result_main.is_new()
        assert result_dev.is_new()
        assert result_main.codebase_identity.unique_key != result_dev.codebase_identity.unique_key

    def test_same_branch_different_commits_is_update(self, neo4j_driver: Driver):
        """Test that same branch with different commits is an update."""
        tracker = IngestionTracker(neo4j_driver)

        # First commit
        identity1 = CodebaseIdentifier.create_manual_identity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="a" * 40,
        )

        # Second commit (same branch)
        identity2 = CodebaseIdentifier.create_manual_identity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="b" * 40,
        )

        # Track both
        result1 = tracker.track_manual_ingestion(identity1)
        result2 = tracker.track_manual_ingestion(identity2)

        # First should be NEW, second should be UPDATE
        assert result1.is_new()
        assert result2.is_update()
        # Same unique_key
        assert identity1.unique_key == identity2.unique_key

    def test_context_manager(self, neo4j_driver: Driver):
        """Test using tracker as context manager."""
        with IngestionTracker(neo4j_driver) as tracker:
            assert tracker.driver == neo4j_driver
            assert tracker.schema.verify_schema()

        # Driver should be closed after context
        # Note: We can't easily test this without checking internal state

    def test_close(self, neo4j_driver: Driver):
        """Test explicit close."""
        tracker = IngestionTracker(neo4j_driver)
        tracker.close()

        # After close, operations should fail
        with pytest.raises(Exception):
            tracker.get_codebase_info("test-key")

    def test_ingestion_timestamps_are_different(self, neo4j_driver: Driver, sample_codebase_identity: CodebaseIdentity):
        """Test that multiple ingestions have different timestamps."""
        tracker = IngestionTracker(neo4j_driver)

        result1 = tracker.track_manual_ingestion(sample_codebase_identity)

        # Wait a bit to ensure different timestamp
        import time

        time.sleep(0.01)

        updated_identity = CodebaseIdentity(
            remote_url=sample_codebase_identity.remote_url,
            branch=sample_codebase_identity.branch,
            commit_sha="b" * 40,
            unique_key=sample_codebase_identity.unique_key,
        )
        result2 = tracker.track_manual_ingestion(updated_identity)

        assert result1.ingestion_metadata.timestamp < result2.ingestion_metadata.timestamp

    def test_ingestion_creates_audit_trail(self, neo4j_driver: Driver, sample_codebase_identity: CodebaseIdentity):
        """Test that ingestions create a proper audit trail with SUPERSEDED_BY links."""
        tracker = IngestionTracker(neo4j_driver)

        # Create chain of ingestions
        results = []
        for i in range(3):
            identity = CodebaseIdentity(
                remote_url=sample_codebase_identity.remote_url,
                branch=sample_codebase_identity.branch,
                commit_sha=f"{i:040d}",
                unique_key=sample_codebase_identity.unique_key,
            )
            result = tracker.track_manual_ingestion(identity)
            results.append(result)

        # Verify SUPERSEDED_BY links exist
        with neo4j_driver.session() as session:
            # Check that ingestion 0 is superseded by ingestion 1
            result = session.run(
                """
                MATCH (prev:Ingestion {ingestion_id: $prev_id})-[:SUPERSEDED_BY]->(next:Ingestion {ingestion_id: $next_id})
                RETURN count(*) as count
                """,
                prev_id=results[0].ingestion_metadata.ingestion_id,
                next_id=results[1].ingestion_metadata.ingestion_id,
            )
            assert result.single()["count"] == 1

            # Check that ingestion 1 is superseded by ingestion 2
            result = session.run(
                """
                MATCH (prev:Ingestion {ingestion_id: $prev_id})-[:SUPERSEDED_BY]->(next:Ingestion {ingestion_id: $next_id})
                RETURN count(*) as count
                """,
                prev_id=results[1].ingestion_metadata.ingestion_id,
                next_id=results[2].ingestion_metadata.ingestion_id,
            )
            assert result.single()["count"] == 1
