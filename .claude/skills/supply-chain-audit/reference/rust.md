# Dimension 9: Rust / Cargo Supply Chain

---

## Check 1: Cargo.lock Committed

### Detection

```bash
# Check if Cargo.lock is in .gitignore (violation for applications)
grep "Cargo.lock" .gitignore 2>/dev/null
# Check if Cargo.lock exists
ls Cargo.lock 2>/dev/null || echo "MISSING"
```

### Rule

| Project Type            | Cargo.lock Policy                                             |
| ----------------------- | ------------------------------------------------------------- |
| Binary / application    | **Commit** `Cargo.lock` — ensures reproducible builds         |
| Library (`[lib]` only)  | `.gitignore` is acceptable — consumers use their own lockfile |
| Workspace with binaries | **Commit** `Cargo.lock`                                       |

### Severity

| Finding                                              | Severity |
| ---------------------------------------------------- | -------- |
| Binary/application with `Cargo.lock` in `.gitignore` | High     |
| `Cargo.lock` missing and project is an application   | High     |

---

## Check 2: build.rs Risk Assessment

`build.rs` files execute arbitrary Rust code at compile time. They are a supply chain
risk vector when present in transitive dependencies.

### Detection

```bash
# Find build.rs files in the project
find . -name "build.rs" -not -path "*/target/*"

# Find which dependencies use build scripts
cargo metadata --format-version 1 | python3 -c "
import sys, json
meta = json.load(sys.stdin)
for pkg in meta['packages']:
    if pkg.get('build_script') and pkg['name'] not in ['$(basename $(pwd))']:
        print(f'{pkg[\"name\"]} {pkg[\"version\"]}: build_script={pkg[\"build_script\"]}')
"
```

### Assessment

Flag direct dependencies with `build.rs` for manual review:

```
# Information finding — not automatically a violation
FOUND: openssl-sys 0.9.x uses build.rs (legitimate — detects system OpenSSL)
FOUND: prost-build 0.12.x uses build.rs (legitimate — protobuf code generation)
REVIEW: unknown-crate 0.1.0 uses build.rs (investigate purpose)
```

### Severity

| Finding                                                           | Severity               |
| ----------------------------------------------------------------- | ---------------------- |
| Dependency with `build.rs` that has no obvious legitimate purpose | High (flag for review) |
| `build.rs` in project root fetching network resources             | Critical               |

---

## Check 3: [patch] and [replace] Directive Scope

`[patch]` and `[replace]` sections in `Cargo.toml` override crate sources.
They are legitimate for local development but dangerous if committed with
path patches pointing outside the repository.

### Detection

```bash
grep -A5 "\[patch\]" Cargo.toml 2>/dev/null
grep -A5 "\[replace\]" Cargo.toml 2>/dev/null
```

### Pattern

```toml
# VIOLATION — path patch pointing outside the repo
[patch.crates-io]
serde = { path = "../../external/serde-fork" }  # arbitrary code execution risk

# ACCEPTABLE — pointing to workspace member
[patch.crates-io]
my-internal-crate = { path = "./crates/my-internal-crate" }

# ACCEPTABLE — specific git commit (not branch)
[patch.crates-io]
some-crate = { git = "https://github.com/some/crate", rev = "abc1234" }

# VIOLATION — mutable branch patch
[patch.crates-io]
some-crate = { git = "https://github.com/some/crate", branch = "main" }
```

### Severity

| Finding                                               | Severity          |
| ----------------------------------------------------- | ----------------- |
| `[patch]` with external path outside repository       | Critical          |
| `[patch]` with git source using branch (mutable)      | High              |
| `[patch]` with git source using specific commit SHA   | Info (acceptable) |
| `[replace]` directive (deprecated — prefer `[patch]`) | Medium            |

---

## Check 4: cargo audit

```bash
# Install if not present
cargo install cargo-audit

# Run audit
cargo audit

# Output machine-readable JSON for CI parsing
cargo audit --json | python3 -c "
import sys, json
report = json.load(sys.stdin)
vulns = report.get('vulnerabilities', {}).get('list', [])
for v in vulns:
    print(f'{v[\"advisory\"][\"id\"]}: {v[\"package\"][\"name\"]} {v[\"package\"][\"version\"]} - {v[\"advisory\"][\"title\"]}')
    print(f'  CVSS: {v[\"advisory\"].get(\"cvss\", \"N/A\")}')
"
```

### CI Integration

```yaml
- name: Install cargo-audit
  run: cargo install cargo-audit --locked

- name: Run security audit
  run: cargo audit --deny warnings
```

### Severity

| Finding                            | Severity           |
| ---------------------------------- | ------------------ |
| Known CVE in direct dependency     | Per CVE CVSS score |
| Known CVE in transitive dependency | Per CVE CVSS score |
| `cargo audit` not in CI            | Medium             |

---

## Verification Checklist (Rust)

- [ ] `Cargo.lock` is committed (for binary/application projects)
- [ ] `cargo audit` runs in CI and fails on vulnerabilities
- [ ] No `[patch]` with external paths outside the repository
- [ ] No `[patch]` with mutable git branch references
- [ ] Direct dependencies with `build.rs` reviewed and justified
- [ ] No `[replace]` directives (use `[patch]` instead)
