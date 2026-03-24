# How to Run a Supply Chain Audit

The `supply-chain-audit` skill audits your repository's full build and deployment
supply chain for security vulnerabilities. It auto-detects which ecosystems are
present and audits only relevant dimensions.

**Motivated by**: the March 2026 Trivy supply chain compromise, where 75 of 76
`aquasecurity/trivy-action` tags were force-pushed with attacker-controlled code.

## Quick Start

Simply ask Claude to run an audit in any Claude Code session:

```
Run a supply chain audit on this repo
```

Or use more specific triggers:

```
Audit action pinning in .github/workflows
Check for compromised actions
Assess SLSA compliance
Review CI security
```

## What Gets Audited

The skill auto-detects ecosystems from signal files:

| Signal Files                              | Ecosystem Audited                                     |
| ----------------------------------------- | ----------------------------------------------------- |
| `.github/workflows/*.yml`                 | GitHub Actions (pinning, permissions, secrets, cache) |
| `*.csproj`, `nuget.config`                | .NET / NuGet lock files                               |
| `requirements.txt`, `pyproject.toml`      | Python / PyPI hash pinning                            |
| `Cargo.toml`                              | Rust / Cargo lock files                               |
| `package.json`                            | Node.js / npm lock files                              |
| `go.mod`                                  | Go module integrity                                   |
| `Dockerfile*`                             | Container base image pinning                          |
| `.github/dependabot.yml`, `renovate.json` | Automation bot configuration _(planned)_              |
| `.github/CODEOWNERS`                      | Branch protection and governance _(planned)_          |

Only ecosystems with signal files present are audited — no false positives for
absent technologies.

## Understanding the Report

Findings are reported in four severity levels:

| Severity     | Examples                                                                                                        |
| ------------ | --------------------------------------------------------------------------------------------------------------- |
| **Critical** | `pull_request_target` + PR head checkout; secrets piped through shell; `dotnet restore` without `--locked-mode` |
| **High**     | Unpinned action tags; overly broad permissions to third-party actions; missing lock files                       |
| **Medium**   | Predictable cache keys; missing NuGet audit configuration                                                       |
| **Info**     | Best-practice gaps with low exploitation likelihood                                                             |

Each finding includes:

- File path and line number
- Exact problematic value
- Fix instruction with corrected value
- SLSA level impact (where applicable)

## Example Output

```markdown
## Supply Chain Audit Report

**Repo:** my-app **Date:** 2026-03-23 **Ecosystems detected:** GitHub Actions, .NET, Node.js

### Summary

| Dimension              | Critical | High  | Medium | Info  |
| ---------------------- | -------- | ----- | ------ | ----- |
| GitHub Actions Pinning | 0        | 2     | 0      | 1     |
| Secret Exposure        | 1        | 0     | 0      | 0     |
| .NET / NuGet           | 0        | 1     | 1      | 0     |
| **Total**              | **1**    | **3** | **1**  | **1** |

### Critical Findings

- [ ] **Secrets piped through shell** — `${{ secrets.API_KEY }}` used in `echo ${{ secrets.API_KEY }} | base64`
      in `.github/workflows/ci.yml:45`. Fix: use OIDC or pass via environment variable directly.

### High Findings

- [ ] **Unpinned action** — `uses: actions/checkout@v4` in `.github/workflows/ci.yml:12`.
      Fix: pin to `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4`
```

## Critical Security Patterns to Know

### pull_request_target Misuse (Critical)

This is a commonly misunderstood attack vector. If your workflow uses
`pull_request_target` **and** checks out the PR's head commit, attackers can
submit a PR that executes arbitrary code with your full repository secrets:

```yaml
# DANGEROUS — attacker controls the code AND gets your secrets
on: pull_request_target
steps:
  - uses: actions/checkout@v4
    with:
      ref: ${{ github.event.pull_request.head.sha }} # ← attacker's code
  - run: npm ci && npm test # ← attacker executes anything here
```

**Fix**: Use `pull_request` (no `_target`) for workflows that run PR code.
Reserve `pull_request_target` only for bot workflows that never check out fork code.

### Dependabot Without minimumReleaseAge (Medium)

Without a stabilization period, your automated updates can pick up a malicious
package version within minutes of it being published. Attackers sometimes
compromise maintainer accounts specifically to publish brief malicious releases:

```json
// renovate.json — add this to prevent acting on just-published versions
{
  "minimumReleaseAge": "3 days"
}
```

## Follow-Up Actions

After the audit, the skill recommends related skills:

- **`pre-commit-manager`** — install hooks that enforce action SHA pinning locally
- **`dependency-resolver`** — check lock file drift across all package managers
- **`cybersecurity-analyst`** — runtime security analysis (complements static audit)
- **`silent-degradation-audit`** — CI reliability check post-supply-chain-fix

## Running as a CI Check

Ask Claude to generate a scheduled workflow:

```
Generate a weekly GitHub Actions workflow that runs a supply chain audit
and posts findings as a PR comment
```

## Reference

- Skill location: `.claude/skills/supply-chain-audit/`
- Issue: [#3440](https://github.com/rysweet/amplihack/issues/3440)
- Reference files: `.claude/skills/supply-chain-audit/reference/` (one file per ecosystem)
- Eval scenarios: `.claude/skills/supply-chain-audit/reference/eval-scenarios.md`
