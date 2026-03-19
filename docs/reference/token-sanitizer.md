# Token Sanitizer Reference

The token sanitizer (`amplihack.proxy.token_sanitizer`) replaces API keys and secrets in request and response bodies before they are logged, stored in memory, or forwarded to external services.

## Contents

- [What Gets Sanitized](#what-gets-sanitized)
- [Pattern Ordering](#pattern-ordering)
- [Usage](#usage)
- [API](#api)
- [Adding Custom Patterns](#adding-custom-patterns)
- [Redacted Tokens](#redacted-tokens)

---

## What Gets Sanitized

The sanitizer detects and replaces the following token types:

| Token Type            | Pattern                     | Redacted Form                      |
| --------------------- | --------------------------- | ---------------------------------- |
| OpenAI project key    | `sk-proj-…`                 | `sk-proj-***`                      |
| OpenAI standard key   | `sk-…`                      | `sk-***`                           |
| Azure subscription ID | UUID format in Azure paths  | `[REDACTED:azure-subscription-id]` |
| GitHub PAT            | `ghp_…` or `github_pat_…`   | `ghp_***` / `github_pat_***`       |
| Generic bearer token  | `Bearer <token>` in headers | `[REDACTED:bearer-token]`          |

---

## Pattern Ordering

**Patterns are matched in order from most specific to least specific.** This is critical for correct redaction.

The `sk-proj-` pattern is placed **before** the `sk-` pattern. Without this ordering, every project key would be mis-redacted as a generic OpenAI key:

```
Input:    sk-proj-abc123…
Correct:  sk-proj-***   (sk-proj- matches first)
Incorrect: sk-***        (if sk- matched first)
```

The redacted form matters: downstream systems use the prefix to decide which key management vault was the source and to alert on unexpected key types appearing in logs.

---

## Usage

```python
from amplihack.proxy.token_sanitizer import sanitize

raw_body = '{"api_key": "sk-proj-xxxxxxxxxxxxxxxxxxxxxxxx"}'
clean_body = sanitize(raw_body)
print(clean_body)
# {"api_key": "sk-proj-***"}
```

The function is idempotent — the replacement strings (e.g. `sk-***`) contain only three asterisks after the prefix, which is shorter than the `{6,}` minimum required by any pattern. A second call produces the same output.

```python
# Idempotent: safe to call twice
twice = sanitize(sanitize(raw_body))
assert twice == sanitize(raw_body)
```

---

## API

### `sanitize(text: str) -> str`

Scans `text` for known secret patterns and replaces each match with its redacted form. Returns the sanitized string.

**Parameters**

| Name   | Type  | Description                                            |
| ------ | ----- | ------------------------------------------------------ |
| `text` | `str` | Input text, typically a JSON request or response body. |

**Returns** `str` — A copy of `text` with all recognised secrets replaced using the `***` format (e.g. `sk-***`, `sk-proj-***`).

**Raises** Nothing. Errors in regex compilation surface at import time, not at call time.

---

### `sanitize_dict(data: dict | None) -> dict`

Recursively sanitizes a dictionary. Returns a new dict with secrets replaced.

- Keys in `FULLY_REDACT_KEYS` (includes `Authorization`, `X-Api-Key`) have their **entire value** replaced with `[REDACTED:bearer-token]`.
- All other string values are passed through `sanitize()`.
- Nested dicts and lists are processed recursively.
- `None` input returns an empty dict.

```python
from amplihack.proxy.token_sanitizer import sanitize_dict

raw = {"Authorization": "Bearer sk-ant-abc123", "Content-Type": "application/json"}
clean = sanitize_dict(raw)
# {"Authorization": "[REDACTED:bearer-token]", "Content-Type": "application/json"}
```

---

## Adding Custom Patterns

Patterns are defined as a list of `(raw_string_regex, replacement)` tuples in `token_sanitizer.py`. Insert more-specific patterns **before** less-specific ones:

```python
# In token_sanitizer.py — maintain specificity order
PATTERNS = [
    (r"sk-proj-[a-zA-Z0-9_-]{6,}", "sk-proj-***"),  # More specific
    (r"sk-[a-zA-Z0-9_-]{6,}",       "sk-***"),       # Less specific — MUST follow
    # Add project-specific patterns here, most specific first
]
```

---

## Redacted Tokens

Redacted values appear in:

- The amplihack proxy access log (`~/.amplihack/.claude/runtime/logs/proxy.log`)
- Memory records created from sanitized request content
- Trace logs when `AMPLIHACK_LOG_LEVEL=DEBUG`

Each redacted form preserves the token prefix for routing context (e.g. `sk-proj-***` vs `sk-***`) while ensuring the secret value never appears in any log or stored record.

---

## See Also

- [Proxy Configuration Guide](../PROXY_CONFIG_GUIDE.md) — proxy setup and logging configuration
- [Security Recommendations](../SECURITY_RECOMMENDATIONS.md) — key rotation and vault practices
- [Trace Logging API](./trace-logging-api.md) — how sanitized data flows into trace logs
