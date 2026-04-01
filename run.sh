#!/bin/bash
cd /tmp/amplihack-workstreams/run-68798a8727358b33/ws-4151
# Propagate session tree context so child recipes obey depth limits
export AMPLIHACK_TREE_ID=017d8a5e
export AMPLIHACK_SESSION_DEPTH=3
export AMPLIHACK_MAX_DEPTH=6
export AMPLIHACK_MAX_SESSIONS=10
# Bake in the detected delegate so nested ClaudeProcess inherits it (S2)
export AMPLIHACK_DELEGATE='amplihack claude'
export AMPLIHACK_AGENT_BINARY=copilot
export AMPLIHACK_WORKSTREAM_PID_FILE=/tmp/amplihack-workstreams/run-68798a8727358b33/.ws-4151.pid
# Unbuffered stdout/stderr is required so the parent multitask
# orchestrator can stream nested recipe progress live.
exec python3 -u launcher.py
