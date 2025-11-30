# Remote Execution Module

**Version**: 0.1.0 (Phase 1 MVP)
**Status**: ✅ Implementation Complete

## Overview

This module enables executing amplihack commands on remote Azure VMs using azlin for provisioning and management. It provides secure context packaging, VM lifecycle orchestration, remote execution, and result integration.

## Architecture

```
┌─────────────────────┐
│  Local Machine      │
│                     │
│  1. Package Context │──┐
│  2. Transfer        │  │ SSH/SCP
│  3. Execute         │  │ via azlin
│  4. Retrieve        │  │
│  5. Integrate       │  │
└─────────────────────┘  │
                         │
┌────────────────────────┼────────┐
│  Azure VM (azlin)      ↓        │
│                                 │
│  1. Receive context             │
│  2. Restore git + .claude       │
│  3. Run amplihack               │
│  4. Package results             │
│  5. Send back                   │
└─────────────────────────────────┘
```

## Components

### 1. errors.py

Error class hierarchy for remote execution operations.

**Classes**:

- `RemoteExecutionError` - Base exception
- `PackagingError` - Context packaging errors
- `ProvisioningError` - VM provisioning errors
- `TransferError` - File transfer errors
- `ExecutionError` - Remote execution errors
- `IntegrationError` - Result integration errors
- `CleanupError` - VM cleanup errors

### 2. context_packager.py

Secure context packaging with multi-layer secret detection.

**Key Features**:

- Comprehensive secret scanning (API keys, tokens, passwords)
- Git bundle creation (all branches and history)
- Archive size validation (max 500MB)
- Automatic exclusion of sensitive files

**Secret Patterns Detected**:

- Anthropic/OpenAI API keys
- GitHub Personal Access Tokens
- Azure/AWS credentials
- Generic API keys and passwords

**Usage**:

```python
with ContextPackager(repo_path) as packager:
    secrets = packager.scan_secrets()
    if secrets:
        raise PackagingError("Secrets detected")
    archive = packager.package()
```

### 3. orchestrator.py

VM lifecycle management via azlin CLI.

**Key Features**:

- VM provisioning with retry logic
- Intelligent VM reuse (< 24 hours old, matching size)
- Cleanup with force option
- VM tagging for identification

**Usage**:

```python
orchestrator = Orchestrator()
options = VMOptions(size='Standard_D2s_v3')
vm = orchestrator.provision_or_reuse(options)
# ... use vm ...
orchestrator.cleanup(vm)
```

### 4. executor.py

Remote command execution and file transfer.

**Key Features**:

- Context archive transfer with retry
- Remote setup and execution
- Timeout enforcement
- Log and git state retrieval

**Usage**:

```python
executor = Executor(vm, timeout_minutes=120)
executor.transfer_context(archive_path)
result = executor.execute_remote(
    command='auto',
    prompt='implement feature X',
    max_turns=10
)
```

### 5. integrator.py

Result integration into local repository.

**Key Features**:

- Git branch import into `remote-exec/` namespace
- Log copying to `.claude/runtime/logs/remote/`
- Conflict detection
- Integration summary generation

**Usage**:

```python
integrator = Integrator(repo_path)
summary = integrator.integrate(results_dir)
report = integrator.create_summary_report(summary)
```

### 6. cli.py

Click-based CLI entry point.

**Key Features**:

- Progress reporting (7 steps)
- Error handling with actionable messages
- VM preservation on failure
- Result summary display

**Usage**:

```bash
amplihack remote auto "implement feature X"
amplihack remote --max-turns 20 ultrathink "analyze code"
```

## File Structure

```
.claude/tools/amplihack/remote/
├── __init__.py              # Public API
├── cli.py                   # CLI entry point
├── context_packager.py      # Context packaging
├── orchestrator.py          # VM lifecycle
├── executor.py              # Remote execution (includes bootstrap script)
├── integrator.py            # Result integration
├── errors.py                # Error classes
├── README.md                # This file
└── tests/
    ├── __init__.py
    ├── test_context_packager.py
    ├── test_orchestrator.py
    └── test_integrator.py

.claude/commands/amplihack/
└── remote.md                # Slash command docs
```

## Usage

### Command-Line Interface

```bash
# Basic usage
amplihack remote auto "implement user authentication"

# With size shortcuts (recommended)
amplihack remote auto "implement feature" --vm-size l

# With full Azure VM size names
amplihack remote --max-turns 20 --vm-size Standard_D4s_v3 auto "refactor API"

# Keep VM for debugging
amplihack remote --keep-vm ultrathink "analyze performance"

# Use specific VM
amplihack remote --vm-name amplihack-ryan-123 auto "continue work"
```

### VM Size Options

Use size shortcuts (s/m/l/xl) or full Azure VM names:

| Shortcut | Azure VM Size     | vCPUs | RAM   | Use Case                            |
| -------- | ----------------- | ----- | ----- | ----------------------------------- |
| **s**    | Standard_D2s_v3   | 2     | 8GB   | Simple tasks, quick tests           |
| **m**    | Standard_D4s_v3   | 4     | 16GB  | Standard development work (default) |
| **l**    | Standard_E16as_v5 | 16    | 128GB | Complex tasks, large repos          |
| **xl**   | Standard_E32as_v5 | 32    | 256GB | Heavy workloads, ML tasks           |

**Recommendation**: Use `--vm-size l` for most development tasks to avoid timeout issues during initial amplihack installation on the remote VM.

### Programmatic Usage

```python
from pathlib import Path
from amplihack.remote import (
    execute_remote_workflow,
    VMOptions
)

execute_remote_workflow(
    repo_path=Path.cwd(),
    command='auto',
    prompt='implement feature X',
    max_turns=10,
    vm_options=VMOptions(
        size='Standard_D2s_v3',
        keep_vm=False,
        no_reuse=False
    ),
    timeout=120
)
```

## Security

### Secret Scanning

**Hard Requirement**: Zero secrets transferred. Command fails immediately if secrets detected.

**Detection Patterns**:

- `ANTHROPIC_API_KEY = "sk-ant-..."` <!-- pragma: allowlist secret -->
- `OPENAI_API_KEY = "sk-..."` <!-- pragma: allowlist secret -->
- `password = "..."` <!-- pragma: allowlist secret -->
- Generic API keys and tokens

**Auto-Excluded Files** (18 patterns):

- `.env*` - Environment variables
- `*credentials*`, `*secret*` - Credential/secret files <!-- pragma: allowlist secret -->
- `*.pem`, `*.key`, `*.p12`, `*.pfx` - Private keys and certificates
- `.ssh/`, `.aws/`, `.azure/` - Cloud credentials
- `node_modules/`, `__pycache__/`, `.venv/` - Dependencies and cache

### API Key Transfer

Only `ANTHROPIC_API_KEY` is transferred, using secure SSH environment passing. Never hardcode keys in source files.

## Testing

### Run Unit Tests

```bash
cd .claude/tools/amplihack/remote
python -m pytest tests/
```

### Test Coverage

- `test_context_packager.py` - Secret detection, packaging, exclusions
- `test_orchestrator.py` - VM provisioning, reuse, cleanup
- `test_integrator.py` - Branch import, log copying, conflict detection

### Manual Testing

```bash
# Test secret detection
echo 'API_KEY = "sk-test-123"' > test.py  # pragma: allowlist secret
git add test.py
amplihack remote auto "test"  # Should fail

# Test basic execution
amplihack remote auto "create hello.txt with 'Hello Remote'"

# Test VM reuse
amplihack remote --keep-vm auto "task 1"
amplihack remote auto "task 2"  # Should reuse VM

# Cleanup
azlin list | grep amplihack
azlin kill <vm-name>
```

## Error Handling

### PackagingError

**Cause**: Secrets detected, archive too large, .claude missing
**Action**: Remove secrets, reduce repo size, verify .claude exists

### ProvisioningError

**Cause**: Azlin not installed, VM creation failed, quota exceeded
**Action**: Install azlin, check Azure subscription, verify quota

### TransferError

**Cause**: Network failure, file transfer timeout
**Action**: Retry, check network, verify VM disk space

### ExecutionError

**Cause**: Remote command failed, timeout exceeded
**Action**: Inspect VM logs, increase timeout, fix command

### IntegrationError

**Cause**: Merge conflicts, branch import failed
**Action**: Manual merge, check git state

### CleanupError

**Cause**: VM deletion failed
**Action**: Manual cleanup via `azlin kill <vm-name>`

## Performance

### Timings (Typical)

- **VM Provisioning**: 4-7 minutes (new) or 0 seconds (reuse)
- **Context Transfer**: 30-120 seconds (depends on size)
- **Execution**: Variable (depends on command)
- **Result Retrieval**: 10-30 seconds
- **Total Overhead**: 5-10 minutes (with reuse)

### Optimization Tips

1. **Enable VM reuse**: Saves 5-7 minutes
2. **Keep repo clean**: Faster packaging and transfer
3. **Use appropriate VM size**: Balance cost and performance
4. **Set realistic timeouts**: Prevent premature termination

## Cost Considerations

### VM Costs (Estimated)

- **Standard_D2s_v3**: $0.10-0.15/hour (2 vCPU, 8GB)
- **Standard_D4s_v3**: $0.20-0.30/hour (4 vCPU, 16GB)

### Cost Optimization

- VM reuse reduces provisioning overhead
- Auto-cleanup prevents abandoned VMs
- Timeout enforcement prevents runaway costs
- Monitor with `azlin list` periodically

## Azlin Integration Notes

### Path Handling Requirements

**Critical**: Azlin cp command requires specific path formats:

**Local Paths**: Must be relative (run from correct directory using `cwd`)

```bash
# ✓ Correct
cd /tmp && azlin cp file.tar.gz vm:~/file.tar.gz

# ✗ Wrong - absolute path rejected
azlin cp /tmp/file.tar.gz vm:~/file.tar.gz
```

**Remote Paths**: Must use `~/` notation (not `/tmp/`)

```bash
# ✓ Correct
azlin cp file.tar.gz vm:~/file.tar.gz

# ✗ Wrong - absolute path rejected
azlin cp file.tar.gz vm:/tmp/file.tar.gz
```

### Non-Interactive Mode

Use `--yes` flag for automation:

```bash
azlin new --size s --name my-vm --yes
```

**Known Limitation**: Azlin's bastion prompts may still require confirmation due to upstream bug in `click.confirm()` implementation.

## Requirements

### Local Machine

- Python 3.11+
- Git 2.30+
- azlin (via `pip install azlin`)
- Azure CLI 2.50+ (used by azlin)
- ANTHROPIC_API_KEY in environment

### Azure

- Active subscription with credits
- VM quota (Standard_D series)
- Network access to Azure regions

## Troubleshooting

### VM provisioning takes too long

- Check Azure subscription status
- Verify region availability
- Try different VM size

### Transfer fails

- Check network connection
- Verify archive < 500MB
- Check VM disk space

### Execution fails

- VM preserved automatically
- Connect: `azlin connect <vm-name>`
- Check logs: `cat .claude/runtime/logs/*.log`

### Results not retrieved

- VM preserved on failure
- Manual retrieval: See remote.md troubleshooting section

## Contributing

When modifying this module:

1. Follow zero-BS principle (no TODOs, no placeholders)
2. Add tests for new functionality
3. Update documentation
4. Verify security (no secret leakage)
5. Test with real VMs before committing

## References

- **Azlin**: https://github.com/rysweet/azlin
- **Requirements**: `.claude/runtime/logs/remote-execution-requirements.md`
- **Investigation**: `.claude/runtime/logs/investigation-remote-execution-findings.md`
- **Slash Command**: `.claude/commands/amplihack/remote.md`

## Status

**Phase 1 MVP**: ✅ Complete

All core components implemented and tested:

- ✅ Context packaging with secret scanning
- ✅ VM provisioning and reuse
- ✅ File transfer (bidirectional)
- ✅ Remote execution with timeout
- ✅ Result integration
- ✅ Error handling
- ✅ CLI interface
- ✅ Unit tests
- ✅ Documentation

Ready for end-to-end testing with real Azure VMs.
