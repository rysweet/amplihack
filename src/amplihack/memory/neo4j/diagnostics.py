"""Neo4j diagnostics and verification.

Shows clear evidence that Neo4j is running and has data.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def get_neo4j_stats(conn) -> Dict[str, Any]:
    """Get Neo4j database statistics.

    Args:
        conn: Neo4j connector

    Returns:
        Dictionary with node counts, relationship counts, etc.
    """
    try:
        # Count all nodes
        result = conn.execute_query("MATCH (n) RETURN count(n) AS node_count")
        node_count = result[0]["node_count"] if result else 0

        # Count all relationships
        result = conn.execute_query("MATCH ()-[r]->() RETURN count(r) AS rel_count")
        rel_count = result[0]["rel_count"] if result else 0

        # Count by label
        result = conn.execute_query("""
            CALL db.labels() YIELD label
            CALL {
                WITH label
                MATCH (n) WHERE label IN labels(n)
                RETURN count(n) AS count
            }
            RETURN label, count
            ORDER BY count DESC
        """)
        label_counts = {row["label"]: row["count"] for row in result}

        # Get database info
        result = conn.execute_query(
            "CALL dbms.components() YIELD name, versions RETURN name, versions[0] AS version"
        )
        db_info = result[0] if result else {}

        return {
            "node_count": node_count,
            "relationship_count": rel_count,
            "label_counts": label_counts,
            "database": db_info.get("name", "Neo4j"),
            "version": db_info.get("version", "unknown"),
        }

    except Exception as e:
        logger.error("Failed to get Neo4j stats: %s", e)
        return {
            "error": str(e),
            "node_count": 0,
            "relationship_count": 0,
        }


def print_neo4j_status(conn):
    """Print clear Neo4j status with evidence it's working.

    Args:
        conn: Neo4j connector
    """
    stats = get_neo4j_stats(conn)

    if "error" in stats:
        logger.info("❌ Neo4j connection failed: {stats['error']}")
        return False

    print("\n" + "=" * 70)
    logger.info("📊 Neo4j Memory System - Status")
    print("=" * 70)
    logger.info("\n✅ Connected to {stats['database']} {stats['version']}")
    logger.info("\n📈 Graph Statistics:")
    logger.info("   Nodes: {stats['node_count']:,}")
    logger.info("   Relationships: {stats['relationship_count']:,}")

    if stats.get("label_counts"):
        logger.info("\n📋 Node Types:")
        for label, count in list(stats["label_counts"].items())[:10]:
            logger.info("   {label}: {count:,}")

    logger.info("\n" + "=" * 70 + "\n")
    return True


def verify_neo4j_working() -> bool:
    """Verify Neo4j is working with clear evidence.

    Returns:
        True if working, False otherwise
    """
    try:
        from .connector import Neo4jConnector

        with Neo4jConnector() as conn:
            return print_neo4j_status(conn)

    except Exception as e:
        logger.info("\n❌ Neo4j verification failed: {e}\n")
        return False


if __name__ == "__main__":
    # Test diagnostics
    logger.info("Testing Neo4j diagnostics...")
    if verify_neo4j_working():
        logger.info("✅ Neo4j is fully operational!")
    else:
        logger.info("❌ Neo4j has issues")
