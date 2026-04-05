# Bug Hunt Guide

Consolidated three-pass bug hunt checklist for the code-atlas skill.

## Pass 1: Comprehensive Build + Hunt

> "Build the atlas from verified code paths, then systematically hunt contradictions between layers."

### Checklist

- [ ] **Route/DTO Mismatch** (api-contracts x data-flow): For every route handler, verify all
      accessed request fields exist in the declared DTO. Flag fields accessed but not declared.
- [ ] **Orphaned Environment Variables** (runtime-topology x inventory): Compare env vars
      used in code (`process.env.*`, `os.getenv()`, `viper.Get()`) against `.env.example` or
      documented vars. Report used-but-undeclared and declared-but-unused.
- [ ] **Dead Runtime Paths** (runtime-topology x api-contracts): Services in topology with
      no routes. Routes referencing services not in topology.
- [ ] **Stale Documentation** (all layers x docs/): Docs referencing routes, services, or
      env vars that no longer exist in code.
- [ ] **Layer 7 Structural Issues** (service-components): Services in topology with no
      discoverable internal packages. Internal packages imported by 3+ siblings (high coupling).
- [ ] **Layer 8 Dead Code** (ast-lsp-bindings): Exported symbols never referenced.
      Symbols on api-contracts routes listed in dead-code report.

### Pass 1 Output Format

One file per bug: `docs/atlas/bug-reports/{YYYY-MM-DD}-pass1-{slug}.md`

```markdown
## Bug: {Title}

**Layer**: {slug} x {slug}
**Severity**: Critical | High | Medium | Low
**Pass**: 1
**Evidence**:

- {description of evidence with relative file:line references}
- code_quote: `{relevant code snippet}`

**Impact**: {What breaks and when}
**Fix**: {Recommended action}
```

Every bug requires at least one `code_quote` with a relative file path. No speculation.

---

## Pass 2: Fresh-Eyes Cross-Check

> "Re-examine the atlas from scratch in a new context window. Validate, overturn, or strengthen Pass 1 findings."

### Checklist

- [ ] **Fresh atlas read**: Reviewer receives all layer output files without Pass 1 bug reports.
      Independently identifies contradictions.
- [ ] **Cross-check each Pass 1 finding**: For each, assign verdict:
  - `CONFIRMED` -- independently found the same issue; severity upgraded
  - `OVERTURNED` -- evidence does not support the finding; closed with explanation
  - `NEEDS_ATTENTION` -- ambiguous; requires human review
- [ ] **New findings**: Any contradiction found in Pass 2 but missed in Pass 1 is filed as
      a new Pass 2 bug.

### Pass 2 Output Format

One file per cross-check: `docs/atlas/bug-reports/{YYYY-MM-DD}-pass2-{slug}.md`

```markdown
## Pass 2 Cross-Check: {pass1-bug-slug}

**Pass 1 verdict:** {severity} -- {title}
**Pass 2 verdict:** CONFIRMED | OVERTURNED | NEEDS_ATTENTION

**Rationale:** {One paragraph explaining Pass 2's independent finding.}
```

---

## Pass 3: Scenario Deep-Dive

> "Trace each user-journeys journey end-to-end. Produce a PASS/FAIL/NEEDS_ATTENTION verdict for every journey."

### Checklist

For each journey in `docs/atlas/user-journeys/*.mmd`:

- [ ] Trace every step through api-contracts, data-flow, runtime-topology, service-components,
      and ast-lsp-bindings
- [ ] For each step, verify:

| Check               | Source Layer       | Question                                                              |
| ------------------- | ------------------ | --------------------------------------------------------------------- |
| Route exists        | api-contracts      | Does the endpoint appear in the route inventory?                      |
| DTO complete        | data-flow          | Are all request fields declared? Any response fields never populated? |
| Topology matches    | runtime-topology   | Does the inter-service call appear in the topology?                   |
| Component reachable | service-components | Are handler and service components in the per-service diagram?        |
| No dead code        | ast-lsp-bindings   | Are any symbols on this path in the dead-code report?                 |

### Pass 3 Output Format

One file per journey: `docs/atlas/bug-reports/{YYYY-MM-DD}-pass3-{journey-slug}.md`

```markdown
## Journey: {journey-slug}

### Verdict: PASS | FAIL | NEEDS_ATTENTION

| Criterion                     | Status    | Evidence                           |
| ----------------------------- | --------- | ---------------------------------- |
| api-contracts routes match    | pass/fail | {evidence with relative file:line} |
| data-flow complete            | pass/fail | {evidence}                         |
| service-components reachable  | pass/fail | {evidence}                         |
| No dead code on critical path | pass/warn | {evidence}                         |

**Verdict Rationale:** {One paragraph explaining the verdict with specific file:line references.}
```

### Verdict Semantics

| Verdict           | Condition                                                    |
| ----------------- | ------------------------------------------------------------ |
| `PASS`            | All criteria pass                                            |
| `FAIL`            | At least one criterion fails (critical or major bug on path) |
| `NEEDS_ATTENTION` | At least one criterion is a warning and none fail            |

---

## Multi-Agent Validation

After all three passes, verdict adjudication happens during the multi-agent validation stage
(not in this guide). The bug-hunt guide covers detection only. Final triage and filing
decisions are made by the reviewer agent during validation.

## Evidence Rules

1. All `file:line` references must be relative paths (SEC-16)
2. Every filed bug must include at least one `code_quote`
3. No bugs filed without code evidence -- no speculation
4. Bug report `code_quote` fields are redacted of credential patterns (SEC-15)
