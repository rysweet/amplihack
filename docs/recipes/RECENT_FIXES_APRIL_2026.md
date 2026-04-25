# Recent Fixes — April 2026

This document tracks bug fixes and improvements merged in April 2026, following
the [Diátaxis](https://diataxis.fr/) framework (Explanation sections).

---

## April 25 — Eval Async/Sync Contract Fixes

Two sequential fixes in the `amplihack-agent-eval` progressive test suite
resolved a class of bugs where Python's `asyncio.run()` was misapplied to
sync methods, or omitted from genuinely async ones.

### Don't wrap sync `answer_question` with `asyncio.run()` (PR #4471)

**Problem**: `agent_subprocess.py` called `asyncio.run(agent.answer_question(...))`
inside the `testing_phase` function. Every L1–L12 level failed with:

```
ValueError: a coroutine was expected, got ('', ReasoningTrace(...))
```

The bench logs obscured the root cause by reporting
`Testing phase failed: WARNING: amplihack_memory.graph not available`.

**Root cause**: `AnswerSynthesizerMixin.answer_question`
(`src/amplihack/agents/goal_seeking/answer_synthesizer.py:52`) is a **sync**
method. It calls `_run_async_or_return` internally and returns the resolved
value directly. Passing the resolved tuple `('', ReasoningTrace)` to
`asyncio.run()` raised `ValueError` because `asyncio.run()` expects a coroutine,
not an already-resolved value.

**Fix**: Call `agent.answer_question(...)` directly without `asyncio.run()`.
`learn_from_content` (line 120) is genuinely async and remains wrapped.

**Rule**: Before wrapping a call with `asyncio.run()`, verify via the method
signature or docstring that the method is `async def`. Sync wrappers that
internally dispatch to async code (like `_run_async_or_return`) return
synchronously — wrapping them is incorrect.

---

### Await async `grade_metacognition` in progressive suite (PR #4472)

**Problem**: This bug was hidden by the #4471 error above. Once #4471 was
fixed and `answer_question` began returning the correct trace, the downstream
`grade_metacognition` call surfaced a new failure across all L1–L12 levels:

```
RuntimeWarning: coroutine 'grade_metacognition' was never awaited
✗ L1 failed: 'coroutine' object has no attribute 'effort_calibration'
✗ L2 failed: 'coroutine' object has no attribute 'effort_calibration'
... (repeats L1 through L12)
```

**Root cause**: `grade_metacognition` is **async**
(`metacognition_grader.py:280`) but `progressive_test_suite.run_single_level`
is a **sync** method and called it without `asyncio.run()`. The returned
coroutine was never awaited; the subsequent `.effort_calibration` access
raised `AttributeError`.

**Fix**: Wrap the call with `asyncio.run(grade_metacognition(...))` and add
the `asyncio` import to `progressive_test_suite.py`.

**Rule**: When a sync function must call an async function, use
`asyncio.run()`. When an async function calls another async function, use
`await`. The `run_single_level` function is sync, so `asyncio.run()` is the
correct bridge.

---

### Summary table

| PR | File | Bug | Fix |
|----|------|-----|-----|
| #4471 | `eval/agent_subprocess.py` | `asyncio.run()` on sync `answer_question` | Call directly |
| #4472 | `progressive_test_suite.py` | Missing `asyncio.run()` on async `grade_metacognition` | Add `asyncio.run()` + import |

**Dependency**: #4472 was shadowed by #4471. Fix #4471 first to expose the
downstream grader bug.
