#!/usr/bin/env python3
"""
Tool Integration Example

Demonstrates:
- Creating function tools
- Agent automatically calling tools
- Tools with multiple parameters
- Async tools for I/O operations
- Tool call inspection
"""

import asyncio
import os
from datetime import datetime

from agents_framework import Agent, ModelClient, function_tool


@function_tool
def get_current_time(timezone: str = "UTC") -> str:
    """
    Get current time for a timezone.

    Args:
        timezone: Timezone name (e.g., "UTC", "America/New_York")

    Returns:
        Current time as string
    """
    # Simplified - real implementation would use pytz
    now = datetime.now()
    return f"Current time in {timezone}: {now.strftime('%Y-%m-%d %H:%M:%S')}"


@function_tool
def calculate(expression: str) -> float:
    """
    Evaluate a mathematical expression.

    Args:
        expression: Math expression to evaluate (e.g., "2 + 2", "5 * 3")

    Returns:
        Result of the calculation
    """
    try:
        # SECURITY WARNING: eval() executes arbitrary Python code and should NEVER
        # be used with untrusted input. This example uses a hardcoded expression for
        # demonstration purposes only. In production, use ast.literal_eval() for safe
        # evaluation of literals, or a proper expression parser for calculations.
        result = eval(expression, {"__builtins__": {}})
        return float(result)
    except Exception as e:
        return f"Error: {e!s}"


@function_tool
def get_weather(location: str, units: str = "fahrenheit") -> str:
    """
    Get weather for a location.

    Args:
        location: City name or zip code
        units: Temperature units (fahrenheit or celsius)

    Returns:
        Weather description
    """
    # Mock implementation
    weather_data = {
        "Seattle": {"temp": 62, "conditions": "Rainy"},
        "San Francisco": {"temp": 68, "conditions": "Foggy"},
        "New York": {"temp": 75, "conditions": "Sunny"},
    }

    data = weather_data.get(location, {"temp": 70, "conditions": "Clear"})
    temp = data["temp"]

    if units == "celsius":
        temp = (temp - 32) * 5 / 9

    return f"Weather in {location}: {data['conditions']}, {temp:.1f}°{units[0].upper()}"


@function_tool
async def search_docs(query: str, max_results: int = 3) -> list[dict]:
    """
    Search documentation database.

    Args:
        query: Search query
        max_results: Maximum number of results to return

    Returns:
        List of matching documents
    """
    # Simulate async I/O operation
    await asyncio.sleep(0.1)

    # Mock results
    results = [
        {"title": f"Document about {query} - Part 1", "snippet": f"Information on {query}..."},
        {"title": f"Document about {query} - Part 2", "snippet": f"More about {query}..."},
        {"title": f"{query} FAQ", "snippet": f"Common questions about {query}..."},
    ]

    return results[:max_results]


async def basic_tool_usage():
    """Agent automatically calls tools based on user message."""
    print("=== Basic Tool Usage ===")

    agent = Agent(
        name="assistant",
        model=ModelClient(model="gpt-4"),
        instructions="You are a helpful assistant with access to tools.",
        tools=[get_current_time, calculate, get_weather],
    )

    # Agent automatically calls appropriate tools
    queries = [
        "What time is it?",
        "What's 23 times 45?",
        "What's the weather in Seattle?",
    ]

    for query in queries:
        response = await agent.run(message=query)
        print(f"User: {query}")
        print(f"Agent: {response.content}")
        print()


async def multiple_tool_calls():
    """Agent calls multiple tools for one query."""
    print("=== Multiple Tool Calls ===")

    agent = Agent(
        name="assistant",
        model=ModelClient(model="gpt-4"),
        instructions="You are a helpful assistant.",
        tools=[get_weather, get_current_time],
        parallel_tool_calls=True,  # Enable parallel execution
    )

    response = await agent.run(message="What's the weather and current time in Seattle?")

    print("User: What's the weather and current time in Seattle?")
    print(f"Agent: {response.content}")
    print()


async def tool_call_inspection():
    """Inspect which tools were called."""
    print("=== Tool Call Inspection ===")

    agent = Agent(
        name="assistant", model=ModelClient(model="gpt-4"), tools=[calculate, get_weather]
    )

    response = await agent.run(message="What's 15 * 8 and what's the weather in San Francisco?")

    print("User: What's 15 * 8 and what's the weather in San Francisco?")
    print(f"Agent: {response.content}")
    print("\nTool Calls:")

    for tool_call in response.tool_calls:
        print(f"  - Function: {tool_call.function.name}")
        print(f"    Arguments: {tool_call.function.arguments}")
        print(f"    Result: {tool_call.result}")
    print()


async def async_tool_example():
    """Use async tools for I/O operations."""
    print("=== Async Tool Example ===")

    agent = Agent(
        name="assistant",
        model=ModelClient(model="gpt-4"),
        instructions="You are a documentation assistant.",
        tools=[search_docs],
    )

    response = await agent.run(message="Search for information about agents in the docs")

    print("User: Search for information about agents in the docs")
    print(f"Agent: {response.content}")
    print()


async def main():
    """Run all examples."""
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        return

    await basic_tool_usage()
    await multiple_tool_calls()
    await tool_call_inspection()
    await async_tool_example()

    print("✓ All examples completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
