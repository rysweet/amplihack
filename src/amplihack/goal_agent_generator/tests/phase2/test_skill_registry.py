"""Tests for SkillRegistry."""

import json
import tempfile
from pathlib import Path

import pytest

from ...models import GeneratedSkillDefinition, SkillDefinition, ValidationResult
from ...phase2.skill_registry import SkillRegistry


class TestSkillRegistry:
    """Tests for SkillRegistry."""

    @pytest.fixture
    def temp_registry_path(self):
        """Create temporary registry file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "registry.json"

    @pytest.fixture
    def registry(self, temp_registry_path):
        """Create registry instance."""
        return SkillRegistry(registry_path=temp_registry_path, auto_load=False)

    @pytest.fixture
    def sample_skills(self):
        """Create sample skills."""
        return [
            SkillDefinition(
                name="analyzer",
                source_path=Path("analyzer.md"),
                capabilities=["analyze", "inspect", "review"],
                description="Analyzes code and data",
                content="# Analyzer skill",
                match_score=0.9,
            ),
            SkillDefinition(
                name="tester",
                source_path=Path("tester.md"),
                capabilities=["test", "validate", "verify"],
                description="Tests and validates code",
                content="# Tester skill",
                match_score=0.8,
            ),
            GeneratedSkillDefinition(
                name="documenter",
                source_path=Path("documenter.md"),
                capabilities=["document", "report"],
                description="Documents code and processes",
                content="# Documenter skill",
                generation_model="claude-3",
                generation_prompt="Generate documenter",
                match_score=0.85,
            ),
        ]

    def test_initialization(self, temp_registry_path):
        """Test registry initialization."""
        registry = SkillRegistry(registry_path=temp_registry_path, auto_load=False)

        assert registry.registry_path == temp_registry_path
        assert registry.count() == 0

    def test_register_skill(self, registry, sample_skills):
        """Test registering a single skill."""
        registry.register(sample_skills[0])

        assert registry.count() == 1
        assert registry.get_skill("analyzer") is not None

    def test_register_batch(self, registry, sample_skills):
        """Test registering multiple skills."""
        registry.register_batch(sample_skills)

        assert registry.count() == 3
        assert registry.get_skill("analyzer") is not None
        assert registry.get_skill("tester") is not None
        assert registry.get_skill("documenter") is not None

    def test_get_skill_exists(self, registry, sample_skills):
        """Test retrieving existing skill."""
        registry.register(sample_skills[0])

        skill = registry.get_skill("analyzer")

        assert skill is not None
        assert skill.name == "analyzer"
        assert "analyze" in skill.capabilities

    def test_get_skill_not_exists(self, registry):
        """Test retrieving non-existent skill."""
        skill = registry.get_skill("nonexistent")

        assert skill is None

    def test_search_by_capability(self, registry, sample_skills):
        """Test searching by single capability."""
        registry.register_batch(sample_skills)

        skills = registry.search_by_capability("test")

        assert len(skills) == 1
        assert skills[0].name == "tester"

    def test_search_by_capability_multiple_matches(self, registry, sample_skills):
        """Test searching capability with multiple matches."""
        # Add another skill with analyze capability
        extra_skill = SkillDefinition(
            name="data-analyzer",
            source_path=Path("data.md"),
            capabilities=["analyze", "process"],
            description="Data analysis",
            content="# Data analyzer",
        )

        registry.register_batch(sample_skills + [extra_skill])

        skills = registry.search_by_capability("analyze")

        assert len(skills) == 2
        skill_names = [s.name for s in skills]
        assert "analyzer" in skill_names
        assert "data-analyzer" in skill_names

    def test_search_by_capability_not_found(self, registry, sample_skills):
        """Test searching for non-existent capability."""
        registry.register_batch(sample_skills)

        skills = registry.search_by_capability("nonexistent")

        assert len(skills) == 0

    def test_search_by_capabilities_multiple(self, registry, sample_skills):
        """Test searching by multiple capabilities."""
        registry.register_batch(sample_skills)

        skills = registry.search_by_capabilities(["analyze", "test"])

        # Should return both analyzer and tester
        assert len(skills) >= 2

    def test_search_by_capabilities_ranks_by_matches(self, registry):
        """Test that search ranks results by match count."""
        skills = [
            SkillDefinition(
                name="skill-a",
                source_path=Path("a.md"),
                capabilities=["cap1"],
                description="A",
                content="# A",
            ),
            SkillDefinition(
                name="skill-b",
                source_path=Path("b.md"),
                capabilities=["cap1", "cap2"],
                description="B",
                content="# B",
            ),
            SkillDefinition(
                name="skill-c",
                source_path=Path("c.md"),
                capabilities=["cap1", "cap2", "cap3"],
                description="C",
                content="# C",
            ),
        ]

        registry.register_batch(skills)

        results = registry.search_by_capabilities(["cap1", "cap2", "cap3"])

        # skill-c should be first (3 matches), then skill-b (2), then skill-a (1)
        assert results[0].name == "skill-c"
        assert results[1].name == "skill-b"
        assert results[2].name == "skill-a"

    def test_search_by_domain(self, registry, sample_skills):
        """Test searching by domain."""
        registry.register_batch(sample_skills)

        # Should auto-categorize based on descriptions
        skills = registry.search_by_domain("testing")

        assert len(skills) > 0

    def test_list_all(self, registry, sample_skills):
        """Test listing all skills."""
        registry.register_batch(sample_skills)

        all_skills = registry.list_all()

        assert len(all_skills) == 3
        skill_names = [s.name for s in all_skills]
        assert "analyzer" in skill_names
        assert "tester" in skill_names
        assert "documenter" in skill_names

    def test_count(self, registry, sample_skills):
        """Test counting skills."""
        assert registry.count() == 0

        registry.register(sample_skills[0])
        assert registry.count() == 1

        registry.register_batch(sample_skills[1:])
        assert registry.count() == 3

    def test_clear(self, registry, sample_skills):
        """Test clearing registry."""
        registry.register_batch(sample_skills)
        assert registry.count() == 3

        registry.clear()
        assert registry.count() == 0
        assert registry.get_skill("analyzer") is None

    def test_remove_skill_exists(self, registry, sample_skills):
        """Test removing existing skill."""
        registry.register_batch(sample_skills)

        removed = registry.remove("analyzer")

        assert removed is True
        assert registry.count() == 2
        assert registry.get_skill("analyzer") is None

    def test_remove_skill_not_exists(self, registry):
        """Test removing non-existent skill."""
        removed = registry.remove("nonexistent")

        assert removed is False

    def test_save_and_load(self, registry, sample_skills, temp_registry_path):
        """Test saving and loading registry."""
        registry.register_batch(sample_skills)
        registry.save()

        # Create new registry instance and load
        new_registry = SkillRegistry(registry_path=temp_registry_path, auto_load=True)

        assert new_registry.count() == 3
        assert new_registry.get_skill("analyzer") is not None
        assert new_registry.get_skill("tester") is not None
        assert new_registry.get_skill("documenter") is not None

    def test_save_creates_valid_json(self, registry, sample_skills, temp_registry_path):
        """Test that saved file is valid JSON."""
        registry.register_batch(sample_skills)
        registry.save()

        # Read and parse JSON
        with open(temp_registry_path) as f:
            data = json.load(f)

        assert "version" in data
        assert "skills" in data
        assert "skill_count" in data
        assert data["skill_count"] == 3

    def test_load_nonexistent_file(self, registry):
        """Test loading from non-existent file."""
        # Should not raise error
        registry.load()
        assert registry.count() == 0

    def test_serialize_existing_skill(self, registry, sample_skills):
        """Test serializing existing skill."""
        skill = sample_skills[0]
        serialized = registry._serialize_skill(skill)

        assert serialized["name"] == "analyzer"
        assert serialized["type"] == "existing"
        assert "capabilities" in serialized
        assert "description" in serialized

    def test_serialize_generated_skill(self, registry, sample_skills):
        """Test serializing generated skill."""
        skill = sample_skills[2]  # documenter is generated
        serialized = registry._serialize_skill(skill)

        assert serialized["name"] == "documenter"
        assert serialized["type"] == "generated"
        assert "generation_model" in serialized
        assert "generation_prompt" in serialized

    def test_deserialize_existing_skill(self, registry):
        """Test deserializing existing skill."""
        data = {
            "type": "existing",
            "name": "test-skill",
            "source_path": "test.md",
            "capabilities": ["test"],
            "description": "Test",
            "content": "# Test",
            "match_score": 0.8,
        }

        skill = registry._deserialize_skill(data)

        assert skill is not None
        assert skill.name == "test-skill"
        assert not isinstance(skill, GeneratedSkillDefinition)

    def test_deserialize_generated_skill(self, registry):
        """Test deserializing generated skill."""
        data = {
            "type": "generated",
            "name": "gen-skill",
            "source_path": "gen.md",
            "capabilities": ["generate"],
            "description": "Generated",
            "content": "# Generated",
            "generation_model": "claude-3",
            "generation_prompt": "Prompt",
            "provenance": "ai_generated",
            "generated_at": "2024-01-01T00:00:00",
            "match_score": 0.9,
        }

        skill = registry._deserialize_skill(data)

        assert skill is not None
        assert isinstance(skill, GeneratedSkillDefinition)
        assert skill.generation_model == "claude-3"

    def test_deserialize_invalid_data(self, registry):
        """Test deserializing invalid data."""
        data = {"invalid": "data"}

        skill = registry._deserialize_skill(data)

        assert skill is None

    def test_extract_domain(self, registry):
        """Test domain extraction."""
        skill = SkillDefinition(
            name="test-skill",
            source_path=Path("test.md"),
            capabilities=["test"],
            description="Tests and validates code quality",
            content="# Tester",
        )

        domain = registry._extract_domain(skill)

        assert domain == "testing"

    def test_extract_domain_from_content(self, registry):
        """Test domain extraction from content."""
        skill = SkillDefinition(
            name="skill",
            source_path=Path("skill.md"),
            capabilities=["unknown"],
            description="Some skill",
            content="# Skill\n\nThis skill deploys applications to production",
        )

        domain = registry._extract_domain(skill)

        assert domain == "deployment"

    def test_extract_domain_default(self, registry):
        """Test default domain extraction."""
        skill = SkillDefinition(
            name="skill",
            source_path=Path("skill.md"),
            capabilities=["xyz"],
            description="Unknown skill",
            content="# Skill",
        )

        domain = registry._extract_domain(skill)

        assert domain == "general"

    def test_get_statistics(self, registry, sample_skills):
        """Test getting registry statistics."""
        registry.register_batch(sample_skills)

        stats = registry.get_statistics()

        assert stats["total_skills"] == 3
        assert stats["capabilities_count"] > 0
        assert stats["domains_count"] > 0
        assert "domains" in stats
        assert "top_capabilities" in stats
        assert stats["generated_skills"] == 1  # documenter
        assert stats["existing_skills"] == 2  # analyzer, tester

    def test_get_top_capabilities(self, registry):
        """Test getting top capabilities."""
        skills = [
            SkillDefinition(
                name=f"skill-{i}",
                source_path=Path(f"skill-{i}.md"),
                capabilities=["common", f"unique-{i}"],
                description=f"Skill {i}",
                content=f"# Skill {i}",
            )
            for i in range(3)
        ]

        registry.register_batch(skills)

        top = registry._get_top_capabilities(limit=2)

        # "common" should be first (3 occurrences)
        assert len(top) <= 2
        assert top[0][0] == "common"
        assert top[0][1] == 3

    def test_capability_indexing_case_insensitive(self, registry):
        """Test that capability indexing is case-insensitive."""
        skill = SkillDefinition(
            name="skill",
            source_path=Path("skill.md"),
            capabilities=["ANALYZE", "Test"],
            description="Skill",
            content="# Skill",
        )

        registry.register(skill)

        # Search with different case
        results = registry.search_by_capability("analyze")
        assert len(results) == 1

        results = registry.search_by_capability("test")
        assert len(results) == 1

    def test_auto_load_on_initialization(self, temp_registry_path, sample_skills):
        """Test auto-loading registry on initialization."""
        # Create and save registry
        registry1 = SkillRegistry(registry_path=temp_registry_path, auto_load=False)
        registry1.register_batch(sample_skills)
        registry1.save()

        # Create new instance with auto_load=True
        registry2 = SkillRegistry(registry_path=temp_registry_path, auto_load=True)

        assert registry2.count() == 3

    def test_registry_path_creation(self):
        """Test that registry path is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "nested" / "dir" / "registry.json"

            registry = SkillRegistry(registry_path=registry_path, auto_load=False)

            # Parent directory should be created
            assert registry_path.parent.exists()
