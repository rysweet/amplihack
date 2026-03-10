# Distributed Eval Plan

## Goal

Run LongHorizonMemoryEval against distributed agents and achieve parity
with single-agent (90%+). The eval harness, grading, and report format
are identical — only the agent adapter differs.

## Architecture

```
LongHorizonMemoryEval.run(RemoteAgentAdapter)
  │
  ├── Phase 1: Learning (5000 turns)
  │   └── adapter.learn_from_content(turn_text)
  │       └── Send LEARN_CONTENT to Service Bus topic
  │           with target_agent=agent-{learn_count % agent_count}
  │           → Each agent's ServiceBusInputSource skips non-targeted messages
  │           → Targeted agent processes via OODA: decide("store") → learn
  │           → 5000/100 = 50 turns per agent
  │
  ├── Phase 2: Wait for processing
  │   └── First answer_question() call triggers _wait_for_agents_idle()
  │       └── Polls agent-0 subscription queue depth via az CLI
  │       └── Loops until activeMessageCount == 0 (no timeout)
  │       └── Expected: ~12 min (50 real + 4950 skip-and-complete per agent)
  │
  └── Phase 3: Questioning (50 questions)
      └── adapter.answer_question(question_text)
          ├── Send INPUT to Service Bus topic
          │   with target_agent=agent-{question_count % agent_count}
          │   and event_id=uuid for correlation
          │   → Targeted agent processes via OODA: decide("answer") → act()
          │   → act() calls answer_question(), prints to stdout
          │   → act() fires on_answer(agent_name, answer) callback
          │   → Entrypoint's AnswerPublisher.publish_answer() sends
          │     {event_id, agent_id, answer} to eval-responses topic
          │
          └── Background listener thread on adapter
              → Subscribes to eval-responses topic (eval-reader subscription)
              → Matches response by event_id
              → Signals waiting answer_question() call
              → No timeout — waits until answer arrives

  └── Phase 4: Grading
      └── LongHorizonMemoryEval._grade_multi_vote() — identical to single-agent
```

## Code Walkthrough

### 1. RemoteAgentAdapter.learn_from_content()
**File**: `deploy/azure_hive/remote_agent_adapter.py`

```python
target_agent = self._learn_count % self._agent_count
target_name = f"agent-{target_agent}"
msg = {"event_type": "LEARN_CONTENT", "target_agent": target_name, ...}
self._sender.send_messages(msg)  # → Service Bus topic (all subscriptions receive)
```

All 100 subscriptions receive the message, but only the targeted agent processes it.

### 2. ServiceBusInputSource.next() — target filtering
**File**: `src/amplihack/agents/goal_seeking/input_source.py`

```python
target = raw.get("target_agent", "") or payload.get("target_agent", "")
if target and target != self._agent_name:
    self._receiver.complete_message(msg)  # Skip — not for this agent
    continue
```

Non-targeted agents complete the message (removing it from their queue)
without processing. This means each agent iterates through all 5000 messages
but only processes ~50.

### 3. GoalSeekingAgent.on_answer callback
**File**: `src/amplihack/agents/goal_seeking/goal_seeking_agent.py`

```python
# In act(), after producing an answer:
if self.on_answer:
    self.on_answer(self._agent_name, output)
```

Set by entrypoint via DI: `agent.on_answer = answer_publisher.publish_answer`

### 4. AnswerPublisher.publish_answer()
**File**: `deploy/azure_hive/agent_entrypoint.py`

```python
def publish_answer(self, agent_name, answer):
    msg = {"event_type": "EVAL_ANSWER", "event_id": self._current_event_id,
           "agent_id": agent_name, "answer": answer}
    self._sender.send_messages(msg)  # → eval-responses topic
```

The `_current_event_id` is set by `_CorrelatingInputSource.next()` which
reads `event_id` from the incoming Service Bus message metadata before
the agent's process() call.

### 5. _CorrelatingInputSource — event_id context setting
**File**: `deploy/azure_hive/agent_entrypoint.py`

```python
def next(self):
    text = self._source.next()
    meta = getattr(self._source, "last_event_metadata", {})
    event_id = meta.get("event_id", "")
    if event_id:
        self._publisher.set_context(event_id, ...)
    return text
```

This runs BEFORE agent.process(text), so the event_id is set when on_answer fires.

### 6. RemoteAgentAdapter._listen_for_answers() — background thread
**File**: `deploy/azure_hive/remote_agent_adapter.py`

```python
messages = receiver.receive_messages(max_message_count=50, max_wait_time=5)
for msg in messages:
    body = json.loads(str(msg))
    event_id = body.get("event_id", "")
    if event_id in self._answer_events:
        self._pending_answers[event_id] = body.get("answer", "")
        self._answer_events[event_id].set()  # Signal waiting thread
```

### 7. RemoteAgentAdapter.answer_question() — waits for signal
**File**: `deploy/azure_hive/remote_agent_adapter.py`

```python
answer_event = threading.Event()
self._answer_events[event_id] = answer_event
self._sender.send_messages(msg)  # Send question
answer_event.wait()  # No timeout — blocks until answer arrives
answer = self._pending_answers.pop(event_id)
return answer
```

## Known Failure Modes (from previous attempts)

| # | Failure | Root Cause | Status |
|---|---------|-----------|--------|
| 1 | 0% score — no answers | Log Analytics polling found wrong/stale answers | Fixed: on_answer callback via Service Bus |
| 2 | Answers truncated to 200 chars | `logger.info(..., output[:200])` | Fixed: removed truncation |
| 3 | Wrong answer for wrong question | No correlation between question and answer | Fixed: event_id in message, matched in listener |
| 4 | All agents answer every question | Service Bus topic broadcasts to all | Fixed: target_agent field, ServiceBusInputSource skips |
| 5 | Timeout waiting for answers | 5000 messages per agent (broadcast) | Fixed: partitioned content, 50 per agent |
| 6 | AnswerPublisher stdout wrapping failed | print() not intercepted in all envs | Fixed: on_answer callback instead |
| 7 | Questions sent before content processed | Fixed time-based wait too short | Fixed: poll queue depth until 0, no timeout |
| 8 | eval-responses topic name wrong | AMPLIHACK_HIVE_NAME not set | Fixed: env var in Bicep |

## Small-Scale Test Plan

**Test**: 10 turns, 3 questions, 5 agents

This specifically tests all 8 failure modes:
- 10 turns partitioned across 5 agents = 2 per agent (tests partitioning)
- Each agent receives 10 messages, skips 8, processes 2 (tests targeting)
- 3 questions to agents 0, 1, 2 (tests targeted question delivery)
- Answers must come back via eval-responses topic (tests callback)
- Answers must be full text (tests no truncation)
- Answers must match the correct question (tests event_id correlation)
- Questions must wait until queue empty (tests queue depth polling)
- eval-responses topic must use deployment-specific name (tests env var)

**Expected score**: 90%+ (matching single-agent at same scale)

**Validation checks**:
1. Agent-0 queue depth reaches 0 before questions sent
2. All 3 answers received via Service Bus (not timeout)
3. Each answer matches its question (not cross-contaminated)
4. Answers are full text (not truncated)
5. Score matches single-agent baseline at same turn count

## Full-Scale Test Plan

After small-scale passes: 5000 turns, 50 questions, 100 agents (Sonnet + Opus)
