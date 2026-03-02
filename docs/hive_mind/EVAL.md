# Distributed Hive Mind — Evaluation Guide

## Overview

The hive mind evaluation uses **real LLM-backed LearningAgents** (not keyword matching) to measure whether distributed knowledge sharing improves agent performance on a long-horizon memory benchmark.

Each agent uses:

- **CognitiveMemory** (Kuzu graph DB) for local fact storage
- **LLM extraction** (~3 calls per content turn) for structured fact extraction
- **LLM synthesis** (~2 calls per question) for answer generation
- **Hybrid grading** (deterministic rubric + LLM judgment) for scoring

## The LearningAgent Eval

### Script

```bash
uv run python experiments/hive_mind/run_learning_agent_hive_eval.py \
  --turns 100 --questions 20 --agents 5 --groups 2
```

### Three Conditions

| Condition     | Agents | Hive Topology                   | What It Tests                                  |
| ------------- | ------ | ------------------------------- | ---------------------------------------------- |
| **SINGLE**    | 1      | None                            | Baseline: one agent, no sharing                |
| **HIVE_FLAT** | N      | Single shared InMemoryHiveGraph | Does flat sharing help? (round-robin learning) |
| **HIVE_FED**  | N      | M groups in federation tree     | Does federation add value over flat?           |

### How It Works

1. **Data generation**: `generate_dialogue(num_turns=100)` creates 100 deterministic content turns across 12 information blocks (people, infrastructure, security, etc.)
2. **Learning phase**: Each turn is fed to `agent.learn_from_content(content)` which triggers LLM fact extraction. In multi-agent modes, turns are distributed round-robin.
3. **Auto-promotion**: `CognitiveAdapter.store_fact()` automatically promotes every stored fact to the shared hive. Other agents see these facts when they query.
4. **Quiz phase**: `agent.answer_question(question)` synthesizes answers using LLM from both local memory and hive facts.
5. **Grading**: Hybrid deterministic (rubric keywords) + LLM judgment on 5 dimensions.

### Key Architecture: CognitiveAdapter Hive Integration

```
learn_from_content(content)
  → LLM extracts facts
  → CognitiveAdapter.store_fact()
    → Stores in local Kuzu DB
    → Auto-promotes to hive (InMemoryHiveGraph)

answer_question(question)
  → CognitiveAdapter.search() / get_all_facts()
    → Queries local Kuzu DB
    → Queries shared hive
    → Merges + deduplicates (local facts prioritized)
  → LLM synthesizes answer from merged facts
```

### Expected Timing

| Turns | Questions | LLM Calls/Condition | Time/Condition (Sonnet) |
| ----- | --------- | ------------------- | ----------------------- |
| 100   | 20        | ~340                | 5-10 min                |
| 1000  | 100       | ~3400               | 50-100 min              |

### CLI Options

```
--turns N          Dialogue turns (default: 100)
--questions N      Quiz questions (default: 20)
--agents N         Agents for hive conditions (default: 5)
--groups N         Groups for federated condition (default: 2)
--model MODEL      LLM model (default: claude-sonnet-4-5-20250929)
--conditions LIST  Comma-separated: single,flat,federated
--output PATH      Output JSON path
--parallel-workers Workers for Q&A grading (default: 5)
```

## Scoring Dimensions

Each question is graded on 5 dimensions (0.0 to 1.0):

| Dimension                  | Grading Method | What It Measures                             |
| -------------------------- | -------------- | -------------------------------------------- |
| **factual_accuracy**       | Deterministic  | Are required keywords present in the answer? |
| **specificity**            | Deterministic  | Are specific details included (not generic)? |
| **temporal_awareness**     | LLM            | Does the answer respect temporal ordering?   |
| **source_attribution**     | LLM            | Can the agent cite where facts came from?    |
| **confidence_calibration** | LLM            | Is the agent's confidence well-calibrated?   |

Overall score = average across all dimensions for all questions.

## Azure Deployment Eval

### Agent Runner (v2.0 — LearningAgent)

The Azure agent runner (`experiments/hive_mind/agent_runner.py`) now wraps a real LearningAgent:

- `/learn` endpoint: feeds raw content to `agent.learn_from_content()` (LLM extraction)
- `/query` endpoint: calls `agent.answer_question()` (LLM synthesis)
- Service Bus propagates facts between containers
- Each container has its own Kuzu DB + shared hive store

```bash
# Deploy
bash experiments/hive_mind/deploy_azure_hive.sh

# Check status
bash experiments/hive_mind/deploy_azure_hive.sh --status

# Run eval
bash experiments/hive_mind/deploy_azure_hive.sh --eval

# Cleanup
bash experiments/hive_mind/deploy_azure_hive.sh --cleanup
```

## Interpreting Results

### Output JSON Structure

```json
{
  "config": {
    "turns": 100, "questions": 20, "model": "claude-sonnet-4-5-20250929",
    "seed": 42, "agents": 5, "groups": 2
  },
  "results": [
    {
      "mode": "single",
      "num_agents": 1,
      "overall_score": 0.75,
      "hive_facts": 0,
      "elapsed_s": 300.0,
      "category_breakdown": [...],
      "per_question": [...]
    }
  ]
}
```

### Results (2026-03-02, 100 turns, 20 questions, Sonnet 4.5)

| Condition  | Agents | Score      | Time   | Hive Facts |
| ---------- | ------ | ---------- | ------ | ---------- |
| **Single** | 1      | **96.75%** | 18 min | 0          |
| **Flat**   | 5      | **98.9%**  | 21 min | 519        |
| Federated  | 5 (2g) | 63.4%      | 22 min | 510        |

**Key findings:**

- **Flat sharing beats single agent by +2.15pp** — hive sharing provides genuine value
- Flat excels at incident tracking (50% → 97.5%) where cross-agent facts help
- **Federated underperforms** due to needle-in-haystack failures (0%) — the tree
  traversal drops facts that flat sharing preserves
- Federation penalty comes from requiring cross-group traversal which limits per-group results

### Category Breakdown

| Category                 | Single | Flat  | Federated |
| ------------------------ | ------ | ----- | --------- |
| needle_in_haystack       | 100%   | 100%  | 0%        |
| temporal_evolution       | 100%   | 100%  | 100%      |
| numerical_precision      | 100%   | 100%  | 33.3%     |
| cross_reference          | 100%   | 100%  | 75%       |
| meta_memory              | 100%   | 100%  | 100%      |
| source_attribution       | 100%   | 97.5% | 81.8%     |
| infrastructure_knowledge | 100%   | 100%  | 100%      |
| security_log_analysis    | 100%   | 100%  | 100%      |
| distractor_resistance    | 92.5%  | 92.5% | 77.5%     |
| incident_tracking        | 50%    | 97.5% | 100%      |

## Known Limitations

1. **LLM cost**: 100 turns x 3 conditions = ~1000 LLM calls. Use `--model` to select a cheaper model for rapid iteration.
2. **Round-robin distribution**: Simple round-robin may not optimally distribute facts by domain. Future work: domain-aware routing.
3. **Best-of-N answering**: Multi-agent adapter queries all agents and picks the longest answer. More sophisticated routing (by domain relevance) would improve results.
4. **In-memory hive**: Azure containers lose hive state on restart. Kuzu DB persists via Azure Files mount but the hive doesn't.
