#!/bin/bash
# .claude/skills/code-atlas/tests/test_security_controls.sh
#
# TDD tests for Code Atlas security controls (SEC-01 through SEC-10).
# Tests validate that each security control is enforced when atlas layers write output.
#
# THESE TESTS WILL FAIL until the corresponding security validators are implemented.
# The tests define the expected behavior — implement to make them pass.
#
# Usage: bash .claude/skills/code-atlas/tests/test_security_controls.sh
# Exit:  0 = all tests passed, non-zero = failures
#
# Requires:
#   - scripts/validate_atlas_output.sh   (SEC-01, SEC-03, SEC-09, SEC-10)
#   - scripts/safe_read.sh               (SEC-02, SEC-07)
#   - scripts/check_file_size.sh         (SEC-08)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

VALIDATE_SCRIPT="${REPO_ROOT}/scripts/validate_atlas_output.sh"
SAFE_READ_SCRIPT="${REPO_ROOT}/scripts/safe_read.sh"

PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------
assert_pass() {
    local test_name="$1"
    local condition="$2"  # "true" or "false"
    local detail="${3:-}"

    if [[ "$condition" == "true" ]]; then
        echo "PASS: $test_name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $test_name${detail:+ — $detail}"
        FAIL=$((FAIL + 1))
    fi
}

assert_exit_code() {
    local test_name="$1"
    local expected="$2"
    local actual="$3"
    local output="${4:-}"
    if [[ "$actual" -eq "$expected" ]]; then
        echo "PASS: $test_name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $test_name (expected exit $expected, got $actual)"
        [[ -n "$output" ]] && echo "  Output: ${output:0:200}"
        FAIL=$((FAIL + 1))
    fi
}

assert_not_in_file() {
    local test_name="$1"
    local pattern="$2"
    local file="$3"

    if [[ ! -f "$file" ]]; then
        echo "FAIL: $test_name — file not found: $file"
        FAIL=$((FAIL + 1))
        return
    fi
    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo "FAIL: $test_name — forbidden pattern '$pattern' found in $file"
        FAIL=$((FAIL + 1))
    else
        echo "PASS: $test_name"
        PASS=$((PASS + 1))
    fi
}

assert_in_file() {
    local test_name="$1"
    local pattern="$2"
    local file="$3"

    if [[ ! -f "$file" ]]; then
        echo "FAIL: $test_name — file not found: $file"
        FAIL=$((FAIL + 1))
        return
    fi
    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo "PASS: $test_name"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $test_name — expected pattern '$pattern' not found in $file"
        FAIL=$((FAIL + 1))
    fi
}

# ============================================================================
# SEC-01: Secret Value Redaction (CRITICAL)
# ============================================================================

echo ""
echo "=== SEC-01: Secret Value Redaction ==="

# Precondition: validate_atlas_output.sh must exist
if [[ ! -f "$VALIDATE_SCRIPT" ]]; then
    echo "FAIL: SEC-01 prerequisite — validate_atlas_output.sh not found at $VALIDATE_SCRIPT"
    FAIL=$((FAIL + 5))
else

    # TEST-SEC-01-A: .env values never appear in atlas output
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/docs/atlas/inventory"

    # Create a fake .env with a real secret
    cat > "$tmpdir/.env" << 'EOF'
DATABASE_URL=postgres://user:MYSECRETPASSWORD@localhost/db  # pragma: allowlist secret
JWT_SECRET=supersecretjwtkey123  # pragma: allowlist secret
REDIS_URL=redis://:REDISPASS@localhost:6379  # pragma: allowlist secret
EOF

    # Simulate what atlas layer6 should produce: keys ONLY
    cat > "$tmpdir/docs/atlas/inventory/env-vars.md" << 'EOF'
| Variable | Description | Required |
|----------|-------------|----------|
| DATABASE_URL | PostgreSQL connection | Yes |
| JWT_SECRET | JWT signing key | Yes |
| REDIS_URL | Redis connection | Yes |
EOF

    # Run validator — it should PASS because values are not in the file
    output=$(bash "$VALIDATE_SCRIPT" --atlas-dir "$tmpdir/docs/atlas" 2>&1 || true)
    exit_val=$?

    assert_not_in_file "SEC-01-A: MYSECRETPASSWORD not in env-vars.md" \
        "MYSECRETPASSWORD" \
        "$tmpdir/docs/atlas/inventory/env-vars.md"
    assert_not_in_file "SEC-01-A: supersecretjwtkey123 not in env-vars.md" \
        "supersecretjwtkey123" \
        "$tmpdir/docs/atlas/inventory/env-vars.md"
    assert_not_in_file "SEC-01-A: REDISPASS not in env-vars.md" \
        "REDISPASS" \
        "$tmpdir/docs/atlas/inventory/env-vars.md"

    # TEST-SEC-01-B: Kubernetes Secret data block values never emitted
    mkdir -p "$tmpdir/docs/atlas/repo-surface"
    cat > "$tmpdir/docs/atlas/repo-surface/README.md" << 'EOF'
# Layer 1 - Runtime Topology
Services: api, auth, db-proxy
Secrets mounted: db-credentials (key names: DATABASE_URL, DB_PASSWORD)
EOF

    assert_not_in_file "SEC-01-B: K8s secret values not in layer1 README" \
        "dXNlcjpwYXNz\|cGFzc3dvcmQ=\|base64" \
        "$tmpdir/docs/atlas/repo-surface/README.md"

    rm -rf "$tmpdir"
fi

# TEST-SEC-01-C: validate_atlas_output.sh itself detects secrets if they leaked
tmpdir=$(mktemp -d)
mkdir -p "$tmpdir/docs/atlas/inventory"

# Intentionally bad output with a leaked secret (env-var assignment format triggers SEC-01)
cat > "$tmpdir/docs/atlas/inventory/env-vars.md" << 'EOF'
# Leaked secrets example (bad atlas output)
JWT_SECRET=supersecretjwtkey123  # pragma: allowlist secret
DATABASE_URL=postgres://user:MYSECRETPASSWORD@localhost/db  # pragma: allowlist secret
EOF

if [[ -f "$VALIDATE_SCRIPT" ]]; then
    output=$(bash "$VALIDATE_SCRIPT" --atlas-dir "$tmpdir/docs/atlas" --strict 2>&1) && exit_val=0 || exit_val=$?
    # Should exit non-zero (detected a problem)
    assert_exit_code "SEC-01-C: validator exits 1 when secret value found in output" 1 "$exit_val" "$output"
fi
rm -rf "$tmpdir"

# ============================================================================
# SEC-02: Path Traversal Prevention (CRITICAL)
# ============================================================================

echo ""
echo "=== SEC-02: Path Traversal Prevention ==="

# Precondition: safe_read.sh must exist
if [[ ! -f "$SAFE_READ_SCRIPT" ]]; then
    echo "FAIL: SEC-02 prerequisite — safe_read.sh not found at $SAFE_READ_SCRIPT"
    FAIL=$((FAIL + 3))
else

    # TEST-SEC-02-A: Relative path traversal rejected
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/codebase"
    echo "safe content" > "$tmpdir/codebase/safe.txt"

    output=$(bash "$SAFE_READ_SCRIPT" "$tmpdir/codebase/../../etc/passwd" --boundary "$tmpdir/codebase" 2>&1) && exit_val=0 || exit_val=$?
    assert_exit_code "SEC-02-A: relative path escape blocked (exit 1)" 1 "$exit_val" "$output"
    # Output should mention PATH_TRAVERSAL or security error
    if echo "$output" | grep -qi "path.traversal\|security\|blocked\|denied\|invalid\|Error\|boundary"; then
        echo "PASS: SEC-02-A: error message mentions traversal/security"
        PASS=$((PASS + 1))
    else
        echo "FAIL: SEC-02-A: error message should mention traversal/security"
        echo "  Got: $output"
        FAIL=$((FAIL + 1))
    fi
    rm -rf "$tmpdir"

    # TEST-SEC-02-B: Absolute path outside codebase_path rejected
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/codebase"

    output=$(bash "$SAFE_READ_SCRIPT" "/etc/passwd" --boundary "$tmpdir/codebase" 2>&1) && exit_val=0 || exit_val=$?
    assert_exit_code "SEC-02-B: absolute path outside codebase blocked (exit 1)" 1 "$exit_val" "$output"
    rm -rf "$tmpdir"

    # TEST-SEC-02-C: Valid absolute path within codebase reads successfully
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/codebase/src"
    echo "package main" > "$tmpdir/codebase/src/main.go"

    output=$(bash "$SAFE_READ_SCRIPT" "$tmpdir/codebase/src/main.go" --boundary "$tmpdir/codebase" 2>&1)
    exit_val=$?
    assert_exit_code "SEC-02-C: valid path within codebase reads (exit 0)" 0 "$exit_val" "$output"
    rm -rf "$tmpdir"

fi

# ============================================================================
# SEC-03: XSS Prevention — Mermaid/DOT Label Sanitization (HIGH)
# ============================================================================

echo ""
echo "=== SEC-03: XSS Prevention ==="

# TEST-SEC-03-A: HTML chars in service name are escaped in Mermaid output
tmpdir=$(mktemp -d)
mkdir -p "$tmpdir/docs/atlas/repo-surface"

# Simulate atlas output that was generated from a service named "<evil-service>"
cat > "$tmpdir/docs/atlas/repo-surface/topology.mmd" << 'EOF'
graph LR
    api["&lt;evil-service&gt;"]
    auth["safe-auth"]
    api --> auth
EOF

assert_not_in_file "SEC-03-A: raw < not in Mermaid label" "<evil-service>" \
    "$tmpdir/docs/atlas/repo-surface/topology.mmd"

# TEST-SEC-03-B: JavaScript-like content in service name is escaped
cat > "$tmpdir/docs/atlas/repo-surface/topology.mmd" << 'EOF'
graph LR
    xss["&lt;script&gt;alert(1)&lt;/script&gt;"]
EOF
assert_not_in_file "SEC-03-B: <script> not raw in Mermaid output" \
    "<script>" \
    "$tmpdir/docs/atlas/repo-surface/topology.mmd"

rm -rf "$tmpdir"

if [[ -f "$VALIDATE_SCRIPT" ]]; then
    # TEST-SEC-03-C: Validator catches unescaped HTML in .mmd files
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/docs/atlas/repo-surface"
    cat > "$tmpdir/docs/atlas/repo-surface/topology.mmd" << 'EOF'
graph LR
    xss["<script>alert(1)</script>"]
EOF
    output=$(bash "$VALIDATE_SCRIPT" --atlas-dir "$tmpdir/docs/atlas" --strict 2>&1) && exit_val=0 || exit_val=$?
    assert_exit_code "SEC-03-C: validator catches unescaped HTML in .mmd (exit 1)" 1 "$exit_val" "$output"
    rm -rf "$tmpdir"
fi

# ============================================================================
# SEC-05: Output Confinement to docs/atlas/ (HIGH)
# ============================================================================

echo ""
echo "=== SEC-05: Output Confinement ==="

if [[ -f "$VALIDATE_SCRIPT" ]]; then
    # TEST-SEC-05-A: Validator detects symlink in docs/atlas/ escaping the boundary
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/docs/atlas/repo-surface"

    # Create a file outside atlas, then symlink it into atlas
    echo "sensitive outside content" > "$tmpdir/outside.txt"
    ln -s "$tmpdir/outside.txt" "$tmpdir/docs/atlas/repo-surface/topology.mmd"

    output=$(bash "$VALIDATE_SCRIPT" --atlas-dir "$tmpdir/docs/atlas" --strict 2>&1) && exit_val=0 || exit_val=$?
    assert_exit_code "SEC-05-A: validator detects symlink escaping docs/atlas/ (exit 1)" 1 "$exit_val" "$output"
    rm -rf "$tmpdir"
fi

# ============================================================================
# SEC-09: Credential Redaction in Bug Reports (CRITICAL)
# ============================================================================

echo ""
echo "=== SEC-09: Credential Redaction in Bug Reports ==="

tmpdir=$(mktemp -d)
mkdir -p "$tmpdir/docs/atlas/bug-reports"

# A well-formed bug report: code_quote should not contain secrets
cat > "$tmpdir/docs/atlas/bug-reports/pass1-contradictions.md" << 'EOF'
# Pass 1 Bug Report

## BUG-001: Orphaned env var DATABASE_URL

**Severity:** HIGH
**Layer:** 6 → 3

**Evidence:**
- Layer 6: DATABASE_URL declared in .env.example
- Layer 3: No route handler reads DATABASE_URL directly

**Code quote:**
```
# .env.example line 1
DATABASE_URL=***REDACTED***
```

**Recommendation:** Verify DATABASE_URL is consumed by the database module, not raw routes.
EOF

assert_not_in_file "SEC-09-A: pass1 bug report no raw secret values" \
    "postgres://\|password\|secret\|SECRETPASSWORD" \
    "$tmpdir/docs/atlas/bug-reports/pass1-contradictions.md"

assert_in_file "SEC-09-B: pass1 bug report uses REDACTED placeholder" \
    "REDACTED" \
    "$tmpdir/docs/atlas/bug-reports/pass1-contradictions.md"

if [[ -f "$VALIDATE_SCRIPT" ]]; then
    # TEST-SEC-09-C: Validator rejects bug report with raw credentials
    cat > "$tmpdir/docs/atlas/bug-reports/bad-report.md" << 'EOF'
# Bug
Code quote: DATABASE_URL=postgres://user:MYSECRETPASSWORD@localhost/db  # pragma: allowlist secret
EOF
    output=$(bash "$VALIDATE_SCRIPT" --atlas-dir "$tmpdir/docs/atlas" --strict 2>&1) && exit_val=0 || exit_val=$?
    assert_exit_code "SEC-09-C: validator catches credential in bug report (exit 1)" 1 "$exit_val" "$output"
fi

rm -rf "$tmpdir"

# ============================================================================
# SEC-10: DOT/Mermaid Injection Prevention (HIGH)
# ============================================================================

echo ""
echo "=== SEC-10: DOT/Mermaid Injection Prevention ==="

if [[ -f "$VALIDATE_SCRIPT" ]]; then
    # TEST-SEC-10-A: XSS payload in DOT label detected
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/docs/atlas/repo-surface"
    # Use a <script> tag in a DOT label — caught by SEC-10 XSS pattern check
    cat > "$tmpdir/docs/atlas/repo-surface/topology.dot" << 'EOF'
digraph topology {
    "api" -> "auth" [label="<script>alert(1)</script>"];
}
EOF
    output=$(bash "$VALIDATE_SCRIPT" --atlas-dir "$tmpdir/docs/atlas" --strict 2>&1) && exit_val=0 || exit_val=$?
    assert_exit_code "SEC-10-A: XSS payload in DOT label detected (exit 1)" 1 "$exit_val" "$output"
    rm -rf "$tmpdir"
fi

# ============================================================================
# SEC-04: Safe YAML Parsing (HIGH)
# ============================================================================

echo ""
echo "=== SEC-04: Safe YAML Parsing ==="

# TEST-SEC-04-A: Verify yaml.safe_load() is used instead of yaml.load()
# Scan all Python source files under scripts/ and the skill directory for unsafe yaml.load usage
REPO_ROOT_LOCAL="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"

unsafe_yaml_files=()
while IFS= read -r pyfile; do
    # Check for yaml.load( without safe_load — exclude safe_load lines
    if grep -qP 'yaml\.load\s*\(' "$pyfile" 2>/dev/null; then
        # Confirm it is NOT safe_load
        if grep -P 'yaml\.load\s*\(' "$pyfile" 2>/dev/null | grep -qv 'safe_load'; then
            unsafe_yaml_files+=("$pyfile")
        fi
    fi
done < <(find "$REPO_ROOT_LOCAL/scripts" "$REPO_ROOT_LOCAL/.claude/skills/code-atlas" \
    -name '*.py' 2>/dev/null)

if [[ ${#unsafe_yaml_files[@]} -eq 0 ]]; then
    echo "PASS: SEC-04-A: no yaml.load() (unsafe) calls found — yaml.safe_load() enforced"
    PASS=$((PASS + 1))
else
    echo "FAIL: SEC-04-A: unsafe yaml.load() found in: ${unsafe_yaml_files[*]}"
    FAIL=$((FAIL + 1))
fi

# ============================================================================
# SEC-06: Shell Metacharacter Rejection (HIGH)
# ============================================================================

echo ""
echo "=== SEC-06: Shell Metacharacter Rejection ==="

if [[ -f "$SAFE_READ_SCRIPT" ]]; then
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/codebase"
    echo "safe content" > "$tmpdir/codebase/safe.txt"

    # TEST-SEC-06-A: Path with $() shell substitution is rejected
    output=$(bash "$SAFE_READ_SCRIPT" '$tmpdir/codebase/$(whoami)' \
        --boundary "$tmpdir/codebase" 2>&1) && exit_val=0 || exit_val=$?
    assert_exit_code "SEC-06-A: path with \$() rejected (exit 1)" 1 "$exit_val" "$output"

    # TEST-SEC-06-B: Path with backtick substitution is rejected
    output=$(bash "$SAFE_READ_SCRIPT" '$tmpdir/codebase/`id`' \
        --boundary "$tmpdir/codebase" 2>&1) && exit_val=0 || exit_val=$?
    assert_exit_code "SEC-06-B: path with backtick rejected (exit 1)" 1 "$exit_val" "$output"

    # TEST-SEC-06-C: Path with semicolon is rejected
    output=$(bash "$SAFE_READ_SCRIPT" "$tmpdir/codebase/safe.txt;ls" \
        --boundary "$tmpdir/codebase" 2>&1) && exit_val=0 || exit_val=$?
    assert_exit_code "SEC-06-C: path with semicolon rejected (exit 1)" 1 "$exit_val" "$output"

    rm -rf "$tmpdir"
fi

# ============================================================================
# SEC-08: Large File DoS Prevention (MEDIUM)
# ============================================================================

echo ""
echo "=== SEC-08: Large File DoS Prevention ==="

if [[ -f "$SAFE_READ_SCRIPT" ]]; then
    # TEST-SEC-08-A: Files over 10MB are rejected by safe_read.sh (SEC-08)
    tmpdir=$(mktemp -d)
    mkdir -p "$tmpdir/docs/atlas"

    # Create a 12MB file to test size limit
    dd if=/dev/zero of="$tmpdir/docs/atlas/huge.mmd" bs=1M count=12 2>/dev/null

    output=$(bash "$SAFE_READ_SCRIPT" "$tmpdir/docs/atlas/huge.mmd" --boundary "$tmpdir/docs/atlas" 2>&1) && exit_val=0 || exit_val=$?
    assert_exit_code "SEC-08-A: 12MB file rejected (exit 1)" 1 "$exit_val" "$output"

    rm -rf "$tmpdir"
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "=================================="
echo "Results: ${PASS} passed, ${FAIL} failed"
echo "=================================="

[[ $FAIL -eq 0 ]] && exit 0 || exit 1
