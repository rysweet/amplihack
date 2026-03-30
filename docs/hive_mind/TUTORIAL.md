# Distributed Hive Mind — Tutorial

Get multiple goal-seeking agents sharing knowledge through a federated hive mind.

## Prerequisites

```bash
# From the amplihack5 repo root
uv sync
```

## 1. Local Quick Start (In-Memory, Single Process)

The fastest way to see the hive mind work. All state lives in Python dicts.

```python
from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
    InMemoryHiveGraph,
    HiveFact,
    create_hive_graph,
)

# Create a hive
hive = create_hive_graph("memory", hive_id="my-hive")

# Register agents
hive.register_agent("alice", domain="security")
hive.register_agent("bob", domain="infrastructure")

# Alice promotes a fact
hive.promote_fact("alice", HiveFact(
    fact_id="", content="SSH runs on port 22", concept="networking", confidence=0.95,
))

# Bob promotes a fact
hive.promote_fact("bob", HiveFact(
    fact_id="", content="Nginx default port is 80", concept="networking", confidence=0.9,
))

# Query the hive
results = hive.query_facts("port networking", limit=10)
for fact in results:
    print(f"  [{fact.confidence:.0%}] {fact.content}")
```

## 2. Federation (Multiple Hives in a Tree)

Split agents across domain-specific hives, then query across the whole tree.

```python
from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
    InMemoryHiveGraph,
    HiveFact,
)

# Create a tree: root -> [security, infrastructure, data]
root = InMemoryHiveGraph("root")

security = InMemoryHiveGraph("security")
infra = InMemoryHiveGraph("infrastructure")
data = InMemoryHiveGraph("data")

for child in [security, infra, data]:
    root.add_child(child)
    child.set_parent(root)

# Each hive has its own agents and facts
security.register_agent("sec-1", domain="security")
security.promote_fact("sec-1", HiveFact(
    fact_id="", content="CVE-2024-1234 affects OpenSSL 3.x",
    concept="vulnerabilities", confidence=0.95,
))

infra.register_agent("infra-1", domain="infrastructure")
infra.promote_fact("infra-1", HiveFact(
    fact_id="", content="Server prod-db-01 runs on 10.0.1.5 port 5432",
    concept="servers", confidence=0.9,
))

data.register_agent("data-1", domain="data")
data.promote_fact("data-1", HiveFact(
    fact_id="", content="Users table has 2.5M rows with daily growth of 10K",
    concept="schema", confidence=0.85,
))

# Federated query from root finds facts across ALL hives
results = root.query_federated("server port infrastructure", limit=10)
for fact in results:
    print(f"  [{fact.confidence:.0%}] {fact.content}")

# Federated query from a child also traverses the tree
results = security.query_federated("server database port", limit=10)
print(f"\nSecurity hive found {len(results)} results across federation")
```

## 3. LearningAgent with Hive Store (Recommended)

Connect a real LLM-backed LearningAgent to a shared hive for distributed memory.
Facts learned by the agent are auto-promoted to the hive; queries merge local + hive facts.

```python
from pathlib import Path
from amplihack.agents.goal_seeking.learning_agent import LearningAgent
from amplihack.agents.goal_seeking.hive_mind.hive_graph import InMemoryHiveGraph

# Create shared hive
hive = InMemoryHiveGraph("shared-hive")
hive.register_agent("agent_a")
hive.register_agent("agent_b")

# Create agents with hive_store
agent_a = LearningAgent(
    agent_name="agent_a",
    storage_path=Path("/tmp/agent_a_db"),
    use_hierarchical=True,
    hive_store=hive,  # <-- Auto-promotes facts to hive
)
agent_b = LearningAgent(
    agent_name="agent_b",
    storage_path=Path("/tmp/agent_b_db"),
    use_hierarchical=True,
    hive_store=hive,
)

# Agent A learns biology
agent_a.learn_from_content(
    "Photosynthesis converts sunlight into chemical energy in chloroplasts."
)

# Agent B learns chemistry
agent_b.learn_from_content(
    "Water (H2O) has a bent molecular geometry with a 104.5 degree bond angle."
)

# Agent B can answer questions about biology (facts shared via hive)
answer = agent_b.answer_question("How do plants convert sunlight to energy?")
print(answer)

agent_a.close()
agent_b.close()
```

**How auto-promotion works**: When `CognitiveAdapter.store_fact()` is called
(inside `learn_from_content`), it stores the fact in the agent's local Kuzu DB
AND promotes it to the hive. When `search()` or `get_all_facts()` is called
(inside `answer_question`), it queries both local Kuzu and the hive, deduplicates
by content, and returns merged results.

## 4. Distributed Agents with Kuzu (Full Stack)

Each agent owns its own Kuzu database. A shared HiveGraphStore acts as the
federation layer. FederatedGraphStore composes local + hive for unified queries.

```python
# Requires: pip install kuzu
# Requires: amplihack-memory-lib installed

from amplihack.agents.goal_seeking.hive_mind.distributed import AgentNode
from amplihack.agents.goal_seeking.hive_mind.event_bus import create_event_bus

# Create event bus (local for testing, "redis" or "azure" for production)
bus = create_event_bus("local")

# Create agents with their own Kuzu databases
agent_a = AgentNode(
    agent_id="bio-agent",
    domain="biology",
    db_path="/tmp/hive_eval/bio-agent",
    hive_store=None,  # or pass a HiveGraphStore for federation
    event_bus=bus,
)

# Learn and query
agent_a.learn("Mitosis is cell division", tags=["biology"])
results = agent_a.query("cell division")
print(f"Found: {results}")

agent_a.close()
```

## 5. Deploy to Azure

The deploy script provisions everything idempotently:

```bash
# Set your API key
export ANTHROPIC_API_KEY="your-api-key-here"  # pragma: allowlist secret

# Deploy 20 agents + 1 adversary to Azure Container Apps
bash experiments/hive_mind/deploy_azure_hive.sh

# Check status
bash experiments/hive_mind/deploy_azure_hive.sh --status

# Run the eval against deployed agents
bash experiments/hive_mind/deploy_azure_hive.sh --eval

# Tear down when done
bash experiments/hive_mind/deploy_azure_hive.sh --cleanup
```

### What Gets Provisioned

| Resource           | Details                                                              |
| ------------------ | -------------------------------------------------------------------- |
| Resource Group     | `hive-mind-rg` (eastus)                                              |
| Container Registry | `hivacrhivemind` — Basic SKU, admin enabled                          |
| Service Bus        | `hive-sb-dj2qo2w7vu5zi` — Standard SKU, `hive-events` topic, 21 subs |
| Storage Account    | Azure Files share for Kuzu DB persistence                            |
| Container Apps     | 21 apps (20 domain + 1 adversary), 2.0 CPU / 4.0 GiB each            |

### Environment Overrides

```bash
export HIVE_RESOURCE_GROUP="my-rg"      # Default: hive-mind-rg
export HIVE_LOCATION="westus2"           # Default: eastus
export HIVE_AGENT_COUNT=10               # Default: 20
export HIVE_IMAGE_TAG="v2"               # Default: latest
```

## 6. Running the LearningAgent Eval

Compare single vs flat-sharing vs federated using real LLM agents:

```bash
# LearningAgent eval — real LLM fact extraction + synthesis
uv run python experiments/hive_mind/run_learning_agent_hive_eval.py \
  --turns 100 --questions 20 --agents 5 --groups 2

# Run just single condition (faster iteration)
uv run python experiments/hive_mind/run_learning_agent_hive_eval.py \
  --turns 50 --questions 10 --conditions single

# Use a specific model
uv run python experiments/hive_mind/run_learning_agent_hive_eval.py \
  --model claude-sonnet-4-5-20250929 --turns 100 --questions 20
```

For keyword-based eval scripts (no LLM, faster but less realistic):

```bash
# 20-agent distributed eval with Kuzu DBs
uv run python experiments/hive_mind/run_distributed_20agent_eval.py

# 20-agent distributed eval with event bus
uv run python experiments/hive_mind/run_full_distributed_eval.py
```

## Architecture

```
         Root Hive (InMemoryHiveGraph)
        ┌────┼────────┐─────────┐
    People Tech  Data  Ops  Misc
     Hive  Hive  Hive  Hive  Hive
      │     │     │     │     │
   agents agents agents agents agents
   (own    (own   (own   (own   (own
    Kuzu)  Kuzu)  Kuzu)  Kuzu)  Kuzu)
```

- Each agent owns its own Kuzu DB (private knowledge)
- Hive nodes are HiveGraph instances (shared knowledge)
- Federation enables recursive cross-tree queries
- EventBus propagates facts between agents (Local/Redis/Azure Service Bus)
- HiveController reconciles desired state from YAML manifests

## Key Files

| File                                         | Purpose                                           |
| -------------------------------------------- | ------------------------------------------------- |
| `src/.../hive_mind/hive_graph.py`            | HiveGraph protocol, InMemoryHiveGraph, federation |
| `src/.../hive_mind/controller.py`            | HiveController (desired-state YAML manifests)     |
| `src/.../hive_mind/distributed.py`           | AgentNode, HiveCoordinator                        |
| `src/.../hive_mind/event_bus.py`             | EventBus protocol + Local/Azure SB/Redis backends |
| `tests/hive_mind/`                           | 192 tests                                         |
| `experiments/hive_mind/`                     | 15 eval scripts                                   |
| `experiments/hive_mind/deploy_azure_hive.sh` | Azure deployment (idempotent)                     |
