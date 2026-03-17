# Code Atlas — Security Controls Test Plan

**Purpose:** Verify that each SEC-NN control from SECURITY.md is correctly implemented before any layer writes output to `docs/atlas/`.

**How to use:** These are manual and automated test scenarios. Automated tests (marked `[AUTO]`) have corresponding shell/Python test scripts. Manual tests (marked `[MANUAL]`) require human review.

---

## SEC-01: Secret Value Redaction

### TEST-SEC-01-A [AUTO]: Env var values never appear in Layer 6b output

**Setup:**

```bash
echo "DATABASE_URL=postgres://user:MYSECRETPASSWORD@localhost/db" > /tmp/test.env
echo "JWT_SECRET=supersecretjwtkey123" >> /tmp/test.env
```

**Action:** Run `/code-atlas layers=6` with the test env file.

**Expected:**

- `docs/atlas/inventory/env-vars.md` contains `DATABASE_URL` (key name)
- `docs/atlas/inventory/env-vars.md` does NOT contain `MYSECRETPASSWORD`
- `docs/atlas/inventory/env-vars.md` does NOT contain `supersecretjwtkey123`

**Pass criteria:** `grep -r "MYSECRETPASSWORD\|supersecretjwtkey123" docs/atlas/` returns no output.

---

### TEST-SEC-01-B [AUTO]: Kubernetes Secrets — data block never emitted

**Setup:** Create a test K8s Secret manifest with a base64-encoded value.

**Expected:** Layer 1 inventory lists the secret name (e.g., `db-credentials`) but never the `data:` contents.

---

## SEC-02: Path Traversal Prevention

### TEST-SEC-02-A [AUTO]: Relative path escape blocked

**Action:** Invoke skill with `codebase_path=/tmp/test-repo` and a crafted relative path `../../etc/passwd`.

**Expected:** SkillError with code `PATH_TRAVERSAL`, no file read attempted, atlas build continues for valid paths.

---

### TEST-SEC-02-B [MANUAL]: Symlink to outside codebase_path blocked

**Setup:** Create `test-repo/malicious-link -> /etc/`

**Expected:** File discovery skips `malicious-link` (SEC-07 also applies). No files from `/etc/` appear in atlas output.

---

## SEC-03: XSS Prevention — Label Sanitization

### TEST-SEC-03-A [AUTO]: Service name with HTML chars sanitized

**Setup:** Create a service named `<evil-service>` in docker-compose.yml.

**Expected:** In `docs/atlas/repo-surface/topology.mmd`, the label appears as `&lt;evil-service&gt;`.

**Pass criteria:** `grep "<evil-service>" docs/atlas/repo-surface/topology.mmd` returns no output.

---

### TEST-SEC-03-B [AUTO]: Route path with angle brackets sanitized

**Setup:** Create a route definition `/api/<version>/users` (unusual but possible in some frameworks).

**Expected:** In Layer 3 output, `<version>` is rendered as `&lt;version&gt;`.

---

## SEC-04: Safe Manifest Parsing

### TEST-SEC-04-A [MANUAL]: YAML bomb rejected

**Setup:** Create a docker-compose.yml with a YAML alias bomb (nested references that expand exponentially).

**Expected:** Parser raises an error or times out safely. Does not consume unbounded memory. SkillError logged.

---

### TEST-SEC-04-B [AUTO]: .env file is read, never sourced

**Action:** Verify that atlas implementation does not use `source .env` or `eval $(cat .env)`.

**Method:** `grep -r "source.*\.env\|eval.*env\|bash.*\.env" .claude/skills/code-atlas/` returns no results.

---

## SEC-06: Shell Injection Prevention

### TEST-SEC-06-A [MANUAL]: File path with spaces handled safely

**Setup:** Create `services/my service with spaces/routes.ts`.

**Expected:** Atlas build completes. No shell error. Paths with spaces treated as single arguments.

---

### TEST-SEC-06-B [MANUAL]: File path with semicolon does not execute

**Setup:** Create a file named `routes; rm -rf /tmp/test.ts` (or similar).

**Expected:** File is skipped or processed safely. The semicolon does not cause command injection.

---

## SEC-09: Credential Redaction in Bug Reports

### TEST-SEC-09-A [AUTO]: Password pattern redacted from code quote

**Setup:** Ensure a source file contains `db_password = "actual-secret-here"`.

**Action:** Run Pass 1 bug hunt. If this line appears in a code quote evidence block:

**Expected:** Bug report evidence shows `db_password = ***REDACTED***`.

**Pass criteria:** `grep -r "actual-secret-here" docs/atlas/bug-reports/` returns no output.

---

### TEST-SEC-09-B [AUTO]: Base64 token redacted

**Setup:** File contains a long base64 string (>40 chars) resembling an API token.

**Expected:** Bug report shows `***REDACTED***` in place of the base64 value.

---

## SEC-10: DOT/Mermaid Injection Prevention

### TEST-SEC-10-A [AUTO]: Route with Mermaid syntax characters sanitized

**Setup:** A route path `/api/users[legacy]` or `/api/users(v2)`.

**Expected:** Layer 3 Mermaid output renders `[legacy]` as `&#91;legacy&#93;` so it does not break diagram syntax.

**Pass criteria:** `mmdc -i docs/atlas/api-contracts/routes.mmd` completes without error.

---

### TEST-SEC-10-B [AUTO]: DOT label with quotes does not break diagram

**Setup:** A service named `My "Quoted" Service`.

**Expected:** DOT output wraps label as `"My \"Quoted\" Service"` — valid DOT syntax.

**Pass criteria:** `dot -Tsvg docs/atlas/repo-surface/topology.dot` completes without error.

---

## Test Run Checklist

Before considering security controls complete:

- [ ] TEST-SEC-01-A: Env var values not in Layer 6b output
- [ ] TEST-SEC-01-B: K8s Secret data block not emitted
- [ ] TEST-SEC-02-A: Path traversal returns SkillError
- [ ] TEST-SEC-03-A: HTML chars in service names escaped in diagrams
- [ ] TEST-SEC-04-B: No `source .env` in implementation
- [ ] TEST-SEC-09-A: Password patterns redacted in bug reports
- [ ] TEST-SEC-10-A: Mermaid injection chars escaped in route labels
- [ ] TEST-SEC-10-B: DOT quotes escaped in service labels
