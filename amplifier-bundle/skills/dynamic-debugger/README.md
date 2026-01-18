# Dynamic Debugger Skill

Interactive debugging for Python, C/C++, and Rust through natural language commands via the Debug Adapter Protocol (DAP) and Model Context Protocol (MCP).

## Quick Start

### Installation

1. **Install dap-mcp server:**

   ```bash
   pip install dap-mcp
   # or
   uv pip install dap-mcp
   ```

2. **Install language debuggers:**

   ```bash
   # Python
   pip install debugpy

   # C/C++/Rust (lldb with DAP support)
   # macOS: brew install llvm
   # Ubuntu: sudo apt install lldb
   ```

3. **Enable the skill** (opt-in):

   Edit `SKILL.md` frontmatter and remove or set to `false`:

   ```yaml
   disableModelInvocation: false # Enable auto-activation
   ```

   Or invoke explicitly:

   ```
   User: "Use the dynamic-debugger skill to debug this Python function"
   ```

### Basic Usage

Once enabled, just ask Claude to debug in natural language:

```
"Debug this Python function"
"Set a breakpoint at line 42"
"Step through this code"
"What's the value of userId?"
```

The skill automatically:

1. Detects debugging intent
2. Identifies project language
3. Starts dap-mcp server
4. Provides debugging capabilities
5. Cleans up on exit

## Supported Languages

**Current (via dap-mcp):**

- ✅ Python (debugpy)
- ✅ C/C++ (lldb)
- ✅ Rust (lldb)

**Planned (see [issue #1570](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1570)):**

- 📋 JavaScript/TypeScript
- 📋 Go
- 📋 Java
- 📋 .NET

## Documentation

- **SKILL.md** - Main skill file with quick start and navigation guide
- **reference.md** - Complete API reference for debugging commands
- **examples.md** - Working code examples for each supported language
- **patterns.md** - Production debugging patterns and best practices
- **tests/MCP_TESTING.md** - Testing protocol and validation guide

## Architecture

```
dynamic-debugger/
├── SKILL.md              # Main skill (progressive disclosure)
├── README.md             # This file
├── reference.md          # API reference (on-demand)
├── examples.md           # Working examples (on-demand)
├── patterns.md           # Best practices (on-demand)
├── configs/
│   ├── debugpy.json      # Python debugger config
│   ├── lldb.json         # C/C++/Rust debugger config
│   └── future/           # Planned language configs
├── scripts/
│   ├── detect_language.py       # Auto language detection
│   ├── generate_dap_config.py   # Config generation
│   ├── monitor_session.py       # Resource monitoring
│   ├── start_dap_mcp.sh         # Server lifecycle
│   └── cleanup_debug.sh         # Cleanup
└── tests/                # Comprehensive test suite
```

## Features

- **Natural Language Interface**: Debug using conversational commands
- **Auto-Detection**: Automatically identifies debugging intent and language
- **Progressive Disclosure**: Loads docs on-demand (token efficient)
- **Resource Management**: 4GB memory limit, 30min session timeout
- **Graceful Cleanup**: Automatic cleanup on exit

## Testing

```bash
cd .claude/skills/dynamic-debugger/tests

# Run unit + integration tests
pytest

# Run E2E integration test
python3 test_mcp_integration.py

# Run MCP protocol test
python3 test_mcp_client.py
```

**Test Coverage:**

- 55 unit/integration tests
- E2E server lifecycle validation
- MCP protocol testing

## Security Considerations

⚠️ **Important:**

- Full filesystem access required for debugging
- Debugger processes run with your user privileges
- Can access memory, environment variables, credentials
- **Only debug code you trust**

See SKILL.md Security section for complete details.

## Philosophy

**Score: 92/100 (A-grade)**

- Ruthless simplicity: Delegates complexity to dap-mcp
- Zero-BS: All code works, no stubs (55 tests passing)
- Brick philosophy: Self-contained, regeneratable modules
- Progressive disclosure: 1,400 token base, on-demand loading

## Contributing

See [issue #1570](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1570) for planned language extensions.

## Issues

- **Parent**: [#1552](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1552) - Dynamic debugger skill
- **PR**: [#1553](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/pull/1553) - Implementation
- **Future**: [#1570](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues/1570) - Additional languages

## License

Part of amplihack framework.

---

**Version**: 1.0.0
**Status**: Production-ready for Python, C/C++, Rust
**Maintained**: Yes
