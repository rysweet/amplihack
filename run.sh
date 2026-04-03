#!/bin/bash
cd /tmp/amplihack-workstreams/ws-4215
# Propagate session tree context so child recipes obey depth limits
export AMPLIHACK_TREE_ID=38a3fc70
export AMPLIHACK_SESSION_DEPTH=2
export AMPLIHACK_MAX_DEPTH=6
export AMPLIHACK_MAX_SESSIONS=10
# Bake in the detected delegate so nested ClaudeProcess inherits it (S2)
export AMPLIHACK_DELEGATE='amplihack claude'
export AMPLIHACK_WORKSTREAM_ISSUE=4215
export AMPLIHACK_WORKSTREAM_PROGRESS_FILE=/tmp/amplihack-workstreams/state/ws-4215.progress.json
export AMPLIHACK_WORKSTREAM_STATE_FILE=/tmp/amplihack-workstreams/state/ws-4215.json
export AMPLIHACK_WORKTREE_PATH=''
# Unbuffered stdout/stderr is required so the parent multitask
# orchestrator can stream nested recipe progress live.
exec python3 -u launcher.py
