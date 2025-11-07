# Autonomous Dependency Installer - Implementation Summary

## Overview

Created a goal-seeking autonomous dependency installer that can detect, plan,
and install missing dependencies with user confirmation and comprehensive safety
mechanisms.

## Created Files

### 1. Agent Definition

**Location**:
`.claude/agents/amplihack/infrastructure/dependency-installer-agent.md`

**Purpose**: Defines the autonomous installation agent that can install
dependencies with user confirmation.

**Key Features**:

- Goal-seeking behavior (start with end state, work backwards)
- Safety mechanisms (confirmation prompts, transparency, logging)
- OS-specific installation strategies
- Comprehensive error handling and rollback instructions
- Integration with neo4j-setup-agent

### 2. Implementation

**Location**: `src/amplihack/memory/neo4j/dependency_installer.py`

**Core Classes**:

- `DependencyInstaller` - Main orchestrator for autonomous installation
- `OSDetector` - Detect operating system and version
- `InstallStrategy` - Abstract base for OS-specific strategies
- `AptInstaller` - Ubuntu/Debian installation strategy (apt)
- `BrewInstaller` - macOS installation strategy (Homebrew)
- `Dependency` - Data class representing a dependency to install
- `InstallResult` - Data class for installation results

**Key Methods**:

- `check_missing_dependencies()` - Detect what's missing
- `show_installation_plan()` - Display plan to user
- `confirm_installation()` - Request user approval
- `install_dependency()` - Install single dependency
- `install_missing()` - Main entry point (check → plan → confirm → install)

**Safety Features**:

- Never executes sudo commands silently
- Shows exact commands before execution
- Requires explicit confirmation for system-level changes
- Comprehensive logging to `~/.amplihack/logs/dependency_installer.log`
- Provides rollback instructions for each installation

### 3. Tests

**Location**: `tests/unit/memory/neo4j/test_dependency_installer.py`

**Test Coverage** (25 tests, all passing):

- OS detection (Ubuntu, macOS, unsupported OS)
- Installation strategies (apt, Homebrew)
- Dependency checking (Docker, Docker Compose, Python packages)
- Installation execution (success, failure, user group changes)
- User confirmation (yes, no, auto-confirm)
- Integration flows (full installation, no dependencies missing)

**Test Approach**:

- Mock all subprocess.run calls (no actual sudo operations)
- Use patch.dict for neo4j import mocking
- Test error conditions and edge cases

### 4. Updated Agent Definition

**Location**: `.claude/agents/amplihack/infrastructure/neo4j-setup-agent.md`

**Changes**:

- Updated type from "Advisory" to "Hybrid (Check → Report → Auto-Install with
  Confirmation)"
- Added delegation pattern to dependency-installer-agent
- Updated workflow to include auto-install option
- Added example outputs showing auto-install flow
- Documented integration between setup and installer agents

## Example Workflow

### User Experience

```bash
# User starts amplihack
amplihack

# Neo4j memory system initializes
# Detects Docker Compose missing
# Dependency installer agent activates

Neo4j Setup Verification
========================

[1/6] Docker installed................... ✓
[2/6] Docker daemon running.............. ✓
[3/6] Docker Compose available........... ✗
[4/6] NEO4J_PASSWORD set................. ✓
[5/6] Docker Compose file exists......... ✓
[6/6] Ports available.................... ✓

Found 1 missing dependency:
- Docker Compose plugin

Would you like to install this automatically? (y/n): y

Installation Plan
==================

[1] docker-compose-plugin
    Why: Required for Neo4j container orchestration
    Risk: low
    Commands:
      🔒 sudo apt install -y docker-compose-plugin
    ⚠️  Requires sudo (will prompt for password)

Estimated time: 0 minutes
Requires sudo: Yes

Proceed with installation? (y/n): y

[Installing] docker-compose-plugin...
  Running (requires password): sudo apt install -y docker-compose-plugin
  ✓ Installed successfully

Installation Summary
=====================

✓ Installed: 1
✗ Failed: 0
○ Skipped: 0

Total time: 15.3 seconds

[Rechecking all prerequisites...]

All prerequisites satisfied ✓
Neo4j memory system ready to start
```

## Architecture

### Delegation Pattern

```
neo4j-setup-agent (orchestrator)
    ↓
    checks prerequisites
    ↓
    detects missing dependencies
    ↓
    offers auto-install
    ↓
    delegates to → dependency-installer-agent
                   ↓
                   detects OS
                   ↓
                   plans installation
                   ↓
                   requests confirmation
                   ↓
                   executes safely
                   ↓
                   verifies success
    ↓
    re-checks prerequisites
    ↓
    reports final state
```

### Key Design Principles

1. **Goal-Seeking**: Start with desired end state ("Neo4j operational") and work
   backwards
2. **Safety First**: Never execute sudo commands without explicit user
   confirmation
3. **Transparency**: Show exactly what will be done and why
4. **Resilience**: Handle failures gracefully, provide rollback instructions
5. **Reusability**: Installer can be used for other dependencies beyond Neo4j
6. **Testability**: All system operations are mockable for testing

## Supported Platforms

### Currently Supported

- **Ubuntu/Debian**: Using apt package manager
- **macOS**: Using Homebrew package manager

### Installation Capabilities

- Docker (docker.io)
- Docker Compose plugin (docker-compose-plugin)
- Python packages (neo4j, pytest, etc.)
- System packages (curl, git, build-essential, etc.)
- User group membership (adding user to docker group)

### Future Support (Not Yet Implemented)

- Windows (WSL2 + Docker Desktop)
- Arch Linux (pacman)
- Red Hat/CentOS (yum/dnf)

## Usage

### As Library

```python
from src.amplihack.memory.neo4j.dependency_installer import (
    install_neo4j_dependencies,
    check_dependencies,
    DependencyInstaller
)

# Check what's missing (non-interactive)
missing = check_dependencies()
print(f"Missing: {missing}")

# Install with confirmation
success = install_neo4j_dependencies(auto_confirm=False)

# Install without confirmation (for CI/automated environments)
success = install_neo4j_dependencies(auto_confirm=True)

# Advanced usage
installer = DependencyInstaller()
missing_deps = installer.check_missing_dependencies()
installer.show_installation_plan(missing_deps)
result = installer.install_missing(confirm=True)
```

### Integration with Neo4j Setup

The installer is designed to be invoked by `neo4j-setup-agent` when
prerequisites fail:

```python
# In lifecycle.py or setup code
from .dependency_installer import install_neo4j_dependencies

result = check_neo4j_prerequisites()
if not result['all_passed']:
    print("Missing dependencies detected")
    if user_wants_auto_install():
        success = install_neo4j_dependencies(auto_confirm=False)
        if success:
            # Re-check prerequisites
            result = check_neo4j_prerequisites()
```

## Security Considerations

### What We Do

- ✅ Always show commands before execution
- ✅ Request confirmation for sudo operations
- ✅ Log all actions to audit trail
- ✅ Provide rollback instructions
- ✅ Use official package repositories only
- ✅ Verify installations after completion

### What We Don't Do

- ❌ Execute sudo commands silently
- ❌ Install from untrusted sources
- ❌ Modify system files without permission
- ❌ Skip security checks for convenience

## Testing

Run the test suite:

```bash
uv run pytest tests/unit/memory/neo4j/test_dependency_installer.py -v
```

**Results**: 25/25 tests passing

**Coverage**:

- OS detection and strategy selection
- Dependency checking logic
- Installation execution (mocked)
- Error handling and failure scenarios
- User confirmation flows
- Integration workflows

## Logging

All installation actions are logged to:

```
~/.amplihack/logs/dependency_installer.log
```

Log format:

```
2025-11-03 10:15:23 [INFO] Starting dependency installation
2025-11-03 10:15:24 [INFO] Detected OS: ubuntu 22.04
2025-11-03 10:15:25 [INFO] Missing: docker-compose-plugin
2025-11-03 10:15:26 [CONFIRM] User approved installation plan
2025-11-03 10:15:27 [EXEC] Running: sudo apt install docker-compose-plugin
2025-11-03 10:15:45 [SUCCESS] Installed docker-compose-plugin
2025-11-03 10:15:46 [VERIFY] docker compose version: v2.20.0
2025-11-03 10:15:47 [INFO] Installation complete: 1 succeeded, 0 failed
```

## Next Steps

### Integration

1. Connect dependency installer to Neo4j startup code
2. Add command-line flags (`--auto-install`, `--check-deps`)
3. Integrate with amplihack CLI

### Enhancements

1. Add Windows support (WSL2 + Docker Desktop)
2. Add more Linux distributions (Arch, Red Hat, etc.)
3. Add version checking (ensure minimum versions)
4. Add dependency caching for offline installation
5. Add parallel installation where safe
6. Add pre-flight checks (disk space, network connectivity)

### Documentation

1. Add user guide to main docs
2. Add troubleshooting section
3. Add screenshots of installation flow

## Files Modified/Created

```
Created:
├── .claude/agents/amplihack/infrastructure/dependency-installer-agent.md
├── src/amplihack/memory/neo4j/dependency_installer.py
├── tests/unit/memory/neo4j/__init__.py
├── tests/unit/memory/neo4j/test_dependency_installer.py
└── DEPENDENCY_INSTALLER_SUMMARY.md (this file)

Modified:
└── .claude/agents/amplihack/infrastructure/neo4j-setup-agent.md
```

## Success Criteria Met

✅ Created dependency-installer-agent.md with safety mechanisms ✅ Implemented
dependency_installer.py with OS detection and strategies ✅ Added confirmation
prompts and logging for all operations ✅ Created comprehensive test suite (25
tests, all passing) ✅ Updated neo4j-setup-agent to use dependency installer ✅
Documented integration pattern and usage

## Summary

The autonomous dependency installer provides a safe, transparent, and
user-controlled way to install missing dependencies. It follows the project's
philosophy of ruthless simplicity while maintaining security through explicit
user confirmation for system-level changes. The agent can detect what's missing,
plan the installation, request permission, execute safely, and verify success -
making the Neo4j setup process much smoother for users who lack Docker or Docker
Compose.
