#!/bin/bash
# .claude/skills/code-atlas/tests/test_atlas_output_structure.sh
#
# TDD tests for atlas output directory structure and file naming contracts.
# Validates that when /code-atlas runs on a fixture codebase, the output
# at docs/atlas/ matches the exact structure defined in SKILL.md.
#
# THESE TESTS WILL FAIL until the atlas layer generation is implemented.
#
# Usage: bash .claude/skills/code-atlas/tests/test_atlas_output_structure.sh [fixture_dir]
# Exit:  0 = all tests passed, non-zero = failures

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
FIXTURES_DIR="${SCRIPT_DIR}/fixtures"

PASS=0
FAIL=0

# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------
assert_file_exists() {
    local label="$1"
    local path="$2"
    if [[ -f "$path" ]]; then
        echo "PASS: $label"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $label — file not found: $path"
        FAIL=$((FAIL + 1))
    fi
}

assert_dir_exists() {
    local label="$1"
    local path="$2"
    if [[ -d "$path" ]]; then
        echo "PASS: $label"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $label — directory not found: $path"
        FAIL=$((FAIL + 1))
    fi
}

assert_file_contains() {
    local label="$1"
    local pattern="$2"
    local file="$3"
    if [[ ! -f "$file" ]]; then
        echo "FAIL: $label — file not found: $file"
        FAIL=$((FAIL + 1))
        return
    fi
    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo "PASS: $label"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $label — pattern '$pattern' not found in $file"
        FAIL=$((FAIL + 1))
    fi
}

assert_file_not_empty() {
    local label="$1"
    local file="$2"
    if [[ ! -f "$file" ]]; then
        echo "FAIL: $label — file not found: $file"
        FAIL=$((FAIL + 1))
        return
    fi
    if [[ -s "$file" ]]; then
        echo "PASS: $label"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $label — file is empty: $file"
        FAIL=$((FAIL + 1))
    fi
}

assert_valid_mermaid() {
    local label="$1"
    local file="$2"
    if [[ ! -f "$file" ]]; then
        echo "FAIL: $label — .mmd file not found: $file"
        FAIL=$((FAIL + 1))
        return
    fi
    # A valid Mermaid file must start with a diagram type keyword
    first_token=$(head -3 "$file" | grep -oE "^(graph|flowchart|sequenceDiagram|classDiagram|stateDiagram|erDiagram|journey|gantt|pie|gitGraph)" | head -1 || true)
    if [[ -n "$first_token" ]]; then
        echo "PASS: $label (starts with: $first_token)"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $label — not a valid Mermaid diagram (must start with diagram type keyword)"
        echo "  First 3 lines of $file:"
        head -3 "$file" | sed 's/^/    /'
        FAIL=$((FAIL + 1))
    fi
}

assert_valid_dot() {
    local label="$1"
    local file="$2"
    if [[ ! -f "$file" ]]; then
        echo "FAIL: $label — .dot file not found: $file"
        FAIL=$((FAIL + 1))
        return
    fi
    # Valid DOT file must contain digraph or graph keyword
    if grep -qE "^(di)?graph\s" "$file" 2>/dev/null; then
        echo "PASS: $label"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $label — not a valid DOT file (must start with 'graph' or 'digraph')"
        FAIL=$((FAIL + 1))
    fi
}

assert_markdown_table() {
    local label="$1"
    local file="$2"
    local min_rows="${3:-1}"
    if [[ ! -f "$file" ]]; then
        echo "FAIL: $label — inventory file not found: $file"
        FAIL=$((FAIL + 1))
        return
    fi
    # Count table separator rows (|---|) as a proxy for having a proper table
    separator_count=$(grep -c "^|[-| ]*|$" "$file" 2>/dev/null || echo "0")
    row_count=$(grep -c "^|" "$file" 2>/dev/null || echo "0")
    if [[ "$row_count" -ge "$((min_rows + 2))" ]]; then  # header + separator + data rows
        echo "PASS: $label ($row_count table rows including header)"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $label — expected markdown table with at least $min_rows data rows, found $row_count total rows"
        FAIL=$((FAIL + 1))
    fi
}

# ---------------------------------------------------------------------------
# Create minimal Go fixture codebase (Scenario 1 from test_scenarios.md)
# ---------------------------------------------------------------------------
setup_go_fixture() {
    local dir="$1"
    mkdir -p "$dir"/{cmd/server,internal/{handlers,models}}

    # Entry point
    cat > "$dir/cmd/server/main.go" << 'EOF'
package main

import (
    "github.com/gin-gonic/gin"
    "myapp/internal/handlers"
)

func main() {
    r := gin.Default()
    handlers.RegisterUserRoutes(r)
    r.Run(":8080")
}
EOF

    # Handler with routes
    cat > "$dir/internal/handlers/user_handler.go" << 'EOF'
package handlers

import (
    "net/http"
    "github.com/gin-gonic/gin"
)

func RegisterUserRoutes(r *gin.Engine) {
    r.GET("/users", ListUsers)
    r.POST("/users", CreateUser)
}

func ListUsers(c *gin.Context) {
    c.JSON(http.StatusOK, gin.H{"users": []string{}})
}

func CreateUser(c *gin.Context) {
    c.JSON(http.StatusCreated, gin.H{"id": "new-user"})
}
EOF

    # Model
    cat > "$dir/internal/models/user_model.go" << 'EOF'
package models

type User struct {
    ID    string `json:"id"`
    Email string `json:"email"`
    Name  string `json:"name"`
}
EOF

    # Docker compose
    cat > "$dir/docker-compose.yml" << 'EOF'
version: "3.8"
services:
  api:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL
      - PORT
EOF

    # Env example
    cat > "$dir/.env.example" << 'EOF'
DATABASE_URL=postgres://localhost/mydb
PORT=8080
EOF

    # Go module
    cat > "$dir/go.mod" << 'EOF'
module myapp

go 1.21

require github.com/gin-gonic/gin v1.9.1
EOF

    # Git init
    git -C "$dir" init -q
    git -C "$dir" config user.email "test@test.com"
    git -C "$dir" config user.name "Test"
    git -C "$dir" add .
    git -C "$dir" commit -q -m "init go fixture"
}

# ---------------------------------------------------------------------------
# Test Suite: Fixture-based output structure validation
# ---------------------------------------------------------------------------
# NOTE: These tests create a fixture codebase, then expect /code-atlas to
# have been run against it. Since we cannot invoke the Claude skill directly,
# these tests validate the OUTPUT STRUCTURE that the skill must produce.
# They FAIL until the atlas generation is implemented.
# ---------------------------------------------------------------------------

ATLAS_DIR="${1:-${REPO_ROOT}/docs/atlas}"

echo ""
echo "=== Atlas Output Structure Tests ==="
echo "Testing against: $ATLAS_DIR"
echo "(Run /code-atlas first, then re-run these tests)"
echo ""

# ---------------------------------------------------------------------------
# Test Group 1: Top-level structure
# ---------------------------------------------------------------------------

echo "--- Top-level directory structure ---"
assert_dir_exists "docs/atlas/ directory exists" "$ATLAS_DIR"
assert_file_exists "docs/atlas/index.md exists" "$ATLAS_DIR/index.md"
assert_file_contains "index.md mentions Layer 1" "layer1\|Layer 1\|Runtime Topology" "$ATLAS_DIR/index.md"
assert_file_contains "index.md mentions Layer 2" "layer2\|Layer 2\|Dependenc" "$ATLAS_DIR/index.md"
assert_file_contains "index.md mentions Layer 3" "layer3\|Layer 3\|API|Contracts|Routing\|API|Contracts|Routing" "$ATLAS_DIR/index.md"
assert_file_contains "index.md mentions Layer 4" "layer4\|Layer 4\|Data Flow" "$ATLAS_DIR/index.md"
assert_file_contains "index.md mentions Layer 5" "layer5\|Layer 5\|User Journey\|Scenario" "$ATLAS_DIR/index.md"
assert_file_contains "index.md mentions Layer 6" "layer6\|Layer 6\|Inventory" "$ATLAS_DIR/index.md"

# ---------------------------------------------------------------------------
# Test Group 2: Layer 1 — Runtime Topology
# ---------------------------------------------------------------------------

echo ""
echo "--- Layer 1: Runtime Topology ---"
L1="$ATLAS_DIR/repo-surface"
assert_dir_exists  "repo-surface/ exists"                  "$L1"
assert_file_exists "repo-surface/topology.dot"             "$L1/topology.dot"
assert_file_exists "repo-surface/topology.mmd"             "$L1/topology.mmd"
assert_file_exists "repo-surface/topology.svg"             "$L1/topology.svg"
assert_file_exists "repo-surface/README.md"                "$L1/README.md"
assert_valid_dot   "topology.dot is valid DOT syntax"        "$L1/topology.dot"
assert_valid_mermaid "topology.mmd is valid Mermaid syntax"  "$L1/topology.mmd"
assert_file_not_empty "topology.svg is not empty"            "$L1/topology.svg"
assert_file_contains "topology.dot has at least one node"    "label\|graph\|digraph" "$L1/topology.dot"

# ---------------------------------------------------------------------------
# Test Group 3: Layer 2 — Compile-time Dependencies
# ---------------------------------------------------------------------------

echo ""
echo "--- Layer 2: Compile-time Dependencies ---"
L2="$ATLAS_DIR/compile-deps"
assert_dir_exists  "compile-deps/ exists"             "$L2"
assert_file_exists "compile-deps/dependencies.mmd"    "$L2/dependencies.mmd"
assert_file_exists "compile-deps/dependencies.svg"    "$L2/dependencies.svg"
assert_file_exists "compile-deps/inventory.md"        "$L2/inventory.md"
assert_file_exists "compile-deps/README.md"           "$L2/README.md"
assert_valid_mermaid "dependencies.mmd is valid Mermaid"     "$L2/dependencies.mmd"
assert_markdown_table "inventory.md has package table" "$L2/inventory.md" 1

# ---------------------------------------------------------------------------
# Test Group 4: Layer 3 — API|Contracts|Routing API|Contracts|Routing
# ---------------------------------------------------------------------------

echo ""
echo "--- Layer 3: API Contracts ---"
L3="$ATLAS_DIR/api-contracts"
assert_dir_exists  "api-contracts/ exists"             "$L3"
assert_file_exists "api-contracts/routing.mmd"         "$L3/routing.mmd"
assert_file_exists "api-contracts/routing.svg"         "$L3/routing.svg"
assert_file_exists "api-contracts/route-inventory.md"  "$L3/route-inventory.md"
assert_file_exists "api-contracts/README.md"           "$L3/README.md"
assert_valid_mermaid "routing.mmd is valid Mermaid"          "$L3/routing.mmd"
assert_markdown_table "route-inventory.md has route rows"    "$L3/route-inventory.md" 1
# Route inventory must have API|Contracts|Routing method column
assert_file_contains "route-inventory.md has Method column"  "[Mm]ethod\|GET\|POST\|PUT\|DELETE\|PATCH" "$L3/route-inventory.md"
# Route inventory must have Path column
assert_file_contains "route-inventory.md has Path column"    "[Pp]ath\|/\|endpoint" "$L3/route-inventory.md"

# ---------------------------------------------------------------------------
# Test Group 5: Layer 4 — Data Flows
# ---------------------------------------------------------------------------

echo ""
echo "--- Layer 4: Data Flows ---"
L4="$ATLAS_DIR/data-flow"
assert_dir_exists  "data-flow/ exists"                 "$L4"
assert_file_exists "data-flow/dataflow.mmd"            "$L4/dataflow.mmd"
assert_file_exists "data-flow/dataflow.svg"            "$L4/dataflow.svg"
assert_file_exists "data-flow/README.md"               "$L4/README.md"
assert_valid_mermaid "dataflow.mmd is valid Mermaid"         "$L4/dataflow.mmd"

# ---------------------------------------------------------------------------
# Test Group 6: Layer 5 — User Journey Scenarios
# ---------------------------------------------------------------------------

echo ""
echo "--- Layer 5: User Journey Scenarios ---"
L5="$ATLAS_DIR/user-journeys"
assert_dir_exists  "user-journeys/ exists"            "$L5"
assert_file_exists "user-journeys/README.md"          "$L5/README.md"
# At least one journey diagram must exist
journey_count=$(find "$L5" -name "journey-*.mmd" 2>/dev/null | wc -l)
if [[ "$journey_count" -ge 1 ]]; then
    echo "PASS: layer5 has $journey_count journey diagram(s)"
    PASS=$((PASS + 1))
else
    echo "FAIL: layer5 must have at least one journey-*.mmd file"
    FAIL=$((FAIL + 1))
fi

# ---------------------------------------------------------------------------
# Test Group 7: Layer 6 — Inventory Tables
# ---------------------------------------------------------------------------

echo ""
echo "--- Layer 6: Inventory Tables ---"
L6="$ATLAS_DIR/inventory"
assert_dir_exists  "inventory/ exists"                "$L6"
assert_file_exists "inventory/services.md"            "$L6/services.md"
assert_file_exists "inventory/env-vars.md"            "$L6/env-vars.md"
assert_file_exists "inventory/data-stores.md"         "$L6/data-stores.md"
assert_file_exists "inventory/external-deps.md"       "$L6/external-deps.md"
assert_markdown_table "services.md has service rows"         "$L6/services.md" 1
assert_markdown_table "env-vars.md has env var rows"         "$L6/env-vars.md" 1

# CRITICAL: env-vars.md must NOT contain real values
# Check for common secret value patterns
if [[ -f "$L6/env-vars.md" ]]; then
    if grep -qE "=.{8,}" "$L6/env-vars.md" 2>/dev/null; then
        # Found something that looks like key=value with a real value
        if grep -qE "REDACTED|\*\*\*" "$L6/env-vars.md" 2>/dev/null; then
            echo "PASS: env-vars.md: values are redacted"
            PASS=$((PASS + 1))
        else
            echo "FAIL: env-vars.md: may contain unredacted env var values (SEC-01)"
            FAIL=$((FAIL + 1))
        fi
    else
        echo "PASS: env-vars.md: no raw key=value assignments found"
        PASS=$((PASS + 1))
    fi
fi

# ---------------------------------------------------------------------------
# Test Group 8: Bug Reports from both passes
# ---------------------------------------------------------------------------

echo ""
echo "--- Bug Reports ---"
BR="$ATLAS_DIR/bug-reports"
assert_dir_exists  "bug-reports/ exists"                     "$BR"
assert_file_exists "bug-reports/merged-findings.md"     "$BR/merged-findings.md"
assert_file_exists "bug-reports/validated-bugs.md"       "$BR/validated-bugs.md"

# Bug reports must have required fields
assert_file_contains "merged report has Severity field" "[Ss]everity" "$BR/merged-findings.md"
assert_file_contains "merged report has Evidence field" "[Ee]vidence\|Code quote\|code_quote" "$BR/merged-findings.md"
assert_file_contains "validated report has journey reference" "[Jj]ourney\|scenario\|[Uu]ser" "$BR/validated-bugs.md"

# ---------------------------------------------------------------------------
# Test Group 9: .build-stamp freshness metadata
# ---------------------------------------------------------------------------

echo ""
echo "--- Build Stamp ---"
assert_file_exists "docs/atlas/.build-stamp exists" "$ATLAS_DIR/.build-stamp"
if [[ -f "$ATLAS_DIR/.build-stamp" ]]; then
    assert_file_contains ".build-stamp has git hash" "[0-9a-f]\{7,40\}" "$ATLAS_DIR/.build-stamp"
    assert_file_contains ".build-stamp has date" "[0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}" "$ATLAS_DIR/.build-stamp"
fi

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
echo ""
echo "=================================="
echo "Results: ${PASS} passed, ${FAIL} failed"
echo "=================================="
echo ""
echo "NOTE: Most failures are expected — this is a TDD test suite."
echo "Implement the /code-atlas skill to make these tests pass."

[[ $FAIL -eq 0 ]] && exit 0 || exit 1
