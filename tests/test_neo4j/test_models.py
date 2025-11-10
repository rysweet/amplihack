"""Tests for Neo4j data models."""

from datetime import datetime

import pytest

from amplihack.memory.neo4j.models import (
    CodebaseIdentity,
    IngestionMetadata,
    IngestionResult,
    IngestionStatus,
)


class TestCodebaseIdentity:
    """Test CodebaseIdentity model."""

    def test_create_valid_identity(self):
        """Test creating a valid CodebaseIdentity."""
        identity = CodebaseIdentity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="a" * 40,
            unique_key="b" * 64,
        )

        assert identity.remote_url == "https://github.com/test/repo.git"
        assert identity.branch == "main"
        assert identity.commit_sha == "a" * 40
        assert identity.unique_key == "b" * 64
        assert identity.metadata == {}

    def test_create_identity_with_metadata(self):
        """Test creating CodebaseIdentity with metadata."""
        metadata = {"repo_path": "/path/to/repo"}
        identity = CodebaseIdentity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="a" * 40,
            unique_key="b" * 64,
            metadata=metadata,
        )

        assert identity.metadata == metadata

    def test_missing_remote_url(self):
        """Test that missing remote_url raises ValueError."""
        with pytest.raises(ValueError, match="remote_url is required"):
            CodebaseIdentity(
                remote_url="",
                branch="main",
                commit_sha="a" * 40,
                unique_key="b" * 64,
            )

    def test_missing_branch(self):
        """Test that missing branch raises ValueError."""
        with pytest.raises(ValueError, match="branch is required"):
            CodebaseIdentity(
                remote_url="https://github.com/test/repo.git",
                branch="",
                commit_sha="a" * 40,
                unique_key="b" * 64,
            )

    def test_missing_commit_sha(self):
        """Test that missing commit_sha raises ValueError."""
        with pytest.raises(ValueError, match="commit_sha is required"):
            CodebaseIdentity(
                remote_url="https://github.com/test/repo.git",
                branch="main",
                commit_sha="",
                unique_key="b" * 64,
            )

    def test_missing_unique_key(self):
        """Test that missing unique_key raises ValueError."""
        with pytest.raises(ValueError, match="unique_key is required"):
            CodebaseIdentity(
                remote_url="https://github.com/test/repo.git",
                branch="main",
                commit_sha="a" * 40,
                unique_key="",
            )

    def test_to_dict(self):
        """Test converting to dictionary."""
        metadata = {"repo_path": "/path/to/repo"}
        identity = CodebaseIdentity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="a" * 40,
            unique_key="b" * 64,
            metadata=metadata,
        )

        result = identity.to_dict()

        assert result["remote_url"] == "https://github.com/test/repo.git"
        assert result["branch"] == "main"
        assert result["commit_sha"] == "a" * 40
        assert result["unique_key"] == "b" * 64
        assert result["repo_path"] == "/path/to/repo"

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "remote_url": "https://github.com/test/repo.git",
            "branch": "main",
            "commit_sha": "a" * 40,
            "unique_key": "b" * 64,
            "repo_path": "/path/to/repo",
        }

        identity = CodebaseIdentity.from_dict(data)

        assert identity.remote_url == "https://github.com/test/repo.git"
        assert identity.branch == "main"
        assert identity.commit_sha == "a" * 40
        assert identity.unique_key == "b" * 64
        assert identity.metadata == {"repo_path": "/path/to/repo"}


class TestIngestionMetadata:
    """Test IngestionMetadata model."""

    def test_create_valid_metadata(self):
        """Test creating valid IngestionMetadata."""
        timestamp = datetime.now()
        metadata = IngestionMetadata(
            ingestion_id="test-id",
            timestamp=timestamp,
            commit_sha="a" * 40,
            ingestion_counter=1,
        )

        assert metadata.ingestion_id == "test-id"
        assert metadata.timestamp == timestamp
        assert metadata.commit_sha == "a" * 40
        assert metadata.ingestion_counter == 1
        assert metadata.metadata == {}

    def test_create_metadata_with_extra(self):
        """Test creating IngestionMetadata with extra metadata."""
        extra = {"source": "cli"}
        metadata = IngestionMetadata(
            ingestion_id="test-id",
            timestamp=datetime.now(),
            commit_sha="a" * 40,
            ingestion_counter=1,
            metadata=extra,
        )

        assert metadata.metadata == extra

    def test_missing_ingestion_id(self):
        """Test that missing ingestion_id raises ValueError."""
        with pytest.raises(ValueError, match="ingestion_id is required"):
            IngestionMetadata(
                ingestion_id="",
                timestamp=datetime.now(),
                commit_sha="a" * 40,
                ingestion_counter=1,
            )

    def test_missing_commit_sha(self):
        """Test that missing commit_sha raises ValueError."""
        with pytest.raises(ValueError, match="commit_sha is required"):
            IngestionMetadata(
                ingestion_id="test-id",
                timestamp=datetime.now(),
                commit_sha="",
                ingestion_counter=1,
            )

    def test_invalid_counter(self):
        """Test that invalid ingestion_counter raises ValueError."""
        with pytest.raises(ValueError, match="ingestion_counter must be >= 1"):
            IngestionMetadata(
                ingestion_id="test-id",
                timestamp=datetime.now(),
                commit_sha="a" * 40,
                ingestion_counter=0,
            )

    def test_to_dict(self):
        """Test converting to dictionary."""
        timestamp = datetime.now()
        extra = {"source": "cli"}
        metadata = IngestionMetadata(
            ingestion_id="test-id",
            timestamp=timestamp,
            commit_sha="a" * 40,
            ingestion_counter=1,
            metadata=extra,
        )

        result = metadata.to_dict()

        assert result["ingestion_id"] == "test-id"
        assert result["timestamp"] == timestamp.isoformat()
        assert result["commit_sha"] == "a" * 40
        assert result["ingestion_counter"] == "1"
        assert result["source"] == "cli"

    def test_from_dict(self):
        """Test creating from dictionary."""
        timestamp = datetime.now()
        data = {
            "ingestion_id": "test-id",
            "timestamp": timestamp.isoformat(),
            "commit_sha": "a" * 40,
            "ingestion_counter": "1",
            "source": "cli",
        }

        metadata = IngestionMetadata.from_dict(data)

        assert metadata.ingestion_id == "test-id"
        assert metadata.timestamp.isoformat() == timestamp.isoformat()
        assert metadata.commit_sha == "a" * 40
        assert metadata.ingestion_counter == 1
        assert metadata.metadata == {"source": "cli"}


class TestIngestionResult:
    """Test IngestionResult model."""

    def test_create_new_result(self):
        """Test creating NEW status result."""
        identity = CodebaseIdentity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="a" * 40,
            unique_key="b" * 64,
        )
        metadata = IngestionMetadata(
            ingestion_id="test-id",
            timestamp=datetime.now(),
            commit_sha="a" * 40,
            ingestion_counter=1,
        )

        result = IngestionResult(
            status=IngestionStatus.NEW,
            codebase_identity=identity,
            ingestion_metadata=metadata,
        )

        assert result.status == IngestionStatus.NEW
        assert result.is_new()
        assert not result.is_update()
        assert not result.is_error()
        assert result.previous_ingestion_id is None
        assert result.error_message is None

    def test_create_update_result(self):
        """Test creating UPDATE status result."""
        identity = CodebaseIdentity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="a" * 40,
            unique_key="b" * 64,
        )
        metadata = IngestionMetadata(
            ingestion_id="test-id-2",
            timestamp=datetime.now(),
            commit_sha="b" * 40,
            ingestion_counter=2,
        )

        result = IngestionResult(
            status=IngestionStatus.UPDATE,
            codebase_identity=identity,
            ingestion_metadata=metadata,
            previous_ingestion_id="test-id-1",
        )

        assert result.status == IngestionStatus.UPDATE
        assert not result.is_new()
        assert result.is_update()
        assert not result.is_error()
        assert result.previous_ingestion_id == "test-id-1"

    def test_create_error_result(self):
        """Test creating ERROR status result."""
        identity = CodebaseIdentity(
            remote_url="error",
            branch="error",
            commit_sha="0" * 40,
            unique_key="error",
        )
        metadata = IngestionMetadata(
            ingestion_id="error-id",
            timestamp=datetime.now(),
            commit_sha="0" * 40,
            ingestion_counter=1,
        )

        result = IngestionResult(
            status=IngestionStatus.ERROR,
            codebase_identity=identity,
            ingestion_metadata=metadata,
            error_message="Test error",
        )

        assert result.status == IngestionStatus.ERROR
        assert not result.is_new()
        assert not result.is_update()
        assert result.is_error()
        assert result.error_message == "Test error"

    def test_to_dict(self):
        """Test converting to dictionary."""
        identity = CodebaseIdentity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="a" * 40,
            unique_key="b" * 64,
        )
        metadata = IngestionMetadata(
            ingestion_id="test-id",
            timestamp=datetime.now(),
            commit_sha="a" * 40,
            ingestion_counter=1,
        )

        result = IngestionResult(
            status=IngestionStatus.NEW,
            codebase_identity=identity,
            ingestion_metadata=metadata,
        )

        result_dict = result.to_dict()

        assert result_dict["status"] == "new"
        assert "codebase_identity" in result_dict
        assert "ingestion_metadata" in result_dict
        assert result_dict["previous_ingestion_id"] is None
        assert result_dict["error_message"] is None
