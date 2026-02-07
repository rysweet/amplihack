"""Comprehensive TDD tests for amplihack-expert Claude Code skill.

Test Structure:
- Level 1: File Structure and Token Budget Tests
- Level 2: YAML Frontmatter Validation Tests
- Level 3: Navigation and Link Validation Tests
- Level 4: Auto-Activation Trigger Tests
- Level 5: Integration Tests (Progressive Disclosure)
- Level 6: Philosophy Compliance Tests

All tests follow TDD methodology - they will FAIL initially until implementation is complete.
"""

import re
import sys
from pathlib import Path
from typing import Any

import pytest  # type: ignore[import-untyped]
import yaml

# Skill directory structure
SKILL_DIR = Path(__file__).parent.parent
SKILL_FILE = SKILL_DIR / "SKILL.md"
REFERENCE_FILE = SKILL_DIR / "reference.md"
EXAMPLES_FILE = SKILL_DIR / "examples.md"

# Token budget limits from MODULE_SPEC
TOKEN_BUDGET = {
    "skill_md": 800,
    "reference_md": 1200,
    "examples_md": 600,
    "total": 2600,
}


# ============================================================================
# Level 1: File Structure and Token Budget Tests
# ============================================================================


def test_skill_directory_exists():
    """Verify amplihack-expert skill directory exists."""
    assert SKILL_DIR.exists(), f"Skill directory not found: {SKILL_DIR}"
    assert SKILL_DIR.is_dir(), f"Skill path is not a directory: {SKILL_DIR}"


def test_skill_file_exists():
    """Verify SKILL.md exists."""
    assert SKILL_FILE.exists(), f"SKILL.md not found: {SKILL_FILE}"


def test_reference_file_exists():
    """Verify reference.md exists."""
    assert REFERENCE_FILE.exists(), f"reference.md not found: {REFERENCE_FILE}"


def test_examples_file_exists():
    """Verify examples.md exists."""
    assert EXAMPLES_FILE.exists(), f"examples.md not found: {EXAMPLES_FILE}"


def count_tokens(text: str) -> int:
    """
    Approximate token count (4 chars per token).
    This is a rough estimate - actual tokenization may vary.
    """
    return len(text) // 4


def test_skill_md_token_budget():
    """Verify SKILL.md is under 800 token budget."""
    if not SKILL_FILE.exists():
        pytest.skip("SKILL.md does not exist yet (TDD)")

    content = SKILL_FILE.read_text()
    token_count = count_tokens(content)

    assert token_count <= TOKEN_BUDGET["skill_md"], (
        f"SKILL.md exceeds token budget: {token_count} > {TOKEN_BUDGET['skill_md']} tokens"
    )


def test_reference_md_token_budget():
    """Verify reference.md is under 1,200 token budget."""
    if not REFERENCE_FILE.exists():
        pytest.skip("reference.md does not exist yet (TDD)")

    content = REFERENCE_FILE.read_text()
    token_count = count_tokens(content)

    assert token_count <= TOKEN_BUDGET["reference_md"], (
        f"reference.md exceeds token budget: {token_count} > {TOKEN_BUDGET['reference_md']} tokens"
    )


def test_examples_md_token_budget():
    """Verify examples.md is under 600 token budget."""
    if not EXAMPLES_FILE.exists():
        pytest.skip("examples.md does not exist yet (TDD)")

    content = EXAMPLES_FILE.read_text()
    token_count = count_tokens(content)

    assert token_count <= TOKEN_BUDGET["examples_md"], (
        f"examples.md exceeds token budget: {token_count} > {TOKEN_BUDGET['examples_md']} tokens"
    )


def test_total_token_budget():
    """Verify total token budget across all three files is under 2,600 tokens."""
    if not all([SKILL_FILE.exists(), REFERENCE_FILE.exists(), EXAMPLES_FILE.exists()]):
        pytest.skip("Not all skill files exist yet (TDD)")

    skill_tokens = count_tokens(SKILL_FILE.read_text())
    reference_tokens = count_tokens(REFERENCE_FILE.read_text())
    examples_tokens = count_tokens(EXAMPLES_FILE.read_text())
    total_tokens = skill_tokens + reference_tokens + examples_tokens

    assert total_tokens <= TOKEN_BUDGET["total"], (
        f"Total token budget exceeded: {total_tokens} > {TOKEN_BUDGET['total']} tokens "
        f"(SKILL: {skill_tokens}, reference: {reference_tokens}, examples: {examples_tokens})"
    )


# ============================================================================
# Level 2: YAML Frontmatter Validation Tests
# ============================================================================


def extract_yaml_frontmatter(file_path: Path) -> dict | None:
    """Extract and parse YAML frontmatter from markdown file."""
    if not file_path.exists():
        return None

    content = file_path.read_text()
    if not content.startswith("---"):
        return None

    # Extract YAML between --- delimiters
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    try:
        return yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None


def test_skill_md_has_valid_yaml():
    """Verify SKILL.md has valid YAML frontmatter."""
    if not SKILL_FILE.exists():
        pytest.skip("SKILL.md does not exist yet (TDD)")

    metadata = extract_yaml_frontmatter(SKILL_FILE)
    assert metadata is not None, "SKILL.md missing or has invalid YAML frontmatter"
    assert isinstance(metadata, dict), "YAML frontmatter is not a dictionary"


def test_yaml_required_fields():
    """Verify YAML frontmatter has all required fields."""
    if not SKILL_FILE.exists():
        pytest.skip("SKILL.md does not exist yet (TDD)")

    metadata = extract_yaml_frontmatter(SKILL_FILE)
    if metadata is None:
        pytest.skip("YAML frontmatter not available")

    required_fields = ["name", "description", "version", "author", "tags"]
    for field in required_fields:
        assert field in metadata, f"YAML missing required field: {field}"


def test_yaml_name_field():
    """Verify YAML name field is 'amplihack-expert'."""
    if not SKILL_FILE.exists():
        pytest.skip("SKILL.md does not exist yet (TDD)")

    metadata = extract_yaml_frontmatter(SKILL_FILE)
    if metadata is None:
        pytest.skip("YAML frontmatter not available")

    # Type guard: metadata is now known to be Dict, not None
    assert isinstance(metadata, dict), "Metadata should be a dictionary"

    assert metadata.get("name") == "amplihack-expert", (
        f"YAML name field should be 'amplihack-expert', got: {metadata.get('name')}"
    )


def test_yaml_triggers_defined():
    """Verify YAML has triggers section with keywords, patterns, and file_paths."""
    if not SKILL_FILE.exists():
        pytest.skip("SKILL.md does not exist yet (TDD)")

    metadata = extract_yaml_frontmatter(SKILL_FILE)
    if metadata is None:
        pytest.skip("YAML frontmatter not available")

    # Type guard: narrow metadata to Dict[str, Any]
    assert isinstance(metadata, dict), "Metadata should be a dictionary"
    md: dict[str, Any] = metadata  # Explicit type annotation for Pyright

    assert "triggers" in md, "YAML missing 'triggers' section"
    triggers = md["triggers"]
    assert isinstance(triggers, dict), "triggers should be a dictionary"

    assert "keywords" in triggers, "triggers missing 'keywords' list"
    assert "patterns" in triggers, "triggers missing 'patterns' list"
    assert "file_paths" in triggers, "triggers missing 'file_paths' list"

    assert isinstance(triggers["keywords"], list), "keywords should be a list"
    assert isinstance(triggers["patterns"], list), "patterns should be a list"
    assert isinstance(triggers["file_paths"], list), "file_paths should be a list"


def test_yaml_token_budget_defined():
    """Verify YAML has token_budget section with limits."""
    if not SKILL_FILE.exists():
        pytest.skip("SKILL.md does not exist yet (TDD)")

    metadata = extract_yaml_frontmatter(SKILL_FILE)
    if metadata is None:
        pytest.skip("YAML frontmatter not available")

    # Type guard: narrow metadata to Dict[str, Any]
    assert isinstance(metadata, dict), "Metadata should be a dictionary"
    md: dict[str, Any] = metadata  # Explicit type annotation for Pyright

    assert "token_budget" in md, "YAML missing 'token_budget' section"
    budget = md["token_budget"]
    assert isinstance(budget, dict), "token_budget should be a dictionary"

    assert budget.get("skill_md") == 800, "token_budget.skill_md should be 800"
    assert budget.get("reference_md") == 1200, "token_budget.reference_md should be 1200"
    assert budget.get("examples_md") == 600, "token_budget.examples_md should be 600"
    assert budget.get("total") == 2600, "token_budget.total should be 2600"


def test_yaml_disclosure_strategy_defined():
    """Verify YAML has progressive disclosure strategy."""
    if not SKILL_FILE.exists():
        pytest.skip("SKILL.md does not exist yet (TDD)")

    metadata = extract_yaml_frontmatter(SKILL_FILE)
    if metadata is None:
        pytest.skip("YAML frontmatter not available")

    # Type guard: narrow metadata to Dict[str, Any]
    assert isinstance(metadata, dict), "Metadata should be a dictionary"
    md: dict[str, Any] = metadata  # Explicit type annotation for Pyright

    assert "disclosure_strategy" in md, "YAML missing 'disclosure_strategy' section"
    strategy = md["disclosure_strategy"]
    assert isinstance(strategy, dict), "disclosure_strategy should be a dictionary"

    expected_strategies = [
        "quick_answer",
        "architecture_question",
        "how_to_question",
        "comprehensive",
    ]
    for key in expected_strategies:
        assert key in strategy, f"disclosure_strategy missing '{key}'"


def test_yaml_references_defined():
    """Verify YAML has references to related files."""
    if not SKILL_FILE.exists():
        pytest.skip("SKILL.md does not exist yet (TDD)")

    metadata = extract_yaml_frontmatter(SKILL_FILE)
    if metadata is None:
        pytest.skip("YAML frontmatter not available")

    # Type guard: narrow metadata to Dict[str, Any]
    assert isinstance(metadata, dict), "Metadata should be a dictionary"
    md: dict[str, Any] = metadata  # Explicit type annotation for Pyright

    assert "references" in md, "YAML missing 'references' section"
    references = md["references"]
    assert isinstance(references, list), "references should be a list"
    assert len(references) > 0, "references list is empty"


# ============================================================================
# Level 3: Navigation and Link Validation Tests
# ============================================================================


def extract_markdown_links(content: str) -> list[str]:
    """Extract all markdown links from content."""
    # Match [text](link) pattern
    link_pattern = r"\[([^\]]+)\]\(([^\)]+)\)"
    matches = re.findall(link_pattern, content)
    return [link for _, link in matches]


def test_navigation_guide_exists():
    """Verify SKILL.md has a Navigation Guide section."""
    if not SKILL_FILE.exists():
        pytest.skip("SKILL.md does not exist yet (TDD)")

    content = SKILL_FILE.read_text()
    assert "Navigation Guide" in content or "navigation guide" in content.lower(), (
        "SKILL.md missing Navigation Guide section"
    )


def test_skill_md_links_to_reference():
    """Verify SKILL.md contains link to reference.md."""
    if not SKILL_FILE.exists():
        pytest.skip("SKILL.md does not exist yet (TDD)")

    content = SKILL_FILE.read_text()
    links = extract_markdown_links(content)

    # Check for reference.md in links or direct mentions
    has_reference_link = any("reference.md" in link for link in links)
    has_reference_mention = "reference.md" in content

    assert has_reference_link or has_reference_mention, "SKILL.md should reference reference.md"


def test_skill_md_links_to_examples():
    """Verify SKILL.md contains link to examples.md."""
    if not SKILL_FILE.exists():
        pytest.skip("SKILL.md does not exist yet (TDD)")

    content = SKILL_FILE.read_text()
    links = extract_markdown_links(content)

    # Check for examples.md in links or direct mentions
    has_examples_link = any("examples.md" in link for link in links)
    has_examples_mention = "examples.md" in content

    assert has_examples_link or has_examples_mention, "SKILL.md should reference examples.md"


def test_all_internal_links_valid():
    """Verify all internal links (to reference.md, examples.md) are valid."""
    files_to_check = [SKILL_FILE, REFERENCE_FILE, EXAMPLES_FILE]

    for file_path in files_to_check:
        if not file_path.exists():
            continue

        content = file_path.read_text()
        links = extract_markdown_links(content)

        for link in links:
            # Check internal links (relative paths)
            if link in ["reference.md", "examples.md", "SKILL.md"]:
                target_path = SKILL_DIR / link
                assert target_path.exists(), (
                    f"{file_path.name} links to {link}, but file does not exist"
                )


# ============================================================================
# Level 4: Auto-Activation Trigger Tests
# ============================================================================


def test_primary_keywords_present():
    """Verify primary keywords are defined in triggers."""
    if not SKILL_FILE.exists():
        pytest.skip("SKILL.md does not exist yet (TDD)")

    metadata = extract_yaml_frontmatter(SKILL_FILE)
    if metadata is None or "triggers" not in metadata:
        pytest.skip("YAML triggers not available")

    # Type guard: narrow metadata to Dict[str, Any]
    assert isinstance(metadata, dict), "Metadata should be a dictionary"
    md: dict[str, Any] = metadata

    keywords = md["triggers"].get("keywords", [])

    # Primary keywords from MODULE_SPEC
    expected_primary = ["amplihack", "ultrathink", "DEFAULT_WORKFLOW", ".claude/", "workflow"]

    for keyword in expected_primary:
        assert any(keyword.lower() in k.lower() for k in keywords), (
            f"Primary keyword '{keyword}' missing from triggers.keywords"
        )


def test_question_patterns_present():
    """Verify question patterns are defined and valid regex."""
    if not SKILL_FILE.exists():
        pytest.skip("SKILL.md does not exist yet (TDD)")

    metadata = extract_yaml_frontmatter(SKILL_FILE)
    if metadata is None or "triggers" not in metadata:
        pytest.skip("YAML triggers not available")

    # Type guard: narrow metadata to Dict[str, Any]
    assert isinstance(metadata, dict), "Metadata should be a dictionary"
    md: dict[str, Any] = metadata

    patterns = md["triggers"].get("patterns", [])

    # Verify patterns exist
    assert len(patterns) > 0, "No question patterns defined"

    # Verify patterns are valid regex
    for pattern in patterns:
        try:
            re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            pytest.fail(f"Invalid regex pattern '{pattern}': {e}")


def test_file_path_patterns_present():
    """Verify file path patterns are defined."""
    if not SKILL_FILE.exists():
        pytest.skip("SKILL.md does not exist yet (TDD)")

    metadata = extract_yaml_frontmatter(SKILL_FILE)
    if metadata is None or "triggers" not in metadata:
        pytest.skip("YAML triggers not available")

    # Type guard: narrow metadata to Dict[str, Any]
    assert isinstance(metadata, dict), "Metadata should be a dictionary"
    md: dict[str, Any] = metadata

    file_paths = md["triggers"].get("file_paths", [])

    # Expected file path patterns from MODULE_SPEC
    expected_paths = [
        "~/.amplihack/",
        ".claude/agents/",
        ".claude/commands/",
        ".claude/workflow/",
        ".claude/skills/",
    ]

    for path in expected_paths:
        assert any(path in fp for fp in file_paths), (
            f"File path pattern '{path}' missing from triggers.file_paths"
        )


def test_trigger_activation_simulation():
    """Simulate trigger activation with sample user messages."""
    if not SKILL_FILE.exists():
        pytest.skip("SKILL.md does not exist yet (TDD)")

    metadata = extract_yaml_frontmatter(SKILL_FILE)
    if metadata is None or "triggers" not in metadata:
        pytest.skip("YAML triggers not available")

    # Type guard: narrow metadata to Dict[str, Any]
    assert isinstance(metadata, dict), "Metadata should be a dictionary"
    md: dict[str, Any] = metadata

    keywords = [k.lower() for k in md["triggers"].get("keywords", [])]
    patterns = md["triggers"].get("patterns", [])

    # Test cases: (message, should_trigger)
    test_cases = [
        ("How does amplihack work?", True),
        ("What is ultrathink?", True),
        ("How do I use the DEFAULT_WORKFLOW?", True),
        ("What agents are available in amplihack?", True),
        ("Explain the workflow system", True),
        ("Tell me about Python", False),
        ("What is Docker?", False),
    ]

    for message, should_trigger in test_cases:
        # Check keyword match
        keyword_match = any(keyword in message.lower() for keyword in keywords)

        # Check pattern match
        pattern_match = any(re.search(pattern, message, re.IGNORECASE) for pattern in patterns)

        triggered = keyword_match or pattern_match

        assert triggered == should_trigger, (
            f"Trigger mismatch for '{message}': expected {should_trigger}, got {triggered}"
        )


# ============================================================================
# Level 5: Integration Tests (Progressive Disclosure)
# ============================================================================


def test_progressive_disclosure_content_structure():
    """Verify progressive disclosure: SKILL.md is gateway, others have depth."""
    if not all([SKILL_FILE.exists(), REFERENCE_FILE.exists(), EXAMPLES_FILE.exists()]):
        pytest.skip("Not all skill files exist yet (TDD)")

    skill_content = SKILL_FILE.read_text()
    reference_content = REFERENCE_FILE.read_text()
    examples_content = EXAMPLES_FILE.read_text()

    # SKILL.md should be shorter and reference others
    assert count_tokens(skill_content) < count_tokens(reference_content), (
        "SKILL.md should be shorter than reference.md (progressive disclosure)"
    )

    # reference.md should have architecture details
    assert "architecture" in reference_content.lower(), (
        "reference.md should contain architecture details"
    )

    # examples.md should have practical examples
    assert "example" in examples_content.lower(), "examples.md should contain examples"


def test_cross_file_link_resolution():
    """Verify all cross-file links resolve correctly."""
    if not all([SKILL_FILE.exists(), REFERENCE_FILE.exists(), EXAMPLES_FILE.exists()]):
        pytest.skip("Not all skill files exist yet (TDD)")

    # Check that when SKILL.md references reference.md, it exists
    skill_content = SKILL_FILE.read_text()
    if "reference.md" in skill_content:
        assert REFERENCE_FILE.exists(), "SKILL.md references reference.md but it doesn't exist"

    if "examples.md" in skill_content:
        assert EXAMPLES_FILE.exists(), "SKILL.md references examples.md but it doesn't exist"


def test_example_commands_are_valid():
    """Verify example commands in examples.md are syntactically valid."""
    if not EXAMPLES_FILE.exists():
        pytest.skip("examples.md does not exist yet (TDD)")

    content = EXAMPLES_FILE.read_text()

    # Extract command examples (lines starting with /)
    command_pattern = r"^(/[a-z:]+(?:\s+.*)?)$"
    commands = re.findall(command_pattern, content, re.MULTILINE)

    # Verify commands follow naming convention
    for cmd in commands:
        assert cmd.startswith("/"), f"Command should start with '/': {cmd}"
        # Check for valid command format
        assert re.match(r"^/[a-z][a-z0-9:_-]*", cmd), f"Command has invalid format: {cmd}"


def test_examples_reference_real_workflows():
    """Verify examples reference actual workflow files."""
    if not EXAMPLES_FILE.exists():
        pytest.skip("examples.md does not exist yet (TDD)")

    content = EXAMPLES_FILE.read_text()

    # Check for references to actual workflow files
    expected_workflows = [
        "DEFAULT_WORKFLOW",
        "INVESTIGATION_WORKFLOW",
        "N_VERSION_WORKFLOW",
        "DEBATE_WORKFLOW",
        "CASCADE_WORKFLOW",
        "FIX_WORKFLOW",
    ]

    # At least 3 workflows should be mentioned in examples
    mentioned_workflows = [wf for wf in expected_workflows if wf in content]
    assert len(mentioned_workflows) >= 3, (
        f"examples.md should reference at least 3 workflows, found: {mentioned_workflows}"
    )


# ============================================================================
# Level 6: Philosophy Compliance Tests
# ============================================================================


def calculate_simplicity_score(content: str) -> float:
    """
    Calculate ruthless simplicity score based on content characteristics.

    Criteria:
    - Short sentences (prefer < 20 words)
    - Bullet points and tables (high density)
    - Low complexity words (avoid jargon)
    - Code examples (concrete over abstract)
    - No redundancy

    Returns: Score from 0-100 (target > 85%)
    """
    score = 100.0

    # Penalty for long paragraphs (> 300 chars without bullet/table)
    paragraphs = content.split("\n\n")
    long_paragraphs = [
        p for p in paragraphs if len(p) > 300 and not p.startswith(("-", "*", "|", "#"))
    ]
    score -= len(long_paragraphs) * 2

    # Bonus for tables (dense information)
    table_count = content.count("|")
    score += min(table_count / 10, 10)  # Up to 10 bonus points

    # Bonus for code examples
    code_block_count = content.count("```")
    score += min(code_block_count / 2, 10)  # Up to 10 bonus points

    # Bonus for bullet points
    bullet_count = len(
        [line for line in content.split("\n") if line.strip().startswith(("-", "*"))]
    )
    score += min(bullet_count / 5, 10)  # Up to 10 bonus points

    # Penalty for complexity markers (very, extremely, really, etc.)
    complexity_words = ["very", "extremely", "really", "quite", "somewhat", "perhaps"]
    for word in complexity_words:
        score -= content.lower().count(word) * 0.5

    return max(0, min(100, score))


def test_ruthless_simplicity_score():
    """Verify ruthless simplicity score is > 85% for all files."""
    if not all([SKILL_FILE.exists(), REFERENCE_FILE.exists(), EXAMPLES_FILE.exists()]):
        pytest.skip("Not all skill files exist yet (TDD)")

    files = {
        "SKILL.md": SKILL_FILE,
        "reference.md": REFERENCE_FILE,
        "examples.md": EXAMPLES_FILE,
    }

    for name, file_path in files.items():
        content = file_path.read_text()
        score = calculate_simplicity_score(content)

        assert score >= 85, f"{name} simplicity score too low: {score:.1f}% (target > 85%)"


def test_zero_bs_implementation():
    """Verify no TODOs, placeholders, or incomplete implementations."""
    if not all([SKILL_FILE.exists(), REFERENCE_FILE.exists(), EXAMPLES_FILE.exists()]):
        pytest.skip("Not all skill files exist yet (TDD)")

    files = {
        "SKILL.md": SKILL_FILE,
        "reference.md": REFERENCE_FILE,
        "examples.md": EXAMPLES_FILE,
    }

    bs_markers = ["TODO", "FIXME", "XXX", "PLACEHOLDER", "TBD", "COMING SOON"]

    for name, file_path in files.items():
        content = file_path.read_text()

        for marker in bs_markers:
            assert marker not in content.upper(), (
                f"{name} contains BS marker '{marker}' - Zero-BS implementation required"
            )


def test_modular_design_independence():
    """Verify each file is independently readable (modular design)."""
    if not all([SKILL_FILE.exists(), REFERENCE_FILE.exists(), EXAMPLES_FILE.exists()]):
        pytest.skip("Not all skill files exist yet (TDD)")

    # Each file should have a clear title/heading
    for file_path in [SKILL_FILE, REFERENCE_FILE, EXAMPLES_FILE]:
        content = file_path.read_text()

        # Check for main heading
        has_heading = content.lstrip().startswith("#")
        assert has_heading, f"{file_path.name} should start with a clear heading"


def test_progressive_disclosure_pattern():
    """Verify progressive disclosure pattern is implemented correctly."""
    if not SKILL_FILE.exists():
        pytest.skip("SKILL.md does not exist yet (TDD)")

    content = SKILL_FILE.read_text()

    # SKILL.md should guide users to other files
    navigation_indicators = [
        "reference.md",
        "examples.md",
        "when to read",
        "see also",
        "for more",
    ]

    has_navigation = any(indicator in content.lower() for indicator in navigation_indicators)
    assert has_navigation, (
        "SKILL.md should guide users to reference.md and examples.md (progressive disclosure)"
    )


def test_no_dead_code_or_content():
    """Verify no commented-out sections or unused content."""
    if not all([SKILL_FILE.exists(), REFERENCE_FILE.exists(), EXAMPLES_FILE.exists()]):
        pytest.skip("Not all skill files exist yet (TDD)")

    for file_path in [SKILL_FILE, REFERENCE_FILE, EXAMPLES_FILE]:
        content = file_path.read_text()

        # Check for commented-out markdown sections
        # Note: HTML comments <!-- --> are sometimes valid, so we check for excessive use
        comment_pattern = r"<!--[\s\S]*?-->"
        comments = re.findall(comment_pattern, content)

        # Allow up to 2 small comments (for metadata), but flag large commented sections
        large_comments = [c for c in comments if len(c) > 100]
        assert len(large_comments) == 0, (
            f"{file_path.name} contains large commented sections (dead code)"
        )


# ============================================================================
# Summary and Reporting
# ============================================================================


def test_skill_readiness_report():
    """Generate comprehensive readiness report (informational, does not fail)."""
    print("\n" + "=" * 70)
    print("amplihack-expert Skill Readiness Report")
    print("=" * 70)

    # File existence
    print("\nFile Structure:")
    for file_path, name in [
        (SKILL_FILE, "SKILL.md"),
        (REFERENCE_FILE, "reference.md"),
        (EXAMPLES_FILE, "examples.md"),
    ]:
        status = "✓ Exists" if file_path.exists() else "✗ Missing"
        print(f"  {name:20s}: {status}")

    if not all([SKILL_FILE.exists(), REFERENCE_FILE.exists(), EXAMPLES_FILE.exists()]):
        print("\n⚠ Not all files exist yet - skill is incomplete")
        print("=" * 70 + "\n")
        return

    # Token budget
    print("\nToken Budget:")
    skill_tokens = count_tokens(SKILL_FILE.read_text())
    reference_tokens = count_tokens(REFERENCE_FILE.read_text())
    examples_tokens = count_tokens(EXAMPLES_FILE.read_text())
    total_tokens = skill_tokens + reference_tokens + examples_tokens

    print(f"  SKILL.md:     {skill_tokens:4d} / {TOKEN_BUDGET['skill_md']} tokens")
    print(f"  reference.md: {reference_tokens:4d} / {TOKEN_BUDGET['reference_md']} tokens")
    print(f"  examples.md:  {examples_tokens:4d} / {TOKEN_BUDGET['examples_md']} tokens")
    print(f"  Total:        {total_tokens:4d} / {TOKEN_BUDGET['total']} tokens")

    # Philosophy compliance
    print("\nPhilosophy Compliance:")
    for file_path, name in [
        (SKILL_FILE, "SKILL.md"),
        (REFERENCE_FILE, "reference.md"),
        (EXAMPLES_FILE, "examples.md"),
    ]:
        content = file_path.read_text()
        score = calculate_simplicity_score(content)
        status = "✓" if score >= 85 else "✗"
        print(f"  {name:20s}: {status} {score:.1f}% simplicity score")

    # Overall readiness
    print("\n" + "=" * 70)
    all_budgets_ok = (
        skill_tokens <= TOKEN_BUDGET["skill_md"]
        and reference_tokens <= TOKEN_BUDGET["reference_md"]
        and examples_tokens <= TOKEN_BUDGET["examples_md"]
        and total_tokens <= TOKEN_BUDGET["total"]
    )

    metadata = extract_yaml_frontmatter(SKILL_FILE)
    yaml_ok = metadata is not None and "name" in metadata

    if all_budgets_ok and yaml_ok:
        print("✓ amplihack-expert skill is READY for use")
    else:
        print("✗ amplihack-expert skill needs adjustments")

    print("=" * 70 + "\n")


# ============================================================================
# Utility for Manual Testing
# ============================================================================


if __name__ == "__main__":
    # When run directly, execute tests with verbose output
    sys.exit(pytest.main([__file__, "-v", "--tb=short", "-s"]))
