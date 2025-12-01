"""Filesystem package orchestrator for agent bundles."""

import json
import logging
import subprocess
import sys
from pathlib import Path

from .documentation_generator import generate_instructions
from .exceptions import PackagingError
from .models import AgentBundle
from .repackage_generator import (
    generate_bash_script,
    generate_python_script,
    make_executable,
)

logger = logging.getLogger(__name__)


class FilesystemPackager:
    """
    Create complete filesystem packages for agent bundles.

    Orchestrates creation of all necessary files including agents, documentation,
    repackaging scripts, and build artifacts.
    """

    def __init__(self, output_dir: Path):
        """
        Initialize filesystem packager.

        Args:
            output_dir: Directory where package will be created
        """
        if not output_dir:
            raise ValueError("output_dir cannot be None or empty")

        self.output_dir = Path(output_dir)
        self._validate_output_dir()

    def _validate_output_dir(self) -> None:
        """
        Validate output directory path for security.

        Raises:
            PackagingError: If path is unsafe
        """
        resolved = self.output_dir.resolve()

        # Prevent writing to system directories (but allow temp directories)
        unsafe_paths = [
            Path("/"),
            Path("/etc"),
            Path("/usr"),
            Path("/bin"),
            Path("/sbin"),
            Path("/sys"),
            Path("/proc"),
            Path("/dev"),
        ]

        # Allow common temp directory patterns
        allowed_temp_patterns = [
            "/tmp/",
            "/var/tmp/",
            "/var/folders/",  # macOS temp
            "/private/var/folders/",  # macOS temp (canonical)
        ]

        resolved_str = str(resolved)
        is_temp_dir = any(resolved_str.startswith(pattern) for pattern in allowed_temp_patterns)

        if not is_temp_dir:
            for unsafe_path in unsafe_paths:
                if resolved == unsafe_path or resolved.is_relative_to(unsafe_path):
                    raise PackagingError(
                        f"Cannot write to system directory: {resolved}. Choose a user directory for output."
                    )

    def create_package(
        self,
        bundle: AgentBundle,
        build_uvx: bool = True,
        options: dict | None = None,
    ) -> Path:
        """
        Create complete filesystem package.

        Creates:
        - agents/ directory with all agent markdown files
        - tests/ directory with test files
        - docs/ directory with documentation
        - config/ directory with configuration
        - pyproject.toml, setup.py for Python packaging
        - manifest.json with bundle metadata
        - README.md with quick reference
        - INSTRUCTIONS.md with detailed usage guide (NEW)
        - repackage.sh bash script (NEW)
        - repackage.py python script (NEW)
        - dist/*.uvx if build_uvx=True (NEW)

        Args:
            bundle: AgentBundle to package
            build_uvx: Whether to build UVX package (default True)
            options: Optional packaging options

        Returns:
            Path to created package directory

        Raises:
            PackagingError: If package creation fails
        """
        options = options or {}

        try:
            # Create package directory
            package_name = f"{bundle.name}-{bundle.version}"
            package_path = self.output_dir / package_name

            logger.info(f"Creating filesystem package at: {package_path}")

            # Create directory structure
            self._create_directory_structure(package_path)

            # Write agents
            self._write_agents(bundle, package_path)

            # Write tests
            self._write_tests(bundle, package_path)

            # Write documentation
            self._write_documentation(bundle, package_path)

            # Write configuration
            self._write_configuration(bundle, package_path)

            # Write Python packaging files
            self._write_python_packaging(bundle, package_path)

            # Write manifest
            self._write_manifest(bundle, package_path)

            # Write README
            self._write_readme(bundle, package_path)

            # Write INSTRUCTIONS.md (NEW)
            self._write_instructions(bundle, package_path)

            # Write repackage scripts (NEW)
            self._write_repackage_scripts(bundle, package_path)

            # Build UVX package if requested (NEW)
            if build_uvx:
                self._build_uvx_package(bundle, package_path)

            logger.info(f"Successfully created package at: {package_path}")
            return package_path

        except Exception as e:
            logger.error(f"Failed to create filesystem package: {e}")
            raise PackagingError(
                f"Failed to create filesystem package: {e!s}. Check file permissions and disk space."
            )

    def _create_directory_structure(self, package_path: Path) -> None:
        """Create package directory structure."""
        logger.debug("Creating directory structure")

        directories = [
            package_path,
            package_path / "agents",
            package_path / "tests",
            package_path / "docs",
            package_path / "config",
            package_path / "dist",
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def _write_agents(self, bundle: AgentBundle, package_path: Path) -> None:
        """Write agent markdown files."""
        logger.debug(f"Writing {len(bundle.agents)} agents")

        agents_dir = package_path / "agents"
        for agent in bundle.agents:
            agent_file = agents_dir / f"{agent.name}.md"
            agent_file.write_text(agent.content)

    def _write_tests(self, bundle: AgentBundle, package_path: Path) -> None:
        """Write test files."""
        logger.debug("Writing tests")

        tests_dir = package_path / "tests"

        # Create __init__.py for tests package
        (tests_dir / "__init__.py").write_text('"""Tests for agent bundle."""\n')

        # Write agent tests
        for agent in bundle.agents:
            if agent.tests:
                test_file = tests_dir / f"test_{agent.name}.py"
                test_file.write_text("\n".join(agent.tests))

    def _write_documentation(self, bundle: AgentBundle, package_path: Path) -> None:
        """Write documentation files."""
        logger.debug("Writing documentation")

        docs_dir = package_path / "docs"

        # Write agent-specific documentation
        for agent in bundle.agents:
            if agent.documentation:
                doc_file = docs_dir / f"{agent.name}_docs.md"
                doc_file.write_text(agent.documentation)

    def _write_configuration(self, bundle: AgentBundle, package_path: Path) -> None:
        """Write configuration files."""
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

    def _write_python_packaging(self, bundle: AgentBundle, package_path: Path) -> None:
        """Write Python packaging files (pyproject.toml, setup.py)."""
        logger.debug("Writing Python packaging files")

        # Write pyproject.toml
        pyproject_content = self._generate_pyproject_toml(bundle)
        (package_path / "pyproject.toml").write_text(pyproject_content)

        # Write setup.py
        setup_content = self._generate_setup_py(bundle)
        (package_path / "setup.py").write_text(setup_content)

        # Write __init__.py
        init_content = self._generate_init_py(bundle)
        (package_path / "__init__.py").write_text(init_content)

    def _generate_pyproject_toml(self, bundle: AgentBundle) -> str:
        """Generate pyproject.toml content."""
        # Sanitize description for TOML (single line, no newlines)
        description_sanitized = bundle.description.replace("\n", " ").replace('"', '\\"').strip()

        return f"""[build-system]
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

    def _generate_setup_py(self, bundle: AgentBundle) -> str:
        """Generate setup.py content."""
        # Sanitize description for Python string (escape quotes, single line)
        description_sanitized = bundle.description.replace("\n", " ").replace('"', '\\"').strip()

        return f'''"""Setup script for {bundle.name}."""

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

    def _generate_init_py(self, bundle: AgentBundle) -> str:
        """Generate __init__.py content."""
        agent_names = [agent.name for agent in bundle.agents]
        agent_all = ", ".join(f'"{name}"' for name in agent_names)

        return f'''"""
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

    def _write_manifest(self, bundle: AgentBundle, package_path: Path) -> None:
        """Write manifest.json."""
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

    def _write_readme(self, bundle: AgentBundle, package_path: Path) -> None:
        """Write README.md."""
        logger.debug("Writing README")

        agent_list = "\n".join(f"- **{agent.name}**: {agent.role}" for agent in bundle.agents)

        readme_content = f"""# {bundle.name}

{bundle.description}

## Quick Start

### Installation

```bash
# Using UVX
uvx install {bundle.name}-{bundle.version}.uvx

# Using pip
pip install -e .
```

### Usage

```python
from {bundle.name} import load, get_agent

# Load bundle
bundle = load()

# Get specific agent
agent = get_agent("{bundle.agents[0].name if bundle.agents else "agent-name"}")
```

## Agents

{agent_list}

## Documentation

See [INSTRUCTIONS.md](INSTRUCTIONS.md) for detailed usage instructions.

## Requirements

- Python >= 3.11
- amplihack >= 1.0.0

## Testing

```bash
pytest tests/
```

## Repackaging

After making changes, use the provided scripts:

```bash
# Bash
./repackage.sh

# Python
python repackage.py
```

## License

MIT

---

Generated by Agent Bundle Generator v{bundle.version}
Bundle ID: {bundle.id}
"""

        (package_path / "README.md").write_text(readme_content)

    def _write_instructions(self, bundle: AgentBundle, package_path: Path) -> None:
        """Write INSTRUCTIONS.md with detailed usage guide."""
        logger.debug("Writing INSTRUCTIONS.md")

        instructions_content = generate_instructions(bundle)
        (package_path / "INSTRUCTIONS.md").write_text(instructions_content)

    def _write_repackage_scripts(self, bundle: AgentBundle, package_path: Path) -> None:
        """Write repackage.sh and repackage.py scripts."""
        logger.debug("Writing repackage scripts")

        # Write bash script
        bash_script_content = generate_bash_script(bundle)
        bash_script_path = package_path / "repackage.sh"
        bash_script_path.write_text(bash_script_content)
        make_executable(bash_script_path)

        # Write python script
        python_script_content = generate_python_script(bundle)
        python_script_path = package_path / "repackage.py"
        python_script_path.write_text(python_script_content)
        make_executable(python_script_path)

    def _build_uvx_package(self, bundle: AgentBundle, package_path: Path) -> None:
        """Build UVX package in dist/ directory."""
        logger.debug("Building UVX package")

        # Check if we're in the package directory structure
        # We need to run setup.py from the package directory
        dist_dir = package_path / "dist"
        dist_dir.mkdir(exist_ok=True)

        try:
            # Try building with setup.py
            result = subprocess.run(
                [sys.executable, "setup.py", "sdist", f"--dist-dir={dist_dir}"],
                check=False,
                cwd=package_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                logger.info("Successfully built source distribution")
            else:
                logger.warning(f"Source distribution build failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            logger.warning("UVX package build timed out")
        except Exception as e:
            logger.warning(f"UVX package build failed: {e}")
            # Non-fatal - package can still be used without .uvx file
