"""Code freshness detection for Code Understanding Engine.

Detects when codebase has changed and index needs updating.
"""

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def get_codebase_last_modified(project_root: Path, patterns: list[str] | None = None) -> datetime:
    """Get most recent modification time of code files.

    Args:
        project_root: Project root directory
        patterns: File patterns to check (default: ['*.py', '*.js', '*.ts'])

    Returns:
        Most recent modification time
    """
    if patterns is None:
        patterns = ["**/*.py", "**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx"]

    latest = datetime.fromtimestamp(0)  # Epoch

    for pattern in patterns:
        for file_path in project_root.glob(pattern):
            if ".git" in file_path.parts or "node_modules" in file_path.parts:
                continue
            try:
                mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if mtime > latest:
                    latest = mtime
            except Exception as e:
                logger.debug("Could not check mtime for %s: %s", file_path, e)

    return latest


def get_code_index_last_updated(conn) -> datetime | None:
    """Get when code understanding index was last updated.

    Args:
        conn: Neo4j connector

    Returns:
        Last update time, or None if never indexed
    """
    try:
        query = """
        OPTIONAL MATCH (m:CodeIndexMetadata)
        RETURN m.last_updated AS last_updated
        ORDER BY m.last_updated DESC
        LIMIT 1
        """
        result = conn.execute_query(query)

        if result and result[0].get("last_updated"):
            # Neo4j datetime to Python datetime
            last_updated_str = result[0]["last_updated"]
            return datetime.fromisoformat(last_updated_str)

        return None  # Never indexed

    except Exception as e:
        logger.debug("Could not query index metadata: %s", e)
        return None


def is_code_index_stale(
    project_root: Path, conn, max_age_minutes: int = 60
) -> tuple[bool, str | None]:
    """Check if code understanding index is stale.

    Index is stale if:
    - Never been created
    - Code modified after last index
    - Index older than max_age_minutes

    Args:
        project_root: Project root directory
        conn: Neo4j connector
        max_age_minutes: Maximum age before considered stale

    Returns:
        (is_stale, reason)
    """
    try:
        # Get last index time
        last_indexed = get_code_index_last_updated(conn)

        if last_indexed is None:
            return True, "Code Understanding Engine has never been initialized"

        # Get most recent code modification
        code_mtime = get_codebase_last_modified(project_root)

        # Check if code changed after index
        if code_mtime > last_indexed:
            files_changed = (code_mtime - last_indexed).total_seconds() / 60
            return True, f"Code modified {files_changed:.0f} minutes ago (index is outdated)"

        # Check age
        age_minutes = (datetime.now() - last_indexed).total_seconds() / 60
        if age_minutes > max_age_minutes:
            return True, f"Index is {age_minutes:.0f} minutes old (refresh recommended)"

        return False, f"Code Understanding index is up to date ({age_minutes:.0f}min old)"

    except Exception as e:
        logger.warning("Freshness check failed: %s", e)
        return False, f"Could not check freshness: {e}"


def update_index_metadata(conn, project_root: Path):
    """Update index metadata after successful indexing.

    Args:
        conn: Neo4j connector
        project_root: Project root directory
    """
    try:
        query = """
        MERGE (m:CodeIndexMetadata {project_root: $project_root})
        SET m.last_updated = $timestamp,
            m.file_count = $file_count
        RETURN m.last_updated AS updated
        """

        # Count code files
        file_count = sum(1 for _ in project_root.glob("**/*.py") if ".git" not in str(_))

        params = {
            "project_root": str(project_root),
            "timestamp": datetime.now().isoformat(),
            "file_count": file_count,
        }

        conn.execute_write(query, params)
        logger.info("Updated code index metadata: %d files", file_count)

    except Exception as e:
        logger.warning("Could not update index metadata: %s", e)


if __name__ == "__main__":
    # Test freshness detection
    print("Testing code freshness detection...")

    import sys

    sys.path.insert(0, "src")

    from amplihack.memory.neo4j import Neo4jConnector

    try:
        with Neo4jConnector() as conn:
            project_root = Path.cwd()

            is_stale, reason = is_code_index_stale(project_root, conn)
            print(f"Stale: {is_stale}")
            print(f"Reason: {reason}")

            if is_stale:
                print("\n✅ Would prompt user to update Code Understanding Engine")
            else:
                print("\n✅ Index is fresh, no update needed")

    except Exception as e:
        print(f"Test failed: {e}")
