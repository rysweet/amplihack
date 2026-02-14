"""High-level experience storage and retrieval with automatic management."""

import json
from datetime import datetime, timedelta
from pathlib import Path

from .connector import MemoryConnector
from .exceptions import InvalidExperienceError, MemoryQuotaExceededError
from .experience import Experience, ExperienceType


class ExperienceStore:
    """High-level storage and retrieval of experiences with auto-management.

    Features:
    - Automatic compression of old experiences
    - Retention policies (max_age_days, max_experiences)
    - Duplicate detection
    - Full-text search
    - Statistics tracking

    Attributes:
        agent_name: Agent identifier
        auto_compress: Enable automatic compression
        max_age_days: Maximum age for experiences (days)
        max_experiences: Maximum number of experiences
        max_memory_mb: Maximum storage size (MB)
    """

    def __init__(
        self,
        agent_name: str,
        auto_compress: bool = True,
        max_age_days: int | None = None,
        max_experiences: int | None = None,
        max_memory_mb: int = 100,
        storage_path: Path | None = None,
    ):
        """Initialize experience store.

        Args:
            agent_name: Agent identifier
            auto_compress: Enable automatic compression (default: True)
            max_age_days: Maximum age for experiences (None = no limit)
            max_experiences: Maximum number of experiences (None = no limit)
            max_memory_mb: Maximum storage size in MB
            storage_path: Storage directory (optional)
        """
        self.agent_name = agent_name
        self.auto_compress = auto_compress
        self.max_age_days = max_age_days
        self.max_experiences = max_experiences
        self.max_memory_mb = max_memory_mb

        # Initialize connector
        self.connector = MemoryConnector(
            agent_name=agent_name,
            storage_path=storage_path,
            max_memory_mb=max_memory_mb,
            enable_compression=auto_compress,
        )

    def add(self, experience: Experience) -> str:
        """Add experience with automatic management.

        Args:
            experience: Experience to add

        Returns:
            experience_id: ID of stored experience

        Raises:
            InvalidExperienceError: If experience is invalid
            MemoryQuotaExceededError: If storage quota exceeded
        """
        # Validate experience
        self._validate_experience(experience)

        # Check storage quota
        self._check_quota()

        # Store experience
        exp_id = self.connector.store_experience(experience)

        # Run cleanup if needed
        if self.auto_compress or self.max_age_days or self.max_experiences:
            self._cleanup()

        return exp_id

    def search(
        self,
        query: str,
        experience_type: ExperienceType | None = None,
        min_confidence: float = 0.0,
        limit: int = 10,
    ) -> list[Experience]:
        """Search experiences by text query.

        Uses SQLite FTS5 for full-text search.

        Args:
            query: Search query (text)
            experience_type: Filter by experience type
            min_confidence: Minimum confidence threshold
            limit: Maximum results

        Returns:
            List of matching experiences
        """
        if not query or not query.strip():
            # Empty query - return all experiences
            return self.connector.retrieve_experiences(
                limit=limit,
                experience_type=experience_type,
                min_confidence=min_confidence,
            )

        # Use FTS5 for text search
        sql = """
            SELECT e.* FROM experiences e
            JOIN experiences_fts fts ON e.experience_id = fts.experience_id
            WHERE fts.experiences_fts MATCH ?
            AND e.agent_name = ?
            AND e.confidence >= ?
        """
        params = [query, self.agent_name, min_confidence]

        if experience_type:
            sql += " AND e.experience_type = ?"
            params.append(experience_type.value)

        sql += " ORDER BY e.timestamp DESC LIMIT ?"
        params.append(limit)

        cursor = self.connector._connection.execute(sql, params)
        rows = cursor.fetchall()

        experiences = []
        for row in rows:
            exp = Experience(
                experience_id=row["experience_id"],
                experience_type=ExperienceType(row["experience_type"]),
                context=row["context"],
                outcome=row["outcome"],
                confidence=row["confidence"],
                timestamp=datetime.fromtimestamp(row["timestamp"]),
                metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                tags=json.loads(row["tags"]) if row["tags"] else [],
            )
            experiences.append(exp)

        return experiences

    def get_statistics(self) -> dict:
        """Get storage statistics.

        Returns:
            Dictionary with statistics:
            - total_experiences: Total count
            - by_type: Count by experience type
            - storage_size_kb: Storage size in KB
            - compressed_experiences: Count of compressed experiences
            - compression_ratio: Compression ratio (if compression enabled)
        """
        conn = self.connector._connection

        # Total count
        cursor = conn.execute(
            "SELECT COUNT(*) FROM experiences WHERE agent_name = ?", (self.agent_name,)
        )
        total = cursor.fetchone()[0]

        # Count by type
        by_type = {}
        cursor = conn.execute(
            """
            SELECT experience_type, COUNT(*) as count
            FROM experiences
            WHERE agent_name = ?
            GROUP BY experience_type
        """,
            (self.agent_name,),
        )

        for row in cursor:
            exp_type = ExperienceType(row["experience_type"])
            by_type[exp_type] = row["count"]

        # Storage size
        db_path = self.connector.db_path
        storage_size_kb = db_path.stat().st_size / 1024 if db_path.exists() else 0

        # Compressed count
        cursor = conn.execute(
            "SELECT COUNT(*) FROM experiences WHERE agent_name = ? AND compressed = 1",
            (self.agent_name,),
        )
        compressed = cursor.fetchone()[0]

        # Calculate compression ratio (simplified)
        compression_ratio = 1.0
        if compressed > 0:
            # Estimate: compressed experiences save ~3x space
            compression_ratio = 3.0

        return {
            "total_experiences": total,
            "by_type": by_type,
            "storage_size_kb": storage_size_kb,
            "compressed_experiences": compressed,
            "compression_ratio": compression_ratio,
        }

    def _cleanup(self):
        """Run cleanup: compression, age limit, count limit."""
        conn = self.connector._connection

        # 1. Compress old experiences (>30 days)
        if self.auto_compress:
            cutoff = int((datetime.now() - timedelta(days=30)).timestamp())
            conn.execute(
                """
                UPDATE experiences
                SET compressed = 1
                WHERE agent_name = ?
                AND timestamp < ?
                AND compressed = 0
            """,
                (self.agent_name, cutoff),
            )

        # 2. Delete experiences older than max_age_days
        if self.max_age_days:
            cutoff = int((datetime.now() - timedelta(days=self.max_age_days)).timestamp())
            conn.execute(
                """
                DELETE FROM experiences
                WHERE agent_name = ?
                AND timestamp < ?
            """,
                (self.agent_name, cutoff),
            )

        # 3. Limit to max_experiences (keep most recent + high-confidence patterns)
        if self.max_experiences:
            # Get count
            cursor = conn.execute(
                "SELECT COUNT(*) FROM experiences WHERE agent_name = ?", (self.agent_name,)
            )
            count = cursor.fetchone()[0]

            if count > self.max_experiences:
                # Keep high-confidence patterns regardless of age
                conn.execute(
                    """
                    DELETE FROM experiences
                    WHERE agent_name = ?
                    AND experience_id NOT IN (
                        SELECT experience_id FROM (
                            SELECT experience_id, timestamp FROM experiences
                            WHERE agent_name = ?
                            AND (
                                (experience_type = 'pattern' AND confidence >= 0.9)
                                OR experience_id IN (
                                    SELECT experience_id FROM experiences
                                    WHERE agent_name = ?
                                    ORDER BY timestamp DESC
                                    LIMIT ?
                                )
                            )
                            ORDER BY timestamp DESC
                        )
                    )
                """,
                    (self.agent_name, self.agent_name, self.agent_name, self.max_experiences),
                )

        # 4. Commit changes
        conn.commit()

        # 5. Vacuum database to reclaim space (must be outside transaction)
        conn.isolation_level = None
        conn.execute("VACUUM")
        conn.isolation_level = ""

    def _validate_experience(self, experience: Experience):
        """Validate experience before storage.

        Raises:
            InvalidExperienceError: If validation fails
        """
        if not experience.context.strip():
            raise InvalidExperienceError("context cannot be empty")

        if not experience.outcome.strip():
            raise InvalidExperienceError("outcome cannot be empty")

        if not (0.0 <= experience.confidence <= 1.0):
            raise InvalidExperienceError("confidence must be between 0.0 and 1.0")

    def _check_quota(self):
        """Check if storage quota is exceeded.

        Raises:
            MemoryQuotaExceededError: If quota exceeded
        """
        db_path = self.connector.db_path
        if not db_path.exists():
            return

        size_mb = db_path.stat().st_size / (1024 * 1024)
        if size_mb > self.max_memory_mb:
            raise MemoryQuotaExceededError(
                f"Storage quota exceeded: {size_mb:.1f}MB > {self.max_memory_mb}MB"
            )
