# Evaluation Scenarios

Three test cases for validating this skill's detection accuracy.
Follow Claude best-practices eval structure: each scenario includes
fixture files, expected findings, and a pass/fail checklist.

---

## Scenario A: Trivy-Style Compromise

**Description**: Repo with an unpinned action referencing a known-compromised tag,
plus a workflow that passes GITHUB_TOKEN to the third-party step.

### Fixture Files

`.github/workflows/security-scan.yml`:

```yaml
name: Security Scan
on: [push]
permissions:
  security-events: write
  contents: read
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Trivy
        uses: aquasecurity/trivy-action@v0.35.0
        env:
          GITHUB_TOKEN: ${{ github.token }}
        with:
          scan-type: fs
```

### Expected Findings

| Severity | Dimension          | File:Line            | Description                                                            |
| -------- | ------------------ | -------------------- | ---------------------------------------------------------------------- |
| Critical | Secret Exposure    | security-scan.yml:10 | GITHUB_TOKEN passed to third-party action env                          |
| High     | Action Pinning     | security-scan.yml:8  | `trivy-action@v0.35.0` — mutable tag, known-compromised                |
| High     | Action Pinning     | security-scan.yml:5  | `checkout@v4` — mutable tag                                            |
| High     | Action Permissions | security-scan.yml:3  | `security-events: write` granted at workflow level to third-party step |

### Pass/Fail Checklist

- [ ] Detects `GITHUB_TOKEN` in `env:` of third-party action step — Critical
- [ ] Flags `@v0.35.0` as mutable tag (not SHA) — High
- [ ] Flags `@v4` as mutable tag — High
- [ ] Flags `security-events: write` at workflow level applying to third-party step — High
- [ ] Provides SHA-pin fix instruction for at least one action
- [ ] Does not flag `actions/checkout` as "third-party" (it is first-party)

---

## Scenario B: .NET Restore Without Lock Mode

**Description**: .NET repo with `dotnet restore` in CI lacking `--locked-mode`,
missing `packages.lock.json`, and a non-default NuGet source without `<clear/>`.

### Fixture Files

`.github/workflows/ci.yml` (relevant excerpt):

```yaml
- name: Restore
  run: dotnet restore MyApp.sln
```

`nuget.config`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<configuration>
  <packageSources>
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" />
    <add key="myFeed" value="https://pkgs.dev.azure.com/myorg/_packaging/myfeed/nuget/v3/index.json" />
  </packageSources>
</configuration>
```

`Directory.Build.props` (excerpt):

```xml
<Project>
  <PropertyGroup>
    <TargetFramework>net9.0</TargetFramework>
  </PropertyGroup>
</Project>
```

Signal files present: `MyApp.csproj`, `MyApp.sln`, `nuget.config`, `Directory.Build.props`

### Expected Findings

| Severity | Dimension    | File:Line             | Description                                    |
| -------- | ------------ | --------------------- | ---------------------------------------------- |
| Critical | .NET / NuGet | ci.yml:2              | `dotnet restore` without `--locked-mode`       |
| High     | .NET / NuGet | nuget.config:5        | Private feed without `<clear/>` before sources |
| High     | .NET / NuGet | (repo root)           | `packages.lock.json` not found in project      |
| Medium   | .NET / NuGet | nuget.config          | `<packageSourceMapping>` absent                |
| Medium   | .NET / NuGet | Directory.Build.props | `<NuGetAudit>` not enabled                     |

### Pass/Fail Checklist

- [ ] Detects `dotnet restore` without `--locked-mode` — Critical
- [ ] Detects missing `<clear/>` before private NuGet source — High
- [ ] Detects missing `packages.lock.json` — High
- [ ] Detects missing `<packageSourceMapping>` — Medium
- [ ] Detects missing `<NuGetAudit>` — Medium
- [ ] Does not flag Python/Rust/npm (no signal files present) — no false positives

---

## Scenario C: Node.js npx + Postinstall Risk

**Description**: Node.js repo using `npx` in CI for tooling, with a direct
dependency that has a `postinstall` script.

### Fixture Files

`.github/workflows/build.yml` (relevant excerpt):

```yaml
- name: Install deps
  run: npm install
- name: Lint
  run: npx eslint@latest src/
```

`package.json` (relevant excerpt):

```json
{
  "dependencies": {
    "express": "^4.18.0",
    "some-analytics-sdk": "^2.3.1"
  },
  "devDependencies": {
    "eslint": "^8.0.0"
  }
}
```

`node_modules/some-analytics-sdk/package.json` (relevant excerpt):

```json
{
  "scripts": {
    "postinstall": "node ./scripts/telemetry-install.js"
  }
}
```

`package-lock.json`: present and committed.

### Expected Findings

| Severity | Dimension     | File:Line    | Description                                                                         |
| -------- | ------------- | ------------ | ----------------------------------------------------------------------------------- |
| Critical | Node.js / npm | build.yml:4  | `npm install` in CI — use `npm ci` to enforce lockfile                              |
| High     | Node.js / npm | build.yml:6  | `npx eslint@latest` — unpinned `@latest` tag executes downloaded package            |
| High     | Node.js / npm | package.json | `some-analytics-sdk` has `postinstall` script — arbitrary code execution on install |

### Pass/Fail Checklist

- [ ] Detects `npm install` instead of `npm ci` — Critical
- [ ] Detects `npx` with `@latest` — High
- [ ] Detects `postinstall` in direct dependency — High
- [ ] Does not flag `package-lock.json` (it is present and committed) — no false positive
- [ ] Provides `npm ci` as the fix for `npm install`
- [ ] Does not flag .NET/Python/Rust dimensions (no signal files) — no false positives

---

## Scenario D: pull_request_target Checkout Vulnerability

**Description**: Repo with a `pull_request_target` triggered workflow that
checks out the PR's head commit — a critical RCE vector giving fork PRs
full access to repository secrets and write permissions.

### Fixture Files

`.github/workflows/docs-preview.yml`:

```yaml
name: Docs Preview
on:
  pull_request_target:
    branches: [main]
permissions:
  contents: read
  pull-requests: write
jobs:
  build-preview:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
      - run: npm ci && npm run build:docs
      - uses: actions/upload-artifact@v3
        with:
          name: docs-preview
          path: ./dist
      - name: Comment preview link
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: 'Preview ready!'
            })
```

### Expected Findings

| Severity | Dimension          | File:Line           | Description                                                                                             |
| -------- | ------------------ | ------------------- | ------------------------------------------------------------------------------------------------------- |
| Critical | Dangerous Triggers | docs-preview.yml:10 | `pull_request_target` + checkout of PR head SHA — attacker code runs with write permissions and secrets |
| High     | Action Pinning     | docs-preview.yml:9  | `checkout@v4` — mutable tag                                                                             |
| High     | Action Pinning     | docs-preview.yml:14 | `upload-artifact@v3` — mutable tag                                                                      |
| High     | Action Pinning     | docs-preview.yml:19 | `github-script@v7` — mutable tag                                                                        |

### Pass/Fail Checklist

- [ ] Detects `pull_request_target` + PR head SHA checkout as Critical
- [ ] Explains why this is dangerous (fork PRs + secrets + write access)
- [ ] Provides concrete fix: use `pull_request` trigger for this workflow
- [ ] Flags all three unpinned `@v4`, `@v3`, `@v7` tags — High
- [ ] Does not flag the `pull-requests: write` permission as a standalone finding
      (it is appropriate for commenting; the danger is the trigger+checkout combo)
- [ ] Does not false-positive on `github-script` as a "third-party action"
      (it is `actions/*` — first-party)
