#!/bin/bash
# github-api-adapter.sh
#
# Thin adapter around the GitHub CLI (gh) for atlas CI operations.
# Provides retry logic, rate-limit awareness, and structured error handling
# so that callers never need to handle gh-specific failure modes directly.
#
# Supported operations:
#   post-pr-comment   <pr_number> <body_file>    Post (or update) a PR comment
#   create-issue      <title>    <body_file>      Open a GitHub issue with labels
#   get-pr-files      <pr_number>                 List files changed in a PR
#   check-rate-limit                              Print current API rate limit status
#
# Usage:
#   bash scripts/github-api-adapter.sh post-pr-comment 42 /tmp/comment.md
#   bash scripts/github-api-adapter.sh create-issue "Atlas rebuild failed" /tmp/body.md
#   bash scripts/github-api-adapter.sh get-pr-files 42
#   bash scripts/github-api-adapter.sh check-rate-limit
#
# Environment variables:
#   GH_TOKEN         GitHub token (required; exported by GitHub Actions automatically)
#   ATLAS_ISSUE_LABELS  Comma-separated labels for issues (default: documentation,automated)
#   GH_RETRY_MAX     Max retry attempts (default: 4)
#   GH_RETRY_DELAY   Initial retry delay in seconds (default: 5)
#
# Exit codes:
#   0 - Operation succeeded
#   1 - Operation failed after all retries
#   2 - Usage / argument error

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
GH_RETRY_MAX="${GH_RETRY_MAX:-4}"
GH_RETRY_DELAY="${GH_RETRY_DELAY:-5}"
ATLAS_ISSUE_LABELS="${ATLAS_ISSUE_LABELS:-documentation,automated}"

# Marker used to identify existing atlas PR comments for update-or-create logic
ATLAS_COMMENT_MARKER="<!-- atlas-ci-comment -->"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log()  { echo "[github-api-adapter] $*"; }
warn() { echo "[github-api-adapter] WARN: $*" >&2; }
err()  { echo "[github-api-adapter] ERROR: $*" >&2; }

# Check that gh CLI is available and authenticated
assert_gh_available() {
    if ! command -v gh &>/dev/null; then
        err "'gh' CLI not found. Install from https://cli.github.com/"
        exit 1
    fi
    if [[ -z "${GH_TOKEN:-}" ]]; then
        warn "GH_TOKEN not set. Relying on existing gh auth state."
    fi
}

# Check whether the GitHub API rate limit is close to exhausted.
# Prints a warning if fewer than 50 requests remain, sleeps until reset if exhausted.
check_and_respect_rate_limit() {
    local rate_json
    rate_json=$(gh api rate_limit 2>/dev/null || echo '{}')
    local remaining
    remaining=$(echo "$rate_json" | grep -o '"remaining":[0-9]*' | head -1 | grep -o '[0-9]*' || echo "999")
    local reset_at
    reset_at=$(echo "$rate_json" | grep -o '"reset":[0-9]*' | head -1 | grep -o '[0-9]*' || echo "0")

    if [[ "$remaining" -lt 10 ]]; then
        local now
        now=$(date +%s)
        local wait_secs=$(( reset_at - now + 5 ))
        if [[ $wait_secs -gt 0 ]]; then
            warn "Rate limit almost exhausted (${remaining} remaining). Sleeping ${wait_secs}s until reset."
            sleep "$wait_secs"
        fi
    elif [[ "$remaining" -lt 50 ]]; then
        warn "Rate limit low: ${remaining} requests remaining."
    fi
}

# Retry wrapper with exponential backoff.
# Usage: gh_with_retry <max> <delay> <gh_args...>
gh_with_retry() {
    local max="$1"
    local delay="$2"
    shift 2
    local args=("$@")
    local attempt=1
    local current_delay=$delay

    while [[ $attempt -le $max ]]; do
        # Check rate limit before each attempt
        check_and_respect_rate_limit || true

        if gh "${args[@]}"; then
            return 0
        fi
        local rc=$?

        # Classify the exit code
        if [[ $rc -eq 4 ]]; then
            err "Authentication error (gh exit 4). Check GH_TOKEN."
            return 1  # No retry for auth failures
        fi

        if [[ $attempt -lt $max ]]; then
            warn "Attempt ${attempt}/${max} failed (exit ${rc}). Retrying in ${current_delay}s..."
            sleep "$current_delay"
            current_delay=$(( current_delay * 2 ))
        else
            err "All ${max} attempts failed."
        fi
        (( attempt++ ))
    done
    return 1
}

# ---------------------------------------------------------------------------
# Operation: post-pr-comment
# ---------------------------------------------------------------------------
# Posts a PR comment. If a previous atlas comment exists (identified by the
# hidden marker), updates it instead of creating a duplicate.
#
# Args: <pr_number> <body_file>
op_post_pr_comment() {
    local pr_number="$1"
    local body_file="$2"

    if [[ -z "$pr_number" || -z "$body_file" ]]; then
        err "post-pr-comment requires <pr_number> and <body_file>"
        exit 2
    fi
    if [[ ! -f "$body_file" ]]; then
        err "Body file not found: ${body_file}"
        exit 2
    fi

    # Prepend the hidden marker to the comment body
    local tmp_body
    tmp_body=$(mktemp)
    {
        echo "$ATLAS_COMMENT_MARKER"
        echo ""
        cat "$body_file"
    } > "$tmp_body"

    log "Looking for existing atlas comment on PR #${pr_number}..."
    local existing_comment_id=""
    existing_comment_id=$(
        gh pr view "$pr_number" --json comments \
            --jq '.comments[] | select(.body | contains("'"$ATLAS_COMMENT_MARKER"'")) | .databaseId' \
            2>/dev/null | head -1 || true
    )

    if [[ -n "$existing_comment_id" ]]; then
        log "Updating existing comment ${existing_comment_id} on PR #${pr_number}..."
        gh_with_retry "$GH_RETRY_MAX" "$GH_RETRY_DELAY" \
            api "repos/{owner}/{repo}/issues/comments/${existing_comment_id}" \
            --method PATCH \
            --field "body=@${tmp_body}"
    else
        log "Creating new comment on PR #${pr_number}..."
        gh_with_retry "$GH_RETRY_MAX" "$GH_RETRY_DELAY" \
            pr comment "$pr_number" --body-file "$tmp_body"
    fi

    rm -f "$tmp_body"
    log "PR comment posted successfully."
}

# ---------------------------------------------------------------------------
# Operation: create-issue
# ---------------------------------------------------------------------------
# Opens a GitHub issue with the atlas labels.
#
# Args: <title> <body_file>
op_create_issue() {
    local title="$1"
    local body_file="$2"

    if [[ -z "$title" || -z "$body_file" ]]; then
        err "create-issue requires <title> and <body_file>"
        exit 2
    fi
    if [[ ! -f "$body_file" ]]; then
        err "Body file not found: ${body_file}"
        exit 2
    fi

    log "Creating issue: ${title}"

    # Build label args — gh expects --label for each label
    local label_args=()
    IFS=',' read -ra labels <<< "$ATLAS_ISSUE_LABELS"
    for label in "${labels[@]}"; do
        label_args+=(--label "${label// /}")
    done

    gh_with_retry "$GH_RETRY_MAX" "$GH_RETRY_DELAY" \
        issue create \
        --title "$title" \
        --body-file "$body_file" \
        "${label_args[@]}"

    log "Issue created successfully."
}

# ---------------------------------------------------------------------------
# Operation: get-pr-files
# ---------------------------------------------------------------------------
# Prints the list of files changed in a PR (newline-separated).
#
# Args: <pr_number>
op_get_pr_files() {
    local pr_number="$1"

    if [[ -z "$pr_number" ]]; then
        err "get-pr-files requires <pr_number>"
        exit 2
    fi

    log "Fetching changed files for PR #${pr_number}..."
    gh_with_retry "$GH_RETRY_MAX" "$GH_RETRY_DELAY" \
        pr view "$pr_number" --json files \
        --jq '.files[].path'
}

# ---------------------------------------------------------------------------
# Operation: check-rate-limit
# ---------------------------------------------------------------------------
op_check_rate_limit() {
    log "Checking GitHub API rate limit..."
    local rate_json
    rate_json=$(gh api rate_limit 2>/dev/null || echo '{}')
    local remaining
    remaining=$(echo "$rate_json" | grep -o '"remaining":[0-9]*' | head -1 | grep -o '[0-9]*' || echo "unknown")
    local limit
    limit=$(echo "$rate_json" | grep -o '"limit":[0-9]*' | head -1 | grep -o '[0-9]*' || echo "unknown")
    local reset_at
    reset_at=$(echo "$rate_json" | grep -o '"reset":[0-9]*' | head -1 | grep -o '[0-9]*' || echo "0")

    local reset_human="unknown"
    if [[ "$reset_at" != "0" ]] && command -v date &>/dev/null; then
        reset_human=$(date -d "@${reset_at}" '+%Y-%m-%d %H:%M:%S UTC' 2>/dev/null || date -r "$reset_at" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo "unknown")
    fi

    echo "GitHub API Rate Limit"
    echo "  Remaining: ${remaining} / ${limit}"
    echo "  Resets at: ${reset_human}"
}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
assert_gh_available

OPERATION="${1:-}"
shift || true

case "$OPERATION" in
    post-pr-comment)
        op_post_pr_comment "${1:-}" "${2:-}"
        ;;
    create-issue)
        op_create_issue "${1:-}" "${2:-}"
        ;;
    get-pr-files)
        op_get_pr_files "${1:-}"
        ;;
    check-rate-limit)
        op_check_rate_limit
        ;;
    --help|-h|help)
        sed -n '3,30p' "$0" | sed 's/^# //'
        exit 0
        ;;
    "")
        err "No operation specified."
        echo "Usage: $0 <operation> [args...]"
        echo "Operations: post-pr-comment, create-issue, get-pr-files, check-rate-limit"
        exit 2
        ;;
    *)
        err "Unknown operation: ${OPERATION}"
        echo "Operations: post-pr-comment, create-issue, get-pr-files, check-rate-limit"
        exit 2
        ;;
esac
