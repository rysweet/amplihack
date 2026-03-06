# From Prompt to Hive Mind

A step-by-step tutorial that takes you from a single LearningAgent to a
federated hive mind running in Azure. Each step is self-contained with working
code you can copy-paste.

**Prerequisites**

```bash
cd amplihack5
uv sync                          # install dependencies
export ANTHROPIC_API_KEY="your-key-here"  # pragma: allowlist secret
```

---

## Step 1: Single Agent

Create a LearningAgent, feed it content, and ask it questions. This is the
baseline — one agent, one Kuzu database, no sharing.

```python
from pathlib import Path
from amplihack.agents.goal_seeking.learning_agent import LearningAgent

# Create a cloud security analyst
agent = LearningAgent(
    agent_name="sec-analyst",
    storage_path=Path("/tmp/sec-analyst-db"),
    use_hierarchical=True,          # use CognitiveMemory (Kuzu graph DB)
)

# Feed it infrastructure observations
agent.learn_from_content(
    "Server prod-db-01 runs PostgreSQL 15.4 on 10.0.1.5:5432. "
    "It has 64 GB RAM, 16 vCPUs, and handles the primary OLTP workload. "
    "Last patched 2025-12-01."
)

agent.learn_from_content(
    "Security incident INC-2025-0042: Brute-force SSH attempts detected on "
    "prod-db-01 from 203.0.113.17. Firewall rule FW-101 was added to block "
    "the source IP. Incident resolved 2025-12-15."
)

# Ask questions — the agent synthesizes answers from what it learned
answer = agent.answer_question(
    "What database runs on prod-db-01 and was it involved in any incidents?"
)
print(answer)

agent.close()
```

Under the hood, each `learn_from_content()` call triggers:

1. **LLM extraction** (~3 calls): temporal metadata, structured facts as JSON,
   and a summary concept map
2. **Local storage**: facts stored in the agent's Kuzu graph database
3. **No sharing**: facts stay local — only this agent can see them

Each `answer_question()` call triggers:

1. **Retrieval**: search local Kuzu DB for relevant facts
2. **LLM synthesis** (~2 calls): generate an answer from retrieved context

---

## Step 2: Two Agents Sharing a Hive

Now connect two agents through a shared `InMemoryHiveGraph`. Agent A learns
infrastructure facts, Agent B learns incident facts. Either agent can answer
questions about both topics because facts are shared through the hive.

```python
from pathlib import Path
from amplihack.agents.goal_seeking.learning_agent import LearningAgent
from amplihack.agents.goal_seeking.hive_mind.hive_graph import InMemoryHiveGraph

# Create the shared hive
hive = InMemoryHiveGraph("shared-hive")
hive.register_agent("infra-analyst")
hive.register_agent("incident-analyst")

# Create two agents — both point at the same hive
agent_a = LearningAgent(
    agent_name="infra-analyst",
    storage_path=Path("/tmp/infra-analyst-db"),
    use_hierarchical=True,
    hive_store=hive,       # <-- auto-promotes facts to the shared hive
)

agent_b = LearningAgent(
    agent_name="incident-analyst",
    storage_path=Path("/tmp/incident-analyst-db"),
    use_hierarchical=True,
    hive_store=hive,
)

# Agent A learns infrastructure
agent_a.learn_from_content(
    "Server prod-web-01 runs Nginx 1.25 on 10.0.2.10:443. "
    "It serves the public API behind Azure Front Door."
)

agent_a.learn_from_content(
    "Server prod-db-01 runs PostgreSQL 15.4 on 10.0.1.5:5432 "
    "with 3 read replicas (prod-db-02, prod-db-03, prod-db-04)."
)

# Agent B learns incidents
agent_b.learn_from_content(
    "INC-2025-0051: SQL injection attempt on prod-web-01 via /api/users "
    "endpoint. WAF rule WAF-203 blocked the payload. No data exfiltration."
)

# Agent B can answer infra questions — facts came from Agent A via the hive
answer = agent_b.answer_question(
    "What server runs PostgreSQL and how many read replicas does it have?"
)
print(f"Agent B (incident analyst) answers infra question:\n{answer}\n")

# Agent A can answer incident questions — facts came from Agent B via the hive
answer = agent_a.answer_question(
    "Were there any SQL injection attempts? What server was targeted?"
)
print(f"Agent A (infra analyst) answers incident question:\n{answer}")

agent_a.close()
agent_b.close()
```

**How auto-promotion works**: When `CognitiveAdapter.store_fact()` runs inside
`learn_from_content()`, it stores the fact in the agent's local Kuzu DB AND
promotes it to the hive via `hive.promote_fact()`. When `answer_question()`
runs, it queries both local Kuzu and the hive, deduplicates by content, and
returns merged results.

**Key insight**: Learn once, available everywhere. Agent A never learned about
incidents, but it can answer incident questions because the facts are in the
shared hive.

---

## Step 3: Federated Hive Mind

Scale to 10 agents across 2 teams (SOC + Infrastructure). Each team has its own
group hive. A root hive connects the groups. High-confidence facts (>= 0.9)
broadcast across groups automatically. All facts are reachable via federated
queries.

```python
from pathlib import Path
from amplihack.agents.goal_seeking.learning_agent import LearningAgent
from amplihack.agents.goal_seeking.hive_mind.hive_graph import InMemoryHiveGraph

# Build the federation tree: root -> [soc-group, infra-group]
root = InMemoryHiveGraph("root-hive", enable_gossip=True, enable_ttl=True)

soc_group = InMemoryHiveGraph("soc-group", enable_gossip=True, enable_ttl=True)
soc_group.set_parent(root)
root.add_child(soc_group)

infra_group = InMemoryHiveGraph("infra-group", enable_gossip=True, enable_ttl=True)
infra_group.set_parent(root)
root.add_child(infra_group)

# Create 5 SOC agents
soc_agents = []
for i in range(5):
    name = f"soc-agent-{i}"
    soc_group.register_agent(name, domain="security")
    agent = LearningAgent(
        agent_name=name,
        storage_path=Path(f"/tmp/fed-soc-{i}"),
        use_hierarchical=True,
        hive_store=soc_group,
    )
    soc_agents.append(agent)

# Create 5 infra agents
infra_agents = []
for i in range(5):
    name = f"infra-agent-{i}"
    infra_group.register_agent(name, domain="infrastructure")
    agent = LearningAgent(
        agent_name=name,
        storage_path=Path(f"/tmp/fed-infra-{i}"),
        use_hierarchical=True,
        hive_store=infra_group,
    )
    infra_agents.append(agent)

# SOC agents learn security events
soc_agents[0].learn_from_content(
    "ALERT: Lateral movement detected from 10.0.1.5 to 10.0.2.10 "
    "using compromised credentials. Containment initiated."
)
soc_agents[1].learn_from_content(
    "Threat intel: APT-29 campaign targeting PostgreSQL instances "
    "via CVE-2025-1234. Patch available in PG 15.5."
)

# Infra agents learn infrastructure state
infra_agents[0].learn_from_content(
    "Server prod-db-01 (10.0.1.5) upgraded to PostgreSQL 15.5. "
    "Patch applied for CVE-2025-1234. Verified by infra team."
)

# Enable gossip between groups (peers = sibling hives)
soc_group.run_gossip([infra_group])
infra_group.run_gossip([soc_group])

# Cross-team knowledge discovery via federated query
# An infra agent can find security facts from the SOC group
answer = infra_agents[2].answer_question(
    "What threats target PostgreSQL and has prod-db-01 been patched?"
)
print(f"Infra agent answers cross-team question:\n{answer}")

# Clean up
for agent in soc_agents + infra_agents:
    agent.close()
```

**How federation works**:

- Facts learned by SOC agents land in the `soc-group` hive
- Facts with confidence >= 0.9 auto-broadcast to sibling groups via root
- `query_federated()` traverses local group -> root -> sibling groups
- **RRF (Reciprocal Rank Fusion)** merges results from all groups
- **Domain routing** gives 3x priority to groups matching query keywords
- **Gossip** proactively pushes top-K facts to peer hives
- **TTL** decays fact confidence over time; `gc()` removes expired facts

---

## Step 4: Prompt Variants

The LearningAgent supports 5 prompt variants that control the system prompt
used during LLM synthesis. These range from minimal to expert-level.

### The 5 Variants

| Variant | Style      | Description                                            |
| ------- | ---------- | ------------------------------------------------------ |
| 1       | Minimal    | Bare-bones: "Answer questions about the environment"   |
| 2       | Basic      | Adds uncertainty awareness: "When uncertain, say so"   |
| 3       | Structured | Explicit instructions for each answer dimension        |
| 4       | Detailed   | Full context about infrastructure/security domains     |
| 5       | Expert     | Memory organization instructions, multi-step reasoning |

### Using Prompt Variants

```bash
# Run eval with variant 3 (structured)
PYTHONPATH=src uv run python experiments/hive_mind/run_learning_agent_hive_eval.py \
  --turns 50 --questions 10 --prompt-variant 3

# Compare all variants
for v in 1 2 3 4 5; do
  PYTHONPATH=src uv run python experiments/hive_mind/run_learning_agent_hive_eval.py \
    --turns 50 --questions 10 --prompt-variant $v \
    --output /tmp/variant_${v}_results.json
done
```

In code:

```python
agent = LearningAgent(
    agent_name="analyst",
    storage_path=Path("/tmp/variant-test"),
    use_hierarchical=True,
    prompt_variant=3,   # 1-5
)
```

### Current Limitation

Prompt variants only affect the **synthesis prompt** (the system prompt used
when generating answers from retrieved facts). They do not affect:

- Fact extraction prompts (used during `learn_from_content()`)
- Concept map generation
- Grading prompts

### Creating Full Persona Variants

To create a complete persona that affects all LLM calls, you would need to:

1. Create variant files in `src/amplihack/agents/goal_seeking/prompts/variants/`
2. Modify `learn_from_content()` to use variant-specific extraction prompts
3. Modify `_generate_concept_map()` to use variant-specific map prompts

The current design keeps variants focused on synthesis since that's where prompt
differences have the largest measurable impact on eval scores.

---

## Step 5: Running the Eval

The eval measures whether hive mind sharing improves agent performance on a
long-horizon memory benchmark.

### Single Agent Baseline

```bash
PYTHONPATH=src uv run python experiments/hive_mind/run_learning_agent_hive_eval.py \
  --turns 100 --questions 20 --conditions single
```

### All Three Topologies

```bash
# Full 3-condition comparison: single vs flat vs federated
PYTHONPATH=src uv run python experiments/hive_mind/run_learning_agent_hive_eval.py \
  --turns 100 --questions 20 --agents 5 --groups 2
```

### CLI Options

```
--turns N            Content turns to learn (default: 100)
--questions N        Quiz questions to ask (default: 20)
--agents N           Agent count for hive conditions (default: 5)
--groups N           Group count for federated condition (default: 2)
--model MODEL        LLM model (default: claude-sonnet-4-5-20250929)
--conditions LIST    Comma-separated: single,flat,federated (default: all)
--output PATH        Output JSON path
--prompt-variant N   Prompt variant 1-5
--parallel-workers N Parallel grading workers (default: 5)
--seed N             Random seed (default: 42)
```

### Continuous Eval with L1-L12

The eval harness uses 12 question categories (L1-L12) across 10 domains:

| Category                 | What It Tests                            |
| ------------------------ | ---------------------------------------- |
| needle_in_haystack       | Finding specific facts in a large corpus |
| temporal_evolution       | Understanding time-ordered changes       |
| numerical_precision      | Exact numbers, ports, versions           |
| cross_reference          | Connecting facts from different domains  |
| meta_memory              | Self-awareness of what agent has learned |
| source_attribution       | Citing where facts originated            |
| infrastructure_knowledge | Server/network/deployment facts          |
| security_log_analysis    | Security event interpretation            |
| distractor_resistance    | Ignoring irrelevant information          |
| incident_tracking        | Following incident timelines             |

### Interpreting Results

The output JSON contains per-condition scores, category breakdowns, and
per-question details. Key things to look for:

- **Single vs Flat**: Flat should equal or beat single (sharing adds coverage)
- **Flat vs Federated**: Federation may trail flat at small scale due to
  multi-pool scoring overhead; check per-category for where gaps appear
- **Category breakdown**: Identifies which question types benefit most from
  sharing (cross_reference and incident_tracking typically benefit most)
- **Hive fact counts**: Federated conditions show more total facts (broadcast
  copies across groups)

### Confidence Intervals

For statistically meaningful results, run 3+ trials with different seeds:

```bash
for seed in 42 123 456; do
  PYTHONPATH=src uv run python experiments/hive_mind/run_learning_agent_hive_eval.py \
    --turns 100 --questions 20 --seed $seed \
    --output /tmp/eval_seed_${seed}.json
done
```

Compare median scores across runs. Single runs are unreliable due to LLM
stochasticity.

### Expected Timing

| Turns | Questions | LLM Calls/Condition | Approx Time/Condition |
| ----- | --------- | ------------------- | --------------------- |
| 50    | 10        | ~170                | 2-5 min               |
| 100   | 20        | ~340                | 5-10 min              |
| 1000  | 100       | ~3400               | 50-100 min            |

---

## Step 6: Azure Deployment

Deploy the hive mind to Azure Container Apps for production-scale evaluation.

### Overview

The deploy script (`experiments/hive_mind/deploy_azure_hive.sh`) provisions
everything idempotently:

```bash
# Deploy 20 domain agents + 1 adversary
bash experiments/hive_mind/deploy_azure_hive.sh

# Check deployment status
bash experiments/hive_mind/deploy_azure_hive.sh --status

# Run the eval against deployed agents
bash experiments/hive_mind/deploy_azure_hive.sh --eval

# Tear down when done
bash experiments/hive_mind/deploy_azure_hive.sh --cleanup
```

### What Gets Provisioned

| Resource           | Details                                                                   |
| ------------------ | ------------------------------------------------------------------------- |
| Resource Group     | `hive-mind-rg` (eastus)                                                   |
| Container Registry | `hivacrhivemind` — Basic SKU, admin enabled                               |
| Service Bus        | `hive-sb-dj2qo2w7vu5zi` — Standard SKU, `hive-events` topic, 21 subs     |
| Storage Account    | Azure Files share for Kuzu DB persistence                                 |
| Container Apps     | 21 apps (20 domain + 1 adversary), 2.0 CPU / 4.0 GiB each                |
| Log Analytics      | Centralized logging workspace                                             |

### 21 Containers

- **20 domain agents**: 10 domains x 2 agents each (biology, chemistry, physics,
  math, compsci, history, geography, economics, psychology, engineering)
- **1 adversarial agent**: Injects incorrect facts to test consensus filtering

Each container runs the `agent_runner.py` HTTP server:

- `POST /learn` — feeds content to `agent.learn_from_content()`
- `POST /query` — calls `agent.answer_question()`
- Service Bus propagates `FACT_PROMOTED` events between containers

### Difference from Local Eval

| Aspect              | Local (in-process)                       | Azure (containers)                       |
| ------------------- | ---------------------------------------- | ---------------------------------------- |
| Hive sharing        | Shared Python object (InMemoryHiveGraph or DistributedHiveGraph) | Service Bus topic/subscription broadcast via NetworkGraphStore |
| Fact propagation    | Instant (same memory space)              | Async (Service Bus message delivery)     |
| Storage             | Temp directories                         | Azure Files (persistent Kuzu DBs)        |
| Topology            | Flat or federated tree                   | Flat broadcast (all agents subscribe)    |
| Agent communication | Direct method calls                      | HTTP + Service Bus                       |

### Environment Overrides

```bash
export HIVE_RESOURCE_GROUP="my-rg"      # Default: hive-mind-rg
export HIVE_LOCATION="westus2"           # Default: eastus
export HIVE_AGENT_COUNT=10               # Default: 20
export HIVE_IMAGE_TAG="v2"               # Default: latest
```

### Prerequisites

- Azure CLI authenticated (`az login`)
- `ANTHROPIC_API_KEY` environment variable set
- Active Azure subscription selected

---

## Next Steps

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — deep dive into data structures,
  CRDTs, gossip protocol, and retrieval pipeline
- **[EVAL.md](EVAL.md)** — evaluation methodology, scoring dimensions, and
  interpreting results
- **[DESIGN.md](DESIGN.md)** — original design decisions and trade-offs
