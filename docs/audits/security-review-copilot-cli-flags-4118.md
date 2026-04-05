# Security Review: Copilot CLI Flags Fix (#4118/#4168)

**Date**: 2026-04-04
**Reviewer**: Security Agent (automated)
**Scope**: Commits `3dc141ccb`, `0d7507c64`, `da0c81b78` on branch `issue-4205-clean`
**Verdict**: APPROVED

## Changes Reviewed

1. **smart-orchestrator.yaml** — classify-and-decompose step conditionally selects CLI flags based on `$AGENT_BIN`
2. **claude_process.py** — `_build_command()` selects permission flags based on delegate type
3. **auto_mode.py** — `_run_sdk_subprocess()` routes flags per agent binary; adds session limit env overrides, subprocess timeouts, and logging improvements

## Security Checklist

| Area                             | Status | Notes                                                                                 |
| -------------------------------- | ------ | ------------------------------------------------------------------------------------- |
| Input validation                 | PASS   | Env vars validated via `_get_positive_int_env`; unknown binaries raise `RuntimeError` |
| Output encoding                  | PASS   | No user content reflected unsanitized                                                 |
| Authentication/authorization     | N/A    | No auth changes                                                                       |
| Sensitive data handling          | PASS   | `env -u CLAUDECODE` strips session tokens before subprocess invocation                |
| No hardcoded secrets             | PASS   | Clean                                                                                 |
| Error messages (no info leakage) | PASS   | Errors emit binary name and exit code only; no stack traces or credentials            |

## Findings

### FINDING 1 — MEDIUM: Copilot branch loses tool restriction enforcement

**Location**: `smart-orchestrator.yaml` lines 140-144

Claude branch uses `--disallowed-tools` (runtime-enforced tool blocklist). Copilot branch uses `--allow-all-tools` with a prompt-injected constraint:

```
SYSTEM CONSTRAINT: You are a task classifier. Output ONLY JSON. Do NOT invoke dev-orchestrator or any workflow. Do NOT use any tools.
```

This is a **soft constraint** — the model _can_ still invoke tools. Claude's `--disallowed-tools` is runtime-enforced (tools are literally unavailable).

**Risk**: LOW. The classify step is a single-turn `-p` invocation. Even if the model ignores the constraint, the subprocess exits after one turn. No persistent damage vector.

**Mitigation**: Copilot CLI does not support `--disallowed-tools`. This is the best available approach. Documented in commit message.

**Verdict**: Accepted tradeoff. No remediation needed.

### FINDING 2 — LOW: `$AGENT_BIN` glob matching breadth

**Location**: `smart-orchestrator.yaml` line 141

```bash
case "$AGENT_BIN" in
  *copilot*|*codex*)
```

Any binary path containing "copilot" or "codex" matches. An attacker who controls `AMPLIHACK_AGENT_BINARY` already has shell access, making this non-exploitable.

**Verdict**: Accepted.

### FINDING 3 — LOW: Session limit overrides via environment

**Location**: `auto_mode.py` lines 216-225

`_get_positive_int_env()` allows users to raise `max_total_api_calls` and `max_session_duration` via env vars. The validation correctly rejects non-positive and non-integer values with warnings, falling back to safe defaults.

**Verdict**: Clean. Good defensive coding.

### FINDING 4 — POSITIVE: Unknown agent binary fails loudly

**Location**: `auto_mode.py` lines 403-407

Unknown agent binaries raise `RuntimeError` immediately rather than silently degrading with wrong flags. This follows the fail-secure principle.

### FINDING 5 — POSITIVE: Branch name validation

**Location**: `default-workflow.yaml` (commit `da0c81b78`)

Branch names are validated against `[^a-zA-Z0-9/_.-]` pattern before use in CLI commands, preventing argument injection via exotic branch names.

## Test Coverage

- 21 tests in `test_classify_decompose_copilot_flags.py` — validate YAML case-statement flag isolation
- 8 tests in `test_auto_mode_copilot_flags.py` — validate Python subprocess flag routing, timeouts, unknown-binary rejection
- All 29 tests passing

## Conclusion

No blocking security issues. The implementation follows defense-in-depth principles: runtime-enforced restrictions where available (Claude), prompt-level constraints as fallback (Copilot), and fail-loud behavior for unknown binaries. The tradeoffs are documented and the risk surface is minimal.
