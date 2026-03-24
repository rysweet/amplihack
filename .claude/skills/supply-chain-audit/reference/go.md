# Dimension 11: Go Module Integrity

---

## Check 1: go.sum Presence and Commitment

### Detection

```bash
# Check go.sum exists
ls go.sum 2>/dev/null || echo "MISSING"

# Check if go.sum is in .gitignore (violation)
grep "go.sum" .gitignore 2>/dev/null && echo "VIOLATION: go.sum in .gitignore"
```

### Why go.sum Matters

`go.sum` contains cryptographic hashes for every module version used in the build.
The Go toolchain refuses to use a module if its hash doesn't match. Committing
`go.sum` makes the lockfile tamper-evident and enables reproducible builds.

### Severity

| Finding                                            | Severity |
| -------------------------------------------------- | -------- |
| `go.sum` missing from repository                   | High     |
| `go.sum` in `.gitignore`                           | High     |
| `go.sum` present but `go.mod` inconsistent with it | High     |

---

## Check 2: GONOSUMCHECK and GONOSUMDB

### Detection

```bash
grep -rn "GONOSUMCHECK\|GONOSUMDB\|GOFLAGS\|GONOSUMCHECK" \
    .github/workflows/ Makefile Dockerfile .env* 2>/dev/null
```

### Pattern

```yaml
# VIOLATION — disables sum verification entirely
env:
  GONOSUMCHECK: "*"
  GONOSUMDB: "*"

# VIOLATION — disables sum check for specific module (may be legitimate but flag for review)
env:
  GONOSUMCHECK: "github.com/internal/mymodule"

# ACCEPTABLE — private modules that can't reach sum.golang.org
env:
  GONOSUMCHECK: "github.com/myorg/*"  # only if myorg is your own org
  GOPRIVATE: "github.com/myorg/*"
```

### Severity

| Finding                                                                               | Severity |
| ------------------------------------------------------------------------------------- | -------- |
| `GONOSUMCHECK=*` (disables all sum checks)                                            | Critical |
| `GONOSUMDB=*`                                                                         | High     |
| `GONOSUMCHECK` for modules not owned by your org                                      | High     |
| `GOPRIVATE` set without `GONOSUMCHECK` (acceptable — uses go.sum for private modules) | Info     |

---

## Check 3: replace Directives

`replace` directives in `go.mod` override module sources — like Rust's `[patch]`.
They are appropriate for workspace development but risky when pointing outside
the repository.

### Detection

```bash
grep -A2 "^replace" go.mod 2>/dev/null
```

### Pattern

```go
// VIOLATION — path outside repository
replace github.com/some/package => ../../external/package

// ACCEPTABLE — workspace member
replace github.com/myorg/internal => ./internal

// ACCEPTABLE — specific commit (not branch)
replace github.com/some/package => github.com/myorg/fork v0.0.0-20240101000000-abc123456789

// VIOLATION — mutable branch
replace github.com/some/package => github.com/myorg/fork main
```

### Severity

| Finding                                              | Severity |
| ---------------------------------------------------- | -------- |
| `replace` pointing to path outside repository        | Critical |
| `replace` with mutable version/branch                | High     |
| `replace` with specific pseudo-version (commit hash) | Info     |

---

## Check 4: go mod verify

```bash
# Verify module downloads against go.sum
go mod verify

# Check for vulnerabilities (requires Go 1.18+)
go install golang.org/x/vuln/cmd/govulncheck@latest
govulncheck ./...
```

### CI Integration

```yaml
- name: Verify modules
  run: go mod verify

- name: Check vulnerabilities
  run: |
    go install golang.org/x/vuln/cmd/govulncheck@latest
    govulncheck ./...
```

---

## Check 5: Toolchain Pinning (Go 1.21+)

Go 1.21 introduced `toolchain` directive in `go.mod`:

```
// go.mod
go 1.22.3
toolchain go1.22.3  // pins exact Go toolchain version
```

### Detection

```bash
grep "^toolchain" go.mod 2>/dev/null || echo "No toolchain directive"
```

### Severity

| Finding                                                       | Severity |
| ------------------------------------------------------------- | -------- |
| Go 1.21+ project without `toolchain` directive                | Medium   |
| Toolchain version in `go.mod` inconsistent with CI Go version | Medium   |

---

## Verification Checklist (Go)

- [ ] `go.sum` committed and not in `.gitignore`
- [ ] `go mod verify` passes in CI
- [ ] No `GONOSUMCHECK=*` or `GONOSUMDB=*` in CI
- [ ] `GONOSUMCHECK` scoped only to your own organization's modules
- [ ] No `replace` directives pointing outside the repository
- [ ] `govulncheck ./...` runs in CI
- [ ] `toolchain` directive pinned in `go.mod` (Go 1.21+)
