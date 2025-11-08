#!/usr/bin/env python3
"""
Test Neo4j connection and basic operations.
"""

import os
import sys
from pathlib import Path

# Load .env if it exists
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key] = value

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from amplihack.memory.neo4j import config, connector, schema

    print("✅ Successfully imported Neo4j modules")
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)


def test_connection():
    """Test basic Neo4j connection."""
    print("\n" + "=" * 60)
    print("Testing Neo4j Connection")
    print("=" * 60)

    try:
        # Get configuration
        cfg = config.Neo4jConfig.from_environment()
        print(f"📍 URI: {cfg.uri}")
        print(f"👤 User: {cfg.user}")
        print(f"🔐 Password: {'*' * len(cfg.password)}")

        # Test connection
        print("\n🔌 Connecting to Neo4j...")
        with connector.Neo4jConnector(cfg.uri, cfg.user, cfg.password) as conn:
            result = conn.execute_query("RETURN 1 AS num, 'Hello Neo4j!' AS msg")
            print("✅ Connection successful!")
            print(f"   Result: {result}")

            # Test schema initialization
            print("\n📝 Initializing schema...")
            schema_mgr = schema.SchemaManager(conn)
            schema_mgr.initialize_schema()
            print("✅ Schema initialized!")

            # Verify schema
            print("\n🔍 Verifying schema...")
            if schema_mgr.verify_schema():
                print("✅ Schema verification passed!")
            else:
                print("❌ Schema verification failed!")
                return False

            # Test creating a memory node
            print("\n💾 Testing memory creation...")
            result = conn.execute_write("""
                CREATE (m:Memory {
                    id: randomUUID(),
                    content: 'Test memory from connection test',
                    timestamp: datetime(),
                    agent_type: 'test'
                })
                RETURN m.id AS id, m.content AS content
            """)
            print(f"✅ Created test memory: {result}")

            # Query it back
            print("\n📖 Querying memories...")
            result = conn.execute_query("""
                MATCH (m:Memory)
                WHERE m.agent_type = 'test'
                RETURN m.content AS content, m.timestamp AS timestamp
                LIMIT 1
            """)
            print(f"✅ Retrieved memory: {result}")

            # Cleanup test data
            print("\n🧹 Cleaning up test data...")
            conn.execute_write("MATCH (m:Memory {agent_type: 'test'}) DELETE m")
            print("✅ Cleanup complete!")

        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
