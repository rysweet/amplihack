"""Main tracking logic for code ingestion metadata.

This module provides the high-level API for tracking code ingestions in Neo4j,
implementing the decision logic for new vs. update operations.
"""

import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from neo4j import Driver

from .identifier import CodebaseIdentifier
from .models import CodebaseIdentity, IngestionMetadata, IngestionResult, IngestionStatus
from .neo4j_schema import Neo4jSchema
from .query_builder import QueryBuilder


class IngestionTracker:
    """Track code ingestion metadata in Neo4j.

    This class provides the main API for tracking code ingestions, implementing
    the decision logic for whether to create a new codebase or update an existing one.

    The decision logic is:
    - Same unique_key → UPDATE (increment counter, new Ingestion node)
    - Different unique_key → NEW (create Codebase and Ingestion)
    """

    def __init__(self, driver: Driver, auto_initialize: bool = True):
        """Initialize ingestion tracker.

        Args:
            driver: Neo4j driver instance
            auto_initialize: Whether to automatically initialize schema
        """
        self.driver = driver
        self.schema = Neo4jSchema(driver)
        self.query_builder = QueryBuilder()

        if auto_initialize:
            self.schema.initialize_schema()

    def track_ingestion(
        self,
        repo_path: Path,
        metadata: Optional[dict[str, str]] = None,
    ) -> IngestionResult:
        """Track a code ingestion from a Git repository.

        This is the main entry point for tracking ingestions. It:
        1. Extracts codebase identity from Git
        2. Checks if this codebase has been ingested before
        3. Creates or updates the tracking metadata accordingly

        Args:
            repo_path: Path to Git repository
            metadata: Optional additional metadata to store

        Returns:
            IngestionResult with status and metadata

        Raises:
            ValueError: If repo_path is not a valid Git repository
            RuntimeError: If database operation fails
        """
        try:
            # Extract codebase identity from Git
            identity = CodebaseIdentifier.from_git_repo(repo_path)
            return self._track_ingestion_impl(identity, metadata)

        except (ValueError, RuntimeError) as e:
            # Return error result instead of raising
            error_identity = CodebaseIdentity(
                remote_url="error",
                branch="error",
                commit_sha="0" * 40,
                unique_key="error",
            )
            error_metadata = IngestionMetadata(
                ingestion_id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                commit_sha="0" * 40,
                ingestion_counter=1,
            )
            return IngestionResult(
                status=IngestionStatus.ERROR,
                codebase_identity=error_identity,
                ingestion_metadata=error_metadata,
                error_message=str(e),
            )

    def track_manual_ingestion(
        self,
        identity: CodebaseIdentity,
        metadata: Optional[dict[str, str]] = None,
    ) -> IngestionResult:
        """Track an ingestion with manually provided identity.

        Useful for testing or when Git access is not available.

        Args:
            identity: Codebase identity
            metadata: Optional additional metadata

        Returns:
            IngestionResult with status and metadata
        """
        try:
            # Validate identity
            if not CodebaseIdentifier.validate_identity(identity):
                raise ValueError("Invalid codebase identity")

            return self._track_ingestion_impl(identity, metadata)

        except Exception as e:
            error_metadata = IngestionMetadata(
                ingestion_id=str(uuid.uuid4()),
                timestamp=datetime.now(),
                commit_sha=identity.commit_sha,
                ingestion_counter=1,
            )
            return IngestionResult(
                status=IngestionStatus.ERROR,
                codebase_identity=identity,
                ingestion_metadata=error_metadata,
                error_message=str(e),
            )

    def _track_ingestion_impl(
        self,
        identity: CodebaseIdentity,
        metadata: Optional[dict[str, str]] = None,
    ) -> IngestionResult:
        """Core implementation of ingestion tracking logic.

        Shared by both track_ingestion() and track_manual_ingestion().

        Args:
            identity: Validated codebase identity
            metadata: Optional additional metadata

        Returns:
            IngestionResult with status and metadata

        Raises:
            RuntimeError: If database operation fails
        """
        # Generate ingestion metadata
        ingestion_id = str(uuid.uuid4())
        timestamp = datetime.now()

        # Check if codebase exists
        existing_ingestion = self._get_latest_ingestion(identity.unique_key)

        if existing_ingestion is None:
            # New codebase - create everything
            ingestion_counter = 1
            ingestion_metadata = IngestionMetadata(
                ingestion_id=ingestion_id,
                timestamp=timestamp,
                commit_sha=identity.commit_sha,
                ingestion_counter=ingestion_counter,
                metadata=metadata or {},
            )

            self._create_new_codebase(identity, ingestion_metadata)

            return IngestionResult(
                status=IngestionStatus.NEW,
                codebase_identity=identity,
                ingestion_metadata=ingestion_metadata,
                previous_ingestion_id=None,
            )
        # Existing codebase - update
        previous_counter = existing_ingestion["ingestion_counter"]
        previous_ingestion_id = existing_ingestion["ingestion_id"]

        ingestion_counter = previous_counter + 1
        ingestion_metadata = IngestionMetadata(
            ingestion_id=ingestion_id,
            timestamp=timestamp,
            commit_sha=identity.commit_sha,
            ingestion_counter=ingestion_counter,
            metadata=metadata or {},
        )

        self._update_existing_codebase(identity, ingestion_metadata, previous_ingestion_id)

        return IngestionResult(
            status=IngestionStatus.UPDATE,
            codebase_identity=identity,
            ingestion_metadata=ingestion_metadata,
            previous_ingestion_id=previous_ingestion_id,
        )

    def get_ingestion_history(self, unique_key: str) -> List[dict]:
        """Get complete ingestion history for a codebase.

        Args:
            unique_key: Unique key of the codebase

        Returns:
            List of ingestion records in chronological order
        """
        with self.driver.session() as session:
            query = self.query_builder.get_ingestion_history()
            result = session.run(query, unique_key=unique_key)

            history = []
            for record in result:
                ingestion = dict(record["i"])
                history.append(ingestion)

            return history

    def get_codebase_info(self, unique_key: str) -> Optional[dict]:
        """Get codebase information by unique key.

        Args:
            unique_key: Unique key of the codebase

        Returns:
            Codebase information dict or None if not found
        """
        with self.driver.session() as session:
            query, param_name = self.query_builder.get_codebase_by_unique_key()
            result = session.run(query, **{param_name: unique_key})

            record = result.single()
            if record:
                return dict(record["c"])
            return None

    def _get_latest_ingestion(self, unique_key: str) -> Optional[dict]:
        """Get the latest ingestion for a codebase.

        Args:
            unique_key: Unique key of the codebase

        Returns:
            Ingestion dict or None if no ingestions exist
        """
        with self.driver.session() as session:
            query = self.query_builder.get_latest_ingestion()
            result = session.run(query, unique_key=unique_key)

            record = result.single()
            if record:
                return dict(record["i"])
            return None

    def _create_new_codebase(
        self,
        identity: CodebaseIdentity,
        metadata: IngestionMetadata,
    ) -> None:
        """Create new codebase and ingestion in a transaction.

        Args:
            identity: Codebase identity
            metadata: Ingestion metadata

        Raises:
            RuntimeError: If database operation fails
        """
        try:
            with self.driver.session() as session:
                query, params = self.query_builder.track_new_codebase(identity, metadata)

                # Use parameterized queries for security (no additional validation needed)
                session.run(query, **params)

        except Exception as e:
            raise RuntimeError(f"Failed to create new codebase: {e}") from e

    def _update_existing_codebase(
        self,
        identity: CodebaseIdentity,
        metadata: IngestionMetadata,
        previous_ingestion_id: str,
    ) -> None:
        """Update existing codebase with new ingestion.

        Args:
            identity: Codebase identity
            metadata: Ingestion metadata
            previous_ingestion_id: ID of previous ingestion

        Raises:
            RuntimeError: If database operation fails
        """
        try:
            with self.driver.session() as session:
                query, params = self.query_builder.track_update_codebase(
                    identity,
                    metadata,
                    previous_ingestion_id,
                )

                # Use parameterized queries for security (no additional validation needed)
                session.run(query, **params)

        except Exception as e:
            raise RuntimeError(f"Failed to update codebase: {e}") from e

    def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()

    def __enter__(self) -> "IngestionTracker":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
