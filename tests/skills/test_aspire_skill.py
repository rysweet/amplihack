"""Validation tests for the Aspire skill following TDD methodology.

Tests validate skill file structure, YAML frontmatter, token budgets, content
structure, and progressive disclosure patterns. These tests will FAIL until the
skill is properly validated (TDD approach).

Philosophy:
- Skills are markdown files, not executable code
- Validation focuses on structure, not behavior
- Token efficiency is critical (target: <2000 tokens)
- Progressive disclosure: SKILL.md references supporting files
"""

import re
from pathlib import Path

import pytest
import tiktoken

# Path constants
WORKTREE_ROOT = Path("/home/azureuser/src/amplihack/worktrees/feat/issue-2197-aspire-skill")
SKILL_DIR = WORKTREE_ROOT / ".claude" / "skills" / "aspire"
SKILL_FILE = SKILL_DIR / "SKILL.md"

# Expected files in skill directory
REQUIRED_FILES = [
    "SKILL.md",
    "reference.md",
    "examples.md",
    "patterns.md",
    "troubleshooting.md",
    "commands.md",
]

# Token budget constants
MAX_SKILL_TOKENS = 2000
TARGET_SKILL_TOKENS = 1800


def count_tokens(text: str) -> int:
    """Count tokens using tiktoken for claude-sonnet-4-5."""
    # Use cl100k_base encoding (closest to Claude's tokenizer)
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def extract_yaml_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown file."""
    # Match YAML frontmatter between --- delimiters
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}

    yaml_text = match.group(1)
    result = {}

    # Parse simple YAML (key: value or key: [list])
    current_key = None
    for line in yaml_text.split("\n"):
        line = line.strip()
        if not line:
            continue

        if line.startswith("- "):
            # List item
            if current_key and isinstance(result.get(current_key), list):
                result[current_key].append(line[2:].strip())
        elif ":" in line:
            # Key: value
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()

            if not value:
                # Empty value, might be start of list
                result[key] = []
                current_key = key
            else:
                result[key] = value
                current_key = None

    return result


class TestFileStructure:
    """Test that all required files exist in correct location."""

    def test_skill_directory_exists(self):
        """Test that aspire skill directory exists."""
        assert SKILL_DIR.exists(), f"Skill directory does not exist: {SKILL_DIR}"
        assert SKILL_DIR.is_dir(), f"Skill path is not a directory: {SKILL_DIR}"

    def test_all_required_files_exist(self):
        """Test that all required skill files exist."""
        missing_files = []
        for filename in REQUIRED_FILES:
            file_path = SKILL_DIR / filename
            if not file_path.exists():
                missing_files.append(filename)

        assert not missing_files, (
            f"Missing required skill files: {missing_files}\nExpected location: {SKILL_DIR}"
        )

    def test_no_unexpected_files(self):
        """Test that only expected files exist (no cruft)."""
        actual_files = {f.name for f in SKILL_DIR.iterdir() if f.is_file()}
        expected_files = set(REQUIRED_FILES)

        unexpected = actual_files - expected_files

        # Allow common safe files
        allowed_extras = {".gitkeep", "README.md"}
        unexpected = unexpected - allowed_extras

        assert not unexpected, (
            f"Unexpected files in skill directory: {unexpected}\n"
            f"Only these files are expected: {expected_files}"
        )

    def test_files_are_markdown(self):
        """Test that all required files are markdown (.md)."""
        for filename in REQUIRED_FILES:
            assert filename.endswith(".md"), f"File is not markdown: {filename}"

    def test_files_are_readable(self):
        """Test that all files can be read."""
        for filename in REQUIRED_FILES:
            file_path = SKILL_DIR / filename
            try:
                content = file_path.read_text(encoding="utf-8")
                assert len(content) > 0, f"File is empty: {filename}"
            except Exception as e:
                pytest.fail(f"Cannot read file {filename}: {e}")


class TestYAMLFrontmatter:
    """Test YAML frontmatter structure and content."""

    @pytest.fixture
    def skill_content(self):
        """Load SKILL.md content."""
        return SKILL_FILE.read_text(encoding="utf-8")

    @pytest.fixture
    def frontmatter(self, skill_content):
        """Extract YAML frontmatter."""
        return extract_yaml_frontmatter(skill_content)

    def test_has_yaml_frontmatter(self, skill_content):
        """Test that SKILL.md has YAML frontmatter."""
        assert skill_content.startswith("---\n"), "SKILL.md must start with YAML frontmatter (---)"

        # Check for closing ---
        assert "---" in skill_content[4:], "YAML frontmatter must be closed with ---"

    def test_name_field_exists(self, frontmatter):
        """Test that name field exists."""
        assert "name" in frontmatter, "Missing 'name' field in frontmatter"

    def test_name_is_aspire(self, frontmatter):
        """Test that name is 'aspire' (lowercase, kebab-case)."""
        name = frontmatter.get("name", "")
        assert name == "aspire", f"Name must be 'aspire' (lowercase), got: '{name}'"

    def test_name_follows_conventions(self, frontmatter):
        """Test that name follows naming conventions."""
        name = frontmatter.get("name", "")

        # Must be lowercase
        assert name == name.lower(), f"Name must be lowercase: {name}"

        # Must not start/end with hyphen
        assert not name.startswith("-"), f"Name cannot start with hyphen: {name}"
        assert not name.endswith("-"), f"Name cannot end with hyphen: {name}"

        # Must not have consecutive hyphens
        assert "--" not in name, f"Name cannot have consecutive hyphens: {name}"

    def test_description_field_exists(self, frontmatter):
        """Test that description field exists and is non-empty."""
        assert "description" in frontmatter, "Missing 'description' field"

        description = frontmatter.get("description", "")
        assert len(description) > 0, "Description field is empty"
        assert len(description.strip()) > 0, "Description is whitespace only"

    def test_description_contains_trigger_keywords(self, frontmatter):
        """Test that description contains relevant trigger keywords."""
        description = frontmatter.get("description", "").lower()

        # Should contain at least one of these key terms
        key_terms = ["aspire", "distributed", "microservices", "orchestration"]

        found_terms = [term for term in key_terms if term in description]
        assert len(found_terms) > 0, (
            f"Description should contain at least one of: {key_terms}\nGot: {description}"
        )

    def test_version_field_exists(self, frontmatter):
        """Test that version field exists."""
        assert "version" in frontmatter, "Missing 'version' field"

        version = frontmatter.get("version", "")
        assert len(version) > 0, "Version field is empty"

    def test_version_format(self, frontmatter):
        """Test that version follows semver format."""
        version = frontmatter.get("version", "")

        # Simple semver pattern: X.Y.Z
        semver_pattern = r"^\d+\.\d+\.\d+$"
        assert re.match(semver_pattern, version), (
            f"Version must follow semver format (X.Y.Z): {version}"
        )

    def test_source_urls_field_exists(self, frontmatter):
        """Test that source_urls field exists."""
        assert "source_urls" in frontmatter, "Missing 'source_urls' field"

    def test_source_urls_is_list(self, frontmatter):
        """Test that source_urls is a list."""
        source_urls = frontmatter.get("source_urls", None)
        assert isinstance(source_urls, list), (
            f"source_urls must be a list, got: {type(source_urls)}"
        )

    def test_source_urls_contains_official_aspire_urls(self, frontmatter):
        """Test that source_urls contains official Aspire URLs."""
        source_urls = frontmatter.get("source_urls", [])

        # Convert to lowercase for case-insensitive matching
        urls_lower = [url.lower() for url in source_urls]

        # Should contain official Aspire documentation
        has_aspire_dev = any("aspire.dev" in url for url in urls_lower)
        has_ms_learn = any("learn.microsoft.com" in url and "aspire" in url for url in urls_lower)

        assert has_aspire_dev or has_ms_learn, (
            f"source_urls should contain official Aspire URLs\nGot: {source_urls}"
        )

    def test_activation_keywords_field_exists(self, frontmatter):
        """Test that activation_keywords field exists."""
        assert "activation_keywords" in frontmatter, "Missing 'activation_keywords' field"

    def test_activation_keywords_is_list(self, frontmatter):
        """Test that activation_keywords is a list."""
        keywords = frontmatter.get("activation_keywords", None)
        assert isinstance(keywords, list), (
            f"activation_keywords must be a list, got: {type(keywords)}"
        )

    def test_activation_keywords_includes_core_terms(self, frontmatter):
        """Test that activation_keywords includes core Aspire terms."""
        keywords = frontmatter.get("activation_keywords", [])
        keywords_lower = [k.lower() for k in keywords]

        # Must include these core terms
        required_terms = ["aspire", "distributed app", "microservices"]

        missing_terms = []
        for term in required_terms:
            if term not in keywords_lower:
                missing_terms.append(term)

        assert not missing_terms, (
            f"activation_keywords missing required terms: {missing_terms}\nGot: {keywords}"
        )

    def test_activation_keywords_has_sufficient_coverage(self, frontmatter):
        """Test that activation_keywords has good coverage (at least 5 terms)."""
        keywords = frontmatter.get("activation_keywords", [])
        assert len(keywords) >= 5, (
            f"activation_keywords should have at least 5 terms for good coverage\n"
            f"Got {len(keywords)}: {keywords}"
        )


class TestTokenBudget:
    """Test token budget constraints."""

    @pytest.fixture
    def skill_content(self):
        """Load SKILL.md content."""
        return SKILL_FILE.read_text(encoding="utf-8")

    def test_skill_under_max_token_budget(self, skill_content):
        """Test that SKILL.md is under maximum token budget (2000)."""
        token_count = count_tokens(skill_content)
        assert token_count <= MAX_SKILL_TOKENS, (
            f"SKILL.md exceeds maximum token budget!\n"
            f"Token count: {token_count}\n"
            f"Maximum allowed: {MAX_SKILL_TOKENS}\n"
            f"Exceeded by: {token_count - MAX_SKILL_TOKENS} tokens"
        )

    def test_skill_under_target_token_budget(self, skill_content):
        """Test that SKILL.md is under target token budget (1800)."""
        token_count = count_tokens(skill_content)
        assert token_count <= TARGET_SKILL_TOKENS, (
            f"SKILL.md exceeds target token budget!\n"
            f"Token count: {token_count}\n"
            f"Target: {TARGET_SKILL_TOKENS}\n"
            f"Exceeded by: {token_count - TARGET_SKILL_TOKENS} tokens\n"
            f"(Target provides buffer for future edits)"
        )

    def test_token_budget_declared_in_frontmatter(self, skill_content):
        """Test that token_budget is declared in frontmatter."""
        frontmatter = extract_yaml_frontmatter(skill_content)
        assert "token_budget" in frontmatter, "Missing 'token_budget' field in frontmatter"

        declared_budget = frontmatter.get("token_budget", "")
        assert declared_budget, "token_budget field is empty"

    def test_declared_budget_matches_target(self, skill_content):
        """Test that declared token_budget matches target (1800)."""
        frontmatter = extract_yaml_frontmatter(skill_content)
        declared_budget = int(frontmatter.get("token_budget", "0"))

        assert declared_budget == TARGET_SKILL_TOKENS, (
            f"Declared token_budget ({declared_budget}) should match target ({TARGET_SKILL_TOKENS})"
        )

    def test_actual_tokens_within_declared_budget(self, skill_content):
        """Test that actual tokens are within declared budget."""
        frontmatter = extract_yaml_frontmatter(skill_content)
        declared_budget = int(frontmatter.get("token_budget", "0"))
        actual_tokens = count_tokens(skill_content)

        assert actual_tokens <= declared_budget, (
            f"Actual tokens ({actual_tokens}) exceed declared budget ({declared_budget})"
        )


class TestContentStructure:
    """Test content structure and organization."""

    @pytest.fixture
    def skill_content(self):
        """Load SKILL.md content."""
        return SKILL_FILE.read_text(encoding="utf-8")

    def test_has_overview_section(self, skill_content):
        """Test that SKILL.md contains Overview section."""
        assert "## Overview" in skill_content, "Missing '## Overview' section"

    def test_has_quick_start_section(self, skill_content):
        """Test that SKILL.md contains Quick Start section."""
        assert "## Quick Start" in skill_content, "Missing '## Quick Start' section"

    def test_has_core_workflows_section(self, skill_content):
        """Test that SKILL.md contains Core Workflows section."""
        assert "## Core Workflows" in skill_content, "Missing '## Core Workflows' section"

    def test_has_navigation_guide_section(self, skill_content):
        """Test that SKILL.md contains Navigation Guide section."""
        assert "## Navigation Guide" in skill_content, "Missing '## Navigation Guide' section"

    def test_navigation_guide_references_all_supporting_files(self, skill_content):
        """Test that Navigation Guide references all supporting files."""
        # Find Navigation Guide section
        nav_start = skill_content.find("## Navigation Guide")
        assert nav_start != -1, "Navigation Guide section not found"

        # Extract Navigation Guide content (until next ## section or end)
        nav_end = skill_content.find("\n## ", nav_start + 1)
        if nav_end == -1:
            nav_section = skill_content[nav_start:]
        else:
            nav_section = skill_content[nav_start:nav_end]

        # Check that each supporting file is mentioned
        supporting_files = ["reference.md", "examples.md", "patterns.md", "troubleshooting.md"]
        missing_references = []

        for filename in supporting_files:
            if filename not in nav_section:
                missing_references.append(filename)

        assert not missing_references, (
            f"Navigation Guide must reference all supporting files.\nMissing: {missing_references}"
        )

    def test_overview_describes_core_problem(self, skill_content):
        """Test that Overview describes the core problem Aspire solves."""
        # Find Overview section
        overview_start = skill_content.find("## Overview")
        assert overview_start != -1

        overview_end = skill_content.find("\n## ", overview_start + 1)
        overview_section = skill_content[overview_start:overview_end]

        # Should mention distributed/cloud-native/orchestration concepts
        key_concepts = ["distributed", "cloud-native", "orchestration", "microservices"]
        found_concepts = [c for c in key_concepts if c.lower() in overview_section.lower()]

        assert len(found_concepts) >= 2, (
            f"Overview should describe core Aspire concepts.\n"
            f"Expected at least 2 of: {key_concepts}\n"
            f"Found: {found_concepts}"
        )

    def test_quick_start_has_code_examples(self, skill_content):
        """Test that Quick Start contains code examples."""
        # Find Quick Start section
        qs_start = skill_content.find("## Quick Start")
        assert qs_start != -1

        qs_end = skill_content.find("\n## ", qs_start + 1)
        if qs_end == -1:
            qs_section = skill_content[qs_start:]
        else:
            qs_section = skill_content[qs_start:qs_end]

        # Should contain code blocks (```bash or ```csharp)
        assert "```bash" in qs_section or "```csharp" in qs_section, (
            "Quick Start should contain code examples"
        )

    def test_core_workflows_has_subsections(self, skill_content):
        """Test that Core Workflows has subsections."""
        # Find Core Workflows section
        cw_start = skill_content.find("## Core Workflows")
        assert cw_start != -1

        cw_end = skill_content.find("\n## ", cw_start + 1)
        if cw_end == -1:
            cw_section = skill_content[cw_start:]
        else:
            cw_section = skill_content[cw_start:cw_end]

        # Should have subsections (### headers)
        subsection_count = cw_section.count("### ")
        assert subsection_count >= 2, (
            f"Core Workflows should have at least 2 subsections (###)\nFound: {subsection_count}"
        )


class TestProgressiveDisclosure:
    """Test progressive disclosure patterns."""

    @pytest.fixture
    def skill_content(self):
        """Load SKILL.md content."""
        return SKILL_FILE.read_text(encoding="utf-8")

    def test_navigation_guide_uses_read_when_pattern(self, skill_content):
        """Test that Navigation Guide uses 'Read when you need:' pattern."""
        # Find Navigation Guide section
        nav_start = skill_content.find("## Navigation Guide")
        assert nav_start != -1

        nav_end = skill_content.find("\n## ", nav_start + 1)
        if nav_end == -1:
            nav_section = skill_content[nav_start:]
        else:
            nav_section = skill_content[nav_start:nav_end]

        # Should use progressive disclosure pattern
        pattern_phrases = [
            "Read when",
            "when you need",
            "read when you need",
        ]

        found_pattern = any(phrase.lower() in nav_section.lower() for phrase in pattern_phrases)

        assert found_pattern, (
            "Navigation Guide should use 'Read when you need:' pattern for progressive disclosure"
        )

    def test_supporting_files_referenced_not_inlined(self, skill_content):
        """Test that supporting file content is not inlined in SKILL.md."""
        # SKILL.md should reference supporting files, not contain their full content
        # This test ensures we maintain progressive disclosure

        # Get file size of SKILL.md
        skill_size = len(skill_content)

        # SKILL.md should be significantly smaller than sum of all files
        # (This is a proxy for "not inlining content")
        total_size = 0
        for filename in REQUIRED_FILES:
            file_path = SKILL_DIR / filename
            total_size += len(file_path.read_text(encoding="utf-8"))

        # SKILL.md should be less than 40% of total content
        ratio = skill_size / total_size
        assert ratio < 0.4, (
            f"SKILL.md seems to inline too much content ({ratio:.1%} of total)\n"
            f"Should reference supporting files, not duplicate content"
        )

    def test_no_nested_references_in_supporting_files(self):
        """Test that supporting files don't reference each other (one level deep)."""
        # Supporting files should not create circular references or deep nesting
        supporting_files = ["reference.md", "examples.md", "patterns.md", "troubleshooting.md"]

        for filename in supporting_files:
            file_path = SKILL_DIR / filename
            content = file_path.read_text(encoding="utf-8")

            # Check if this file references other supporting files
            other_files = [f for f in supporting_files if f != filename]
            found_references = []

            for other_file in other_files:
                if other_file in content:
                    found_references.append(other_file)

            # Allow README references and "see also" patterns, but warn if excessive
            if len(found_references) > 2:
                pytest.fail(
                    f"{filename} references too many other files: {found_references}\n"
                    f"Supporting files should be one level deep, not nested"
                )


class TestExamples:
    """Test that examples.md contains complete examples."""

    @pytest.fixture
    def examples_content(self):
        """Load examples.md content."""
        return (SKILL_DIR / "examples.md").read_text(encoding="utf-8")

    def test_examples_file_exists(self):
        """Test that examples.md exists."""
        assert (SKILL_DIR / "examples.md").exists(), "examples.md does not exist"

    def test_examples_has_code_blocks(self, examples_content):
        """Test that examples.md contains code blocks."""
        # Should have at least 5 code blocks
        code_block_count = examples_content.count("```")
        # Each code block has opening and closing ```, so divide by 2
        code_block_count = code_block_count // 2

        assert code_block_count >= 5, (
            f"examples.md should have at least 5 code blocks\nFound: {code_block_count}"
        )

    def test_examples_has_csharp_code(self, examples_content):
        """Test that examples.md contains C# code examples."""
        assert "```csharp" in examples_content, (
            "examples.md should contain C# code examples (```csharp)"
        )

    def test_examples_are_complete(self, examples_content):
        """Test that examples are complete (contain complete code, not snippets)."""
        # Find all C# code blocks
        code_blocks = re.findall(r"```csharp\n(.*?)```", examples_content, re.DOTALL)

        # At least some code blocks should be substantial (> 10 lines)
        substantial_blocks = [block for block in code_blocks if block.count("\n") >= 10]

        assert len(substantial_blocks) >= 2, (
            f"examples.md should have at least 2 substantial code examples (>10 lines)\n"
            f"Found: {len(substantial_blocks)}"
        )


class TestReferences:
    """Test that reference.md is comprehensive."""

    @pytest.fixture
    def reference_content(self):
        """Load reference.md content."""
        return (SKILL_DIR / "reference.md").read_text(encoding="utf-8")

    def test_reference_file_exists(self):
        """Test that reference.md exists."""
        assert (SKILL_DIR / "reference.md").exists(), "reference.md does not exist"

    def test_reference_covers_apphost_api(self, reference_content):
        """Test that reference.md covers AppHost API."""
        # Should mention key AppHost concepts
        key_terms = ["AppHost", "AddProject", "AddRedis", "AddPostgres", "WithReference"]

        found_terms = [term for term in key_terms if term in reference_content]

        assert len(found_terms) >= 4, (
            f"reference.md should cover AppHost API\n"
            f"Expected at least 4 of: {key_terms}\n"
            f"Found: {found_terms}"
        )


class TestPatterns:
    """Test that patterns.md contains best practices."""

    @pytest.fixture
    def patterns_content(self):
        """Load patterns.md content."""
        return (SKILL_DIR / "patterns.md").read_text(encoding="utf-8")

    def test_patterns_file_exists(self):
        """Test that patterns.md exists."""
        assert (SKILL_DIR / "patterns.md").exists(), "patterns.md does not exist"

    def test_patterns_covers_production_topics(self, patterns_content):
        """Test that patterns.md covers production deployment topics."""
        # Should cover production concerns
        production_topics = [
            "production",
            "deployment",
            "security",
            "performance",
            "high availability",
        ]

        found_topics = [
            topic for topic in production_topics if topic.lower() in patterns_content.lower()
        ]

        assert len(found_topics) >= 3, (
            f"patterns.md should cover production topics\n"
            f"Expected at least 3 of: {production_topics}\n"
            f"Found: {found_topics}"
        )


class TestTroubleshooting:
    """Test that troubleshooting.md provides debugging guidance."""

    @pytest.fixture
    def troubleshooting_content(self):
        """Load troubleshooting.md content."""
        return (SKILL_DIR / "troubleshooting.md").read_text(encoding="utf-8")

    def test_troubleshooting_file_exists(self):
        """Test that troubleshooting.md exists."""
        assert (SKILL_DIR / "troubleshooting.md").exists(), "troubleshooting.md does not exist"

    def test_troubleshooting_covers_common_issues(self, troubleshooting_content):
        """Test that troubleshooting.md covers common issues."""
        # Should cover common problem areas
        common_issues = ["error", "debug", "fix", "problem", "issue"]

        found_issues = [
            issue for issue in common_issues if issue.lower() in troubleshooting_content.lower()
        ]

        assert len(found_issues) >= 3, (
            f"troubleshooting.md should cover common issues\n"
            f"Expected at least 3 of: {common_issues}\n"
            f"Found: {found_issues}"
        )


class TestNoInternalBrokenReferences:
    """Test that there are no broken internal references."""

    def test_no_broken_internal_links(self):
        """Test that internal markdown links are not broken."""
        for filename in REQUIRED_FILES:
            file_path = SKILL_DIR / filename
            content = file_path.read_text(encoding="utf-8")

            # Find all markdown links: [text](link)
            links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)

            broken_links = []
            for link_text, link_target in links:
                # Skip external URLs (http/https)
                if link_target.startswith("http"):
                    continue

                # Skip anchors within same file (#section)
                if link_target.startswith("#"):
                    continue

                # Check if referenced file exists
                # Handle relative paths
                if "/" in link_target:
                    # Complex path, skip for now
                    continue

                referenced_file = SKILL_DIR / link_target
                if not referenced_file.exists():
                    broken_links.append((link_text, link_target))

            assert not broken_links, f"{filename} has broken internal links:\n{broken_links}"


# Test markers for organization
pytest.mark.unit = pytest.mark.unit
