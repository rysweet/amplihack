"""TDD validation tests for Issue #3939 deliverables.

Validates that all 5 files meet acceptance criteria:
1. .claude/skills/gherkin-expert/SKILL.md — skill definition
2. .claude/agents/amplihack/specialized/gherkin-expert.md — agent definition
3. .claude/agents/amplihack/specialized/prompt-writer.md — tri-path update
4. .claude/context/PATTERNS.md — formal spec pattern
5. amplifier-bundle/recipes/default-workflow.yaml — workflow guidance
"""

import os
from pathlib import Path

import pytest

# Base paths — resolve relative to repo root
# Navigate up from experiments/hive_mind/gherkin_v2_recipe_executor/reference/
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
AMPLIHACK_ROOT = Path(os.environ.get("AMPLIHACK_ROOT", Path.home() / ".amplihack"))

SKILL_PATH = AMPLIHACK_ROOT / ".claude/skills/gherkin-expert/SKILL.md"
AGENT_PATH = AMPLIHACK_ROOT / ".claude/agents/amplihack/specialized/gherkin-expert.md"
PROMPT_WRITER_PATH = AMPLIHACK_ROOT / ".claude/agents/amplihack/specialized/prompt-writer.md"
PATTERNS_PATH = AMPLIHACK_ROOT / ".claude/context/PATTERNS.md"
WORKFLOW_PATH = REPO_ROOT / "amplifier-bundle/recipes/default-workflow.yaml"


def read_file(path: Path) -> str:
    assert path.exists(), f"File not found: {path}"
    return path.read_text()


# ======================================================================
# Deliverable 1: SKILL.md
# ======================================================================


class TestGherkinExpertSkill:
    """Validates .claude/skills/gherkin-expert/SKILL.md"""

    @pytest.fixture(autouse=True)
    def load(self):
        self.content = read_file(SKILL_PATH)

    def test_file_exists(self):
        assert SKILL_PATH.exists()

    def test_has_frontmatter(self):
        assert self.content.startswith("---"), "Must start with YAML frontmatter"
        parts = self.content.split("---", 2)
        assert len(parts) >= 3, "Must have opening and closing --- for frontmatter"

    def test_frontmatter_has_name(self):
        assert "name: gherkin-expert" in self.content

    def test_frontmatter_has_agent_reference(self):
        assert "agent:" in self.content
        assert "gherkin-expert" in self.content

    def test_has_activation_keywords(self):
        assert "activation_keywords" in self.content

    def test_activation_includes_gherkin(self):
        assert "Gherkin" in self.content

    def test_activation_includes_bdd(self):
        assert "BDD" in self.content

    def test_activation_includes_given_when_then(self):
        assert "Given" in self.content and "When" in self.content and "Then" in self.content

    def test_describes_when_gherkin_adds_value(self):
        """Skill must communicate that Gherkin is a judgment call, not a rule."""
        lower = self.content.lower()
        assert "judgment" in lower or "judgement" in lower, (
            "Must state that Gherkin is a judgment call"
        )

    def test_includes_evidence(self):
        """Must cite empirical evidence for Gherkin effectiveness."""
        assert "0.898" in self.content or "+26%" in self.content, (
            "Must include Gherkin experiment results"
        )

    def test_english_is_acceptable_alternative(self):
        """Must make clear that English is fine for simple cases."""
        lower = self.content.lower()
        assert "english" in lower, "Must mention English as an alternative"
        # Either says "default" or "English is fine" — both communicate the same thing
        assert "default" in lower or "english is fine" in lower

    def test_includes_usage_examples(self):
        assert "/gherkin-expert" in self.content or "gherkin-expert" in self.content


# ======================================================================
# Deliverable 2: Agent definition
# ======================================================================


class TestGherkinExpertAgent:
    """Validates .claude/agents/amplihack/specialized/gherkin-expert.md"""

    @pytest.fixture(autouse=True)
    def load(self):
        self.content = read_file(AGENT_PATH)

    def test_file_exists(self):
        assert AGENT_PATH.exists()

    def test_has_frontmatter(self):
        assert self.content.startswith("---")

    def test_frontmatter_has_name(self):
        assert "name: gherkin-expert" in self.content

    def test_has_role(self):
        lower = self.content.lower()
        assert "gherkin" in lower and ("expert" in lower or "specialist" in lower)

    def test_covers_gherkin_syntax(self):
        """Agent must know Gherkin syntax: Feature, Scenario, Given/When/Then."""
        assert "Feature" in self.content
        assert "Scenario" in self.content
        assert "Given" in self.content

    def test_covers_scenario_outlines(self):
        assert "Scenario Outline" in self.content or "Examples" in self.content

    def test_covers_declarative_style(self):
        """Agent must teach declarative over imperative scenarios."""
        lower = self.content.lower()
        assert "declarative" in lower

    def test_covers_when_to_use_gherkin(self):
        """Must include guidance on when Gherkin is appropriate."""
        lower = self.content.lower()
        has_good_fit = "good fit" in lower or "worth" in lower or "consider" in lower
        has_overkill = "overkill" in lower or "english" in lower
        assert has_good_fit and has_overkill, (
            "Must cover both when to use and when not to use Gherkin"
        )

    def test_references_tla_plus_complement(self):
        """Must mention TLA+ as a complementary formalism."""
        assert "TLA+" in self.content

    def test_includes_anti_patterns(self):
        """Must warn against common Gherkin anti-patterns."""
        lower = self.content.lower()
        assert "anti-pattern" in lower or "bad" in lower or "wrong" in lower

    def test_includes_empirical_evidence(self):
        assert "0.898" in self.content or "0.713" in self.content

    def test_template_provided(self):
        """Must include a Gherkin scenario template."""
        assert "```gherkin" in self.content


# ======================================================================
# Deliverable 3: prompt-writer.md tri-path update
# ======================================================================


class TestPromptWriterTriPath:
    """Validates that prompt-writer.md has unified tri-path formal spec guidance."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.content = read_file(PROMPT_WRITER_PATH)

    def test_has_tri_path_section(self):
        """Must have a section about specification language judgment."""
        lower = self.content.lower()
        assert "tri-path" in lower or "path 1" in lower or "specification language" in lower

    def test_path1_english_default(self):
        """Path 1 must be English-only as default."""
        assert "English" in self.content
        lower = self.content.lower()
        assert "default" in lower

    def test_path2_gherkin(self):
        """Path 2 must cover Gherkin/BDD scenarios."""
        assert "Gherkin" in self.content
        assert "BDD" in self.content or "Given" in self.content

    def test_path3_tla_plus(self):
        """Path 3 must cover TLA+ formal predicates."""
        assert "TLA+" in self.content

    def test_gherkin_evidence(self):
        """Must cite Gherkin evidence."""
        assert "0.898" in self.content or "+26%" in self.content

    def test_tla_evidence(self):
        """Must cite TLA+ evidence."""
        assert "0.86" in self.content or "+51%" in self.content or "0.57" in self.content

    def test_judgment_indicators(self):
        """Must include guidance indicators for choosing the right path."""
        lower = self.content.lower()
        assert "judgment" in lower or "judgement" in lower

    def test_formal_specs_not_mandatory(self):
        """Must NOT present formal specs as mandatory."""
        lower = self.content.lower()
        # Check it says something like "judgment call" or "not a rule"
        has_optional = (
            "judgment call" in lower
            or "not a rule" in lower
            or "consider" in lower
            or "earn their place" in lower
        )
        assert has_optional


# ======================================================================
# Deliverable 4: PATTERNS.md formal spec pattern
# ======================================================================


class TestPatternsUpdate:
    """Validates that PATTERNS.md has the 'Formal Specification as Prompt' pattern."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.content = read_file(PATTERNS_PATH)

    def test_has_formal_spec_pattern(self):
        assert "Formal Specification as Prompt" in self.content

    def test_tla_evidence_table(self):
        """Must include TLA+ experiment results."""
        assert "tla_only" in self.content or "TLA+" in self.content
        assert "0.86" in self.content

    def test_gherkin_evidence_table(self):
        """Must include Gherkin experiment results."""
        assert "gherkin_only" in self.content
        assert "0.898" in self.content

    def test_domain_guidance(self):
        """Must include domain guidance for when to use each."""
        assert "Consider TLA+" in self.content or "TLA+ when" in self.content
        assert "Consider Gherkin" in self.content or "Gherkin when" in self.content

    def test_english_only_mentioned(self):
        """Must mention English-only as default."""
        assert "English-only" in self.content or "English only" in self.content

    def test_proportionality(self):
        """Must mention proportionality — only formalize when warranted."""
        lower = self.content.lower()
        assert "proportionality" in lower or "judgment" in lower


# ======================================================================
# Deliverable 5: default-workflow.yaml guidance
# ======================================================================


class TestWorkflowUpdate:
    """Validates that default-workflow.yaml has formal spec guidance."""

    @pytest.fixture(autouse=True)
    def load(self):
        self.content = read_file(WORKFLOW_PATH)

    def test_mentions_gherkin_in_design_step(self):
        """Design step should mention Gherkin as an option."""
        assert "Gherkin" in self.content

    def test_mentions_tla_in_design_step(self):
        """Design step should mention TLA+ as an option."""
        assert "TLA+" in self.content

    def test_judgment_call_framing(self):
        """Must frame as judgment call, not mandatory."""
        lower = self.content.lower()
        assert "judgment" in lower or "consider" in lower

    def test_references_patterns_md(self):
        """Should reference PATTERNS.md for evidence."""
        assert "PATTERNS.md" in self.content or "Formal Specification" in self.content

    def test_tdd_step_references_formal_specs(self):
        """TDD step should mention using formal specs for test derivation."""
        lower = self.content.lower()
        # The TDD step should mention deriving tests from specs
        assert "gherkin" in lower and ("test" in lower or "tdd" in lower)


# ======================================================================
# Cross-deliverable consistency
# ======================================================================


class TestCrossDeliverableConsistency:
    """Validates consistency across all 5 deliverables."""

    @pytest.fixture(autouse=True)
    def load_all(self):
        self.skill = read_file(SKILL_PATH)
        self.agent = read_file(AGENT_PATH)
        self.prompt_writer = read_file(PROMPT_WRITER_PATH)
        self.patterns = read_file(PATTERNS_PATH)
        self.workflow = read_file(WORKFLOW_PATH)

    def test_all_five_files_exist(self):
        """All 5 deliverable files must exist."""
        assert SKILL_PATH.exists()
        assert AGENT_PATH.exists()
        assert PROMPT_WRITER_PATH.exists()
        assert PATTERNS_PATH.exists()
        assert WORKFLOW_PATH.exists()

    def test_skill_references_agent(self):
        """Skill must reference the gherkin-expert agent."""
        assert "gherkin-expert" in self.skill

    def test_consistent_evidence_gherkin(self):
        """Gherkin evidence must appear in skill, agent, prompt-writer, and patterns."""
        for name, content in [
            ("skill", self.skill),
            ("agent", self.agent),
            ("prompt_writer", self.prompt_writer),
            ("patterns", self.patterns),
        ]:
            assert "0.898" in content or "+26%" in content, f"{name} must cite Gherkin evidence"

    def test_consistent_judgment_framing(self):
        """All files must frame formal specs as judgment call, not rule."""
        for name, content in [
            ("skill", self.skill),
            ("agent", self.agent),
            ("prompt_writer", self.prompt_writer),
        ]:
            lower = content.lower()
            has_judgment = (
                "judgment" in lower
                or "judgement" in lower
                or "not a rule" in lower
                or "consider" in lower
            )
            assert has_judgment, f"{name} must frame formal specs as optional/judgment"

    def test_no_mandatory_language(self):
        """No deliverable should use 'MUST use Gherkin' or 'always use TLA+'."""
        for name, content in [
            ("skill", self.skill),
            ("agent", self.agent),
            ("prompt_writer", self.prompt_writer),
            ("workflow", self.workflow),
        ]:
            lower = content.lower()
            assert "must use gherkin" not in lower, f"{name} should NOT say 'must use Gherkin'"
            assert "always use tla" not in lower, f"{name} should NOT say 'always use TLA+'"
