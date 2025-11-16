"""Integration tests for goal agent generator."""

import tempfile
import uuid
from pathlib import Path

import pytest

from ..prompt_analyzer import PromptAnalyzer
from ..objective_planner import ObjectivePlanner
from ..skill_synthesizer import SkillSynthesizer
from ..agent_assembler import AgentAssembler
from ..packager import GoalAgentPackager


class TestIntegration:
    """Integration tests for complete pipeline."""

    @pytest.fixture
    def sample_prompt(self):
        """Create sample prompt file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""# Goal: Automate Security Analysis

Create an automated security scanning system that:
- Scans codebase for vulnerabilities
- Generates detailed reports
- Sends alerts for critical issues

## Constraints
- Must complete within 30 minutes
- Cannot modify existing code

## Success Criteria
- All vulnerabilities detected
- Report generated in JSON format
- Team notified of critical issues
""")
            return Path(f.name)

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def temp_skills_dir(self):
        """Create temporary skills directory with sample skills."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            skills_dir.mkdir()

            # Create sample skill
            (skills_dir / "security-analyzer.md").write_text("""# Security Analyzer

Analyzes code for security vulnerabilities.

## Capabilities
- Vulnerability scanning
- Security auditing
- Threat detection
""")

            yield skills_dir

    def test_end_to_end_pipeline(self, sample_prompt, temp_output_dir, temp_skills_dir):
        """Test complete pipeline from prompt to packaged agent."""
        # Stage 1: Analyze prompt
        analyzer = PromptAnalyzer()
        goal_definition = analyzer.analyze(sample_prompt)

        assert goal_definition.goal
        assert goal_definition.domain == "security-analysis"
        assert len(goal_definition.constraints) > 0
        assert len(goal_definition.success_criteria) > 0

        # Stage 2: Create execution plan
        planner = ObjectivePlanner()
        execution_plan = planner.generate_plan(goal_definition)

        assert execution_plan.phase_count >= 3
        assert len(execution_plan.required_skills) > 0
        assert execution_plan.total_estimated_duration

        # Stage 2b: Synthesize skills
        synthesizer = SkillSynthesizer(skills_directory=temp_skills_dir)
        skills = synthesizer.synthesize_skills(execution_plan)

        assert len(skills) > 0
        assert all(skill.content for skill in skills)

        # Stage 3: Assemble bundle
        assembler = AgentAssembler()
        bundle = assembler.assemble(goal_definition, execution_plan, skills)

        assert bundle.is_complete
        assert bundle.name
        assert bundle.auto_mode_config
        assert bundle.metadata

        # Stage 4: Package agent
        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        assert agent_dir.exists()
        assert (agent_dir / "main.py").exists()
        assert (agent_dir / "README.md").exists()
        assert (agent_dir / "prompt.md").exists()
        assert (agent_dir / ".claude" / "agents").exists()

    def test_pipeline_with_custom_name(self, sample_prompt, temp_output_dir, temp_skills_dir):
        """Test pipeline with custom bundle name."""
        analyzer = PromptAnalyzer()
        goal_definition = analyzer.analyze(sample_prompt)

        planner = ObjectivePlanner()
        execution_plan = planner.generate_plan(goal_definition)

        synthesizer = SkillSynthesizer(skills_directory=temp_skills_dir)
        skills = synthesizer.synthesize_skills(execution_plan)

        assembler = AgentAssembler()
        bundle = assembler.assemble(
            goal_definition, execution_plan, skills, bundle_name="custom-security-agent"
        )

        assert bundle.name == "custom-security-agent"

        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        assert agent_dir.name == "custom-security-agent"

    def test_packaged_agent_structure(self, sample_prompt, temp_output_dir, temp_skills_dir):
        """Test that packaged agent has correct structure."""
        # Complete pipeline
        analyzer = PromptAnalyzer()
        goal_definition = analyzer.analyze(sample_prompt)

        planner = ObjectivePlanner()
        execution_plan = planner.generate_plan(goal_definition)

        synthesizer = SkillSynthesizer(skills_directory=temp_skills_dir)
        skills = synthesizer.synthesize_skills(execution_plan)

        assembler = AgentAssembler()
        bundle = assembler.assemble(goal_definition, execution_plan, skills)

        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        # Verify structure
        assert (agent_dir / "main.py").is_file()
        assert (agent_dir / "README.md").is_file()
        assert (agent_dir / "prompt.md").is_file()
        assert (agent_dir / "agent_config.json").is_file()
        assert (agent_dir / ".claude").is_dir()
        assert (agent_dir / ".claude" / "agents").is_dir()
        assert (agent_dir / ".claude" / "context").is_dir()
        assert (agent_dir / ".claude" / "context" / "goal.json").is_file()
        assert (agent_dir / ".claude" / "context" / "execution_plan.json").is_file()
        assert (agent_dir / "logs").is_dir()

        # Verify main.py is executable
        assert (agent_dir / "main.py").stat().st_mode & 0o111

    def test_packaged_agent_content(self, sample_prompt, temp_output_dir, temp_skills_dir):
        """Test that packaged agent contains expected content."""
        analyzer = PromptAnalyzer()
        goal_definition = analyzer.analyze(sample_prompt)

        planner = ObjectivePlanner()
        execution_plan = planner.generate_plan(goal_definition)

        synthesizer = SkillSynthesizer(skills_directory=temp_skills_dir)
        skills = synthesizer.synthesize_skills(execution_plan)

        assembler = AgentAssembler()
        bundle = assembler.assemble(goal_definition, execution_plan, skills)

        packager = GoalAgentPackager(output_dir=temp_output_dir)
        agent_dir = packager.package(bundle)

        # Check README content
        readme = (agent_dir / "README.md").read_text()
        assert bundle.name in readme
        assert goal_definition.goal in readme
        assert str(execution_plan.phase_count) in readme

        # Check main.py content
        main_py = (agent_dir / "main.py").read_text()
        assert "AutoMode" in main_py
        assert bundle.name in main_py

        # Check config
        import json

        config = json.loads((agent_dir / "agent_config.json").read_text())
        assert config["name"] == bundle.name
        assert "auto_mode_config" in config

    @pytest.mark.parametrize(
        "domain",
        ["data-processing", "security-analysis", "automation", "testing", "deployment"],
    )
    def test_pipeline_for_various_domains(
        self, domain, temp_output_dir, temp_skills_dir, sample_prompt
    ):
        """Test pipeline works for different domains."""
        # Create domain-specific prompt
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write(f"# Goal: Test {domain}\n\nDomain-specific task for {domain}")
            domain_prompt = Path(f.name)

        try:
            analyzer = PromptAnalyzer()
            goal_definition = analyzer.analyze(domain_prompt)

            # Force domain for testing
            goal_definition.domain = domain

            planner = ObjectivePlanner()
            execution_plan = planner.generate_plan(goal_definition)

            synthesizer = SkillSynthesizer(skills_directory=temp_skills_dir)
            skills = synthesizer.synthesize_skills(execution_plan)

            assembler = AgentAssembler()
            bundle = assembler.assemble(goal_definition, execution_plan, skills)

            packager = GoalAgentPackager(output_dir=temp_output_dir)
            agent_dir = packager.package(bundle)

            assert agent_dir.exists()
            assert bundle.is_complete
        finally:
            domain_prompt.unlink()
