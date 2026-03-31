# External Service Integration Assessment: step-03-create-issue

**Date:** 2026-03-31
**Context:** Step 8b of default-workflow recipe — idempotency guards for step-03-create-issue
**File:** `amplifier-bundle/recipes/default-workflow.yaml` (lines 289-373)

## Summary

The idempotency guards added to step-03-create-issue interact with one external service: **GitHub API via `gh` CLI**. All external service integration concerns are already properly handled in the implementation. No additional API clients, service adapters, or retry layers are needed.

## External Service: GitHub API (via `gh` CLI)

### Integration Points

| Call                                     | Purpose                                   | Line    |
| ---------------------------------------- | ----------------------------------------- | ------- |
| `gh issue view "$REF_ISSUE_NUM"`         | Guard 1: Verify referenced issue exists   | 324     |
| `gh issue list --search "$SEARCH_QUERY"` | Guard 2: Search for duplicate open issues | 345     |
| `gh label list` / `gh label create`      | Ensure workflow label exists              | 361-364 |
| `gh issue create`                        | Fallback: create new issue                | 366-372 |

### Resilience Patterns Already Implemented

| Concern                    | Pattern             | Details                                                                       |
| -------------------------- | ------------------- | ----------------------------------------------------------------------------- |
| **Timeout**                | `timeout 60`        | Wraps every `gh` API call to prevent indefinite hangs                         |
| **Error handling**         | `\|\| echo ''`      | API failures produce empty string, allowing graceful fallthrough              |
| **Stderr isolation**       | `2>/dev/null`       | Suppresses gh noise (auth warnings, rate-limit messages)                      |
| **Graceful degradation**   | Guard fallthrough   | Both guards fall through to issue creation if API calls fail                  |
| **Input validation**       | Numeric regex check | Issue numbers validated as `^[0-9]+$` before interpolation (defense-in-depth) |
| **Retry on label failure** | `\|\| true`         | Label creation failure is non-fatal                                           |
| **Fallback creation**      | Two-attempt create  | First attempt with `--label`, second without if labeling fails                |

### Why No Additional Integration Code Is Needed

1. **`gh` CLI handles auth internally** — token management, OAuth refresh, and credential storage are delegated to the CLI tool
2. **`gh` CLI handles HTTP retries** — built-in retry logic for transient network errors
3. **Shell-based recipe steps don't benefit from client libraries** — adding a Python/TypeScript adapter would increase complexity without improving reliability
4. **Timeout + fallthrough pattern is sufficient** — matches the resilience model used by step-16-create-draft-pr

## Conclusion

**No action required.** All external service integration patterns (timeout, error handling, fallback, input validation) are already implemented inline in the bash step. This assessment confirms the implementation is complete and consistent with step-16's proven pattern.
