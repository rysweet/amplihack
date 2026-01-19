# Plugin Development Guide

Guide for contributing to and extending the amplihack Claude Code plugin.

## Contents

- [Development Setup](#development-setup)
- [Plugin Architecture](#plugin-architecture)
- [Adding Features](#adding-features)
- [Testing](#testing)
- [Contributing](#contributing)

## Development Setup

### Prerequisites

- **Python 3.9+** with pip
- **Git** for version control
- **Claude Code** installed
- **Node.js 18+** (for TypeScript components)
- **Rust 1.70+** (optional, for performance-critical components)

### Clone Repository

```bash
# Clone amplihack
git clone https://github.com/rysweet/amplihack.git
cd amplihack

# Create development branch
git checkout -b feature/my-plugin-feature
```

### Install in Development Mode

```bash
# Install in editable mode
pip install -e .

# Install development dependencies
pip install -e .[dev]

# Install plugin from source
amplihack plugin install --dev

# Verify development mode
amplihack plugin status --verbose
# Should show: Mode: Development
```

### Development Environment

```bash
# Set development environment variables
export AMPLIHACK_DEV_MODE=1
export AMPLIHACK_LOG_LEVEL=debug
export CLAUDE_PLUGIN_ROOT=~/.amplihack/.claude

# Verify
amplihack plugin env
```

## Plugin Architecture

### Directory Structure

```
amplihack/
├── src/amplihack/
│   └── plugin/                    # Plugin implementation
│       ├── __init__.py           # Plugin entry point
│       ├── installer.py          # Installation logic
│       ├── detector.py           # LSP detection
│       ├── configurator.py       # Configuration management
│       └── manager.py            # Plugin lifecycle
├── .claude/                       # Plugin content
│   ├── agents/                   # AI agents
│   ├── commands/                 # Slash commands
│   ├── skills/                   # Auto-loading skills
│   ├── templates/                # Reusable templates
│   ├── tools/                    # Hooks and utilities
│   └── workflow/                 # Process definitions
├── tests/
│   └── plugin/                   # Plugin tests
│       ├── test_installer.py
│       ├── test_detector.py
│       └── test_integration.py
└── docs/plugin/                  # This documentation
```

### Core Components

#### 1. Plugin Installer (`src/amplihack/plugin/installer.py`)

Handles plugin installation and updates:

```python
from pathlib import Path
from typing import Optional

class PluginInstaller:
    """Install and manage amplihack plugin."""

    def __init__(self, plugin_root: Optional[Path] = None):
        """Initialize installer.

        Args:
            plugin_root: Plugin installation directory
                        (default: ~/.amplihack/.claude)
        """
        self.plugin_root = plugin_root or self._default_root()

    def install(self, force: bool = False) -> InstallResult:
        """Install plugin to plugin_root.

        Args:
            force: Reinstall even if already installed

        Returns:
            InstallResult with status and details
        """
        # Implementation
        pass

    def update(self, version: Optional[str] = None) -> UpdateResult:
        """Update plugin to specified version."""
        pass

    def uninstall(self, purge: bool = False) -> UninstallResult:
        """Remove plugin."""
        pass
```

#### 2. LSP Detector (`src/amplihack/plugin/detector.py`)

Auto-detects project languages:

```python
from typing import List, Dict
from pathlib import Path

class LSPDetector:
    """Detect project languages and configure LSP."""

    LANGUAGE_PATTERNS = {
        "typescript": [".ts", ".tsx"],
        "javascript": [".js", ".jsx"],
        "python": [".py", ".pyi"],
        "rust": [".rs"],
        "go": [".go"],
    }

    ROOT_MARKERS = {
        "typescript": ["tsconfig.json", "package.json"],
        "python": ["pyproject.toml", "setup.py"],
        "rust": ["Cargo.toml"],
        "go": ["go.mod"],
    }

    def detect(self, project_path: Path) -> List[DetectedLanguage]:
        """Detect languages in project.

        Args:
            project_path: Path to project directory

        Returns:
            List of detected languages with metadata
        """
        # Implementation
        pass

    def configure_lsp(
        self,
        languages: List[str],
        output_dir: Path
    ) -> Dict[str, Path]:
        """Generate LSP configurations.

        Args:
            languages: List of language names
            output_dir: Where to write configs

        Returns:
            Mapping of language -> config file path
        """
        pass
```

#### 3. Configuration Manager (`src/amplihack/plugin/configurator.py`)

Manages plugin and user configuration:

```python
from pathlib import Path
from typing import Any, Optional

class ConfigurationManager:
    """Manage plugin configuration."""

    def __init__(self, config_root: Path):
        """Initialize with config directory."""
        self.config_root = config_root
        self.user_prefs_path = config_root / "preferences" / "USER_PREFERENCES.md"
        self.lsp_config_dir = config_root / "lsp"

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        pass

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        pass

    def load_user_preferences(self) -> Dict[str, Any]:
        """Load user preferences from Markdown."""
        pass

    def save_user_preferences(self, prefs: Dict[str, Any]) -> None:
        """Save user preferences to Markdown."""
        pass
```

### Path Resolution

All plugin paths use `${CLAUDE_PLUGIN_ROOT}`:

```python
from pathlib import Path
import os

def resolve_plugin_path(relative_path: str) -> Path:
    """Resolve path relative to plugin root.

    Args:
        relative_path: Path relative to ${CLAUDE_PLUGIN_ROOT}

    Returns:
        Absolute path

    Example:
        >>> resolve_plugin_path("agents/core/architect.md")
        Path("/home/user/.amplihack/.claude/agents/core/architect.md")
    """
    root = Path(os.environ.get(
        "CLAUDE_PLUGIN_ROOT",
        Path.home() / ".amplihack" / ".claude"
    ))
    return root / relative_path


# Usage in plugin code
AGENT_DIR = resolve_plugin_path("agents")
SKILLS_DIR = resolve_plugin_path("skills")
TEMPLATES_DIR = resolve_plugin_path("templates")
```

## Adding Features

### Adding a New Agent

1. **Create agent definition**:

```bash
# Create new agent file
mkdir -p .claude/agents/specialized
vim .claude/agents/specialized/my-agent.md
```

```markdown
---
agent_name: my-agent
agent_type: specialized
capabilities:
  - custom_analysis
  - specialized_task
dependencies:
  - analyzer
  - builder
---

# My Agent

Specialized agent for [specific task].

## When to Use

Use this agent when:
- [Specific scenario 1]
- [Specific scenario 2]

## Capabilities

### 1. Custom Analysis

[Description]

### 2. Specialized Task

[Description]

## Usage

```bash
# Invoke via Task tool
Task(subagent_type="my-agent", prompt="Analyze X")
```

## Examples

[Working examples]
```

2. **Test the agent**:

```bash
# Test agent in development mode
amplihack plugin test-agent my-agent

# Test in real project
cd test-project
claude

# Use the agent
/ultrathink "Use my-agent to analyze X"
```

3. **Add tests**:

```python
# tests/plugin/test_agents.py
def test_my_agent_invocation():
    """Test my-agent can be invoked."""
    from amplihack.agents import load_agent

    agent = load_agent("my-agent")
    assert agent is not None
    assert "custom_analysis" in agent.capabilities
```

### Adding a New Command

1. **Create command file**:

```bash
vim .claude/commands/my-command.py
```

```python
"""My Custom Command

Implements /my-command for specific functionality.
"""

from pathlib import Path
from typing import Optional

def execute(args: Optional[str] = None) -> None:
    """Execute my custom command.

    Args:
        args: Command arguments (optional)
    """
    print(f"Executing my-command with args: {args}")

    # Implementation
    result = perform_custom_task(args)

    print(f"Result: {result}")


def perform_custom_task(args: Optional[str]) -> str:
    """Perform the custom task."""
    # Implementation
    return "Success"


if __name__ == "__main__":
    import sys
    execute(sys.argv[1] if len(sys.argv) > 1 else None)
```

2. **Register command**:

```bash
# Add to .claude/commands/README.md
echo "/my-command - Custom functionality" >> .claude/commands/README.md
```

3. **Test command**:

```bash
# Test command directly
python .claude/commands/my-command.py "test args"

# Test in Claude Code
claude
/my-command test args
```

### Adding LSP Support for New Language

1. **Create LSP configuration template**:

```bash
cat > .claude/tools/lsp/templates/mylang.json << 'EOF'
{
  "language": "mylang",
  "server": "mylang-ls",
  "command": "mylang-language-server",
  "args": ["--stdio"],
  "initialization_options": {
    "mylang": {
      "option1": true,
      "option2": "value"
    }
  },
  "file_extensions": [".mylang", ".ml"],
  "root_markers": ["mylang.config", "package.json"]
}
EOF
```

2. **Add detection logic**:

```python
# src/amplihack/plugin/detector.py

class LSPDetector:
    LANGUAGE_PATTERNS = {
        # ... existing patterns ...
        "mylang": [".mylang", ".ml"],
    }

    ROOT_MARKERS = {
        # ... existing markers ...
        "mylang": ["mylang.config", "package.json"],
    }
```

3. **Test detection**:

```bash
# Create test project
mkdir test-mylang-project
cd test-mylang-project
touch file.mylang mylang.config

# Test detection
amplihack plugin lsp-detect --dry-run
# Should show: Found: mylang (1 file)
```

### Adding a New Skill

1. **Create skill directory**:

```bash
mkdir -p .claude/skills/my-skill
cd .claude/skills/my-skill
```

2. **Create skill files**:

```bash
# Skill metadata
cat > skill.md << 'EOF'
# My Skill

## Purpose

[What this skill does]

## When I Activate

I activate when you mention:
- "keyword1"
- "keyword2"

## Usage

[How to use this skill]
EOF

# Skill implementation (if needed)
cat > skill.py << 'EOF'
"""My Skill Implementation"""

def process(input_text: str) -> str:
    """Process input with skill logic."""
    # Implementation
    return f"Processed: {input_text}"
EOF
```

3. **Test skill**:

```bash
# Test skill loading
amplihack plugin test-skill my-skill

# Test skill invocation
claude
# Mention trigger keywords
```

## Testing

### Running Tests

```bash
# Run all plugin tests
pytest tests/plugin/

# Run specific test
pytest tests/plugin/test_installer.py::test_install_success

# Run with coverage
pytest tests/plugin/ --cov=src/amplihack/plugin --cov-report=html
```

### Writing Tests

#### Unit Tests

```python
# tests/plugin/test_detector.py
import pytest
from pathlib import Path
from amplihack.plugin.detector import LSPDetector

def test_detect_typescript_project(tmp_path):
    """Test TypeScript project detection."""
    # Setup
    project = tmp_path / "test-project"
    project.mkdir()
    (project / "tsconfig.json").touch()
    (project / "index.ts").write_text("const x: string = 'test';")

    # Execute
    detector = LSPDetector()
    languages = detector.detect(project)

    # Assert
    assert len(languages) == 1
    assert languages[0].name == "typescript"
    assert languages[0].file_count == 1


def test_detect_multiple_languages(tmp_path):
    """Test multi-language project detection."""
    project = tmp_path / "mixed-project"
    project.mkdir()

    # Create mixed language files
    (project / "main.py").write_text("print('hello')")
    (project / "index.ts").write_text("console.log('hello');")
    (project / "main.rs").write_text("fn main() { println!(\"hello\"); }")

    detector = LSPDetector()
    languages = detector.detect(project)

    assert len(languages) == 3
    lang_names = {lang.name for lang in languages}
    assert lang_names == {"python", "typescript", "rust"}
```

#### Integration Tests

```python
# tests/plugin/test_integration.py
import pytest
from pathlib import Path
from amplihack.plugin.installer import PluginInstaller

def test_full_installation_flow(tmp_path):
    """Test complete installation flow."""
    plugin_root = tmp_path / ".amplihack" / ".claude"

    # Install
    installer = PluginInstaller(plugin_root=plugin_root)
    result = installer.install()

    assert result.success
    assert plugin_root.exists()
    assert (plugin_root / "agents").exists()
    assert (plugin_root / "commands").exists()

    # Verify components
    agent_count = len(list((plugin_root / "agents").rglob("*.md")))
    assert agent_count >= 30  # Should have 30+ agents

    # Update
    update_result = installer.update()
    assert update_result.success

    # Uninstall
    uninstall_result = installer.uninstall()
    assert uninstall_result.success
```

### Manual Testing

```bash
# Install plugin in test mode
amplihack plugin install --test --location /tmp/test-plugin

# Test in isolated environment
export CLAUDE_PLUGIN_ROOT=/tmp/test-plugin/.claude
cd test-project
claude

# Test specific features
/ultrathink "Test feature X"
amplihack plugin lsp-detect
amplihack plugin status

# Clean up
amplihack plugin uninstall --purge
```

## Contributing

### Development Workflow

1. **Create feature branch**:

```bash
git checkout -b feature/my-feature
```

2. **Make changes**:

```bash
# Edit files
vim src/amplihack/plugin/detector.py

# Test changes
pytest tests/plugin/test_detector.py
```

3. **Run quality checks**:

```bash
# Format code
black src/amplihack/plugin/
black tests/plugin/

# Lint
flake8 src/amplihack/plugin/
mypy src/amplihack/plugin/

# Run all tests
pytest tests/plugin/ --cov
```

4. **Commit changes**:

```bash
git add .
git commit -m "feat: Add LSP support for MyLang"
```

5. **Create pull request**:

```bash
git push origin feature/my-feature
# Open PR on GitHub
```

### Code Style

Follow amplihack philosophy:

- **Ruthless simplicity**: Simple > complex
- **Zero-BS**: Everything works or doesn't exist
- **Clear contracts**: Explicit interfaces
- **Self-documenting**: Code explains itself

```python
# Good: Simple, clear
def detect_language(file_path: Path) -> Optional[str]:
    """Detect language from file extension."""
    extension = file_path.suffix.lower()
    return EXTENSION_MAP.get(extension)


# Bad: Over-engineered
class LanguageDetectionStrategyFactory:
    def create_strategy(self, detection_mode: str) -> IDetectionStrategy:
        if detection_mode == "extension":
            return ExtensionBasedStrategy()
        # ... more complexity
```

### Documentation Standards

Follow the Eight Rules:

1. **Location**: All docs in `docs/plugin/`
2. **Linking**: Link from `docs/plugin/README.md`
3. **Simplicity**: Plain language, minimal words
4. **Real Examples**: Runnable code, not placeholders
5. **Diataxis**: One doc type per file
6. **Scanability**: Descriptive headings
7. **Local Links**: Relative paths
8. **Currency**: Delete outdated docs

### Commit Messages

Follow conventional commits:

```bash
feat: Add LSP support for Elixir
fix: Resolve path resolution on Windows
docs: Update plugin installation guide
test: Add integration tests for detector
refactor: Simplify configuration manager
```

### Pull Request Template

```markdown
## Description

[Brief description of changes]

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Breaking change

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Checklist

- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

## Building and Releasing

### Build Plugin Package

```bash
# Build source distribution
python -m build --sdist

# Build wheel
python -m build --wheel

# Build both
python -m build
```

### Version Bumping

```bash
# Bump version
bumpversion patch  # 0.9.0 -> 0.9.1
bumpversion minor  # 0.9.0 -> 0.10.0
bumpversion major  # 0.9.0 -> 1.0.0
```

### Release Process

1. **Update CHANGELOG.md**
2. **Bump version**: `bumpversion minor`
3. **Run tests**: `pytest tests/`
4. **Build**: `python -m build`
5. **Tag release**: `git tag v0.10.0`
6. **Push**: `git push --tags`
7. **Publish to PyPI**: `twine upload dist/*`

## Debugging

### Enable Debug Logging

```bash
# Set debug mode
export AMPLIHACK_LOG_LEVEL=debug
export AMPLIHACK_DEV_MODE=1

# Run command
amplihack plugin install --verbose

# View logs
amplihack plugin logs --level debug --tail 100
```

### Debug Plugin Installation

```python
# Debug installer
from amplihack.plugin.installer import PluginInstaller

installer = PluginInstaller(plugin_root="/tmp/debug-plugin/.claude")
installer.debug = True
result = installer.install()

print(f"Install result: {result}")
print(f"Logs: {result.logs}")
```

### Debug LSP Detection

```bash
# Run detection with verbose output
amplihack plugin lsp-detect --verbose --dry-run

# Check detection logic
python -c "
from amplihack.plugin.detector import LSPDetector
from pathlib import Path

detector = LSPDetector()
detector.debug = True
languages = detector.detect(Path.cwd())
for lang in languages:
    print(f'{lang.name}: {lang.file_count} files')
"
```

## Resources

- **amplihack Repo**: https://github.com/rysweet/amplihack
- **Issue Tracker**: https://github.com/rysweet/amplihack/issues
- **Discussions**: https://github.com/rysweet/amplihack/discussions
- **Documentation**: [docs/plugin/](./README.md)

## Getting Help

### Community

- **GitHub Discussions**: Ask questions
- **GitHub Issues**: Report bugs
- **Pull Requests**: Contribute code

### Development Support

```bash
# Get development help
amplihack plugin dev-help

# Check development environment
amplihack plugin dev-status

# Run development diagnostics
amplihack plugin dev-diagnose
```

---

**Happy hacking! Contributions welcome!** 🚀
