# Recent Fixes — April 2026

This document explains bugs fixed and features landed in amplihack during April
2026, following the [Diátaxis](https://diataxis.fr/) framework. Each entry
covers the **problem**, the **fix**, and the **rule** to prevent recurrence.

---

## April 25, 2026 — Eval Reliability, LLM Provider Routing & Code Visualizer

### fix(eval): Don't Wrap Sync `answer_question` with `asyncio.run` (PR #4471)

**Problem**: Every L1-L12 testing phase in the Simard daemon failed with:

```
ValueError: a coroutine was expected, got ('', ReasoningTrace(...))
```

`agent_subprocess.py` wrapped `agent.answer_question(...)` inside
`asyncio.run()`. However, `AnswerSynthesizerMixin.answer_question` is a **sync**
method — it internally dispatches to the async implementation and returns the
resolved value directly via `_run_async_or_return`. Passing the already-resolved
tuple to `asyncio.run` raised `ValueError` because `asyncio.run` expects a
coroutine, not a tuple.

The bench logs masked the real error, surfacing it as:

```
Testing phase failed: WARNING: amplihack_memory.graph not available
```

**Fix**: Call `agent.answer_question(...)` directly without `asyncio.run`.
`learn_from_content` (line 120 in the same file) is genuinely async and remains
wrapped.

**Rule**: Before wrapping a method with `asyncio.run`, verify it returns a
coroutine and not an already-resolved value. Inspect `_run_async_or_return`
adapters carefully — they synchronize at call time and return the concrete
result, not a coroutine.

---

### fix(eval): Await Async `grade_metacognition` in Progressive Suite (PR #4472)

**Problem**: With PR #4471 fixing the `answer_question` wrapping, the downstream
call to `grade_metacognition` was now exposed. `progressive_test_suite
.run_single_level` (a sync method) called the async `grade_metacognition`
without `asyncio.run`, producing:

```
RuntimeWarning: coroutine 'grade_metacognition' was never awaited
AttributeError: 'coroutine' object has no attribute 'effort_calibration'
```

L1-L12 benchmarks therefore scored every level as failed.

**Fix**: Wrap the call with `asyncio.run(grade_metacognition(...))`. Add the
`asyncio` import to `progressive_test_suite.py`.

**Rule**: When a sync caller needs an async result, use `asyncio.run`. The
inverse (#4471) — using `asyncio.run` on a sync method — is also wrong. Audit
both directions whenever bridging sync/async boundaries.

---

### fix(llm): Honor `SIMARD_LLM_PROVIDER` / `AMPLIHACK_LLM_PROVIDER` Env Override (PR #4477)

**Problem**: Simard's OODA daemon scored **0.00% on every L1-L12 evaluation**
while reporting `✓ completed` (hollow success). Root cause: two intertwined bugs
caused the LLM router to silently default to the bundled Claude Code CLI, which
was "Not logged in".

**Bug 1 — `_detect_launcher` is purely file-based**: Detection read
`<project_root>/.claude/runtime/launcher_context.json`. If the file was missing,
stale, or malformed, it returned `"claude"`. Callers that bypass
`amplihack copilot` (such as Simard's Rust daemon importing `amplihack.eval`
directly via Python subprocess) never had a launcher context file written, so
`SIMARD_LLM_PROVIDER=copilot` was ignored every time.

**Bug 2 — Copilot SDK probe imports a non-existent module**:

```python
from copilot.types import MessageOptions, SessionConfig  # copilot >= 0.1.0: ModuleNotFoundError
```

This silently set `_COPILOT_SDK_OK = False`, making the entire copilot path dead
code. `_query_copilot` also called a stale API (`client.start()`,
`session.send_and_wait(MessageOptions(prompt=...))`) that no longer exists.

**Fix**:

- `_detect_launcher` now checks `AMPLIHACK_LLM_PROVIDER` then
  `SIMARD_LLM_PROVIDER` first; an explicit override wins unconditionally. File
  detection is the second tier; `"claude"` remains the final fallback.
- Recognized provider values: `claude`/`anthropic`/`claude-code` and
  `copilot`/`github-copilot`/`gh-copilot`/`rustyclawd`. Unknown values fall
  through to file detection.
- `completion()` now refuses to silently fall back across providers when an env
  override is present. If the user pinned `copilot` but the SDK is unavailable,
  it logs a warning and returns `""` rather than masking the misconfiguration.
- `_query_copilot` rewritten against the real `copilot 0.1.0` API:

```python
async with CopilotClient() as client:
    session = await client.create_session(
        on_permission_request=PermissionHandler.approve_all,
        working_directory=str(project_root),
    )
    event = await session.send_and_wait(prompt, timeout=float(QUERY_TIMEOUT))
```

17 new tests in `tests/llm/test_provider_env_override.py` covering value
normalization, env priority, file-vs-env precedence, and the no-silent-fallback
contract.

**Rule**: Always check explicit env overrides (`AMPLIHACK_LLM_PROVIDER`,
`SIMARD_LLM_PROVIDER`) before falling back to file-based detection. Never
silently route to a different provider than the one the caller pinned — log a
warning and return empty instead.

---

### feat(code-visualizer): Multi-Language Support — Python, TypeScript, Rust, Go (PR #4480)

**Previously**: The `code-visualizer` skill analyzed only Python files,
producing mermaid import/dependency diagrams via an `ast`-based parser.

**New architecture**: Language-agnostic dispatcher + per-language analyzers.

| Module | Role |
|---|---|
| `scripts/graph.py` | Shared `Node`/`Edge`/`Graph` dataclasses (data contract) |
| `scripts/python_analyzer.py` | AST-based Python import extraction |
| `scripts/ts_analyzer.py` | Bounded-regex TS/JS (`.ts`, `.tsx`, `.js`, `.jsx`, `.mjs`, `.cjs`) |
| `scripts/rust_analyzer.py` | `use`/`mod` extraction |
| `scripts/go_analyzer.py` | Single and grouped `import (...)` with alias support |
| `scripts/dispatcher.py` | Walks target dir, groups by extension, lazy-loads analyzers |
| `scripts/mermaid_renderer.py` | Language-blind renderer; one `subgraph` per language |
| `scripts/staleness.py` | Compares max source mtime vs. diagram mtime |
| `scripts/visualizer.py` | CLI entry point |

**Dispatcher behavior**:

- Skips `IGNORE_DIRS`: `.git`, `node_modules`, `__pycache__`, `dist`, `build`,
  `target`, etc.
- Never follows symlinks.
- Lazy-loads analyzers via `importlib` — only the detected languages are loaded.

**CLI**:

```bash
# Generate per-language diagrams
code-visualizer <path> [--output DIR] [--basename NAME]

# Generate a combined view (one subgraph per language)
code-visualizer <path> --combined

# Check if diagrams are stale
code-visualizer <path> --check-staleness
```

**Tests**: 36 new tests under
`amplifier-bundle/skills/code-visualizer/tests/`:

- Per-analyzer correctness including malformed-input resilience
- Dispatcher routing + `IGNORE_DIRS` enforcement + nonexistent-path rejection
- Renderer: empty graph, edges, id sanitization, combined-view subgraphs
- Staleness: missing diagram, fresh, stale, language-scoped
- CLI: per-language output files, `--combined`, basename validation
- Smoke test: runs dispatcher against the repo root

**Adding a new language**: Drop `<lang>_analyzer.py` exposing
`normalize(paths) -> Graph` into `scripts/`, register its module name and
extension set in `dispatcher.LANGUAGES`. No inheritance required.

---

## Summary Table

| PR | Area | Type | Rule |
|---|---|---|---|
| #4471 | eval | fix | Don't wrap sync methods with `asyncio.run`; verify methods return coroutines |
| #4472 | eval | fix | Sync callers need `asyncio.run` to await async results |
| #4477 | llm | fix | Check env overrides before file-based provider detection; no silent fallback |
| #4480 | code-visualizer | feat | Add language by dropping `_analyzer.py` + registering in `dispatcher.LANGUAGES` |
