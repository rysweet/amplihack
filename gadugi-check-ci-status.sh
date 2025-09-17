#!/bin/bash
# CI Status Checker Script
# This script checks the CI status for the current PR or a specified PR number

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2

    case $status in
        "success"|"SUCCESS")
            echo -e "${GREEN}✓ ${message}${NC}"
            ;;
        "failure"|"FAILURE")
            echo -e "${RED}✗ ${message}${NC}"
            ;;
        "pending"|"IN_PROGRESS")
            echo -e "${YELLOW}⏳ ${message}${NC}"
            ;;
        *)
            echo -e "${BLUE}• ${message}${NC}"
            ;;
    esac
}

# Function to get PR number
get_pr_number() {
    if [ -n "${1:-}" ]; then
        echo "$1"
    else
        # Try to get PR number from current branch
        local current_branch=$(git branch --show-current)
        gh pr list --head "$current_branch" --json number --jq '.[0].number' 2>/dev/null || echo ""
    fi
}

# Function to check CI status
check_ci_status() {
    local pr_number=$1

    echo -e "${BLUE}Checking CI status for PR #${pr_number}...${NC}\n"

    # Get PR info including CI status
    local pr_info=$(gh pr view "$pr_number" --json state,mergeable,statusCheckRollup 2>/dev/null)

    if [ -z "$pr_info" ]; then
        echo -e "${RED}Error: Could not fetch PR information${NC}"
        return 1
    fi

    # Parse PR state and mergeable status
    local pr_state=$(echo "$pr_info" | jq -r '.state')
    local mergeable=$(echo "$pr_info" | jq -r '.mergeable')

    echo -e "${BLUE}PR State:${NC} $pr_state"
    echo -e "${BLUE}Mergeable:${NC} $mergeable\n"

    # Parse and display CI checks
    echo -e "${BLUE}CI Checks:${NC}"
    echo "$pr_info" | jq -r '.statusCheckRollup[] | "\(.name)|\(.status)|\(.conclusion)"' | while IFS='|' read -r name status conclusion; do
        if [ "$status" = "COMPLETED" ]; then
            print_status "$conclusion" "$name"
        else
            print_status "$status" "$name (in progress)"
        fi
    done

    # Check for failed jobs and get details
    local failed_count=$(echo "$pr_info" | jq -r '.statusCheckRollup[] | select(.conclusion == "FAILURE") | .name' | wc -l)

    if [ "$failed_count" -gt 0 ]; then
        echo -e "\n${RED}Failed checks detected. Getting details...${NC}\n"

        # Get the latest workflow run
        local latest_run=$(gh run list --limit 1 --json databaseId --jq '.[0].databaseId')

        if [ -n "$latest_run" ]; then
            echo -e "${BLUE}Latest workflow run ID:${NC} $latest_run\n"

            # Get failed job details
            local failed_jobs=$(gh run view "$latest_run" --json jobs | jq -r '.jobs[] | select(.conclusion == "failure") | "\(.name)|\(.databaseId)"')

            if [ -n "$failed_jobs" ]; then
                echo -e "${BLUE}Failed jobs:${NC}"
                echo "$failed_jobs" | while IFS='|' read -r job_name job_id; do
                    echo -e "${RED}  • $job_name (ID: $job_id)${NC}"

                    # Option to view logs
                    echo -e "    To view logs: ${YELLOW}gh run view $latest_run --job $job_id --log-failed${NC}"
                done
            fi
        fi
    fi

    # Summary
    echo -e "\n${BLUE}Summary:${NC}"
    local total_checks=$(echo "$pr_info" | jq -r '.statusCheckRollup | length')
    local completed_checks=$(echo "$pr_info" | jq -r '.statusCheckRollup[] | select(.status == "COMPLETED") | .name' | wc -l)
    local successful_checks=$(echo "$pr_info" | jq -r '.statusCheckRollup[] | select(.conclusion == "SUCCESS") | .name' | wc -l)

    echo -e "Total checks: $total_checks"
    echo -e "Completed: $completed_checks"
    echo -e "Successful: $successful_checks"
    echo -e "Failed: $failed_count"

    if [ "$failed_count" -eq 0 ] && [ "$completed_checks" -eq "$total_checks" ]; then
        echo -e "\n${GREEN}All CI checks passed! 🎉${NC}"
        return 0
    elif [ "$failed_count" -gt 0 ]; then
        echo -e "\n${RED}CI checks failed. Please fix the issues above.${NC}"
        return 1
    else
        echo -e "\n${YELLOW}CI checks still in progress...${NC}"
        return 2
    fi
}

# Main execution
main() {
    # Check if gh CLI is available
    if ! command -v gh &> /dev/null; then
        echo -e "${RED}Error: GitHub CLI (gh) is not installed${NC}"
        exit 1
    fi

    # Get PR number
    local pr_number=$(get_pr_number "${1:-}")

    if [ -z "$pr_number" ]; then
        echo -e "${RED}Error: No PR number provided and could not detect from current branch${NC}"
        echo "Usage: $0 [PR_NUMBER]"
        exit 1
    fi

    # Check CI status
    check_ci_status "$pr_number"
}

# Run main function
main "$@"
