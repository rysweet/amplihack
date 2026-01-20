"""
Base packager for agent bundles with common file operations.

This module provides the core file I/O functionality shared between
UVXPackager and FilesystemPackager, eliminating 71% code duplication.
"""

import json
import logging
from pathlib import Path
from typing import Any

from .models import AgentBundle

logger = logging.getLogger(__name__)


class BundlePackager:
    """
    Base class for bundle packaging operations.

    Provides common file writing operations for all packagers:
    - Directory structure creation
    - Agent file writing
    - Test file writing
    - Documentation writing
    - Configuration writing
    - Manifest generation
    - README generation
    - Python packaging files (__init__.py, setup.py, pyproject.toml)
    """

    def create_directory_structure(self, package_path: Path) -> None:
        """
        Create standard bundle directory structure.

        Args:
            package_path: Root path for the package
        """
        logger.debug("Creating directory structure")

        directories = [
            package_path,
            package_path / "agents",
            package_path / "tests",
            package_path / "docs",
            package_path / "config",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def write_agents(self, bundle: AgentBundle, package_path: Path) -> None:
        """
        Write agent markdown files to agents/ directory.

        Args:
            bundle: Agent bundle containing agent definitions
            package_path: Root path for the package
        """
        logger.debug(f"Writing {len(bundle.agents)} agents")

        agents_dir = package_path / "agents"
        for agent in bundle.agents:
            agent_file = agents_dir / f"{agent.name}.md"
            agent_file.write_text(agent.content)

    def write_tests(self, bundle: AgentBundle, package_path: Path) -> None:
        """
        Write test files to tests/ directory.

        Args:
            bundle: Agent bundle containing test definitions
            package_path: Root path for the package
        """
        logger.debug("Writing tests")

        tests_dir = package_path / "tests"

        # Create __init__.py for tests package (FilesystemPackager pattern)
        (tests_dir / "__init__.py").write_text('"""Tests for agent bundle."""\n')

        # Write agent tests
        for agent in bundle.agents:
            if agent.tests:
                test_file = tests_dir / f"test_{agent.name}.py"
                test_file.write_text("\n".join(agent.tests))

    def write_documentation(self, bundle: AgentBundle, package_path: Path) -> None:
        """
        Write documentation files to docs/ directory.

        Args:
            bundle: Agent bundle containing documentation
            package_path: Root path for the package
        """
        logger.debug("Writing documentation")

        docs_dir = package_path / "docs"

        # Write agent-specific documentation
        for agent in bundle.agents:
            if agent.documentation:
                doc_file = docs_dir / f"{agent.name}_docs.md"
                doc_file.write_text(agent.documentation)

    def write_configuration(self, bundle: AgentBundle, package_path: Path) -> None:
        """
        Write configuration files to config/ directory.

        Args:
            bundle: Agent bundle containing configuration metadata
            package_path: Root path for the package
        """
        logger.debug("Writing configuration")

        config_dir = package_path / "config"
        config_file = config_dir / "bundle_config.json"

        config = {
            "bundle_id": str(bundle.id),
            "bundle_name": bundle.name,
            "bundle_version": bundle.version,
            "enabled_agents": [agent.name for agent in bundle.agents],
            "default_model": "inherit",
            "preferences": bundle.metadata.get("preferences", {}),
            "metadata": bundle.metadata,
        }

        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)

    def write_manifest(self, bundle: AgentBundle, package_path: Path) -> None:
        """
        Write manifest.json with bundle metadata.

        Args:
            bundle: Agent bundle containing manifest data
            package_path: Root path for the package
        """
        logger.debug("Writing manifest")

        manifest = {
            "bundle": {
                "id": str(bundle.id),
                "name": bundle.name,
                "version": bundle.version,
                "description": bundle.description,
                "created_at": bundle.created_at.isoformat(),
                "updated_at": bundle.updated_at.isoformat(),
            },
            "agents": [
                {
                    "id": str(agent.id),
                    "name": agent.name,
                    "type": agent.type,
                    "role": agent.role,
                    "description": agent.description,
                    "model": agent.model,
                    "capabilities": agent.capabilities,
                    "dependencies": agent.dependencies,
                    "file": f"agents/{agent.name}.md",
                }
                for agent in bundle.agents
            ],
            "metadata": bundle.metadata,
        }

        manifest_file = package_path / "manifest.json"
        with open(manifest_file, "w") as f:
            json.dump(manifest, f, indent=2)

    def write_readme(self, bundle: AgentBundle, package_path: Path) -> None:
        """
        Write README.md with installation and usage instructions.

        Args:
            bundle: Agent bundle
            package_path: Root path for the package
        """
        logger.debug("Writing README")

        agent_list = "\n".join(f"- **{agent.name}**: {agent.role}" for agent in bundle.agents)

        readme_content = f"""# {bundle.name}

{bundle.description}

## Installation

### Using UVX

```bash
uvx install {bundle.name}
```

### Using pip

```bash
pip install {bundle.name}
```

## Quick Start

```python
from {bundle.name} import load, get_agent

# Load the entire bundle
bundle = load()

# Get a specific agent
agent = get_agent("{bundle.agents[0].name if bundle.agents else "agent"}")

# Use the agent
result = agent.process("input data")
```

## Agents Included

{agent_list}

## Requirements

- Python >= 3.11
- amplihack >= 1.0.0

## Documentation

See the `docs/` directory for detailed documentation.

## Testing

```bash
pytest tests/
```

## License

MIT

---
Generated by Agent Bundle Generator v{bundle.version}
Bundle ID: {bundle.id}
"""

        (package_path / "README.md").write_text(readme_content)

    def write_python_init(self, bundle: AgentBundle, package_path: Path) -> None:
        """
        Write __init__.py with bundle API.

        Args:
            bundle: Agent bundle
            package_path: Root path for the package
        """
        logger.debug("Writing __init__.py")

        agent_names = [agent.name for agent in bundle.agents]
        agent_all = ", ".join(f'"{name}"' for name in agent_names)

        init_content = f'''"""
{bundle.name} - Agent Bundle

{bundle.description}
"""

__version__ = "{bundle.version}"
__bundle_id__ = "{bundle.id}"

import json
from pathlib import Path

# Load manifest
_manifest_path = Path(__file__).parent / "manifest.json"
with open(_manifest_path) as f:
    manifest = json.load(f)


def load():
    """Load the complete bundle."""
    return {{
        "manifest": manifest,
        "agents": {agent_names},
    }}


def get_agent(name):
    """Get agent metadata by name."""
    for agent in manifest.get("agents", []):
        if agent.get("name") == name:
            return agent
    return None


def list_agents():
    """List all available agents."""
    return [agent.get("name") for agent in manifest.get("agents", [])]


__all__ = [
    "manifest",
    "load",
    "get_agent",
    "list_agents",
    {agent_all},
]
'''

        (package_path / "__init__.py").write_text(init_content)

    def write_setup_py(self, bundle: AgentBundle, package_path: Path) -> None:
        """
        Write setup.py for Python packaging.

        Args:
            bundle: Agent bundle
            package_path: Root path for the package
        """
        logger.debug("Writing setup.py")

        # Sanitize description for Python string (escape quotes, single line)
        description_sanitized = bundle.description.replace("\n", " ").replace('"', '\\"').strip()

        setup_content = f'''"""Setup script for {bundle.name}."""

from setuptools import setup, find_packages

setup(
    name="{bundle.name}",
    version="{bundle.version}",
    description="{description_sanitized}",
    author="Agent Bundle Generator",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "amplihack>=1.0.0",
    ],
    package_data={{
        "": ["*.json", "*.md", "*.yaml"],
        "agents": ["*.md"],
        "tests": ["*.py"],
        "docs": ["*.md"],
        "config": ["*.json"],
    }},
    entry_points={{
        "amplihack.bundles": [
            "{bundle.name} = {bundle.name}:load",
        ],
    }},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
    ],
)
'''

        (package_path / "setup.py").write_text(setup_content)

    def write_pyproject_toml(self, bundle: AgentBundle, package_path: Path) -> None:
        """
        Write pyproject.toml for modern Python packaging.

        Args:
            bundle: Agent bundle
            package_path: Root path for the package
        """
        logger.debug("Writing pyproject.toml")

        # Sanitize description for TOML (single line, no newlines)
        description_sanitized = bundle.description.replace("\n", " ").replace('"', '\\"').strip()

        pyproject_content = f"""[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "{bundle.name}"
version = "{bundle.version}"
description = "{description_sanitized}"
readme = "README.md"
requires-python = ">=3.11"
license = {{text = "MIT"}}
authors = [
    {{name = "Agent Bundle Generator"}},
]
keywords = ["amplihack", "agents", "ai", "automation"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "amplihack>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "black>=23.0",
    "ruff>=0.1.0",
]

[project.entry-points."amplihack.bundles"]
{bundle.name} = "{bundle.name}:load"

[tool.setuptools.packages.find]
where = ["."]
include = ["{bundle.name}*", "agents*", "config*"]

[tool.setuptools.package-data]
"*" = ["*.md", "*.json", "*.yaml"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"

[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
target-version = "py311"
"""

        (package_path / "pyproject.toml").write_text(pyproject_content)

    def write_all_common_files(
        self, bundle: AgentBundle, package_path: Path, options: dict[str, Any] | None = None
    ) -> None:
        """
        Write all common files in one operation.

        This is a convenience method that calls all the individual write methods.

        Args:
            bundle: Agent bundle
            package_path: Root path for the package
            options: Optional packaging options (unused, for future extensibility)
        """
        self.create_directory_structure(package_path)
        self.write_agents(bundle, package_path)
        self.write_tests(bundle, package_path)
        self.write_documentation(bundle, package_path)
        self.write_configuration(bundle, package_path)
        self.write_manifest(bundle, package_path)
        self.write_readme(bundle, package_path)
        self.write_python_init(bundle, package_path)
        self.write_setup_py(bundle, package_path)
        self.write_pyproject_toml(bundle, package_path)
