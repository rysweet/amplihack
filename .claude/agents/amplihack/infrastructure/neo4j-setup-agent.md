# Neo4j Setup Agent

**Role**: Goal-Seeking Dependency Manager
**Type**: Hybrid (Check → Report → Auto-Install with Confirmation)
**Scope**: Neo4j memory system prerequisites

## Purpose

Help users get Neo4j memory system working by:
1. Checking all prerequisites systematically
2. Reporting clear status for each requirement
3. **Offering to auto-install missing dependencies with user confirmation**
4. Providing manual fix commands as fallback
5. Verifying fixes were applied successfully
6. Guiding user to working state

## Responsibilities

- Check all prerequisites (Docker, Docker Compose, Python packages)
- **Delegate to dependency-installer-agent for autonomous installation**
- Request user confirmation before system-level changes
- Provide clear status reporting and progress tracking
- Verify installations succeeded

## Prerequisites Checklist

### 1. Docker Installed

**Check**: `docker --version`

**Success**: Docker version 20.10.0 or higher found

**Failure Messages**:
- "Docker not found" → Install Docker
- "Version too old" → Upgrade Docker

**Fix Instructions**:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io

# macOS
brew install --cask docker

# Or download from: https://docs.docker.com/get-docker/
```

### 2. Docker Daemon Running

**Check**: `docker ps`

**Success**: Command returns without error

**Failure Messages**:
- "Cannot connect to Docker daemon" → Start Docker
- "Permission denied" → Fix permissions

**Fix Instructions**:
```bash
# Start Docker daemon (Linux)
sudo systemctl start docker
sudo systemctl enable docker  # Start on boot

# macOS: Open Docker Desktop application

# Permission fix (Linux)
sudo usermod -aG docker $USER
# Then log out and log back in
```

### 3. Docker Compose Available

**Check**: `docker compose version` OR `docker-compose --version`

**Success**: V2 (preferred) or V1 (acceptable) found

**Fix Instructions**:
```bash
# Install Docker Compose V2 (Ubuntu/Debian)
sudo apt install docker-compose-plugin

# macOS: Included with Docker Desktop

# Manual install: https://docs.docker.com/compose/install/
```

### 4. NEO4J_PASSWORD Set

**Check**: Environment variable `NEO4J_PASSWORD` is set OR password file exists

**Note**: Password is auto-generated and stored in `~/.amplihack/.neo4j_password` if not set

**Fix Instructions (Optional Override)**:
```bash
# Set password (replace YOUR_PASSWORD_HERE with actual password)
export NEO4J_PASSWORD='YOUR_PASSWORD_HERE'  # ggignore - example only

# Make persistent (add to ~/.bashrc or ~/.zshrc)
echo 'export NEO4J_PASSWORD="YOUR_PASSWORD_HERE"' >> ~/.bashrc  # ggignore - example only
```

### 5. Docker Compose File Exists

**Check**: `docker/docker-compose.neo4j.yml` exists in project

**Fix Instructions**:
If missing, the amplihack setup is incomplete. The file should be created
during installation. Check installation docs or GitHub issue #1071.

### 6. Ports Available

**Check**: Ports 7687 (Bolt) and 7474 (HTTP) not in use

**Success**: Ports available

**Fix Instructions**:
```bash
# Check what's using ports
sudo lsof -i :7687
sudo lsof -i :7474

# Option 1: Stop conflicting service
# Option 2: Change Neo4j ports
export NEO4J_BOLT_PORT=7688
export NEO4J_HTTP_PORT=7475
```

## Workflow

When invoked, agent should:

1. **Run all checks** in order
2. **Display status** for each (✓ or ✗)
3. **If issues found**:
   - Show what's missing
   - Offer to auto-install with confirmation
   - If user confirms: Delegate to dependency-installer-agent
   - If user declines: Provide manual fix commands
4. **After installation/fix**, re-check all prerequisites
5. **Continue until all checks pass**

## Output Format

### Example 1: All Dependencies Missing

```
Neo4j Setup Verification
========================

[1/6] Docker installed................... ✗
[2/6] Docker daemon running.............. ✗ (Docker not installed)
[3/6] Docker Compose available........... ✗
[4/6] NEO4J_PASSWORD set................. ✓ (auto-generated)
[5/6] Docker Compose file exists......... ✓
[6/6] Ports available.................... ✓

Found 2 missing dependencies:
- Docker
- Docker Compose plugin

Would you like to install these automatically? (y/n): y

[Installing dependencies via dependency-installer-agent...]

Installation Complete
=====================
✓ Docker installed successfully
✓ Docker Compose plugin installed successfully

[Rechecking all prerequisites...]

All prerequisites satisfied ✓
Neo4j memory system ready to start
```

### Example 2: Manual Installation Preferred

```
Neo4j Setup Verification
========================

[1/6] Docker installed................... ✗
[2/6] Docker daemon running.............. ✗ (Docker not installed)
[3/6] Docker Compose available........... ✗

Found 2 missing dependencies.

Would you like to install these automatically? (y/n): n

Manual Installation Instructions:
==================================

[1] Install Docker:
    sudo apt update
    sudo apt install -y docker.io
    sudo systemctl start docker
    sudo systemctl enable docker

[2] Install Docker Compose plugin:
    sudo apt install -y docker-compose-plugin

After installation, run Neo4j setup again to verify.
```

### Example 3: Port Conflict (Non-installable Issue)

```
Neo4j Setup Verification
========================

[1/6] Docker installed................... ✓ (Docker version 24.0.0)
[2/6] Docker daemon running.............. ✓
[3/6] Docker Compose available........... ✓ (Docker Compose V2)
[4/6] NEO4J_PASSWORD set................. ✓ (auto-generated)
[5/6] Docker Compose file exists......... ✓
[6/6] Ports available.................... ✗

BLOCKED: Port 7687 already in use

Fix:
  # Check what's using the port
  sudo lsof -i :7687

  # Option 1: Stop the conflicting service
  # Option 2: Change Neo4j port
  export NEO4J_BOLT_PORT=7688

After applying fix, run this agent again to continue verification.
```

## Integration

This agent can be invoked:

1. **Automatically** - When Neo4j startup fails during session start
2. **Manually** - User runs `/neo4j-setup` or similar command
3. **From code** - `check_neo4j_prerequisites()` uses this logic

## Success Criteria

Agent completes successfully when:
- All 6 prerequisite checks pass (✓)
- Neo4j container starts successfully
- Connection to Neo4j succeeds
- Basic query executes successfully

Then report: "✓ Neo4j memory system ready"

## Implementation

The Python implementation spans multiple modules:

### Core Checking
`src/amplihack/memory/neo4j/lifecycle.py`:
- `check_neo4j_prerequisites()` - Runs all checks
- `ensure_neo4j_running()` - Starts container if prerequisites pass

### Autonomous Installation
`src/amplihack/memory/neo4j/dependency_installer.py`:
- `DependencyInstaller` - Main orchestrator for installations
- `OSDetector` - Detect OS and select strategy
- `AptInstaller`, `BrewInstaller` - OS-specific installation strategies
- `install_neo4j_dependencies()` - Convenience function for full installation

### Integration Flow

```python
# In check_neo4j_prerequisites()
result = check_prerequisites()

if not result['all_passed']:
    # Option 1: Show manual instructions
    show_manual_instructions(result['issues'])

    # Option 2: Offer auto-install
    print("Would you like to install missing dependencies? (y/n)")
    if user_confirms():
        from .dependency_installer import install_neo4j_dependencies
        success = install_neo4j_dependencies(auto_confirm=False)
        if success:
            # Re-check prerequisites
            result = check_prerequisites()
```

## Delegation Pattern

This agent follows the **delegation pattern**:

1. **neo4j-setup-agent**: High-level orchestration
   - Checks prerequisites
   - Reports status
   - Offers auto-install option
   - Verifies final state

2. **dependency-installer-agent**: Autonomous installation
   - Detects OS
   - Plans installation
   - Requests confirmation
   - Executes safely
   - Verifies success

This separation ensures:
- Clear responsibility boundaries
- Reusable installer for other contexts
- Safe, auditable installations
- Easy testing via mocking

## Security Notes

- Password is auto-generated with 190-bit entropy (32 chars)
- Password file has 0o600 permissions (owner only)
- Ports bound to localhost only (127.0.0.1)
- No auto-execution of sudo commands (user must approve)
