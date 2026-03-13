# Environment Variables Reference

This page documents all environment variables recognized by amplihack.
Set these variables before launching amplihack to configure its behavior.

---

## Agent Selection

### `AMPLIHACK_AGENT_BINARY`

Specifies which agent binary amplihack delegates work to.
Set automatically by the launcher based on the chosen subcommand
(`claude`, `copilot`, `codex`, `amplifier`), but can be overridden to
use a custom or alternate binary.

| Value | Default | Since |
|-------|---------|-------|
| Binary name (e.g. `claude`, `copilot`, `codex`) | Set by launcher | 0.6.43 |

**Example**:

```bash
# Force copilot binary even when running the `claude` subcommand
AMPLIHACK_AGENT_BINARY=copilot amplihack claude
```

> **Note**: The Rust recipe runner and delegation scripts read this variable
> to forward the correct agent binary. Override with care — mismatches between
> the launcher subcommand and this variable can cause unexpected behaviour.

---

## Installation & Updates

### `AMPLIHACK_NONINTERACTIVE`

Disables interactive prompts in the launcher and installer.
Use this in CI/CD pipelines or scripted environments where there is no
terminal attached.

| Value | Effect |
|-------|--------|
| `1`, `true`, `yes` | Skips all interactive prompts; shows manual instructions instead |
| *(unset)* | Interactive prompts enabled when a TTY is detected |

**Example**:

```bash
AMPLIHACK_NONINTERACTIVE=1 amplihack claude
```

> Automatically skips auto-update checks and dependency install prompts.
> See [Interactive Installation](INTERACTIVE_INSTALLATION.md) for details.

---

### `AMPLIHACK_SKIP_UPDATE`

Bypasses the version update check on launch.

| Value | Effect |
|-------|--------|
| `1` | Skip update check |
| *(unset)* | Update check runs normally |

**Example**:

```bash
AMPLIHACK_SKIP_UPDATE=1 amplihack claude
```

---

### `AMPLIHACK_AUTO_INSTALL`

Controls automatic installation of missing agent CLI tools (e.g. `claude`).

| Value | Effect |
|-------|--------|
| `0`, `false`, `no` | Disables auto-installation |
| *(unset)* | Auto-installation enabled |

**Example**:

```bash
AMPLIHACK_AUTO_INSTALL=0 amplihack claude
```

---

### `AMPLIHACK_UVX_MODE`

Forces the launcher into uvx invocation mode.

| Value | Effect |
|-------|--------|
| `1`, `true`, `yes` | Enables uvx mode |
| *(unset)* | Mode auto-detected |

---

## Paths & Layout

### `AMPLIHACK_HOME`

Overrides the amplihack installation root directory.
By default amplihack resolves assets relative to the installed package.

| Value | Default |
|-------|---------|
| Absolute path to directory | Auto-detected from package |

**Example**:

```bash
AMPLIHACK_HOME=/opt/my-amplihack amplihack claude
```

---

## Mode & Runtime

### `AMPLIHACK_MODE`

Overrides the automatically detected operation mode.

| Value | Effect |
|-------|--------|
| Mode name string | Forces the specified mode |
| *(unset)* | Mode auto-detected |

---

### `AMPLIHACK_HOOK_ENGINE`

Selects the hook execution engine.

| Value | Effect |
|-------|--------|
| `rust` | Use Rust-compiled hook binaries (faster) |
| `python` | Use Python hook scripts (default fallback) |
| *(unset)* | Rust used when binary is available; Python otherwise |

**Example**:

```bash
AMPLIHACK_HOOK_ENGINE=rust amplihack claude
```

---

## Proxy & Streaming

### `AMPLIHACK_USE_LITELLM`

Enables the LiteLLM router in the proxy layer.

| Value | Default |
|-------|---------|
| `true` / `false` | `true` |

---

### `AMPLIHACK_PROXY_TIMEOUT`

Sets the proxy request timeout in seconds.

| Value | Default | Constraints |
|-------|---------|-------------|
| Float (seconds) | `120.0` | Must be positive and ≤ 600 |

**Example**:

```bash
AMPLIHACK_PROXY_TIMEOUT=300 amplihack claude
```

---

### `AMPLIHACK_TOOL_ONE_PER_RESPONSE`

When enabled, restricts the proxy to one tool call per model response turn.

| Value | Default |
|-------|---------|
| `true` / `false` | `true` |

---

### `AMPLIHACK_TOOL_RETRY_ATTEMPTS`

Number of times the proxy retries a failed tool call.

| Value | Default |
|-------|---------|
| Integer | `3` |

---

### `AMPLIHACK_TOOL_TIMEOUT`

Per-tool-call timeout in seconds.

| Value | Default |
|-------|---------|
| Integer (seconds) | `30` |

---

### `AMPLIHACK_TOOL_FALLBACK`

Enables graceful fallback when a tool call fails.

| Value | Default |
|-------|---------|
| `true` / `false` | `true` |

---

### `AMPLIHACK_TOOL_STREAM_BUFFER`

Buffer size (bytes) for tool call streaming.

| Value | Default |
|-------|---------|
| Integer (bytes) | `1024` |

---

### `AMPLIHACK_REASONING_EFFORT`

Enables extended reasoning effort mode in the proxy.

| Value | Default |
|-------|---------|
| `true` / `false` | `false` |

---

## Tracing & Observability

### `AMPLIHACK_TRACE_LOGGING`

Enables JSONL trace logging of all LLM interactions.

| Value | Default |
|-------|---------|
| `true` / `false` | `false` (disabled) |

**Example**:

```bash
AMPLIHACK_TRACE_LOGGING=true amplihack claude
```

---

### `AMPLIHACK_TRACE_FILE`

Path to the trace log file written when `AMPLIHACK_TRACE_LOGGING=true`.

| Value | Default |
|-------|---------|
| Absolute file path | `~/.amplihack/trace.jsonl` |

**Example**:

```bash
AMPLIHACK_TRACE_LOGGING=true \
AMPLIHACK_TRACE_FILE=/tmp/my-session.jsonl \
amplihack claude
```

---

## CI / Scripted Environments

When running amplihack in a CI pipeline or other non-interactive context,
set the following combination to suppress all prompts and version update
traffic:

```bash
export AMPLIHACK_NONINTERACTIVE=1
export AMPLIHACK_SKIP_UPDATE=1
export AMPLIHACK_AUTO_INSTALL=0
```

amplihack also auto-detects common CI markers (`CI`, `GITHUB_ACTIONS`,
`JENKINS_URL`, isolated `HOME`, restricted `PATH`) and suppresses interactive
behaviour automatically.

---

## Related

- [Interactive Installation](INTERACTIVE_INSTALLATION.md) — dependency install
  prompts and CI behaviour
- [Prerequisites](PREREQUISITES.md) — required tools
- [Proxy Configuration](PROXY_CONFIG_GUIDE.md) — advanced proxy settings
