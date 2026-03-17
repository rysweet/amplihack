#!/bin/bash
# test_staleness_triggers.sh
#
# Tests that check-atlas-staleness.sh correctly detects stale layers
# for all documented trigger patterns.
#
# Usage: bash .claude/skills/code-atlas/tests/test_staleness_triggers.sh
# Exit: 0 = all tests passed, 1 = one or more tests failed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
STALENESS_SCRIPT="${REPO_ROOT}/scripts/check-atlas-staleness.sh"

PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------
assert_layer_detected() {
    local test_name="$1"
    local expected_layer="$2"
    local changed_file="$3"

    # Create a temp git repo with a fake changed file to test pattern matching
    local tmpdir
    tmpdir=$(mktemp -d)
    cd "$tmpdir"
    git init -q
    git commit --allow-empty -m "init" -q

    # Stage a fake file change
    mkdir -p "$(dirname "$changed_file")"
    echo "test" > "$changed_file"
    git add .
    git commit -q -m "add $changed_file"

    # Run staleness check — should detect the expected layer
    output=$(bash "$STALENESS_SCRIPT" 2>&1 || true)

    if echo "$output" | grep -q "STALE:"; then
        echo "PASS: $test_name — Layer $expected_layer detected for $changed_file"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $test_name — Expected Layer $expected_layer stale for $changed_file"
        echo "  Output was: $output"
        FAIL=$((FAIL + 1))
    fi

    cd "$REPO_ROOT"
    rm -rf "$tmpdir"
}

assert_no_layer_detected() {
    local test_name="$1"
    local changed_file="$2"

    local tmpdir
    tmpdir=$(mktemp -d)
    cd "$tmpdir"
    git init -q
    git commit --allow-empty -m "init" -q

    mkdir -p "$(dirname "$changed_file")"
    echo "test" > "$changed_file"
    git add .
    git commit -q -m "add $changed_file"

    output=$(bash "$STALENESS_SCRIPT" 2>&1 || true)

    if echo "$output" | grep -q "STALE"; then
        echo "FAIL: $test_name — Unexpected stale detection for $changed_file"
        echo "  Output was: $output"
        FAIL=$((FAIL + 1))
    else
        echo "PASS: $test_name — No false positive for $changed_file"
        PASS=$((PASS + 1))
    fi

    cd "$REPO_ROOT"
    rm -rf "$tmpdir"
}

# ---------------------------------------------------------------------------
# Layer 1: Runtime Topology triggers
# ---------------------------------------------------------------------------
assert_layer_detected "Layer1: docker-compose.yml"      1 "docker-compose.yml"
assert_layer_detected "Layer1: docker-compose.override.yml" 1 "docker-compose.override.yml"
assert_layer_detected "Layer1: k8s manifest"            1 "k8s/deployment.yaml"
assert_layer_detected "Layer1: kubernetes manifest"     1 "kubernetes/service.yaml"
assert_layer_detected "Layer1: helm chart"              1 "helm/templates/deployment.yaml"

# ---------------------------------------------------------------------------
# Layer 2: Dependency triggers
# ---------------------------------------------------------------------------
assert_layer_detected "Layer2: go.mod"                  2 "go.mod"
assert_layer_detected "Layer2: nested go.mod"           2 "services/api/go.mod"
assert_layer_detected "Layer2: package.json"            2 "package.json"
assert_layer_detected "Layer2: nested package.json"     2 "services/web/package.json"
assert_layer_detected "Layer2: csproj"                  2 "MyApp.csproj"
assert_layer_detected "Layer2: Cargo.toml"              2 "Cargo.toml"
assert_layer_detected "Layer2: requirements.txt"        2 "requirements.txt"
assert_layer_detected "Layer2: pyproject.toml"          2 "pyproject.toml"

# ---------------------------------------------------------------------------
# Layer 3: API Contracts triggers (including previously undocumented patterns)
# ---------------------------------------------------------------------------
assert_layer_detected "Layer3: routes.ts"               3 "src/api/routes.ts"
assert_layer_detected "Layer3: route file"              3 "services/api/route_users.go"
assert_layer_detected "Layer3: controller (Go)"         3 "internal/controller_auth.go"
assert_layer_detected "Layer3: controller (TS)"         3 "src/controllers/user.controller.ts"
assert_layer_detected "Layer3: views.py"                3 "app/views.py"
assert_layer_detected "Layer3: router.ts"               3 "src/router.ts"
assert_layer_detected "Layer3: handler.go (was undocumented)" 3 "internal/user_handler.go"

# ---------------------------------------------------------------------------
# Layer 4: Data Flow triggers (including previously undocumented patterns)
# ---------------------------------------------------------------------------
assert_layer_detected "Layer4: dto.ts"                  4 "src/dtos/user.dto.ts"
assert_layer_detected "Layer4: schema.py"               4 "app/schemas.py"
assert_layer_detected "Layer4: _request.go"             4 "internal/auth/login_request.go"
assert_layer_detected "Layer4: _response.go"            4 "internal/auth/login_response.go"
assert_layer_detected "Layer4: types.ts"                4 "src/types.ts"
assert_layer_detected "Layer4: model.go (was undocumented)" 4 "internal/order_model.go"

# ---------------------------------------------------------------------------
# Layer 5: User Journey triggers
# ---------------------------------------------------------------------------
assert_layer_detected "Layer5: page.tsx"                5 "src/pages/checkout.page.tsx"
assert_layer_detected "Layer5: cmd Go file"             5 "cmd/server.go"
assert_layer_detected "Layer5: cli Python file"         5 "cli/main.py"

# ---------------------------------------------------------------------------
# Layer 6: Inventory triggers
# ---------------------------------------------------------------------------
assert_layer_detected "Layer6: .env.example"            6 ".env.example"
assert_layer_detected "Layer6: service README"          6 "services/api/README.md"

# ---------------------------------------------------------------------------
# Negative tests: irrelevant files should not trigger
# ---------------------------------------------------------------------------
assert_no_layer_detected "No trigger: unrelated .md"       "docs/CHANGELOG.md"
assert_no_layer_detected "No trigger: test file"           "src/__tests__/unit.test.ts"
assert_no_layer_detected "No trigger: Makefile"            "Makefile"

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
echo ""
echo "=================================="
echo "Results: ${PASS} passed, ${FAIL} failed"
echo "=================================="

[[ $FAIL -eq 0 ]] && exit 0 || exit 1
