# TUI Testing with PTY Virtualization - Complete Explanation

**Date**: 2026-01-20
**Context**: Testing Claude Code plugin in TUI without a real terminal

## The Problem: Why TUI Testing is Different

### Traditional Command-Line Testing

```bash
# This works fine for CLI apps
./my-app --version > output.txt
grep "1.0.0" output.txt
```

**Why it works**: CLI apps just read stdin and write to stdout/stderr. No terminal required.

### TUI Apps Need a Real Terminal

```bash
# This FAILS for TUI apps
claude /plugin > output.txt  # ❌ TUI won't start
```

**Why it fails**: TUI apps (like Claude Code, vim, htop) check if they're running in a terminal using `isatty()`:

```c
if (!isatty(STDIN_FILENO)) {
    fprintf(stderr, "Error: Must run in a terminal\n");
    exit(1);
}
```

## The Solution: Pseudo-Terminals (PTY)

### What is a PTY?

A **pseudo-terminal (PTY)** is a software-emulated terminal. It consists of two parts:

1. **Master side**: Controlled by our test program
2. **Slave side**: Used by the TUI application (thinks it's a real terminal)

```
┌─────────────────┐
│  Test Program   │
│   (master)      │
└────────┬────────┘
         │ PTY
         │
┌────────▼────────┐
│  Claude Code    │
│   (slave)       │
│  Thinks it's    │
│  in a real TTY  │
└─────────────────┘
```

### How node-pty Implements PTY

`node-pty` is a Node.js library that creates real PTYs using OS-specific APIs:

- **Linux**: Uses `openpty()` and `fork()` system calls
- **macOS**: Uses `forkpty()` system call
- **Windows**: Uses ConPTY (Windows 10+) or WinPTY API

```javascript
const pty = require("node-pty");

// This creates a REAL pseudo-terminal
const ptyProcess = pty.spawn("claude", ["--help"], {
  name: "xterm-256color",
  cols: 80,
  rows: 24,
});

// Now claude thinks it's running in a terminal!
// isatty() returns TRUE
```

## Our Implementation: Three Approaches

### ❌ Approach 1 (Initial - WRONG): Setting TERM Variable

```bash
# This DOESN'T WORK
TERM=xterm-256color claude /plugin  # Still no TTY!
```

**Problem**: Setting `TERM` environment variable doesn't create a TTY. The application still sees stdout is a pipe/file, not a terminal.

### ⚠️ Approach 2: expect (TCL Automation)

```tcl
#!/usr/bin/expect -f
spawn claude --plugin-dir ~/.amplihack/.claude/
send "/plugin\r"
expect "amplihack"
```

**How it works**: `expect`'s `spawn` command creates a PTY internally.

**Pros**:

- ✅ Creates real PTY
- ✅ No compilation needed
- ✅ Simple syntax

**Cons**:

- ⚠️ TCL language (not mainstream)
- ⚠️ Harder to debug
- ⚠️ Less control over PTY settings

### ✅ Approach 3: node-pty (BEST)

```javascript
const pty = require("node-pty");

const ptyProcess = pty.spawn(
  "claude",
  ["--plugin-dir", "~/.amplihack/.claude/", "--add-dir", "/tmp"],
  {
    name: "xterm-256color",
    cols: 120,
    rows: 40,
    env: {
      ...process.env,
      TERM: "xterm-256color",
    },
  }
);

ptyProcess.write("/plugin\r");

ptyProcess.onData((data) => {
  console.log("Received:", data);
  if (data.includes("amplihack")) {
    console.log("✅ Plugin detected!");
  }
});
```

**Why this is best**:

- ✅ **Real PTY**: Creates actual pseudo-terminal (like SSH or tmux)
- ✅ **Full control**: Set terminal size, type, environment
- ✅ **Cross-platform**: Works on Linux, macOS, Windows
- ✅ **Programmatic**: Easy to integrate with test frameworks
- ✅ **Professional**: Used by VS Code, Hyper, and other terminal apps
- ✅ **CI/CD friendly**: No display/X11 required

## How Gadugi Uses PTY

Gadugi-agentic-test framework uses node-pty for TUI testing:

### PTYManager Class

```typescript
// From gadugi-agentic-test/src/utils/terminal/PTYManager.ts
import * as pty from "node-pty";

export class PTYManager extends EventEmitter {
  private pty: pty.IPty | null = null;

  public spawn(): Promise<void> {
    this.pty = pty.spawn(this.config.shell, this.config.args, {
      cwd: this.config.cwd,
      env: this.config.env,
      cols: this.config.cols,
      rows: this.config.rows,
    });

    // Real PTY created!
    this.pty.onData((data: string) => {
      this.emit("data", data);
    });
  }

  public write(data: string): boolean {
    this.pty.write(data);
  }
}
```

### Why PTYManager Matters

1. **Cross-platform abstraction**: Handles OS differences
2. **Event-driven**: Async I/O for responsive testing
3. **Buffer management**: Handles large outputs
4. **Lifecycle management**: Proper cleanup and signal handling

## Real-World Analogy

### Without PTY (Pipe)

```
Test → stdout (pipe) → File
              ↓
           No TTY!
         TUI refuses
         to start
```

### With PTY

```
Test ←→ PTY Master ←→ PTY Slave ←→ TUI App
                                    ↓
                                 Sees TTY!
                               Starts normally
```

**It's like**:

- **Without PTY**: Talking to someone through a hole in the wall (pipe)
- **With PTY**: Using a phone (bidirectional, feels like they're there)

## Technical Details: How isatty() Works

When Claude Code starts, it checks if it's in a terminal:

```rust
// Simplified Rust code (Claude Code is likely in Rust)
use std::io::IsTerminal;

fn main() {
    if !std::io::stdin().is_terminal() {
        eprintln!("Error: Not running in a terminal");
        std::process::exit(1);
    }

    // Start TUI...
}
```

**With regular pipe**:

```c
isatty(STDIN_FILENO)  // Returns 0 (false) - not a TTY
```

**With PTY**:

```c
isatty(STDIN_FILENO)  // Returns 1 (true) - IS a TTY!
```

## Comparison Table

| Method           | Creates Real PTY? | Works in CI? | Cross-platform? | Easy to Debug? | Recommended              |
| ---------------- | ----------------- | ------------ | --------------- | -------------- | ------------------------ |
| `command > file` | ❌ No             | ✅ Yes       | ✅ Yes          | ✅ Yes         | ❌ Doesn't work for TUIs |
| `TERM=xterm`     | ❌ No             | ✅ Yes       | ✅ Yes          | ✅ Yes         | ❌ Doesn't create TTY    |
| `expect`         | ✅ Yes            | ✅ Yes       | ✅ Yes          | ⚠️ Moderate    | ✅ Good option           |
| `node-pty`       | ✅ Yes            | ✅ Yes       | ✅ Yes          | ✅ Yes         | ✅ **BEST**              |
| `script` command | ✅ Yes            | ⚠️ Sometimes | ⚠️ Unix only    | ⚠️ Moderate    | ⚠️ Okay                  |

## Common Misconceptions

### ❌ "Setting TERM variable creates a terminal"

**False**. `TERM` just tells programs what terminal features are available. It doesn't create a TTY.

### ❌ "Redirecting stdin creates an interactive session"

**False**. `echo "/plugin" | claude` still shows stdin as a pipe, not a TTY.

### ❌ "Only Electron apps need PTY"

**False**. ANY TUI application (vim, htop, Claude Code) needs a real terminal or PTY.

### ✅ "PTY is like SSH for local processes"

**True**! SSH creates a PTY on the remote machine. node-pty does the same locally.

## Our Final Implementation

We provide **three test options**:

### 1. **node-pty Test** (Recommended)

```bash
cd tests/agentic
npm install
node test-claude-plugin-pty.js
```

- Uses real PTY
- Production-quality approach
- What professionals use

### 2. **expect Test** (Alternative)

```bash
cd tests/agentic
./run-plugin-test.sh
```

- Uses expect (TCL)
- No compilation needed
- Simpler but less control

### 3. **Gadugi Framework** (Future)

```yaml
# claude-code-plugin-test.yaml
steps:
  - action: launch_tui
    command: claude
    # Gadugi uses PTYManager internally
```

- Full framework integration
- When gadugi is stable

## Key Takeaways

1. **TUI apps REQUIRE a real terminal (TTY)**
2. **Pseudo-terminals (PTY) simulate real terminals**
3. **node-pty creates real PTYs programmatically**
4. **This is NOT unique to Claude Code** - all TUIs need this
5. **PTY is the professional solution** - used by VS Code, terminals, SSH

## References

- **node-pty**: https://github.com/microsoft/node-pty
- **Unix PTY**: `man pty` on any Unix system
- **POSIX spec**: https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap11.html
- **Gadugi Framework**: https://github.com/rysweet/gadugi-agentic-test

---

**🏴‍☠️ In pirate terms**:

- **Regular pipe** = Messagin' in a bottle (one-way, no confirmation)
- **PTY** = Ship-to-ship speakin' trumpet (two-way, feels like ye be there!)

_Generated by amplihack agentic testing system on 2026-01-20_
