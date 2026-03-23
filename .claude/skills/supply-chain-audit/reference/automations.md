# Automated Dependency Update Tools and Branch Protection

## Dimension 14: Dependabot / Renovate Configuration

Dependabot and Renovate automate dependency updates. Misconfigured, they
can become supply chain attack vectors via auto-merge, broad token scope, or
no stabilization period before acting on new package versions.

### Dependabot Checks

Signal file: `.github/dependabot.yml`

**Missing config (Info)**: No `dependabot.yml` found. Unmanaged dependency
updates can drift silently. Recommend adding Dependabot for all detected ecosystems.

**Auto-merge without status checks (High)**: `automerge: true` combined with
no required status checks — compromised upstream package auto-merges to main.

**No minimum release age (Medium)**: Missing `cooldown.days` (Dependabot) or
similar stabilization — new packages published within 48h carry higher supply
chain risk.

**Missing security-only group (Info)**: Security updates buried among
maintenance bumps cause review fatigue. Recommend a dedicated security group.

### Renovate Checks

Signal files: `renovate.json`, `renovate.json5`, `.renovaterc`, `.renovaterc.json`

**Global automerge without minimumReleaseAge (High)**: `"automerge": true`
with no `"minimumReleaseAge"` allows acting on packages within minutes of a
potentially malicious publish. Recommend `"minimumReleaseAge": "3 days"`.

**Missing minimumReleaseAge (Medium)**: No stabilization period configured.
Attackers sometimes compromise accounts to publish malicious versions quickly;
a 3-day window catches most reactive takedowns.

**Major version auto-merge (High)**: `automerge: true` without excluding
`version-update:semver-major` — major bumps may have breaking API changes
or introduce new dependencies.

### Secure Renovate Template

```json
{
  "extends": ["config:base"],
  "minimumReleaseAge": "3 days",
  "automerge": false,
  "packageRules": [
    {
      "matchUpdateTypes": ["patch"],
      "matchPackagePatterns": ["eslint", "prettier"],
      "automerge": true,
      "minimumReleaseAge": "3 days"
    },
    {
      "matchUpdateTypes": ["major"],
      "automerge": false,
      "addLabels": ["major-update"]
    }
  ]
}
```

## Dimension 15: Branch Protection and CODEOWNERS

Supply chain fixes are only effective if the protected branch cannot be
bypassed. Audits the governance layer around the build chain files.

### Branch Protection Checks

Check `.github/CODEOWNERS` and note whether API branch protection is accessible.
If `gh api` is available: `gh api repos/{owner}/{repo}/branches/main/protection`.

**Critical**: No branch protection on default branch — any workflow or bot
can push directly without review.

**High**: `Allow force pushes` enabled on the protected branch.

**High**: `Require approvals: 0` — automated PRs can self-merge.

**High**: `Require status checks` not configured — a failing CI fix can still merge.

### CODEOWNERS Checks

Look for `.github/CODEOWNERS` or `CODEOWNERS` at repo root.

**Medium**: `.github/workflows/` not in CODEOWNERS — CI configuration
changes reach production without a designated security reviewer.

**Medium**: Build configuration files unprotected — flag if missing entries for:

- `.github/workflows/`, `.github/aw/`
- `Dockerfile*`, `docker-compose*.yml`
- `nuget.config`, `Directory.Build.props`
- `package.json`, `.npmrc`
- `go.mod`, `Cargo.toml`
- `requirements.txt`, `pyproject.toml`

**Info**: CODEOWNERS exists but uses `*` catch-all only — no specific
ownership over sensitive supply chain files.
