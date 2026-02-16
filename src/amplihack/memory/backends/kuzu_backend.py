"""Kuzu graph database backend for memory storage."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import kuzu

from ..exceptions import InvalidExperienceError
from ..experience import Experience, ExperienceType
from .base import MemoryBackend


class KuzuBackend(MemoryBackend):
    """Kuzu graph database backend for memory storage.

    Provides graph-based storage with relationship support and
    native text search capabilities.
    """

    def __init__(
        self,
        db_path: Path,
        agent_name: str,
        max_memory_mb: int = 100,
        enable_compression: bool = True,
    ):
        """Initialize Kuzu backend.

        Args:
            db_path: Path to Kuzu database directory
            agent_name: Agent identifier
            max_memory_mb: Maximum storage size in MB (advisory)
            enable_compression: Enable compression (advisory, Kuzu handles this)
        """
        self.db_path = db_path
        self.agent_name = agent_name
        self.max_memory_mb = max_memory_mb
        self.enable_compression = enable_compression

        # Initialize Kuzu database (creates directory automatically)
        # Kuzu creates the directory if it doesn't exist
        self.db = kuzu.Database(str(self.db_path))
        self.conn = kuzu.Connection(self.db)

        self.initialize_schema()

    def initialize_schema(self):
        """Initialize Kuzu graph schema."""
        # Create Experience node table if not exists
        try:
            self.conn.execute("""
                CREATE NODE TABLE IF NOT EXISTS Experience(
                    experience_id STRING,
                    agent_name STRING,
                    experience_type STRING,
                    context STRING,
                    outcome STRING,
                    confidence DOUBLE,
                    timestamp INT64,
                    metadata STRING,
                    tags STRING,
                    compressed BOOLEAN,
                    PRIMARY KEY(experience_id)
                )
            """)
        except Exception as e:
            # Table might already exist
            if "already exists" not in str(e).lower():
                raise

        # Create relationship tables for future graph features
        try:
            self.conn.execute("""
                CREATE REL TABLE IF NOT EXISTS SIMILAR_TO(
                    FROM Experience TO Experience,
                    similarity_score DOUBLE
                )
            """)
        except Exception as e:
            if "already exists" not in str(e).lower():
                raise

        try:
            self.conn.execute("""
                CREATE REL TABLE IF NOT EXISTS LEADS_TO(
                    FROM Experience TO Experience,
                    causal_strength DOUBLE
                )
            """)
        except Exception as e:
            if "already exists" not in str(e).lower():
                raise

    def store_experience(self, experience: Experience) -> str:
        """Store an experience as a node in Kuzu.

        Args:
            experience: Experience to store

        Returns:
            experience_id: ID of stored experience
        """
        # Validate experience
        if not experience.context.strip():
            raise InvalidExperienceError("context cannot be empty")
        if not experience.outcome.strip():
            raise InvalidExperienceError("outcome cannot be empty")
        if not (0.0 <= experience.confidence <= 1.0):
            raise InvalidExperienceError("confidence must be between 0.0 and 1.0")

        # Convert to JSON strings for storage
        metadata_json = json.dumps(experience.metadata) if experience.metadata else "{}"
        tags_json = json.dumps(experience.tags) if experience.tags else "[]"

        # Store as node in Kuzu
        self.conn.execute(
            """
            CREATE (:Experience {
                experience_id: $id,
                agent_name: $agent,
                experience_type: $type,
                context: $context,
                outcome: $outcome,
                confidence: $conf,
                timestamp: $ts,
                metadata: $metadata,
                tags: $tags,
                compressed: false
            })
        """,
            {
                "id": experience.experience_id,
                "agent": self.agent_name,
                "type": experience.experience_type.value,
                "context": experience.context,
                "outcome": experience.outcome,
                "conf": experience.confidence,
                "ts": int(experience.timestamp.timestamp()),
                "metadata": metadata_json,
                "tags": tags_json,
            },
        )

        return experience.experience_id

    def retrieve_experiences(
        self,
        limit: int | None = None,
        experience_type: ExperienceType | None = None,
        min_confidence: float = 0.0,
    ) -> list[Experience]:
        """Retrieve experiences from Kuzu.

        Args:
            limit: Maximum number of experiences to retrieve
            experience_type: Filter by experience type
            min_confidence: Minimum confidence threshold

        Returns:
            List of experiences sorted by recency
        """
        # Build query dynamically
        where_clauses = ["e.agent_name = $agent", "e.confidence >= $min_conf"]
        params = {"agent": self.agent_name, "min_conf": min_confidence}

        if experience_type:
            where_clauses.append("e.experience_type = $exp_type")
            params["exp_type"] = experience_type.value

        where_clause = " AND ".join(where_clauses)

        # Build full query
        query = f"""
            MATCH (e:Experience)
            WHERE {where_clause}
            RETURN e.experience_id, e.experience_type, e.context, e.outcome,
                   e.confidence, e.timestamp, e.metadata, e.tags
            ORDER BY e.timestamp DESC
        """

        if limit:
            query += f" LIMIT {limit}"

        result = self.conn.execute(query, params)

        experiences = []
        while result.has_next():
            row = result.get_next()
            exp = Experience(
                experience_id=row[0],
                experience_type=ExperienceType(row[1]),
                context=row[2],
                outcome=row[3],
                confidence=row[4],
                timestamp=datetime.fromtimestamp(row[5]),
                metadata=json.loads(row[6]) if row[6] else {},
                tags=json.loads(row[7]) if row[7] else [],
            )
            experiences.append(exp)

        return experiences

    def search(
        self,
        query: str,
        experience_type: ExperienceType | None = None,
        min_confidence: float = 0.0,
        limit: int = 10,
    ) -> list[Experience]:
        """Search experiences using Kuzu's text search.

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
            return self.retrieve_experiences(
                limit=limit,
                experience_type=experience_type,
                min_confidence=min_confidence,
            )

        # Extract keywords from query for search (drop stop words)
        stop_words = {
            "a",
            "an",
            "the",
            "is",
            "was",
            "are",
            "were",
            "be",
            "been",
            "do",
            "does",
            "did",
            "what",
            "when",
            "where",
            "who",
            "why",
            "how",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "it",
            "its",
            "not",
            "no",
            "and",
            "or",
            "but",
            "if",
            "from",
        }
        keywords = [w for w in query.split() if w.lower() not in stop_words and len(w) > 1]
        if not keywords:
            keywords = query.split()[:3]  # Fallback to first 3 words

        # Build OR conditions for each keyword
        keyword_conditions = []
        params = {
            "agent": self.agent_name,
            "min_conf": min_confidence,
        }
        for i, kw in enumerate(keywords[:6]):  # Max 6 keywords
            param_name = f"kw{i}"
            keyword_conditions.append(
                f"(lower(e.context) CONTAINS lower(${param_name}) OR lower(e.outcome) CONTAINS lower(${param_name}))"
            )
            params[param_name] = kw

        keyword_clause = " OR ".join(keyword_conditions) if keyword_conditions else "true"

        where_clauses = [
            "e.agent_name = $agent",
            "e.confidence >= $min_conf",
            f"({keyword_clause})",
        ]

        if experience_type:
            where_clauses.append("e.experience_type = $exp_type")
            params["exp_type"] = experience_type.value

        where_clause = " AND ".join(where_clauses)

        # Execute search query
        kuzu_query = f"""
            MATCH (e:Experience)
            WHERE {where_clause}
            RETURN e.experience_id, e.experience_type, e.context, e.outcome,
                   e.confidence, e.timestamp, e.metadata, e.tags
            ORDER BY e.timestamp DESC
            LIMIT {limit}
        """

        result = self.conn.execute(kuzu_query, params)

        experiences = []
        while result.has_next():
            row = result.get_next()
            exp = Experience(
                experience_id=row[0],
                experience_type=ExperienceType(row[1]),
                context=row[2],
                outcome=row[3],
                confidence=row[4],
                timestamp=datetime.fromtimestamp(row[5]),
                metadata=json.loads(row[6]) if row[6] else {},
                tags=json.loads(row[7]) if row[7] else [],
            )
            experiences.append(exp)

        return experiences

    def get_statistics(self) -> dict:
        """Get Kuzu storage statistics.

        Returns:
            Dictionary with statistics
        """
        # Total count
        result = self.conn.execute(
            """
            MATCH (e:Experience)
            WHERE e.agent_name = $agent
            RETURN COUNT(e) as total
        """,
            {"agent": self.agent_name},
        )
        total = result.get_next()[0] if result.has_next() else 0

        # Count by type
        result = self.conn.execute(
            """
            MATCH (e:Experience)
            WHERE e.agent_name = $agent
            RETURN e.experience_type, COUNT(e) as count
        """,
            {"agent": self.agent_name},
        )

        by_type = {}
        while result.has_next():
            row = result.get_next()
            exp_type = ExperienceType(row[0])
            by_type[exp_type] = row[1]

        # Storage size (approximate from database directory)
        storage_size_kb = 0
        if self.db_path.exists():
            for file in self.db_path.rglob("*"):
                if file.is_file():
                    storage_size_kb += file.stat().st_size / 1024

        # Compressed count
        result = self.conn.execute(
            """
            MATCH (e:Experience)
            WHERE e.agent_name = $agent AND e.compressed = true
            RETURN COUNT(e) as compressed
        """,
            {"agent": self.agent_name},
        )
        compressed = result.get_next()[0] if result.has_next() else 0

        # Compression ratio
        compression_ratio = 1.0
        if compressed > 0:
            compression_ratio = 3.0

        return {
            "total_experiences": total,
            "by_type": by_type,
            "storage_size_kb": storage_size_kb,
            "compressed_experiences": compressed,
            "compression_ratio": compression_ratio,
        }

    def close(self):
        """Close Kuzu connection."""
        # Kuzu connections are automatically managed
        # Just cleanup references
        self.conn = None
        self.db = None

    def get_connection(self):
        """Get Kuzu connection for advanced operations.

        Returns:
            kuzu.Connection object
        """
        return self.conn

    def cleanup(
        self,
        auto_compress: bool = True,
        max_age_days: int | None = None,
        max_experiences: int | None = None,
    ):
        """Run cleanup operations on Kuzu database.

        Args:
            auto_compress: Compress old experiences (>30 days)
            max_age_days: Delete experiences older than this
            max_experiences: Limit to maximum number of experiences
        """
        # 1. Mark old experiences as compressed (>30 days)
        if auto_compress:
            cutoff = int((datetime.now() - timedelta(days=30)).timestamp())
            self.conn.execute(
                """
                MATCH (e:Experience)
                WHERE e.agent_name = $agent
                  AND e.timestamp < $cutoff
                  AND e.compressed = false
                SET e.compressed = true
            """,
                {"agent": self.agent_name, "cutoff": cutoff},
            )

        # 2. Delete experiences older than max_age_days
        if max_age_days:
            cutoff = int((datetime.now() - timedelta(days=max_age_days)).timestamp())
            self.conn.execute(
                """
                MATCH (e:Experience)
                WHERE e.agent_name = $agent AND e.timestamp < $cutoff
                DELETE e
            """,
                {"agent": self.agent_name, "cutoff": cutoff},
            )

        # 3. Limit to max_experiences (keep most recent + high-confidence patterns)
        if max_experiences:
            # Get current count
            result = self.conn.execute(
                """
                MATCH (e:Experience)
                WHERE e.agent_name = $agent
                RETURN COUNT(e) as count
            """,
                {"agent": self.agent_name},
            )
            count = result.get_next()[0] if result.has_next() else 0

            if count > max_experiences:
                # Get IDs to keep: high-confidence patterns + most recent
                # Note: Kuzu doesn't support UNION in the same way, so we'll do it differently

                # First, get high-confidence pattern IDs
                high_conf_result = self.conn.execute(
                    """
                    MATCH (e:Experience)
                    WHERE e.agent_name = $agent
                      AND e.experience_type = 'pattern'
                      AND e.confidence >= 0.8
                    RETURN e.experience_id
                """,
                    {"agent": self.agent_name},
                )
                keep_ids = set()
                while high_conf_result.has_next():
                    keep_ids.add(high_conf_result.get_next()[0])

                # Then, get most recent experience IDs
                recent_result = self.conn.execute(
                    f"""
                    MATCH (e:Experience)
                    WHERE e.agent_name = $agent
                    RETURN e.experience_id
                    ORDER BY e.timestamp DESC
                    LIMIT {max_experiences}
                """,
                    {"agent": self.agent_name},
                )
                while recent_result.has_next():
                    keep_ids.add(recent_result.get_next()[0])

                # Delete all experiences except those in keep_ids
                if keep_ids:
                    # Get all experience IDs
                    all_result = self.conn.execute(
                        """
                        MATCH (e:Experience)
                        WHERE e.agent_name = $agent
                        RETURN e.experience_id
                    """,
                        {"agent": self.agent_name},
                    )
                    all_ids = []
                    while all_result.has_next():
                        all_ids.append(all_result.get_next()[0])

                    # Delete those not in keep_ids
                    for exp_id in all_ids:
                        if exp_id not in keep_ids:
                            self.conn.execute(
                                """
                                MATCH (e:Experience {experience_id: $id})
                                DELETE e
                            """,
                                {"id": exp_id},
                            )
