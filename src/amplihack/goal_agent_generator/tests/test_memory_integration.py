"""Tests for memory integration in goal agent generator."""

import shutil
import tempfile
import uuid
from pathlib import Path

import pytest

from ..agent_assembler import AgentAssembler
from ..models import ExecutionPlan, GoalDefinition, PlanPhase, SkillDefinition
from ..packager import GoalAgentPackager
from ..templates.memory_template import (
    get_memory_config_yaml,
    get_memory_initialization_code,
    get_memory_readme_section,
)


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_goal_definition():
    """Create a sample goal definition."""
    return GoalDefinition(
        raw_prompt="Test goal prompt",
        goal="Test automated data processing",
        domain="data-processing",
        complexity="moderate",
    )


@pytest.fixture
def sample_execution_plan(sample_goal_definition):
    """Create a sample execution plan."""
    phases = [
        PlanPhase(
            name="Setup",
            description="Initialize processing",
            required_capabilities=["file-io", "data-validation"],
            estimated_duration="5 minutes",
        ),
        PlanPhase(
            name="Process",
            description="Process data",
            required_capabilities=["data-processing"],
            estimated_duration="10 minutes",
        ),
    ]

    plan = ExecutionPlan(
        goal_id=uuid.uuid4(),
        phases=phases,
        total_estimated_duration="15 minutes",
        required_skills=["file-reader", "data-processor"],
    )

    return plan


@pytest.fixture
def sample_skills():
    """Create sample skill definitions."""
    return [
        SkillDefinition(
            name="file-reader",
            source_path=Path("/fake/path/file-reader.md"),
            capabilities=["file-io"],
            description="Read files from disk",
            content="# File Reader\nReads files.",
            match_score=0.9,
        ),
    ]


class TestMemoryTemplate:
    """Tests for memory template generation."""

    def test_get_memory_initialization_code(self):
        """Test memory initialization code generation."""
        code = get_memory_initialization_code("test-agent", "./memory")

        assert "MemoryConnector" in code
        assert "ExperienceStore" in code
        assert "test-agent" in code
        assert "store_success" in code
        assert "store_failure" in code
        assert "store_pattern" in code
        assert "store_insight" in code
        assert "recall_relevant" in code
        assert "cleanup_memory" in code

    def test_get_memory_config_yaml(self):
        """Test memory config YAML generation."""
        config = get_memory_config_yaml("test-agent")

        assert "memory:" in config
        assert "enabled: true" in config
        assert "test-agent" in config
        assert "max_experiences: 1000" in config
        assert "auto_compress: true" in config

    def test_get_memory_readme_section(self):
        """Test memory README section generation."""
        section = get_memory_readme_section()

        assert "## Memory & Learning" in section
        assert "amplihack-memory-lib" in section
        assert "store_success" in section
        assert "recall_relevant" in section
        assert "Example Usage" in section


class TestAgentAssemblerMemory:
    """Tests for agent assembler with memory."""

    def test_assemble_without_memory(
        self, sample_goal_definition, sample_execution_plan, sample_skills
    ):
        """Test assembling agent without memory."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            sample_goal_definition,
            sample_execution_plan,
            sample_skills,
            bundle_name="test-agent",
            enable_memory=False,
        )

        assert bundle.name == "test-agent"
        assert "memory_enabled" not in bundle.metadata or not bundle.metadata["memory_enabled"]

    def test_assemble_with_memory(
        self, sample_goal_definition, sample_execution_plan, sample_skills
    ):
        """Test assembling agent with memory enabled."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            sample_goal_definition,
            sample_execution_plan,
            sample_skills,
            bundle_name="test-agent",
            enable_memory=True,
        )

        assert bundle.name == "test-agent"
        assert bundle.metadata["memory_enabled"] is True
        assert bundle.metadata["memory_storage_path"] == "./memory"


class TestPackagerMemory:
    """Tests for packager with memory integration."""

    def test_package_without_memory(
        self, temp_output_dir, sample_goal_definition, sample_execution_plan, sample_skills
    ):
        """Test packaging agent without memory."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            sample_goal_definition,
            sample_execution_plan,
            sample_skills,
            bundle_name="test-agent-no-mem",
            enable_memory=False,
        )

        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        # Check standard files exist
        assert (agent_dir / "main.py").exists()
        assert (agent_dir / "README.md").exists()
        assert (agent_dir / "requirements.txt").exists()

        # Check memory files don't exist
        assert not (agent_dir / "memory_config.yaml").exists()
        assert not (agent_dir / "memory").exists()

        # Check requirements.txt doesn't include memory lib
        requirements = (agent_dir / "requirements.txt").read_text()
        assert "amplihack-memory-lib" not in requirements

    def test_package_with_memory(
        self, temp_output_dir, sample_goal_definition, sample_execution_plan, sample_skills
    ):
        """Test packaging agent with memory enabled."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            sample_goal_definition,
            sample_execution_plan,
            sample_skills,
            bundle_name="test-agent-mem",
            enable_memory=True,
        )

        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        # Check standard files exist
        assert (agent_dir / "main.py").exists()
        assert (agent_dir / "README.md").exists()
        assert (agent_dir / "requirements.txt").exists()

        # Check memory-specific files exist
        assert (agent_dir / "memory_config.yaml").exists()
        assert (agent_dir / "memory").exists()
        assert (agent_dir / "memory" / ".gitignore").exists()

        # Check requirements.txt includes memory lib
        requirements = (agent_dir / "requirements.txt").read_text()
        assert "amplihack-memory-lib" in requirements

        # Check main.py includes memory imports
        main_content = (agent_dir / "main.py").read_text()
        assert "amplihack_memory" in main_content
        assert "MemoryConnector" in main_content
        assert "store_success" in main_content

        # Check README includes memory section
        readme = (agent_dir / "README.md").read_text()
        assert "Memory & Learning" in readme


class TestEndToEndMemoryIntegration:
    """End-to-end tests for memory integration."""

    def test_full_generation_with_memory(
        self, temp_output_dir, sample_goal_definition, sample_execution_plan, sample_skills
    ):
        """Test complete agent generation with memory."""
        # Assemble
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            sample_goal_definition,
            sample_execution_plan,
            sample_skills,
            bundle_name="full-test-agent",
            enable_memory=True,
        )

        # Package
        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        # Verify complete structure
        assert agent_dir.exists()
        assert (agent_dir / "main.py").exists()
        assert (agent_dir / "README.md").exists()
        assert (agent_dir / "requirements.txt").exists()
        assert (agent_dir / "memory_config.yaml").exists()
        assert (agent_dir / "memory").exists()

        # Verify main.py has proper memory initialization
        main_content = (agent_dir / "main.py").read_text()
        assert "MemoryConnector" in main_content
        assert "ExperienceStore" in main_content
        assert "cleanup_memory" in main_content

        # Verify memory config has correct agent name
        config = (agent_dir / "memory_config.yaml").read_text()
        assert "full-test-agent" in config

        # Verify .gitignore in memory directory
        gitignore = (agent_dir / "memory" / ".gitignore").read_text()
        assert "*.sqlite" in gitignore
        assert "*.db" in gitignore
