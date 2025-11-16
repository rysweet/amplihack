# Serena MCP Integration

Self-contained module for detecting, configuring, and managing the Serena MCP server integration with Claude Desktop.

## Purpose

This module provides a complete solution for integrating the Serena MCP server (https://github.com/oraios/serena) with Claude Desktop. It handles:

1. **Detection**: Checks for prerequisites (uv, Serena accessibility, platform configuration)
2. **Configuration**: Manages Claude Desktop's MCP server configuration
3. **CLI**: Provides user-friendly command-line interface

## Contract

### Public API

```python
from .claude.tools.amplihack.integrations.serena import (
    # Detector
    SerenaDetector,
    SerenaDetectionResult,

    # Configurator
    SerenaConfigurator,
    SerenaConfig,

    # CLI
    SerenaCLI,

    # Errors
    SerenaIntegrationError,
    UvNotFoundError,
    SerenaNotFoundError,
    ConfigurationError,
    PlatformNotSupportedError,
)
```

### Core Behaviors

#### Detection (SerenaDetector)

Detects system prerequisites and configuration paths:

```python
detector = SerenaDetector()
result = detector.detect_all()

# Check if ready to configure
if result.is_ready():
    print("All prerequisites met!")
else:
    print("Missing prerequisites:")
    if not result.uv_available:
        print("  - uv not installed")
    if not result.serena_available:
        print("  - Serena not accessible")
```

#### Configuration (SerenaConfigurator)

Manages MCP server configuration:

```python
configurator = SerenaConfigurator()

# Add Serena to configuration
if configurator.add_to_mcp_servers():
    print("Serena configured successfully")

# Check configuration
if configurator.is_configured():
    config = configurator.get_current_config()
    print(f"Command: {config.command}")
    print(f"Args: {config.args}")

# Remove configuration
if configurator.remove_from_mcp_servers():
    print("Serena removed successfully")

# Export for manual setup
configurator.export_to_claude_desktop(Path("serena_config.json"))
```

#### CLI (SerenaCLI)

Command-line interface integrated with amplihack:

```bash
# Show status
amplihack serena status

# Configure Serena
amplihack serena setup

# Remove configuration
amplihack serena remove

# Export configuration snippet
amplihack serena export output.json

# Show diagnostics
amplihack serena diagnose
```

## Dependencies

### Required

- Python 3.10+
- Standard library only (no external dependencies for core functionality)

### Prerequisites for Serena

- `uv` (Python package installer and runner)
- Git (for accessing Serena from GitHub)
- Network access to github.com

## Architecture

### Module Structure

```
serena/
├── __init__.py           # Public API exports
├── errors.py             # Error definitions with structured messages
├── detector.py           # Prerequisite detection
├── configurator.py       # MCP configuration management
├── cli.py                # CLI interface
├── README.md             # This file
└── tests/
    ├── __init__.py
    ├── test_detector.py
    ├── test_configurator.py
    └── test_cli.py
```

### Design Principles

1. **Brick Design**: Self-contained module with clear boundaries
2. **Single Responsibility**: Each class has one job
3. **Fail-Fast**: Clear errors with actionable fixes
4. **Cross-Platform**: Supports Linux, macOS, Windows, WSL
5. **Zero-BS**: No placeholders, TODOs, or unimplemented functions

### Key Components

#### 1. SerenaDetector

**Responsibility**: Detect system prerequisites and configuration paths

**Methods**:
- `detect_all()`: Complete system detection
- `detect_uv()`: Check if uv is installed
- `detect_serena()`: Check if Serena is accessible via uvx
- `detect_platform()`: Identify OS platform
- `get_mcp_config_path()`: Get Claude Desktop config path

**Platform Support**:
- Linux: `~/.config/Claude/claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%/Claude/claude_desktop_config.json`
- WSL: Uses Linux paths

#### 2. SerenaConfigurator

**Responsibility**: Manage Claude Desktop MCP server configuration

**Methods**:
- `is_configured()`: Check if Serena is configured
- `add_to_mcp_servers()`: Add Serena to configuration
- `remove_from_mcp_servers()`: Remove Serena from configuration
- `get_current_config()`: Get current Serena configuration
- `export_to_claude_desktop()`: Export configuration snippet

**Configuration Format**:
```json
{
  "mcpServers": {
    "serena": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/oraios/serena",
        "serena"
      ],
      "env": {}
    }
  }
}
```

**Safety Features**:
- Preserves existing MCP servers
- Validates JSON before writing
- Creates directories as needed
- Never overwrites without confirmation

#### 3. SerenaCLI

**Responsibility**: Provide command-line interface

**Commands**:
- `status`: Show detection and configuration status
- `setup`: Configure Serena MCP server
- `remove`: Remove Serena configuration
- `export`: Export configuration snippet
- `diagnose`: Show detailed diagnostic information

**Integration**: Automatically registered with amplihack CLI via `create_parser()`

### Error Handling

All errors inherit from `SerenaIntegrationError` and include:
- Human-readable message
- Suggested fix with actionable steps

```python
try:
    configurator.add_to_mcp_servers()
except UvNotFoundError as e:
    print(e)  # Includes installation instructions
except ConfigurationError as e:
    print(e)  # Includes troubleshooting steps
```

## Usage Examples

### Basic Detection and Setup

```python
from .claude.tools.amplihack.integrations.serena import (
    SerenaDetector,
    SerenaConfigurator,
)

# Detect prerequisites
detector = SerenaDetector()
result = detector.detect_all()

if result.is_ready():
    # Configure Serena
    configurator = SerenaConfigurator(detector)
    if configurator.add_to_mcp_servers():
        print("Serena configured! Restart Claude Desktop.")
else:
    print(result.get_status_summary())
```

### CLI Usage

```bash
# Check if ready to configure
amplihack serena status

# Output:
# Serena MCP Integration Status
# ========================================
#
# Prerequisites:
#   uv available: Yes
#   uv path: /usr/bin/uv
#   Serena accessible: Yes
#
# Configuration:
#   Platform: linux
#   MCP config path: /home/user/.config/Claude/claude_desktop_config.json
#   Config exists: Yes
#   Serena configured: No
#
# Status: Prerequisites met, ready to configure
# Run 'amplihack serena setup' to configure

# Configure Serena
amplihack serena setup

# Output:
# Configuring Serena MCP server...
#
# Success! Serena has been configured.
#
# Next steps:
#   1. Restart Claude Desktop
#   2. Serena MCP server will be available
#
# Configuration written to: /home/user/.config/Claude/claude_desktop_config.json

# Export for manual setup
amplihack serena export my-config.json

# Output:
# Exporting Serena configuration to my-config.json...
#
# Success! Configuration exported to: my-config.json
#
# Manual setup instructions:
#   1. Open your Claude Desktop config file:
#      /home/user/.config/Claude/claude_desktop_config.json
#   2. Merge the exported configuration into mcpServers section
#   3. Restart Claude Desktop
```

### Programmatic Usage

```python
from pathlib import Path
from .claude.tools.amplihack.integrations.serena import (
    SerenaCLI,
    SerenaDetector,
    SerenaConfigurator,
)

# Create CLI instance
cli = SerenaCLI()

# Setup argparse
import argparse
parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers()
cli.setup_parser(subparsers)

# Execute command
args = parser.parse_args(["serena", "status"])
exit_code = cli.execute(args)
```

## Testing

Run tests with pytest:

```bash
# Run all tests
pytest .claude/tools/amplihack/integrations/serena/tests/

# Run specific test file
pytest .claude/tools/amplihack/integrations/serena/tests/test_detector.py

# Run with coverage
pytest --cov=.claude/tools/amplihack/integrations/serena .claude/tools/amplihack/integrations/serena/tests/
```

Test coverage includes:
- Detection logic for all platforms
- Configuration operations (add, remove, export)
- CLI commands and error handling
- Edge cases and error conditions

## Troubleshooting

### Common Issues

**Issue**: "uv is not installed or not found in PATH"

**Solution**: Install uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Issue**: "Serena is not accessible via uvx"

**Solution**: Ensure Git is installed and test manually:
```bash
uvx --from git+https://github.com/oraios/serena serena --help
```

**Issue**: "Failed to write configuration"

**Solution**:
1. Close Claude Desktop
2. Check file permissions
3. Verify config directory exists

**Issue**: "Platform 'FreeBSD' is not supported"

**Solution**: This module supports Linux, macOS, Windows, and WSL. Other platforms are not currently supported.

## Philosophy Alignment

This module follows amplihack's core principles:

1. **Ruthless Simplicity**: Uses standard library, no external dependencies
2. **Brick Design**: Self-contained with clear public API
3. **Zero-BS**: Every function works or doesn't exist
4. **Fail-Fast**: Clear errors with actionable fixes
5. **Regeneratable**: Can be rebuilt from this specification

## Future Enhancements

Potential improvements (not currently implemented):

1. Auto-restart Claude Desktop after configuration
2. Validation that Serena is actually working after setup
3. Support for custom Serena arguments/environment
4. Interactive configuration wizard
5. Backup/restore of MCP configuration

## License

Part of the amplihack project. See repository LICENSE for details.
