"""
Bundle builder for Agent Bundle Generator.

Assembles agents into complete bundles with proper structure and manifest.
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .exceptions import GenerationError
from .models import AgentBundle, ExtractedIntent, GeneratedAgent

logger = logging.getLogger(__name__)


class BundleBuilder:
    """
    Build agent bundles from generated agents.

    Creates complete bundle structures with manifests, metadata, and organization.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize the bundle builder.

        Args:
            output_dir: Optional output directory for bundles
        """
        self.output_dir = output_dir or Path.cwd() / "bundles"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build(
        self,
        agents: List[GeneratedAgent],
        intent: ExtractedIntent,
        name: Optional[str] = None,
        version: str = "1.0.0",
    ) -> AgentBundle:
        """
        Build a complete agent bundle.

        Args:
            agents: List of generated agents
            intent: Original extracted intent
            name: Optional bundle name
            version: Bundle version

        Returns:
            Complete AgentBundle

        Raises:
            GenerationError: If bundle building fails
        """
        if not agents:
            raise GenerationError(
                "Cannot build bundle without agents", generation_stage="bundle_building"
            )

        # Generate bundle name if not provided
        if not name:
            name = self._generate_bundle_name(intent, agents)

        # Create bundle metadata
        metadata = self._create_metadata(intent, agents)

        # Create manifest
        manifest = self._create_manifest(agents, name, version, metadata)

        # Create bundle
        bundle = AgentBundle(
            id=uuid.uuid4(),
            name=name,
            version=version,
            description=self._generate_description(intent, agents),
            agents=agents,
            manifest=manifest,
            metadata=metadata,
            status="ready",
        )

        # Validate bundle
        issues = self.validate_bundle(bundle)
        if issues:
            logger.warning(f"Bundle validation issues: {issues}")

        return bundle

    def _generate_bundle_name(self, intent: ExtractedIntent, agents: List[GeneratedAgent]) -> str:
        """Generate a bundle name from intent and agents."""
        # Use domain and action for name
        base_name = f"{intent.domain}_{intent.action}_bundle"

        # Clean up name
        base_name = base_name.replace("-", "_").lower()

        # Add agent count if multiple
        if len(agents) > 1:
            base_name += f"_{len(agents)}x"

        return base_name

    def _generate_description(self, intent: ExtractedIntent, agents: List[GeneratedAgent]) -> str:
        """Generate bundle description."""
        agent_names = [agent.name for agent in agents]

        description = f"""
Agent bundle for {intent.domain} domain with {intent.complexity} complexity.

Contains {len(agents)} specialized agents:
{", ".join(agent_names)}

Action: {intent.action}
Confidence: {intent.confidence:.1%}
        """.strip()

        return description

    def _create_metadata(
        self, intent: ExtractedIntent, agents: List[GeneratedAgent]
    ) -> Dict[str, Any]:
        """Create bundle metadata."""
        total_generation_time = sum(agent.generation_time_seconds for agent in agents)

        metadata = {
            "author": "Agent Bundle Generator",
            "created_at": datetime.utcnow().isoformat(),
            "intent": {
                "action": intent.action,
                "domain": intent.domain,
                "complexity": intent.complexity,
                "confidence": intent.confidence,
            },
            "statistics": {
                "agent_count": len(agents),
                "total_capabilities": sum(len(agent.capabilities) for agent in agents),
                "total_dependencies": len(
                    set(dep for agent in agents for dep in agent.dependencies)
                ),
                "generation_time_seconds": total_generation_time,
                "average_agent_time": total_generation_time / len(agents) if agents else 0,
            },
            "tags": self._generate_tags(intent, agents),
            "requirements": {
                "python": ">=3.11",
                "amplihack": ">=1.0.0",
            },
        }

        return metadata

    def _create_manifest(
        self, agents: List[GeneratedAgent], name: str, version: str, metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create bundle manifest."""
        manifest = {
            "manifest_version": "1.0",
            "bundle": {
                "name": name,
                "version": version,
                "description": f"Agent bundle containing {len(agents)} agents",
            },
            "agents": [
                {
                    "name": agent.name,
                    "type": agent.type,
                    "role": agent.role,
                    "file": f"agents/{agent.name}.md",
                    "capabilities": agent.capabilities,
                    "dependencies": agent.dependencies,
                    "model": agent.model,
                }
                for agent in agents
            ],
            "structure": {
                "root": ".",
                "agents_dir": "agents",
                "tests_dir": "tests",
                "docs_dir": "docs",
                "config_dir": "config",
            },
            "metadata": metadata,
            "installation": {
                "method": "uvx",
                "command": f"uvx install {name}",
                "requirements": metadata["requirements"],
            },
        }

        return manifest

    def _generate_tags(self, intent: ExtractedIntent, agents: List[GeneratedAgent]) -> List[str]:
        """Generate tags for the bundle."""
        tags = [
            intent.domain,
            intent.action,
            intent.complexity,
        ]

        # Add agent types
        agent_types = set(agent.type for agent in agents)
        tags.extend(agent_types)

        # Add capability tags
        all_capabilities = set()
        for agent in agents:
            all_capabilities.update(agent.capabilities)
        tags.extend(list(all_capabilities)[:5])  # Limit to top 5 capabilities

        return tags

    def write_bundle(self, bundle: AgentBundle, output_dir: Optional[Path] = None) -> Path:
        """
        Write bundle to disk.

        Args:
            bundle: AgentBundle to write
            output_dir: Optional output directory

        Returns:
            Path to bundle directory

        Raises:
            GenerationError: If writing fails
        """
        output_dir = output_dir or self.output_dir
        bundle_dir = output_dir / bundle.name

        try:
            # Create bundle directory structure
            bundle_dir.mkdir(parents=True, exist_ok=True)
            (bundle_dir / "agents").mkdir(exist_ok=True)
            (bundle_dir / "tests").mkdir(exist_ok=True)
            (bundle_dir / "docs").mkdir(exist_ok=True)
            (bundle_dir / "config").mkdir(exist_ok=True)

            # Write manifest
            manifest_path = bundle_dir / "manifest.json"
            with open(manifest_path, "w") as f:
                json.dump(bundle.manifest, f, indent=2)

            # Write agents
            for agent in bundle.agents:
                agent_path = bundle_dir / "agents" / f"{agent.name}.md"
                agent_path.write_text(agent.content)

                # Write tests if available
                if agent.tests:
                    test_path = bundle_dir / "tests" / f"test_{agent.name}.py"
                    test_path.write_text("\n".join(agent.tests))

                # Write documentation if available
                if agent.documentation:
                    doc_path = bundle_dir / "docs" / f"{agent.name}_docs.md"
                    doc_path.write_text(agent.documentation)

            # Write README
            readme_path = bundle_dir / "README.md"
            readme_content = self._generate_readme(bundle)
            readme_path.write_text(readme_content)

            # Write configuration
            config_path = bundle_dir / "config" / "bundle_config.json"
            with open(config_path, "w") as f:
                json.dump(
                    {
                        "bundle_id": str(bundle.id),
                        "version": bundle.version,
                        "metadata": bundle.metadata,
                    },
                    f,
                    indent=2,
                )

            logger.info(f"Bundle written to {bundle_dir}")
            return bundle_dir

        except Exception as e:
            raise GenerationError(
                f"Failed to write bundle: {e!s}",
                generation_stage="bundle_writing",
                partial_content=str(bundle_dir),
            )

    def _generate_readme(self, bundle: AgentBundle) -> str:
        """Generate README for bundle."""
        agent_list = "\n".join([f"- **{agent.name}**: {agent.role}" for agent in bundle.agents])

        return f"""# {bundle.name}

{bundle.description}

## Installation

```bash
uvx install {bundle.name}
```

## Agents

This bundle contains {len(bundle.agents)} agents:

{agent_list}

## Usage

```python
from amplihack.bundles import {bundle.name}

# Load the bundle
bundle = {bundle.name}.load()

# Access individual agents
for agent in bundle.agents:
    result = agent.process(data)
```

## Requirements

- Python >= 3.11
- amplihack >= 1.0.0

## Configuration

Configuration can be customized in `config/bundle_config.json`

## Testing

Run tests with:

```bash
pytest tests/
```

## Documentation

Additional documentation is available in the `docs/` directory.

## Metadata

- Version: {bundle.version}
- Created: {bundle.created_at.isoformat()}
- Agents: {len(bundle.agents)}
- Status: {bundle.status}

## License

MIT

---
Generated by Agent Bundle Generator v1.0.0
"""

    def validate_bundle(self, bundle: AgentBundle) -> List[str]:
        """
        Validate bundle structure and content.

        Args:
            bundle: Bundle to validate

        Returns:
            List of validation issues (empty if valid)
        """
        issues = []

        # Check bundle basics
        if not bundle.name:
            issues.append("Bundle missing name")
        if not bundle.agents:
            issues.append("Bundle has no agents")
        if not bundle.manifest:
            issues.append("Bundle missing manifest")

        # Check agent uniqueness
        agent_names = [agent.name for agent in bundle.agents]
        if len(agent_names) != len(set(agent_names)):
            issues.append("Duplicate agent names found")

        # Check manifest structure
        if bundle.manifest:
            required_keys = ["manifest_version", "bundle", "agents"]
            for key in required_keys:
                if key not in bundle.manifest:
                    issues.append(f"Manifest missing required key: {key}")

        # Validate each agent
        for agent in bundle.agents:
            if not agent.content:
                issues.append(f"Agent {agent.name} has no content")
            if len(agent.content) < 100:
                issues.append(f"Agent {agent.name} content too short")

        return issues

    def merge_bundles(self, bundles: List[AgentBundle], name: str = "merged_bundle") -> AgentBundle:
        """
        Merge multiple bundles into one.

        Args:
            bundles: List of bundles to merge
            name: Name for merged bundle

        Returns:
            Merged AgentBundle
        """
        if not bundles:
            raise GenerationError("No bundles to merge")

        # Collect all agents
        all_agents = []
        for bundle in bundles:
            all_agents.extend(bundle.agents)

        # Merge metadata
        merged_metadata = {
            "merged_from": [bundle.name for bundle in bundles],
            "merge_date": datetime.utcnow().isoformat(),
            "source_bundles": len(bundles),
            "total_agents": len(all_agents),
        }

        # Create merged bundle
        merged = AgentBundle(
            name=name,
            version="1.0.0",
            description=f"Merged bundle from {len(bundles)} source bundles",
            agents=all_agents,
            metadata=merged_metadata,
            manifest=self._create_manifest(all_agents, name, "1.0.0", merged_metadata),
            status="ready",
        )

        return merged
