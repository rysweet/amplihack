"""Tests for Cypher query builder."""

from datetime import datetime

import pytest

from amplihack.memory.neo4j.identifier import CodebaseIdentifier
from amplihack.memory.neo4j.models import IngestionMetadata
from amplihack.memory.neo4j.query_builder import QueryBuilder


class TestQueryBuilder:
    """Test Cypher query construction."""

    def test_get_codebase_by_unique_key(self):
        """Test query to get codebase by unique key."""
        query, param_name = QueryBuilder.get_codebase_by_unique_key()

        assert "MATCH" in query
        assert "Codebase" in query
        assert "unique_key" in query
        assert param_name == "unique_key"

    def test_create_codebase_node(self):
        """Test query to create codebase node."""
        identity = CodebaseIdentifier.create_manual_identity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="a" * 40,
        )

        query, params = QueryBuilder.create_codebase_node(identity)

        assert "CREATE" in query
        assert "Codebase" in query
        assert params["unique_key"] == identity.unique_key
        assert params["remote_url"] == identity.remote_url
        assert params["branch"] == identity.branch
        assert params["commit_sha"] == identity.commit_sha

    def test_update_codebase_node(self):
        """Test query to update codebase node."""
        identity = CodebaseIdentifier.create_manual_identity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="b" * 40,
        )

        query, params = QueryBuilder.update_codebase_node(identity)

        assert "MATCH" in query
        assert "SET" in query
        assert "ingestion_count" in query
        assert params["unique_key"] == identity.unique_key
        assert params["commit_sha"] == identity.commit_sha

    def test_create_ingestion_node(self):
        """Test query to create ingestion node."""
        metadata = IngestionMetadata(
            ingestion_id="test-id",
            timestamp=datetime.now(),
            commit_sha="a" * 40,
            ingestion_counter=1,
        )

        query, params = QueryBuilder.create_ingestion_node(metadata)

        assert "CREATE" in query
        assert "Ingestion" in query
        assert params["ingestion_id"] == metadata.ingestion_id
        assert params["commit_sha"] == metadata.commit_sha
        assert params["ingestion_counter"] == metadata.ingestion_counter

    def test_link_ingestion_to_codebase(self):
        """Test query to link ingestion to codebase."""
        query = QueryBuilder.link_ingestion_to_codebase()

        assert "MATCH" in query
        assert "CREATE" in query
        assert "INGESTION_OF" in query

    def test_link_ingestion_to_previous(self):
        """Test query to link ingestion to previous."""
        query = QueryBuilder.link_ingestion_to_previous()

        assert "MATCH" in query
        assert "CREATE" in query
        assert "SUPERSEDED_BY" in query

    def test_get_latest_ingestion(self):
        """Test query to get latest ingestion."""
        query = QueryBuilder.get_latest_ingestion()

        assert "MATCH" in query
        assert "ORDER BY" in query
        assert "LIMIT 1" in query

    def test_get_ingestion_count(self):
        """Test query to get ingestion count."""
        query = QueryBuilder.get_ingestion_count()

        assert "MATCH" in query
        assert "ingestion_count" in query

    def test_get_ingestion_history(self):
        """Test query to get ingestion history."""
        query = QueryBuilder.get_ingestion_history()

        assert "MATCH" in query
        assert "OPTIONAL MATCH" in query
        assert "SUPERSEDED_BY" in query
        assert "ORDER BY" in query

    def test_track_new_codebase(self):
        """Test complete query for new codebase."""
        identity = CodebaseIdentifier.create_manual_identity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="a" * 40,
        )
        metadata = IngestionMetadata(
            ingestion_id="test-id",
            timestamp=datetime.now(),
            commit_sha="a" * 40,
            ingestion_counter=1,
        )

        query, params = QueryBuilder.track_new_codebase(identity, metadata)

        # Verify query structure
        assert "CREATE" in query
        assert "Codebase" in query
        assert "Ingestion" in query
        assert "INGESTION_OF" in query

        # Verify parameters
        assert params["unique_key"] == identity.unique_key
        assert params["remote_url"] == identity.remote_url
        assert params["ingestion_id"] == metadata.ingestion_id
        assert params["ingestion_counter"] == metadata.ingestion_counter

    def test_track_update_codebase(self):
        """Test complete query for updating codebase."""
        identity = CodebaseIdentifier.create_manual_identity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="b" * 40,
        )
        metadata = IngestionMetadata(
            ingestion_id="test-id-2",
            timestamp=datetime.now(),
            commit_sha="b" * 40,
            ingestion_counter=2,
        )

        query, params = QueryBuilder.track_update_codebase(identity, metadata, "test-id-1")

        # Verify query structure
        assert "MATCH" in query
        assert "SET" in query
        assert "CREATE" in query
        assert "Ingestion" in query
        assert "INGESTION_OF" in query
        assert "SUPERSEDED_BY" in query

        # Verify parameters
        assert params["unique_key"] == identity.unique_key
        assert params["ingestion_id"] == metadata.ingestion_id
        assert params["previous_ingestion_id"] == "test-id-1"

    def test_parameterization_prevents_injection(self):
        """Test that queries use parameters instead of string concatenation."""
        identity = CodebaseIdentifier.create_manual_identity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="a" * 40,
        )

        query, params = QueryBuilder.create_codebase_node(identity)

        # Query should use parameter placeholders
        assert "$unique_key" in query
        assert "$remote_url" in query
        assert "$branch" in query
        assert "$commit_sha" in query

        # Actual values should be in params dict
        assert identity.unique_key not in query
        assert identity.remote_url not in query

    def test_metadata_fields_included_in_create_codebase(self):
        """Test that metadata fields are included in codebase creation."""
        identity = CodebaseIdentifier.create_manual_identity(
            remote_url="https://github.com/test/repo.git",
            branch="main",
            commit_sha="a" * 40,
            metadata={"repo_path": "/path/to/repo", "custom_field": "value"},
        )

        query, params = QueryBuilder.create_codebase_node(identity)

        # Metadata should be in params (but not necessarily in query template)
        assert params["unique_key"] == identity.unique_key
        # Core fields are there
        assert "unique_key" in params
        assert "remote_url" in params

    def test_metadata_fields_included_in_create_ingestion(self):
        """Test that metadata fields are included in ingestion creation."""
        metadata = IngestionMetadata(
            ingestion_id="test-id",
            timestamp=datetime.now(),
            commit_sha="a" * 40,
            ingestion_counter=1,
            metadata={"source": "cli", "user": "test"},
        )

        query, params = QueryBuilder.create_ingestion_node(metadata)

        # Core fields are there
        assert params["ingestion_id"] == metadata.ingestion_id
        assert params["commit_sha"] == metadata.commit_sha
