#!/bin/bash
# .claude/skills/code-atlas/tests/test_bug_hunt_workflow.sh
#
# TDD tests for the three-pass bug-hunting workflow.
# Tests validate that the bug-hunt workflow produces structured, evidence-backed
# bug reports with the correct format and without security violations.
#
# Pass 1: Contradiction hunt — find route/DTO mismatches, orphaned env vars, dead paths
# Pass 2: Fresh-eyes cross-check — independent re-examination + confirm/overturn Pass 1 findings
# Pass 3: Scenario deep-dive — per-journey PASS/FAIL/NEEDS_ATTENTION verdicts
#
# THESE TESTS WILL FAIL until the bug-hunt workflow is implemented.
#
# Usage: bash .claude/skills/code-atlas/tests/test_bug_hunt_workflow.sh
# Exit:  0 = all tests passed, non-zero = failures

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"

PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------
assert_contains() {
    local label="$1"; local pattern="$2"; local content="$3"
    if echo "$content" | grep -q "$pattern"; then
        echo "PASS: $label"; PASS=$((PASS + 1))
    else
        echo "FAIL: $label — pattern '$pattern' not found"
        echo "  Content preview: ${content:0:200}"
        FAIL=$((FAIL + 1))
    fi
}

assert_file_contains() {
    local label="$1"; local pattern="$2"; local file="$3"
    if [[ ! -f "$file" ]]; then
        echo "FAIL: $label — file not found: $file"; FAIL=$((FAIL + 1)); return
    fi
    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo "PASS: $label"; PASS=$((PASS + 1))
    else
        echo "FAIL: $label — '$pattern' not in $file"; FAIL=$((FAIL + 1))
    fi
}

assert_not_in_file() {
    local label="$1"; local pattern="$2"; local file="$3"
    if [[ ! -f "$file" ]]; then
        echo "FAIL: $label — file not found: $file"; FAIL=$((FAIL + 1)); return
    fi
    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo "FAIL: $label — forbidden '$pattern' found in $file"; FAIL=$((FAIL + 1))
    else
        echo "PASS: $label"; PASS=$((PASS + 1))
    fi
}

# ---------------------------------------------------------------------------
# Bug Report Format Contract
# ---------------------------------------------------------------------------
# Every bug report entry must conform to this structure:
#
#   ## BUG-NNN: Short description
#   **Severity:** CRITICAL | HIGH | MEDIUM | LOW
#   **Layer:** X → Y  (where detected, from which layer context)
#   **Evidence:**
#   - Layer N: <observation>
#   - Layer M: <observation>
#   **Code quote:**
#   ```
#   <actual code from codebase>
#   ```
#   **Recommendation:** <actionable fix>
# ---------------------------------------------------------------------------

ATLAS="${REPO_ROOT}/docs/atlas"
P1_REPORT="${ATLAS}/bug-reports/mermaid-arm/pass1-findings.md"
P2_REPORT="${ATLAS}/bug-reports/graphviz-arm/pass1-findings.md"

# ============================================================================
# Test Group 1: Bug Report Schema Validation
# ============================================================================

echo ""
echo "=== Bug Report Schema Tests ==="

validate_bug_report_schema() {
    local report_file="$1"
    local report_name="$2"

    if [[ ! -f "$report_file" ]]; then
        echo "FAIL: $report_name — file does not exist: $report_file"
        FAIL=$((FAIL + 6))
        return
    fi

    # 1.1: Must have at least one BUG entry header
    bug_count=$(grep -cE "^## BUG-[0-9]+" "$report_file" 2>/dev/null || echo 0)
    if [[ "$bug_count" -ge 1 ]]; then
        echo "PASS: $report_name — has $bug_count BUG-NNN entries"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $report_name — no BUG-NNN entries found (need ## BUG-001 format)"
        FAIL=$((FAIL + 1))
    fi

    # 1.2: Every BUG entry must have Severity
    severity_count=$(grep -cE "\*\*Severity:\*\*" "$report_file" 2>/dev/null || echo 0)
    if [[ "$severity_count" -ge "$bug_count" && "$bug_count" -gt 0 ]]; then
        echo "PASS: $report_name — all $bug_count bugs have Severity field"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $report_name — $severity_count Severity fields for $bug_count bugs"
        FAIL=$((FAIL + 1))
    fi

    # 1.3: Severity values must be valid
    assert_file_contains "$report_name: has valid severity level" \
        "Severity.*\(CRITICAL\|HIGH\|MEDIUM\|LOW\)" "$report_file"

    # 1.4: Must have Evidence fields
    evidence_count=$(grep -cE "\*\*Evidence:\*\*|\*\*Code quote:\*\*" "$report_file" 2>/dev/null || echo 0)
    if [[ "$evidence_count" -ge "$bug_count" && "$bug_count" -gt 0 ]]; then
        echo "PASS: $report_name — all bugs have Evidence/Code quote"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $report_name — $evidence_count evidence sections for $bug_count bugs"
        FAIL=$((FAIL + 1))
    fi

    # 1.5: Must have Recommendation fields
    rec_count=$(grep -cE "\*\*Recommendation:\*\*" "$report_file" 2>/dev/null || echo 0)
    if [[ "$rec_count" -ge "$bug_count" && "$bug_count" -gt 0 ]]; then
        echo "PASS: $report_name — all bugs have Recommendation"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $report_name — $rec_count Recommendations for $bug_count bugs"
        FAIL=$((FAIL + 1))
    fi

    # 1.6: SEC-09 — no raw secret values in code quotes
    assert_not_in_file "$report_name SEC-09: no raw passwords" \
        "password\s*=\s*[a-zA-Z0-9!@#$%^&*]\{4,\}" "$report_file"
    assert_not_in_file "$report_name SEC-09: no connection strings with passwords" \
        "://.*:.*@" "$report_file"
}

validate_bug_report_schema "$P1_REPORT" "mermaid-arm-findings"
validate_bug_report_schema "$P2_REPORT" "graphviz-arm-findings"

# ============================================================================
# Test Group 2: Pass 1 Contradiction Hunt — Specific Detections
# ============================================================================

echo ""
echo "=== Pass 1: Specific Contradiction Detections ==="

# CONTRACT: The Go fixture has these known contradictions to detect:
# - user_model.go declares Password field with json:"-" (hidden in API but visible in code)
# - .env.example has JWT_SECRET but no route handler explicitly reads JWT_SECRET
# - CreateUserRequest requires 3 fields but POST /api/users doesn't validate them explicitly

# 2.1: Test that route/DTO mismatch detection produces entries in Pass 1 report
# This simulates a codebase where a route expects a DTO that doesn't exist yet
tmpdir=$(mktemp -d)
mkdir -p "$tmpdir/docs/atlas/bug-reports"

# Create a pass1 report that correctly identifies a route/DTO mismatch
cat > "$tmpdir/docs/atlas/bug-reports/mermaid-arm/pass1-findings.md" << 'EOF'
# Pass 1 Bug Report — Contradiction Hunt

Generated: 2026-03-16T10:00:00Z

## BUG-001: Route POST /api/orders references missing OrderRequest DTO

**Severity:** HIGH
**Layer:** 3 → 4

**Evidence:**
- Layer 3 (route-inventory.md line 12): `POST /api/orders → handler CreateOrder`
- Layer 4 (dataflow.mmd): No `OrderRequest` or `CreateOrderRequest` struct found

**Code quote:**
```go
// internal/handlers/order_handler.go line 23
r.POST("/api/orders", CreateOrder)
```

**Recommendation:** Create `internal/models/order_model.go` with `CreateOrderRequest` struct,
or update the route handler to reference an existing DTO.

## BUG-002: Orphaned env var PAYMENT_SECRET not consumed by any handler

**Severity:** MEDIUM
**Layer:** 6 → 3

**Evidence:**
- Layer 6 (env-vars.md line 5): `PAYMENT_SECRET` declared in .env.example
- Layer 3 (route-inventory.md): No handler references `PAYMENT_SECRET` or payment routes

**Code quote:**
```
# .env.example line 5
PAYMENT_SECRET=***REDACTED***
```

**Recommendation:** Either add a payment route/handler that consumes PAYMENT_SECRET,
or remove it from .env.example if the payment feature is not implemented.
EOF

validate_bug_report_schema "$tmpdir/docs/atlas/bug-reports/mermaid-arm/pass1-findings.md" "fixture-mermaid-arm"

# 2.2: Route/DTO mismatch is the primary Pass 1 contradiction type
assert_file_contains "P1 fixture: route/DTO mismatch detected" \
    "[Rr]oute.*[Mm]issing\|DTO.*not found\|route.*DTO\|missing.*DTO\|[Mm]ismatch" \
    "$tmpdir/docs/atlas/bug-reports/mermaid-arm/pass1-findings.md"

# 2.3: Orphaned env var detection
assert_file_contains "P1 fixture: orphaned env var detected" \
    "[Oo]rphan\|env.*var.*not.*consumed\|PAYMENT_SECRET" \
    "$tmpdir/docs/atlas/bug-reports/mermaid-arm/pass1-findings.md"

# 2.4: Values are redacted in evidence
assert_not_in_file "P1 fixture SEC-09: no raw secret values" \
    "payment-secret-value\|real-secret-here" \
    "$tmpdir/docs/atlas/bug-reports/mermaid-arm/pass1-findings.md"

rm -rf "$tmpdir"

# ============================================================================
# Test Group 3: Pass 2 Journey Trace — Specific Journey Coverage
# ============================================================================

echo ""
echo "=== Pass 2: Journey Trace Coverage ==="

tmpdir=$(mktemp -d)
mkdir -p "$tmpdir/docs/atlas/bug-reports"

# Create a well-formed pass2 report
cat > "$tmpdir/docs/atlas/bug-reports/graphviz-arm/pass1-findings.md" << 'EOF'
# Pass 2 Bug Report — User Journey Trace

Generated: 2026-03-16T10:05:00Z

## Journey: User Registration

Steps traced through atlas layers:
1. User submits POST /api/users (Layer 3: route)
2. Handler calls CreateUser function (Layer 3: handler)
3. CreateUserRequest deserialized (Layer 4: DTO)
4. User struct created and stored (Layer 4: model)

## BUG-003: CreateUserRequest.Password validation bypassed in test route

**Severity:** HIGH
**Layer:** 3 → 4 (journey: User Registration, step 3)

**Evidence:**
- Layer 4 (user_model.go): CreateUserRequest has `binding:"required"` on Password
- Layer 3 (user_handler.go test route): A test endpoint POST /api/test-users skips binding validation
- Journey trace: Registration journey step 3 can succeed without password via test endpoint

**Code quote:**
```go
// internal/handlers/test_handler.go line 8
r.POST("/api/test-users", func(c *gin.Context) {
    // NOTE: No binding validation - allows empty password
    var u models.User
    c.BindJSON(&u)
    c.JSON(201, u)
})
```

**Recommendation:** Remove POST /api/test-users from production code or add equivalent validation.

## Journey: User Listing (Admin)

Steps traced:
1. Client sends GET /api/users (Layer 3: route)
2. ListUsers handler returns all users (Layer 3: handler)
3. User struct serialized to JSON (Layer 4: model)

## BUG-004: User.Password field exposed via JSON serialization despite json:"-" tag

**Severity:** CRITICAL
**Layer:** 4 → 3 (journey: User Listing, step 3)

**Evidence:**
- Layer 4 (user_model.go): User.Password has json:"-" tag (excluded from JSON)
- Layer 4 (dataflow.mmd): ListUsers returns []User, which includes Password
- Journey trace: GET /api/users response includes Password field in some test configurations

**Code quote:**
```go
// internal/models/user_model.go line 7
Password string `json:"-"`  // Should be excluded from JSON responses
```

**Recommendation:** Verify Password is excluded in all serialization paths. Add integration test
asserting Password field is absent from GET /api/users response body.
EOF

validate_bug_report_schema "$tmpdir/docs/atlas/bug-reports/graphviz-arm/pass1-findings.md" "fixture-graphviz-arm"

# 3.1: Pass 2 must reference journey names
assert_file_contains "P2: references journey names" \
    "[Jj]ourney:\|[Ss]cenario:" \
    "$tmpdir/docs/atlas/bug-reports/graphviz-arm/pass1-findings.md"

# 3.2: Pass 2 must trace steps through layers
assert_file_contains "P2: traces steps through layers" \
    "[Ss]tep.*Layer\|Layer.*step\|journey.*step\|[Ss]teps traced" \
    "$tmpdir/docs/atlas/bug-reports/graphviz-arm/pass1-findings.md"

# 3.3: Pass 2 bugs must reference the originating journey
assert_file_contains "P2: BUG entries reference journey" \
    "journey:\|[Ss]cenario:" \
    "$tmpdir/docs/atlas/bug-reports/graphviz-arm/pass1-findings.md"

# 3.4: Layer references in Pass 2 must be in format "Layer N → M"
assert_file_contains "P2: layer cross-references" \
    "Layer [1-6].*→.*[1-6]\|[1-6] → [1-6]" \
    "$tmpdir/docs/atlas/bug-reports/graphviz-arm/pass1-findings.md"

rm -rf "$tmpdir"

# ============================================================================
# Test Group 4: Bug Hunt Completeness Checks
# ============================================================================

echo ""
echo "=== Bug Hunt Completeness ==="

# 4.1: Both pass reports must exist after a full atlas run
if [[ -f "$P1_REPORT" ]] && [[ -f "$P2_REPORT" ]]; then
    echo "PASS: both pass reports exist"
    PASS=$((PASS + 1))
else
    missing=""
    [[ ! -f "$P1_REPORT" ]] && missing="mermaid-arm-findings.md"
    [[ ! -f "$P2_REPORT" ]] && missing="$missing graphviz-arm-findings.md"
    echo "FAIL: missing bug reports:$missing"
    FAIL=$((FAIL + 1))
fi

# 4.2: Pass 1 must document the DETECTION METHODOLOGY
if [[ -f "$P1_REPORT" ]]; then
    assert_file_contains "P1: documents contradiction types checked" \
        "route.*DTO\|DTO.*route\|orphan\|dead.*path\|stale.*doc\|mismatch" "$P1_REPORT"
fi

# 4.3: Pass 2 must reference Pass 1 or follow-up on its findings
if [[ -f "$P2_REPORT" ]]; then
    # Pass 2 is journey-focused — it must trace specific routes
    assert_file_contains "P2: references specific routes or endpoints" \
        "/api/\|GET\|POST\|PUT\|DELETE" "$P2_REPORT"
fi

# ============================================================================
# Test Group 5: SKILL.md Protocol Compliance
# ============================================================================

echo ""
echo "=== Protocol Compliance ==="

SKILL="${REPO_ROOT}/.claude/skills/code-atlas/SKILL.md"

# 5.1: SKILL.md must define the two-pass structure
assert_file_contains "SKILL.md: Pass 1 defined" "[Pp]ass 1\|pass.1\|First pass" "$SKILL"
assert_file_contains "SKILL.md: Pass 2 defined" "[Pp]ass 2\|pass.2\|Second pass" "$SKILL"

# 5.2: SKILL.md must define contradiction types for Pass 1
assert_file_contains "SKILL.md: route/DTO mismatch mentioned" "route.*DTO\|DTO.*route\|mismatch\|contradict" "$SKILL"

# 5.3: SKILL.md must define user journey concept
assert_file_contains "SKILL.md: user journey concept defined" "[Uu]ser.*[Jj]ourney\|journey.*scenario\|scenario" "$SKILL"

# 5.4: SKILL.md must describe bug evidence format
assert_file_contains "SKILL.md: bug evidence format defined" "[Ee]vidence\|code.*quote\|code_quote" "$SKILL"

# 5.5: SECURITY.md must exist and mention secret redaction (SEC-01)
SECURITY="${REPO_ROOT}/.claude/skills/code-atlas/SECURITY.md"
assert_file_contains "SECURITY.md: SEC-01 secret redaction defined" "[Rr]edact\|REDACTED\|SEC-01" "$SECURITY"

# 5.6: SKILL.md must define three-pass structure (v1.1.0)
assert_file_contains "SKILL.md: Pass 3 defined" "[Pp]ass 3\|pass.3\|Pass 3" "$SKILL"

# 5.7: SKILL.md must define JourneyVerdict
assert_file_contains "SKILL.md: JourneyVerdict concept defined" "[Jj]ourney[Vv]erdict\|Journey.*Verdict\|PASS.*FAIL.*NEEDS_ATTENTION\|verdict.*journey" "$SKILL"

# 5.8: SKILL.md Pass 3 must document per-journey verdict block format
assert_file_contains "SKILL.md: verdict block format with PASS/FAIL/NEEDS_ATTENTION" "PASS | FAIL | NEEDS_ATTENTION\|PASS.*FAIL.*NEEDS_ATTENTION" "$SKILL"

# 5.9: API-CONTRACTS.md must have pass: 1 | 2 | 3 in BugReport schema
API_CONTRACTS="${REPO_ROOT}/.claude/skills/code-atlas/API-CONTRACTS.md"
assert_file_contains "API-CONTRACTS.md: BugReport pass extended to 1|2|3" "pass.*1.*2.*3\|1 | 2 | 3" "$API_CONTRACTS"

# ============================================================================
# Test Group 6: Pass 3 Verdict Block Tests (v1.1.0)
# ============================================================================

echo ""
echo "=== Pass 3 Verdict Block Tests (v1.1.0) ==="

ATLAS="${REPO_ROOT}/docs/atlas"
BUG_REPORTS="${ATLAS}/bug-reports"

# Cache pass3 file list once — avoids 5 redundant filesystem scans below.
mapfile -d '' _pass3_files < <(find "$BUG_REPORTS" -name "*pass3*" -print0 2>/dev/null)
pass3_count="${#_pass3_files[@]}"

# 6.1: At least one pass3 report file should exist (requires atlas run)
if [[ "$pass3_count" -gt 0 ]]; then
    echo "PASS: 6.1 at least one pass3 bug report exists ($pass3_count files)"
    PASS=$((PASS + 1))
else
    echo "FAIL: 6.1 no pass3 bug reports found in $BUG_REPORTS (run /code-atlas first)"
    FAIL=$((FAIL + 1))
fi

# 6.2–6.6: Per-file checks using the cached list.
for p3_file in "${_pass3_files[@]}"; do
    assert_file_contains "6.2 pass3 report has Journey heading: $(basename "$p3_file")" \
        "## Journey:" "$p3_file"

    assert_file_contains "6.3 pass3 report has Verdict: $(basename "$p3_file")" \
        "### Verdict:.*PASS\|### Verdict:.*FAIL\|### Verdict:.*NEEDS_ATTENTION" "$p3_file"

    assert_file_contains "6.4 pass3 report has status symbols: $(basename "$p3_file")" \
        "✅\|❌\|⚠️" "$p3_file"

    assert_file_contains "6.5 pass3 report has Verdict Rationale: $(basename "$p3_file")" \
        "\*\*Verdict Rationale:\*\*\|Verdict Rationale:" "$p3_file"

    if grep -q '^\| [^|]* \| [^|]* \| /' "$p3_file" 2>/dev/null; then
        echo "FAIL: 6.6 SEC-16 — absolute path found in pass3 evidence: $(basename "$p3_file")"
        FAIL=$((FAIL + 1))
    else
        echo "PASS: 6.6 SEC-16 — no absolute paths in evidence: $(basename "$p3_file")"
        PASS=$((PASS + 1))
    fi
done

# 6.7: SKILL.md Pass 3 documents scenario deep-dive methodology
assert_file_contains "6.7 SKILL.md Pass 3 documents scenario deep-dive" \
    "[Ss]cenario.*[Dd]eep-[Dd]ive\|deep-dive\|deep dive" "$SKILL"

# 6.8: API-CONTRACTS.md §4b contains JourneyVerdict schema
assert_file_contains "6.8 API-CONTRACTS.md §4b contains JourneyVerdict schema" \
    "JourneyVerdict\|journey_verdict" "$API_CONTRACTS"

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
echo ""
echo "=================================="
echo "Results: ${PASS} passed, ${FAIL} failed"
echo "=================================="
echo ""
echo "NOTE: Tests against live docs/atlas/ fail until /code-atlas is run."

[[ $FAIL -eq 0 ]] && exit 0 || exit 1
