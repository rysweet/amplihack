#!/bin/bash

# Amplihack Status Line
# Shows: directory, git branch, model, tokens, cost, duration
#
# Configure in ~/.claude/settings.json:
#   "statusLine": {
#     "type": "command",
#     "command": "$CLAUDE_PROJECT_DIR/.claude/tools/statusline.sh"
#   }

# Read JSON from Claude Code and normalize (remove newlines for reliable parsing)
input=$(cat | tr -d '\n\r')

# Extract values without jq (portable)
extract_json() {
    local key="$1"
    local default="$2"
    local value=$(echo "$input" | grep -o "\"$key\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" | sed "s/.*: *\"\([^\"]*\)\".*/\1/" | head -1)
    if [ -z "$value" ]; then
        value=$(echo "$input" | grep -o "\"$key\"[[:space:]]*:[[:space:]]*[^,}]*" | sed "s/.*: *\([^,}]*\).*/\1/" | tr -d ' ' | head -1)
    fi
    echo "${value:-$default}"
}

# Extract session data
current_dir=$(extract_json "current_dir" "")
[ -z "$current_dir" ] && current_dir=$(extract_json "cwd" "$(pwd)")
model_name=$(extract_json "display_name" "Claude")
model_id=$(extract_json "id" "")
total_cost=$(extract_json "total_cost_usd" "0")
total_duration=$(extract_json "total_duration_ms" "0")
transcript_path=$(extract_json "transcript_path" "")

# Extract session ID from transcript path
extract_session_id() {
    local transcript_path="$1"

    # Return empty if no transcript path
    [ -z "$transcript_path" ] && return

    # Extract session_id from path pattern: .../sessions/{session_id}/...
    local session_id=$(echo "$transcript_path" | sed -n 's|.*/sessions/\([^/]*\)/.*|\1|p')

    # Fallback: Check CLAUDE_SESSION_ID env var
    if [ -z "$session_id" ] && [ -n "$CLAUDE_SESSION_ID" ]; then
        session_id="$CLAUDE_SESSION_ID"
    fi

    echo "$session_id"
}

# Get session ID
session_id=$(extract_session_id "$transcript_path")

# Change to directory for git
cd "$current_dir" 2>/dev/null || cd "$(pwd)"

# Format directory (~ for home)
display_dir=$(echo "$current_dir" | sed "s|^$HOME|~|")

# Model color (red=Opus, green=Sonnet, blue=Haiku)
case "$model_id" in
    *opus*) model_color="31" ;;
    *sonnet*) model_color="32" ;;
    *haiku*) model_color="34" ;;
    *)
        case "$model_name" in
            *Opus*|*opus*) model_color="31" ;;
            *Sonnet*|*sonnet*) model_color="32" ;;
            *Haiku*|*haiku*) model_color="34" ;;
            *) model_color="37" ;;
        esac
        ;;
esac

# Git info
git_info=""
if git rev-parse --is-inside-work-tree &>/dev/null; then
    branch=$(git symbolic-ref --quiet --short HEAD 2>/dev/null || git rev-parse --short HEAD 2>/dev/null)
    if [ -n "$branch" ]; then
        # Check for uncommitted changes
        if ! git diff-index --quiet HEAD 2>/dev/null; then
            git_color="33"  # Yellow (dirty)
            dirty_marker="*"
        else
            git_color="36"  # Cyan (clean)
            dirty_marker=""
        fi

        # Get remote name
        remote=$(git remote 2>/dev/null | head -1)
        if [ -n "$remote" ]; then
            git_info=" \033[${git_color}m($branch$dirty_marker → $remote)\033[0m"
        else
            git_info=" \033[${git_color}m($branch$dirty_marker)\033[0m"
        fi
    fi
fi

# Calculate tokens from transcript
calculate_tokens() {
    local transcript="$1"

    # Return 0 if transcript doesn't exist or is empty
    if [ -z "$transcript" ] || [ ! -f "$transcript" ]; then
        echo "0"
        return
    fi

    # Extract all token values from transcript using grep/awk
    local input_tokens=$(grep -o '"input_tokens"[[:space:]]*:[[:space:]]*[0-9]*' "$transcript" 2>/dev/null | grep -o '[0-9]*$' | awk '{s+=$1} END {print s+0}')
    local output_tokens=$(grep -o '"output_tokens"[[:space:]]*:[[:space:]]*[0-9]*' "$transcript" 2>/dev/null | grep -o '[0-9]*$' | awk '{s+=$1} END {print s+0}')
    local cache_read=$(grep -o '"cache_read_input_tokens"[[:space:]]*:[[:space:]]*[0-9]*' "$transcript" 2>/dev/null | grep -o '[0-9]*$' | awk '{s+=$1} END {print s+0}')
    local cache_write=$(grep -o '"cache_creation_input_tokens"[[:space:]]*:[[:space:]]*[0-9]*' "$transcript" 2>/dev/null | grep -o '[0-9]*$' | awk '{s+=$1} END {print s+0}')

    # Sum all token types
    echo $((input_tokens + output_tokens + cache_read + cache_write))
}

# Format tokens for display
format_tokens() {
    local tokens="$1"

    # Handle zero/empty
    if [ -z "$tokens" ] || [ "$tokens" -eq 0 ] 2>/dev/null; then
        echo ""
        return
    fi

    # Format based on magnitude
    if [ "$tokens" -ge 1000000 ]; then
        # Millions: 1.2M
        echo "$(awk "BEGIN {printf \"%.1f\", $tokens/1000000}" 2>/dev/null || echo "0")M"
    elif [ "$tokens" -ge 1000 ]; then
        # Thousands: 234K
        echo "$(($tokens / 1000))K"
    else
        # Under 1K: show exact number
        echo "$tokens"
    fi
}

# Get and format token count
total_tokens=$(calculate_tokens "$transcript_path")
tokens_formatted=$(format_tokens "$total_tokens")
if [ -n "$tokens_formatted" ]; then
    tokens_str=" \033[36m🎫 $tokens_formatted\033[0m"
else
    tokens_str=""
fi

# Format cost (handle awk variations)
cost_formatted=$(echo "$total_cost" | awk '{printf "%.2f", $1}' 2>/dev/null || echo "0.00")

# Format duration
if [ "$total_duration" -eq 0 ] 2>/dev/null; then
    duration_str=""
else
    duration_seconds=$((total_duration / 1000))
    if [ $duration_seconds -lt 60 ]; then
        duration_str=" ⏱${duration_seconds}s"
    elif [ $duration_seconds -lt 3600 ]; then
        duration_minutes=$((duration_seconds / 60))
        duration_str=" ⏱${duration_minutes}m"
    else
        duration_hours=$((duration_seconds / 3600))
        duration_str=" ⏱${duration_hours}h"
    fi
fi

# Power-steering session counter (invocations for current session)
# Uses session_id in path like lock counter
power_steering_str=""
# Use CLAUDE_PROJECT_DIR to find counter (works in worktrees)
project_dir="${CLAUDE_PROJECT_DIR:-$current_dir}"
if [ -n "$session_id" ]; then
    ps_count_file="$project_dir/.claude/runtime/power-steering/$session_id/session_count"
    if [ -f "$ps_count_file" ]; then
        ps_count=$(cat "$ps_count_file" 2>/dev/null || echo "0")
        if [ "$ps_count" -gt 0 ] 2>/dev/null; then
            power_steering_str=" \033[35m🚦×$ps_count\033[0m"
        fi
    fi
fi

# Lock mode indicator (if active)
# Note: session_id is NOT required for basic lock indicator - only for counter
lock_str=""
# Use CLAUDE_PROJECT_DIR to find lock file (works in worktrees)
lock_flag="$project_dir/.claude/runtime/locks/.lock_active"
if [ -f "$lock_flag" ]; then
    # Lock is active - show basic indicator first
    lock_str=" \033[33m🔒\033[0m"

    # Optionally enhance with counter if session_id available
    if [ -n "$session_id" ]; then
        lock_counter_file="$project_dir/.claude/runtime/locks/$session_id/lock_invocations.txt"
        if [ -f "$lock_counter_file" ]; then
            lock_count=$(cat "$lock_counter_file" 2>/dev/null || echo "0")
            if [ "$lock_count" -gt 0 ] 2>/dev/null; then
                lock_str=" \033[33m🔒×$lock_count\033[0m"
            fi
        fi
    fi
fi

# Output status line
echo -e "\033[32m$display_dir\033[0m$git_info \033[${model_color}m$model_name\033[0m$tokens_str 💰\$$cost_formatted$duration_str$power_steering_str$lock_str"
