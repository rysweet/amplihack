# Evaluation Scenarios

Three graded scenarios for validating the supply-chain-audit skill.
Each scenario specifies fixture files, planted findings, expected outputs,
and pass/fail criteria.

---

## Scenario A: GitHub Actions Monorepo (GHA + Python + Node)

**Active Ecosystems**: GitHub Actions (Dims 1-4), Python (Dim 8), Node.js (Dim 10)
**Total Planted Findings**: 7
**Expected Severity Distribution**: 2 Critical, 3 High, 2 Medium

### Fixture Files

#### `.github/workflows/ci.yml`

```yaml
# Planted findings: F1 (Dim1 Critical), F2 (Dim2 High), F3 (Dim3 Critical)
name: CI
on: [push, pull_request_target] # F2: pull_request_target without permissions

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4 # F1: unpinned action (High→Critical with pull_request_target)
      - uses: actions/setup-python@v5 # also unpinned
      - run: pip install -r requirements.txt
      - run: echo "Token=${{ secrets.API_TOKEN }}" # F3: secret echoed to log
      - run: pytest
```

#### `requirements.txt`

```
# Planted finding: F4 (Dim8 High — no hash pinning)
requests==2.31.0
flask==3.0.3
gunicorn==22.0.0
```

#### `package.json`

```json
{
  "name": "frontend",
  "scripts": {
    "build": "npx webpack --config webpack.config.js",
    "test": "jest"
  },
  "devDependencies": {
    "webpack": "^5.91.0"
  }
}
```

**Planted findings**: F5 (Dim10 High — no lock file), F6 (Dim10 High — unversioned npx), F7 (Dim8 Medium — `pip install` without `--require-hashes` in workflow)

### Expected Findings

> **Note**: `Ref` column uses fixture labels (F1-F7). Actual skill output IDs follow `{SEVERITY}-{NNN}` format defined in contracts.md (e.g., `CRIT-001`). File-level findings (no applicable line) use `:0`.

| Ref | Dimension | File:Line                       | Severity | Description                                              |
| --- | --------- | ------------------------------- | -------- | -------------------------------------------------------- |
| F1  | Dim 1     | `.github/workflows/ci.yml:8`    | Critical | `pull_request_target` + unpinned action + no permissions |
| F2  | Dim 2     | `.github/workflows/ci.yml:3`    | Critical | `pull_request_target` without `permissions: read-all`    |
| F3  | Dim 3     | `.github/workflows/ci.yml:12`   | Critical | Secret echoed to log                                     |
| F4  | Dim 8     | `requirements.txt:2-4`          | High     | No hash pinning in requirements.txt                      |
| F5  | Dim 10    | `package.json:0` _(file-level)_ | High     | No `package-lock.json` detected                          |
| F6  | Dim 10    | `package.json:4`                | High     | `npx webpack` without version pin                        |
| F7  | Dim 8     | `.github/workflows/ci.yml:10`   | Medium   | `pip install` without `--require-hashes`                 |

### Pass/Fail Criteria

- **PASS**: Skill identifies all 7 findings with correct severity
- **PARTIAL PASS**: Skill identifies 5-6 findings; missing findings are Info-level misses
- **FAIL**: Skill misses F1, F2, or F3 (Critical findings)
- **FAIL**: Skill misses F4 (High finding in requirements.txt)

---

## Scenario B: Containerized Go Service (Containers + Go + Credentials)

**Active Ecosystems**: Containers (Dims 5, 12), Go (Dim 11), Credentials (Dim 6)
**Total Planted Findings**: 5
**Expected Severity Distribution**: 1 Critical, 3 High, 1 Medium

### Fixture Files

#### `Dockerfile`

```dockerfile
# Planted finding: F1 (Dim5 High — mutable tag)
FROM golang:1.22-alpine AS builder
RUN apk add --no-cache git
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN go build -o /app/server ./cmd/server

# Planted finding: F2 (Dim12 High — final stage not distroless + root user)
FROM alpine:latest  # also unpinned — F3 (Dim5 Critical — :latest)
COPY --from=builder /app/server /server
CMD ["/server"]  # runs as root — no USER instruction
```

#### `.github/workflows/deploy.yml`

```yaml
# Planted finding: F4 (Dim6 High — long-lived AWS credentials)
name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: aws-actions/configure-aws-credentials@e3dd6a429d7300a6a4c196c26e071d42e0343502 # v4.0.2 (pinned — not a planted finding)
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
```

#### `go.mod`

```
module github.com/myorg/service

go 1.22

require (
    github.com/gin-gonic/gin v1.9.1
    github.com/some/package v1.0.0
)

// Planted finding: F5 (Dim11 Medium — mutable replace)
replace github.com/some/package => github.com/myorg/fork main
```

### Expected Findings

> **Note**: `Ref` column uses fixture labels (F1-F5). Actual skill output IDs follow `{SEVERITY}-{NNN}` format defined in contracts.md.

| Ref | Dimension | File:Line                           | Severity | Description                                      |
| --- | --------- | ----------------------------------- | -------- | ------------------------------------------------ |
| F1  | Dim 5     | `Dockerfile:2`                      | High     | `golang:1.22-alpine` uses semver tag, not digest |
| F2  | Dim 12    | `Dockerfile:10-13`                  | High     | Final stage runs as root; no USER instruction    |
| F3  | Dim 5     | `Dockerfile:10`                     | Critical | `alpine:latest` — mutable :latest tag            |
| F4  | Dim 6     | `.github/workflows/deploy.yml:9-12` | High     | Static AWS credentials; OIDC available           |
| F5  | Dim 11    | `go.mod:11`                         | Medium   | `replace` directive uses mutable branch `main`   |

### Pass/Fail Criteria

- **PASS**: Skill identifies all 5 findings with correct severity
- **PARTIAL PASS**: Skill identifies F1, F3, F4 (misses F2 or F5)
- **FAIL**: Skill misses F3 (Critical — `:latest` tag)
- **FAIL**: Skill misses F4 (High — static cloud credentials)

---

## Scenario C: .NET + Rust Mixed Repo (Dim7 + Dim9 + SLSA Readiness)

**Active Ecosystems**: .NET/NuGet (Dim 7), Rust (Dim 9), SLSA assessment
**Total Planted Findings**: 6
**Expected Severity Distribution**: 0 Critical, 4 High, 2 Medium

### Fixture Files

#### `MyService/MyService.csproj`

```xml
<!-- Planted finding: F1 (Dim7 High — no lock file) -->
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8.0</TargetFramework>
  </PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.3" />
    <PackageReference Include="Microsoft.Extensions.Http" Version="8.0.0" />
  </ItemGroup>
</Project>
```

(No `packages.lock.json` present, no `Directory.Build.props`)

#### `NuGet.Config`

```xml
<!-- Planted finding: F2 (Dim7 High — dependency confusion risk) -->
<configuration>
  <packageSources>
    <add key="internal" value="https://pkgs.dev.azure.com/myorg/_packaging/feed/nuget/v3/index.json" />
    <add key="nuget.org" value="https://api.nuget.org/v3/index.json" />
    <!-- Missing <clear /> and no packageSourceMapping -->
  </packageSources>
</configuration>
```

#### `Cargo.toml` (workspace member `tools/`)

```toml
# Planted finding: F3 (Dim9 Medium — Cargo.lock in .gitignore for binary)
[package]
name = "deploy-tool"
version = "0.1.0"
edition = "2021"

[[bin]]
name = "deploy-tool"
path = "src/main.rs"

[dependencies]
reqwest = { version = "0.12", features = ["json"] }
serde_json = "1.0"
```

(`.gitignore` contains `Cargo.lock`)

#### `.github/workflows/build.yml`

```yaml
# Planted findings: F4 (Dim1 High — unpinned), F5 (Dim2 Medium — no permissions)
name: Build
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4 # F4: unpinned
      - uses: actions/setup-dotnet@v4 # also unpinned
      - run: dotnet build
      - uses: dtolnay/rust-toolchain@stable # F6: unpinned
        with:
          toolchain: stable
      - run: cargo build --release
```

(No `permissions:` key — F5)

### Expected Findings

> **Note**: `Ref` column uses fixture labels (F1-F6). Actual skill output IDs follow `{SEVERITY}-{NNN}` format defined in contracts.md. File-level findings (absent file/property) use `:0`.

| Ref | Dimension | File:Line                                     | Severity | Description                                              |
| --- | --------- | --------------------------------------------- | -------- | -------------------------------------------------------- |
| F1  | Dim 7     | `MyService/MyService.csproj:0` _(file-level)_ | High     | No `packages.lock.json`; no `RestoreLockedMode`          |
| F2  | Dim 7     | `NuGet.Config:4-7`                            | High     | Internal + public sources without `packageSourceMapping` |
| F3  | Dim 9     | `.gitignore:0` _(file-level)_                 | Medium   | `Cargo.lock` excluded for binary crate `deploy-tool`     |
| F4  | Dim 1     | `.github/workflows/build.yml:7`               | High     | `actions/checkout@v4` — unpinned semver ref              |
| F5  | Dim 2     | `.github/workflows/build.yml:4`               | Medium   | No `permissions:` key (implicit all permissions)         |
| F6  | Dim 1     | `.github/workflows/build.yml:11`              | High     | `dtolnay/rust-toolchain@stable` — mutable branch ref     |

### SLSA Readiness Expected Assessment

```markdown
| Requirement             | Status                                           |
| ----------------------- | ------------------------------------------------ |
| Build is scripted       | ✅                                               |
| Build runs on hosted CI | ✅                                               |
| Provenance generated    | ❌ No SLSA generator workflow found              |
| Action refs SHA-pinned  | ❌ 3 unpinned refs found (F4, F6 + setup-dotnet) |

Current SLSA Level: L1 (scripted build, no provenance)
Blockers to L2: Add SLSA generator; sign provenance with OIDC
```

### Pass/Fail Criteria

- **PASS**: Skill identifies all 6 findings; SLSA assessment reports L1 with blockers
- **PARTIAL PASS**: Skill identifies 4-5 findings; SLSA assessment present
- **FAIL**: Skill misses F2 (dependency confusion risk in NuGet.Config)
- **FAIL**: No SLSA readiness assessment produced
