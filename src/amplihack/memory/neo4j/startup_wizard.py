"""Neo4j startup wizard with user interaction.

Handles Neo4j startup with clear user feedback and decisions.
"""

import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def check_container_logs_for_ready(container_name: str) -> bool:
    """Check Docker logs for 'Started' message.

    Args:
        container_name: Container name

    Returns:
        True if Neo4j reports ready in logs
    """
    try:
        result = subprocess.run(
            ["docker", "logs", container_name, "--tail", "50"],
            capture_output=True,
            timeout=5,
            text=True,
        )
        logs = result.stdout + result.stderr
        return "Started." in logs or "Remote interface available" in logs
    except Exception as e:
        logger.debug("Could not check logs: %s", e)
        return False


def wait_for_neo4j_with_feedback(max_wait: int = 60) -> bool:
    """Wait for Neo4j to be ready with user feedback.

    Args:
        max_wait: Maximum seconds to wait

    Returns:
        True if ready, False if timeout
    """
    from .lifecycle import is_neo4j_running
    from .connector import Neo4jConnector

    print("\n⏳ Waiting for Neo4j to be ready...")
    print("   (This usually takes 20-30 seconds on first startup)")

    start_time = time.time()
    last_dot = 0

    while time.time() - start_time < max_wait:
        elapsed = int(time.time() - start_time)

        # Print progress dots every 2 seconds
        if elapsed > last_dot + 2:
            print(".", end="", flush=True)
            last_dot = elapsed

        # Check container logs first (faster than connection attempt)
        if check_container_logs_for_ready("amplihack-neo4j"):
            print(" ✅ Container reports ready!")

            # Now verify we can actually connect
            try:
                with Neo4jConnector() as conn:
                    result = conn.execute_query("RETURN 1 AS test")
                    if result and result[0].get("test") == 1:
                        print("✅ Connection verified!\n")
                        return True
            except Exception as e:
                logger.debug("Connection attempt failed: %s", e)

        time.sleep(2)

    print(f"\n❌ Timeout after {max_wait} seconds\n")
    return False


def show_neo4j_stats_or_empty():
    """Show Neo4j stats or note if database is empty."""
    try:
        from .diagnostics import get_neo4j_stats
        from .connector import Neo4jConnector

        with Neo4jConnector() as conn:
            stats = get_neo4j_stats(conn)

            print("="*70)
            print("📊 Neo4j Memory System - Connected")
            print("="*70)
            print(f"\n✅ Database: {stats.get('database', 'Neo4j')} {stats.get('version', 'unknown')}")

            node_count = stats.get('node_count', 0)
            rel_count = stats.get('relationship_count', 0)

            if node_count == 0:
                print("\n📊 Database Status: EMPTY (expected on first startup)")
                print("   The database is ready and will accumulate memories as you work.")
            else:
                print(f"\n📈 Graph Statistics:")
                print(f"   Nodes: {node_count:,}")
                print(f"   Relationships: {rel_count:,}")

                if stats.get("label_counts"):
                    print(f"\n📋 Node Types:")
                    for label, count in list(stats["label_counts"].items())[:5]:
                        print(f"   {label}: {count:,}")

            print("\n" + "="*70 + "\n")
            return True

    except Exception as e:
        logger.error("Failed to get stats: %s", e)
        print(f"❌ Could not retrieve database stats: {e}\n")
        return False


def ask_user_continue_without_neo4j() -> bool:
    """Ask user if they want to continue without Neo4j.

    Returns:
        True if user wants to continue, False to exit
    """
    print("\n" + "="*70)
    print("⚠️  Neo4j Memory System Unavailable")
    print("="*70)
    print("\nYou can:")
    print("  1. Continue with basic memory system (SQLite)")
    print("  2. Try to troubleshoot and retry Neo4j")
    print("  3. Exit and fix manually")

    while True:
        response = input("\nYour choice (1/2/3): ").strip()

        if response == "1":
            print("\n✅ Continuing with basic memory system...\n")
            return True
        elif response == "2":
            return _troubleshoot_and_retry()
        elif response == "3":
            print("\n👋 Exiting. Fix Neo4j and try again.\n")
            return False
        else:
            print("Please enter 1, 2, or 3")


def _troubleshoot_and_retry() -> bool:
    """Provide troubleshooting and offer retry."""
    print("\n" + "="*70)
    print("🔧 Troubleshooting Neo4j")
    print("="*70)

    print("\n1. Check Docker logs:")
    print("   docker logs amplihack-neo4j")

    print("\n2. Check container status:")
    print("   docker ps -a | grep amplihack-neo4j")

    print("\n3. Check ports not in use:")
    print("   lsof -i :7787 (bolt)")
    print("   lsof -i :7774 (http)")

    print("\n4. Try restarting container:")
    print("   docker restart amplihack-neo4j")

    while True:
        response = input("\nRetry connection? (y/n): ").strip().lower()

        if response == "y":
            print("\n⏳ Retrying...")
            if wait_for_neo4j_with_feedback(max_wait=30):
                show_neo4j_stats_or_empty()
                return True
            else:
                print("\n❌ Still cannot connect")
                return ask_user_continue_without_neo4j()
        elif response == "n":
            print("\n👋 Exiting. Fix and try again later.\n")
            return False
        else:
            print("Please enter y or n")


def interactive_neo4j_startup() -> bool:
    """Interactive Neo4j startup with user feedback and decisions.

    Returns:
        True if should continue (with or without Neo4j), False to exit
    """
    from . import lifecycle, auto_setup

    print("\n" + "="*70)
    print("🚀 Neo4j Memory System Startup")
    print("="*70 + "\n")

    # 1. Auto-setup prerequisites
    print("📋 Checking prerequisites...")
    if not auto_setup.ensure_prerequisites():
        print("\n❌ Prerequisites not met\n")
        return ask_user_continue_without_neo4j()

    print("✅ Prerequisites ready\n")

    # 2. Start Neo4j
    print("🐳 Starting Neo4j container...")
    if not lifecycle.ensure_neo4j_running(blocking=True):
        print("❌ Failed to start Neo4j\n")
        return ask_user_continue_without_neo4j()

    # 3. Wait for ready with feedback
    if not wait_for_neo4j_with_feedback(max_wait=60):
        return ask_user_continue_without_neo4j()

    # 4. Show stats
    show_neo4j_stats_or_empty()

    return True  # Continue with Neo4j ready


if __name__ == "__main__":
    # Test the wizard
    if interactive_neo4j_startup():
        print("✅ Ready to start Claude Code!")
    else:
        print("❌ Exiting")
        sys.exit(1)
