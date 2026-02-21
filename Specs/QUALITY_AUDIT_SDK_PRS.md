# Quality Audit: SDK PRs

**Date**: 2026-02-20
**Auditor**: Automated Quality Audit
**Branch**: feat/quality-audit-sdk-prs
**PRs Audited**: #2426, #2427, #2428, #2431, #2432, #2433

## Audit Checklist Summary

| Check                          | #2426 | #2427 | #2428 | #2431 | #2432 | #2433  |
| ------------------------------ | ----- | ----- | ----- | ----- | ----- | ------ |
| No eval()/exec() calls         | PASS  | PASS  | PASS  | PASS  | PASS  | PASS\* |
| No hardcoded secrets/API keys  | PASS  | PASS  | PASS  | PASS  | PASS  | PASS   |
| Subprocess calls have timeouts | N/A   | PASS  | N/A   | N/A   | N/A   | N/A    |
| Generic error messages         | FAIL  | FAIL  | FAIL  | N/A   | FAIL  | FAIL   |
| Input validation               | FAIL  | FAIL  | FAIL  | N/A   | PASS  | PASS   |
| No bare except: clauses        | PASS  | PASS  | PASS  | N/A   | PASS  | PASS   |
| No swallowed exceptions        | FAIL  | FAIL  | FAIL  | N/A   | PASS  | PASS   |
| Prompts in template files      | MIXED | MIXED | MIXED | PASS  | PASS  | MIXED  |
| Configurable model names       | FAIL  | PASS  | PASS  | N/A   | PASS  | FAIL   |
| No print() in production       | PASS  | PASS  | PASS  | PASS  | FAIL  | PASS   |

\* PR #2433 has eval() in test data for the code_review eval scenario (intentional -- it is the
code being analyzed by the security scanner, not production code executing eval).

---

## PR #2426 - Claude SDK (branch: feat/pr-b-claude-sdk)

### Files Audited

- `src/amplihack/agents/goal_seeking/sdk_adapters/base.py`
- `src/amplihack/agents/goal_seeking/sdk_adapters/claude_sdk.py`
- `src/amplihack/agents/goal_seeking/sdk_adapters/factory.py`
- `src/amplihack/agents/goal_seeking/sdk_adapters/__init__.py`
- `tests/agents/goal_seeking/test_claude_sdk_adapter.py`

### Findings

1. **Error message leaks internal state** (claude_sdk.py:150-153)
   - `response=f"Agent execution failed: {e}"` exposes raw exception to user
   - `metadata={"error": str(e)}` leaks full stack trace info

2. **No input validation on agent name** (base.py:140)
   - Empty string or None could pass through without error

3. **No input validation on run() task** (base.py:399-417)
   - Empty task string not rejected

4. **Swallowed exceptions in tool implementations** (base.py)
   - `_tool_search`: `except Exception: return []` -- no logging
   - `_tool_explain`: `except Exception: return "No knowledge..."` -- no logging
   - `_tool_find_gaps`: `except Exception: return {"gaps": [...]}` -- no logging
   - `_tool_verify`: `except Exception: return {"verified": False}` -- no logging

5. **Missing error handling in close()** (base.py:419-422)
   - No try/except around memory.close()

6. **No confidence bounds checking** (base.py:325)
   - `_tool_store` accepts any float for confidence, no clamping to [0, 1]

7. **Model name not configurable via env var** (claude_sdk.py:54)
   - Hardcoded default "claude-sonnet-4-5-20250929" with no env var fallback

8. **Factory SDKType() can throw uncaught ValueError** (factory.py:52)
   - `SDKType(sdk.lower())` throws ValueError for unknown strings before reaching
     the final `raise ValueError` at line 104

### Fixes Applied

- Added input validation for empty agent name in `base.py`
- Added input validation for empty task in `run()`
- Added `logger.exception()` calls to all swallowed except blocks in tool implementations
- Added input validation for empty content in `_tool_learn()`
- Added confidence clamping in `_tool_store()` to [0.0, 1.0]
- Changed error messages to generic "Agent execution encountered an error."
- Changed metadata to use `type(e).__name__` instead of `str(e)`
- Added try/except to `close()` method
- Added `CLAUDE_AGENT_MODEL` env var support in claude_sdk.py
- Added try/except around `SDKType()` in factory.py with descriptive error message
- Added empty name validation in factory.py `create_agent()`

---

## PR #2427 - Copilot SDK (branch: feat/pr-c-copilot-sdk)

### Files Audited

- `src/amplihack/agents/goal_seeking/sdk_adapters/copilot_sdk.py`
- `src/amplihack/agents/goal_seeking/cognitive_adapter.py`
- `src/amplihack/agents/goal_seeking/flat_retriever_adapter.py`
- `src/amplihack/agents/goal_seeking/hierarchical_memory.py`
- `src/amplihack/agents/goal_seeking/json_utils.py`
- `src/amplihack/agents/goal_seeking/similarity.py`
- `tests/agents/goal_seeking/test_copilot_sdk_adapter.py`

### Findings

1. **Swallowed exception in event tracking** (copilot_sdk.py:247-248)
   - `except Exception: pass` in `_track_tools()` -- best-effort but should log at debug level

2. **Error message leaks in ToolResult** (copilot_sdk.py:82)
   - `error=str(exc)` exposes raw exception to LLM context

3. **Swallowed exceptions in hierarchical_memory.py** (lines 964, 1059, 1073)
   - Three `except Exception: pass` or `except Exception: stats[...] = 0` without logging
   - These handle optional DB tables but should log at debug level

4. **Model name configurable via env var** -- PASS
   - `os.environ.get("COPILOT_MODEL", "gpt-4.1")` already in place

5. **Timeout configurable via env var** -- PASS
   - `os.environ.get("COPILOT_AGENT_TIMEOUT", "300")` with max 600s

### Fixes Applied

- Changed `except Exception: pass` to `logger.debug(...)` in event tracking
- Changed `error=str(exc)` to `error=type(exc).__name__` in ToolResult
- Changed `logger.warning` to `logger.exception` for full stack trace capture
- Added debug logging to three swallowed exceptions in hierarchical_memory.py

---

## PR #2428 - Microsoft SDK (branch: feat/pr-d-microsoft-sdk)

### Files Audited

- `src/amplihack/agents/goal_seeking/sdk_adapters/microsoft_sdk.py`
- `tests/agents/goal_seeking/test_microsoft_sdk_adapter.py`

### Findings

1. **Error message leaks internal state** (microsoft_sdk.py:304-310)
   - `response=f"Agent execution failed: {e}"` exposes raw exception
   - `metadata={"error": str(e)}` leaks full exception string

2. **Model name configurable via env var** -- PASS
   - `os.environ.get("MICROSOFT_AGENT_MODEL", "gpt-4o")` already in place

3. **No subprocess calls** -- N/A
4. **No eval()/exec() calls** -- PASS
5. **No hardcoded secrets** -- PASS

### Fixes Applied

- Changed error response to generic "Agent execution encountered an error."
- Changed metadata error to `type(e).__name__`
- Changed `logger.error` to `logger.exception` for full stack trace capture

---

## PR #2431 - Self-Improving Skill (branch: feat/pr-e-self-improving-skill)

### Files Audited

- `.claude/skills/self-improving-agent-builder/SKILL.md`

### Findings

This PR contains only a markdown SKILL.md file defining a Claude Code skill.
No Python source code to audit.

- **No code files**: Only markdown, no exception handling to review
- **No security concerns**: Skill definition is prompt-only

### Fixes Applied

None required -- no Python files in this PR.

---

## PR #2432 - Meta-eval Teaching (branch: feat/meta-eval-teaching-experiment)

### Files Audited

- `src/amplihack/eval/meta_eval_experiment.py`
- `src/amplihack/eval/metacognition_grader.py`
- `src/amplihack/eval/teaching_session.py`

### Findings

1. **print() statements in production code** (meta_eval_experiment.py:468-495)
   - 15 print() statements in `main()` CLI entry point
   - **Verdict**: ACCEPTABLE -- `main()` is a CLI entry point invoked via `__main__`,
     print() is the standard output mechanism for CLI tools

2. **Error message leaks in quiz results** (meta_eval_experiment.py:395)
   - `"student_answer": f"Error: {e}"` exposes raw exception in quiz output

3. **Model name configurable** -- PASS
   - Configurable via `ExperimentConfig.model` and CLI `--model` argument

4. **metacognition_grader.py** -- Clean
   - Pure rules-based grader, no LLM calls, no exception handling issues
   - All functions are stateless with proper input checks

5. **teaching_session.py** -- Clean
   - Proper `logger.warning()` in except blocks
   - Model configurable via `TeachingConfig`

### Fixes Applied

- Changed quiz error from `f"Error: {e}"` to generic message
  "Unable to generate answer due to an error."

---

## PR #2433 - Domain Agents (branch: feat/domain-specific-agents)

### Files Audited

- `src/amplihack/agents/domain_agents/base.py`
- `src/amplihack/agents/domain_agents/code_review/agent.py`
- `src/amplihack/agents/domain_agents/code_review/tools.py`
- `src/amplihack/agents/domain_agents/code_review/eval_levels.py`
- `src/amplihack/agents/domain_agents/meeting_synthesizer/agent.py`
- `src/amplihack/agents/domain_agents/meeting_synthesizer/tools.py`
- `src/amplihack/agents/domain_agents/meeting_synthesizer/eval_levels.py`
- `src/amplihack/agents/domain_agents/skill_injector.py`
- `src/amplihack/agents/goal_seeking/action_executor.py`
- `src/amplihack/eval/domain_eval_harness.py`
- `src/amplihack/eval/teaching_eval.py`

### Findings

1. **Model name not configurable via env var** (base.py:64)
   - Hardcoded "gpt-4o-mini" default with no env var fallback

2. **Error message leaks in domain_eval_harness.py** (line 230)
   - `grading_details=f"Agent execution failed: {e!s}"` exposes raw exception

3. **Missing logging import in domain_eval_harness.py**
   - No logger configured; exception details lost when scenario fails

4. **eval() in eval scenario test data** (code_review/eval_levels.py:L3-003)
   - `"code": "def calculate(expr):\n    return eval(expr)\n"` -- this is intentional
     test input for the security scanner, not production code

5. **Input validation** -- PASS
   - `DomainAgent.__init__` validates empty agent_name and domain
   - `skill_injector.py` validates empty domain, skill_name, and non-callable tool_fn
   - `action_executor.py` validates empty name and non-callable func
   - All tool functions check for empty/None inputs

6. **No bare except: clauses** -- PASS
7. **No swallowed exceptions** -- PASS (action_executor properly returns ActionResult with error)
8. **teaching_eval.py** -- Clean (no exception handling issues)

### Fixes Applied

- Added `DOMAIN_AGENT_MODEL` env var support in base.py
- Added `import os` to base.py
- Changed error message in domain_eval_harness.py to use `type(e).__name__`
- Added `import logging` and logger to domain_eval_harness.py
- Added `logger.exception()` call for failed scenario execution

---

## Cross-Cutting Observations

### Positive Patterns (Consistent Across PRs)

- No bare `except:` clauses found in any production code
- No hardcoded secrets or API keys
- No use of `eval()` or `exec()` in production paths
- Good use of specific exception types (`json.JSONDecodeError`, `ImportError`, `ValueError`)
- Consistent use of `from __future__ import annotations` for Python 3.10 compat
- Clean separation of concerns (tools, agents, eval, adapters)

### Recurring Issues Fixed

1. **Error message leaking** (5 files): Raw exception strings exposed via `f"...{e}"`
   - Fixed in: claude_sdk.py, copilot_sdk.py, microsoft_sdk.py, domain_eval_harness.py, meta_eval_experiment.py
2. **Swallowed exceptions** (2 files): `except Exception: pass` without logging
   - Fixed in: copilot_sdk.py (event tracking), hierarchical_memory.py (3 locations)
3. **Missing input validation** (2 files): No checks for empty agent name/task
   - Fixed in: base.py (name validation, task validation, content validation)
4. **Model configurability** (2 files): No env var fallback for model names
   - Fixed in: claude_sdk.py (CLAUDE_AGENT_MODEL), domain_agents/base.py (DOMAIN_AGENT_MODEL)
5. **Missing logger.exception()**: Several except blocks used logger.error instead
   - Fixed in: claude_sdk.py, microsoft_sdk.py, copilot_sdk.py (upgrades to logger.exception)

### Files Modified in This Audit

1. `src/amplihack/agents/goal_seeking/sdk_adapters/base.py` (input validation, error handling, tool hardening)
2. `src/amplihack/agents/goal_seeking/sdk_adapters/claude_sdk.py` (generic errors, env var model)
3. `src/amplihack/agents/goal_seeking/sdk_adapters/copilot_sdk.py` (generic errors, debug logging)
4. `src/amplihack/agents/goal_seeking/sdk_adapters/microsoft_sdk.py` (generic errors)
5. `src/amplihack/agents/goal_seeking/sdk_adapters/factory.py` (input validation, ValueError handling)
6. `src/amplihack/agents/goal_seeking/hierarchical_memory.py` (debug logging for optional DB features)
7. `src/amplihack/agents/domain_agents/base.py` (env var model support)
8. `src/amplihack/eval/domain_eval_harness.py` (logging, generic errors)
9. `src/amplihack/eval/meta_eval_experiment.py` (generic quiz error)
