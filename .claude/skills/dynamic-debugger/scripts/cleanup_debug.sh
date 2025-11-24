#!/usr/bin/env bash
# Cleanup debugging resources

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="${SKILL_DIR}/.dap_mcp.pid"
LOG_FILE="${SKILL_DIR}/.dap_mcp.log"
FORCE_MODE="${1:-}"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

cleanup_server() {
    # Stop server using the lifecycle script
    if [[ -f "$SCRIPT_DIR/start_dap_mcp.sh" ]]; then
        "$SCRIPT_DIR/start_dap_mcp.sh" stop
    else
        log_message "WARNING: start_dap_mcp.sh not found, manual cleanup required"
    fi
}

cleanup_files() {
    log_message "Cleaning up temporary files..."

    # Remove PID and log files
    rm -f "$PID_FILE"

    # Archive log file if it exists and has content
    if [[ -f "$LOG_FILE" ]] && [[ -s "$LOG_FILE" ]]; then
        local archive_file="${SKILL_DIR}/.dap_mcp_$(date +%Y%m%d_%H%M%S).log"
        mv "$LOG_FILE" "$archive_file"
        log_message "Log archived to: $archive_file"
    else
        rm -f "$LOG_FILE"
    fi

    # Remove generated configs
    rm -f "${SKILL_DIR}/configs/generated_"*.json

    # Remove any other temporary files
    rm -f "${SKILL_DIR}"/.dap_mcp.*

    log_message "File cleanup complete"
}

cleanup_processes() {
    log_message "Checking for orphaned debugger processes..."

    # List of debugger processes to check
    local debuggers=("debugpy" "node --inspect" "dlv" "gdb -i=dap" "lldb-dap")
    local killed=0

    for debugger in "${debuggers[@]}"; do
        if pids=$(pgrep -f "$debugger" 2>/dev/null); then
            log_message "Found orphaned $debugger processes: $pids"
            if [[ "$FORCE_MODE" == "--force" ]]; then
                # shellcheck disable=SC2086
                kill -TERM $pids 2>/dev/null || true
                killed=$((killed + 1))
            else
                log_message "Use --force to kill these processes"
            fi
        fi
    done

    if [[ $killed -gt 0 ]]; then
        log_message "Killed $killed orphaned processes"
        sleep 1
    fi
}

verify_cleanup() {
    log_message "Verifying cleanup..."

    local issues=0

    # Check if PID file still exists
    if [[ -f "$PID_FILE" ]]; then
        log_message "WARNING: PID file still exists: $PID_FILE"
        issues=$((issues + 1))
    fi

    # Check if server process is still running
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            log_message "WARNING: Server process still running (PID: $pid)"
            issues=$((issues + 1))
        fi
    fi

    if [[ $issues -eq 0 ]]; then
        log_message "Cleanup verification passed"
        return 0
    else
        log_message "Cleanup verification found $issues issues"
        return 1
    fi
}

main() {
    log_message "Starting debug cleanup..."

    # Stop server
    cleanup_server

    # Clean up files
    cleanup_files

    # Clean up processes (if force mode)
    if [[ "$FORCE_MODE" == "--force" ]]; then
        cleanup_processes
    fi

    # Verify cleanup
    verify_cleanup

    log_message "Debug cleanup complete"
}

# Show usage if requested
if [[ "${1:-}" == "--help" ]] || [[ "${1:-}" == "-h" ]]; then
    echo "Usage: $0 [--force]"
    echo ""
    echo "Clean up debugging resources including:"
    echo "  - Stop dap-mcp server"
    echo "  - Remove temporary files"
    echo "  - Archive log files"
    echo ""
    echo "Options:"
    echo "  --force    Also kill any orphaned debugger processes"
    exit 0
fi

# Run main cleanup
main
