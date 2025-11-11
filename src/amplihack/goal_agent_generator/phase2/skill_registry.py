"""
Skill Registry - Central registry for all skills (existing + generated).

Provides in-memory cache with disk persistence, indexed by name, capabilities, and domain.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from ..models import GeneratedSkillDefinition, SkillDefinition


class SkillRegistry:
    """Central registry for managing skills."""

    # Default registry file location
    DEFAULT_REGISTRY_PATH = Path.home() / ".claude" / "skills_registry.json"

    def __init__(self, registry_path: Optional[Path] = None, auto_load: bool = True):
        """
        Initialize skill registry.

        Args:
            registry_path: Path to registry JSON file
            auto_load: Whether to automatically load existing registry
        """
        self.registry_path = registry_path or self.DEFAULT_REGISTRY_PATH

        # In-memory storage
        self._skills: Dict[str, SkillDefinition] = {}
        self._capabilities_index: Dict[str, Set[str]] = {}  # capability -> skill_names
        self._domain_index: Dict[str, Set[str]] = {}  # domain -> skill_names

        # Ensure registry directory exists
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing registry if requested
        if auto_load and self.registry_path.exists():
            self.load()

    def register(self, skill: SkillDefinition) -> None:
        """
        Register a skill in the registry.

        Args:
            skill: Skill to register
        """
        # Store skill
        self._skills[skill.name] = skill

        # Index by capabilities
        for capability in skill.capabilities:
            cap_lower = capability.lower()
            if cap_lower not in self._capabilities_index:
                self._capabilities_index[cap_lower] = set()
            self._capabilities_index[cap_lower].add(skill.name)

        # Index by domain (extract from description or use default)
        domain = self._extract_domain(skill)
        if domain not in self._domain_index:
            self._domain_index[domain] = set()
        self._domain_index[domain].add(skill.name)

    def register_batch(self, skills: List[SkillDefinition]) -> None:
        """
        Register multiple skills at once.

        Args:
            skills: List of skills to register
        """
        for skill in skills:
            self.register(skill)

    def get_skill(self, name: str) -> Optional[SkillDefinition]:
        """
        Retrieve a skill by name.

        Args:
            name: Skill name

        Returns:
            SkillDefinition or None if not found
        """
        return self._skills.get(name)

    def search_by_capability(self, capability: str) -> List[SkillDefinition]:
        """
        Search for skills by capability.

        Args:
            capability: Capability to search for

        Returns:
            List of matching skills
        """
        cap_lower = capability.lower()
        skill_names = self._capabilities_index.get(cap_lower, set())

        return [self._skills[name] for name in skill_names if name in self._skills]

    def search_by_capabilities(self, capabilities: List[str]) -> List[SkillDefinition]:
        """
        Search for skills matching multiple capabilities.

        Args:
            capabilities: List of capabilities to search for

        Returns:
            List of skills sorted by match count (most matches first)
        """
        # Count matches for each skill
        skill_matches: Dict[str, int] = {}

        for capability in capabilities:
            cap_lower = capability.lower()
            skill_names = self._capabilities_index.get(cap_lower, set())

            for skill_name in skill_names:
                skill_matches[skill_name] = skill_matches.get(skill_name, 0) + 1

        # Sort by match count descending
        sorted_skills = sorted(skill_matches.items(), key=lambda x: x[1], reverse=True)

        return [self._skills[name] for name, _ in sorted_skills if name in self._skills]

    def search_by_domain(self, domain: str) -> List[SkillDefinition]:
        """
        Search for skills by domain.

        Args:
            domain: Domain to search for

        Returns:
            List of matching skills
        """
        domain_lower = domain.lower()
        skill_names = self._domain_index.get(domain_lower, set())

        return [self._skills[name] for name in skill_names if name in self._skills]

    def list_all(self) -> List[SkillDefinition]:
        """
        Get all registered skills.

        Returns:
            List of all skills
        """
        return list(self._skills.values())

    def count(self) -> int:
        """
        Get total number of registered skills.

        Returns:
            Number of skills
        """
        return len(self._skills)

    def clear(self) -> None:
        """Clear all skills from registry."""
        self._skills.clear()
        self._capabilities_index.clear()
        self._domain_index.clear()

    def remove(self, skill_name: str) -> bool:
        """
        Remove a skill from registry.

        Args:
            skill_name: Name of skill to remove

        Returns:
            True if skill was removed, False if not found
        """
        if skill_name not in self._skills:
            return False

        skill = self._skills[skill_name]

        # Remove from skills
        del self._skills[skill_name]

        # Remove from capability index
        for capability in skill.capabilities:
            cap_lower = capability.lower()
            if cap_lower in self._capabilities_index:
                self._capabilities_index[cap_lower].discard(skill_name)
                if not self._capabilities_index[cap_lower]:
                    del self._capabilities_index[cap_lower]

        # Remove from domain index
        domain = self._extract_domain(skill)
        if domain in self._domain_index:
            self._domain_index[domain].discard(skill_name)
            if not self._domain_index[domain]:
                del self._domain_index[domain]

        return True

    def save(self) -> None:
        """Save registry to disk."""
        registry_data = {
            "version": "1.0.0",
            "saved_at": datetime.utcnow().isoformat(),
            "skill_count": len(self._skills),
            "skills": [self._serialize_skill(skill) for skill in self._skills.values()],
        }

        with open(self.registry_path, "w") as f:
            json.dump(registry_data, f, indent=2)

    def load(self) -> None:
        """Load registry from disk."""
        if not self.registry_path.exists():
            return

        with open(self.registry_path, "r") as f:
            registry_data = json.load(f)

        # Clear existing data
        self.clear()

        # Load skills
        for skill_data in registry_data.get("skills", []):
            skill = self._deserialize_skill(skill_data)
            if skill:
                self.register(skill)

    def _serialize_skill(self, skill: SkillDefinition) -> dict:
        """
        Serialize a skill to JSON-compatible dict.

        Args:
            skill: Skill to serialize

        Returns:
            Dictionary representation
        """
        data = {
            "name": skill.name,
            "source_path": str(skill.source_path),
            "capabilities": skill.capabilities,
            "description": skill.description,
            "content": skill.content,
            "dependencies": skill.dependencies,
            "match_score": skill.match_score,
        }

        # Add generated skill fields if applicable
        if isinstance(skill, GeneratedSkillDefinition):
            data["type"] = "generated"
            data["generation_prompt"] = skill.generation_prompt
            data["generation_model"] = skill.generation_model
            data["provenance"] = skill.provenance
            data["generated_at"] = skill.generated_at.isoformat()

            if skill.validation_result:
                data["validation_result"] = {
                    "passed": skill.validation_result.passed,
                    "issues": skill.validation_result.issues,
                    "warnings": skill.validation_result.warnings,
                    "quality_score": skill.validation_result.quality_score,
                }
        else:
            data["type"] = "existing"

        return data

    def _deserialize_skill(self, data: dict) -> Optional[SkillDefinition]:
        """
        Deserialize a skill from JSON dict.

        Args:
            data: Dictionary representation

        Returns:
            SkillDefinition or None if deserialization fails
        """
        try:
            skill_type = data.get("type", "existing")

            if skill_type == "generated":
                from ..models import ValidationResult

                validation_result = None
                if "validation_result" in data:
                    vr = data["validation_result"]
                    validation_result = ValidationResult(
                        passed=vr["passed"],
                        issues=vr["issues"],
                        warnings=vr["warnings"],
                        quality_score=vr["quality_score"],
                    )

                return GeneratedSkillDefinition(
                    name=data["name"],
                    source_path=Path(data["source_path"]),
                    capabilities=data["capabilities"],
                    description=data["description"],
                    content=data["content"],
                    dependencies=data.get("dependencies", []),
                    match_score=data.get("match_score", 0.0),
                    generation_prompt=data.get("generation_prompt", ""),
                    generation_model=data.get("generation_model", ""),
                    validation_result=validation_result,
                    provenance=data.get("provenance", "ai_generated"),
                    generated_at=datetime.fromisoformat(data["generated_at"]),
                )
            else:
                return SkillDefinition(
                    name=data["name"],
                    source_path=Path(data["source_path"]),
                    capabilities=data["capabilities"],
                    description=data["description"],
                    content=data["content"],
                    dependencies=data.get("dependencies", []),
                    match_score=data.get("match_score", 0.0),
                )

        except Exception as e:
            print(f"Error deserializing skill: {e}")
            return None

    def _extract_domain(self, skill: SkillDefinition) -> str:
        """
        Extract domain from skill description.

        Args:
            skill: Skill to extract domain from

        Returns:
            Domain string (lowercase)
        """
        # Common domain keywords
        domain_keywords = {
            "data": ["data", "processing", "transform", "parse"],
            "security": ["security", "vulnerability", "audit", "scan"],
            "testing": ["test", "validate", "verify", "qa"],
            "deployment": ["deploy", "release", "publish", "ship"],
            "monitoring": ["monitor", "alert", "track", "observe"],
            "documentation": ["document", "report", "readme"],
            "analysis": ["analyze", "review", "inspect", "examine"],
            "development": ["build", "create", "generate", "implement"],
            "optimization": ["optimize", "improve", "enhance", "performance"],
            "integration": ["integrate", "connect", "api", "webhook"],
        }

        description_lower = skill.description.lower()
        content_lower = skill.content[:500].lower()  # First 500 chars

        # Check each domain's keywords
        for domain, keywords in domain_keywords.items():
            if any(kw in description_lower or kw in content_lower for kw in keywords):
                return domain

        # Default domain
        return "general"

    def get_statistics(self) -> dict:
        """
        Get registry statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "total_skills": len(self._skills),
            "capabilities_count": len(self._capabilities_index),
            "domains_count": len(self._domain_index),
            "domains": list(self._domain_index.keys()),
            "top_capabilities": self._get_top_capabilities(5),
            "generated_skills": sum(
                1 for s in self._skills.values() if isinstance(s, GeneratedSkillDefinition)
            ),
            "existing_skills": sum(
                1 for s in self._skills.values() if not isinstance(s, GeneratedSkillDefinition)
            ),
        }

    def _get_top_capabilities(self, limit: int = 5) -> List[tuple[str, int]]:
        """
        Get most common capabilities.

        Args:
            limit: Maximum number to return

        Returns:
            List of (capability, count) tuples
        """
        capability_counts = [
            (cap, len(skills)) for cap, skills in self._capabilities_index.items()
        ]

        capability_counts.sort(key=lambda x: x[1], reverse=True)

        return capability_counts[:limit]
