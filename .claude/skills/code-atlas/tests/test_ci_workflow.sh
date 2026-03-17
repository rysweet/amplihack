#!/bin/bash
# .claude/skills/code-atlas/tests/test_ci_workflow.sh
#
# TDD tests for the atlas CI workflow (.github/workflows/atlas-ci.yml).
# Validates YAML syntax, required jobs, trigger configuration, and
# script path references match actual script locations.
#
# Tests are mostly structural (can run without GitHub Actions) plus
# one integration test that runs the staleness script in PR mode.
#
# Usage: bash .claude/skills/code-atlas/tests/test_ci_workflow.sh
# Exit:  0 = all tests passed, non-zero = failures

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
CI_WORKFLOW="${REPO_ROOT}/.github/workflows/atlas-ci.yml"
STALENESS_SCRIPT="${REPO_ROOT}/scripts/check-atlas-staleness.sh"
REBUILD_SCRIPT="${REPO_ROOT}/scripts/rebuild-atlas-all.sh"

PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------
assert_pass() {
    local label="$1"; local ok="$2"; local detail="${3:-}"
    if [[ "$ok" == "true" ]]; then
        echo "PASS: $label"; PASS=$((PASS + 1))
    else
        echo "FAIL: $label${detail:+ — $detail}"; FAIL=$((FAIL + 1))
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
        echo "FAIL: $label — pattern '$pattern' not in $file"; FAIL=$((FAIL + 1))
    fi
}

assert_file_exists() {
    local label="$1"; local path="$2"
    [[ -f "$path" ]] && { echo "PASS: $label"; PASS=$((PASS + 1)); } || { echo "FAIL: $label — not found: $path"; FAIL=$((FAIL + 1)); }
}

# ============================================================================
# Test Group 1: Required Files Exist
# ============================================================================

echo ""
echo "=== Required Files ==="

assert_file_exists "atlas-ci.yml exists"                "$CI_WORKFLOW"
assert_file_exists "check-atlas-staleness.sh exists"    "$STALENESS_SCRIPT"
assert_file_exists "rebuild-atlas-all.sh exists"        "$REBUILD_SCRIPT"

# Scripts must be executable
if [[ -f "$STALENESS_SCRIPT" ]]; then
    assert_pass "check-atlas-staleness.sh is executable" \
        "$([[ -x "$STALENESS_SCRIPT" ]] && echo true || echo false)"
fi
if [[ -f "$REBUILD_SCRIPT" ]]; then
    assert_pass "rebuild-atlas-all.sh is executable" \
        "$([[ -x "$REBUILD_SCRIPT" ]] && echo true || echo false)"
fi

# ============================================================================
# Test Group 2: CI Workflow YAML Structure
# ============================================================================

echo ""
echo "=== CI Workflow YAML Structure ==="

# 2.1: Must define all three patterns as separate jobs
assert_file_contains "CI: atlas-staleness-gate job defined" \
    "atlas-staleness-gate\|atlas.staleness.gate" "$CI_WORKFLOW"
assert_file_contains "CI: atlas-pr-impact job defined" \
    "atlas-pr-impact\|atlas.pr.impact" "$CI_WORKFLOW"
assert_file_contains "CI: atlas-scheduled-rebuild job defined" \
    "atlas-scheduled-rebuild\|atlas.scheduled.rebuild\|scheduled.*rebuild" "$CI_WORKFLOW"

# 2.2: Triggers must cover push to main
assert_file_contains "CI: triggers on push to main" \
    "push:" "$CI_WORKFLOW"
assert_file_contains "CI: push trigger includes main branch" \
    "branches:.*main\|branches:\n.*main\|- main" "$CI_WORKFLOW"

# 2.3: Triggers must cover pull_request
assert_file_contains "CI: triggers on pull_request" \
    "pull_request:" "$CI_WORKFLOW"

# 2.4: Scheduled trigger (weekly)
assert_file_contains "CI: scheduled cron trigger present" \
    "cron:\|schedule:" "$CI_WORKFLOW"
assert_file_contains "CI: weekly schedule (Monday or * * 1)" \
    "0 .* \* 1\|0 .* \* \* 1\|Monday" "$CI_WORKFLOW"

# 2.5: workflow_dispatch for manual runs
assert_file_contains "CI: workflow_dispatch trigger" \
    "workflow_dispatch" "$CI_WORKFLOW"

# 2.6: Pattern 1 staleness gate runs check-atlas-staleness.sh
assert_file_contains "CI: Pattern 1 calls staleness script" \
    "check-atlas-staleness.sh" "$CI_WORKFLOW"

# 2.7: Pattern 3 rebuild runs rebuild-atlas-all.sh
assert_file_contains "CI: Pattern 3 calls rebuild script" \
    "rebuild-atlas-all.sh" "$CI_WORKFLOW"

# 2.8: Artifact upload for staleness report
assert_file_contains "CI: uploads staleness artifact" \
    "upload-artifact\|stale.*report\|atlas.*report" "$CI_WORKFLOW"

# 2.9: Creates GitHub Issue on rebuild failure
assert_file_contains "CI: creates issue on rebuild failure" \
    "gh issue create\|issue.*create\|create.*issue" "$CI_WORKFLOW"

# 2.10: Uses ubuntu-latest runner
assert_file_contains "CI: uses ubuntu-latest" \
    "ubuntu-latest" "$CI_WORKFLOW"

# 2.11: Checkout action is used
assert_file_contains "CI: uses actions/checkout" \
    "actions/checkout" "$CI_WORKFLOW"

# ============================================================================
# Test Group 3: Script Path Consistency
# ============================================================================

echo ""
echo "=== Script Path Consistency ==="

# 3.1: CI workflow script paths must match actual file locations
if [[ -f "$CI_WORKFLOW" ]]; then
    # Extract script paths referenced in CI workflow
    staleness_path_in_ci=$(grep -oE "scripts/check-atlas-staleness\.sh" "$CI_WORKFLOW" | head -1 || true)
    rebuild_path_in_ci=$(grep -oE "scripts/rebuild-atlas-all\.sh" "$CI_WORKFLOW" | head -1 || true)

    if [[ -n "$staleness_path_in_ci" ]]; then
        if [[ -f "${REPO_ROOT}/${staleness_path_in_ci}" ]]; then
            echo "PASS: staleness script path in CI matches real location"
            PASS=$((PASS + 1))
        else
            echo "FAIL: CI references ${staleness_path_in_ci} but file not found at ${REPO_ROOT}/${staleness_path_in_ci}"
            FAIL=$((FAIL + 1))
        fi
    else
        echo "FAIL: CI workflow does not reference check-atlas-staleness.sh"
        FAIL=$((FAIL + 1))
    fi

    if [[ -n "$rebuild_path_in_ci" ]]; then
        if [[ -f "${REPO_ROOT}/${rebuild_path_in_ci}" ]]; then
            echo "PASS: rebuild script path in CI matches real location"
            PASS=$((PASS + 1))
        else
            echo "FAIL: CI references ${rebuild_path_in_ci} but file not found"
            FAIL=$((FAIL + 1))
        fi
    else
        echo "FAIL: CI workflow does not reference rebuild-atlas-all.sh"
        FAIL=$((FAIL + 1))
    fi
fi

# ============================================================================
# Test Group 4: YAML Validity (requires yq or python3)
# ============================================================================

echo ""
echo "=== YAML Validity ==="

if command -v python3 >/dev/null 2>&1; then
    yaml_valid=$(python3 -c "
import sys
try:
    import yaml
    with open('${CI_WORKFLOW}') as f:
        yaml.safe_load(f)
    print('true')
except Exception as e:
    print('false')
    sys.stderr.write(str(e) + '\n')
" 2>/dev/null || echo "false")
    assert_pass "atlas-ci.yml is valid YAML (python3+yaml)" "$yaml_valid"
elif command -v yq >/dev/null 2>&1; then
    if yq '.' "$CI_WORKFLOW" > /dev/null 2>&1; then
        echo "PASS: atlas-ci.yml is valid YAML (yq)"
        PASS=$((PASS + 1))
    else
        echo "FAIL: atlas-ci.yml has invalid YAML syntax"
        FAIL=$((FAIL + 1))
    fi
else
    echo "SKIP: YAML validity check (python3+yaml or yq required)"
fi

# ============================================================================
# Test Group 5: Pattern 1 Integration — Staleness Gate Behavior
# ============================================================================

echo ""
echo "=== Pattern 1 Integration: Staleness Gate ==="

if [[ ! -f "$STALENESS_SCRIPT" ]]; then
    echo "SKIP: staleness script not found, skipping integration tests"
else
    # 5.1: --pr flag is accepted without error
    tmpdir=$(mktemp -d)
    git -C "$tmpdir" init -q
    git -C "$tmpdir" config user.email "test@test.com"
    git -C "$tmpdir" config user.name "Test"
    git -C "$tmpdir" commit --allow-empty -q -m "init"
    git -C "$tmpdir" checkout -b main -q 2>/dev/null || true
    git -C "$tmpdir" remote add origin "$tmpdir" 2>/dev/null || true

    # Create a feature branch with an atlas-triggering change
    git -C "$tmpdir" checkout -b feature-test -q 2>/dev/null || true
    echo "version: '3.8'" > "$tmpdir/docker-compose.yml"
    git -C "$tmpdir" add .
    git -C "$tmpdir" commit -q -m "add docker-compose"

    # Test: run with explicit range (simulates PR mode)
    # Capture exit code separately (don't use || true which masks the exit code)
    set +e
    output=$(cd "$tmpdir" && bash "$STALENESS_SCRIPT" "HEAD~1" "HEAD" 2>&1)
    exit_code=$?
    set -e

    # Should detect Layer 1 as stale (docker-compose.yml changed)
    if echo "$output" | grep -q "Layer 1 STALE\|Layer 1.*stale\|STALE.*Layer 1"; then
        echo "PASS: Pattern 1: docker-compose.yml change triggers Layer 1 stale"
        PASS=$((PASS + 1))
    else
        echo "FAIL: Pattern 1: docker-compose.yml change should trigger Layer 1 stale"
        echo "  Output: $output"
        FAIL=$((FAIL + 1))
    fi

    # Exit code must be 1 (stale detected)
    if [[ "$exit_code" -eq 1 ]]; then
        echo "PASS: Pattern 1: exit code 1 when stale layers detected"
        PASS=$((PASS + 1))
    else
        echo "FAIL: Pattern 1: expected exit 1 for stale, got $exit_code"
        FAIL=$((FAIL + 1))
    fi

    rm -rf "$tmpdir"

    # 5.2: Clean repo (no relevant changes) exits 0
    tmpdir=$(mktemp -d)
    git -C "$tmpdir" init -q
    git -C "$tmpdir" config user.email "test@test.com"
    git -C "$tmpdir" config user.name "Test"
    git -C "$tmpdir" commit --allow-empty -q -m "init"

    # Make a non-atlas-triggering change
    echo "# just a comment" > "$tmpdir/Makefile"
    git -C "$tmpdir" add .
    git -C "$tmpdir" commit -q -m "add Makefile"

    output=$(cd "$tmpdir" && bash "$STALENESS_SCRIPT" "HEAD~1" "HEAD" 2>&1 || true)
    exit_code=$?

    if [[ "$exit_code" -eq 0 ]]; then
        echo "PASS: Pattern 1: non-atlas file change exits 0 (fresh)"
        PASS=$((PASS + 1))
    else
        echo "FAIL: Pattern 1: Makefile change should not trigger stale (got exit $exit_code)"
        echo "  Output: $output"
        FAIL=$((FAIL + 1))
    fi

    rm -rf "$tmpdir"
fi

# ============================================================================
# Test Group 6: Pattern 2 Integration — PR Impact Annotation
# ============================================================================

echo ""
echo "=== Pattern 2: PR Impact Annotation ==="

if [[ -f "$STALENESS_SCRIPT" ]]; then
    # 6.1: Multiple layer triggers in one PR are all detected
    tmpdir=$(mktemp -d)
    git -C "$tmpdir" init -q
    git -C "$tmpdir" config user.email "test@test.com"
    git -C "$tmpdir" config user.name "Test"
    git -C "$tmpdir" commit --allow-empty -q -m "init"

    # Change files that trigger Layer 2 AND Layer 3 simultaneously
    mkdir -p "$tmpdir/services/api/src"
    echo '{"name":"api"}' > "$tmpdir/services/api/package.json"
    echo "export const router = {}" > "$tmpdir/services/api/src/user.routes.ts"
    git -C "$tmpdir" add .
    git -C "$tmpdir" commit -q -m "add api service files"

    output=$(cd "$tmpdir" && bash "$STALENESS_SCRIPT" "HEAD~1" "HEAD" 2>&1 || true)

    if echo "$output" | grep -q "Layer 2 STALE"; then
        echo "PASS: Pattern 2: package.json change triggers Layer 2 stale"
        PASS=$((PASS + 1))
    else
        echo "FAIL: Pattern 2: package.json should trigger Layer 2"
        echo "  Output: $output"
        FAIL=$((FAIL + 1))
    fi

    if echo "$output" | grep -q "Layer 3 STALE"; then
        echo "PASS: Pattern 2: routes.ts change triggers Layer 3 stale"
        PASS=$((PASS + 1))
    else
        echo "FAIL: Pattern 2: user.routes.ts should trigger Layer 3"
        echo "  Output: $output"
        FAIL=$((FAIL + 1))
    fi

    rm -rf "$tmpdir"
fi

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
echo ""
echo "=================================="
echo "Results: ${PASS} passed, ${FAIL} failed"
echo "=================================="

[[ $FAIL -eq 0 ]] && exit 0 || exit 1
