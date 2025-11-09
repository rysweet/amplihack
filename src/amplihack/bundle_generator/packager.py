"""
UVX packager for Agent Bundle Generator.

Packages bundles for distribution via uvx package manager.
"""

import hashlib
import json
import logging
import shutil
import tarfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from .exceptions import PackagingError
from .models import AgentBundle, PackagedBundle

logger = logging.getLogger(__name__)


class UVXPackager:
    """
    Package agent bundles for UVX distribution.

    Creates uvx-compatible packages with proper structure and metadata.
    """

    # UVX package structure
    UVX_STRUCTURE = {
        "metadata": "uvx.json",
        "manifest": "manifest.json",
        "agents": "agents/",
        "tests": "tests/",
        "docs": "docs/",
        "config": "config/",
        "entry": "__init__.py",
    }

    def __init__(self, package_dir: Optional[Path] = None):
        """
        Initialize the UVX packager.

        Args:
            package_dir: Optional directory for packages
        """
        self.package_dir = package_dir or Path.cwd() / "packages"
        self.package_dir.mkdir(parents=True, exist_ok=True)

    def package(
        self,
        bundle: AgentBundle,
        format: Literal["tar.gz", "zip", "directory", "uvx"] = "uvx",
        options: Optional[Dict[str, Any]] = None,
    ) -> PackagedBundle:
        """
        Package a bundle for distribution.

        Args:
            bundle: Bundle to package
            format: Package format
            options: Optional packaging options

        Returns:
            PackagedBundle with package information

        Raises:
            PackagingError: If packaging fails
        """
        options = options or {}

        try:
            # Create package directory
            package_name = f"{bundle.name}-{bundle.version}"
            package_path = self.package_dir / package_name

            # Prepare bundle structure
            self._prepare_structure(bundle, package_path)

            # Create UVX metadata
            if format == "uvx":
                self._create_uvx_metadata(bundle, package_path)

            # Create package based on format
            if format == "tar.gz":
                final_path = self._create_tarball(package_path, options)
            elif format == "zip":
                final_path = self._create_zip(package_path, options)
            elif format == "directory":
                final_path = package_path
            elif format == "uvx":
                final_path = self._create_uvx_package(package_path, options)
            else:
                raise PackagingError(f"Unknown format: {format}", package_format=format)

            # Calculate checksum
            checksum = self._calculate_checksum(final_path)

            # Get package size
            if final_path.is_file():
                size_bytes = final_path.stat().st_size
            else:
                size_bytes = sum(f.stat().st_size for f in final_path.rglob("*") if f.is_file())

            # Create UVX metadata
            uvx_metadata = self._generate_uvx_metadata(bundle, format)

            return PackagedBundle(
                bundle=bundle,
                package_path=final_path,
                format=format,
                checksum=checksum,
                size_bytes=size_bytes,
                uvx_metadata=uvx_metadata,
            )

        except Exception as e:
            raise PackagingError(
                f"Failed to package bundle: {e!s}",
                package_format=format,
                file_path=str(package_path) if "package_path" in locals() else None,
            )

    def _prepare_structure(self, bundle: AgentBundle, package_path: Path) -> None:
        """Prepare bundle directory structure with agents, tests, and docs."""
        # Create directories
        package_path.mkdir(parents=True, exist_ok=True)
        (package_path / "agents").mkdir(exist_ok=True)
        (package_path / "tests").mkdir(exist_ok=True)
        (package_path / "docs").mkdir(exist_ok=True)
        (package_path / "config").mkdir(exist_ok=True)

        # Write agents
        for agent in bundle.agents:
            agent_file = package_path / "agents" / f"{agent.name}.md"
            agent_file.write_text(agent.content)

            # Write tests
            if agent.tests:
                test_file = package_path / "tests" / f"test_{agent.name}.py"
                test_file.write_text("\n".join(agent.tests))

            # Write docs
            if agent.documentation:
                doc_file = package_path / "docs" / f"{agent.name}_docs.md"
                doc_file.write_text(agent.documentation)

        # Write manifest
        manifest_file = package_path / "manifest.json"
        with open(manifest_file, "w") as f:
            json.dump(bundle.manifest, f, indent=2)

        # Write README
        readme_file = package_path / "README.md"
        readme_file.write_text(self._generate_readme(bundle))

        # Write configuration
        config_file = package_path / "config" / "bundle_config.json"
        with open(config_file, "w") as f:
            json.dump(bundle.metadata, f, indent=2)

    def _create_uvx_metadata(self, bundle: AgentBundle, package_path: Path) -> None:
        """Create UVX-specific metadata files and entry points."""
        uvx_metadata = {
            "name": bundle.name,
            "version": bundle.version,
            "description": bundle.description,
            "type": "agent-bundle",
            "entry_point": f"amplihack.bundles.{bundle.name}",
            "python_requirement": ">=3.11",
            "dependencies": {
                "amplihack": ">=1.0.0",
            },
            "agents": [
                {
                    "name": agent.name,
                    "type": agent.type,
                    "capabilities": agent.capabilities,
                }
                for agent in bundle.agents
            ],
            "metadata": bundle.metadata,
            "created": datetime.utcnow().isoformat(),
        }

        # Write UVX metadata
        uvx_file = package_path / "uvx.json"
        with open(uvx_file, "w") as f:
            json.dump(uvx_metadata, f, indent=2)

        # Create Python entry point
        init_file = package_path / "__init__.py"
        init_content = self._generate_init_file(bundle)
        init_file.write_text(init_content)

        # Create setup.py for compatibility
        setup_file = package_path / "setup.py"
        setup_content = self._generate_setup_file(bundle)
        setup_file.write_text(setup_content)

    def _generate_init_file(self, bundle: AgentBundle) -> str:
        """Generate __init__.py for the package."""
        agent_imports = "\n".join([f"from .agents import {agent.name}" for agent in bundle.agents])

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

# Import agents
{agent_imports}

# Bundle API
def load():
    """Load the complete bundle."""
    return {{
        "manifest": manifest,
        "agents": [{", ".join(agent.name for agent in bundle.agents)}],
    }}

def get_agent(name):
    """Get a specific agent by name."""
    agents = {{
        {", ".join(f'"{agent.name}": {agent.name}' for agent in bundle.agents)}
    }}
    return agents.get(name)

__all__ = [
    "manifest",
    "load",
    "get_agent",
    {", ".join(f'"{agent.name}"' for agent in bundle.agents)}
]
'''

    def _generate_setup_file(self, bundle: AgentBundle) -> str:
        """Generate setup.py for the package."""
        return f'''"""
Setup file for {bundle.name}
"""

from setuptools import setup, find_packages

setup(
    name="{bundle.name}",
    version="{bundle.version}",
    description="{bundle.description}",
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
    }},
    entry_points={{
        "amplihack.bundles": [
            "{bundle.name} = {bundle.name}:load",
        ],
    }},
)
'''

    def _generate_readme(self, bundle: AgentBundle) -> str:
        """Generate README for the package."""
        return f"""# {bundle.name}

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

{chr(10).join(f"- **{agent.name}**: {agent.role}" for agent in bundle.agents)}

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

    def _create_tarball(self, package_path: Path, options: Dict[str, Any]) -> Path:
        """Create a tar.gz archive."""
        compression = options.get("compression", "gzip")
        output_file = package_path.with_suffix(".tar.gz")

        with tarfile.open(
            output_file, f"w:{compression[0] if compression != 'none' else ''}"
        ) as tar:
            tar.add(package_path, arcname=package_path.name)

        # Clean up directory if requested
        if options.get("cleanup", True):
            shutil.rmtree(package_path)

        return output_file

    def _create_zip(self, package_path: Path, options: Dict[str, Any]) -> Path:
        """Create a zip archive."""
        output_file = package_path.with_suffix(".zip")
        compression = (
            zipfile.ZIP_DEFLATED if options.get("compression", True) else zipfile.ZIP_STORED
        )

        with zipfile.ZipFile(output_file, "w", compression) as zipf:
            for file_path in package_path.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(package_path.parent)
                    zipf.write(file_path, arcname)

        # Clean up directory if requested
        if options.get("cleanup", True):
            shutil.rmtree(package_path)

        return output_file

    def _create_uvx_package(self, package_path: Path, options: Dict[str, Any]) -> Path:
        """Create a UVX-specific package."""
        # UVX packages are tar.gz with specific structure
        output_file = package_path.with_suffix(".uvx")

        # Create tar.gz with UVX extension
        with tarfile.open(output_file, "w:gz") as tar:
            tar.add(package_path, arcname=package_path.name)

        # Clean up directory if requested
        if options.get("cleanup", True):
            shutil.rmtree(package_path)

        return output_file

    def _calculate_checksum(self, path: Path) -> str:
        """Calculate SHA256 checksum of package."""
        sha256 = hashlib.sha256()

        if path.is_file():
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
        else:
            # For directories, checksum all files
            for file_path in sorted(path.rglob("*")):
                if file_path.is_file():
                    with open(file_path, "rb") as f:
                        for chunk in iter(lambda: f.read(4096), b""):
                            sha256.update(chunk)

        return sha256.hexdigest()

    def _generate_uvx_metadata(self, bundle: AgentBundle, format: str) -> Dict[str, Any]:
        """Generate UVX metadata for the package."""
        return {
            "format_version": "1.0.0",
            "package_format": format,
            "bundle_id": str(bundle.id),
            "bundle_name": bundle.name,
            "bundle_version": bundle.version,
            "python_requirement": ">=3.11",
            "amplihack_requirement": ">=1.0.0",
            "entry_point": f"amplihack.bundles.{bundle.name}",
            "install_command": f"uvx install {bundle.name}",
            "agent_count": len(bundle.agents),
            "created_at": datetime.utcnow().isoformat(),
        }

    def extract_package(self, package_path: Path, target_path: Path) -> AgentBundle:
        """
        Extract a packaged bundle.

        Args:
            package_path: Path to package file
            target_path: Target directory for extraction

        Returns:
            Extracted AgentBundle

        Raises:
            PackagingError: If extraction fails
        """
        if not package_path.exists():
            raise PackagingError(f"Package not found: {package_path}")

        try:
            target_path.mkdir(parents=True, exist_ok=True)

            # Extract based on format
            if package_path.suffix == ".zip":
                with zipfile.ZipFile(package_path, "r") as zipf:
                    zipf.extractall(target_path)
            elif package_path.suffix in [".tar", ".gz", ".uvx"]:
                with tarfile.open(package_path, "r:*") as tar:
                    tar.extractall(target_path)
            else:
                raise PackagingError(f"Unknown package format: {package_path.suffix}")

            # Find and load manifest
            manifest_files = list(target_path.rglob("manifest.json"))
            if not manifest_files:
                raise PackagingError("No manifest found in package")

            manifest_path = manifest_files[0]
            bundle_root = manifest_path.parent

            with open(manifest_path) as f:
                manifest = json.load(f)

            # Load agents from extracted files
            from .models import GeneratedAgent

            agents = []
            agents_dir = bundle_root / "agents"
            if agents_dir.exists():
                for agent_info in manifest.get("agents", []):
                    agent_file = agents_dir / f"{agent_info['name']}.md"
                    if agent_file.exists():
                        agent = GeneratedAgent(
                            name=agent_info["name"],
                            type=agent_info.get("type", "specialized"),
                            role=agent_info.get("role", ""),
                            description=agent_info.get("description", ""),
                            content=agent_file.read_text(),
                            capabilities=agent_info.get("capabilities", []),
                            dependencies=agent_info.get("dependencies", []),
                        )
                        agents.append(agent)

            # Reconstruct bundle
            bundle = AgentBundle(
                name=manifest["bundle"]["name"],
                version=manifest["bundle"]["version"],
                description=manifest["bundle"]["description"],
                agents=agents,
                manifest=manifest,
                metadata=manifest.get("metadata", {}),
                status="ready",
            )

            return bundle

        except Exception as e:
            raise PackagingError(f"Failed to extract package: {e!s}", file_path=str(package_path))
