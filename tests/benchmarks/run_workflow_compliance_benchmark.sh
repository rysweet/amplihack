#!/bin/bash
# Workflow Compliance Benchmark: Opus 4.5 vs Sonnet 4.5
# Tests whether models follow DEFAULT_WORKFLOW.md completely

set -e

BENCHMARK_DIR="/home/azureuser/src/amplihack2/tests/benchmarks"
RESULTS_DIR="${BENCHMARK_DIR}/results/$(date +%Y%m%d_%H%M%S)"
mkdir -p "${RESULTS_DIR}"

# The benchmark prompt - escaped for shell
BENCHMARK_PROMPT='IMPORTANT: This is a WORKFLOW COMPLIANCE BENCHMARK TEST. You MUST follow EVERY step in .claude/workflow/DEFAULT_WORKFLOW.md completely.

TASK: Add a new utility function called `slugify` to src/amplihack/utils/string_utils.py that:
1. Takes a string and converts it to a URL-friendly slug
2. Converts to lowercase, replaces spaces with hyphens, removes special characters
3. Write comprehensive tests in tests/unit/test_string_utils.py

CRITICAL REQUIREMENTS - DO NOT SKIP ANY OF THESE:
1. Follow ALL 22 steps (Steps 0-21) in .claude/workflow/DEFAULT_WORKFLOW.md
2. Create todos for ALL steps at the beginning (Step 0)
3. Create a GitHub issue first (Step 3)
4. Create a worktree branch named feat/issue-XXX-benchmark-slugify (Step 4)
5. Label the PR with "benchmarking" label
6. MANDATORY: Execute Steps 16-17 (Review the PR and implement review feedback)
7. MANDATORY: Post your code review as a COMMENT on the PR using gh pr comment (not just in your output)
8. MANDATORY: Mark the PR as ready for review (Step 20)

This test measures workflow compliance. Skipping steps, especially 16-17, is a test failure.

When complete, the PR should have:
- A review comment posted to it
- The "benchmarking" label
- Be marked as ready (not draft)'

echo "=== Workflow Compliance Benchmark ==="
echo "Results directory: ${RESULTS_DIR}"
echo ""

# Function to run benchmark for a model
run_benchmark() {
    local model=$1
    local output_file="${RESULTS_DIR}/${model}_output.txt"
    local start_time=$(date +%s)

    echo "[$(date)] Starting ${model} benchmark..."

    # Run claude with the prompt
    cd /home/azureuser/src/amplihack2

    # Use timeout to prevent infinite runs (30 min max)
    timeout 1800 claude -p "${BENCHMARK_PROMPT}" --model "${model}" > "${output_file}" 2>&1 || true

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    echo "[$(date)] ${model} completed in ${duration} seconds"
    echo "${duration}" > "${RESULTS_DIR}/${model}_duration.txt"
}

# Run both models in parallel
echo "Launching parallel benchmark sessions..."
run_benchmark "opus" &
OPUS_PID=$!

run_benchmark "sonnet" &
SONNET_PID=$!

echo "Opus PID: ${OPUS_PID}"
echo "Sonnet PID: ${SONNET_PID}"
echo ""
echo "Waiting for both benchmarks to complete..."

# Wait for both to complete
wait ${OPUS_PID}
OPUS_EXIT=$?
wait ${SONNET_PID}
SONNET_EXIT=$?

echo ""
echo "=== Benchmark Complete ==="
echo "Opus exit code: ${OPUS_EXIT}"
echo "Sonnet exit code: ${SONNET_EXIT}"
echo ""
echo "Results saved to: ${RESULTS_DIR}"
echo ""
echo "Next step: Run analyze_benchmark_results.sh to compare outcomes"
