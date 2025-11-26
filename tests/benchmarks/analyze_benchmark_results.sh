#!/bin/bash
# Analyze Workflow Compliance Benchmark Results

set -e

echo "=== Analyzing Benchmark Results ==="
echo ""

# Find benchmark PRs
echo "## Finding Benchmark PRs..."
BENCHMARK_PRS=$(gh pr list --label benchmarking --json number,title,state,isDraft,author --jq '.[] | "\(.number)|\(.title)|\(.state)|\(.isDraft)"' 2>/dev/null || echo "")

if [ -z "${BENCHMARK_PRS}" ]; then
    echo "No benchmark PRs found with 'benchmarking' label"
    exit 1
fi

echo "Found PRs:"
echo "${BENCHMARK_PRS}"
echo ""

# Analyze each PR
analyze_pr() {
    local pr_number=$1
    local model_hint=$2

    echo ""
    echo "### PR #${pr_number} Analysis ###"

    # Get PR details
    local pr_details=$(gh pr view ${pr_number} --json title,state,isDraft,body,comments 2>/dev/null)

    # Check if PR has comments (indicates Step 16 was followed)
    local comment_count=$(echo "${pr_details}" | jq '.comments | length')
    echo "- Comments on PR: ${comment_count}"

    # Check if draft
    local is_draft=$(echo "${pr_details}" | jq -r '.isDraft')
    echo "- Is Draft: ${is_draft}"

    # Check state
    local state=$(echo "${pr_details}" | jq -r '.state')
    echo "- State: ${state}"

    # Scoring
    local score=0
    local max_score=5

    # PR exists = 1 point
    ((score++)) || true
    echo "  [+1] PR created"

    # Has benchmarking label = 1 point (we know this since we filtered by label)
    ((score++)) || true
    echo "  [+1] Has 'benchmarking' label"

    # Not draft = 1 point (Step 20 compliance)
    if [ "${is_draft}" = "false" ]; then
        ((score++)) || true
        echo "  [+1] PR is ready (not draft) - Step 20 compliance"
    else
        echo "  [0] PR is still draft - Step 20 NOT completed"
    fi

    # Has review comments = 2 points (Step 16 compliance - this is key!)
    if [ "${comment_count}" -gt 0 ]; then
        ((score+=2)) || true
        echo "  [+2] Has review comments posted - Step 16 compliance"
    else
        echo "  [0] NO review comments posted - Step 16 NOT completed (CRITICAL)"
    fi

    echo ""
    echo "SCORE: ${score}/${max_score}"
    echo ""
}

# Process each PR
echo "${BENCHMARK_PRS}" | while IFS='|' read -r number title state draft; do
    analyze_pr "${number}" "${title}"
done

echo ""
echo "=== Analysis Complete ==="
