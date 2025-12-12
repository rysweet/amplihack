#!/usr/bin/env bash
# Server lifecycle management for dap-mcp

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
PID_FILE="${SKILL_DIR}/.dap_mcp.pid"
LOG_FILE="${SKILL_DIR}/.dap_mcp.log"
CONFIG_FILE="${1:-}"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >&2
}

start_server() {
    local config_file="$1"

    if [[ -z "$config_file" ]]; then
        log_message "ERROR: Configuration file required"
        echo "Usage: $0 start <config_file>"
        return 1
    fi

    if [[ ! -f "$config_file" ]]; then
        log_message "ERROR: Configuration file not found: $config_file"
        return 1
    fi

    # Check if already running
    if [[ -f "$PID_FILE" ]]; then
        local pid
        pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            log_message "Server already running (PID: $pid)"
            return 0
        else
            log_message "Removing stale PID file"
            rm -f "$PID_FILE"
        fi
    fi

    # Check if dap-mcp is available
    if ! python3 -m dap_mcp --help &> /dev/null; then
        log_message "ERROR: dap-mcp not found. Please install it with: pip install dap-mcp"
        return 1
    fi

    # Start dap-mcp server in background
    log_message "Starting dap-mcp server with config: $config_file"
    nohup python3 -m dap_mcp --config "$config_file" \
        > "$LOG_FILE" 2>&1 &

    local pid=$!
    echo "$pid" > "$PID_FILE"

    # Wait for server to be ready (max 10 seconds)
    local counter=0
    while [[ $counter -lt 10 ]]; do
        if grep -q "Server ready\|listening on" "$LOG_FILE" 2>/dev/null || \
           ps -p "$pid" > /dev/null 2>&1; then
            log_message "Server started successfully (PID: $pid)"
            log_message "Logs available at: $LOG_FILE"
            return 0
        fi
        sleep 1
        counter=$((counter + 1))
    done

    # Check if process is still running
    if ps -p "$pid" > /dev/null 2>&1; then
        log_message "ERROR: Server started but not responding after 10 seconds"
        log_message "Check logs at: $LOG_FILE"
        return 1
    else
        log_message "ERROR: Failed to start server"
        log_message "Last 20 lines of log:"
        tail -n 20 "$LOG_FILE" >&2
        rm -f "$PID_FILE"
        return 1
    fi
}

stop_server() {
    if [[ ! -f "$PID_FILE" ]]; then
        log_message "Server not running (no PID file)"
        return 0
    fi

    local pid
    pid=$(cat "$PID_FILE")

    if ! ps -p "$pid" > /dev/null 2>&1; then
        log_message "Server not running (stale PID file)"
        rm -f "$PID_FILE"
        return 0
    fi

    log_message "Stopping server (PID: $pid)..."

    # Try graceful shutdown first
    kill -TERM "$pid" 2>/dev/null || true

    # Wait up to 5 seconds for graceful shutdown
    local counter=0
    while [[ $counter -lt 5 ]]; do
        if ! ps -p "$pid" > /dev/null 2>&1; then
            log_message "Server stopped gracefully"
            rm -f "$PID_FILE"
            return 0
        fi
        sleep 1
        counter=$((counter + 1))
    done

    # Force kill if still running
    log_message "Force stopping server..."
    kill -KILL "$pid" 2>/dev/null || true
    sleep 1

    if ps -p "$pid" > /dev/null 2>&1; then
        log_message "WARNING: Failed to stop process $pid"
        return 1
    else
        log_message "Server force stopped"
        rm -f "$PID_FILE"
        return 0
    fi
}

restart_server() {
    local config_file="$1"
    log_message "Restarting server..."
    stop_server
    sleep 1
    start_server "$config_file"
}

status_server() {
    if [[ ! -f "$PID_FILE" ]]; then
        echo "Server: NOT RUNNING"
        return 1
    fi

    local pid
    pid=$(cat "$PID_FILE")

    if ps -p "$pid" > /dev/null 2>&1; then
        echo "Server: RUNNING (PID: $pid)"
        echo "Log file: $LOG_FILE"
        echo "PID file: $PID_FILE"
        return 0
    else
        echo "Server: NOT RUNNING (stale PID file)"
        return 1
    fi
}

# Main command handler
case "${1:-}" in
    start)
        start_server "${2:-}"
        ;;
    stop)
        stop_server
        ;;
    restart)
        restart_server "${2:-}"
        ;;
    status)
        status_server
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status} [config_file]"
        echo ""
        echo "Commands:"
        echo "  start <config>  Start dap-mcp server with configuration"
        echo "  stop            Stop running dap-mcp server"
        echo "  restart <config> Restart dap-mcp server"
        echo "  status          Check if server is running"
        exit 1
        ;;
esac
