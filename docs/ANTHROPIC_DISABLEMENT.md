# Anthropic Safe-Disablement Strategy

This page describes how to disable Anthropic paths in amplihack without silent failures.
When `ANTHROPIC_DISABLED=true` every component that depends on the Anthropic SDK either
raises a clear `ConfigurationError` immediately (for direct callers) or falls back to a
safe alternative and emits a `logger.warning` (for components that can degrade gracefully).

---

## Why this exists

Certain environments cannot or must not contact Anthropic's API — air-gapped deployments,
cost-control CI runs, compliance requirements that mandate only GitHub Copilot models, etc.
Without an explicit disablement mechanism the old code would:

- silently fall back if the key was absent, giving no indication that a feature was
  degraded
- crash deep inside the SDK with an `AuthenticationError` if a stale key was present
- leak the API key value in exception tracebacks

The safe-disablement strategy replaces that behaviour with clear, early, auditable failure.

---

## Quick start

```bash
# Disable Anthropic completely — all Anthropic paths fail with a clear error or log
export ANTHROPIC_DISABLED=true

# Run anything that would otherwise use Anthropic; it will use CopilotBackend instead
amplihack fleet run ...
```

---

## Configuration reference

### `ANTHROPIC_DISABLED`

| Attribute | Value |
|---|---|
| **Type** | Environment variable |
| **Values** | `true` / `1` (case-insensitive, leading/trailing whitespace ignored) |
| **Default** | unset (Anthropic enabled) |
| **Scope** | Process-wide; affects all amplihack components in the same process |

Setting this variable disables Anthropic at every level:

| Component | Behaviour when `ANTHROPIC_DISABLED=true` |
|---|---|
| `fleet/_backends.py` — `AnthropicBackend.__init__` | Raises `ConfigurationError` immediately |
| `fleet/_backends.py` — `auto_detect_backend()` | Falls back to `CopilotBackend`; logs a warning if `ANTHROPIC_API_KEY` is also set |
| `eval/gherkin_agent_evaluator.py` — `_has_anthropic_api_key()` | Returns `False`; consensus evaluation degrades gracefully using the non-Anthropic path |
| `agents/goal_seeking/hive_mind/query_expansion.py` | `HAS_ANTHROPIC` set to `False` at module load; `expand_query()` uses the local synonym fallback |
| `vendor/blarify` — `rotating_anthropic.py` | `RotatingKeyChatAnthropic.__init__` raises `RuntimeError` immediately |

!!! note "Normalisation"
    The flag is checked with `.strip().lower() == "true"`.  
    `ANTHROPIC_DISABLED=True`, `ANTHROPIC_DISABLED= TRUE `, and `ANTHROPIC_DISABLED=true`
    are all equivalent.

### `ANTHROPIC_API_KEY`

The standard Anthropic SDK key.  When `ANTHROPIC_DISABLED=true` the key is **ignored**
even if present; `auto_detect_backend()` will log a warning noting the conflict and
continue with `CopilotBackend`.

---

## Component details

### `fleet._backends` — LLM backend layer

```
src/amplihack/fleet/_backends.py
```

#### `ConfigurationError`

```python
class ConfigurationError(RuntimeError):
    """Raised when a backend is unavailable due to missing or disabled configuration."""
```

Raised by `AnthropicBackend.__init__` when:

- `ANTHROPIC_DISABLED=true`, or
- `ANTHROPIC_API_KEY` is absent

The error message always names the controlling environment variable so the operator knows
exactly what to fix.

`ConfigurationError` is listed in `__all__` and is part of the **public API** — callers
should import and catch it explicitly rather than catching the base `RuntimeError`.

#### `_SecretValue`

An internal wrapper class that prevents the Anthropic API key from appearing in
`repr()`, `str()`, or exception tracebacks.

```python
backend._api_key               # → <_SecretValue object> (wrapper, not a string)
repr(backend._api_key)         # → '**********'
str(backend._api_key)          # → '**********'
backend._api_key.get_secret_value()  # → '<actual key>'  (internal use only)
```

!!! note "Direct attribute access"
    `backend._api_key` returns the `_SecretValue` wrapper object, not the string
    `'**********'`.  The masking only applies when the object is coerced to a string
    via `repr()` or `str()` (e.g., in log output or tracebacks).

`_SecretValue` is **not** exported from `__all__` and is not part of the public API.

#### `AnthropicBackend`

```python
class AnthropicBackend:
    def __init__(
        self,
        model: str = "claude-opus-4-6",
        api_key: str = "",
        max_tokens: int = DEFAULT_LLM_MAX_TOKENS,
    ) -> None: ...

    def complete(self, system_prompt: str, user_prompt: str) -> str: ...
```

Raises `ConfigurationError` on `__init__` when disabled.  `complete()` is never
reached in the disabled state.

#### `auto_detect_backend()`

```python
def auto_detect_backend() -> LLMBackend: ...
```

Selection priority:

```
1. AnthropicBackend  — if ANTHROPIC_API_KEY is set AND ANTHROPIC_DISABLED is not true
2. CopilotBackend    — fallback (always available)
```

When `ANTHROPIC_DISABLED=true` and `ANTHROPIC_API_KEY` is set, the function logs:

```
WARNING amplihack.fleet._backends — ANTHROPIC_API_KEY is set but ANTHROPIC_DISABLED=true; falling back to CopilotBackend.
```

---

### `eval.gherkin_agent_evaluator` — Gherkin consensus evaluation

```
src/amplihack/eval/gherkin_agent_evaluator.py
```

`_has_anthropic_api_key()` is an internal predicate used by the consensus evaluation
path.  When `ANTHROPIC_DISABLED=true` it returns `False` regardless of whether
`ANTHROPIC_API_KEY` is set and logs:

```
WARNING amplihack.eval.gherkin_agent_evaluator — Anthropic API disabled (ANTHROPIC_DISABLED=true); consensus evaluation will use non-Anthropic path.
```

The evaluator continues without Anthropic; Gherkin scenarios are still evaluated,
but the consensus step uses whatever non-Anthropic evaluator is configured.

---

### `agents.goal_seeking.hive_mind.query_expansion` — Query expansion

```
src/amplihack/agents/goal_seeking/hive_mind/query_expansion.py
```

The module exports a `HAS_ANTHROPIC` boolean that is resolved at **import time**:

1. Try `import anthropic`.  If that fails, `HAS_ANTHROPIC = False` and a warning is logged.
2. If the import succeeds but `ANTHROPIC_DISABLED=true`, `HAS_ANTHROPIC` is forced to
   `False` and a second warning is logged.

```python
from amplihack.agents.goal_seeking.hive_mind.query_expansion import HAS_ANTHROPIC
# False when SDK is absent or ANTHROPIC_DISABLED=true
```

`expand_query()` falls back to a local synonym map when `HAS_ANTHROPIC` is `False`.
The fallback returns `[query]` (a single-item list) when no synonyms are known for the
input term — callers expecting a richer expansion will receive a narrower result set.

---

### `vendor.blarify` — Optional Anthropic vendor path

```
src/amplihack/vendor/blarify/agents/llm_provider.py
src/amplihack/vendor/blarify/agents/rotating_provider/rotating_anthropic.py
```

Both files guard their `langchain-anthropic` / `anthropic` imports with
`try/except ImportError`.  The module loads cleanly even when the SDK is absent.

`RotatingKeyChatAnthropic.__init__` checks `ANTHROPIC_DISABLED` at instantiation
time and raises `RuntimeError` if the flag is set — **before** attempting to use
the SDK.  If `ANTHROPIC_DISABLED` is not set but the SDK is absent, `ImportError`
is raised instead with a clear install hint.

`llm_provider.py` likewise guards both its `anthropic` and `langchain_anthropic`
imports so the broader blarify vendor layer does not crash on import.

---

## Usage examples

### Verify the flag is honoured

```python
import os
os.environ["ANTHROPIC_DISABLED"] = "true"

from amplihack.fleet._backends import AnthropicBackend, ConfigurationError

try:
    backend = AnthropicBackend()
except ConfigurationError as exc:
    print(exc)
# AnthropicBackend is disabled (ANTHROPIC_DISABLED=true).
# Unset ANTHROPIC_DISABLED or choose a different backend.
```

### Use `auto_detect_backend()` transparently

```python
import os
os.environ["ANTHROPIC_DISABLED"] = "true"

from amplihack.fleet._backends import auto_detect_backend, CopilotBackend

backend = auto_detect_backend()
assert isinstance(backend, CopilotBackend)   # Copilot used automatically
```

### Check `HAS_ANTHROPIC` before calling `expand_query`

```python
import os
os.environ["ANTHROPIC_DISABLED"] = "true"

# Must import AFTER setting the env var — HAS_ANTHROPIC is resolved at module load.
from amplihack.agents.goal_seeking.hive_mind.query_expansion import (
    HAS_ANTHROPIC,
    expand_query,
)

assert HAS_ANTHROPIC is False

# Falls back to local synonym map; returns [query] if no synonyms known
results = expand_query("agent")
print(results)  # e.g. ['agent', 'worker', 'actor', ...]
```

### Running in CI without Anthropic

```yaml
# .github/workflows/ci.yml  (excerpt)
env:
  ANTHROPIC_DISABLED: "true"   # never contact Anthropic in CI
  # ANTHROPIC_API_KEY intentionally absent

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pytest tests/ -q
```

---

## Logging reference

All disabled-path log records use `logging.WARNING` level and follow the pattern:

```
<logger-name> — <human-readable reason> (<FLAG>=<value>); <fallback description>.
```

| Logger | Message (truncated) |
|---|---|
| `amplihack.fleet._backends` | `AnthropicBackend is disabled (ANTHROPIC_DISABLED=true)…` |
| `amplihack.fleet._backends` | `ANTHROPIC_API_KEY is set but ANTHROPIC_DISABLED=true; falling back to CopilotBackend.` |
| `amplihack.eval.gherkin_agent_evaluator` | `Anthropic API disabled (ANTHROPIC_DISABLED=true); consensus evaluation will use non-Anthropic path.` |
| `amplihack.agents.goal_seeking.hive_mind.query_expansion` | `Anthropic is disabled (ANTHROPIC_DISABLED=true); query_expansion will use local synonym fallback.` |
| `amplihack.agents.goal_seeking.hive_mind.query_expansion` | `anthropic SDK not available; query_expansion will use local synonym fallback. Install with: pip install anthropic` |
| `amplihack.vendor.blarify.agents.rotating_provider.rotating_anthropic` | `langchain-anthropic is not installed; RotatingKeyChatAnthropic will raise ImportError when instantiated.` |
| `amplihack.vendor.blarify.agents.llm_provider` | `langchain-anthropic is not installed; Anthropic models will be unavailable in LLMProvider.` |

---

## Security considerations

| Concern | Mitigation |
|---|---|
| API key in tracebacks | `_SecretValue` wrapper makes `repr(key)` → `**********` |
| Key in log output | No component logs the key value; only the flag name appears in messages |
| Disable flag bypassed | Flag is checked with `.strip().lower()` so whitespace/casing variants cannot bypass it |
| Flag state exposure | `ANTHROPIC_DISABLED` is internal Python state; no HTTP or CLI surface exposes it |

---

## Troubleshooting

**`ConfigurationError: AnthropicBackend is disabled`**  
You instantiated `AnthropicBackend()` directly while `ANTHROPIC_DISABLED=true`.
Either unset the flag or use `auto_detect_backend()` which selects `CopilotBackend`
automatically.

**`query_expansion` returns fewer synonyms than expected**  
`HAS_ANTHROPIC` is `False` (SDK absent or flag set).  Check `ANTHROPIC_DISABLED` and
whether `anthropic` is installed (`pip install anthropic`).  Note: `HAS_ANTHROPIC` is
resolved at import time — set the env var *before* importing the module.

**`ANTHROPIC_DISABLED=true` set after import has no effect on `HAS_ANTHROPIC`**  
`HAS_ANTHROPIC` is a module-level constant fixed at import time.  Setting
`os.environ["ANTHROPIC_DISABLED"] = "true"` after `query_expansion` has already been
imported will **not** change `HAS_ANTHROPIC`.  Always set the flag in the process
environment before any amplihack imports.

**`ANTHROPIC_DISABLED=true` but Anthropic is still being called**  
The module was imported before the env var was set.  Ensure the variable is set in the
process environment before any amplihack imports occur (e.g., at the top of your entry
point or in the shell before starting Python).

**Blarify vendor raises `RuntimeError` when `ANTHROPIC_DISABLED=true`**  
This is by design.  `RotatingKeyChatAnthropic.__init__` checks `ANTHROPIC_DISABLED`
before attempting to use the SDK.  Unset the flag or switch to a non-Anthropic provider
in the blarify path.

**Blarify vendor raises `ImportError` at runtime, not at import**  
`rotating_anthropic.py` loads cleanly (the `langchain-anthropic` import is wrapped in
`try/except`) but raises `ImportError` at instantiation if the SDK is absent.
Install the package (`pip install langchain-anthropic`) or avoid the blarify Anthropic
provider path.
