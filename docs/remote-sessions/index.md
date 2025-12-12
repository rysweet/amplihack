# Remote Sessions

Execute amplihack tasks on remote Azure VMs with disconnect-resilient sessions that survive SSH disconnection.

## What Are Remote Sessions?

Remote Sessions allow you to run long-running amplihack tasks on powerful Azure VMs without worrying about laptop disconnections, local resource constraints, or network interruptions. Each session runs in a tmux session on the remote VM, continuing to execute even when you close your terminal.

## Key Features

### Disconnect Resilience

Sessions run in tmux on remote VMs. Close your laptop, lose network connection, or restart your terminal - the work continues uninterrupted.

### Multi-Session Pooling

Run up to 4 concurrent sessions on a single L-size VM (128GB RAM). Intelligent pooling automatically distributes sessions across VMs for efficient Azure quota usage.

### Resource Scaling

Execute complex tasks on VMs with 128GB+ RAM that would overwhelm local machines. Perfect for large codebase analysis, parallel agent orchestration, or memory-intensive operations.

### Transparent Monitoring

Check session output, status, and pool capacity at any time without reconnecting. Use `amplihack remote output` to capture current tmux pane content.

## Quick Navigation

<div class="grid cards" markdown>

-   :material-book-open-variant:{ .lg .middle } **User Guide**

    ---

    Complete guide to using remote sessions including architecture, prerequisites, and common workflows.

    [:octicons-arrow-right-24: Read the User Guide](README.md)

-   :material-console:{ .lg .middle } **CLI Reference**

    ---

    Complete command reference for all `amplihack remote` commands with examples and options.

    [:octicons-arrow-right-24: Browse CLI Reference](CLI_REFERENCE.md)

-   :material-school:{ .lg .middle } **Tutorial**

    ---

    Step-by-step walkthrough of common workflows with real examples and expected outputs.

    [:octicons-arrow-right-24: Start the Tutorial](TUTORIAL.md)

-   :material-cog:{ .lg .middle } **Developer Guide**

    ---

    Internal architecture, component design, and implementation details for contributors.

    [:octicons-arrow-right-24: View Developer Guide](../../.claude/tools/amplihack/remote/README.md)

</div>

## Quick Start

```bash
# Start a task remotely
amplihack remote start "implement user authentication"

# Check all sessions
amplihack remote list

# View session output
amplihack remote output sess-20251125-143022-abc

# Check pool status
amplihack remote status

# Kill a session
amplihack remote kill sess-20251125-143022-abc
```

## Common Use Cases

### Long-Running Refactoring

Run comprehensive refactoring tasks that take hours without blocking your local machine.

```bash
amplihack remote start --vm-size l "refactor entire authentication system"
```

### Parallel Analysis

Launch multiple analysis sessions across different codebases or modules simultaneously.

```bash
amplihack remote start "analyze auth module" "analyze API layer" "analyze database layer"
```

### Resource-Intensive Tasks

Execute tasks requiring more RAM than your laptop provides.

```bash
amplihack remote start --vm-size xl "analyze codebase with 500k+ lines"
```

### Overnight Batch Work

Start tasks at end of day and review results the next morning.

```bash
amplihack remote start "generate comprehensive test suite for entire project"
# Close laptop, go home
# Next morning: amplihack remote list
```

## Architecture Overview

```
Local Machine                  Azure VM Pool
+------------------+           +--------------------------------+
|  amplihack       |   SSH     | VM 1: L-size (128GB RAM)       |
|  remote start    | --------> |  tmux session 1 (32GB)         |
|                  |           |  tmux session 2 (32GB)         |
+------------------+           |  tmux session 3 (32GB)         |
        |                      |  tmux session 4 (32GB)         |
        v                      +--------------------------------+
+------------------+           | VM 2: L-size (128GB RAM)       |
| VMPoolManager    |   SSH     |  tmux session 5 (32GB)         |
| - Multi-session  | --------> |  tmux session 6 (32GB)         |
| - Capacity mgmt  |           |  ... (up to 4 sessions)        |
| - File locking   |           +--------------------------------+
+------------------+
```

## Prerequisites

1. **azlin** - Azure VM provisioning tool

   ```bash
   # Install via uvx from GitHub (not available on PyPI)
   uvx --from git+https://github.com/rysweet/azlin --python 3.11 azlin --help

   # Or create persistent wrapper script
   cat > /usr/local/bin/azlin << 'EOF'
#!/bin/bash
exec uvx --from git+https://github.com/rysweet/azlin --python 3.11 azlin "$@"
EOF
   chmod +x /usr/local/bin/azlin

   # Configure Azure authentication
   azlin auth setup
   ```

2. **Azure CLI** - Authenticated with subscription access

   ```bash
   az login
   ```

3. **ANTHROPIC_API_KEY** - Set in environment

   ```bash
   export ANTHROPIC_API_KEY="sk-ant-..."
   ```

## VM Capacity Tiers

| Size | Azure VM SKU      | RAM   | Max Sessions | Memory/Session | Estimated Cost* |
| ---- | ----------------- | ----- | ------------ | -------------- | --------------- |
| s    | Standard_D8s_v3   | 32GB  | 1            | 32GB           | ~$0.38/hr       |
| m    | Standard_E8s_v5   | 64GB  | 2            | 32GB           | ~$0.50/hr       |
| l    | Standard_E16s_v5  | 128GB | 4            | 32GB           | ~$1.01/hr       |
| xl   | Standard_E32s_v5  | 256GB | 8            | 32GB           | ~$2.02/hr       |

*Costs vary by region and may change. Check [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/) for current rates.

**Recommendation**: Use `--size l` for most work (4 concurrent sessions, 32GB each). Each session gets ample RAM for complex Claude Code tasks.

## Available Features

Remote Sessions includes:

- **VMPoolManager**: Multi-session VM pooling with intelligent capacity management
- **CLI Commands**: list, start, output, kill, status
- **File Locking**: Concurrent state management with fcntl-based exclusive locks
- **Session Isolation**: Each session runs in isolated workspace with dedicated memory allocation
- **Pool Monitoring**: Real-time capacity tracking and utilization metrics
- **Automatic Reuse**: Sessions share VMs when capacity available in same region

## Next Steps

- **New to Remote Sessions?** Start with the [User Guide](README.md)
- **Ready to use it?** Jump to the [Tutorial](TUTORIAL.md)
- **Need command details?** Check the [CLI Reference](CLI_REFERENCE.md)
- **Want to contribute?** Read the [Developer Guide](../../.claude/tools/amplihack/remote/README.md)

## Support

For issues, questions, or feature requests, see:

- [GitHub Issues](https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues)
- [Troubleshooting Guide](README.md#troubleshooting)
- [Developer Documentation](../../.claude/tools/amplihack/remote/README.md)
