#!/usr/bin/env python3
"""
Simple Workflow Example

Demonstrates:
- Creating graph-based workflows
- Sequential agent execution
- Parallel agent execution
- Conditional routing
- Workflow state management
"""

import asyncio
import os

from agents_framework import Agent, GraphWorkflow, ModelClient


async def sequential_workflow():
    """Sequential execution: Research → Write → Review."""
    print("=== Sequential Workflow ===")

    # Create specialized agents
    researcher = Agent(
        name="researcher",
        model=ModelClient(model="gpt-4"),
        instructions="Research topics and gather key facts. Be thorough.",
    )

    writer = Agent(
        name="writer",
        model=ModelClient(model="gpt-4"),
        instructions="Write clear, concise content based on research.",
    )

    reviewer = Agent(
        name="reviewer",
        model=ModelClient(model="gpt-4"),
        instructions="Review content for accuracy and clarity.",
    )

    # Build workflow
    workflow = GraphWorkflow()

    workflow.add_node("research", researcher)
    workflow.add_node("write", writer)
    workflow.add_node("review", reviewer)

    # Define sequential flow
    workflow.add_edge("research", "write")
    workflow.add_edge("write", "review")

    workflow.set_entry_point("research")

    # Execute workflow
    result = await workflow.run(initial_message="Research and write about quantum computing")

    print(f"Final output: {result.final_output}")
    print()


async def parallel_workflow():
    """Parallel execution: Multiple analysts → Synthesizer."""
    print("=== Parallel Workflow ===")

    # Create analyst agents
    security_analyst = Agent(
        name="security",
        model=ModelClient(model="gpt-4"),
        instructions="Analyze from security perspective.",
    )

    performance_analyst = Agent(
        name="performance",
        model=ModelClient(model="gpt-4"),
        instructions="Analyze from performance perspective.",
    )

    ux_analyst = Agent(
        name="ux",
        model=ModelClient(model="gpt-4"),
        instructions="Analyze from user experience perspective.",
    )

    synthesizer = Agent(
        name="synthesizer",
        model=ModelClient(model="gpt-4"),
        instructions="Synthesize all analyses into comprehensive report.",
    )

    # Build workflow
    workflow = GraphWorkflow()

    workflow.add_node("security", security_analyst)
    workflow.add_node("performance", performance_analyst)
    workflow.add_node("ux", ux_analyst)
    workflow.add_node("synthesize", synthesizer)

    # Parallel execution - all analysts run concurrently
    workflow.add_edge("START", ["security", "performance", "ux"])

    # Wait for all analysts, then synthesize
    workflow.add_edge(["security", "performance", "ux"], "synthesize")

    # Execute workflow
    result = await workflow.run(initial_state={"topic": "new authentication system"})

    print(f"Synthesis: {result.final_output}")
    print()


async def conditional_workflow():
    """Conditional routing based on state."""
    print("=== Conditional Workflow ===")

    # Create agents
    classifier = Agent(
        name="classifier",
        model=ModelClient(model="gpt-4"),
        instructions="Classify queries as 'simple' or 'complex'.",
    )

    simple_handler = Agent(
        name="simple_handler",
        model=ModelClient(model="gpt-4"),
        instructions="Handle simple queries quickly.",
    )

    complex_handler = Agent(
        name="complex_handler",
        model=ModelClient(model="gpt-4"),
        instructions="Handle complex queries with detailed analysis.",
    )

    # Build workflow
    workflow = GraphWorkflow()

    workflow.add_node("classify", classifier)
    workflow.add_node("simple", simple_handler)
    workflow.add_node("complex", complex_handler)

    # Route based on classification
    def route_query(state):
        """Determine routing based on state."""
        content = state.get("classification", "").lower()
        if "simple" in content:
            return "simple"
        return "complex"

    workflow.add_edge("classify", route_query)

    workflow.set_entry_point("classify")

    # Test simple query
    result1 = await workflow.run(initial_message="What's 2+2?")
    print(f"Simple query result: {result1.final_output}")

    # Test complex query
    result2 = await workflow.run(initial_message="Explain the implications of quantum entanglement")
    print(f"Complex query result: {result2.final_output}")
    print()


async def iterative_workflow():
    """Iterative refinement with approval loop."""
    print("=== Iterative Workflow ===")

    generator = Agent(
        name="generator", model=ModelClient(model="gpt-4"), instructions="Generate content."
    )

    reviewer = Agent(
        name="reviewer",
        model=ModelClient(model="gpt-4"),
        instructions="Review content. Approve if good, otherwise suggest improvements.",
    )

    # Build workflow
    workflow = GraphWorkflow()

    workflow.add_node("generate", generator)
    workflow.add_node("review", reviewer)

    workflow.add_edge("generate", "review")

    # Conditional edge: approved → end, not approved → regenerate
    def check_approval(state):
        """Check if content is approved."""
        review = state.get("review_result", "").lower()
        # Simple heuristic - real implementation would be more sophisticated
        if "approve" in review or "good" in review:
            return "END"
        # Limit iterations to prevent infinite loop
        iterations = state.get("iterations", 0)
        if iterations >= 2:
            return "END"
        return "generate"

    workflow.add_conditional_edge("review", check_approval)

    workflow.set_entry_point("generate")

    # Execute workflow
    result = await workflow.run(
        initial_state={"task": "Write a haiku about coding", "iterations": 0}
    )

    print(f"Final output: {result.final_output}")
    print(f"Iterations: {result.state.get('iterations', 0)}")
    print()


async def stateful_workflow():
    """Workflow with state accumulation."""
    print("=== Stateful Workflow ===")

    # Node functions that update state
    def step1(state: dict) -> dict:
        """First processing step."""
        return {"step1_result": "Gathered data", "count": state.get("count", 0) + 1}

    def step2(state: dict) -> dict:
        """Second processing step."""
        return {
            "step2_result": f"Processed {state.get('step1_result', 'nothing')}",
            "count": state.get("count", 0) + 1,
        }

    def step3(state: dict) -> dict:
        """Final processing step."""
        return {
            "final_result": f"Completed {state.get('step2_result', 'nothing')}",
            "count": state.get("count", 0) + 1,
        }

    # Build workflow
    workflow = GraphWorkflow()

    workflow.add_node("step1", step1)
    workflow.add_node("step2", step2)
    workflow.add_node("step3", step3)

    workflow.add_edge("step1", "step2")
    workflow.add_edge("step2", "step3")

    workflow.set_entry_point("step1")

    # Execute workflow
    result = await workflow.run(initial_state={"count": 0})

    print(f"Final state: {result.state}")
    print(f"Processing steps completed: {result.state.get('count', 0)}")
    print()


async def main():
    """Run all examples."""
    if not os.getenv("OPENAI_API_KEY"):
        print("ERROR: OPENAI_API_KEY environment variable not set")
        return

    await sequential_workflow()
    await parallel_workflow()
    await conditional_workflow()
    await iterative_workflow()
    await stateful_workflow()

    print("✓ All examples completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
