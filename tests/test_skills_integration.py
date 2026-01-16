"""Test suite for skills integration system.

Tests:
- Skills mapper scans and categorizes correctly
- Skills to agents converter generates valid agents
- Skills registry is complete and accurate
- Skills wrapper routes invocations correctly
- Sync-skills command executes successfully
"""

import json
import tempfile
from pathlib import Path
import pytest

from src.amplihack.adapters.skills_mapper import SkillsMapper, SkillMetadata
from src.amplihack.adapters.skills_to_agents import SkillsToAgentsConverter
from src.amplihack.copilot.skills_wrapper import SkillsWrapper
from src.amplihack.commands.sync_skills import sync_skills_command


class TestSkillsMapper:
    """Test skills mapper functionality."""

    def test_mapper_finds_skills(self):
        """Test that mapper finds all skills."""
        mapper = SkillsMapper()
        skills = mapper.scan_all_skills()

        # Should find 67 skills
        assert len(skills) >= 60, f"Expected at least 60 skills, found {len(skills)}"
        assert all(isinstance(s, SkillMetadata) for s in skills)

    def test_categorization(self):
        """Test that skills are categorized correctly."""
        mapper = SkillsMapper()
        mapper.scan_all_skills()

        # Check some known categorizations
        skill_categories = {s.name: s.category for s in mapper.skills}

        # Analysts
        assert 'cybersecurity-analyst' in skill_categories
        assert skill_categories['cybersecurity-analyst'] == 'analyst'

        # Workflows
        assert 'default-workflow' in skill_categories
        assert skill_categories['default-workflow'] == 'workflow'

        # Tool handlers
        assert 'pdf' in skill_categories
        assert skill_categories['pdf'] == 'tool_handler'

    def test_mapping_strategies(self):
        """Test that mapping strategies are assigned correctly."""
        mapper = SkillsMapper()
        mapper.scan_all_skills()

        strategies = {s.name: s.mapping_strategy for s in mapper.skills}

        # Analysts should be custom agents
        assert strategies.get('economist-analyst') == 'custom_agent'

        # Tool handlers should be MCP tools
        assert strategies.get('pdf') == 'mcp_tool'
        assert strategies.get('docx') == 'mcp_tool'

        # Integrations should be hybrid
        assert strategies.get('azure-devops') == 'hybrid'

    def test_registry_generation(self):
        """Test registry JSON generation."""
        mapper = SkillsMapper()

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / 'registry.json'
            registry = mapper.generate_registry(registry_path)

            # Verify registry structure
            assert 'total_skills' in registry
            assert 'skills' in registry
            assert 'by_category' in registry
            assert 'by_strategy' in registry
            assert 'statistics' in registry

            # Verify statistics
            stats = registry['statistics']
            assert 'custom_agents' in stats
            assert 'mcp_tools' in stats
            assert 'hybrid' in stats

            # Should have generated > 0 agents
            assert stats['custom_agents'] > 0

            # Verify file was written
            assert registry_path.exists()

            # Verify valid JSON
            loaded = json.loads(registry_path.read_text())
            assert loaded == registry


class TestSkillsToAgentsConverter:
    """Test skills to agents converter."""

    def test_converter_initialization(self):
        """Test converter initializes correctly."""
        converter = SkillsToAgentsConverter()
        assert converter.mapper is not None
        assert len(converter.mapper.skills) > 0

    def test_agent_conversion(self):
        """Test converting single skill to agent."""
        converter = SkillsToAgentsConverter()

        # Find a custom_agent skill
        skill = next(
            s for s in converter.mapper.skills
            if s.mapping_strategy == 'custom_agent'
        )

        agent = converter.convert_skill_to_agent(skill)
        assert agent is not None
        assert agent.name == skill.name
        assert agent.model == converter.DEFAULT_MODEL
        assert isinstance(agent.instructions, str)
        assert len(agent.instructions) > 0

    def test_agent_yaml_generation(self):
        """Test agent YAML file generation."""
        converter = SkillsToAgentsConverter()

        # Find cybersecurity-analyst skill
        skill = next(
            (s for s in converter.mapper.skills if s.name == 'code-smell-detector'),
            None
        )

        if skill:
            agent = converter.convert_skill_to_agent(skill)
            yaml_content = agent.to_agent_file()

            # Verify YAML structure
            assert f'name: {skill.name}' in yaml_content
            assert 'description:' in yaml_content
            assert 'model:' in yaml_content
            assert 'tools:' in yaml_content
            assert 'instructions:' in yaml_content

    def test_convert_all_skills(self):
        """Test converting all eligible skills."""
        converter = SkillsToAgentsConverter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            agents = converter.convert_all_skills(
                output_dir=output_dir,
                include_strategies=['custom_agent', 'hybrid']
            )

            # Should convert > 0 skills
            assert len(agents) > 0

            # All agents should be written as files
            for name, agent in agents.items():
                agent_file = output_dir / f'{name}.yaml'
                assert agent_file.exists()

                # Verify valid YAML content
                content = agent_file.read_text()
                assert f'name: {name}' in content

    def test_index_generation(self):
        """Test agents index README generation."""
        converter = SkillsToAgentsConverter()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            agents = converter.convert_all_skills(
                output_dir=output_dir,
                include_strategies=['custom_agent']
            )

            index_content = converter.generate_agents_index(agents)

            # Verify index structure
            assert '# GitHub Copilot CLI Custom Agents' in index_content
            assert '## Available Agents' in index_content
            assert f'**Total agents:** {len(agents)}' in index_content

            # Should list some agents
            assert '- **' in index_content


class TestSkillsWrapper:
    """Test skills invocation wrapper."""

    def test_wrapper_loads_registry(self):
        """Test wrapper loads registry correctly."""
        # First generate a registry
        mapper = SkillsMapper()

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / 'registry.json'
            mapper.generate_registry(registry_path)

            # Create wrapper with this registry
            wrapper = SkillsWrapper(registry_path)

            assert wrapper.registry is not None
            assert 'total_skills' in wrapper.registry

    def test_get_skill_info(self):
        """Test retrieving skill info."""
        mapper = SkillsMapper()

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / 'registry.json'
            mapper.generate_registry(registry_path)

            wrapper = SkillsWrapper(registry_path)

            # Get info for known skill
            info = wrapper.get_skill_info('code-smell-detector')
            assert info is not None
            assert info['name'] == 'code-smell-detector'
            assert 'mapping_strategy' in info
            assert 'category' in info

    def test_list_skills_filtering(self):
        """Test skill listing with filters."""
        mapper = SkillsMapper()

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / 'registry.json'
            mapper.generate_registry(registry_path)

            wrapper = SkillsWrapper(registry_path)

            # List all
            all_skills = wrapper.list_skills()
            assert len(all_skills) > 0

            # Filter by category
            analysts = wrapper.list_skills(category='analyst')
            assert all(s['category'] == 'analyst' for s in analysts)
            assert len(analysts) > 0

            # Filter by strategy
            custom_agents = wrapper.list_skills(strategy='custom_agent')
            assert all(s['mapping_strategy'] == 'custom_agent' for s in custom_agents)
            assert len(custom_agents) > 0

    def test_statistics(self):
        """Test getting statistics."""
        mapper = SkillsMapper()

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / 'registry.json'
            mapper.generate_registry(registry_path)

            wrapper = SkillsWrapper(registry_path)

            stats = wrapper.get_statistics()
            assert 'custom_agents' in stats
            assert 'mcp_tools' in stats
            assert isinstance(stats['custom_agents'], int)


class TestSyncSkillsCommand:
    """Test sync-skills command."""

    def test_sync_skills_completes(self):
        """Test that sync-skills command completes successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / 'agents'
            registry_path = Path(tmpdir) / 'registry.json'

            exit_code = sync_skills_command(
                output_dir=output_dir,
                registry_path=registry_path,
                strategies=['custom_agent', 'hybrid'],
                verbose=False
            )

            # Should succeed
            assert exit_code == 0

            # Should create registry
            assert registry_path.exists()

            # Should create agents directory
            assert output_dir.exists()

            # Should create some agent files
            agent_files = list(output_dir.glob('*.yaml'))
            assert len(agent_files) > 0

            # Should create index
            index_file = output_dir / 'README.md'
            assert index_file.exists()


class TestEndToEnd:
    """End-to-end integration tests."""

    def test_full_workflow(self):
        """Test complete workflow from scan to agent generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Step 1: Scan skills
            mapper = SkillsMapper()
            skills = mapper.scan_all_skills()
            assert len(skills) > 0

            # Step 2: Generate registry
            registry_path = tmpdir / 'registry.json'
            registry = mapper.generate_registry(registry_path)
            assert registry_path.exists()

            # Step 3: Convert to agents
            converter = SkillsToAgentsConverter(mapper)
            agents_dir = tmpdir / 'agents'
            agents = converter.convert_all_skills(
                output_dir=agents_dir,
                include_strategies=['custom_agent']
            )
            assert len(agents) > 0
            assert agents_dir.exists()

            # Step 4: Generate index
            index_content = converter.generate_agents_index(agents)
            index_file = agents_dir / 'README.md'
            index_file.write_text(index_content)
            assert index_file.exists()

            # Step 5: Test wrapper with registry
            wrapper = SkillsWrapper(registry_path)
            all_skills = wrapper.list_skills()
            assert len(all_skills) == len(skills)

            # Verify we can find generated agents
            for agent_name in list(agents.keys())[:5]:  # Check first 5
                agent_file = agents_dir / f'{agent_name}.yaml'
                assert agent_file.exists()

                info = wrapper.get_skill_info(agent_name)
                assert info is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
