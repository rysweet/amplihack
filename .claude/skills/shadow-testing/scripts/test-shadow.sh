#!/bin/bash
# Test that shadow environment is using local sources
# Usage: ./test-shadow.sh <container-name> <org> <repo> <expected-commit>

set -e

CONTAINER_NAME="$1"
ORG="$2"
REPO="$3"
EXPECTED_COMMIT="$4"

if [[ -z "$CONTAINER_NAME" || -z "$ORG" || -z "$REPO" ]]; then
    echo "Usage: $0 <container-name> <org> <repo> [expected-commit]"
    echo "Example: $0 shadow-test myorg my-lib abc1234"
    exit 1
fi

echo "Testing shadow environment: $CONTAINER_NAME"
echo "Expected local source: $ORG/$REPO"

# Check 1: Container is running
echo -n "✓ Checking container is running... "
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "FAIL"
    echo "  Container $CONTAINER_NAME is not running"
    exit 1
fi
echo "OK"

# Check 2: Gitea is accessible
echo -n "✓ Checking Gitea server... "
if ! docker exec "$CONTAINER_NAME" curl -sf http://localhost:3000/api/v1/version > /dev/null 2>&1; then
    echo "FAIL"
    echo "  Gitea not accessible at localhost:3000"
    exit 1
fi
echo "OK"

# Check 3: Repository exists in Gitea
echo -n "✓ Checking repository in Gitea... "
if ! docker exec "$CONTAINER_NAME" curl -sf http://shadow:shadow@localhost:3000/api/v1/repos/$ORG/$REPO > /dev/null 2>&1; then
    echo "FAIL"
    echo "  Repository $ORG/$REPO not found in Gitea"
    exit 1
fi
echo "OK"

# Check 4: Git URL rewriting is configured
echo -n "✓ Checking git URL rewriting... "
GIT_CONFIG=$(docker exec "$CONTAINER_NAME" git config --global --get-regexp 'url.*insteadOf')
if ! echo "$GIT_CONFIG" | grep -q "github.com/$ORG/$REPO"; then
    echo "FAIL"
    echo "  Git URL rewriting not configured for $ORG/$REPO"
    exit 1
fi
echo "OK"

# Check 5: Pre-cloned workspace exists
echo -n "✓ Checking pre-cloned workspace... "
if ! docker exec "$CONTAINER_NAME" test -d "/workspace/$ORG/$REPO/.git"; then
    echo "FAIL"
    echo "  Pre-cloned repo not found at /workspace/$ORG/$REPO"
    exit 1
fi
echo "OK"

# Check 6: Clone uses local source
echo -n "✓ Testing git clone uses local source... "
ACTUAL_COMMIT=$(docker exec "$CONTAINER_NAME" bash -c "
    rm -rf /tmp/test-clone 2>/dev/null || true
    git clone https://github.com/$ORG/$REPO /tmp/test-clone --quiet 2>&1
    cd /tmp/test-clone
    git rev-parse HEAD
" | tail -1)

if [[ -z "$ACTUAL_COMMIT" ]]; then
    echo "FAIL"
    echo "  Could not clone repository"
    exit 1
fi

echo "OK (commit: ${ACTUAL_COMMIT:0:7})"

# Check 7: Commit matches expected (if provided)
if [[ -n "$EXPECTED_COMMIT" ]]; then
    echo -n "✓ Verifying commit matches expected... "
    if [[ "${ACTUAL_COMMIT:0:7}" != "${EXPECTED_COMMIT:0:7}" ]]; then
        echo "FAIL"
        echo "  Expected: ${EXPECTED_COMMIT:0:7}"
        echo "  Actual:   ${ACTUAL_COMMIT:0:7}"
        echo "  WARNING: This might indicate local source is NOT being used!"
        exit 1
    fi
    echo "OK"
fi

echo ""
echo "✓ All checks passed!"
echo "  Shadow environment is correctly configured"
echo "  Local source $ORG/$REPO is being used"
