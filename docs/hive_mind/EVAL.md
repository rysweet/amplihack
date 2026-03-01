# Distributed Hive Mind — Evaluation Guide

## What the Eval Measures

The evaluation tests three capabilities of the hive mind system:

| Category               | What It Tests                                            | Pass Criteria                                                                                |
| ---------------------- | -------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| **Self-domain**        | Can an agent retrieve facts from its own knowledge?      | Returns >= 1 result for keyword query matching stored facts                                  |
| **Cross-domain**       | Can an agent find facts from a different agent's domain? | Returns >= 1 result for another domain's keywords (requires federation or event propagation) |
| **Needle-in-haystack** | Can an agent find a specific fact among many?            | The target fact appears in the top-3 results                                                 |

## Eval Modes

### Azure Deployment Eval (`--eval`)

Runs against live Azure Container Apps agents via HTTP:

```bash
bash experiments/hive_mind/deploy_azure_hive.sh --eval
```

**Phases**:

1. Health check all 21 agents
2. Send 5 domain-specific facts per agent (100 total across 10 domains)
3. Run 18 queries: 10 self-domain + 5 cross-domain + 3 needle-in-haystack
4. Collect per-agent stats
5. Save results to `experiments/hive_mind/eval_results_azure.json`

**Architecture**: Each agent runs an independent `InMemoryHiveGraph` in its own container. Cross-domain queries require event bus propagation (Azure Service Bus) to share facts between agents. Without federation, cross-domain scores are expected to be 0%.

### Local Eval Scripts

Run entirely in-process on the dev machine:

```bash
# 5-agent eval comparing 4 conditions (isolated, flat, gossip, hive)
uv run python experiments/hive_mind/run_rigorous_eval.py

# 20-agent distributed eval with real Kuzu DBs + HiveGraph federation
uv run python experiments/hive_mind/run_full_distributed_eval.py

# 20-agent eval with federation tree
uv run python experiments/hive_mind/run_distributed_20agent_eval.py
```

## Domain Facts

The eval uses 5 keyword-rich facts per domain. Each fact has:

- **concept**: Topic category (e.g., "genetics", "reactions", "mechanics")
- **content**: Factual statement with domain-specific keywords
- **confidence**: Score between 0.0 and 1.0

The 10 domains are: biology, chemistry, physics, math, compsci, history, geography, economics, psychology, engineering.

## Query Types

### Self-Domain Queries (10 queries)

Each query uses 3-4 keywords from the agent's own domain. Example:

- Agent `biology_1`, query: `"DNA genetics nucleotide"`
- Expected: Finds "DNA double helix stores genetic information..."

### Cross-Domain Queries (5 queries)

Each query uses keywords from a DIFFERENT domain than the agent. Example:

- Agent `biology_1`, query: `"chemical reactions bonds atoms"` (chemistry keywords)
- Expected: 0 results without federation; >0 with federation or event propagation

### Needle-in-Haystack Queries (3 queries)

Targeted queries for a specific fact among the agent's 5 stored facts. Example:

- Agent `biology_1`, query: `"mitochondria ATP energy powerhouse"`
- Expected: The mitochondria fact appears in top-3 results

## Interpreting Results

### Result JSON Structure

```json
{
  "date": "2026-03-01T23:01:02Z",
  "agents_deployed": 21,
  "agents_healthy": 21,
  "summary": {
    "total_queries": 18,
    "total_passed": 13,
    "self_domain": { "passed": 10, "total": 10 },
    "cross_domain": { "passed": 0, "total": 5 },
    "needle_in_haystack": { "passed": 3, "total": 3 }
  },
  "queries": [...],
  "agent_stats": [...]
}
```

### What Good Looks Like

| Scenario                             | Self-Domain | Cross-Domain | Needle |
| ------------------------------------ | ----------- | ------------ | ------ |
| Isolated agents (no sharing)         | 100%        | 0%           | 100%   |
| Event bus propagation only           | 100%        | 20-60%       | 100%   |
| Full federation tree                 | 100%        | 80-100%      | 100%   |
| Centralized (all facts in one store) | 100%        | 100%         | 100%   |

### Current Results (2026-03-01)

**Azure deployment (21 agents, isolated InMemoryHiveGraph per container)**:

- Self-domain: **10/10 (100%)**
- Cross-domain: **0/5 (0%)** — expected, no federation between containers
- Needle-in-haystack: **3/3 (100%)**
- All 21 agents healthy, 100 facts stored successfully

**Local parity test (720 facts, 5-hive federation)**:

- Flat vs federated delta: **0.0%** across all categories
- Confirms the federation fix (#2754) achieves full parity

## Scoring

- **Self-domain**: Binary pass/fail per query (>= 1 result = pass)
- **Cross-domain**: Binary pass/fail per query (>= 1 result = pass)
- **Needle**: Checks if the target fact appears in results (grep for specific keyword)
- **Overall**: `passed / total_queries * 100`

## How to Add New Test Cases

Edit the eval section of `experiments/hive_mind/deploy_azure_hive.sh`:

1. Add facts to `DOMAIN_FACTS[domain]` JSON arrays
2. Add queries to `SELF_QUERIES`, `CROSS_QUERIES`, or `NEEDLE_QUERIES` associative arrays
3. Results are automatically included in the JSON output

## Known Limitations

1. **No federation between Azure containers**: Each container has an independent InMemoryHiveGraph. Cross-domain queries can only work if the Service Bus event polling thread successfully propagates facts. This requires the containers to be running long enough for the background thread to poll and incorporate events.

2. **Keyword-based scoring**: The HiveGraph uses keyword overlap (tokenized word set intersection) for fact retrieval, not semantic similarity. Queries must share actual words with stored facts to match.

3. **In-memory state**: Azure Container Apps can scale to zero and lose all state. Facts must be re-taught after container restarts. For persistent state, use Kuzu with Azure Files mount.
