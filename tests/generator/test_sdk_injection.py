"""Tests for SDK-aware skill synthesis and tool injection.

Verifies that the generator correctly maps SDK-native tools for each
supported SDK target (claude, copilot, microsoft, mini).
"""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

import pytest

from src.amplihack.goal_agent_generator.agent_assembler import AgentAssembler
from src.amplihack.goal_agent_generator.models import (
    ExecutionPlan,
    GoalDefinition,
    PlanPhase,
    SDKToolConfig,
    SkillDefinition,
)
from src.amplihack.goal_agent_generator.packager import GoalAgentPackager
from src.amplihack.goal_agent_generator.skill_synthesizer import (
    SDK_NATIVE_TOOLS,
    SkillSynthesizer,
)


# --- Fixtures ---


@pytest.fixture
def temp_skills_dir():
    """Create temporary skills directory with sample skills."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir) / "skills"
        skills_dir.mkdir()
        (skills_dir / "analyzer.md").write_text(
            "# Analyzer\nAnalyzes code for patterns.\n## Capabilities\n- Analyze code\n- Review quality"
        )
        yield skills_dir


@pytest.fixture
def synthesizer(temp_skills_dir):
    """SkillSynthesizer with temp directory."""
    return SkillSynthesizer(skills_directory=temp_skills_dir)


@pytest.fixture
def execution_plan():
    """Execution plan requiring file and search capabilities."""
    phases = [
        PlanPhase(
            name="Read Source",
            description="Read source files",
            required_capabilities=["read", "file"],
            estimated_duration="5 minutes",
        ),
        PlanPhase(
            name="Search Patterns",
            description="Search for code patterns",
            required_capabilities=["search", "pattern"],
            estimated_duration="10 minutes",
        ),
        PlanPhase(
            name="Execute Commands",
            description="Run shell commands",
            required_capabilities=["execute", "shell"],
            estimated_duration="5 minutes",
        ),
    ]
    return ExecutionPlan(
        goal_id=uuid.uuid4(),
        phases=phases,
        total_estimated_duration="20 minutes",
        required_skills=["analyzer"],
    )


@pytest.fixture
def goal_definition():
    """Minimal goal definition for testing."""
    return GoalDefinition(
        raw_prompt="Analyze codebase for patterns",
        goal="Analyze codebase for patterns",
        domain="code-analysis",
        constraints=["Must complete in 30 minutes"],
        success_criteria=["All patterns identified"],
    )


@pytest.fixture
def sample_skills(temp_skills_dir):
    """Pre-built skill list."""
    return [
        SkillDefinition(
            name="analyzer",
            source_path=temp_skills_dir / "analyzer.md",
            capabilities=["analyze", "review"],
            description="Code analyzer",
            content="# Analyzer\nAnalyzes code.",
            match_score=0.8,
        )
    ]


# --- SDK Tool Mapping Tests ---


class TestSDKNativeToolsMapping:
    """Test that SDK_NATIVE_TOOLS has correct structure for each SDK."""

    def test_claude_sdk_has_bash_tool(self):
        """Claude SDK should include bash for shell commands."""
        assert "bash" in SDK_NATIVE_TOOLS["claude"]
        assert SDK_NATIVE_TOOLS["claude"]["bash"]["category"] == "system"

    def test_claude_sdk_has_file_tools(self):
        """Claude SDK should include read_file, write_file, edit_file, glob."""
        claude_tools = SDK_NATIVE_TOOLS["claude"]
        for tool_name in ("read_file", "write_file", "edit_file", "glob"):
            assert tool_name in claude_tools
            assert claude_tools[tool_name]["category"] == "file_ops"

    def test_claude_sdk_has_grep(self):
        """Claude SDK should include grep for search."""
        assert "grep" in SDK_NATIVE_TOOLS["claude"]
        assert SDK_NATIVE_TOOLS["claude"]["grep"]["category"] == "search"

    def test_copilot_sdk_has_file_system_and_git(self):
        """Copilot SDK should include file_system and git tools."""
        copilot_tools = SDK_NATIVE_TOOLS["copilot"]
        assert "file_system" in copilot_tools
        assert copilot_tools["file_system"]["category"] == "file_ops"
        assert "git" in copilot_tools
        assert copilot_tools["git"]["category"] == "vcs"

    def test_copilot_sdk_has_web_requests(self):
        """Copilot SDK should include web_requests."""
        assert "web_requests" in SDK_NATIVE_TOOLS["copilot"]
        assert SDK_NATIVE_TOOLS["copilot"]["web_requests"]["category"] == "network"

    def test_microsoft_sdk_has_ai_function(self):
        """Microsoft SDK should include ai_function tool."""
        assert "ai_function" in SDK_NATIVE_TOOLS["microsoft"]
        assert SDK_NATIVE_TOOLS["microsoft"]["ai_function"]["category"] == "ai"

    def test_mini_sdk_has_no_native_tools(self):
        """Mini SDK should have no native tools."""
        assert SDK_NATIVE_TOOLS["mini"] == {}


# --- get_sdk_tools Tests ---


class TestGetSDKTools:
    """Test SkillSynthesizer.get_sdk_tools() method."""

    def test_claude_returns_all_tools_when_no_capabilities(self, synthesizer):
        """Without capabilities filter, return all Claude tools."""
        tools = synthesizer.get_sdk_tools("claude")
        assert len(tools) == 6  # bash, read_file, write_file, edit_file, glob, grep
        tool_names = {t.name for t in tools}
        assert "bash" in tool_names
        assert "read_file" in tool_names
        assert "grep" in tool_names

    def test_claude_file_capabilities_return_file_tools(self, synthesizer):
        """File-related capabilities should match file_ops tools."""
        tools = synthesizer.get_sdk_tools("claude", required_capabilities=["read", "file"])
        tool_names = {t.name for t in tools}
        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "edit_file" in tool_names
        assert "glob" in tool_names
        # bash should NOT be included (system category)
        assert "bash" not in tool_names

    def test_claude_search_capabilities_return_grep(self, synthesizer):
        """Search capabilities should match search tools."""
        tools = synthesizer.get_sdk_tools("claude", required_capabilities=["search"])
        tool_names = {t.name for t in tools}
        assert "grep" in tool_names

    def test_copilot_returns_all_tools_when_no_capabilities(self, synthesizer):
        """Without capabilities filter, return all Copilot tools."""
        tools = synthesizer.get_sdk_tools("copilot")
        assert len(tools) == 3
        tool_names = {t.name for t in tools}
        assert "file_system" in tool_names
        assert "git" in tool_names
        assert "web_requests" in tool_names

    def test_copilot_file_capabilities_return_file_system(self, synthesizer):
        """File capabilities should match Copilot file_system tool."""
        tools = synthesizer.get_sdk_tools("copilot", required_capabilities=["file"])
        tool_names = {t.name for t in tools}
        assert "file_system" in tool_names

    def test_microsoft_ai_capabilities_return_ai_function(self, synthesizer):
        """AI capabilities should match Microsoft ai_function tool."""
        tools = synthesizer.get_sdk_tools("microsoft", required_capabilities=["ai", "generate"])
        assert len(tools) == 1
        assert tools[0].name == "ai_function"
        assert tools[0].category == "ai"

    def test_mini_returns_empty(self, synthesizer):
        """Mini SDK should return no tools."""
        tools = synthesizer.get_sdk_tools("mini")
        assert tools == []

    def test_unknown_sdk_returns_empty(self, synthesizer):
        """Unknown SDK should return no tools."""
        tools = synthesizer.get_sdk_tools("nonexistent")
        assert tools == []

    def test_sdk_tools_are_sdk_tool_config_instances(self, synthesizer):
        """Returned tools should be SDKToolConfig dataclass instances."""
        tools = synthesizer.get_sdk_tools("claude")
        for tool in tools:
            assert isinstance(tool, SDKToolConfig)
            assert tool.name
            assert tool.description
            assert tool.category


# --- synthesize_with_sdk_tools Tests ---


class TestSynthesizeWithSDKTools:
    """Test combined skill + SDK tool synthesis."""

    def test_returns_both_skills_and_sdk_tools(self, synthesizer, execution_plan):
        """Should return both amplihack skills and SDK tool configs."""
        result = synthesizer.synthesize_with_sdk_tools(execution_plan, sdk="claude")
        assert "skills" in result
        assert "sdk_tools" in result
        assert len(result["skills"]) > 0
        assert len(result["sdk_tools"]) > 0

    def test_claude_sdk_tools_match_plan_capabilities(self, synthesizer, execution_plan):
        """SDK tools should match the capabilities required by the plan."""
        result = synthesizer.synthesize_with_sdk_tools(execution_plan, sdk="claude")
        tool_categories = {t.category for t in result["sdk_tools"]}
        # Plan requires: read, file, search, pattern, execute, shell
        assert "file_ops" in tool_categories  # from read/file
        assert "search" in tool_categories  # from search/pattern
        assert "system" in tool_categories  # from execute/shell

    def test_copilot_sdk_tools_match_plan_capabilities(self, synthesizer, execution_plan):
        """Copilot tools should match plan capabilities where possible."""
        result = synthesizer.synthesize_with_sdk_tools(execution_plan, sdk="copilot")
        tool_names = {t.name for t in result["sdk_tools"]}
        assert "file_system" in tool_names  # from file capabilities

    def test_mini_returns_skills_but_no_sdk_tools(self, synthesizer, execution_plan):
        """Mini SDK should return skills but no SDK tools."""
        result = synthesizer.synthesize_with_sdk_tools(execution_plan, sdk="mini")
        assert len(result["skills"]) > 0
        assert result["sdk_tools"] == []


# --- Agent Assembler SDK Integration ---


class TestAssemblerSDKIntegration:
    """Test that AgentAssembler correctly includes SDK tools in bundles."""

    def test_bundle_includes_sdk_tools(self, goal_definition, execution_plan, sample_skills):
        """Bundle should include SDK tools when provided."""
        sdk_tools = [
            SDKToolConfig(name="bash", description="Shell commands", category="system"),
            SDKToolConfig(name="read_file", description="Read files", category="file_ops"),
        ]
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            sdk="claude",
            sdk_tools=sdk_tools,
        )
        assert len(bundle.sdk_tools) == 2
        assert bundle.sdk_tools[0].name == "bash"

    def test_bundle_metadata_contains_sdk_tools(self, goal_definition, execution_plan, sample_skills):
        """Bundle metadata should list SDK tools when provided."""
        sdk_tools = [
            SDKToolConfig(name="file_system", description="File ops", category="file_ops"),
        ]
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            sdk="copilot",
            sdk_tools=sdk_tools,
        )
        assert "sdk_tools" in bundle.metadata
        assert len(bundle.metadata["sdk_tools"]) == 1
        assert bundle.metadata["sdk_tools"][0]["name"] == "file_system"

    def test_bundle_without_sdk_tools_has_empty_list(
        self, goal_definition, execution_plan, sample_skills
    ):
        """Bundle should have empty sdk_tools when none provided."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
        )
        assert bundle.sdk_tools == []


# --- Packager SDK Integration ---


class TestPackagerSDKIntegration:
    """Test that packager writes SDK tools config to generated bundle."""

    @pytest.fixture
    def temp_output_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_sdk_tools_json_written(
        self, goal_definition, execution_plan, sample_skills, temp_output_dir
    ):
        """sdk_tools.json should be written when SDK tools are present."""
        sdk_tools = [
            SDKToolConfig(name="bash", description="Shell commands", category="system"),
        ]
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            bundle_name="test-sdk-agent",
            sdk="claude",
            sdk_tools=sdk_tools,
        )
        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        sdk_tools_path = agent_dir / ".claude" / "context" / "sdk_tools.json"
        assert sdk_tools_path.exists()

        import json

        data = json.loads(sdk_tools_path.read_text())
        assert data["sdk"] == "claude"
        assert len(data["tools"]) == 1
        assert data["tools"][0]["name"] == "bash"

    def test_no_sdk_tools_json_when_empty(
        self, goal_definition, execution_plan, sample_skills, temp_output_dir
    ):
        """sdk_tools.json should NOT be written when no SDK tools."""
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            bundle_name="test-no-sdk-agent",
        )
        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        sdk_tools_path = agent_dir / ".claude" / "context" / "sdk_tools.json"
        assert not sdk_tools_path.exists()

    def test_agent_config_includes_sdk_tools(
        self, goal_definition, execution_plan, sample_skills, temp_output_dir
    ):
        """agent_config.json should include SDK tools."""
        sdk_tools = [
            SDKToolConfig(name="grep", description="Search", category="search"),
        ]
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            sample_skills,
            bundle_name="test-config-agent",
            sdk="claude",
            sdk_tools=sdk_tools,
        )
        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        import json

        config = json.loads((agent_dir / "agent_config.json").read_text())
        assert "sdk_tools" in config
        assert config["sdk_tools"][0]["name"] == "grep"


# --- SDKToolConfig Model Tests ---


class TestSDKToolConfig:
    """Test SDKToolConfig dataclass."""

    def test_to_dict(self):
        """to_dict should return correct dictionary."""
        tool = SDKToolConfig(name="bash", description="Execute commands", category="system")
        d = tool.to_dict()
        assert d == {"name": "bash", "description": "Execute commands", "category": "system"}

    def test_equality(self):
        """Two SDKToolConfigs with same values should be equal."""
        t1 = SDKToolConfig(name="bash", description="Shell", category="system")
        t2 = SDKToolConfig(name="bash", description="Shell", category="system")
        assert t1 == t2


# --- End-to-End SDK Flow ---


class TestSDKEndToEnd:
    """End-to-end test: from plan to packaged agent with SDK tools."""

    @pytest.fixture
    def temp_output_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_claude_sdk_e2e(
        self, synthesizer, goal_definition, execution_plan, temp_output_dir
    ):
        """Full pipeline with Claude SDK should produce agent with bash/read_file tools."""
        # Synthesize
        result = synthesizer.synthesize_with_sdk_tools(execution_plan, sdk="claude")
        skills = result["skills"]
        sdk_tools = result["sdk_tools"]

        # Assemble
        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            skills,
            bundle_name="claude-e2e-agent",
            sdk="claude",
            sdk_tools=sdk_tools,
        )

        # Package
        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        # Verify
        assert agent_dir.exists()
        assert (agent_dir / "main.py").exists()

        import json

        tools_config = json.loads(
            (agent_dir / ".claude" / "context" / "sdk_tools.json").read_text()
        )
        assert tools_config["sdk"] == "claude"
        tool_names = {t["name"] for t in tools_config["tools"]}
        assert "bash" in tool_names or "read_file" in tool_names

    def test_copilot_sdk_e2e(
        self, synthesizer, goal_definition, execution_plan, temp_output_dir
    ):
        """Full pipeline with Copilot SDK should produce agent with file_system/git tools."""
        result = synthesizer.synthesize_with_sdk_tools(execution_plan, sdk="copilot")
        skills = result["skills"]
        sdk_tools = result["sdk_tools"]

        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition,
            execution_plan,
            skills,
            bundle_name="copilot-e2e-agent",
            sdk="copilot",
            sdk_tools=sdk_tools,
        )

        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        assert agent_dir.exists()

        import json

        tools_config = json.loads(
            (agent_dir / ".claude" / "context" / "sdk_tools.json").read_text()
        )
        assert tools_config["sdk"] == "copilot"
        tool_names = {t["name"] for t in tools_config["tools"]}
        assert "file_system" in tool_names
