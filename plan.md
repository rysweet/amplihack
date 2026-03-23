# PR #3175 — Distributed Hive: Single-Agent-Equivalent Performance

## Goal

Fix Azure distributed hive (amplihive3175) to achieve single-agent-equivalent
performance on the bounded 60-turn / 8-question / 10-agent smoke test by
eliminating shard-query storms and missing answers.

## Architecture Summary

- **10 agents** deployed as 2 Container Apps (5 agents each) in `hive-pr3175-rg`
  / `westus2`
- **Transport**: Azure Event Hubs (CBS-free AMQP — reliable in Container Apps)
- **Memory**: CognitiveMemory (Kuzu graph) with DHT-based shard routing
- **3 Event Hubs**: `hive-events-amplihive3175` (input),
  `hive-shards-amplihive3175` (DHT), `eval-responses-amplihive3175`
- **ACR**: `hivacr3175621757.azurecr.io/amplihive3175:latest`

## Root Causes Found and Fixed

### RCA 1: Shard Query Storms (commits 5d413b424, 437302489)

- **Cause**: Every agent fan-out produced O(N²) shard queries — one SHARD_QUERY
  per peer × number of turns
- **Fix 1** (5d413b424): Reduced redundant fanout — each query only asks the
  owning shard, not all shards
- **Fix 2** (437302489): Parallelised shard query handling — concurrent.futures
  ThreadPoolExecutor for SHARD_QUERY events
- **Fix 3** (6d1c0c633): Raised shard query timeout to 30s (was 5s), preventing
  premature empty responses

### RCA 2: Question-Shaped Feed Content Entering answer_question() (commit bfb6232f1)

- **Cause**: `LEARN_CONTENT` events and startup identity
  (`agent.process(f"Agent identity: ...")`) both go through `agent.process()` →
  `decide()` which classifies question-like text as "answer" → fires
  `answer_question()` → triggers distributed shard recall storms even during
  learning phase
- **Fix** (bfb6232f1):
  - Added `GoalSeekingAgent.process_store()` method that force-routes to store
    path (bypasses `decide()`)
  - `_handle_event()` and `_run_event_driven_loop()` now call `process_store()`
    for `LEARN_CONTENT` events
  - Startup identity uses `process_store()` instead of `process()`
  - All 84 unit tests pass

### RCA 3: Duplicate Question Recall in Orient (commit a2651645c)

- **Cause**: `orient()` was recalling from the distributed graph for every
  input, including store operations — amplifying shard traffic
- **Fix**: Added guard so orient-time recall only happens for question inputs

### RCA 4: Gossip Peer Selection (commit e0ebede38)

- **Cause**: Random gossip selected peers non-deterministically, creating hot
  spots
- **Fix**: Deterministic peer selection based on agent index

## Current State (as of 2026-03-16)

**Branch**: `feat/issue-3172-cognitive-memory-unified-graph-clean` **Latest
commit**: `bfb6232f1 fix: force store path for learning events`
**Infrastructure**: amplihive3175 deployed, NOT yet updated with latest image

### Test Results (local)

- `TestGoalSeekingAgentProcessStore` — 1/1 PASSED ✅
- `TestAgentEntrypoint` (48 tests) — 48/48 PASSED ✅
- `TestPartitionRouting` (36 tests) — 36/36 PASSED ✅

### Remaining Work

1. **Rebuild Docker image** with `bfb6232f1` changes and push to ACR
2. **Redeploy** Container Apps with new image
3. **Run smoke test**: 60 turns, 8 questions, 10 agents, 120s answer timeout
4. **Compare** against single-agent baseline, document recall rate
5. If gaps remain: trace remaining structural causes with concrete evidence

## Smoke Test Command

```bash
cd deploy/azure_hive
python eval_distributed.py \
  --connection-string "$EH_CONN" \
  --input-hub hive-events-amplihive3175 \
  --response-hub eval-responses-amplihive3175 \
  --turns 60 --questions 8 --agents 10 \
  --answer-timeout 120 \
  --output /tmp/smoke_60t_8q_10a.json
```

## Single-Agent Baseline

Reference: run
`python -m amplihack.eval.long_horizon_memory --turns 60 --questions 8` locally.
Expected recall: ≥ 7/8 (87.5%) to match single-agent behavior.

## Eval Results

| Run | Turns | Questions | Agents | Recall | Notes                  |
| --- | ----- | --------- | ------ | ------ | ---------------------- |
| TBD | 60    | 8         | 10     | TBD    | After bfb6232f1 deploy |
