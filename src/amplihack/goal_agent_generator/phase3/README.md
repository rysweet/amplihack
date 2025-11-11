# Phase 3: Multi-Agent Coordination for Complex Goals

Phase 3 provides intelligent decomposition of complex goals into coordinated sub-agents with shared state management and orchestrated execution.

## Overview

When goals become sufficiently complex (6+ phases, multiple domains, or >1 hour duration), Phase 3 automatically coordinates multiple specialized agents working together to achieve the goal more efficiently.

## Components

### 1. CoordinationAnalyzer (`coordination_analyzer.py`)

Analyzes execution plans to determine optimal coordination strategy.

**Triggers for multi-agent coordination:**
- 6 or more execution phases
- Estimated duration > 60 minutes
- 3 or more distinct capability domains

**Outputs:**
- `CoordinationStrategy` with type (single, multi_parallel, multi_sequential, hybrid)
- Agent count recommendation
- Phase groupings for each agent
- Coordination overhead and parallelization benefit metrics

**Example:**
```python
from amplihack.goal_agent_generator.phase3 import CoordinationAnalyzer

analyzer = CoordinationAnalyzer()
strategy = analyzer.analyze(execution_plan)

if strategy.coordination_type != "single":
    print(f"Recommended: {strategy.agent_count} agents")
    print(f"Type: {strategy.coordination_type}")
    print(f"Parallelization benefit: {strategy.parallelization_benefit:.1%}")
```

### 2. SubAgentGenerator (`sub_agent_generator.py`)

Generates coordinated sub-agents from complex execution plans.

**Features:**
- Splits phases across multiple agents based on strategy
- Builds dependency graph (DAG) between agents
- Assigns roles: leader, worker, monitor
- Performs topological sort for execution order
- Matches skills to each agent's capabilities

**Example:**
```python
from amplihack.goal_agent_generator.phase3 import SubAgentGenerator

generator = SubAgentGenerator()
graph = generator.generate(goal_definition, execution_plan, skills, strategy)

print(f"Generated {len(graph.nodes)} agents")
print(f"Execution layers: {len(graph.execution_order)}")

for agent in graph.nodes.values():
    print(f"  {agent.name} ({agent.role}): {len(agent.execution_plan.phases)} phases")
```

### 3. SharedStateManager (`shared_state_manager.py`)

Thread-safe shared state storage and pub/sub messaging for agent coordination.

**Features:**
- Thread-safe get/set/update/delete operations
- Pub/sub event system for inter-agent communication
- Persistent storage to `.agent_state.json`
- Event log for debugging
- State versioning

**Example:**
```python
from amplihack.goal_agent_generator.phase3 import SharedStateManager

state_manager = SharedStateManager()

# Agent writes data
state_manager.set("phase.analyze.output", {"data": results}, agent_id)

# Other agent reads data
data = state_manager.get("phase.analyze.output")

# Subscribe to changes
def on_change(state):
    print(f"State changed: {state.key} = {state.value}")

state_manager.subscribe("status", on_change)
```

### 4. CoordinationProtocol (`coordination_protocol.py`)

Defines message types and validation for inter-agent communication.

**Message Types:**
- `AgentStarted` - Agent begins execution
- `AgentCompleted` - Agent finishes successfully
- `AgentFailed` - Agent encounters error
- `PhaseStarted` - Phase begins
- `PhaseCompleted` - Phase finishes
- `PhaseFailed` - Phase fails
- `DataAvailable` - Data ready for other agents
- `HelpNeeded` - Agent needs assistance
- `StatusUpdate` - Progress update
- `Heartbeat` - Liveness signal

**Example:**
```python
from amplihack.goal_agent_generator.phase3 import CoordinationProtocol, MessageType

# Create message
msg = CoordinationProtocol.create_phase_completed(
    agent_id,
    phase_name="analyze",
    success=True,
    outputs={"result": "success"},
    duration_seconds=10.5
)

# Publish to state manager
state_manager.publish_message(msg)

# Retrieve messages
messages = state_manager.get_messages(agent_id, message_type=MessageType.PHASE_COMPLETED)
```

### 5. OrchestrationLayer (`orchestration_layer.py`)

Orchestrates async execution of coordinated agents with dependency management.

**Features:**
- Async/await based execution
- DAG-based dependency ordering
- Parallel execution within layers
- Configurable concurrency limits
- Graceful failure handling
- State tracking and event publishing

**Example:**
```python
import asyncio
from amplihack.goal_agent_generator.phase3 import OrchestrationLayer

state_manager = SharedStateManager()
orchestrator = OrchestrationLayer(
    state_manager,
    max_concurrent_agents=5,
    timeout_seconds=3600
)

# Execute agents
result = await orchestrator.orchestrate(dependency_graph)

print(f"Success: {result.success}")
print(f"Completed: {len(result.completed_agents)}")
print(f"Failed: {len(result.failed_agents)}")
print(f"Duration: {result.total_duration_seconds}s")
print(f"Completion rate: {result.completion_rate:.1%}")
```

## Data Models

### CoordinationStrategy
```python
@dataclass
class CoordinationStrategy:
    coordination_type: Literal["single", "multi_parallel", "multi_sequential", "hybrid"]
    agent_count: int
    agent_groupings: List[List[str]]  # phase names per agent
    coordination_overhead: float  # 0-1
    parallelization_benefit: float  # 0-1
    recommendation_reason: str
```

### SubAgentDefinition
```python
@dataclass
class SubAgentDefinition:
    id: uuid.UUID
    name: str
    role: Literal["leader", "worker", "monitor"]
    goal_definition: GoalDefinition
    execution_plan: ExecutionPlan
    skills: List[SkillDefinition]
    dependencies: List[uuid.UUID]  # Other agent IDs
    shared_state_keys: List[str]
    coordination_protocol: str = "v1"
```

### AgentDependencyGraph
```python
@dataclass
class AgentDependencyGraph:
    nodes: Dict[uuid.UUID, SubAgentDefinition]
    edges: Dict[uuid.UUID, List[uuid.UUID]]  # agent_id -> dependencies
    execution_order: List[List[uuid.UUID]]  # Topologically sorted layers
```

## Complete Workflow

```python
from amplihack.goal_agent_generator.phase3 import (
    CoordinationAnalyzer,
    SubAgentGenerator,
    SharedStateManager,
    OrchestrationLayer
)

# 1. Analyze coordination needs
analyzer = CoordinationAnalyzer()
strategy = analyzer.analyze(execution_plan)

# 2. Generate coordinated agents (if needed)
if strategy.coordination_type != "single":
    generator = SubAgentGenerator()
    graph = generator.generate(goal_definition, execution_plan, skills, strategy)

    # 3. Setup shared state
    state_manager = SharedStateManager()

    # 4. Orchestrate execution
    orchestrator = OrchestrationLayer(state_manager)
    result = await orchestrator.orchestrate(graph)

    # 5. Review results
    if result.success:
        print("All agents completed successfully!")
    else:
        print(f"Failures: {result.failed_agents}")
        for agent_id, error in result.error_messages.items():
            print(f"  {agent_id}: {error}")
```

## Integration with Phase 1 & 2

Phase 3 integrates seamlessly with earlier phases:

1. **Phase 1 (Planning)**: Provides `ExecutionPlan` with phases, dependencies, and estimates
2. **Phase 2 (Skills)**: Provides available skills matched to capabilities
3. **Phase 3 (Coordination)**: Analyzes complexity and coordinates multiple agents if needed

Each sub-agent receives:
- Sub-goal derived from original goal (Phase 1)
- Subset of execution phases (Phase 1)
- Matched skills for its capabilities (Phase 2)
- Coordination metadata and shared state access (Phase 3)

## Testing

All Phase 3 modules have comprehensive test coverage:

```bash
# Run all Phase 3 tests
pytest src/amplihack/goal_agent_generator/tests/phase3/ -v

# Run specific module tests
pytest src/amplihack/goal_agent_generator/tests/phase3/test_coordination_analyzer.py -v
pytest src/amplihack/goal_agent_generator/tests/phase3/test_sub_agent_generator.py -v
pytest src/amplihack/goal_agent_generator/tests/phase3/test_shared_state_manager.py -v
pytest src/amplihack/goal_agent_generator/tests/phase3/test_coordination_protocol.py -v
pytest src/amplihack/goal_agent_generator/tests/phase3/test_orchestration_layer.py -v

# Run integration tests
pytest src/amplihack/goal_agent_generator/tests/phase3/test_phase3_integration.py -v
```

## Performance Characteristics

### Coordination Overhead
- **Single agent**: 0% overhead
- **Parallel coordination**: ~15% overhead (communication, state management)
- **Sequential coordination**: ~5% overhead (simpler coordination)
- **Hybrid coordination**: ~20% overhead (mixed complexity)

### Parallelization Benefits
- High benefit (>60%): Phases with no dependencies, multiple domains
- Medium benefit (30-60%): Some dependencies, shared resources
- Low benefit (<30%): Sequential dependencies, tight coupling

### Scaling
- **Agent count**: Typically 2-5 agents for most complex goals
- **Max concurrency**: Configurable (default: 5 concurrent agents)
- **State management**: Thread-safe, supports 100s of concurrent operations
- **Message throughput**: 1000s of messages/second

## Design Philosophy

Phase 3 follows the "Ruthless Simplicity" principle:

1. **Zero-BS Implementation**: Every function works, no stubs or TODOs
2. **Self-contained modules**: Clear interfaces, minimal coupling
3. **Async-first**: Built on asyncio for efficient concurrency
4. **Graceful degradation**: Continues execution despite non-critical failures
5. **Observable**: Comprehensive logging and event tracking
6. **Type-safe**: Full type hints throughout

## Future Enhancements

Potential improvements for future iterations:

- [ ] Dynamic agent spawning based on load
- [ ] Agent health monitoring and auto-recovery
- [ ] Resource allocation and limits per agent
- [ ] Distributed execution across multiple machines
- [ ] Real-time visualization of agent coordination
- [ ] Historical analytics for strategy optimization
- [ ] Agent skill learning from execution history
