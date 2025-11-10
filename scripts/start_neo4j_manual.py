#!/usr/bin/env python3
"""
Manual Neo4j container starter using docker-py library.
Bypasses docker-compose dependency issues.
"""

import secrets
import string
import time
from pathlib import Path

import docker


def generate_password(length=32):  # ggignore
    """Generate a secure random password."""
    alphabet = (
        string.ascii_letters + string.digits + string.punctuation.replace('"', "").replace("'", "")
    )
    return "".join(secrets.choice(alphabet) for _ in range(length))  # ggignore


def get_or_create_password():
    """Get existing password or create new one."""
    password_file = Path.home() / ".amplihack" / ".neo4j_password"
    password_file.parent.mkdir(parents=True, exist_ok=True)

    if password_file.exists():
        return password_file.read_text().strip()

    password = generate_password()  # ggignore
    password_file.write_text(password)  # ggignore
    password_file.chmod(0o600)
    print(f"✅ Generated new Neo4j password and saved to {password_file}")
    return password


def start_neo4j_container():
    """Start Neo4j container using docker-py."""
    client = docker.from_env()

    # Get or create password
    password = get_or_create_password()

    # Check if container already exists
    container_name = "amplihack-neo4j"
    try:
        existing = client.containers.get(container_name)
        if existing.status == "running":
            print(f"✅ Container {container_name} already running")
            return existing
        print(f"🔄 Starting existing container {container_name}")
        existing.start()
        return existing
    except docker.errors.NotFound:
        pass

    # Create and start new container
    print(f"🚀 Creating new Neo4j container: {container_name}")

    container = client.containers.run(
        image="neo4j:5.15-community",
        name=container_name,
        detach=True,
        ports={
            "7474/tcp": ("127.0.0.1", 7474),  # HTTP
            "7687/tcp": ("127.0.0.1", 7687),  # Bolt
        },
        environment={
            "NEO4J_AUTH": f"neo4j/{password}",
            "NEO4J_PLUGINS": '["apoc"]',
            "NEO4J_server_memory_heap_initial__size": "1G",
            "NEO4J_server_memory_heap_max__size": "2G",
            "NEO4J_server_memory_pagecache_size": "1G",
        },
        volumes={
            "amplihack-neo4j-data": {"bind": "/data", "mode": "rw"},
        },
        restart_policy={"Name": "unless-stopped"},
        healthcheck={
            "test": ["CMD-SHELL", 'cypher-shell -u neo4j -p $NEO4J_PASSWORD "RETURN 1" || exit 1'],
            "interval": 10000000000,  # 10s in nanoseconds
            "timeout": 5000000000,  # 5s
            "retries": 3,
            "start_period": 40000000000,  # 40s
        },
    )

    print(f"✅ Container created: {container.id[:12]}")
    return container


def wait_for_neo4j(container, timeout=60):
    """Wait for Neo4j to be ready."""
    print(f"⏳ Waiting for Neo4j to be ready (timeout: {timeout}s)...")
    start_time = time.time()

    while time.time() - start_time < timeout:
        try:
            container.reload()
            if container.status == "running":
                # Check if Neo4j is accepting connections
                # We'll check logs for "Started." message
                logs = container.logs(tail=50).decode("utf-8")
                if "Started." in logs or "Remote interface available" in logs:
                    print("✅ Neo4j is ready!")
                    return True
            time.sleep(2)
        except Exception as e:
            print(f"⚠️  Waiting... {e}")
            time.sleep(2)

    print(f"❌ Timeout waiting for Neo4j after {timeout}s")
    return False


def test_connection():
    """Test Neo4j connection."""
    try:
        from neo4j import GraphDatabase

        password_file = Path.home() / ".amplihack" / ".neo4j_password"
        password = password_file.read_text().strip()

        print("🔌 Testing Neo4j connection...")
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", password))

        with driver.session() as session:
            result = session.run("RETURN 1 AS num")
            value = result.single()["num"]
            if value == 1:
                print("✅ Connection test successful!")
                return True

        driver.close()
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

    return False


if __name__ == "__main__":
    print("=" * 60)
    print("Neo4j Container Startup Script")
    print("=" * 60)

    try:
        container = start_neo4j_container()

        if wait_for_neo4j(container):
            if test_connection():
                print("\n✅ Neo4j is fully operational!")
                print("   - UI: http://localhost:7474")
                print("   - Bolt: bolt://localhost:7687")
                print("   - Username: neo4j")
                print("   - Password: (stored in ~/.amplihack/.neo4j_password)")
            else:
                print("\n⚠️  Container started but connection test failed")
                print("   - Check logs: docker logs amplihack-neo4j")
        else:
            print("\n❌ Neo4j failed to start within timeout")
            print("   - Check logs: docker logs amplihack-neo4j")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
