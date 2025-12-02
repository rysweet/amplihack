"""
Tests for outside-in-testing skill example YAML files.

Validates that all example YAML files are:
- Valid YAML syntax
- Have required fields
- Follow naming conventions
- Are properly categorized by level
- Have consistent structure
"""

from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

# Skill directory paths
SKILL_DIR = Path(__file__).parent.parent
EXAMPLES_DIR = SKILL_DIR / "examples"


def get_all_example_files() -> List[Path]:
    """Get all YAML example files."""
    return list(EXAMPLES_DIR.rglob("*.yaml"))


def load_yaml_file(file_path: Path) -> Dict[str, Any]:
    """Load and parse a YAML file."""
    with open(file_path) as f:
        return yaml.safe_load(f)


class TestExampleFiles:
    """Test suite for example YAML files."""

    @pytest.fixture
    def example_files(self) -> List[Path]:
        """Fixture providing all example files."""
        return get_all_example_files()

    def test_all_examples_exist(self, example_files):
        """Verify all expected example files exist."""
        expected_count = 15  # 3 CLI + 3 TUI + 3 Web + 4 Electron + 2 Custom
        assert len(example_files) == expected_count, (
            f"Expected {expected_count} example files, found {len(example_files)}"
        )

    def test_example_files_are_valid_yaml(self, example_files):
        """Verify all examples are valid YAML."""
        for file_path in example_files:
            try:
                data = load_yaml_file(file_path)
                assert data is not None, f"{file_path.name} is empty"
            except yaml.YAMLError as e:
                pytest.fail(f"{file_path.name} has invalid YAML syntax: {e}")

    def test_examples_have_required_fields(self, example_files):
        """Verify all examples have required scenario fields."""
        required_fields = ["name", "description", "type", "steps"]

        for file_path in example_files:
            data = load_yaml_file(file_path)
            scenario = data.get("scenario", {})

            for field in required_fields:
                assert field in scenario, f"{file_path.name} missing required field: {field}"

    def test_examples_have_valid_type(self, example_files):
        """Verify all examples have valid application type."""
        valid_types = ["cli", "tui", "web", "electron"]

        for file_path in example_files:
            data = load_yaml_file(file_path)
            scenario_type = data.get("scenario", {}).get("type")

            assert scenario_type in valid_types, (
                f"{file_path.name} has invalid type: {scenario_type}"
            )

    def test_examples_have_level_indicator(self, example_files):
        """Verify all examples specify their complexity level."""
        for file_path in example_files:
            data = load_yaml_file(file_path)
            scenario = data.get("scenario", {})

            assert "level" in scenario, f"{file_path.name} missing level indicator"

            level = scenario["level"]
            assert level in [1, 2, 3], f"{file_path.name} has invalid level: {level}"

    def test_examples_have_tags(self, example_files):
        """Verify all examples have tags."""
        for file_path in example_files:
            data = load_yaml_file(file_path)
            scenario = data.get("scenario", {})

            assert "tags" in scenario, f"{file_path.name} missing tags"

            tags = scenario["tags"]
            assert isinstance(tags, list), f"{file_path.name} tags should be a list"
            assert len(tags) > 0, f"{file_path.name} should have at least one tag"

    def test_examples_have_steps(self, example_files):
        """Verify all examples have at least one step."""
        for file_path in example_files:
            data = load_yaml_file(file_path)
            steps = data.get("scenario", {}).get("steps", [])

            assert len(steps) > 0, f"{file_path.name} has no steps"

    def test_all_steps_have_action(self, example_files):
        """Verify all steps have an action field."""
        for file_path in example_files:
            data = load_yaml_file(file_path)
            steps = data.get("scenario", {}).get("steps", [])

            for idx, step in enumerate(steps):
                assert "action" in step, f"{file_path.name} step {idx} missing action field"

    def test_examples_have_description(self, example_files):
        """Verify all examples have non-empty description."""
        for file_path in example_files:
            data = load_yaml_file(file_path)
            description = data.get("scenario", {}).get("description", "")

            assert description.strip(), f"{file_path.name} has empty description"

    def test_cli_examples_in_correct_directory(self):
        """Verify CLI examples are in cli directory."""
        cli_files = list((EXAMPLES_DIR / "cli").glob("*.yaml"))
        assert len(cli_files) == 3, f"Expected 3 CLI examples, found {len(cli_files)}"

        for file_path in cli_files:
            data = load_yaml_file(file_path)
            assert data["scenario"]["type"] == "cli", (
                f"{file_path.name} in cli/ but type is not 'cli'"
            )

    def test_tui_examples_in_correct_directory(self):
        """Verify TUI examples are in tui directory."""
        tui_files = list((EXAMPLES_DIR / "tui").glob("*.yaml"))
        assert len(tui_files) == 3, f"Expected 3 TUI examples, found {len(tui_files)}"

        for file_path in tui_files:
            data = load_yaml_file(file_path)
            assert data["scenario"]["type"] == "tui", (
                f"{file_path.name} in tui/ but type is not 'tui'"
            )

    def test_web_examples_in_correct_directory(self):
        """Verify Web examples are in web directory."""
        web_files = list((EXAMPLES_DIR / "web").glob("*.yaml"))
        assert len(web_files) == 3, f"Expected 3 Web examples, found {len(web_files)}"

        for file_path in web_files:
            data = load_yaml_file(file_path)
            assert data["scenario"]["type"] == "web", (
                f"{file_path.name} in web/ but type is not 'web'"
            )

    def test_electron_examples_in_correct_directory(self):
        """Verify Electron examples are in electron directory."""
        electron_files = list((EXAMPLES_DIR / "electron").glob("*.yaml"))
        assert len(electron_files) == 4, (
            f"Expected 4 Electron examples, found {len(electron_files)}"
        )

        for file_path in electron_files:
            data = load_yaml_file(file_path)
            assert data["scenario"]["type"] == "electron", (
                f"{file_path.name} in electron/ but type is not 'electron'"
            )

    def test_custom_agent_examples_exist(self):
        """Verify custom agent examples exist."""
        custom_files = list((EXAMPLES_DIR / "custom-agents").glob("*.yaml"))
        assert len(custom_files) == 2, (
            f"Expected 2 custom agent examples, found {len(custom_files)}"
        )

    def test_level_distribution(self, example_files):
        """Verify examples have good level distribution."""
        levels = []
        for file_path in example_files:
            data = load_yaml_file(file_path)
            levels.append(data["scenario"]["level"])

        level_1_count = levels.count(1)
        level_2_count = levels.count(2)
        level_3_count = levels.count(3)

        # Should have examples at each level
        assert level_1_count >= 4, "Should have at least 4 Level 1 examples"
        assert level_2_count >= 6, "Should have at least 6 Level 2 examples"
        assert level_3_count >= 4, "Should have at least 4 Level 3 examples"

    def test_naming_convention(self, example_files):
        """Verify files follow naming convention (lowercase with hyphens)."""
        for file_path in example_files:
            filename = file_path.stem  # Without .yaml extension

            # Should be lowercase with hyphens
            assert filename == filename.lower(), f"{file_path.name} should be lowercase"

            # Should not have underscores
            assert "_" not in filename or "custom" in filename, (
                f"{file_path.name} should use hyphens, not underscores"
            )

    def test_no_placeholder_content(self, example_files):
        """Verify examples don't contain placeholder content."""
        placeholders = ["TODO", "FIXME", "XXX", "PLACEHOLDER", "Coming soon"]

        for file_path in example_files:
            content = file_path.read_text()

            for placeholder in placeholders:
                assert placeholder not in content, (
                    f"{file_path.name} contains placeholder: {placeholder}"
                )


class TestSkillStructure:
    """Test suite for overall skill structure."""

    def test_skill_md_exists(self):
        """Verify SKILL.md exists."""
        skill_file = SKILL_DIR / "SKILL.md"
        assert skill_file.exists(), "SKILL.md not found"

    def test_readme_exists(self):
        """Verify README.md exists."""
        readme_file = SKILL_DIR / "README.md"
        assert readme_file.exists(), "README.md not found"

    def test_examples_directory_exists(self):
        """Verify examples directory exists."""
        assert EXAMPLES_DIR.exists(), "examples/ directory not found"

    def test_scripts_directory_exists(self):
        """Verify scripts directory exists."""
        scripts_dir = SKILL_DIR / "scripts"
        assert scripts_dir.exists(), "scripts/ directory not found"

    def test_check_freshness_script_exists(self):
        """Verify check-freshness.py script exists."""
        script_file = SKILL_DIR / "scripts" / "check-freshness.py"
        assert script_file.exists(), "check-freshness.py not found"

    def test_tests_directory_exists(self):
        """Verify tests directory exists."""
        tests_dir = SKILL_DIR / "tests"
        assert tests_dir.exists(), "tests/ directory not found"

    def test_skill_has_yaml_frontmatter(self):
        """Verify SKILL.md has valid YAML frontmatter."""
        skill_file = SKILL_DIR / "SKILL.md"
        content = skill_file.read_text()

        # Should start with ---
        assert content.startswith("---"), "SKILL.md should start with YAML frontmatter"

        # Extract frontmatter
        parts = content.split("---", 2)
        assert len(parts) >= 3, "SKILL.md frontmatter not properly closed"

        frontmatter = parts[1]

        # Should be valid YAML
        try:
            metadata = yaml.safe_load(frontmatter)
            assert metadata is not None, "Frontmatter is empty"
        except yaml.YAMLError as e:
            pytest.fail(f"SKILL.md frontmatter has invalid YAML: {e}")

        # Check required frontmatter fields
        assert "name" in metadata, "Frontmatter missing 'name'"
        assert "description" in metadata, "Frontmatter missing 'description'"
        assert "version" in metadata, "Frontmatter missing 'version'"
        assert "embedded_framework_version" in metadata, (
            "Frontmatter missing 'embedded_framework_version'"
        )


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])
