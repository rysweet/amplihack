#!/usr/bin/env python3
"""
Decision Logger - Simple utility for recording decisions during sessions.

Following ruthless simplicity:
- Just functions that append to a file
- No complex state management
- Works or doesn't exist
"""

from pathlib import Path
from datetime import datetime


def get_session_id() -> str:
    """Generate session ID for current time."""
    return datetime.now().strftime("%Y-%m-%d-%H%M%S")


def ensure_decision_log(session_id: str = None) -> Path:
    """Create decision log file if it doesn't exist."""
    if not session_id:
        session_id = get_session_id()
    
    log_dir = Path(f".claude/runtime/logs/{session_id}")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_path = log_dir / "DECISIONS.md"
    if not log_path.exists():
        log_path.write_text(
            f"# Decision Log - Session {session_id}\n\n"
            f"Started: {datetime.now().isoformat()}\n\n---\n\n"
        )
    
    return log_path


def log_decision(
    decision: str,
    reasoning: str,
    alternatives: str = "None considered",
    impact: str = "TBD",
    next_steps: str = "Continue implementation",
    session_id: str = None
) -> None:
    """
    Log a decision to the session file.
    
    Args:
        decision: What was decided
        reasoning: Why this approach
        alternatives: What else was considered
        impact: What this changes
        next_steps: What happens next
        session_id: Session to log to (default: current time)
    """
    log_path = ensure_decision_log(session_id)
    
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    entry = f"""## [{timestamp}] Decision
**What**: {decision}
**Why**: {reasoning}
**Alternatives**: {alternatives}
**Impact**: {impact}
**Next**: {next_steps}

---

"""
    
    with open(log_path, "a") as f:
        f.write(entry)


if __name__ == "__main__":
    # Simple CLI usage
    import sys
    
    if len(sys.argv) > 1:
        decision = " ".join(sys.argv[1:])
        log_decision(
            decision=decision,
            reasoning="CLI invocation",
            session_id=get_session_id()
        )
        print(f"Decision logged: {decision}")
    else:
        print("Usage: decision_logger.py <decision text>")
        print("Or import and use: from decision_logger import log_decision")