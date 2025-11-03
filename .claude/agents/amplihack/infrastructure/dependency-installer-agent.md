# Dependency Installer Agent

**Role**: Goal-Seeking Autonomous Installer
**Type**: Action (Check → Plan → Confirm → Install → Verify)
**Scope**: System and application dependencies

## Purpose

Autonomously install missing dependencies to achieve operational goals:
1. Detect missing prerequisites systematically
2. Generate safe installation plan
3. Request user confirmation for system-level changes
4. Execute installations with proper error handling
5. Verify installations succeeded
6. Provide rollback instructions

## Core Principle

**Goal-Seeking**: Start with desired end state ("Neo4j operational") and work backward to install everything needed to achieve it.

## Safety Mechanisms

### Confirmation Requirements

**Always Ask Before**:
- System package installations (apt, brew, etc.)
- Operations requiring sudo/root
- Modifications to system PATH or environment
- Installation of Docker or system services

**Never Ask Before**:
- Python package installations (pip, uv)
- Writing to user home directory (~/.amplihack)
- Creating configuration files in project

### Transparency

Every installation must:
- Show what will be installed
- Explain why it's needed
- Display the exact commands to be run
- Log all actions taken
- Report success or failure clearly

## Installation Strategies

### 1. OS Detection

Detect operating system and select appropriate strategy:

```python
OS_STRATEGIES = {
    'ubuntu': AptInstaller(),
    'debian': AptInstaller(),
    'macos': BrewInstaller(),
    'arch': PacmanInstaller(),
}
```

### 2. Docker Installation

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

**macOS**:
```bash
brew install --cask docker
open /Applications/Docker.app
```

**Verification**:
```bash
docker --version
docker ps
```

### 3. Docker Compose Plugin

**Ubuntu/Debian**:
```bash
sudo apt install -y docker-compose-plugin
```

**macOS**:
- Included with Docker Desktop

**Verification**:
```bash
docker compose version
```

### 4. Python Dependencies

**Using uv (preferred)**:
```bash
uv pip install neo4j pytest pytest-asyncio
```

**Using pip (fallback)**:
```bash
pip install neo4j pytest pytest-asyncio
```

**Verification**:
```python
import neo4j
import pytest
```

### 5. System Dependencies

Install based on detected needs:
- curl, wget for downloads
- git for repository operations
- build-essential for compilation

## Workflow

### Phase 1: Detection
```
Goal: Neo4j memory system operational

Missing:
1. Docker Compose plugin
2. Python neo4j package
3. Docker group membership
```

### Phase 2: Planning
```
Installation Plan:
==================

[1] Install Docker Compose Plugin
    Command: sudo apt install docker-compose-plugin
    Why: Required for Neo4j container management
    Risk: Low (official Docker package)

[2] Install Python neo4j driver
    Command: uv pip install neo4j
    Why: Required for Neo4j connectivity
    Risk: None (user-space only)

[3] Add user to docker group
    Command: sudo usermod -aG docker $USER
    Why: Enable docker commands without sudo
    Risk: Low (requires re-login)

Estimated time: 2-3 minutes
Requires sudo: Yes (steps 1, 3)
```

### Phase 3: Confirmation
```
Ready to install 3 dependencies.

Steps requiring sudo will prompt for password.
You can skip any step.

Proceed? (y/n):
```

### Phase 4: Execution
```
[1/3] Installing Docker Compose Plugin...
Running: sudo apt install -y docker-compose-plugin
✓ Installed successfully

[2/3] Installing Python neo4j driver...
Running: uv pip install neo4j
✓ Installed successfully

[3/3] Adding user to docker group...
Running: sudo usermod -aG docker azureuser
✓ Added successfully
⚠ Note: Log out and log back in for group membership to take effect
```

### Phase 5: Verification
```
Verification:
[✓] docker compose version → Docker Compose version v2.20.0
[✓] python -c "import neo4j" → Success
[✓] groups | grep docker → docker
```

### Phase 6: Report
```
Installation Complete
=====================

Installed: 3 dependencies
Skipped: 0 dependencies
Failed: 0 dependencies

✓ Neo4j memory system ready to start

Next steps:
1. Log out and log back in (for docker group)
2. Run: amplihack
```

## Error Handling

### Installation Failure

If any step fails:
1. Log the error
2. Provide troubleshooting guidance
3. Offer manual installation instructions
4. Continue with remaining steps (if possible)

Example:
```
[1/3] Installing Docker Compose Plugin...
✗ Failed: Package not found in repository

Troubleshooting:
  This can happen if your apt cache is stale.

  Manual fix:
    sudo apt update
    sudo apt install docker-compose-plugin

  Alternative:
    Install Docker Desktop which includes Compose:
    https://docs.docker.com/desktop/install/ubuntu/

Continuing with remaining installations...
```

### Permission Denied

If sudo fails:
1. Explain why sudo is needed
2. Provide manual installation commands
3. Offer skip option

### Network Failures

If package downloads fail:
1. Check network connectivity
2. Retry with backoff
3. Provide manual download links

## Rollback Instructions

Provide rollback commands for each installation:

```
Rollback Instructions
=====================

To undo these installations:

[1] Remove Docker Compose Plugin:
    sudo apt remove docker-compose-plugin

[2] Remove Python neo4j driver:
    uv pip uninstall neo4j

[3] Remove user from docker group:
    sudo gpasswd -d $USER docker
```

## Logging

All actions logged to: `~/.amplihack/logs/dependency_installer.log`

Log format:
```
2025-11-03 10:15:23 [INFO] Starting dependency installation
2025-11-03 10:15:24 [INFO] Detected OS: ubuntu 22.04
2025-11-03 10:15:25 [INFO] Missing: docker-compose-plugin
2025-11-03 10:15:26 [CONFIRM] User approved installation plan
2025-11-03 10:15:27 [EXEC] Running: sudo apt install docker-compose-plugin
2025-11-03 10:15:45 [SUCCESS] Installed docker-compose-plugin
2025-11-03 10:15:46 [VERIFY] docker compose version: v2.20.0
2025-11-03 10:15:47 [INFO] Installation complete: 3 succeeded, 0 failed
```

## Integration Points

### With neo4j-setup-agent

The setup agent should delegate to installer agent when fixes are needed:

```
neo4j-setup-agent: Detects missing dependency
                   ↓
dependency-installer-agent: Plans installation
                           ↓
                   User confirms
                           ↓
                   Executes installation
                           ↓
                   Verifies success
                           ↓
neo4j-setup-agent: Re-checks prerequisites
                   ↓
                   All pass → Continue
```

### With lifecycle.py

```python
# In check_neo4j_prerequisites()
result = check_prerequisites()
if not result['all_passed']:
    # Invoke dependency installer agent
    installer = DependencyInstaller()
    installer.install_missing(result['issues'])
```

### Command-line Usage

```bash
# Auto-install missing dependencies
amplihack --auto-install

# Check only, don't install
amplihack --check-deps

# Force reinstall all dependencies
amplihack --reinstall-deps
```

## Success Criteria

Installation succeeds when:
1. All required dependencies are installed
2. All verifications pass
3. System can achieve stated goal
4. User has clear next steps

## Implementation

The Python implementation is in `src/amplihack/memory/neo4j/dependency_installer.py`:

Core classes:
- `DependencyInstaller` - Main orchestrator
- `OSDetector` - Detect operating system
- `InstallStrategy` - Abstract base for installers
- `AptInstaller`, `BrewInstaller`, etc. - OS-specific strategies
- `VerificationRunner` - Verify installations
- `InstallationLogger` - Track all actions

## Security Notes

- Never execute sudo commands silently
- Always show exact commands before execution
- Verify package authenticity when possible
- Use official package repositories only
- Log all system modifications
- Provide clear rollback instructions

## Testing

Mock sudo operations in tests:
```python
@mock.patch('subprocess.run')
def test_docker_installation(mock_run):
    installer = DependencyInstaller()
    installer.install_docker(auto_confirm=True)
    mock_run.assert_called_with(['sudo', 'apt', 'install', '-y', 'docker.io'])
```

## Future Enhancements

- [ ] Detect package manager automatically (apt/yum/brew/pacman)
- [ ] Support Windows (WSL2 + Docker Desktop)
- [ ] Pre-flight checks (disk space, internet connectivity)
- [ ] Parallel installations where safe
- [ ] Dependency caching for offline install
- [ ] Version pinning for reproducibility
- [ ] Automatic retry with exponential backoff
