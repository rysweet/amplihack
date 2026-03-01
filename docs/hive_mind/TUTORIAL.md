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

## 3. P2P with Raft Consensus (PeerHiveGraph)

For distributed deployments where agents ARE the store. Uses pysyncobj for
Raft consensus — no single point of failure.

```bash
pip install pysyncobj
```

```python
from amplihack.agents.goal_seeking.hive_mind.hive_graph import create_hive_graph

# Create 3 Raft peers (run each in a separate process for real use)
peer1 = create_hive_graph("p2p",
    hive_id="peer-1",
    self_address="localhost:4321",
    peer_addresses=["localhost:4322", "localhost:4323"],
)
peer2 = create_hive_graph("p2p",
    hive_id="peer-2",
    self_address="localhost:4322",
    peer_addresses=["localhost:4321", "localhost:4323"],
)
peer3 = create_hive_graph("p2p",
    hive_id="peer-3",
    self_address="localhost:4323",
    peer_addresses=["localhost:4321", "localhost:4322"],
)

# Write to the leader (Raft elects one automatically)
import time
time.sleep(2)  # Wait for leader election

peer1.register_agent("agent_a", domain="biology")
peer1.promote_fact("agent_a", HiveFact(
    fact_id="", content="DNA stores genetic information",
    concept="genetics", confidence=0.99,
))

# Query any peer — Raft replication ensures consistency
time.sleep(1)
results = peer2.query_facts("DNA genetics")
print(f"Peer2 found: {len(results)} results")

# Clean up
for p in [peer1, peer2, peer3]:
    p.close()
```

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

| Resource           | Details                                                   |
| ------------------ | --------------------------------------------------------- |
| Resource Group     | `hive-mind-eval-rg` (eastus)                              |
| Service Bus        | Standard SKU, `hive-events` topic, 21 subscriptions       |
| Storage Account    | Azure Files share for Kuzu DB persistence                 |
| Container Registry | Basic SKU for agent images                                |
| Container Apps     | 21 apps (20 domain + 1 adversary), 2.0 CPU / 4.0 GiB each |

### Environment Overrides

```bash
export HIVE_RESOURCE_GROUP="my-rg"      # Default: hive-mind-eval-rg
export HIVE_LOCATION="westus2"           # Default: eastus
export HIVE_AGENT_COUNT=10               # Default: 20
export HIVE_IMAGE_TAG="v2"               # Default: latest
```

## 6. Running the Local Eval

Compare isolated vs federated vs distributed retrieval quality:

```bash
# 5-agent rigorous eval (flat vs gossip vs hive)
uv run python experiments/hive_mind/run_rigorous_eval.py

# 20-agent distributed eval with real Kuzu DBs
uv run python experiments/hive_mind/run_full_distributed_eval.py

# 20-agent eval with HiveGraph federation
uv run python experiments/hive_mind/run_distributed_20agent_eval.py
```

## Architecture

```
         Root Hive (InMemoryHiveGraph or PeerHiveGraph)
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
| `src/.../hive_mind/peer_hive.py`             | PeerHiveGraph (Raft consensus via pysyncobj)      |
| `src/.../hive_mind/controller.py`            | HiveController (desired-state YAML manifests)     |
| `src/.../hive_mind/distributed.py`           | AgentNode, HiveCoordinator                        |
| `src/.../hive_mind/event_bus.py`             | EventBus protocol + Local/Azure SB/Redis backends |
| `tests/hive_mind/`                           | 192 tests                                         |
| `experiments/hive_mind/`                     | 15 eval scripts                                   |
| `experiments/hive_mind/deploy_azure_hive.sh` | Azure deployment (idempotent)                     |
