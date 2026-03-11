"""Regression tests for the qa-team skill rename and alias layout."""

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL_MIRRORS = [
    REPO_ROOT / ".claude" / "skills",
    REPO_ROOT / "amplifier-bundle" / "skills",
    REPO_ROOT / "docs" / "claude" / "skills",
]


def load_frontmatter(path: Path) -> dict:
    """Load YAML frontmatter from a markdown file."""
    content = path.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    assert len(parts) >= 3, f"{path} is missing closed YAML frontmatter"
    metadata = yaml.safe_load(parts[1])
    assert isinstance(metadata, dict), f"{path} frontmatter should parse to a mapping"
    return metadata


def test_known_skills_registry_includes_qa_team():
    """The known-skills registry should expose qa-team as a first-class skill."""
    known_skills = (REPO_ROOT / "src" / "amplihack" / "known_skills.py").read_text(
        encoding="utf-8"
    )
    assert '"qa-team"' in known_skills
    assert '"outside-in-testing"' in known_skills


def test_bundle_registers_both_primary_and_alias():
    """The bundle index should advertise both the new primary skill and alias."""
    bundle = (REPO_ROOT / "amplifier-bundle" / "bundle.md").read_text(encoding="utf-8")
    assert "outside-in-testing: { path: skills/outside-in-testing/SKILL.md }" in bundle
    assert "qa-team: { path: skills/qa-team/SKILL.md }" in bundle


def test_qa_team_primary_skill_is_present_in_all_mirrors():
    """All shipped skill mirrors should contain qa-team with the new frontmatter name."""
    for skills_dir in SKILL_MIRRORS:
        skill_file = skills_dir / "qa-team" / "SKILL.md"
        metadata = load_frontmatter(skill_file)
        content = skill_file.read_text(encoding="utf-8")

        assert metadata["name"] == "qa-team"
        assert "--observable" in content
        assert "--ssh-target" in content
        assert "--shadow-mode" in content
        assert "outside-in-testing" in content


def test_outside_in_testing_alias_points_to_qa_team_in_all_mirrors():
    """The legacy skill name should remain available as an alias that redirects to qa-team."""
    for skills_dir in SKILL_MIRRORS:
        alias_dir = skills_dir / "outside-in-testing"
        alias_skill = alias_dir / "SKILL.md"
        metadata = load_frontmatter(alias_skill)
        content = alias_skill.read_text(encoding="utf-8")

        assert metadata["name"] == "outside-in-testing"
        assert "alias for `qa-team`" in content

        for name in ["README.md", "examples", "scripts", "tests"]:
            alias_path = alias_dir / name
            assert alias_path.is_symlink(), f"{alias_path} should be a symlink"


def test_workflow_and_profile_prefer_qa_team_name():
    """Core workflow surfaces should now recommend qa-team for new invocations."""
    default_workflow = (
        REPO_ROOT / "amplifier-bundle" / "recipes" / "default-workflow.yaml"
    ).read_text(encoding="utf-8")
    coding_profile = (REPO_ROOT / ".claude" / "profiles" / "coding.yaml").read_text(
        encoding="utf-8"
    )
    generator_skill = (
        REPO_ROOT / ".claude" / "skills" / "e2e-outside-in-test-generator" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert 'Skill(skill="qa-team")' in default_workflow
    assert "`outside-in-testing` remains an alias" in default_workflow
    assert '- "qa-team"' in coding_profile
    assert "qa-team (primary methodology validation" in generator_skill
