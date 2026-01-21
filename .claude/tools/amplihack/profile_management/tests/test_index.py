"""Tests for skill index building."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from ..index import SkillIndexBuilder


@pytest.fixture
def temp_skills_dir(tmp_path):
    """Create temporary skills directory structure."""
    skills_dir = tmp_path / ".claude" / "skills"

    # Category: office
    office_dir = skills_dir / "office"
    office_dir.mkdir(parents=True)

    pdf_dir = office_dir / "pdf"
    pdf_dir.mkdir()
    (pdf_dir / "SKILL.md").write_text("# PDF Skill")

    xlsx_dir = office_dir / "xlsx"
    xlsx_dir.mkdir()
    (xlsx_dir / "SKILL.md").write_text("# XLSX Skill")

    # Category: analysis
    analysis_dir = skills_dir / "analysis"
    analysis_dir.mkdir()

    economist_dir = analysis_dir / "economist-analyst"
    economist_dir.mkdir()
    (economist_dir / "SKILL.md").write_text("# Economist Analyst")

    return skills_dir


@pytest.fixture
def index_builder(temp_skills_dir):
    """Create SkillIndexBuilder instance."""
    return SkillIndexBuilder(skills_dir=temp_skills_dir)


def test_build_index_creates_file(index_builder):
    """Test that build_index creates index file."""
    index_data = index_builder.build_index()

    assert index_builder.index_file.exists()
    assert index_data["version"] == "1.0"
    assert "generated" in index_data
    assert "skills" in index_data


def test_build_index_discovers_skills(index_builder):
    """Test that build_index discovers all skills."""
    index_data = index_builder.build_index()

    assert len(index_data["skills"]) == 3
    assert index_data["total_skills"] == 3

    skill_names = [s["name"] for s in index_data["skills"]]
    assert "pdf" in skill_names
    assert "xlsx" in skill_names
    assert "economist-analyst" in skill_names


def test_build_index_includes_categories(index_builder):
    """Test that index includes category information."""
    index_data = index_builder.build_index()

    categories = [s["category"] for s in index_data["skills"]]
    assert "office" in categories
    assert "analysis" in categories


def test_build_index_includes_paths(index_builder):
    """Test that index includes relative paths."""
    index_data = index_builder.build_index()

    for skill in index_data["skills"]:
        assert "path" in skill
        assert skill["path"].startswith(".claude/skills/")


def test_build_index_includes_descriptions(index_builder):
    """Test that index includes descriptions."""
    index_data = index_builder.build_index()

    for skill in index_data["skills"]:
        assert "description" in skill
        assert skill["description"]  # Not empty


def test_build_index_force_rebuild(index_builder):
    """Test force rebuilding index."""
    # Build initial index
    index_data1 = index_builder.build_index()
    timestamp1 = index_data1["generated"]

    # Wait a bit to ensure different timestamp
    import time

    time.sleep(0.1)

    # Force rebuild
    index_data2 = index_builder.build_index(force_rebuild=True)
    timestamp2 = index_data2["generated"]

    assert timestamp2 > timestamp1


def test_build_index_reuses_existing(index_builder):
    """Test that build_index reuses existing index."""
    # Build initial index
    index_data1 = index_builder.build_index()

    # Build again without force_rebuild
    index_data2 = index_builder.build_index(force_rebuild=False)

    # Should have same timestamp (reused)
    assert index_data1["generated"] == index_data2["generated"]


def test_load_index_missing_file(tmp_path):
    """Test loading index when file doesn't exist."""
    builder = SkillIndexBuilder(skills_dir=tmp_path / "nonexistent")
    index_data = builder._load_index()

    assert index_data["version"] == "1.0"
    assert index_data["total_skills"] == 0
    assert len(index_data["skills"]) == 0


def test_load_index_corrupted_file(tmp_path):
    """Test loading corrupted index file."""
    skills_dir = tmp_path / ".claude" / "skills"
    skills_dir.mkdir(parents=True)

    index_file = skills_dir / "_index.json"
    index_file.write_text("invalid json {")

    builder = SkillIndexBuilder(skills_dir=skills_dir)
    index_data = builder._load_index()

    # Should return empty index on corruption
    assert index_data["total_skills"] == 0


def test_save_index(tmp_path):
    """Test saving index to file."""
    skills_dir = tmp_path / ".claude" / "skills"
    builder = SkillIndexBuilder(skills_dir=skills_dir)

    index_data = {
        "version": "1.0",
        "generated": datetime.utcnow().isoformat() + "Z",
        "skills": [
            {
                "name": "test-skill",
                "category": "test",
                "path": ".claude/skills/test/test-skill/SKILL.md",
            }
        ],
        "total_skills": 1,
    }

    builder._save_index(index_data)

    assert builder.index_file.exists()

    # Verify saved content
    with open(builder.index_file) as f:
        loaded = json.load(f)
    assert loaded["version"] == "1.0"
    assert loaded["total_skills"] == 1


def test_refresh_index(index_builder):
    """Test refresh_index convenience method."""
    # Build initial index
    index_builder.build_index()

    # Refresh should rebuild
    index_data = index_builder.refresh_index()

    assert index_data["version"] == "1.0"
    assert len(index_data["skills"]) == 3


def test_build_index_empty_directory(tmp_path):
    """Test building index for empty skills directory."""
    empty_dir = tmp_path / ".claude" / "skills"
    empty_dir.mkdir(parents=True)

    builder = SkillIndexBuilder(skills_dir=empty_dir)
    index_data = builder.build_index()

    assert index_data["total_skills"] == 0
    assert len(index_data["skills"]) == 0


def test_build_index_nonexistent_directory(tmp_path):
    """Test building index when skills directory doesn't exist."""
    builder = SkillIndexBuilder(skills_dir=tmp_path / "nonexistent")
    index_data = builder.build_index()

    assert index_data["total_skills"] == 0
    assert len(index_data["skills"]) == 0


def test_build_index_ignores_hidden_directories(tmp_path):
    """Test that index building ignores directories starting with underscore."""
    skills_dir = tmp_path / ".claude" / "skills"
    skills_dir.mkdir(parents=True)

    # Create hidden directory (should be ignored)
    hidden_dir = skills_dir / "_hidden"
    hidden_dir.mkdir()
    skill_dir = hidden_dir / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Hidden Skill")

    builder = SkillIndexBuilder(skills_dir=skills_dir)
    index_data = builder.build_index()

    # Should not include hidden skills
    assert index_data["total_skills"] == 0


def test_build_index_handles_files_in_category_dir(tmp_path):
    """Test that index building handles files in category directories."""
    skills_dir = tmp_path / ".claude" / "skills"
    skills_dir.mkdir(parents=True)

    category_dir = skills_dir / "test"
    category_dir.mkdir()

    # Create both a skill directory and a file
    skill_dir = category_dir / "skill1"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Skill 1")

    # File in category directory (should be ignored)
    (category_dir / "readme.md").write_text("# Category README")

    builder = SkillIndexBuilder(skills_dir=skills_dir)
    index_data = builder.build_index()

    # Should only include the skill directory
    assert index_data["total_skills"] == 1
    assert index_data["skills"][0]["name"] == "skill1"


def test_extract_description_basic(index_builder):
    """Test basic description extraction."""
    skill_file = Path("/skills/test/test-skill/SKILL.md")
    description = index_builder._extract_description(skill_file)

    # For Phase 2, just returns skill name
    assert "test-skill" in description


def test_index_file_format(index_builder):
    """Test that index file is valid JSON with proper formatting."""
    index_builder.build_index()

    with open(index_builder.index_file) as f:
        content = f.read()
        index_data = json.loads(content)

    # Check required fields
    assert "version" in index_data
    assert "generated" in index_data
    assert "skills" in index_data
    assert "total_skills" in index_data

    # Check timestamp format
    timestamp = index_data["generated"]
    assert timestamp.endswith("Z")  # UTC indicator


def test_build_index_skill_with_readme_fallback(tmp_path):
    """Test that index building handles skills with README.md instead of SKILL.md."""
    skills_dir = tmp_path / ".claude" / "skills"
    category_dir = skills_dir / "test"
    category_dir.mkdir(parents=True)

    skill_dir = category_dir / "test-skill"
    skill_dir.mkdir()
    (skill_dir / "README.md").write_text("# Test Skill")

    builder = SkillIndexBuilder(skills_dir=skills_dir)
    index_data = builder.build_index()

    assert index_data["total_skills"] == 1
    assert index_data["skills"][0]["name"] == "test-skill"
