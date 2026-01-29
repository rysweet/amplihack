#!/bin/bash
# Start container with Gitea and configure git URL rewriting
# Usage: ./setup-shadow.sh <container-name> <bundle-path> <org> <repo>

set -e

CONTAINER_NAME="$1"
BUNDLE_PATH="$2"
ORG="$3"
REPO="$4"

if [[ -z "$CONTAINER_NAME" || -z "$BUNDLE_PATH" || -z "$ORG" || -z "$REPO" ]]; then
    echo "Usage: $0 <container-name> <bundle-path> <org> <repo>"
    echo "Example: $0 shadow-test /tmp/my-lib.bundle myorg my-lib"
    exit 1
fi

if [[ ! -f "$BUNDLE_PATH" ]]; then
    echo "Error: Bundle not found: $BUNDLE_PATH"
    exit 1
fi

# Check if container already exists
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "Error: Container $CONTAINER_NAME already exists"
    echo "Remove it first: docker rm -f $CONTAINER_NAME"
    exit 1
fi

echo "Starting shadow container: $CONTAINER_NAME"

# Start container with bundle mounted
docker run -d \
    --name "$CONTAINER_NAME" \
    -v "$BUNDLE_PATH:/snapshots/bundle.git:ro" \
    -e UV_NO_GITHUB_FAST_PATH=1 \
    -e UV_CACHE_DIR=/tmp/uv-cache \
    ghcr.io/microsoft/amplifier-shadow:latest

echo "Waiting for Gitea to start..."
MAX_WAIT=60
WAITED=0
until docker exec "$CONTAINER_NAME" curl -sf http://localhost:3000/api/v1/version > /dev/null 2>&1; do
    if [[ $WAITED -ge $MAX_WAIT ]]; then
        echo "Error: Gitea did not start within ${MAX_WAIT}s"
        docker logs "$CONTAINER_NAME" | tail -20
        exit 1
    fi
    sleep 1
    WAITED=$((WAITED + 1))
    echo -n "."
done
echo " Done!"

echo "Creating organization: $ORG"
docker exec "$CONTAINER_NAME" bash -c "
    curl -s -u shadow:shadow \
        -H 'Content-Type: application/json' \
        -d '{\"username\":\"$ORG\"}' \
        http://localhost:3000/api/v1/orgs > /dev/null 2>&1 || true
"

echo "Creating repository: $ORG/$REPO"
docker exec "$CONTAINER_NAME" bash -c "
    curl -s -u shadow:shadow \
        -H 'Content-Type: application/json' \
        -d '{\"name\":\"$REPO\",\"private\":false}' \
        http://localhost:3000/api/v1/orgs/$ORG/repos > /dev/null 2>&1
"

echo "Pushing bundle to Gitea..."
docker exec "$CONTAINER_NAME" bash -c "
    set -e
    cd /tmp
    rm -rf _push_repo
    mkdir _push_repo && cd _push_repo
    git init --bare --quiet
    
    # Parse bundle refs and fetch each one
    git bundle list-heads /snapshots/bundle.git | while read sha ref; do
        branch_name=\$(echo \"\$ref\" | sed 's|refs/heads/||; s|refs/remotes/origin/|_upstream_|; s|refs/tags/|tags/|')
        if echo \"\$ref\" | grep -q \"HEAD\"; then continue; fi
        git fetch /snapshots/bundle.git \"\$ref:refs/heads/\$branch_name\" 2>/dev/null || true
    done
    
    git remote add origin http://shadow:shadow@localhost:3000/$ORG/$REPO.git
    git push origin --all --force 2>&1 | grep -v 'remote:'
    git push origin --tags --force 2>&1 | grep -v 'remote:' || true
"

echo "Configuring git URL rewriting..."
docker exec "$CONTAINER_NAME" bash -c "
    git config --global user.email 'shadow@localhost'
    git config --global user.name 'Shadow'
    git config --global init.defaultBranch main
    git config --global advice.detachedHead false
    
    # Add URL rewriting patterns with boundary markers
    git config --global --add url.'http://shadow:shadow@localhost:3000/$ORG/$REPO.git'.insteadOf 'https://github.com/$ORG/$REPO.git'
    git config --global --add url.'http://shadow:shadow@localhost:3000/$ORG/$REPO.git'.insteadOf 'https://github.com/$ORG/$REPO.git/'
    git config --global --add url.'http://shadow:shadow@localhost:3000/$ORG/$REPO.git'.insteadOf 'https://github.com/$ORG/$REPO/'
    git config --global --add url.'http://shadow:shadow@localhost:3000/$ORG/$REPO.git'.insteadOf 'https://github.com/$ORG/$REPO@'
    git config --global --add url.'http://shadow:shadow@localhost:3000/$ORG/$REPO.git'.insteadOf 'git@github.com:$ORG/$REPO.git'
    git config --global --add url.'http://shadow:shadow@localhost:3000/$ORG/$REPO.git'.insteadOf 'git+https://github.com/$ORG/$REPO.git'
    git config --global --add url.'http://shadow:shadow@localhost:3000/$ORG/$REPO.git'.insteadOf 'git+https://github.com/$ORG/$REPO@'
    
    # Clear uv cache to ensure fresh resolution
    rm -rf /home/amplifier/.cache/uv/git-v0 2>/dev/null || true
"

echo "Pre-cloning repository to /workspace..."
docker exec "$CONTAINER_NAME" bash -c "
    mkdir -p /workspace/$ORG
    git clone http://shadow:shadow@localhost:3000/$ORG/$REPO.git /workspace/$ORG/$REPO --quiet 2>&1
"

echo ""
echo "✓ Shadow container ready: $CONTAINER_NAME"
echo "  Local source: $ORG/$REPO"
echo "  Pre-cloned at: /workspace/$ORG/$REPO"
echo ""
echo "Test with:"
echo "  docker exec $CONTAINER_NAME git clone https://github.com/$ORG/$REPO /tmp/test"
echo ""
echo "Destroy with:"
echo "  docker rm -f $CONTAINER_NAME"
