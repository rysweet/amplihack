"""Tests for multi-agent packaging in the goal agent generator.

Verifies that --multi-agent and --enable-spawning produce correct
sub-agent configs, directory structure, and YAML files.
"""

from __future__ import annotations

import json
import tempfile
import uuid
from pathlib import Path

import pytest

from src.amplihack.goal_agent_generator.agent_assembler import AgentAssembler
from src.amplihack.goal_agent_generator.models import (
    ExecutionPlan,
    GoalDefinition,
    PlanPhase,
    SkillDefinition,
    SubAgentConfig,
)
from src.amplihack.goal_agent_generator.packager import GoalAgentPackager
from src.amplihack.goal_agent_generator.templates.multi_agent_template import (
    get_coordinator_yaml,
    get_memory_agent_yaml,
    get_multi_agent_init_code,
    get_multi_agent_readme_section,
    get_spawner_yaml,
)


# --- Fixtures ---


@pytest.fixture
def goal_definition():
    return GoalDefinition(
        raw_prompt="Build a data pipeline",
        goal="Build a data pipeline",
        domain="data-processing",
        constraints=["Must handle 1M records"],
        success_criteria=["Pipeline runs end-to-end"],
    )


@pytest.fixture
def execution_plan():
    phases = [
        PlanPhase(
            name="Extract",
            description="Extract data from sources",
            required_capabilities=["read", "file"],
            estimated_duration="10 minutes",
        ),
        PlanPhase(
            name="Transform",
            description="Transform data",
            required_capabilities=["process", "transform"],
            estimated_duration="15 minutes",
        ),
        PlanPhase(
            name="Load",
            description="Load data into destination",
            required_capabilities=["write", "file"],
            estimated_duration="10 minutes",
        ),
    ]
    return ExecutionPlan(
        goal_id=uuid.uuid4(),
        phases=phases,
        total_estimated_duration="35 minutes",
        required_skills=["data-processor"],
    )


@pytest.fixture
def sample_skills():
    return [
        SkillDefinition(
            name="data-processor",
            source_path=Path("builtin"),
            capabilities=["data", "process"],
            description="Processes data",
            content="# Data Processor\nProcesses data.",
            match_score=0.7,
        )
    ]


@pytest.fixture
def temp_output_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# --- SubAgentConfig Model Tests ---


class TestSubAgentConfig:
    """Test SubAgentConfig dataclass."""

    def test_default_filename_from_role(self):
        """Filename should be auto-generated from role if not specified."""
        config = SubAgentConfig(role="coordinator", config={"role": "task_classifier"})
        assert config.filename == "coordinator.yaml"

    def test_custom_filename(self):
        """Custom filename should be preserved."""
        config = SubAgentConfig(
            role="coordinator",
            config={"role": "task_classifier"},
            filename="custom.yaml",
        )
        assert config.filename == "custom.yaml"


# --- Template Tests ---


class TestMultiAgentTemplates:
    """Test YAML template generation functions."""

    def test_coordinator_yaml_contains_strategies(self):
        yaml_content = get_coordinator_yaml("test-agent")
        assert "role: task_classifier" in yaml_content
        assert "entity_centric" in yaml_content
        assert "temporal" in yaml_content
        assert "aggregation" in yaml_content
        assert "full_text" in yaml_content
        assert "simple_all" in yaml_content
        assert "two_phase" in yaml_content
        assert "test-agent" in yaml_content

    def test_memory_agent_yaml_contains_settings(self):
        yaml_content = get_memory_agent_yaml("test-agent")
        assert "role: retrieval_specialist" in yaml_content
        assert "max_facts: 300" in yaml_content
        assert "summarization_threshold: 1000" in yaml_content
        assert "test-agent" in yaml_content

    def test_spawner_yaml_enabled(self):
        yaml_content = get_spawner_yaml("test-agent", enable_spawning=True)
        assert "enabled: true" in yaml_content
        assert "retrieval" in yaml_content
        assert "analysis" in yaml_content
        assert "synthesis" in yaml_content
        assert "code_generation" in yaml_content
        assert "research" in yaml_content
        assert "max_concurrent: 3" in yaml_content
        assert "timeout: 60" in yaml_content

    def test_spawner_yaml_disabled(self):
        yaml_content = get_spawner_yaml("test-agent", enable_spawning=False)
        assert "enabled: false" in yaml_content

    def test_spawner_yaml_custom_limits(self):
        yaml_content = get_spawner_yaml(
            "test-agent", enable_spawning=True, max_concurrent=5, timeout=120
        )
        assert "max_concurrent: 5" in yaml_content
        assert "timeout: 120" in yaml_content

    def test_multi_agent_init_code_is_valid_python(self):
        code = get_multi_agent_init_code("test-agent")
        # Should be parseable Python
        compile(code, "<test>", "exec")

    def test_multi_agent_readme_section_documents_architecture(self):
        section = get_multi_agent_readme_section("test-agent")
        assert "Multi-Agent Architecture" in section
        assert "Coordinator" in section
        assert "Memory Agent" in section
        assert "Spawner" in section
        assert "coordinator.yaml" in section
        assert "memory_agent.yaml" in section
        assert "spawner.yaml" in section


# --- Assembler Multi-Agent Tests ---


class TestAssemblerMultiAgent:
    """Test AgentAssembler multi-agent bundle creation."""

    def test_multi_agent_produces_sub_agent_configs(
        self, goal_definition, execution_plan, sample_skills
    ):
        """multi_agent=True should produce coordinator and memory_agent configs."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            multi_agent=True,
        )
        assert len(bundle.sub_agent_configs) >= 2
        roles = {c.role for c in bundle.sub_agent_configs}
        assert "coordinator" in roles
        assert "memory_agent" in roles

    def test_multi_agent_without_spawning_has_no_spawner(
        self, goal_definition, execution_plan, sample_skills
    ):
        """Without enable_spawning, no spawner config should be present."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            multi_agent=True,
            enable_spawning=False,
        )
        roles = {c.role for c in bundle.sub_agent_configs}
        assert "spawner" not in roles

    def test_enable_spawning_produces_spawner_config(
        self, goal_definition, execution_plan, sample_skills
    ):
        """enable_spawning=True should add spawner to sub_agent_configs."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            multi_agent=True,
            enable_spawning=True,
        )
        roles = {c.role for c in bundle.sub_agent_configs}
        assert "spawner" in roles

        spawner = next(c for c in bundle.sub_agent_configs if c.role == "spawner")
        assert spawner.config["enabled"] is True
        assert "retrieval" in spawner.config["specialist_types"]
        assert spawner.config["max_concurrent"] == 3
        assert spawner.config["timeout"] == 60

    def test_multi_agent_metadata_flags(
        self, goal_definition, execution_plan, sample_skills
    ):
        """Bundle metadata should include multi_agent and enable_spawning flags."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            multi_agent=True,
            enable_spawning=True,
        )
        assert bundle.metadata["multi_agent"] is True
        assert bundle.metadata["enable_spawning"] is True

    def test_no_multi_agent_means_no_sub_agents(
        self, goal_definition, execution_plan, sample_skills
    ):
        """Without multi_agent, sub_agent_configs should be empty."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            multi_agent=False,
        )
        assert bundle.sub_agent_configs == []
        assert "multi_agent" not in bundle.metadata

    def test_multi_agent_increases_max_turns(
        self, goal_definition, execution_plan, sample_skills
    ):
        """Multi-agent should get 1.5x more turns for coordination overhead."""
        assembler = AgentAssembler()

        bundle_single = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            bundle_name="single-agent-aaa",
            multi_agent=False,
        )
        bundle_multi = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            bundle_name="multi-agent-aaa",
            multi_agent=True,
        )

        single_turns = bundle_single.auto_mode_config["max_turns"]
        multi_turns = bundle_multi.auto_mode_config["max_turns"]
        assert multi_turns > single_turns
        assert multi_turns == int(single_turns * 1.5)


# --- Packager Multi-Agent Tests ---


class TestPackagerMultiAgent:
    """Test that packager creates correct directory structure for multi-agent bundles."""

    def test_sub_agents_directory_created(
        self, goal_definition, execution_plan, sample_skills, temp_output_dir
    ):
        """Multi-agent bundle should have sub_agents/ directory."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            bundle_name="test-multi-agent",
            multi_agent=True,
        )
        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        assert (agent_dir / "sub_agents").is_dir()

    def test_coordinator_yaml_written(
        self, goal_definition, execution_plan, sample_skills, temp_output_dir
    ):
        """coordinator.yaml should exist and be valid."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            bundle_name="test-coord-agent",
            multi_agent=True,
        )
        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        coord_path = agent_dir / "sub_agents" / "coordinator.yaml"
        assert coord_path.exists()
        content = coord_path.read_text()
        assert "role: task_classifier" in content
        assert "entity_centric" in content

    def test_memory_agent_yaml_written(
        self, goal_definition, execution_plan, sample_skills, temp_output_dir
    ):
        """memory_agent.yaml should exist and be valid."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            bundle_name="test-mem-agent",
            multi_agent=True,
        )
        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        mem_path = agent_dir / "sub_agents" / "memory_agent.yaml"
        assert mem_path.exists()
        content = mem_path.read_text()
        assert "role: retrieval_specialist" in content
        assert "max_facts: 300" in content

    def test_spawner_yaml_written_with_spawning(
        self, goal_definition, execution_plan, sample_skills, temp_output_dir
    ):
        """spawner.yaml should exist and be enabled when spawning is on."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            bundle_name="test-spawn-agent",
            multi_agent=True,
            enable_spawning=True,
        )
        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        spawner_path = agent_dir / "sub_agents" / "spawner.yaml"
        assert spawner_path.exists()
        content = spawner_path.read_text()
        assert "enabled: true" in content

    def test_spawner_yaml_disabled_without_spawning(
        self, goal_definition, execution_plan, sample_skills, temp_output_dir
    ):
        """spawner.yaml should be written but disabled without --enable-spawning."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            bundle_name="test-no-spawn-agt",
            multi_agent=True,
            enable_spawning=False,
        )
        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        spawner_path = agent_dir / "sub_agents" / "spawner.yaml"
        assert spawner_path.exists()
        content = spawner_path.read_text()
        assert "enabled: false" in content

    def test_sub_agents_init_py_written(
        self, goal_definition, execution_plan, sample_skills, temp_output_dir
    ):
        """sub_agents/__init__.py should be written for import support."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            bundle_name="test-init-agent",
            multi_agent=True,
        )
        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        init_path = agent_dir / "sub_agents" / "__init__.py"
        assert init_path.exists()
        content = init_path.read_text()
        assert "load_sub_agent_configs" in content

    def test_agent_config_includes_sub_agents(
        self, goal_definition, execution_plan, sample_skills, temp_output_dir
    ):
        """agent_config.json should list sub-agents."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            bundle_name="test-cfg-agent",
            multi_agent=True,
            enable_spawning=True,
        )
        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        config = json.loads((agent_dir / "agent_config.json").read_text())
        assert "sub_agents" in config
        roles = {sa["role"] for sa in config["sub_agents"]}
        assert "coordinator" in roles
        assert "memory_agent" in roles
        assert "spawner" in roles

    def test_readme_includes_multi_agent_section(
        self, goal_definition, execution_plan, sample_skills, temp_output_dir
    ):
        """README should document multi-agent architecture."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            bundle_name="test-readme-agent",
            multi_agent=True,
        )
        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        readme = (agent_dir / "README.md").read_text()
        assert "Multi-Agent Architecture" in readme
        assert "Coordinator" in readme

    def test_requirements_includes_pyyaml(
        self, goal_definition, execution_plan, sample_skills, temp_output_dir
    ):
        """requirements.txt should include pyyaml for multi-agent."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            bundle_name="test-reqs-agent",
            multi_agent=True,
        )
        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        requirements = (agent_dir / "requirements.txt").read_text()
        assert "pyyaml" in requirements

    def test_no_sub_agents_dir_without_multi_agent(
        self, goal_definition, execution_plan, sample_skills, temp_output_dir
    ):
        """Without multi-agent, sub_agents/ should not exist."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            bundle_name="test-single-agent",
        )
        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        assert not (agent_dir / "sub_agents").exists()


# --- Generated Agent Import Verification ---


class TestGeneratedAgentImports:
    """Verify that generated agents import from framework, not hardcode behavior."""

    def test_main_py_imports_from_amplihack(
        self, goal_definition, execution_plan, sample_skills, temp_output_dir
    ):
        """Generated main.py should import from amplihack.launcher.auto_mode."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            bundle_name="test-import-agent",
        )
        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        main_content = (agent_dir / "main.py").read_text()
        assert "from amplihack.launcher.auto_mode import AutoMode" in main_content

    def test_no_hardcoded_behavior_overrides(
        self, goal_definition, execution_plan, sample_skills, temp_output_dir
    ):
        """Generated agent should not contain hardcoded behavior overrides."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            bundle_name="test-nohard-agent",
            multi_agent=True,
        )
        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        main_content = (agent_dir / "main.py").read_text()
        # Should not contain hardcoded retrieval strategies, grading, etc.
        assert "def grade(" not in main_content
        assert "def retrieve(" not in main_content
        assert "class Strategy" not in main_content

    def test_all_config_externalized(
        self, goal_definition, execution_plan, sample_skills, temp_output_dir
    ):
        """All configuration should be in YAML/JSON files, not in code."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            bundle_name="test-extern-agent",
            multi_agent=True,
            enable_spawning=True,
        )
        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        # Config files should exist
        assert (agent_dir / "agent_config.json").exists()
        assert (agent_dir / "sub_agents" / "coordinator.yaml").exists()
        assert (agent_dir / "sub_agents" / "memory_agent.yaml").exists()
        assert (agent_dir / "sub_agents" / "spawner.yaml").exists()

        # Config should be valid JSON/YAML
        config = json.loads((agent_dir / "agent_config.json").read_text())
        assert "auto_mode_config" in config


# --- Full End-to-End Multi-Agent Test ---


class TestMultiAgentEndToEnd:
    """Full pipeline test for multi-agent bundle generation."""

    def test_full_pipeline_multi_agent_with_spawning(
        self, goal_definition, execution_plan, sample_skills, temp_output_dir
    ):
        """Complete pipeline: assemble + package with multi-agent + spawning."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            bundle_name="full-e2e-agent",
            multi_agent=True,
            enable_spawning=True,
            enable_memory=True,
        )

        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        # Standard files
        assert (agent_dir / "main.py").exists()
        assert (agent_dir / "README.md").exists()
        assert (agent_dir / "prompt.md").exists()
        assert (agent_dir / "agent_config.json").exists()
        assert (agent_dir / "requirements.txt").exists()

        # Multi-agent files
        assert (agent_dir / "sub_agents").is_dir()
        assert (agent_dir / "sub_agents" / "coordinator.yaml").exists()
        assert (agent_dir / "sub_agents" / "memory_agent.yaml").exists()
        assert (agent_dir / "sub_agents" / "spawner.yaml").exists()
        assert (agent_dir / "sub_agents" / "__init__.py").exists()

        # Memory files
        assert (agent_dir / "memory_config.yaml").exists()
        assert (agent_dir / "memory").is_dir()

        # Verify README has all sections
        readme = (agent_dir / "README.md").read_text()
        assert "Multi-Agent Architecture" in readme
        assert "Memory & Learning" in readme

        # Verify requirements
        reqs = (agent_dir / "requirements.txt").read_text()
        assert "amplihack" in reqs
        assert "pyyaml" in reqs
        assert "amplihack-memory-lib" in reqs
