#!/usr/bin/env python3
"""Debug script to inspect Kuzu database contents after blarify run."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.vendor.blarify.repositories.graph_db_manager.kuzu_manager import KuzuManager


def inspect_kuzu_db(db_path: str):
    """Inspect contents of a Kuzu database."""
    print(f"\n🔍 Inspecting Kuzu database at: {db_path}\n")

    manager = KuzuManager(
        repo_id="test",
        entity_id="test",
        db_path=db_path,
    )

    # Check what node types exist
    print("📊 Querying node types...")
    try:
        results = manager.query("""
            MATCH (n:NODE)
            RETURN DISTINCT n.node_type as type, COUNT(*) as count
        """)
        print(f"Found {len(results)} distinct node types:")
        for r in results:
            print(f"  - {r['type']}: {r['count']} nodes")
    except Exception as e:
        print(f"❌ Error querying node types: {e}")

    # Sample some nodes
    print("\n📝 Sample nodes:")
    try:
        results = manager.query("""
            MATCH (n:NODE)
            RETURN n.node_id, n.name, n.node_type, n.path, n.repo_id, n.entity_id
            LIMIT 10
        """)
        for r in results:
            print(f"  {r['node_type']:15} | {r['name']:30} | {r['path']}")
    except Exception as e:
        print(f"❌ Error querying sample nodes: {e}")

    # Check relationship types
    print("\n🔗 Checking relationships...")
    try:
        # Try CONTAINS
        contains_count = manager.query("""
            MATCH ()-[r:CONTAINS]->()
            RETURN COUNT(r) as count
        """)
        print(f"  CONTAINS relationships: {contains_count[0]['count']}")
    except Exception as e:
        print(f"  CONTAINS: Error - {e}")

    try:
        # Try CALLS
        calls_count = manager.query("""
            MATCH ()-[r:CALLS]->()
            RETURN COUNT(r) as count
        """)
        print(f"  CALLS relationships: {calls_count[0]['count']}")
    except Exception as e:
        print(f"  CALLS: Error - {e}")

    manager.close()
    print("\n✅ Inspection complete")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python debug_kuzu_contents.py <db_path>")
        print("\nExample: python debug_kuzu_contents.py /tmp/blarify_kuzu_xyz")
        sys.exit(1)

    db_path = sys.argv[1]
    inspect_kuzu_db(db_path)
