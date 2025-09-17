#!/bin/bash
# Decision Recorder Hook - Simple reminders for decision recording
# Following ruthless simplicity - just reminds, doesn't enforce

# Session management
SESSION_ID=$(date +"%Y-%m-%d-%H%M%S")
DECISION_LOG=".claude/runtime/logs/${SESSION_ID}/DECISIONS.md"

# Create session directory if it doesn't exist
ensure_session_dir() {
    local session_dir=".claude/runtime/logs/${SESSION_ID}"
    if [ ! -d "$session_dir" ]; then
        mkdir -p "$session_dir"
        echo "📝 Created session directory: $session_dir"
        init_decision_log
    fi
}

# Initialize decision log with header
init_decision_log() {
    cat > "$DECISION_LOG" << EOF
# Decision Record - Session ${SESSION_ID}

**Session Start**: $(date)
**Purpose**: [To be filled by first task]

---

EOF
    echo "✅ Decision log initialized at: $DECISION_LOG"
}

# Record a decision
record_decision() {
    local component="$1"
    local decision="$2"
    local reasoning="$3"
    local alternatives="${4:-None considered}"
    local impact="${5:-To be determined}"
    local next_steps="${6:-Continue with implementation}"

    local timestamp=$(date +"%H:%M:%S")

    cat >> "$DECISION_LOG" << EOF
## [${timestamp}] - ${component}
**Decision**: ${decision}
**Reasoning**: ${reasoning}
**Alternatives**: ${alternatives}
**Impact**: ${impact}
**Next Steps**: ${next_steps}

---

EOF
    echo "📝 Decision recorded for: ${component}"
}

# Hook triggers
on_session_start() {
    ensure_session_dir
    echo "🔴 REMINDER: Decision recording is REQUIRED for this session!"
    echo "📋 Template available at: .claude/templates/DECISION_TEMPLATE.md"
    echo "📝 Session ID: ${SESSION_ID}"
}

on_agent_invocation() {
    local agent_name="$1"
    echo "⚠️ DECISION POINT: Record why you're using the ${agent_name} agent"
    echo "📝 Log location: ${DECISION_LOG}"
}

on_ultrathink_start() {
    echo "🔴 ULTRATHINK DECISION RECORDING REQUIRED!"
    echo "1. Record initial problem decomposition decision"
    echo "2. Document agent selection reasoning"
    echo "3. Log architecture decisions"
    echo "📝 Use: record_decision \"Component\" \"Decision\" \"Reasoning\""
}

on_task_complete() {
    local task_name="$1"
    echo "✅ Task completed: ${task_name}"
    echo "📝 Remember to record completion decision and next steps"
}

on_error_encountered() {
    local error_context="$1"
    echo "⚠️ ERROR DECISION POINT: Document recovery strategy"
    echo "Context: ${error_context}"
    echo "📝 Record: What went wrong, why, and how you'll fix it"
}

# Enforcement check
check_decision_compliance() {
    if [ ! -f "$DECISION_LOG" ]; then
        echo "❌ WARNING: No decision log found for this session!"
        echo "🔴 Creating one now - please document your decisions!"
        ensure_session_dir
        return 1
    fi

    local decision_count=$(grep -c "^## \[" "$DECISION_LOG" 2>/dev/null || echo 0)
    if [ "$decision_count" -eq 0 ]; then
        echo "⚠️ No decisions recorded yet in this session!"
        echo "📝 Use the template at: .claude/templates/DECISION_TEMPLATE.md"
        return 1
    fi

    echo "✅ ${decision_count} decisions recorded so far"
    return 0
}

# Main hook dispatcher
case "${1:-start}" in
    "start")
        on_session_start
        ;;
    "agent")
        on_agent_invocation "$2"
        ;;
    "ultrathink")
        on_ultrathink_start
        ;;
    "task_complete")
        on_task_complete "$2"
        ;;
    "error")
        on_error_encountered "$2"
        ;;
    "check")
        check_decision_compliance
        ;;
    "record")
        shift
        record_decision "$@"
        ;;
    *)
        echo "Usage: $0 {start|agent|ultrathink|task_complete|error|check|record}"
        echo "  start         - Initialize session"
        echo "  agent NAME    - Agent invocation reminder"
        echo "  ultrathink    - Ultrathink specific reminders"
        echo "  task_complete - Task completion reminder"
        echo "  error CONTEXT - Error recovery reminder"
        echo "  check         - Check compliance"
        echo "  record ARGS   - Record a decision"
        ;;
esac