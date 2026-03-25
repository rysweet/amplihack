# Fleet Admiral Reasoning Loop

The fleet admiral is an autonomous reasoning engine that manages coding agent sessions across multiple Azure VMs. It observes what each agent is doing, decides what action to take, and optionally executes that action — all through SSH via azlin and Bastion tunnels.

## The Loop: PERCEIVE → REASON → ACT → LEARN

Each session goes through four phases on every cycle.

```
                    ┌─────────────┐
                    │   SESSION   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  PERCEIVE   │  Single SSH call gathers all context
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
              ┌─────│   REASON    │  LLM decides action (or fast-path WAIT)
              │     └──────┬──────┘
              │            │
         thinking?    ┌────▼────┐
         skip LLM     │   ACT   │  Execute or display (dry-run vs live)
              │        └────┬────┘
              │             │
              └─────►┌──────▼──────┐
                     │   LEARN     │  Append decision to history
                     └─────────────┘
```

## Phase 1: PERCEIVE

A single SSH command connects to the VM through Azure Bastion and gathers everything the admiral needs to reason about a session. The command uses `--yes` to auto-accept Bastion prompts and semicollon-delimited statements so newlines can be safely stripped by the SSH transport layer.

### Data Gathered

| Data                            | How                                                     | Typical Size          |
| ------------------------------- | ------------------------------------------------------- | --------------------- |
| **Full terminal scrollback**    | `tmux capture-pane -t $SESS -p -S -`                    | ~10,000 chars         |
| **Session transcript (early)**  | First 50 user/assistant messages from Claude Code JSONL | ~15,000 chars         |
| **Session transcript (recent)** | Last 200 user/assistant messages from JSONL             | ~50,000 chars         |
| **Working directory**           | `tmux display-message #{pane_current_path}`             | path string           |
| **Git branch**                  | `git branch --show-current`                             | branch name           |
| **Git remote**                  | `git remote get-url origin`                             | repo URL              |
| **Modified files**              | `git diff --name-only HEAD` (first 10)                  | file list             |
| **PR URL**                      | `gh pr list --head <branch> --json url`                 | URL string            |
| **VM health**                   | `free -m`, `df -h /`, `/proc/loadavg`                   | mem/disk/load metrics |
| **Agent process alive**         | `ps -g $SID` checking for claude/node child             | boolean               |
| **Project objectives**          | `gh issue list --label fleet-objective` on remote       | issue list            |

### Transcript Location

Claude Code stores session logs as JSONL files at:

```
~/.claude/projects/<project-key>/<session-uuid>.jsonl
```

Where `<project-key>` is the working directory with `/` replaced by `-` (e.g., `-home-azureuser-src-amplihack`). The most recent JSONL file (by modification time) is selected.

Message extraction uses `grep` + `sed` (no inline Python) to pull `"text"` fields from lines matching `"type":"user"` or `"type":"assistant"`.

### Status Inference

After capturing the terminal, the agent's status is inferred from the output patterns:

| Status          | Detection Pattern                                              | Meaning                                                 |
| --------------- | -------------------------------------------------------------- | ------------------------------------------------------- |
| `thinking`      | `●` (tool call), `✶`/`✻`/`✢` (processing timer), streaming `⏿` | Agent is actively processing — LLM call or tool running |
| `running`       | Status bar shows `(running)`, substantial output               | Agent producing output                                  |
| `waiting_input` | `[Y/n]`, `⏵⏵ bypass`, prompt ending in `?`                     | Agent needs user input                                  |
| `idle`          | Claude Code `❯` prompt with no typed input                     | Agent at prompt, waiting for direction                  |
| `shell`         | Bare bash `$` prompt, no claude/node process                   | Agent dead or crashed                                   |
| `suspended`     | Bare `$` prompt, but claude/node process still alive           | Agent backgrounded (Ctrl-Z or background feature)       |
| `error`         | `error:`, `traceback`, `fatal:`, `panic:` in output            | Error detected                                          |
| `completed`     | `GOAL_STATUS: ACHIEVED`, PR created/merged                     | Agent finished its task                                 |

### Timing

Each SSH call takes 60–120 seconds through Bastion (tunnel setup + command execution). For a fleet of 6 VMs with 12 sessions, a full PERCEIVE pass takes 12–20 minutes. Sessions are polled sequentially within each VM to avoid overwhelming the Bastion tunnels.

## Phase 2: REASON

### Fast Path (No LLM Call)

If the agent's status is `thinking`, the admiral skips the LLM call entirely and returns:

```json
{
  "action": "wait",
  "confidence": 1.0,
  "reasoning": "Agent is actively thinking/processing -- do not interrupt"
}
```

This is critical: interrupting an agent mid-thought corrupts its context and wastes the tokens already spent on reasoning. The fast path ensures zero latency for the most common case (agents are usually working).

### LLM Path

For non-thinking sessions, the admiral sends all gathered context to the LLM backend.

**Context format** (sent as user prompt):

```
VM: dev, Session: cybergym-intg
Status: idle
Repo: https://github.com/cloud-ecosystem-security/cybergym.git
Branch: fix/webui-health-routing
Files modified: nginx.conf, deploy.sh

Session transcript (early + recent messages):
=== Session start ===
[first 50 message excerpts — what the user originally asked]

=== Recent activity ===
[last 200 message excerpts — what the agent has been doing]

Current terminal output (full scrollback):
[entire tmux scrollback — what's on screen right now]
```

**System prompt** instructs the LLM to:

- Recognize thinking indicators across agent types (Claude Code, Copilot, Amplifier)
- Enforce DEFAULT_WORKFLOW (22 steps) — remind agents if steps are skipped
- Require outside-in testing before marking complete
- Use `wait` or `escalate` when confidence < 60% (never `send_input`)
- Never approve destructive operations
- Prefer the simplest answer that keeps the agent moving forward

The system prompt also includes the **Strategy Dictionary** — a reference of 20 decision strategies the admiral can apply (preemption, coordination, lifecycle management, etc.).

### LLM Backends

The admiral supports multiple LLM backends via a protocol interface:

| Backend            | Default Model   | Max Output Tokens | Detection                                               |
| ------------------ | --------------- | ----------------- | ------------------------------------------------------- |
| `AnthropicBackend` | claude-opus-4-6 | 128,000           | `ANTHROPIC_API_KEY` set (uses streaming API internally) |
| `CopilotBackend`   | gpt-4o          | —                 | Copilot SDK available                                   |

`auto_detect_backend()` checks for `ANTHROPIC_API_KEY` first, then falls back to CopilotBackend. Max output tokens (`DEFAULT_LLM_MAX_TOKENS=128000`). Transcript input context can use up to `TRANSCRIPT_MAX_TOKENS=128000`.

### Response Parsing

The LLM returns JSON (possibly wrapped in markdown). The admiral:

1. Extracts JSON between first `{` and last `}`
2. Validates `action` is one of: `send_input`, `wait`, `escalate`, `mark_complete`, `restart`
3. Clamps `confidence` to [0.0, 1.0]
4. Sanitizes `input_text` and `reasoning` as strings
5. Falls back to `{"action": "wait", "confidence": 0.3}` on parse failure

## Phase 3: ACT

### Dry-Run Mode (fleet scout)

In dry-run, the decision is displayed but not executed:

```
============================================================
DRY RUN: dev/parallel-deploy-wk
============================================================
Status: idle
Branch: fix/acr-import
Repo: https://github.com/cloud-ecosystem-security/cybergym.git

Terminal (last 10 lines):
  | The deployment completed successfully in ~21 minutes...
  | ❯

Decision:
  Session: dev/parallel-deploy-wk
  Action: send_input
  Confidence: 90%
  Reasoning: Deployment succeeded, agent needs to create PR.
  Input: "Great! Please create a comprehensive PR..."
============================================================
```

### Live Mode (fleet advance)

In live mode, decisions are executed via SSH:

**send_input**: Each line of `input_text` is sent as a separate `tmux send-keys` command:

```bash
azlin connect $VM --no-tmux --yes -- \
  tmux send-keys -t '$SESSION' '$LINE' Enter
```

**restart**: Sends Ctrl-C twice to interrupt the stuck process. Does NOT re-run the last command (the `!!` history re-execution was removed as a security fix — it would blindly re-run whatever was last in the shell history):

```bash
azlin connect $VM --no-tmux --yes -- \
  tmux send-keys -t '$SESSION' C-c C-c
```

**wait, escalate, mark_complete**: No SSH command sent. Decision is logged only.

### Safety Gates

Before executing any action, multiple safety checks are applied:

**Confidence thresholds** (actions below threshold are silently suppressed):

| Action          | Minimum Confidence | Rationale                                  |
| --------------- | ------------------ | ------------------------------------------ |
| `send_input`    | 60%                | Low confidence = uncertain what to type    |
| `restart`       | 80%                | Restart is disruptive, need high certainty |
| `wait`          | none               | Always safe                                |
| `escalate`      | none               | Always safe                                |
| `mark_complete` | none               | No side effects                            |

**Safe input allow-list** — Common safe operations (y/n, slash commands, git read-only, test commands) skip the blocklist entirely via `SAFE_INPUT_PATTERNS`, preventing false positives.

**Dangerous input blocklist** — 57 regex patterns across 10 threat categories. If `input_text` matches any pattern (and is NOT on the safe allow-list), the action is converted to `escalate`:

| Category                | Example patterns                                                     |
| ----------------------- | -------------------------------------------------------------------- |
| File system destruction | `rm -rf`, `rm -r /`, `shred`, `dd if=`                               |
| Git destructive         | `git push --force`, `git reset --hard`, `git clean -fd`              |
| SQL destructive         | `DROP TABLE`, `DELETE FROM`, `TRUNCATE TABLE`                        |
| Remote code execution   | `curl\|sh`, `wget\|sh`, `python -c`, `eval(`, `node -e`              |
| Reverse shells          | `nc -e`, `bash -i >& /dev/tcp`, `socat`                              |
| Privilege escalation    | `sudo`, `chmod +s`, `chmod 777`, `chown root`                        |
| Credential access       | `cat /etc/shadow`, `cat ~/.ssh/id_`, `printenv`, `ANTHROPIC_API_KEY` |
| Persistence             | `crontab`, `> ~/.bashrc`, `systemctl enable`                         |
| Data exfiltration       | `scp`, `rsync`, `base64\|curl`                                       |
| Resource exhaustion     | Fork bomb variants                                                   |

**Input sanitization**: All session names and VM names are validated against regex (`[a-zA-Z0-9_.-]`). Input text is passed through `shlex.quote()` before SSH execution.

### Confirmation Mode

`fleet advance` prompts for confirmation by default. Use `--force` to skip:

```
  [dev/parallel-deploy-wk] reasoning...
    -> send_input: "Great! Please create a comprehensive PR..." (conf=90%)
    Execute? [Y/n]:
```

For `restart` actions, the default is `n` (must explicitly confirm).

## Phase 4: LEARN

The decision is appended to the reasoner's `_decisions` list. This enables:

- `dry_run_report()` — aggregate all decisions into a summary
- Action count statistics (wait: 6, send_input: 3, mark_complete: 1)
- Historical analysis of admiral behavior

## Entry Points

| Command          | dry_run | Scope                                          | Loop                   |
| ---------------- | ------- | ---------------------------------------------- | ---------------------- |
| `fleet scout`    | Yes     | All sessions (or `--session vm:name` filtered) | Single pass            |
| `fleet advance`  | No      | All sessions (or `--session vm:name` filtered) | Single pass            |
| `fleet dry-run`  | Yes     | Managed sessions (`--vm` filtered)             | Single pass            |
| `fleet run-once` | No      | All managed sessions                           | Single cycle           |
| `fleet start`    | No      | All managed sessions                           | Continuous at interval |

The key difference between `scout`/`advance` and `dry-run`/`run-once`/`start`:

- **scout/advance** use `FleetTUI.refresh_all()` for discovery (sees all VMs including excluded ones) and `SessionReasoner` directly
- **dry-run/run-once/start** use `FleetAdmiral` which has its own reasoner chain (lifecycle, preemption, coordination, batch-assign) and only operates on managed VMs

## Key Files

| File                        | Purpose                                                     |
| --------------------------- | ----------------------------------------------------------- |
| `fleet_session_reasoner.py` | `SessionReasoner` — the PERCEIVE/REASON/ACT/LEARN loop      |
| `_session_gather.py`        | `gather_context()` — single SSH call to collect all context |
| `_session_context.py`       | `SessionContext` + `SessionDecision` dataclasses            |
| `_status.py`                | `infer_agent_status()` — terminal pattern matching          |
| `_system_prompt.py`         | LLM system prompt + strategy dictionary                     |
| `_backends.py`              | `AnthropicBackend`, `CopilotBackend`                        |
| `_validation.py`            | Input sanitization + dangerous pattern blocklist            |
| `_constants.py`             | Confidence thresholds, timeouts, capacity limits            |
| `_cli_session_ops.py`       | `scout` + `advance` CLI commands                            |
| `_cli_formatters.py`        | Report formatting (scout + advance reports)                 |
| `fleet_admiral.py`          | `FleetAdmiral` — autonomous loop with multi-reasoner chain  |

## Configuration

All tunable values are in `_constants.py`:

| Constant                        | Value   | Purpose                                 |
| ------------------------------- | ------- | --------------------------------------- |
| `DEFAULT_LLM_MAX_TOKENS`        | 128,000 | Max output tokens for reasoning JSON    |
| `TRANSCRIPT_MAX_TOKENS`         | 128,000 | Max input tokens for transcript context |
| `MIN_CONFIDENCE_SEND`           | 0.6     | Minimum confidence to send input        |
| `MIN_CONFIDENCE_RESTART`        | 0.8     | Minimum confidence to restart           |
| `SUBPROCESS_TIMEOUT_SECONDS`    | 120     | SSH timeout (Bastion needs ~90s)        |
| `SSH_ACTION_TIMEOUT_SECONDS`    | 30      | send_input/restart SSH timeout          |
| `AZ_CLI_TIMEOUT_SECONDS`        | 30      | az vm list timeout (no Bastion)         |
| `DEFAULT_POLL_INTERVAL_SECONDS` | 60      | Admiral loop interval                   |
| `DEFAULT_CAPTURE_LINES`         | 50      | TUI dashboard capture depth             |
| `DEFAULT_DETAIL_CAPTURE_LINES`  | 500     | Detail view capture depth               |
| `DEFAULT_MAX_AGENTS_PER_VM`     | 3       | Max concurrent agents                   |
