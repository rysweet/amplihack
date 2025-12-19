"""Memory consolidation and quality management.

Handles:
- Memory promotion (project -> global when pattern detected)
- Quality scoring and ranking
- Automatic decay of old/unused memories
- Duplicate detection and merging
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from .connector import Neo4jConnector
from .exceptions import Neo4jConnectionError

logger = logging.getLogger(__name__)


@dataclass
class QualityMetrics:
    """Quality metrics for a memory."""

    memory_id: str
    access_count: int  # Number of times accessed
    age_days: float  # Age in days
    importance: int  # User-assigned importance (1-10)
    tag_richness: int  # Number of tags
    relationship_count: int  # Number of relationships
    quality_score: float  # Combined score (0.0-1.0)

    @classmethod
    def calculate_score(
        cls,
        access_count: int,
        age_days: float,
        importance: int,
        tag_richness: int,
        relationship_count: int,
    ) -> float:
        """Calculate quality score from metrics.

        Score components:
        - Access frequency: 30% (normalized by age)
        - Importance: 30%
        - Tag richness: 20%
        - Relationships: 20%

        Args:
            access_count: Number of accesses
            age_days: Age in days
            importance: User importance (1-10)
            tag_richness: Number of tags
            relationship_count: Number of relationships

        Returns:
            Quality score 0.0-1.0
        """
        # Normalize access frequency by age (avoid division by zero)
        access_frequency = access_count / max(age_days, 1.0)
        access_score = min(access_frequency / 10.0, 1.0)  # Cap at 10 accesses/day

        # Normalize importance
        importance_score = importance / 10.0

        # Normalize tag richness (cap at 10 tags)
        tag_score = min(tag_richness / 10.0, 1.0)

        # Normalize relationships (cap at 10 relationships)
        relationship_score = min(relationship_count / 10.0, 1.0)

        # Weighted combination
        score = (
            0.3 * access_score + 0.3 * importance_score + 0.2 * tag_score + 0.2 * relationship_score
        )

        return round(score, 3)


class MemoryConsolidator:
    """Manages memory consolidation and quality.

    Responsibilities:
    - Promote high-quality project memories to global
    - Calculate and update quality scores
    - Decay old/unused memories
    - Detect and merge duplicates
    """

    def __init__(
        self,
        connector: Neo4jConnector,
        promotion_threshold: float = 0.8,
        decay_threshold_days: int = 90,
    ):
        """Initialize consolidator.

        Args:
            connector: Connected Neo4jConnector
            promotion_threshold: Quality score needed for global promotion
            decay_threshold_days: Age threshold for decay consideration
        """
        self.conn = connector
        self.promotion_threshold = promotion_threshold
        self.decay_threshold_days = decay_threshold_days

    def calculate_quality_scores(self, project_id: str | None = None) -> list[QualityMetrics]:
        """Calculate quality scores for memories.

        Args:
            project_id: Optional project filter (None = all projects)

        Returns:
            List of QualityMetrics for all memories
        """
        project_filter = "p.id = $project_id" if project_id else "true"
        params = {"project_id": project_id} if project_id else {}

        query = f"""
        MATCH (m:Memory)-[:BELONGS_TO]->(p:Project)
        WHERE {project_filter}
        OPTIONAL MATCH (m)-[r:RELATED_TO]-()
        WITH m,
             m.access_count as access_count,
             (timestamp() - m.created_at) / (1000.0 * 86400.0) as age_days,
             coalesce(m.importance, 5) as importance,
             size(coalesce(m.tags, [])) as tag_richness,
             count(DISTINCT r) as relationship_count
        RETURN m.id as memory_id,
               access_count,
               age_days,
               importance,
               tag_richness,
               relationship_count
        ORDER BY age_days ASC
        """

        try:
            results = self.conn.execute_query(query, params)

            metrics = []
            for r in results:
                quality_score = QualityMetrics.calculate_score(
                    access_count=r["access_count"] or 0,
                    age_days=r["age_days"] or 0.0,
                    importance=r["importance"] or 5,
                    tag_richness=r["tag_richness"] or 0,
                    relationship_count=r["relationship_count"] or 0,
                )

                metrics.append(
                    QualityMetrics(
                        memory_id=r["memory_id"],
                        access_count=r["access_count"] or 0,
                        age_days=r["age_days"] or 0.0,
                        importance=r["importance"] or 5,
                        tag_richness=r["tag_richness"] or 0,
                        relationship_count=r["relationship_count"] or 0,
                        quality_score=quality_score,
                    )
                )

            logger.info("Calculated quality scores for %d memories", len(metrics))
            return metrics

        except Exception as e:
            logger.error("Failed to calculate quality scores: %s", e)
            raise Neo4jConnectionError(f"Query failed: {e}")

    def update_quality_scores(self, metrics: list[QualityMetrics]) -> int:
        """Update quality scores in database.

        Args:
            metrics: List of QualityMetrics to update

        Returns:
            Number of memories updated
        """
        if not metrics:
            return 0

        query = """
        UNWIND $metrics as metric
        MATCH (m:Memory {id: metric.memory_id})
        SET m.quality_score = metric.quality_score,
            m.last_quality_update = timestamp()
        RETURN count(m) as updated
        """

        params = {
            "metrics": [
                {
                    "memory_id": m.memory_id,
                    "quality_score": m.quality_score,
                }
                for m in metrics
            ]
        }

        try:
            results = self.conn.execute_write(query, params)
            updated = results[0]["updated"] if results else 0
            logger.info("Updated quality scores for %d memories", updated)
            return updated

        except Exception as e:
            logger.error("Failed to update quality scores: %s", e)
            raise Neo4jConnectionError(f"Query failed: {e}")

    def promote_to_global(self, project_id: str, min_score: float | None = None) -> list[str]:
        """Promote high-quality project memories to global scope.

        Memories are promoted when:
        - Quality score exceeds threshold
        - Pattern detected across multiple sessions
        - Explicitly marked for promotion

        Args:
            project_id: Project to promote from
            min_score: Minimum quality score (default: promotion_threshold)

        Returns:
            List of promoted memory IDs
        """
        min_score = min_score or self.promotion_threshold

        # Find high-quality memories not already global
        query = """
        MATCH (m:Memory)-[:BELONGS_TO]->(p:Project {id: $project_id})
        WHERE m.quality_score >= $min_score
          AND NOT exists((m)-[:BELONGS_TO]->(:Project {id: 'global'}))
        RETURN m.id as memory_id
        LIMIT 100
        """

        try:
            results = self.conn.execute_query(
                query, {"project_id": project_id, "min_score": min_score}
            )

            if not results:
                logger.info("No memories eligible for promotion")
                return []

            memory_ids = [r["memory_id"] for r in results]

            # Create relationships to global project
            promotion_query = """
            MATCH (m:Memory)
            WHERE m.id IN $memory_ids
            MERGE (global:Project {id: 'global'})
            MERGE (m)-[:BELONGS_TO]->(global)
            SET m.promoted_at = timestamp(),
                m.promoted_from = $project_id
            RETURN count(m) as promoted
            """

            promotion_results = self.conn.execute_write(
                promotion_query, {"memory_ids": memory_ids, "project_id": project_id}
            )

            promoted_count = promotion_results[0]["promoted"] if promotion_results else 0
            logger.info("Promoted %d memories to global scope", promoted_count)

            return memory_ids

        except Exception as e:
            logger.error("Failed to promote memories: %s", e)
            raise Neo4jConnectionError(f"Query failed: {e}")

    def apply_decay(self, dry_run: bool = False) -> list[str]:
        """Apply decay to old/unused memories.

        Memories are decayed when:
        - Older than decay_threshold_days
        - Low access frequency
        - Low quality score

        Decay actions:
        - Reduce importance score
        - Mark for archival
        - Eventually delete if unused

        Args:
            dry_run: If True, return candidates without applying decay

        Returns:
            List of memory IDs affected by decay
        """
        cutoff_timestamp = int(
            (datetime.now() - timedelta(days=self.decay_threshold_days)).timestamp() * 1000
        )

        # Find decay candidates
        query = """
        MATCH (m:Memory)
        WHERE m.created_at < $cutoff_timestamp
          AND m.access_count < 5
          AND coalesce(m.quality_score, 0) < 0.5
          AND NOT m:Archived
        RETURN m.id as memory_id, m.quality_score as quality_score
        LIMIT 100
        """

        try:
            results = self.conn.execute_query(query, {"cutoff_timestamp": cutoff_timestamp})

            if not results:
                logger.info("No memories eligible for decay")
                return []

            memory_ids = [r["memory_id"] for r in results]

            if dry_run:
                logger.info("Dry run: %d memories would be decayed", len(memory_ids))
                return memory_ids

            # Apply decay
            decay_query = """
            MATCH (m:Memory)
            WHERE m.id IN $memory_ids
            SET m.importance = CASE
                WHEN m.importance > 1 THEN m.importance - 1
                ELSE 1
            END,
            m.decayed_at = timestamp(),
            m:Archived = true
            RETURN count(m) as decayed
            """

            decay_results = self.conn.execute_write(decay_query, {"memory_ids": memory_ids})
            decayed_count = decay_results[0]["decayed"] if decay_results else 0

            logger.info("Applied decay to %d memories", decayed_count)
            return memory_ids

        except Exception as e:
            logger.error("Failed to apply decay: %s", e)
            raise Neo4jConnectionError(f"Query failed: {e}")

    def detect_duplicates(
        self, project_id: str, similarity_threshold: float = 0.9
    ) -> list[tuple[str, str]]:
        """Detect potential duplicate memories.

        Uses tag overlap and creation time proximity to identify duplicates.

        Args:
            project_id: Project to check
            similarity_threshold: Tag overlap threshold (0.0-1.0)

        Returns:
            List of (memory_id_1, memory_id_2) duplicate pairs
        """
        query = """
        MATCH (m1:Memory)-[:BELONGS_TO]->(p:Project {id: $project_id})
        MATCH (m2:Memory)-[:BELONGS_TO]->(p)
        WHERE m1.id < m2.id
          AND m1.memory_type = m2.memory_type
          AND abs(m1.created_at - m2.created_at) < 3600000
          AND m1.tags IS NOT NULL
          AND m2.tags IS NOT NULL
        WITH m1, m2,
             [tag IN m1.tags WHERE tag IN m2.tags] as common_tags,
             m1.tags + [tag IN m2.tags WHERE NOT tag IN m1.tags] as all_tags
        WHERE size(common_tags) > 0
        WITH m1.id as id1, m2.id as id2,
             toFloat(size(common_tags)) / size(all_tags) as similarity
        WHERE similarity >= $similarity_threshold
        RETURN id1, id2, similarity
        ORDER BY similarity DESC
        LIMIT 50
        """

        try:
            results = self.conn.execute_query(
                query, {"project_id": project_id, "similarity_threshold": similarity_threshold}
            )

            duplicates = [(r["id1"], r["id2"]) for r in results]
            logger.info("Found %d potential duplicate pairs", len(duplicates))
            return duplicates

        except Exception as e:
            logger.error("Failed to detect duplicates: %s", e)
            raise Neo4jConnectionError(f"Query failed: {e}")

    def merge_duplicates(self, memory_id_1: str, memory_id_2: str, keep_first: bool = True) -> bool:
        """Merge two duplicate memories.

        Args:
            memory_id_1: First memory ID
            memory_id_2: Second memory ID
            keep_first: If True, keep first and merge second into it

        Returns:
            True if merged successfully
        """
        keep_id = memory_id_1 if keep_first else memory_id_2
        merge_id = memory_id_2 if keep_first else memory_id_1

        query = """
        MATCH (keep:Memory {id: $keep_id})
        MATCH (merge:Memory {id: $merge_id})

        // Merge tags
        SET keep.tags = keep.tags + [tag IN merge.tags WHERE NOT tag IN keep.tags]

        // Merge metadata
        SET keep.metadata = keep.metadata + merge.metadata

        // Transfer relationships
        WITH keep, merge
        MATCH (merge)-[r:RELATED_TO]-(other)
        WHERE NOT exists((keep)-[:RELATED_TO]-(other))
        CREATE (keep)-[:RELATED_TO]->(other)

        // Mark merged memory as archived
        SET merge.merged_into = $keep_id,
            merge.merged_at = timestamp(),
            merge:Archived = true

        RETURN true as success
        """

        try:
            results = self.conn.execute_write(query, {"keep_id": keep_id, "merge_id": merge_id})

            success = results[0]["success"] if results else False
            if success:
                logger.info("Merged memory %s into %s", merge_id, keep_id)
            else:
                logger.warning("Failed to merge memories")

            return success

        except Exception as e:
            logger.error("Failed to merge duplicates: %s", e)
            return False


# Convenience functions


def run_consolidation(
    connector: Neo4jConnector,
    project_id: str,
    promotion_threshold: float = 0.8,
) -> dict[str, int]:
    """Run full consolidation process for a project.

    Args:
        connector: Neo4jConnector instance
        project_id: Project to consolidate
        promotion_threshold: Score threshold for promotion

    Returns:
        Dictionary with consolidation statistics
    """
    consolidator = MemoryConsolidator(connector, promotion_threshold=promotion_threshold)

    # Calculate and update quality scores
    metrics = consolidator.calculate_quality_scores(project_id)
    updated = consolidator.update_quality_scores(metrics)

    # Promote high-quality memories
    promoted = consolidator.promote_to_global(project_id)

    # Apply decay
    decayed = consolidator.apply_decay(dry_run=False)

    # Detect duplicates
    duplicates = consolidator.detect_duplicates(project_id)

    return {
        "quality_scores_updated": updated,
        "memories_promoted": len(promoted),
        "memories_decayed": len(decayed),
        "duplicate_pairs_found": len(duplicates),
    }
