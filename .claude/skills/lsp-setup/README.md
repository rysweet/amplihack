# LSP Auto-Configuration Module

**Developer documentation for the Claude Code LSP Setup skill.**

## Overview

The LSP Setup module provides automatic Language Server Protocol (LSP) configuration for Claude Code. It follows the brick philosophy: self-contained, regeneratable modules with clear public APIs.

### LSP Architecture - Three Layers

Claude Code's LSP system requires three layers to be configured:

1. **Layer 1: System LSP Binaries** - LSP server executables installed via npm, brew, rustup, etc.
2. **Layer 2: Claude Code LSP Plugins** - Plugins installed via `npx cclsp install <server>` that bridge Claude Code to Layer 1 binaries
3. **Layer 3: Project Configuration** - `.env` file with `ENABLE_LSP_TOOL=1` and project-specific settings

**Critical Understanding**: `cclsp` and `claude-code-lsps` work **together**, not as alternatives:
- `cclsp` = The installation command-line tool
- `claude-code-lsps` = The plugin marketplace that `cclsp` uses
- They are complementary components of the same system

### What This Module Does

This module automates the `npx cclsp@latest setup` workflow, adding:
- Intelligent language detection across 16 languages
- Automatic detection of Layer 1 and Layer 2 installation status
- User-guided installation (NEVER auto-installs system binaries)
- Project-specific configuration generation (Layer 3)
- Connection verification and troubleshooting guidance

## Architecture

### Module Structure

```
.claude/skills/lsp-setup/
├── __init__.py              # Public API exports
├── SKILL.md                 # User-facing documentation
├── README.md                # This file (developer documentation)
├── USAGE_EXAMPLES.md        # Practical usage examples
├── language_detector.py     # Language detection logic
├── lsp_configurator.py      # LSP server configuration
├── plugin_manager.py        # LSP plugin lifecycle management
├── status_tracker.py        # Configuration status tracking
├── config/
│   ├── language_definitions.json  # Supported languages and LSP servers
│   └── lsp_server_templates.json  # LSP server configuration templates
├── tests/
│   ├── test_language_detector.py
│   ├── test_lsp_configurator.py
│   ├── test_plugin_manager.py
│   ├── test_status_tracker.py
│   └── fixtures/
│       ├── sample_python_project/
│       ├── sample_typescript_project/
│       └── sample_polyglot_project/
└── examples/
    ├── basic_usage.py
    ├── advanced_usage.py
    └── troubleshooting.py
```

### Design Philosophy

**Brick Principles Applied:**

1. **Single Responsibility**: Each module handles one aspect of LSP configuration
2. **Self-Contained**: No external dependencies beyond standard library and Claude Code SDK
3. **Clear Public API**: `__all__` defines stable interface
4. **Regeneratable**: Can be rebuilt from this specification
5. **Isolated Testing**: All tests contained within module

**Zero-BS Implementation:**

- No stub functions or placeholders
- Every function works or doesn't exist
- Real LSP server detection, not mock data
- Actual file I/O, not simulated operations

## Module Specifications

### 1. language_detector.py

**Purpose**: Detect programming languages in project directory

**Public API**:

```python
from typing import List, Dict
from dataclasses import dataclass

@dataclass
class LanguageDetection:
    """Result of language detection scan"""
    language: str           # e.g., "python", "typescript"
    file_count: int        # Number of files detected
    primary: bool          # True if this is primary project language
    markers: List[str]     # Framework markers found (e.g., "package.json")

class LanguageDetector:
    """Detects programming languages in project directory"""

    def detect_languages(self, project_root: Path) -> List[LanguageDetection]:
        """
        Scan project directory and identify all languages present.

        Args:
            project_root: Path to project root directory

        Returns:
            List of LanguageDetection objects, sorted by file count (descending)

        Example:
            >>> detector = LanguageDetector()
            >>> languages = detector.detect_languages(Path("/path/to/project"))
            >>> for lang in languages:
            ...     print(f"{lang.language}: {lang.file_count} files")
            python: 23 files
            yaml: 2 files
        """

    def get_primary_language(self, project_root: Path) -> Optional[LanguageDetection]:
        """
        Identify the primary language of the project.

        Primary language determined by:
        1. Language with most files
        2. Presence of framework markers (package.json, Cargo.toml, etc.)
        3. Language-specific configuration files

        Returns:
            LanguageDetection for primary language, or None if no languages detected
        """

    def detect_language_frameworks(self, project_root: Path, language: str) -> List[str]:
        """
        Detect frameworks for a specific language.

        Args:
            project_root: Path to project root
            language: Language identifier (e.g., "python", "typescript")

        Returns:
            List of framework names (e.g., ["django", "flask"])

        Example:
            >>> detector.detect_language_frameworks(Path("/app"), "python")
            ["django"]
        """

__all__ = ["LanguageDetector", "LanguageDetection"]
```

**Dependencies**: Standard library only (`pathlib`, `collections`)

**Testing Strategy**:

- Unit tests with mock file systems (60%)
- Integration tests with fixture projects (30%)
- End-to-end tests with real projects (10%)

### 2. lsp_configurator.py

**Purpose**: Generate LSP server configuration for detected languages

**Public API**:

```python
from typing import Dict, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class LSPServerConfig:
    """Configuration for a single LSP server (all three layers)"""
    language: str          # Language identifier
    server_name: str       # LSP server name (e.g., "pyright", "vtsls")

    # Layer 1: System binary
    layer1_path: Optional[Path]  # Path to system LSP binary (None if not installed)
    layer1_install_cmd: str      # Command to install system binary
    layer1_status: str           # "installed", "not_found", "error"

    # Layer 2: Claude Code plugin
    layer2_installed: bool       # True if Claude Code plugin installed
    layer2_install_cmd: str      # Command to install plugin (npx cclsp install ...)
    layer2_status: str           # "installed", "not_found", "error"

    # Layer 3: Project configuration
    config: Dict[str, any]       # Project-specific settings for .env

    overall_status: str          # "ready", "partial", "not_configured"

class LSPConfigurator:
    """Generates LSP server configurations"""

    def configure_language(
        self,
        language: str,
        project_root: Path,
        detection: LanguageDetection
    ) -> LSPServerConfig:
        """
        Generate LSP configuration for a specific language.

        Args:
            language: Language identifier
            project_root: Path to project root
            detection: LanguageDetection result from language_detector

        Returns:
            LSPServerConfig with server path and configuration

        Example:
            >>> configurator = LSPConfigurator()
            >>> config = configurator.configure_language(
            ...     "python",
            ...     Path("/project"),
            ...     detection
            ... )
            >>> print(config.server_name)
            pyright
            >>> print(config.status)
            installed
        """

    def check_server_installed(self, server_name: str) -> Optional[Path]:
        """
        Check if LSP server is installed on system.

        Args:
            server_name: Name of LSP server (e.g., "pyright")

        Returns:
            Path to server executable if found, None otherwise

        Example:
            >>> configurator.check_server_installed("pyright")
            PosixPath('/usr/local/bin/pyright')
        """

    def generate_env_config(
        self,
        configs: List[LSPServerConfig],
        project_root: Path
    ) -> Dict[str, str]:
        """
        Generate .env configuration entries for LSP servers (Layer 3).

        Args:
            configs: List of LSP server configurations
            project_root: Path to project root

        Returns:
            Dictionary of environment variable key-value pairs

        Example:
            >>> env_config = configurator.generate_env_config(configs, root)
            >>> print(env_config)
            {
                'ENABLE_LSP_TOOL': '1',  # REQUIRED
                'LSP_PYTHON_INTERPRETER': '/path/.venv/bin/python',
                'LSP_PYRIGHT_PATH': '/usr/local/bin/pyright',
                'LSP_VTSLS_PATH': '/usr/local/bin/vtsls'
            }

        Note:
            ENABLE_LSP_TOOL=1 is automatically included and is required for LSP
            features to activate in Claude Code.
        """

    def detect_language_specific_config(
        self,
        language: str,
        project_root: Path
    ) -> Dict[str, str]:
        """
        Detect language-specific configuration (virtual envs, project roots).

        Args:
            language: Language identifier
            project_root: Path to project root

        Returns:
            Dictionary of language-specific configuration

        Example:
            >>> configurator.detect_language_specific_config("python", root)
            {
                'python_interpreter': '/path/.venv/bin/python',
                'venv_path': '/path/.venv'
            }
        """

__all__ = ["LSPConfigurator", "LSPServerConfig"]
```

**Dependencies**: Standard library only (`pathlib`, `shutil`, `subprocess`)

**Testing Strategy**:

- Unit tests with mocked system commands (60%)
- Integration tests with real LSP server checks (30%)
- End-to-end tests with full configuration generation (10%)

### 3. plugin_manager.py

**Purpose**: Manage LSP server lifecycle and Claude Code plugin integration

**Public API**:

```python
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class PluginStatus:
    """Status of a Claude Code LSP plugin"""
    language: str
    server_name: str
    enabled: bool
    connected: bool
    error: Optional[str] = None

class PluginManager:
    """Manages Claude Code LSP plugin lifecycle"""

    def install_plugin(self, config: LSPServerConfig) -> bool:
        """
        Install LSP server plugin in Claude Code.

        Args:
            config: LSP server configuration

        Returns:
            True if installation successful, False otherwise

        Example:
            >>> manager = PluginManager()
            >>> success = manager.install_plugin(config)
            >>> print(success)
            True
        """

    def verify_connection(self, server_name: str) -> PluginStatus:
        """
        Verify LSP server is connected and responding.

        Args:
            server_name: Name of LSP server

        Returns:
            PluginStatus with connection details

        Example:
            >>> status = manager.verify_connection("pyright")
            >>> print(f"{status.server_name}: {'Connected' if status.connected else 'Disconnected'}")
            pyright: Connected
        """

    def get_all_plugin_status(self) -> List[PluginStatus]:
        """
        Get status of all installed LSP plugins.

        Returns:
            List of PluginStatus for all plugins

        Example:
            >>> statuses = manager.get_all_plugin_status()
            >>> for status in statuses:
            ...     print(f"{status.language}: {status.server_name} - {status.connected}")
            python: pyright - True
            typescript: typescript-language-server - True
        """

    def restart_plugin(self, server_name: str) -> bool:
        """
        Restart an LSP server plugin.

        Args:
            server_name: Name of LSP server to restart

        Returns:
            True if restart successful, False otherwise
        """

__all__ = ["PluginManager", "PluginStatus"]
```

**Dependencies**: Claude Code SDK (LSP management APIs)

**Testing Strategy**:

- Unit tests with mocked Claude Code SDK (60%)
- Integration tests with test LSP servers (30%)
- End-to-end tests with real Claude Code instance (10%)

### 4. status_tracker.py

**Purpose**: Track configuration status and provide user feedback

**Public API**:

```python
from typing import List, Dict
from enum import Enum
from dataclasses import dataclass

class ConfigStatus(Enum):
    """Status of LSP configuration"""
    NOT_STARTED = "not_started"
    DETECTING = "detecting"
    CONFIGURING = "configuring"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    ERROR = "error"

@dataclass
class StatusReport:
    """Comprehensive status report"""
    overall_status: ConfigStatus
    languages_detected: List[LanguageDetection]
    servers_configured: List[LSPServerConfig]
    plugins_installed: List[PluginStatus]
    errors: List[str]
    warnings: List[str]

class StatusTracker:
    """Tracks and reports LSP configuration status"""

    def update_status(self, status: ConfigStatus, message: str) -> None:
        """
        Update current configuration status.

        Args:
            status: New configuration status
            message: Status message for user

        Example:
            >>> tracker = StatusTracker()
            >>> tracker.update_status(ConfigStatus.DETECTING, "Scanning for languages...")
        """

    def add_success(self, component: str, message: str) -> None:
        """Record successful operation"""

    def add_warning(self, component: str, message: str) -> None:
        """Record warning (non-fatal issue)"""

    def add_error(self, component: str, message: str) -> None:
        """Record error (fatal issue)"""

    def get_report(self) -> StatusReport:
        """
        Generate comprehensive status report.

        Returns:
            StatusReport with all configuration details

        Example:
            >>> report = tracker.get_report()
            >>> print(f"Status: {report.overall_status}")
            >>> print(f"Languages: {len(report.languages_detected)}")
            Status: complete
            Languages: 3
        """

    def format_report(self, report: StatusReport) -> str:
        """
        Format status report for display to user.

        Args:
            report: StatusReport to format

        Returns:
            Formatted string for terminal output

        Example:
            >>> output = tracker.format_report(report)
            >>> print(output)
            [LSP Setup] Configuration complete! 3/3 servers ready.
        """

__all__ = ["StatusTracker", "StatusReport", "ConfigStatus"]
```

**Dependencies**: Standard library only (`enum`, `dataclasses`)

**Testing Strategy**:

- Unit tests for status tracking logic (60%)
- Integration tests for report generation (30%)
- End-to-end tests for formatted output (10%)

## Configuration Files

### language_definitions.json

Defines supported languages and their LSP servers:

```json
{
  "languages": {
    "python": {
      "extensions": [".py", ".pyi"],
      "lsp_server": "pyright",
      "layer1_install": "npm install -g pyright",
      "layer2_install": "npx cclsp install pyright",
      "framework_markers": {
        "django": ["manage.py", "settings.py"],
        "flask": ["app.py", "requirements.txt"],
        "fastapi": ["main.py", "requirements.txt"]
      },
      "config_detection": {
        "venv": [".venv", "venv", ".virtualenv"],
        "requirements": ["requirements.txt", "pyproject.toml", "setup.py"]
      }
    },
    "typescript": {
      "extensions": [".ts", ".tsx"],
      "lsp_server": "vtsls",
      "layer1_install": "npm install -g @vtsls/language-server",
      "layer2_install": "npx cclsp install vtsls",
      "framework_markers": {
        "react": ["package.json:react"],
        "vue": ["package.json:vue"],
        "angular": ["angular.json"]
      },
      "config_detection": {
        "tsconfig": ["tsconfig.json"],
        "node_modules": ["node_modules"]
      }
    },
    "ruby": {
      "extensions": [".rb"],
      "lsp_server": "ruby-lsp",
      "layer1_install": "gem install ruby-lsp",
      "layer2_install": "npx cclsp install ruby-lsp"
    },
    "php": {
      "extensions": [".php"],
      "lsp_server": "phpactor",
      "layer1_install": "composer global require phpactor/phpactor",
      "layer2_install": "npx cclsp install phpactor"
    }
  }
}
```

**Note**: Each language definition now includes both `layer1_install` (system binary) and `layer2_install` (Claude Code plugin) commands.

### lsp_server_templates.json

Configuration templates for LSP servers:

```json
{
  "pyright": {
    "initialization_options": {
      "python": {
        "analysis": {
          "typeCheckingMode": "basic",
          "autoSearchPaths": true,
          "useLibraryCodeForTypes": true
        }
      }
    },
    "settings": {
      "python.analysis.diagnosticMode": "workspace"
    }
  },
  "vtsls": {
    "initialization_options": {
      "preferences": {
        "includeInlayParameterNameHints": "all",
        "includeInlayFunctionParameterTypeHints": true
      }
    }
  },
  "ruby-lsp": {
    "initialization_options": {
      "enabledFeatures": ["diagnostics", "formatting", "codeActions"]
    }
  },
  "phpactor": {
    "initialization_options": {
      "language_server_phpstan.enabled": true,
      "language_server_psalm.enabled": false
    }
  }
}
```

## Public API (Module Level)

The module exports a clean public API through `__init__.py`:

```python
"""LSP Auto-Configuration Module

Automatically detects languages and configures LSP servers for Claude Code.

Philosophy:
- Ruthless simplicity: No complex abstractions
- Self-contained: Standard library only (except Claude Code SDK)
- User-guided: No automatic system binary installation
- Regeneratable: Clear specifications enable AI rebuilding

Public API (the "studs"):
    LanguageDetector: Detect languages in project
    LSPConfigurator: Generate LSP configuration
    PluginManager: Manage Claude Code LSP plugins
    StatusTracker: Track and report configuration status

    configure_project: High-level function for full project setup

Usage:
    >>> from lsp_setup import configure_project
    >>> result = configure_project(Path("/path/to/project"))
    >>> print(result.format_report())
"""

from .language_detector import LanguageDetector, LanguageDetection
from .lsp_configurator import LSPConfigurator, LSPServerConfig
from .plugin_manager import PluginManager, PluginStatus
from .status_tracker import StatusTracker, StatusReport, ConfigStatus

__all__ = [
    "LanguageDetector",
    "LanguageDetection",
    "LSPConfigurator",
    "LSPServerConfig",
    "PluginManager",
    "PluginStatus",
    "StatusTracker",
    "StatusReport",
    "ConfigStatus",
    "configure_project",
]

def configure_project(
    project_root: Path,
    languages: Optional[List[str]] = None,
    force: bool = False,
    status_only: bool = False
) -> StatusReport:
    """
    High-level function to configure LSP for entire project.

    Args:
        project_root: Path to project root directory
        languages: Optional list of specific languages to configure
        force: Force reconfiguration even if already configured
        status_only: Only check status, don't modify configuration

    Returns:
        StatusReport with configuration results

    Example:
        >>> from pathlib import Path
        >>> from lsp_setup import configure_project
        >>> result = configure_project(Path.cwd())
        >>> print(result.format_report())
        [LSP Setup] Configuration complete! 3/3 servers ready.
    """
```

## Testing Strategy

### Test Coverage Requirements

- **Unit Tests (60%)**: Fast, heavily mocked
- **Integration Tests (30%)**: Multiple components, fixture projects
- **End-to-End Tests (10%)**: Complete workflows, real LSP servers

### Test Execution

```bash
# Run all tests
pytest tests/

# Run specific test module
pytest tests/test_language_detector.py

# Run with coverage
pytest --cov=lsp_setup --cov-report=html tests/

# Run only fast tests (unit)
pytest -m unit tests/

# Run integration tests
pytest -m integration tests/
```

### Test Fixtures

Located in `tests/fixtures/`:

- `sample_python_project/`: Django project with virtual environment
- `sample_typescript_project/`: React project with TypeScript
- `sample_polyglot_project/`: Mixed Python/TypeScript/Rust project
- `sample_empty_project/`: Empty directory for edge case testing

### Testing Philosophy

**Follow TDD Pyramid**:

- Most tests are unit tests (fast, focused)
- Strategic integration tests for component interaction
- Minimal E2E tests for critical user workflows

**Zero-BS Testing**:

- No tests for non-existent features
- Every test validates real behavior
- Mock external dependencies (LSP servers, file system) strategically
- Use real file I/O for integration tests

## Contributing

### Adding New Language Support

1. Update `config/language_definitions.json` with language details:

```json
{
  "new_language": {
    "extensions": [".ext"],
    "lsp_server": "language-server-name",
    "install_command": "install command here",
    "framework_markers": {},
    "config_detection": {}
  }
}
```

2. Add LSP server template to `config/lsp_server_templates.json`

3. Create test fixture in `tests/fixtures/sample_new_language_project/`

4. Add tests in `tests/test_language_detector.py`

5. Update `SKILL.md` supported languages table

### Code Style

- Follow PEP 8 for Python code
- Use type hints for all public APIs
- Document all public functions with docstrings
- Keep functions under 50 lines (ruthless simplicity)
- Prefer explicit over implicit

### Pull Request Checklist

- [ ] All tests pass (`pytest tests/`)
- [ ] Test coverage ≥ 80% (`pytest --cov`)
- [ ] Updated documentation (SKILL.md, README.md, USAGE_EXAMPLES.md)
- [ ] Added type hints to new functions
- [ ] Followed brick philosophy (self-contained, clear API)
- [ ] No stub functions or placeholders
- [ ] Updated `__all__` exports if public API changed

## Maintenance

### Version Updates

When LSP servers change their APIs or installation methods:

1. Update `config/language_definitions.json` with new install commands
2. Update `config/lsp_server_templates.json` with new configuration options
3. Add migration guide in `SKILL.md` troubleshooting section
4. Update tests to reflect API changes

### Deprecation Process

When removing support for a language or LSP server:

1. Add deprecation warning in skill output (1 release)
2. Document removal timeline in `SKILL.md`
3. Remove from `language_definitions.json` (next major release)
4. Archive tests in `tests/archived/`

## Performance Characteristics

- **Language Detection**: O(n) where n = number of files in project
- **Configuration Generation**: O(m) where m = number of languages detected
- **Plugin Installation**: O(p) where p = number of plugins (sequential)
- **Verification**: O(p) where p = number of plugins (parallel)

**Typical Execution Times**:

- Small project (< 100 files): 2-3 seconds
- Medium project (100-1000 files): 3-5 seconds
- Large project (> 1000 files): 5-10 seconds

## Security Considerations

**Safe Subprocess Execution**:

- Never execute arbitrary shell commands from user input
- Validate LSP server paths before execution
- Use absolute paths for all subprocess calls
- Timeout all subprocess operations (30 second default)

**File System Safety**:

- Never overwrite `.env` without user confirmation (unless `--force`)
- Validate all file paths are within project root
- Handle symbolic links safely (resolve before checking)

**Network Safety**:

- No automatic download of LSP servers
- All installation commands are user-executed
- No telemetry or external API calls

## Dependencies

**Required**:

- Python 3.9+
- Claude Code SDK (LSP management APIs)

**Optional**:

- None (all LSP servers are external to the module)

## License

Same as amplihack project (see root LICENSE file).

## Support

For issues or questions:

1. Check troubleshooting section in `SKILL.md`
2. Review usage examples in `USAGE_EXAMPLES.md`
3. Open issue in amplihack repository with:
   - Project structure (language breakdown)
   - LSP server versions
   - Output of `/lsp-setup --status-only`
   - Relevant error messages
