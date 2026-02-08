#!/usr/bin/env python3
"""Simple test to run blarify and inspect the database."""

import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.vendor.blarify.prebuilt.graph_builder import GraphBuilder
from amplihack.vendor.blarify.repositories.graph_db_manager.kuzu_manager import KuzuManager


def test_blarify():
    """Run blarify on a small test directory and inspect results."""

    # Create a simple test Python file
    test_dir = Path(tempfile.mkdtemp(prefix="blarify_test_"))
    test_file = test_dir / "test.py"
    test_file.write_text("""
def hello(name):
    '''Say hello to someone.'''
    return f"Hello, {name}!"

class Greeter:
    '''A class for greeting.'''
    def __init__(self, greeting="Hello"):
        self.greeting = greeting

    def greet(self, name):
        '''Greet someone.'''
        return f"{self.greeting}, {name}!"
""")

    print(f"📁 Test directory: {test_dir}")
    print(f"📄 Test file: {test_file}")

    # Create temp Kuzu database path (don't create directory - Kuzu will do it)
    temp_kuzu_dir = (
        Path(tempfile.gettempdir()) / f"blarify_kuzu_{next(tempfile._get_candidate_names())}"
    )
    print(f"💾 Kuzu database: {temp_kuzu_dir}")

    # Initialize Kuzu manager
    db_manager = KuzuManager(
        repo_id="test_repo",
        entity_id="test_entity",
        db_path=str(temp_kuzu_dir),
    )

    # Build graph
    print("\n🔧 Running blarify...")
    graph_builder = GraphBuilder(
        root_path=str(test_dir),
        db_manager=db_manager,
        only_hierarchy=False,
        extensions_to_skip=[],
        names_to_skip=[],
    )

    graph_builder.build()
    print("✅ Blarify completed")

    # Inspect database
    print("\n🔍 Inspecting database contents...")

    # Check node types
    print("\n📊 Node types:")
    results = db_manager.query("""
        MATCH (n:NODE)
        RETURN DISTINCT n.node_type as type, COUNT(*) as count
    """)
    for r in results:
        print(f"  - {r['type']}: {r['count']} nodes")

    # Sample nodes - return full node to access properties
    print("\n📝 Sample nodes:")
    try:
        # Use direct conn.execute to get node properties
        results = db_manager.conn.execute("""
            MATCH (n:NODE)
            RETURN n
            LIMIT 20
        """)
        while results.has_next():
            row = results.get_next()
            node = row[0]  # First column is the node
            node_type = node.get("node_type", "UNKNOWN")
            name = node.get("name", "")
            path = node.get("path", "")
            print(f"  {node_type:15} | {name:30} | {path}")
    except Exception as e:
        print(f"  Error reading nodes: {e}")

    # Close database
    db_manager.close()

    print(f"\n📂 Database preserved at: {temp_kuzu_dir}")
    print(f"📂 Test files preserved at: {test_dir}")
    print("\nTo inspect database, run:")
    print(f"  python scripts/debug_kuzu_contents.py {temp_kuzu_dir}")


if __name__ == "__main__":
    test_blarify()
