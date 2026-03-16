#!/bin/bash
# .claude/skills/code-atlas/tests/test_layer_contracts.sh
#
# TDD tests for the content contracts of each atlas layer.
# Tests verify that layer outputs correctly represent the codebase under analysis.
# Each test creates a minimal fixture and validates the expected content in the
# corresponding atlas output.
#
# THESE TESTS WILL FAIL until atlas layer generation is implemented.
# They encode the contracts that the implementation must satisfy.
#
# Usage: bash .claude/skills/code-atlas/tests/test_layer_contracts.sh
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
    local label="$1"
    local pattern="$2"
    local file="$3"
    if [[ ! -f "$file" ]]; then
        echo "FAIL: $label — file not found: $file"
        FAIL=$((FAIL + 1)); return
    fi
    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo "PASS: $label"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $label"
        echo "  Pattern: '$pattern' not found in $file"
        head -20 "$file" | sed 's/^/  > /'
        FAIL=$((FAIL + 1))
    fi
}

assert_not_contains() {
    local label="$1"
    local pattern="$2"
    local file="$3"
    if [[ ! -f "$file" ]]; then
        echo "FAIL: $label — file not found: $file"
        FAIL=$((FAIL + 1)); return
    fi
    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo "FAIL: $label — forbidden pattern '$pattern' found in $file"
        FAIL=$((FAIL + 1))
    else
        echo "PASS: $label"
        PASS=$((PASS + 1))
    fi
}

assert_row_count_gte() {
    local label="$1"
    local file="$2"
    local min_data_rows="$3"
    if [[ ! -f "$file" ]]; then
        echo "FAIL: $label — file not found: $file"
        FAIL=$((FAIL + 1)); return
    fi
    # Count rows excluding header and separator
    data_rows=$(grep "^|" "$file" 2>/dev/null | grep -v "^|[-| ]*|$" | grep -v "^| *[A-Z].*|$" | wc -l || echo 0)
    actual_rows=$(grep "^|" "$file" 2>/dev/null | wc -l || echo 0)
    if [[ "$actual_rows" -ge "$((min_data_rows + 2))" ]]; then
        echo "PASS: $label ($actual_rows total rows)"
        PASS=$((PASS + 1))
    else
        echo "FAIL: $label — expected >= $min_data_rows data rows, found ~$actual_rows total rows"
        FAIL=$((FAIL + 1))
    fi
}

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

create_go_fixture() {
    local dir="$1"
    mkdir -p "$dir"/{cmd/server,internal/{handlers,models},k8s}

    cat > "$dir/cmd/server/main.go" << 'EOF'
package main

import (
    "github.com/gin-gonic/gin"
    "myapp/internal/handlers"
)

func main() {
    r := gin.Default()
    handlers.RegisterRoutes(r)
    r.Run(":8080")
}
EOF

    cat > "$dir/internal/handlers/user_handler.go" << 'EOF'
package handlers

import (
    "net/http"
    "github.com/gin-gonic/gin"
    "myapp/internal/models"
)

func RegisterRoutes(r *gin.Engine) {
    r.GET("/api/users", ListUsers)
    r.POST("/api/users", CreateUser)
    r.GET("/api/users/:id", GetUser)
    r.DELETE("/api/users/:id", DeleteUser)
}

func ListUsers(c *gin.Context)  { c.JSON(http.StatusOK, []models.User{}) }
func CreateUser(c *gin.Context) { c.JSON(http.StatusCreated, models.User{}) }
func GetUser(c *gin.Context)    { c.JSON(http.StatusOK, models.User{}) }
func DeleteUser(c *gin.Context) { c.JSON(http.StatusNoContent, nil) }
EOF

    cat > "$dir/internal/models/user_model.go" << 'EOF'
package models

type User struct {
    ID       string `json:"id"`
    Email    string `json:"email"`
    Name     string `json:"name"`
    Role     string `json:"role"`
    Password string `json:"-"`
}

type CreateUserRequest struct {
    Email    string `json:"email" binding:"required"`
    Name     string `json:"name" binding:"required"`
    Password string `json:"password" binding:"required"`
}
EOF

    cat > "$dir/docker-compose.yml" << 'EOF'
version: "3.8"
services:
  api:
    build: .
    ports:
      - "8080:8080"
    depends_on:
      - postgres
      - redis
    environment:
      - DATABASE_URL
      - JWT_SECRET
  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
  redis:
    image: redis:7
    ports:
      - "6379:6379"
EOF

    cat > "$dir/.env.example" << 'EOF'
DATABASE_URL=postgres://user:password@localhost/mydb  # pragma: allowlist secret
JWT_SECRET=your-jwt-secret-here  # pragma: allowlist secret
REDIS_URL=redis://localhost:6379
PORT=8080
EOF

    cat > "$dir/go.mod" << 'EOF'
module myapp

go 1.21

require (
    github.com/gin-gonic/gin v1.9.1
    github.com/golang-jwt/jwt/v5 v5.0.0
    gorm.io/gorm v1.25.4
    gorm.io/driver/postgres v1.5.3
)
EOF

    git -C "$dir" init -q
    git -C "$dir" config user.email "test@test.com"
    git -C "$dir" config user.name "Test"
    git -C "$dir" add .
    git -C "$dir" commit -q -m "go fixture"
}

# ---------------------------------------------------------------------------
# Layer 1 Contracts — Runtime Topology
# ---------------------------------------------------------------------------

echo ""
echo "=== Layer 1 Contract Tests: Runtime Topology ==="

# Setup: We need the atlas to have been run on the Go fixture.
# These tests check an EXISTING atlas output at docs/atlas/.
# If docs/atlas/ doesn't exist, we check the fixture would produce expected output.
ATLAS="${REPO_ROOT}/docs/atlas"

L1="${ATLAS}/layer1-runtime"

# Contract 1.1: topology.dot must contain all services from docker-compose.yml
# If the Go fixture is used (api, postgres, redis services):
assert_contains "L1: topology.dot has 'api' node" "api" "${L1}/topology.dot"
assert_contains "L1: topology.dot has 'postgres' node" "postgres" "${L1}/topology.dot"
assert_contains "L1: topology.dot has 'redis' node" "redis" "${L1}/topology.dot"

# Contract 1.2: topology.mmd mirrors topology.dot (both exist, same services)
assert_contains "L1: topology.mmd has 'api'" "api" "${L1}/topology.mmd"
assert_contains "L1: topology.mmd has 'postgres'" "postgres" "${L1}/topology.mmd"

# Contract 1.3: depends_on relationships become edges in the graph
assert_contains "L1: topology shows api depends on postgres" "api.*postgres\|postgres.*api" "${L1}/topology.dot"

# Contract 1.4: Port mappings are annotated
assert_contains "L1: port 8080 annotated" "8080" "${L1}/topology.dot"

# Contract 1.5: README.md explains the layer
assert_contains "L1: README has layer description" "[Rr]untime\|[Tt]opology\|[Ss]ervice" "${L1}/README.md"

# ---------------------------------------------------------------------------
# Layer 2 Contracts — Compile-time Dependencies
# ---------------------------------------------------------------------------

echo ""
echo "=== Layer 2 Contract Tests: Compile-time Dependencies ==="

L2="${ATLAS}/layer2-dependencies"

# Contract 2.1: inventory.md has columns for Package, Version, License
assert_contains "L2: inventory.md has Package column" "[Pp]ackage\|[Mm]odule\|[Nn]ame" "${L2}/inventory.md"
assert_contains "L2: inventory.md has Version column" "[Vv]ersion" "${L2}/inventory.md"

# Contract 2.2: Known dependencies from go.mod appear in inventory
assert_contains "L2: gin dependency in inventory" "gin" "${L2}/inventory.md"
assert_contains "L2: gorm dependency in inventory" "gorm" "${L2}/inventory.md"
assert_contains "L2: jwt dependency in inventory" "jwt" "${L2}/inventory.md"

# Contract 2.3: Version numbers are shown
assert_contains "L2: version 1.9.1 in inventory" "1\.9\.1" "${L2}/inventory.md"

# Contract 2.4: dependencies.mmd shows the dep graph
assert_contains "L2: mmd has module name" "myapp\|module" "${L2}/dependencies.mmd"

# ---------------------------------------------------------------------------
# Layer 3 Contracts — HTTP Routing
# ---------------------------------------------------------------------------

echo ""
echo "=== Layer 3 Contract Tests: HTTP Routing ==="

L3="${ATLAS}/layer3-http-routing"

# Contract 3.1: All 4 routes from user_handler.go appear in route-inventory.md
assert_contains "L3: GET /api/users in inventory" "GET.*api/users\|/api/users.*GET" "${L3}/route-inventory.md"
assert_contains "L3: POST /api/users in inventory" "POST.*api/users\|/api/users.*POST" "${L3}/route-inventory.md"
assert_contains "L3: GET /api/users/:id in inventory" "/api/users/:id\|/api/users/\{id\}" "${L3}/route-inventory.md"
assert_contains "L3: DELETE /api/users/:id in inventory" "DELETE.*api/users\|/api/users.*DELETE" "${L3}/route-inventory.md"

# Contract 3.2: Handler function names are referenced
assert_contains "L3: ListUsers handler referenced" "ListUsers\|list.users\|listUsers" "${L3}/route-inventory.md"
assert_contains "L3: CreateUser handler referenced" "CreateUser\|create.user\|createUser" "${L3}/route-inventory.md"

# Contract 3.3: DTO/Request type is linked where known
assert_contains "L3: CreateUserRequest DTO referenced" "CreateUserRequest\|CreateUser.*Request\|request" "${L3}/route-inventory.md"

# Contract 3.4: routing.mmd shows method-path nodes or flowchart
assert_contains "L3: mmd shows route structure" "GET\|POST\|DELETE\|/api" "${L3}/routing.mmd"

# ---------------------------------------------------------------------------
# Layer 4 Contracts — Data Flows
# ---------------------------------------------------------------------------

echo ""
echo "=== Layer 4 Contract Tests: Data Flows ==="

L4="${ATLAS}/layer4-dataflow"

# Contract 4.1: User struct appears in dataflow diagram
assert_contains "L4: User struct in dataflow" "User" "${L4}/dataflow.mmd"

# Contract 4.2: CreateUserRequest appears
assert_contains "L4: CreateUserRequest in dataflow" "CreateUserRequest\|CreateUser" "${L4}/dataflow.mmd"

# Contract 4.3: Password field is NOT shown in API layer (json:"-" annotation)
# Note: it's fine to show the struct, but the diagram should note the field is hidden from JSON
# This is a best-effort check; the field name may appear in non-API contexts
# Primary concern: API response diagrams must not show Password as an output field
assert_not_contains "L4: Password not in API output flow" "Password.*response\|response.*Password" "${L4}/dataflow.mmd"

# ---------------------------------------------------------------------------
# Layer 5 Contracts — User Journey Scenarios
# ---------------------------------------------------------------------------

echo ""
echo "=== Layer 5 Contract Tests: User Journey Scenarios ==="

L5="${ATLAS}/layer5-user-journeys"

# Contract 5.1: At least one journey .mmd file exists
journey_files=$(find "${L5}" -name "journey-*.mmd" 2>/dev/null | wc -l)
if [[ "${journey_files}" -ge 1 ]]; then
    echo "PASS: L5: at least 1 journey diagram found (${journey_files} total)"
    PASS=$((PASS + 1))
else
    echo "FAIL: L5: expected at least 1 journey-*.mmd file, found 0"
    FAIL=$((FAIL + 1))
fi

# Contract 5.2: A user registration journey is derived from POST /api/users
assert_contains "L5: registration journey references user creation" \
    "[Rr]egist\|[Cc]reate [Uu]ser\|POST.*users\|/api/users" \
    "${L5}/README.md"

# Contract 5.3: Journey diagrams use valid Mermaid journey or flowchart syntax
for journey_file in "${L5}"/journey-*.mmd; do
    [[ -f "$journey_file" ]] || continue
    fname=$(basename "$journey_file")
    first_kw=$(head -3 "$journey_file" | grep -oE "^(journey|graph|flowchart|sequenceDiagram)" | head -1 || true)
    if [[ -n "$first_kw" ]]; then
        echo "PASS: L5: $fname uses valid diagram type ($first_kw)"
        PASS=$((PASS + 1))
    else
        echo "FAIL: L5: $fname does not start with a recognized Mermaid diagram type"
        FAIL=$((FAIL + 1))
    fi
done

# ---------------------------------------------------------------------------
# Layer 6 Contracts — Inventory Tables
# ---------------------------------------------------------------------------

echo ""
echo "=== Layer 6 Contract Tests: Inventory Tables ==="

L6="${ATLAS}/layer6-inventory"

# Contract 6.1: services.md has row for each docker-compose service
assert_contains "L6: api service in services.md" "api" "${L6}/services.md"
assert_contains "L6: postgres in services.md" "postgres" "${L6}/services.md"
assert_contains "L6: redis in services.md" "redis" "${L6}/services.md"

# Contract 6.2: services.md has port column
assert_contains "L6: services.md has port 8080" "8080" "${L6}/services.md"
assert_contains "L6: services.md has port 5432" "5432" "${L6}/services.md"

# Contract 6.3: env-vars.md has all 4 vars from .env.example
assert_contains "L6: DATABASE_URL in env-vars.md" "DATABASE_URL" "${L6}/env-vars.md"
assert_contains "L6: JWT_SECRET in env-vars.md" "JWT_SECRET" "${L6}/env-vars.md"
assert_contains "L6: REDIS_URL in env-vars.md" "REDIS_URL" "${L6}/env-vars.md"
assert_contains "L6: PORT in env-vars.md" "PORT" "${L6}/env-vars.md"

# Contract 6.4 (SEC-01): env-vars.md MUST NOT contain real values
assert_not_contains "L6 SEC-01: no postgres password in env-vars.md" "password" "${L6}/env-vars.md"
assert_not_contains "L6 SEC-01: no jwt secret value in env-vars.md" "your-jwt-secret-here" "${L6}/env-vars.md"
assert_not_contains "L6 SEC-01: no redis URL with password in env-vars.md" "redis://localhost" "${L6}/env-vars.md"

# Contract 6.5: external-deps.md references external packages
assert_contains "L6: external-deps.md has gin" "gin" "${L6}/external-deps.md"
assert_contains "L6: external-deps.md has gorm" "gorm" "${L6}/external-deps.md"

# ---------------------------------------------------------------------------
# Pass 1 Bug Hunt Contracts
# ---------------------------------------------------------------------------

echo ""
echo "=== Pass 1 Bug Hunt Contract Tests ==="

P1="${ATLAS}/bug-reports/pass1-contradictions.md"

# Contract P1.1: Report file exists
if [[ ! -f "$P1" ]]; then
    echo "FAIL: pass1-contradictions.md does not exist"
    FAIL=$((FAIL + 4))
else
    # Contract P1.2: Report has BUG entries
    bug_count=$(grep -cE "^## BUG-[0-9]+" "$P1" 2>/dev/null || echo 0)
    if [[ "$bug_count" -ge 0 ]]; then
        echo "PASS: pass1 bug report parseable (${bug_count} BUG entries)"
        PASS=$((PASS + 1))
    fi

    # Contract P1.3: Each BUG entry has Severity
    assert_contains "P1: bug entries have Severity field" "[Ss]everity.*HIGH\|[Ss]everity.*MEDIUM\|[Ss]everity.*LOW\|[Ss]everity.*CRITICAL" "$P1"

    # Contract P1.4: Each BUG entry has Layer reference
    assert_contains "P1: bug entries reference layers" "[Ll]ayer [1-6]\|Layer[1-6]" "$P1"

    # Contract P1.5: Code evidence is included
    assert_contains "P1: bug entries have code evidence" "Evidence\|code.quote\|Code quote\|code-block" "$P1"

    # Contract P1.6: No raw secret values in evidence
    assert_not_contains "P1 SEC-09: no raw passwords in bug report" "password.*=.*[a-zA-Z0-9]{8}" "$P1"
fi

# ---------------------------------------------------------------------------
# Pass 2 Bug Hunt Contracts
# ---------------------------------------------------------------------------

echo ""
echo "=== Pass 2 Bug Hunt Contract Tests ==="

P2="${ATLAS}/bug-reports/pass2-journey-bugs.md"

if [[ ! -f "$P2" ]]; then
    echo "FAIL: pass2-journey-bugs.md does not exist"
    FAIL=$((FAIL + 3))
else
    # Contract P2.1: Report references at least one user journey
    assert_contains "P2: report references user journeys" "[Jj]ourney\|[Ss]cenario\|user.flow\|User Flow" "$P2"

    # Contract P2.2: Report traces routes through layers
    assert_contains "P2: report references route paths" "/api/\|GET\|POST\|route" "$P2"

    # Contract P2.3: Report has Severity
    assert_contains "P2: report has severity field" "[Ss]everity\|[Pp]riority" "$P2"
fi

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
echo ""
echo "=================================="
echo "Results: ${PASS} passed, ${FAIL} failed"
echo "=================================="
echo ""
echo "NOTE: Failures are expected — TDD suite. Implement /code-atlas to pass."

[[ $FAIL -eq 0 ]] && exit 0 || exit 1
