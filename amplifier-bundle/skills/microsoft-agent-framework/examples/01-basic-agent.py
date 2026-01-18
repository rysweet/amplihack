#!/usr/bin/env python3
"""
Basic Agent Example

Demonstrates:
- Creating a simple conversational agent
- Single-turn conversations
- Multi-turn conversations with thread
- Accessing response metadata
"""

import asyncio
import os

from agents_framework import Agent, ModelClient, Thread


async def single_turn_example():
    """Simple single-turn conversation."""
    print("=== Single-Turn Conversation ===")

    # Create agent
    agent = Agent(
        name="assistant",
        model=ModelClient(model="gpt-4", temperature=0.7),
        instructions="You are a helpful assistant. Be concise and friendly.",
    )

    # Send message
    response = await agent.run(message="What is the capital of France?")

    print("User: What is the capital of France?")
    print(f"Agent: {response.content}")
    print(f"Tokens used: {response.usage.total_tokens}")
    print()


async def multi_turn_example():
    """Multi-turn conversation with context."""
    print("=== Multi-Turn Conversation ===")

    # Create agent
    agent = Agent(
        name="assistant",
        model=ModelClient(model="gpt-4"),
        instructions="You are a helpful assistant with good memory.",
    )

    # Create thread to maintain conversation history
    thread = Thread()

    # Turn 1
    response1 = await agent.run(thread=thread, message="My name is Alice and I'm learning Python.")
    print("User: My name is Alice and I'm learning Python.")
    print(f"Agent: {response1.content}")
    print()

    # Turn 2 - agent remembers context
    response2 = await agent.run(thread=thread, message="What's my name?")
    print("User: What's my name?")
    print(f"Agent: {response2.content}")
    print()

    # Turn 3 - agent remembers context
    response3 = await agent.run(thread=thread, message="What am I learning?")
    print("User: What am I learning?")
    print(f"Agent: {response3.content}")
    print()


async def response_metadata_example():
    """Inspect response metadata."""
    print("=== Response Metadata ===")

    agent = Agent(name="assistant", model=ModelClient(model="gpt-4"))

    response = await agent.run(message="Explain quantum computing in one sentence.")

    print(f"Content: {response.content}")
    print(f"Model: {response.model}")
    print(f"Role: {response.role}")
    print(f"Prompt tokens: {response.usage.prompt_tokens}")
    print(f"Completion tokens: {response.usage.completion_tokens}")
    print(f"Total tokens: {response.usage.total_tokens}")
    print()


async def main():
    """Run all examples."""
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        print("Set it with: export OPENAI_API_KEY=sk-...")
        return

    await single_turn_example()
    await multi_turn_example()
    await response_metadata_example()

    print("✓ All examples completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
