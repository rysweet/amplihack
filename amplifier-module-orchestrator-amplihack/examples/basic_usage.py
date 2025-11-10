#!/usr/bin/env python3
"""
Basic Usage Example for Amplifier Module Orchestrator

Demonstrates:
- Creating configuration
- Initializing orchestrator
- Executing simple workflow
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from amplifier_module_orchestrator_amplihack import (
        OrchestratorConfig,
        WorkflowRequest,
        execute_workflow,
        initialize_orchestrator,
    )
except ImportError:
    # Module not installed, try local import
    from core import execute_workflow, initialize_orchestrator  # type: ignore
    from models import OrchestratorConfig, WorkflowRequest  # type: ignore


def main():
    print("=== Amplifier Module Orchestrator - Basic Usage ===\n")

    print("1. Creating configuration...")
    config = OrchestratorConfig(max_agents=3, timeout=30, enable_logging=True)
    print(f"   Config: {config.max_agents} agents, {config.timeout}s timeout\n")

    print("2. Initializing orchestrator...")
    orchestrator = initialize_orchestrator(config)
    print(f"   Orchestrator initialized with {len(orchestrator.agents)} agents\n")

    print("3. Creating workflow request...")
    request = WorkflowRequest(
        task="Synthesize research documents into summary",
        documents=[
            "Document 1: Research on AI agents",
            "Document 2: Multi-agent coordination",
            "Document 3: Synthesis techniques",
        ],
        config={"mode": "comprehensive"},
    )
    print(f"   Task: {request.task}")
    print(f"   Documents: {len(request.documents)}\n")

    print("4. Executing workflow...")
    result = execute_workflow(orchestrator, request)

    print("\n=== Results ===")
    print(f"Status: {result.status}")
    print(f"Processing time: {result.processing_time:.3f}s")
    print(f"Agents executed: {len(result.agent_results)}")

    if result.status == "success":
        print("\nAggregated data:")
        for key, value in result.data.items():
            if key != "results":
                print(f"  {key}: {value}")

        print("\nAgent results:")
        for i, agent_result in enumerate(result.agent_results):
            print(
                f"  {i + 1}. {agent_result.agent_type.value}: {agent_result.status} ({agent_result.processing_time:.3f}s)"
            )
    else:
        print(f"Error: {result.error}")


if __name__ == "__main__":
    main()
