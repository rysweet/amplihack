---
name: supply-chain-audit
description: |
  Audits the full build and deployment supply chain for security vulnerabilities across
  CI/CD pipelines, package managers, container images, and credential management.
  Auto-detects ecosystems and audits only relevant dimensions. Use when asked to perform
  a supply chain audit, audit dependencies, check action pinning, review dependency security,
  scan for compromised actions, check CI security, or assess build chain integrity.
  Motivated by the March 2026 Trivy supply chain compromise (75 action tags force-pushed).
auto_activates:
  - "supply chain audit"
  - "audit dependencies"
  - "check action pinning"
  - "dependency security"
  - "CI security audit"
  - "check for compromised actions"
  - "build chain integrity"
  - "SBOM"
  - "SLSA compliance"
metadata:
  version: "1.0"
  author: amplihack
---

# Supply Chain Audit Skill

Audits the full build and deployment supply chain for security vulnerabilities. Covers 12
dimensions across GitHub Actions, package managers (NuGet, PyPI, Cargo, npm, Go), containers,
credentials, and cache integrity. Auto-detects ecosystems; only audits what is present.

Motivated by the Trivy supply chain compromise of March 19, 2026, where 75 of 76 action tags
were force-pushed with malicious code — any pipeline using `aquasecurity/trivy-action@master`
silently executed attacker-controlled code with full GITHUB_TOKEN access.

## When to Use

Use for:

- Pre-merge security gates on repos adding new CI workflows
- Periodic supply chain health checks (weekly/monthly)
- Incident response after upstream compromise reports
- SLSA compliance assessment
- SOC 2 / ISO 27001 supply chain evidence generation

Do not use for:

- Runtime vulnerability scanning of deployed services (use cybersecurity-analyst)
- Dependency version conflict resolution (use dependency-resolver)
- Pre-commit hook management (use pre-commit-manager)

## Workflow

Execute these steps in order:

### Step 1: Detect Ecosystems

Scan the repository for signal files to determine which audit dimensions apply.

| Signal Files                                                                          | Ecosystem          | Dimensions |
| ------------------------------------------------------------------------------------- | ------------------ | ---------- |
| `.github/workflows/*.yml`, `.github/aw/*.yml`                                         | GitHub Actions     | 1, 2, 3, 4 |
| `*.csproj`, `*.sln`, `nuget.config`, `Directory.Build.props`                          | .NET / NuGet       | 7          |
| `requirements.txt`, `pyproject.toml`, `setup.py`, `Pipfile`, `uv.lock`, `poetry.lock` | Python / PyPI      | 8          |
| `Cargo.toml`, `Cargo.lock`                                                            | Rust / Cargo       | 9          |
| `package.json`, `.npmrc`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`          | Node.js / npm      | 10         |
| `go.mod`, `go.sum`                                                                    | Go modules         | 11         |
| `Dockerfile*`, `docker-compose*.yml`, `.dockerignore`                                 | Containers         | 5, 12      |
| Any workflow with cloud provider steps                                                | Credentials / OIDC | 6          |
| `.github/dependabot.yml`, `renovate.json*`, `.renovaterc*`                            | Automation bots    | 14         |
| `.github/CODEOWNERS`, branch protection                                               | Governance         | 15         |

Only proceed with dimensions where signal files are found. Log which dimensions are skipped
and why.

### Step 2: Run Dimension Audits

For each detected dimension, apply the checks in the corresponding reference file. Run
independent dimensions in parallel where possible.

Reference files (one per dimension group):

- `reference/actions.md` — Dimensions 1-4, 13 (GitHub Actions + dangerous triggers)
- `reference/containers.md` — Dimensions 5, 12 (Container chain)
- `reference/credentials.md` — Dimension 6 (OIDC / auth)
- `reference/dotnet.md` — Dimension 7 (.NET / NuGet)
- `reference/python.md` — Dimension 8 (Python / PyPI)
- `reference/rust.md` — Dimension 9 (Rust / Cargo)
- `reference/node.md` — Dimension 10 (Node.js / npm)
- `reference/go.md` — Dimension 11 (Go modules)
- `reference/sbom-slsa.md` — SBOM generation and SLSA mapping
- `reference/automations.md` — Dimensions 14-15 (Dependabot/Renovate + branch protection)

### Step 3: Score Severity

Apply CVSS-aligned scoring to each finding:

| Severity     | CVSS Range | Criteria                                                             |
| ------------ | ---------- | -------------------------------------------------------------------- |
| **Critical** | 9.0-10.0   | Attacker-controlled code execution in CI with secret access          |
| **High**     | 7.0-8.9    | Unverified code execution; overly broad permissions to third parties |
| **Medium**   | 4.0-6.9    | Missing integrity verification; predictable cache keys               |
| **Info**     | 0.1-3.9    | Best practice gap with low exploitation likelihood                   |

### Step 4: Collate Findings

Aggregate all findings into a single report. De-duplicate findings that appear in
multiple dimensions. Each finding must include:

- Severity (Critical / High / Medium / Info)
- Dimension name
- File path and line number
- Exact problematic value
- Fix instruction with corrected value where possible
- SLSA level impact (if applicable)

### Step 5: Generate Report

Emit the report in the format defined in the Output Format section below.

Optionally append:

- SBOM summary (if `reference/sbom-slsa.md` guidance followed)
- Fix-PR generation checklist (see reference/sbom-slsa.md)
- Pre-commit hook recommendations (delegate to pre-commit-manager if hooks are missing)
- Dependency version health check (delegate to dependency-resolver for lock file drift)

## Output Format

The report uses the following structure:

## Supply Chain Audit Report

**Repo:** <name> **Date:** <ISO date> **Ecosystems detected:** <list>

### Summary

| Dimension              | Critical | High  | Medium | Info  |
| ---------------------- | -------- | ----- | ------ | ----- |
| GitHub Actions Pinning | 0        | 1     | 0      | 2     |
| Action Permissions     | 0        | 1     | 0      | 0     |
| Secret Exposure        | 1        | 0     | 0      | 0     |
| Cache Poisoning        | 0        | 0     | 1      | 0     |
| Container Pinning      | 0        | 1     | 0      | 0     |
| OIDC / Credentials     | 1        | 0     | 0      | 0     |
| .NET / NuGet           | 0        | 1     | 1      | 0     |
| Python / PyPI          | 0        | 0     | 0      | 0     |
| Rust / Cargo           | -        | -     | -      | -     |
| Node.js / npm          | 0        | 0     | 1      | 0     |
| Go modules             | -        | -     | -      | -     |
| Docker / OCI           | 0        | 0     | 1      | 0     |
| **Total**              | **2**    | **4** | **4**  | **2** |

_(- = ecosystem not detected)_

### Critical Findings

- [ ] **Secret in third-party action env** — `AZURE_CLIENT_SECRET` passed to
      `some-vendor/action@abc1234` in `.github/workflows/deploy.yml:42`.
      Fix: migrate to OIDC federated credentials (see reference/credentials.md).
      SLSA impact: fails L3 (non-falsifiable build provenance).

### High Findings

- [ ] **Unpinned action tag** — `uses: aquasecurity/trivy-action@v0.35.0` in
      `.github/workflows/ci.yml:89`. Fix: pin to full SHA.

### Medium Findings

- [ ] **Predictable cache key** — binary cache keyed on `${{ runner.os }}-trivy`
      in `.github/workflows/ci.yml:103`. Fix: add a content-addressed component.

### Info

- [ ] **NuGetAudit not enabled** — `<NuGetAudit>` not set in `Directory.Build.props`.
      Recommend adding `<NuGetAudit>true</NuGetAudit>`.

### Recommendations (Priority Order)

1. Pin all action `uses:` to full 40-char SHA hashes.
2. Migrate Azure SP client-secret auth to OIDC federated credentials.
3. Add `--locked-mode` to all `dotnet restore` steps.
4. Pin Dockerfile `FROM` directives to digest hashes.
5. Enable `<NuGetAudit>` in Directory.Build.props.

### SLSA Compliance Status

| SLSA Level          | Status | Blockers                                               |
| ------------------- | ------ | ------------------------------------------------------ |
| L1 (Provenance)     | FAIL   | Missing provenance attestation in 2 workflows          |
| L2 (Hosted build)   | PASS   | Runs on GitHub-hosted runners                          |
| L3 (Hardened build) | FAIL   | Unpinned third-party actions; overly broad permissions |

### Next Steps

- Run `pre-commit-manager` to add action-pinning hooks for local enforcement.
- Run `dependency-resolver` to check lock file drift for detected package managers.
- See `reference/sbom-slsa.md` for SBOM generation guidance.

## Integration Modes

### On-Demand Invocation

```
Run a supply chain audit on this repo
Audit dependencies in .github/workflows
Check action pinning
```

### As a CI Check

Generate a `.github/workflows/supply-chain-audit.yml` that runs this skill weekly
(cron schedule) or on PRs that modify workflow files. Use `safe-outputs` mode to
post findings as PR comments or create GitHub issues.

### With Pre-Commit Hooks

After audit, delegate to `pre-commit-manager` to install hooks that enforce:

- Action SHA pinning (detect-secrets pattern or custom hook)
- `npm ci` instead of `npm install`
- Dockerfile digest pinning linter

### With Dependency Resolver

After detecting package manager lock file issues, delegate to `dependency-resolver`
to compare local vs CI dependency versions and generate pinning recommendations.

## Evaluation Scenarios

See `reference/eval-scenarios.md` for three validated test cases:

1. **Scenario A** — Repo with Trivy-style unpinned action + exposed GITHUB_TOKEN
2. **Scenario B** — .NET repo with `dotnet restore` missing `--locked-mode` + non-default NuGet source
3. **Scenario C** — Node.js repo using `npx` in CI + `postinstall` script in a dependency

Each scenario includes: repo file fixtures, expected findings (severity + dimension),
and a pass/fail checklist aligned with Claude best-practices eval structure.

## Related Skills

- `dependency-resolver` — lock file drift detection and version pinning
- `pre-commit-manager` — install hooks that enforce pinning policies locally
- `cybersecurity-analyst` — runtime security analysis (complements this skill's static checks)
- `silent-degradation-audit` — CI reliability; pairs well post-supply-chain-fix

## Reference Files

| File                          | Covers                                                |
| ----------------------------- | ----------------------------------------------------- |
| `reference/actions.md`        | Dimensions 1-4: GitHub Actions                        |
| `reference/containers.md`     | Dimensions 5, 12: Container supply chain              |
| `reference/credentials.md`    | Dimension 6: OIDC vs secret-based auth                |
| `reference/dotnet.md`         | Dimension 7: .NET / NuGet                             |
| `reference/python.md`         | Dimension 8: Python / PyPI                            |
| `reference/rust.md`           | Dimension 9: Rust / Cargo                             |
| `reference/node.md`           | Dimension 10: Node.js / npm                           |
| `reference/go.md`             | Dimension 11: Go modules                              |
| `reference/sbom-slsa.md`      | SBOM generation + SLSA mapping + fix-PR workflow      |
| `reference/automations.md`    | Dimensions 14-15: Automation bots + branch protection |
| `reference/eval-scenarios.md` | Evaluation test cases                                 |
