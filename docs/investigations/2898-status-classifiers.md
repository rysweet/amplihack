# Investigation: Unifying Dual Status Classifiers (#2898)

**Date**: 2026-03-07
**Branch**: investigate/2898-unify-status-classifiers
**Scope**: Investigation only — no code changes

---

## Summary

The codebase contains two distinct classification systems that both categorize
user intent/session type using keyword matching. This investigation examines
whether merging them into a canonical `_status.py` module is warranted.

**Conclusion: DO-NOT-RECOMMEND**

The classifiers serve fundamentally different purposes, operate at different
points in time, and accept different inputs. Unifying them would increase
coupling without removing meaningful duplication.

---

## 1. What Are the Two Classifiers?

### Classifier A: `WorkflowClassifier`

- **File**: `src/amplihack/workflows/classifier.py`
- **Class**: `WorkflowClassifier`
- **Purpose**: Proactive routing — classifies a user's request _before_ work begins
- **Input**: A single request string (`str`)
- **Output**: One of four workflow names:
  - `Q&A_WORKFLOW`
  - `OPS_WORKFLOW`
  - `INVESTIGATION_WORKFLOW`
  - `DEFAULT_WORKFLOW`
- **Method**: Keyword matching only, with fixed priority order (DEFAULT > INVESTIGATION > OPS > Q&A)
- **Answers the question**: "Which workflow recipe should I execute for this request?"

#### Keyword Map

| Workflow                 | Keywords (sample)                                              |
| ------------------------ | -------------------------------------------------------------- |
| `Q&A_WORKFLOW`           | `what is`, `explain briefly`, `quick question`, `what does`    |
| `OPS_WORKFLOW`           | `run command`, `disk cleanup`, `cleanup`, `organize`, `manage` |
| `INVESTIGATION_WORKFLOW` | `investigate`, `understand`, `analyze`, `how does`             |
| `DEFAULT_WORKFLOW`       | `implement`, `add`, `fix`, `create`, `refactor`, `update`      |

---

### Classifier B: `SessionDetectionMixin`

- **File**: `.claude/tools/amplihack/hooks/power_steering_checker/session_detection.py`
- **Class**: `SessionDetectionMixin` (mixed into `PowerSteeringChecker`)
- **Purpose**: Retroactive detection — classifies what _type of session actually occurred_
- **Input**: Full conversation transcript (`list[dict]`) including tool call records
- **Output**: One of six session types:
  - `SIMPLE`
  - `DEVELOPMENT`
  - `INFORMATIONAL`
  - `MAINTENANCE`
  - `INVESTIGATION`
  - `OPERATIONS`
- **Method**: Hybrid — keyword matching on early user messages _plus_ tool usage pattern analysis (file edits, test runs, PR operations, Read/Grep counts)
- **Answers the question**: "What kind of session was this, so we can apply appropriate power-steering enforcement?"

#### Detection Priority

1. Environment override (`AMPLIHACK_SESSION_TYPE`)
2. Simple task keywords (cleanup, fetch, sync)
3. OPERATIONS keywords (prioritize, backlog, roadmap, sprint)
4. Tool usage patterns (code changes, tests, PR creation) — **concrete evidence**
5. Investigation keywords as tiebreaker

---

## 2. Where Are They Used?

### WorkflowClassifier consumers

| File                                                        | Role                                                                                                                          |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| `src/amplihack/workflows/session_start_skill.py`            | `SessionStartClassifierSkill.process()` calls `classifier.classify()` at session start, then routes to `ExecutionTierCascade` |
| `src/amplihack/workflows/__init__.py`                       | Public re-export                                                                                                              |
| `tests/workflows/test_classifier.py`                        | 60+ unit tests                                                                                                                |
| `tests/workflows/test_regression.py`, `test_performance.py` | Regression and performance tests                                                                                              |

`WorkflowClassifier` is purely a routing component inside the workflow
orchestration path. It fires once at session start.

### SessionDetectionMixin consumers

| File                                                                                 | Role                                                                                          |
| ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------- |
| `.claude/tools/amplihack/hooks/power_steering_checker/main_checker.py`               | `PowerSteeringChecker` inherits this mixin; calls `detect_session_type()` per hook invocation |
| `amplifier-bundle/tools/amplihack/hooks/power_steering_checker/session_detection.py` | Bundled copy                                                                                  |
| `docs/claude/tools/amplihack/hooks/power_steering_checker.py`                        | Documentation copy                                                                            |
| 15+ test files                                                                       | Session classification tests, PR review classification, operations session tests              |

`SessionDetectionMixin` fires on every `PostToolUse` hook invocation for
power-steering enforcement. Its output gates which workflow checks apply.

---

## 3. What Would Unification Look Like?

A canonical `_status.py` would need to accommodate both classifiers. Two
approaches are possible:

### Option A: Shared Constants Module

Extract overlapping keyword lists into a shared module:

```
src/amplihack/workflows/_status.py
  INVESTIGATION_KEYWORDS = [...]   # shared
  OPERATIONS_KEYWORDS = [...]      # shared
  SIMPLE_TASK_KEYWORDS = [...]     # SessionDetectionMixin only
  QA_KEYWORDS = [...]              # WorkflowClassifier only
```

Both classifiers import from `_status.py`. Logic stays in the two existing
classes.

**Effort**: Low (~30 lines changed)
**Benefit**: Removes the handful of keyword strings that overlap

### Option B: Unified Classifier Class

A single `StatusClassifier` that accepts either a `str` or `list[dict]`
(transcript) and dispatches to the appropriate logic.

**Effort**: High — requires reconciling:

- 4-type vs. 6-type output taxonomy
- Keyword-only vs. hybrid (keyword + tool usage) logic
- Different callers, different timing, different contracts

---

## 4. Is the Complexity Justified?

### Arguments for unification

- **Shared keywords**: `INVESTIGATION_KEYWORDS` and some `OPERATIONS_KEYWORDS`
  appear in both classifiers. If a new category is added to one, the other may
  drift.
- **Single source of truth**: Taxonomy stays in sync if maintained in one place.

### Arguments against unification

| Dimension            | WorkflowClassifier        | SessionDetectionMixin               |
| -------------------- | ------------------------- | ----------------------------------- |
| Timing               | Session start (proactive) | Every hook invocation (retroactive) |
| Input                | Single string             | Full transcript + tool calls        |
| Output taxonomy      | 4 workflow names          | 6 session types                     |
| Detection method     | Keyword only              | Keyword + tool usage evidence       |
| Purpose              | Workflow routing          | Power-steering gating               |
| Size                 | ~200 lines                | ~600 lines                          |
| Unique session types | —                         | `SIMPLE`, `MAINTENANCE`             |
| Unique workflows     | `DEFAULT_WORKFLOW`        | —                                   |

- **Different abstractions**: The two classifiers answer different questions.
  Combining them creates a module that does two unrelated things.
- **Input incompatibility**: A `str` and a `list[dict]` transcript are not the
  same kind of input. A unified class needs branching logic or overloads that add
  confusion.
- **Taxonomy mismatch is intentional**: `INFORMATIONAL` (power steering) ≠
  `Q&A_WORKFLOW` (routing). Forcing one taxonomy would break callers.
- **Real overlap is small**: Only ~8 keywords actually overlap between
  `INVESTIGATION_KEYWORDS` (classifier) and `INVESTIGATION_KEYWORDS` (mixin).
  The rest of the keyword lists are distinct.
- **Option A is trivially extractable when needed**: If keyword drift becomes a
  real problem in practice, a shared constants module can be added then. The
  cost of waiting is near-zero.
- **Option B creates accidental complexity**: A single class that must handle
  two input types, two output vocabularies, and two timing scenarios violates
  single-responsibility. This is the exact pattern the project philosophy ("one
  responsibility per brick") warns against.

---

## 5. Conclusion

**DO-NOT-RECOMMEND** creating a canonical `_status.py` at this time.

The two classifiers are architecturally distinct: one is a pre-action router
operating on request text, the other is a post-action enforcer operating on
transcript evidence. Their apparent similarity in naming ("classify session
type") obscures a fundamental difference in purpose, input, timing, and output
contract.

The real duplication is limited to a small set of shared keyword strings.
That duplication does not justify the coupling that a unified class would
introduce. If keyword drift becomes a documented problem across multiple
issues, extracting a thin `_shared_keywords.py` constants module (Option A)
would be the right scoped fix — not a combined classifier.

**If this issue is re-examined in future**, the trigger should be a concrete bug
caused by keyword drift between the two classifiers, not speculative alignment.

---

## Appendix: Keyword Overlap Analysis

Keywords present in **both** classifiers:

| Keyword       | WorkflowClassifier category | SessionDetectionMixin category |
| ------------- | --------------------------- | ------------------------------ |
| `investigate` | INVESTIGATION_WORKFLOW      | INVESTIGATION                  |
| `understand`  | INVESTIGATION_WORKFLOW      | INVESTIGATION                  |
| `analyze`     | INVESTIGATION_WORKFLOW      | INVESTIGATION                  |
| `research`    | INVESTIGATION_WORKFLOW      | INVESTIGATION                  |
| `explore`     | INVESTIGATION_WORKFLOW      | INVESTIGATION                  |
| `how does`    | INVESTIGATION_WORKFLOW      | INVESTIGATION                  |
| `cleanup`     | OPS_WORKFLOW                | SIMPLE                         |
| `clean up`    | OPS_WORKFLOW                | SIMPLE                         |
| `organize`    | OPS_WORKFLOW                | SIMPLE                         |

Keywords present in **SessionDetectionMixin only** (no WorkflowClassifier equivalent):

- `SIMPLE_TASK_KEYWORDS`: git fetch, git pull, rebase, stash, checkout, list files, etc.
- `MAINTENANCE` detection: doc_files_only heuristic (no keywords)
- `DEVELOPMENT` detection: tool usage patterns (no keywords)
- Additional `INVESTIGATION_KEYWORDS`: troubleshoot, diagnos, figure out, why does, why is, what causes, root cause, debug, explain

Keywords present in **WorkflowClassifier only** (no SessionDetectionMixin equivalent):

- `Q&A_WORKFLOW`: what is, explain briefly, quick question, how do i run, what does, can you explain
- `DEFAULT_WORKFLOW`: implement, add, fix, create, refactor, update, build, develop, remove, delete, modify
