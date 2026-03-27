"""TDD tests for GitHub issue #3638: quality-audit-cycle recipe bugs.

Three bugs:
1. seek agent cannot find target files — missing repo_path context var and
   working_dir on agent steps that access the filesystem.
2. verify-fixes and accumulate-history bash steps use bare assignments for
   multi-line JSON template variables, causing shell interpretation errors.
3. SKILL.md uses wrong invocation pattern (amplihack recipe execute vs
   run_recipe_by_name).

These tests are written BEFORE the fix so they initially FAIL, then PASS
once the recipe YAML and SKILL.md are corrected.

References: #3638, #3046 (heredoc safety), #3002 (working_dir forwarding)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
RECIPE_PATH = REPO_ROOT / "amplifier-bundle" / "recipes" / "quality-audit-cycle.yaml"
SKILL_PATHS = [
    REPO_ROOT / "amplifier-bundle" / "skills" / "quality-audit" / "SKILL.md",
    REPO_ROOT / ".claude" / "skills" / "quality-audit" / "SKILL.md",
    REPO_ROOT / "docs" / "claude" / "skills" / "quality-audit" / "SKILL.md",
]

# Agent steps that need filesystem access (read/write files)
FILESYSTEM_AGENT_STEPS = [
    "seek",
    "validate-agent-1",
    "validate-agent-2",
    "validate-agent-3",
    "fix",
    "summary",
    "self-improvement",
]

# Bash steps that receive multi-line JSON via template variables
JSON_BASH_STEPS = {
    "verify-fixes": ["validated_findings", "fix_results"],
    "accumulate-history": ["validated_findings", "cycle_history"],
}

# Scalar-only template vars that are safe for bare assignment
SAFE_SCALAR_VARS = {
    "cycle_number",
    "min_cycles",
    "max_cycles",
    "fix_all_per_cycle",
}


@pytest.fixture(scope="session")
def recipe():
    """Load the quality-audit-cycle recipe as parsed YAML (session-scoped)."""
    with open(RECIPE_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="session")
def recipe_text():
    """Load the raw recipe text for pattern matching (session-scoped)."""
    return RECIPE_PATH.read_text()


@pytest.fixture(scope="session")
def steps_by_id(recipe):
    """Build a dict of step_id -> step_dict for quick lookup (session-scoped)."""
    return {s["id"]: s for s in recipe["steps"]}


@pytest.fixture(scope="session")
def skill_texts():
    """Load all SKILL.md copies — session-scoped since files don't change."""
    texts = {}
    for p in SKILL_PATHS:
        if p.exists():
            texts[str(p.relative_to(REPO_ROOT))] = p.read_text()
    return texts


# ============================================================================
# BUG 1: Missing repo_path and working_dir (#3638 problem 1)
# ============================================================================


class TestBug1RepoPathContext:
    """repo_path must be in recipe context so agents resolve target_path."""

    def test_context_has_repo_path(self, recipe):
        """Recipe context must declare repo_path with a sensible default."""
        context = recipe.get("context", {})
        assert "repo_path" in context, (
            "Missing 'repo_path' in recipe context. The seek agent needs "
            "this to resolve target_path relative to the repository root. "
            "Add: repo_path: '.' to the context section."
        )

    def test_repo_path_default_is_dot(self, recipe):
        """repo_path should default to '.' (current directory)."""
        context = recipe.get("context", {})
        if "repo_path" in context:
            assert context["repo_path"] == ".", (
                f"repo_path should default to '.' (current dir), got '{context['repo_path']}'"
            )


class TestBug1WorkingDir:
    """Agent steps accessing the filesystem need working_dir set."""

    @pytest.mark.parametrize("step_id", FILESYSTEM_AGENT_STEPS)
    def test_agent_step_has_working_dir(self, steps_by_id, step_id):
        """Agent step '{step_id}' must have working_dir: '{{{{repo_path}}}}'."""
        step = steps_by_id.get(step_id)
        assert step is not None, f"Step '{step_id}' not found in recipe"
        assert step.get("working_dir") is not None, (
            f"Step '{step_id}' is missing 'working_dir'. Agent steps that "
            f"access the filesystem must set working_dir: '{{{{repo_path}}}}' "
            f"so target_path resolves correctly. (#3638 bug 1)"
        )

    @pytest.mark.parametrize("step_id", FILESYSTEM_AGENT_STEPS)
    def test_working_dir_references_repo_path(self, steps_by_id, step_id):
        """working_dir must use the {{repo_path}} template variable."""
        step = steps_by_id.get(step_id)
        if step is None:
            pytest.skip(f"Step '{step_id}' not found")
        working_dir = step.get("working_dir", "")
        assert "repo_path" in working_dir, (
            f"Step '{step_id}' working_dir should reference '{{{{repo_path}}}}', "
            f"got '{working_dir}'"
        )


class TestBug1AgentPromptRepoPath:
    """Agent prompts should include Repository path as defense-in-depth."""

    @pytest.mark.parametrize("step_id", FILESYSTEM_AGENT_STEPS)
    def test_prompt_references_repository_path(self, steps_by_id, step_id):
        """Prompt for '{step_id}' should mention repository path (defense-in-depth)."""
        step = steps_by_id.get(step_id)
        if step is None:
            pytest.skip(f"Step '{step_id}' not found")
        prompt = step.get("prompt", "")
        has_repo_ref = "repo_path" in prompt or "Repository" in prompt or "repository" in prompt
        assert has_repo_ref, (
            f"Step '{step_id}' prompt should reference the repository path "
            f"(e.g., '**Repository:** {{{{repo_path}}}}') as defense-in-depth "
            f"in case working_dir is not forwarded by the runner."
        )


# ============================================================================
# BUG 2: Bash quoting / heredoc safety (#3638 problem 2)
# ============================================================================


class TestBug2VerifyFixesHeredocSafety:
    """verify-fixes must use heredocs for multi-line JSON, not bare exports."""

    def test_no_bare_export_validated_findings(self, steps_by_id):
        """verify-fixes must NOT use 'export VALIDATED={{validated_findings}}'."""
        step = steps_by_id["verify-fixes"]
        command = step.get("command", "")
        # Bare export pattern: export VAR={{template}} on a single line
        # without heredoc wrapping
        bare_pattern = re.compile(r"export\s+VALIDATED\s*=\s*\{\{validated_findings\}\}")
        assert not bare_pattern.search(command), (
            "verify-fixes uses bare 'export VALIDATED={{validated_findings}}'. "
            "Multi-line JSON will break bash parsing. Use heredoc-to-tmpfile "
            "pattern (see recurse-decision step for reference). (#3638 bug 2)"
        )

    def test_no_bare_export_fix_results(self, steps_by_id):
        """verify-fixes must NOT use 'export FIX_RESULTS={{fix_results}}'."""
        step = steps_by_id["verify-fixes"]
        command = step.get("command", "")
        bare_pattern = re.compile(r"export\s+FIX_RESULTS\s*=\s*\{\{fix_results\}\}")
        assert not bare_pattern.search(command), (
            "verify-fixes uses bare 'export FIX_RESULTS={{fix_results}}'. "
            "Multi-line JSON will break bash parsing. Use heredoc-to-tmpfile "
            "pattern. (#3638 bug 2)"
        )

    def test_uses_heredoc_for_json_data(self, steps_by_id):
        """verify-fixes should use heredoc or tmpfile pattern for JSON."""
        step = steps_by_id["verify-fixes"]
        command = step.get("command", "")
        uses_heredoc = ("<<" in command and "EOF" in command) or "mktemp" in command
        assert uses_heredoc, (
            "verify-fixes should use heredoc (<<'EOF') or tmpfile (mktemp) "
            "pattern to safely pass multi-line JSON. See recurse-decision "
            "step for the correct pattern. (#3638 bug 2)"
        )

    def test_heredoc_delimiters_single_quoted(self, steps_by_id):
        """Heredoc delimiters must be single-quoted to prevent shell expansion."""
        step = steps_by_id["verify-fixes"]
        command = step.get("command", "")
        # Find all heredoc patterns: << DELIMITER or <<'DELIMITER' or <<"DELIMITER"
        heredocs = re.findall(r"<<\s*(\S+)", command)
        if not heredocs:
            pytest.skip("No heredocs found (test_uses_heredoc_for_json_data should catch this)")
        for delimiter in heredocs:
            # PYEOF is for the python script, not for JSON data — it's safe unquoted
            if delimiter.strip("'\"") == "PYEOF":
                continue
            # JSON-containing heredocs MUST be single-quoted
            is_quoted = delimiter.startswith("'") or delimiter.startswith('"')
            if (
                "validated" in command.split(delimiter)[0].lower()
                or "fix" in command.split(delimiter)[0].lower()
            ):
                assert is_quoted, (
                    f"Heredoc delimiter {delimiter} for JSON data must be "
                    f"single-quoted (<<'{delimiter}') to prevent shell expansion "
                    f"of content that may contain backticks or $() from adversarial "
                    f"codebase content. Security issue. (#3638 bug 2)"
                )


class TestBug2AccumulateHistoryHeredocSafety:
    """accumulate-history must use heredocs for multi-line JSON vars."""

    def test_no_bare_assignment_cycle_history(self, steps_by_id):
        """Must NOT use 'CURRENT_HISTORY={{cycle_history}}' bare."""
        step = steps_by_id["accumulate-history"]
        command = step.get("command", "")
        bare_pattern = re.compile(
            r"^CURRENT_HISTORY\s*=\s*\{\{cycle_history\}\}\s*$",
            re.MULTILINE,
        )
        assert not bare_pattern.search(command), (
            "accumulate-history uses bare 'CURRENT_HISTORY={{cycle_history}}'. "
            "Multi-line content will break bash. Use heredoc or tmpfile. "
            "(#3638 bug 2)"
        )

    def test_no_bare_assignment_validated_findings(self, steps_by_id):
        """Must NOT use 'FINDINGS={{validated_findings}}' bare."""
        step = steps_by_id["accumulate-history"]
        command = step.get("command", "")
        bare_pattern = re.compile(
            r"^FINDINGS\s*=\s*\{\{validated_findings\}\}\s*$",
            re.MULTILINE,
        )
        assert not bare_pattern.search(command), (
            "accumulate-history uses bare 'FINDINGS={{validated_findings}}'. "
            "Multi-line JSON will break bash. Use heredoc or tmpfile. "
            "(#3638 bug 2)"
        )

    def test_uses_heredoc_or_tmpfile(self, steps_by_id):
        """accumulate-history should use safe heredoc/tmpfile for JSON."""
        step = steps_by_id["accumulate-history"]
        command = step.get("command", "")
        uses_safe_pattern = (
            "<<" in command and ("EOF" in command or "HEREDOC" in command)
        ) or "mktemp" in command
        assert uses_safe_pattern, (
            "accumulate-history needs heredoc or tmpfile pattern for safely "
            "handling multi-line JSON variables. (#3638 bug 2)"
        )


class TestBug2ScalarVarsSafe:
    """Scalar vars (cycle_number, min/max_cycles) use quoted assignment."""

    def test_recurse_decision_scalars_are_quoted(self, steps_by_id):
        """recurse-decision uses quoted assignment for scalar vars (defense-in-depth)."""
        step = steps_by_id["recurse-decision"]
        command = step.get("command", "")
        # Quoted assignments for defense-in-depth (N5)
        assert 'CYCLE="{{cycle_number}}"' in command
        assert 'MIN_CYCLES="{{min_cycles}}"' in command
        assert 'MAX_CYCLES="{{max_cycles}}"' in command

    def test_recurse_decision_json_uses_heredoc(self, steps_by_id):
        """recurse-decision already uses heredoc for JSON — verify it stays."""
        step = steps_by_id["recurse-decision"]
        command = step.get("command", "")
        assert "mktemp" in command, "recurse-decision should use tmpfile pattern for JSON vars"
        assert "__AMPLIHACK_SAFE_HEREDOC_VALIDATED_" in command, (
            "recurse-decision heredoc for validated_findings not found"
        )

    def test_recurse_decision_heredocs_single_quoted(self, steps_by_id):
        """recurse-decision heredocs for JSON data must be single-quoted (#3638)."""
        step = steps_by_id["recurse-decision"]
        command = step.get("command", "")
        # Match heredocs (<<DELIM) but not here-strings (<<<)
        heredocs = re.findall(r"(?<!<)<<(?!<)\s*(\S+)", command)
        for delimiter in heredocs:
            if delimiter.strip("'\"") == "PYEOF":
                continue
            is_quoted = delimiter.startswith("'") or delimiter.startswith('"')
            assert is_quoted, (
                f"recurse-decision heredoc delimiter {delimiter} must be "
                f"single-quoted to prevent shell expansion of adversarial "
                f"codebase content. (#3638)"
            )


# ============================================================================
# BUG 3: SKILL.md wrong invocation pattern (#3638 problem 3)
# ============================================================================


class TestBug3SkillMdInvocation:
    """SKILL.md must use run_recipe_by_name(), not 'amplihack recipe execute'."""

    @pytest.mark.parametrize("skill_path", SKILL_PATHS, ids=lambda p: str(p.relative_to(REPO_ROOT)))
    def test_no_amplihack_recipe_execute(self, skill_path):
        """SKILL.md must NOT contain the stale 'amplihack recipe execute' pattern."""
        if not skill_path.exists():
            pytest.skip(f"{skill_path} does not exist")
        text = skill_path.read_text()
        assert "amplihack recipe execute" not in text, (
            f"{skill_path.relative_to(REPO_ROOT)} still uses the stale "
            f"'amplihack recipe execute' invocation. Must use "
            f"run_recipe_by_name('quality-audit-cycle', ...). (#3638 bug 3)"
        )

    @pytest.mark.parametrize("skill_path", SKILL_PATHS, ids=lambda p: str(p.relative_to(REPO_ROOT)))
    def test_uses_run_recipe_by_name(self, skill_path):
        """SKILL.md must contain run_recipe_by_name invocation."""
        if not skill_path.exists():
            pytest.skip(f"{skill_path} does not exist")
        text = skill_path.read_text()
        assert "run_recipe_by_name" in text, (
            f"{skill_path.relative_to(REPO_ROOT)} missing "
            f"run_recipe_by_name() invocation pattern. (#3638 bug 3)"
        )

    @pytest.mark.parametrize("skill_path", SKILL_PATHS, ids=lambda p: str(p.relative_to(REPO_ROOT)))
    def test_invocation_includes_recipe_name(self, skill_path):
        """run_recipe_by_name call must specify 'quality-audit-cycle'."""
        if not skill_path.exists():
            pytest.skip(f"{skill_path} does not exist")
        text = skill_path.read_text()
        assert "quality-audit-cycle" in text, (
            f"{skill_path.relative_to(REPO_ROOT)} must reference "
            f"'quality-audit-cycle' recipe name in invocation. (#3638 bug 3)"
        )

    @pytest.mark.parametrize("skill_path", SKILL_PATHS, ids=lambda p: str(p.relative_to(REPO_ROOT)))
    def test_invocation_includes_repo_path(self, skill_path):
        """Invocation example must include repo_path in user_context."""
        if not skill_path.exists():
            pytest.skip(f"{skill_path} does not exist")
        text = skill_path.read_text()
        assert "repo_path" in text, (
            f"{skill_path.relative_to(REPO_ROOT)} invocation example must "
            f"include 'repo_path' in user_context dict. (#3638 bug 3)"
        )


class TestBug3SkillMdConsistency:
    """All SKILL.md copies must be byte-identical."""

    def test_all_copies_identical(self):
        """All existing SKILL.md copies must have identical content."""
        existing = [(p, p.read_text()) for p in SKILL_PATHS if p.exists()]
        if len(existing) < 2:
            pytest.skip("Fewer than 2 SKILL.md copies found")
        first_path, first_text = existing[0]
        for other_path, other_text in existing[1:]:
            assert first_text == other_text, (
                f"SKILL.md copies differ:\n"
                f"  {first_path.relative_to(REPO_ROOT)}\n"
                f"  {other_path.relative_to(REPO_ROOT)}\n"
                f"Run: cp {first_path} {other_path}"
            )


# ============================================================================
# INTEGRATION: Recipe validates with recipe-runner-rs
# ============================================================================


class TestRecipeValidation:
    """Recipe must parse correctly through both Python and Rust validators."""

    def test_python_parser_accepts_recipe(self):
        """RecipeParser must parse quality-audit-cycle.yaml without errors."""
        from amplihack.recipes.parser import RecipeParser

        parser = RecipeParser()
        recipe = parser.parse_file(RECIPE_PATH)
        assert recipe.name == "quality-audit-cycle"
        assert len(recipe.steps) >= 10, f"Expected ≥10 steps, got {len(recipe.steps)}"

    def test_python_parser_no_warnings(self):
        """RecipeParser.validate() should produce no warnings."""
        from amplihack.recipes.parser import RecipeParser

        parser = RecipeParser()
        recipe = parser.parse_file(RECIPE_PATH)
        raw = RECIPE_PATH.read_text()
        warnings = parser.validate(recipe, raw_yaml=raw)
        assert warnings == [], f"Parser produced warnings: {warnings}"

    def test_all_agent_steps_have_prompts(self, recipe):
        """Every agent step must have a non-empty prompt."""
        for step in recipe["steps"]:
            if step.get("type") == "agent" or ("agent" in step and "command" not in step):
                assert step.get("prompt"), f"Agent step '{step['id']}' missing prompt"

    def test_all_steps_have_unique_ids(self, recipe):
        """Step IDs must be unique."""
        ids = [s["id"] for s in recipe["steps"]]
        assert len(ids) == len(set(ids)), (
            f"Duplicate step IDs: {[x for x in ids if ids.count(x) > 1]}"
        )

    def test_output_vars_declared_in_context(self, recipe):
        """Step output variables should be declared in context."""
        context_keys = set(recipe.get("context", {}).keys())
        for step in recipe["steps"]:
            output_var = step.get("output")
            if output_var:
                assert output_var in context_keys, (
                    f"Step '{step['id']}' output var '{output_var}' not declared in context section"
                )


class TestOutputTemplateVersion:
    """Bug 5: Output template version must match recipe header version."""

    def test_output_template_version_matches_header(self, recipe):
        """The footer version in the output template must match the recipe version."""
        header_version = recipe.get("version", "")
        output_template = recipe.get("output", {}).get("template", "")
        assert f"v{header_version}" in output_template, (
            f"Output template footer should contain 'v{header_version}' "
            f"but template is: {output_template[-80:]}"
        )

    def test_no_stale_v3_version_in_output(self, recipe):
        """Output template must not contain stale v3.0.0 reference."""
        output_template = recipe.get("output", {}).get("template", "")
        assert "v3.0.0" not in output_template, (
            "Output template still contains stale 'v3.0.0' — "
            "should be updated to match recipe header version"
        )
