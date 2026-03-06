#!/usr/bin/env python3
"""
Basic usage example for the Agent Memory System.
Demonstrates how agents can use persistent memory across sessions.
"""

import sys
from pathlib import Path

# Add the memory module to path for this example
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from ..interface import AgentMemory


def example_agent_usage():
    """Example of how an agent would use the memory system."""
    print("Agent Memory System - Basic Usage Example")
    print("=" * 50)

    # Initialize agent memory
    memory = AgentMemory("example-agent")

    print(f"Agent: {memory.agent_name}")
    print(f"Session: {memory.session_id}")
    print(f"Enabled: {memory.enabled}")

    # Store agent preferences
    print("\n1. Storing agent preferences...")
    memory.store("user_preference", "dark_mode")
    memory.store("language", "python")
    memory.store("last_task", "memory system implementation")

    # Store structured configuration
    config = {
        "max_retries": 3,
        "timeout": 30,
        "debug_mode": True,
        "features": ["memory", "hooks", "testing"],
    }
    memory.store("agent_config", config, memory_type="json")

    print("✓ Preferences and config stored")

    # Retrieve memories
    print("\n2. Retrieving memories...")
    preference = memory.retrieve("user_preference")
    language = memory.retrieve("language")
    task = memory.retrieve("last_task")
    agent_config = memory.retrieve("agent_config")

    print(f"User preference: {preference}")
    print(f"Preferred language: {language}")
    print(f"Last task: {task}")
    print(f"Agent config: {agent_config}")

    # List all stored keys
    print("\n3. Listing all stored keys...")
    all_keys = memory.list_keys()
    print(f"All keys: {all_keys}")

    # Pattern-based key listing
    config_keys = memory.list_keys("*config*")
    print(f"Config-related keys: {config_keys}")

    # Memory statistics
    print("\n4. Memory statistics...")
    stats = memory.get_stats()
    print(f"Total keys: {stats['key_count']}")
    print(f"Sample keys: {stats['keys']}")

    # Context manager usage
    print("\n5. Using context manager...")
    with AgentMemory("temp-agent") as temp_memory:
        temp_memory.store("temp_data", "This will be cleaned up")
        temp_value = temp_memory.retrieve("temp_data")
        print(f"Temporary value: {temp_value}")
    # Connection automatically closed

    memory.close()
    print("\n✓ Example completed successfully!")


def example_session_persistence():
    """Example of session persistence across different runs."""
    print("\nSession Persistence Example")
    print("=" * 30)

    # First session
    print("Creating first session...")
    memory1 = AgentMemory("persistent-agent", session_id="session-1")
    memory1.store("session_data", "Data from session 1")
    memory1.close()

    # Second session (different session ID)
    print("Creating second session...")
    memory2 = AgentMemory("persistent-agent", session_id="session-2")
    memory2.store("session_data", "Data from session 2")

    # Verify isolation
    value2 = memory2.retrieve("session_data")
    print(f"Session 2 data: {value2}")

    # Third session (same as first)
    print("Reconnecting to first session...")
    memory3 = AgentMemory("persistent-agent", session_id="session-1")
    value1 = memory3.retrieve("session_data")
    print(f"Session 1 data (retrieved): {value1}")

    memory2.close()
    memory3.close()
    print("✓ Session persistence verified!")


def example_optional_activation():
    """Example of optional memory activation."""
    print("\nOptional Activation Example")
    print("=" * 30)

    # Enabled memory (default)
    enabled_memory = AgentMemory("agent-enabled")
    enabled_memory.store("test", "persistent data")
    value = enabled_memory.retrieve("test")
    print(f"Enabled memory: {value}")

    # Disabled memory
    disabled_memory = AgentMemory("agent-disabled", enabled=False)
    disabled_memory.store("test", "non-persistent data")
    value = disabled_memory.retrieve("test")
    print(f"Disabled memory: {value}")  # Should be None

    enabled_memory.close()
    disabled_memory.close()
    print("✓ Optional activation verified!")


if __name__ == "__main__":
    try:
        example_agent_usage()
        example_session_persistence()
        example_optional_activation()
        print("\n🎉 All examples completed successfully!")
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
