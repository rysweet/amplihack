# Supply Chain Audit

Audits software supply chain security across 12 dimensions: GitHub Actions SHA
pinning, workflow permissions, secrets scanning, cache poisoning, container
image digests, OIDC credentials, and ecosystem lock files.

## Quick Start

```
"supply chain audit"
→ Full audit at repo root, all detected ecosystems

"check action pinning"
→ GitHub Actions dimensions only (1-4)

"audit dependencies in ./services/api"
→ Scoped to a subdirectory

"CI security audit --scope gha,containers"
→ Dimensions 1-5, 12 only
```

## What It Audits

| Scope         | Ecosystems     | Dimensions                                           |
| ------------- | -------------- | ---------------------------------------------------- |
| `gha`         | GitHub Actions | 1: SHA pinning, 2: permissions, 3: secrets, 4: cache |
| `containers`  | Docker         | 5: image digests, 12: build chain                    |
| `credentials` | CI secrets     | 6: OIDC migration                                    |
| `dotnet`      | NuGet          | 7: lock files, source mapping                        |
| `python`      | pip/PyPI       | 8: hash pinning, typosquatting                       |
| `rust`        | Cargo          | 9: Cargo.lock, build.rs, [patch]                     |
| `node`        | npm/yarn       | 10: npm ci, npx, postinstall                         |
| `go`          | Go modules     | 11: go.sum, GONOSUMCHECK, replace                    |

## Output

Produces a structured markdown report with:

- Severity summary (Critical / High / Medium / Info)
- Findings with file:line references and ready-to-use fix templates
- SLSA readiness assessment
- Handoffs to dependency-resolver and pre-commit-manager

Example finding:

    CRITICAL-001 · Dim 1 · Unpinned third-party action
    File: .github/workflows/release.yml:14
    Current: uses: actions/checkout@v4
    Expected: uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2
    Fix: https://github.com/actions/checkout/releases
    Why: Mutable semver tag allows silent code replacement without any file
         change in your repo — a direct supply-chain compromise vector.

## Configuration

### Accepted Risks

Create .supply-chain-accepted-risks.yml to suppress findings that are
intentionally accepted:

    - id: HIGH-002
      file: .github/workflows/ci.yml
      line: 47
      dimension: 1
      rationale: "Pinning blocked by upstream; tracked in GH-4521"
      review_date: "2026-06-01"

Constraints: 64KB file cap; no wildcards; Critical findings cannot be
suppressed; past review_date restores original severity.

## Integration Points

| Skill                    | Trigger                                       |
| ------------------------ | --------------------------------------------- |
| dependency-resolver      | Missing or drifted lock files (Dims 7-11)     |
| pre-commit-manager       | Always — installs SHA-pinning and audit hooks |
| silent-degradation-audit | CI security steps that suppress failures      |
| cybersecurity-analyst    | Runtime exposure beyond supply chain scope    |

## Documentation

| File                        | Contents                                           |
| --------------------------- | -------------------------------------------------- |
| SKILL.md                    | Workflow, scope flags, accepted-risks protocol     |
| reference/contracts.md      | Finding schema, report schema, handoff templates   |
| reference/actions.md        | Dims 1-4: GHA pinning, permissions, secrets, cache |
| reference/containers.md     | Dims 5, 12: Image digests, build chain             |
| reference/credentials.md    | Dim 6: OIDC migration                              |
| reference/dotnet.md         | Dim 7: NuGet lock files                            |
| reference/python.md         | Dim 8: pip hash pinning                            |
| reference/rust.md           | Dim 9: Cargo supply chain                          |
| reference/node.md           | Dim 10: npm/yarn integrity                         |
| reference/go.md             | Dim 11: Go module integrity                        |
| reference/sbom-slsa.md      | SBOM generation, SLSA compliance, cosign           |
| reference/eval-scenarios.md | Evaluation scenarios and pass/fail criteria        |
