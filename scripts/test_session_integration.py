#!/usr/bin/env python3
import os
from pathlib import Path

env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ[key] = value
"""
Test session integration - verify Neo4j starts with amplihack session.
"""
import sys
import time
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.memory.neo4j import lifecycle


def test_session_integration():
    """Test that session start initializes Neo4j."""
    print("=" * 70)
    print("Testing Session Integration")
    print("=" * 70)

    # Check initial state
    print("\n1. Checking initial container state...")
    result = subprocess.run(
        ["docker", "ps", "--filter", "name=amplihack-neo4j", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
    )
    if "amplihack-neo4j" in result.stdout:
        print("   ❌ Container already running (should be stopped for this test)")
        print("   Run: docker stop amplihack-neo4j")
        return False
    print("   ✅ Container not running (correct initial state)")

    # Test lifecycle initialization
    print("\n2. Calling lifecycle.ensure_neo4j_running()...")
    start_time = time.time()

    try:
        lifecycle.ensure_neo4j_running(blocking=True)
        elapsed = time.time() - start_time
        print(f"   ✅ Neo4j started in {elapsed:.2f}s")

        # Verify container is now running
        print("\n3. Verifying container status...")
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=amplihack-neo4j", "--format", "{{.Status}}"],
            capture_output=True,
            text=True,
        )
        if "Up" in result.stdout:
            print(f"   ✅ Container running: {result.stdout.strip()}")
        else:
            print(f"   ❌ Container not running: {result.stdout}")
            return False

        # Test connection
        print("\n4. Testing Neo4j connection...")
        from amplihack.memory.neo4j import connector

        with connector.Neo4jConnector() as conn:
            result = conn.execute_query("RETURN 1 AS num")
            if result and result[0]["num"] == 1:
                print("   ✅ Connection test passed!")
            else:
                print("   ❌ Connection test failed")
                return False

        print("\n" + "=" * 70)
        print("✅ Session Integration Test PASSED!")
        print("=" * 70)
        return True

    except Exception as e:
        print(f"\n❌ Session integration test FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_session_integration()
    sys.exit(0 if success else 1)
