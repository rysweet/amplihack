#!/bin/bash
# Create git bundle snapshot of working tree
# Usage: ./create-bundle.sh /path/to/repo /output/path/bundle.git

set -e

REPO_PATH="$1"
OUTPUT_PATH="$2"

if [[ -z "$REPO_PATH" || -z "$OUTPUT_PATH" ]]; then
    echo "Usage: $0 <repo-path> <output-path>"
    echo "Example: $0 ~/repos/my-lib /tmp/my-lib.bundle"
    exit 1
fi

if [[ ! -d "$REPO_PATH/.git" ]]; then
    echo "Error: $REPO_PATH is not a git repository"
    exit 1
fi

echo "Creating git bundle from $REPO_PATH..."

cd "$REPO_PATH"

# Fetch all refs to ensure complete history
echo "Fetching refs from origin..."
git fetch --all --tags --quiet 2>/dev/null || true

# Check for uncommitted changes
if [[ -n $(git status --porcelain) ]]; then
    echo "Uncommitted changes detected - creating snapshot commit..."
    
    # Create temp clone and commit changes
    TEMP_DIR=$(mktemp -d)
    echo "Cloning to temp directory: $TEMP_DIR"
    git clone --quiet "$REPO_PATH" "$TEMP_DIR"
    
    # Sync working tree (including deletions)
    echo "Syncing working tree..."
    rsync -a --delete --exclude='.git' "$REPO_PATH/" "$TEMP_DIR/"
    
    cd "$TEMP_DIR"
    git add -A
    git commit --allow-empty -m "Shadow snapshot: uncommitted changes" \
        --author="Shadow <shadow@localhost>" --quiet
    
    SNAPSHOT_COMMIT=$(git rev-parse HEAD)
    echo "Snapshot commit: $SNAPSHOT_COMMIT"
    
    # Create bundle with all refs
    echo "Creating bundle..."
    git bundle create "$OUTPUT_PATH" --all --quiet
    
    cd /
    rm -rf "$TEMP_DIR"
else
    echo "No uncommitted changes - bundling clean repository..."
    
    # Get all refs to bundle (local + remote tracking)
    REFS=$(git show-ref --heads --tags | awk '{print $2}')
    REMOTE_REFS=$(git show-ref | grep 'refs/remotes/' | awk '{print $2}' || true)
    
    if [[ -n "$REFS" || -n "$REMOTE_REFS" ]]; then
        # Bundle with explicit refs to include remote tracking refs
        git bundle create "$OUTPUT_PATH" $REFS $REMOTE_REFS --quiet 2>/dev/null
    else
        # Fallback to --all if no refs found
        git bundle create "$OUTPUT_PATH" --all --quiet
    fi
    
    SNAPSHOT_COMMIT=$(git rev-parse HEAD)
    echo "Current commit: $SNAPSHOT_COMMIT"
fi

BUNDLE_SIZE=$(du -h "$OUTPUT_PATH" | cut -f1)
echo "Bundle created successfully: $OUTPUT_PATH ($BUNDLE_SIZE)"
echo "Commit SHA: $SNAPSHOT_COMMIT"
