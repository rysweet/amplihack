---
name: supply-chain-audit
version: 1.0.0
description: |
  Auditing software supply chain security across CI/CD pipelines, container images, and
  language ecosystems. Detects mutable dependency references, insecure CI patterns,
  credential exposure risks, and missing SBOM/SLSA controls. Use when performing a
  supply chain audit, checking action pinning, auditing dependencies, scanning for
  CI security issues, reviewing container security, or assessing dependency security.
  Covers GitHub Actions, containers, Python, Node, Go, Rust, .NET, and more.
auto_activates:
  - "supply chain audit"
  - "audit dependencies"
  - "check action pinning"
  - "dependency security"
  - "CI security audit"
  - "pin GitHub Actions"
  - "check for mutable tags"
  - "SLSA compliance"
  - "SBOM generation"
  - "container image pinning"
priority_score: 72.0
---

# Supply Chain Audit Skill

Auditing software supply chain security across CI/CD pipelines, container images, and
language package ecosystems. Produces structured findings with severity ratings,
`file:line` references, and actionable fix templates.

## When to Use This Skill

- **CI/CD security review**: Unpin action refs, excessive permissions, secret leakage
- **Dependency pinning**: Lock files missing, hash verification absent, mutable semver refs
- **Container supply chain**: Mutable base image tags, non-root execution, SBOM generation
- **Credential hygiene**: OIDC migration from long-lived secrets, subject constraint gaps
- **Compliance mapping**: SLSA L1-L4 readiness assessment, SBOM generation guidance
- **Pre-merge gate**: Block PRs that introduce High/Critical supply chain regressions

---

## Prerequisites — External Tool Check

**Before running the audit**, check for missing external tools and offer to install them:

```python
from supply_chain_audit.external_tools import check_missing_tools, install_tool

missing = check_missing_tools()
if missing:
    # Show the user what's missing and what each tool does
    for tool in missing:
        print(f"Missing: {tool['name']} — {tool['description']}")
        for opt in tool['install_options']:
            print(f"  Install: {opt}")

    # Ask the user if they want to install
    # If yes, install each one:
    for tool in missing:
        success, msg = install_tool(tool['name'])
        print(f"  {tool['name']}: {msg}")
```

The audit runs without these tools (offline/degraded mode) but produces fewer findings:

| Tool     | What's lost without it                            |
| -------- | ------------------------------------------------- |
| `gh`     | Cannot resolve action tags to SHAs via GitHub API |
| `crane`  | Cannot resolve container image digests            |
| `syft`   | Cannot generate SBOMs (SPDX/CycloneDX)            |
| `grype`  | Cannot scan for known CVEs                        |
| `cosign` | Cannot verify image signatures or attestations    |

---

## Ecosystem Detection

Detect which dimensions apply before running checks:

| Signal                                               | Ecosystem      | Dimensions Triggered |
| ---------------------------------------------------- | -------------- | -------------------- |
| `.github/workflows/*.yml`                            | GitHub Actions | 1, 2, 3, 4           |
| `Dockerfile` / `docker-compose.yml`                  | Containers     | 5, 12                |
| `.github/workflows/` with `secrets.*`                | Credentials    | 6                    |
| `*.csproj` / `NuGet.Config`                          | .NET / NuGet   | 7                    |
| `requirements*.txt` / `pyproject.toml` / `setup.cfg` | Python         | 8                    |
| `Cargo.toml` / `Cargo.lock`                          | Rust           | 9                    |
| `package.json` / `package-lock.json` / `yarn.lock`   | Node.js        | 10                   |
| `go.mod` / `go.sum`                                  | Go             | 11                   |

Run all triggered dimensions. Report skipped dimensions explicitly.

---

## 12 Audit Dimensions

### Dimensions 1-4: GitHub Actions

See [reference/actions.md](reference/actions.md)

| #   | Name                 | What to Check                                               |
| --- | -------------------- | ----------------------------------------------------------- |
| 1   | Action SHA pinning   | `uses:` refs must be `@<40-char-SHA>  # vX.Y.Z`             |
| 2   | Workflow permissions | Top-level `permissions: read-all`; job-level minimal grants |
| 3   | Secret exposure      | No secrets in `run:` echo/env; `ACTIONS_STEP_DEBUG` guard   |
| 4   | Cache poisoning      | `actions/cache` key collision; restore-keys breadth         |

### Dimensions 5 & 12: Containers

See [reference/containers.md](reference/containers.md)

| #   | Name               | What to Check                                             |
| --- | ------------------ | --------------------------------------------------------- |
| 5   | Base image pinning | `FROM image@sha256:<digest>` not `:latest` or semver tag  |
| 12  | Docker build chain | Multi-stage scratch/distroless final stage; non-root USER |

### Dimension 6: Credentials

See [reference/credentials.md](reference/credentials.md)

| #   | Name                       | What to Check                                             |
| --- | -------------------------- | --------------------------------------------------------- |
| 6   | OIDC vs long-lived secrets | Prefer `id-token: write` OIDC; verify subject constraints |

### Dimension 7: .NET / NuGet

See [reference/dotnet.md](reference/dotnet.md)

| #   | Name               | What to Check                                                       |
| --- | ------------------ | ------------------------------------------------------------------- |
| 7   | NuGet lock & audit | `RestoreLockedMode`, authorized sources, `NuGetAudit` severity gate |

### Dimension 8: Python

See [reference/python.md](reference/python.md)

| #   | Name                        | What to Check                                                        |
| --- | --------------------------- | -------------------------------------------------------------------- |
| 8   | Python dependency integrity | `--require-hashes`, `--extra-index-url` risks, typosquatting signals |

### Dimension 9: Rust

See [reference/rust.md](reference/rust.md)

| #   | Name               | What to Check                                                        |
| --- | ------------------ | -------------------------------------------------------------------- |
| 9   | Cargo supply chain | `Cargo.lock` committed, `build.rs` risk, `[patch]`/`[replace]` scope |

### Dimension 10: Node.js

See [reference/node.md](reference/node.md)

| #   | Name              | What to Check                                                       |
| --- | ----------------- | ------------------------------------------------------------------- |
| 10  | Node.js integrity | `npm ci` not `npm install`, `npx` resolution, `postinstall` scripts |

### Dimension 11: Go

See [reference/go.md](reference/go.md)

| #   | Name                | What to Check                                                             |
| --- | ------------------- | ------------------------------------------------------------------------- |
| 11  | Go module integrity | `go.sum` present and committed, `GONOSUMCHECK`, `replace` directive scope |

---

## 5-Step Audit Workflow

### Step 1: Scope Detection

```bash
# Detect active ecosystems
ls .github/workflows/*.yml 2>/dev/null && echo "GHA detected"
ls Dockerfile docker-compose.yml 2>/dev/null && echo "Containers detected"
ls requirements*.txt pyproject.toml 2>/dev/null && echo "Python detected"
ls package.json 2>/dev/null && echo "Node detected"
ls go.mod 2>/dev/null && echo "Go detected"
ls Cargo.toml 2>/dev/null && echo "Rust detected"
ls *.csproj 2>/dev/null && echo ".NET detected"
```

Record active dimensions. Skip and annotate inactive ones in the report.

### Step 2: Static Analysis (per ecosystem)

Run dimension-specific checks from each reference file. Collect raw findings with:

- **Dimension number**
- **File path and line number** (`file:line`)
- **Current value** (the offending pattern)
- **Expected value** (the fix)
- **Severity**: Critical / High / Medium / Info

### Step 3: Severity Scoring

Map findings to CVSS-aligned severity bands:

| Severity     | CVSS Range | Examples                                                                    |
| ------------ | ---------- | --------------------------------------------------------------------------- |
| **Critical** | 9.0-10.0   | Unpin third-party action with write permissions + secret access             |
| **High**     | 7.0-8.9    | Mutable action ref; `:latest` container; long-lived secret with broad scope |
| **Medium**   | 4.0-6.9    | Missing `permissions: read-all`; missing `Cargo.lock` commit                |
| **Info**     | 0.1-3.9    | Semver action ref for first-party org action; advisory-only NuGet finding   |

### Step 4: Report Generation

Produce a structured markdown report:

```markdown
## Supply Chain Audit Report

**Date**: YYYY-MM-DD
**Scope**: [list active ecosystems]
**Skipped**: [list inactive ecosystems with reason]

### Summary

| Severity | Count |
| -------- | ----- |
| Critical | N     |
| High     | N     |
| Medium   | N     |
| Info     | N     |

### Findings

#### CRITICAL-001 · Dim 1 · Unpin third-party action

- **File**: `.github/workflows/release.yml:14`
- **Current**: `uses: actions/checkout@v4`
- **Expected**: `uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2`
- **Fix**: Look up SHA at https://github.com/actions/checkout/releases

### SLSA Readiness

[See reference/sbom-slsa.md for compliance table]

### Recommended Next Steps

1. Fix all Critical findings before next deployment
2. Delegate lock-file issues to `dependency-resolver` skill
3. Install SHA-pinning pre-commit hooks via `pre-commit-manager` skill
```

### Step 5: Remediation Prioritization

Order fixes:

1. **Critical first**: Unpin + write-permissions + secret-access combinations
2. **High**: Any mutable reference in production workflows
3. **Delegate**: Lock file generation to `dependency-resolver`
4. **Automate**: Pre-commit enforcement via `pre-commit-manager`
5. **Compliance**: SBOM generation, SLSA provenance — see [reference/sbom-slsa.md](reference/sbom-slsa.md)

---

## Output Format Conventions

- Every finding includes `file:line` (e.g., `.github/workflows/ci.yml:23`)
- Fix templates are copy-pasteable with no placeholders requiring guessing
- SHA lookups always reference the official release page URL
- Severity is explicit per finding; never implicit
- Report ends with a "next steps" section distinguishing manual vs. automatable fixes

---

## Integration Points

| Skill                      | When to Delegate                                                         |
| -------------------------- | ------------------------------------------------------------------------ |
| `dependency-resolver`      | Lock file conflicts, outdated transitive deps, version incompatibilities |
| `pre-commit-manager`       | Install SHA-pinning hooks, `npm ci` enforcement, `go mod verify` hooks   |
| `cybersecurity-analyst`    | Runtime threat modeling, network exposure analysis, post-incident review |
| `silent-degradation-audit` | CI reliability issues, flaky tests masking security regressions          |

---

## Evaluation Scenarios

See [reference/eval-scenarios.md](reference/eval-scenarios.md) for three graded scenarios:

- **Scenario A**: GitHub Actions monorepo — GHA + Python + Node (7 planted findings)
- **Scenario B**: Containerized Go service — Containers + Go + Credentials (5 findings)
- **Scenario C**: .NET + Rust mixed repo — .NET + Rust + SLSA readiness (6 findings)

---

## Additional Reference

- [SBOM generation, CVSS scoring, SLSA L1-L4 mapping, fix-PR workflow](reference/sbom-slsa.md)
- [Invocation interface, finding schema, inter-skill contracts, error handling](reference/contracts.md)
- GitHub Actions SHA lookup: `gh api repos/{owner}/{repo}/git/ref/tags/{tag}`
- SLSA framework: https://slsa.dev
- OpenSSF Scorecard: https://securityscorecards.dev

---

## Related Skills

- `dependency-resolver` — lock file conflict resolution
- `pre-commit-manager` — automated quality enforcement hooks
- `cybersecurity-analyst` — runtime security and threat modeling
- `silent-degradation-audit` — CI reliability and regression detection
- `pr-review-assistant` — philosophy-aware PR review including supply chain checks
