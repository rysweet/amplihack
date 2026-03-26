"""Tests for recipe references in skill files.

Validates that all skill .md files use correct CLI verbs, valid recipe
identifiers, and accurate model field names — preventing regressions of
the "recipe execute" → "recipe run" fix and related recipe integration bugs.

Covers:
- CLI verb correctness (no "recipe execute")
- Referenced recipe YAML files exist in the bundle
- RecipeResult / StepResult / StepStatus field names match source
- Documentation accuracy (howto guide, index.md)
- Context argument syntax (-c key=value, not JSON)
- Recipe discovery via find_recipe()
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# All directories that may contain skill .md files
SKILL_DIRS = [
    REPO_ROOT / ".claude" / "skills",
    REPO_ROOT / "amplifier-bundle" / "skills",
    REPO_ROOT / "docs" / "claude" / "skills",
]

# Where bundled recipe YAML files live
RECIPE_BUNDLE_DIR = REPO_ROOT / "amplifier-bundle" / "recipes"

# Documentation files
HOWTO_DOC = REPO_ROOT / "docs" / "howto" / "invoke-recipes-from-skills.md"
INDEX_DOC = REPO_ROOT / "docs" / "index.md"


def _collect_skill_md_files() -> list[Path]:
    """Collect all .md files from all skill directories."""
    files: list[Path] = []
    for skill_dir in SKILL_DIRS:
        if skill_dir.is_dir():
            files.extend(skill_dir.rglob("*.md"))
    return files


def _collect_bundled_recipe_names() -> set[str]:
    """Return set of recipe names (without .yaml) from amplifier-bundle/recipes/."""
    names: set[str] = set()
    if RECIPE_BUNDLE_DIR.is_dir():
        for f in RECIPE_BUNDLE_DIR.glob("*.yaml"):
            names.add(f.stem)
        for f in RECIPE_BUNDLE_DIR.glob("*.yml"):
            names.add(f.stem)
    return names


# ---------------------------------------------------------------------------
# CLI Verb Correctness
# ---------------------------------------------------------------------------


class TestNoRecipeExecuteVerb:
    """Ensure no skill file uses the removed 'recipe execute' CLI verb."""

    @pytest.mark.unit
    def test_no_recipe_execute_in_skill_files(self):
        """All skill .md files must use 'recipe run', never 'recipe execute'."""
        violations: list[tuple[Path, int, str]] = []
        for md_file in _collect_skill_md_files():
            content = md_file.read_text(encoding="utf-8")
            for lineno, line in enumerate(content.splitlines(), start=1):
                if "recipe execute" in line.lower():
                    violations.append((md_file, lineno, line.strip()))

        assert violations == [], (
            f"Found {len(violations)} occurrence(s) of 'recipe execute' "
            f"(should be 'recipe run'):\n"
            + "\n".join(f"  {v[0].relative_to(REPO_ROOT)}:{v[1]}: {v[2]}" for v in violations)
        )

    @pytest.mark.unit
    def test_no_recipe_execute_in_documentation(self):
        """Documentation must not reference 'execute' as if it were valid.

        Lines in 'Common Mistakes' sections (❌ headings, 'Wrong' comments,
        comparison table 'Wrong' columns, and checklists) are intentional
        negative examples and are excluded.
        """
        for doc_path in [HOWTO_DOC, INDEX_DOC]:
            if not doc_path.exists():
                continue
            content = doc_path.read_text(encoding="utf-8")
            lines = content.splitlines()
            in_wrong_section = False
            lines_with_execute = []

            for lineno, line in enumerate(lines, start=1):
                # Track whether we're inside a "Common Mistakes" / ❌ section
                stripped = line.strip()
                if stripped.startswith("### ❌") or stripped.startswith("## Common Mistakes"):
                    in_wrong_section = True
                    continue
                if stripped.startswith("### ") and "❌" not in stripped:
                    in_wrong_section = False
                if stripped.startswith("## ") and "Common Mistakes" not in stripped:
                    in_wrong_section = False

                if "recipe execute" not in line.lower():
                    continue

                # Skip known negative-example contexts
                if in_wrong_section:
                    continue
                if any(
                    marker in line.lower()
                    for marker in [
                        "wrong",
                        "incorrect",
                        "❌",
                        "no `execute`",
                        "not `recipe execute`",
                        "# wrong",
                        "not a valid verb",
                        "checklist",
                    ]
                ):
                    continue
                # Table cells showing wrong usage (| Wrong | column)
                if "|" in line and "recipe run" in line:
                    continue
                # Checklist items warning against execute
                if line.strip().startswith("- [ ]") or line.strip().startswith("- [x]"):
                    continue

                lines_with_execute.append((doc_path, lineno, line.strip()))

            assert lines_with_execute == [], (
                "Documentation uses 'recipe execute' as if valid:\n"
                + "\n".join(
                    f"  {v[0].relative_to(REPO_ROOT)}:{v[1]}: {v[2]}" for v in lines_with_execute
                )
            )

    @pytest.mark.unit
    def test_cli_has_no_execute_subcommand(self):
        """The recipe CLI argparse must not define an 'execute' subcommand."""
        cli_path = REPO_ROOT / "src" / "amplihack" / "cli.py"
        assert cli_path.exists(), "cli.py not found"
        content = cli_path.read_text(encoding="utf-8")

        # Look for add_parser("execute") which would register the verb
        assert re.search(r'add_parser\(\s*["\']execute["\']', content) is None, (
            "CLI defines an 'execute' subcommand — only run/list/validate/show are valid"
        )

    @pytest.mark.unit
    def test_cli_defines_expected_subcommands(self):
        """The recipe CLI must define exactly run, list, validate, show."""
        cli_path = REPO_ROOT / "src" / "amplihack" / "cli.py"
        content = cli_path.read_text(encoding="utf-8")

        expected_verbs = {"run", "list", "validate", "show"}
        # Filter to recipe-related subparsers (near "recipe" parser)
        recipe_section = content[content.index('"recipe"') :]
        # Stop at next top-level subparser or EOF
        next_section_match = re.search(r"\nsubparsers\.add_parser\(", recipe_section[1:])
        if next_section_match:
            recipe_section = recipe_section[: next_section_match.start() + 1]
        recipe_verbs = set(re.findall(r'add_parser\(\s*["\'](\w+)["\']', recipe_section))

        assert expected_verbs.issubset(recipe_verbs), (
            f"Missing recipe verbs: {expected_verbs - recipe_verbs}. Found: {recipe_verbs}"
        )
        assert "execute" not in recipe_verbs, "'execute' should not be a recipe subcommand"


# ---------------------------------------------------------------------------
# Referenced Recipes Exist
# ---------------------------------------------------------------------------


class TestReferencedRecipesExist:
    """Verify that recipe names/files referenced in skills actually exist."""

    @pytest.mark.unit
    def test_quality_audit_cycle_recipe_exists(self):
        """The quality-audit-cycle recipe must exist in the bundle."""
        recipe_path = RECIPE_BUNDLE_DIR / "quality-audit-cycle.yaml"
        assert recipe_path.is_file(), f"quality-audit-cycle.yaml not found at {recipe_path}"

    @pytest.mark.unit
    def test_all_recipe_run_targets_exist(self):
        """Every 'amplihack recipe run <target>' in skills must reference a real recipe."""
        bundled_names = _collect_bundled_recipe_names()
        missing: list[tuple[Path, str]] = []

        pattern = re.compile(r"amplihack\s+recipe\s+run\s+(\S+)", re.IGNORECASE)
        for md_file in _collect_skill_md_files():
            content = md_file.read_text(encoding="utf-8")
            for match in pattern.finditer(content):
                target = match.group(1).rstrip("\\")
                # Strip .yaml extension if present for name-based lookup
                recipe_name = target.removesuffix(".yaml").removesuffix(".yml")
                if recipe_name not in bundled_names:
                    # Also check if it's a valid path relative to repo
                    target_path = REPO_ROOT / target
                    if not target_path.is_file():
                        missing.append((md_file.relative_to(REPO_ROOT), recipe_name))

        assert missing == [], (
            f"Skills reference {len(missing)} non-existent recipe(s):\n"
            + "\n".join(f"  {m[0]}: {m[1]}" for m in missing)
        )

    @pytest.mark.unit
    def test_recipe_bundle_dir_exists(self):
        """The amplifier-bundle/recipes/ directory must exist."""
        assert RECIPE_BUNDLE_DIR.is_dir(), f"Recipe bundle directory missing: {RECIPE_BUNDLE_DIR}"

    @pytest.mark.unit
    def test_recipe_bundle_has_recipes(self):
        """Bundle must contain at least one recipe YAML file."""
        recipes = list(RECIPE_BUNDLE_DIR.glob("*.yaml"))
        assert len(recipes) > 0, "No .yaml recipes found in bundle"


# ---------------------------------------------------------------------------
# Model Field Accuracy
# ---------------------------------------------------------------------------


class TestModelFieldAccuracy:
    """Verify model classes have the fields that docs and skills reference."""

    @pytest.mark.unit
    def test_recipe_result_has_expected_fields(self):
        """RecipeResult must have: recipe_name, success, step_results, context."""
        from amplihack.recipes.models import RecipeResult

        result = RecipeResult(recipe_name="test", success=True, step_results=[], context={})
        assert hasattr(result, "recipe_name")
        assert hasattr(result, "success")
        assert hasattr(result, "step_results")
        assert hasattr(result, "context")

    @pytest.mark.unit
    def test_recipe_result_does_not_have_stale_fields(self):
        """RecipeResult must NOT have old/removed field names."""
        from amplihack.recipes.models import RecipeResult

        result = RecipeResult(recipe_name="test", success=True)
        # These were incorrectly referenced in old documentation
        assert not hasattr(result, "steps_executed"), (
            "RecipeResult.steps_executed was removed — use step_results"
        )
        assert not hasattr(result, "failed_step"), (
            "RecipeResult.failed_step was removed — check step_results"
        )

    @pytest.mark.unit
    def test_step_result_uses_step_id_not_step_name(self):
        """StepResult must use 'step_id', not 'step_name'."""
        from amplihack.recipes.models import StepResult, StepStatus

        sr = StepResult(step_id="check-lint", status=StepStatus.COMPLETED)
        assert hasattr(sr, "step_id")
        assert not hasattr(sr, "step_name"), "StepResult.step_name is wrong — the field is step_id"

    @pytest.mark.unit
    def test_step_status_enum_values(self):
        """StepStatus must include FAILED (not FAILURE or ERROR)."""
        from amplihack.recipes.models import StepStatus

        expected_members = {"PENDING", "RUNNING", "COMPLETED", "SKIPPED", "FAILED"}
        actual_members = {m.name for m in StepStatus}
        assert expected_members.issubset(actual_members), (
            f"Missing StepStatus members: {expected_members - actual_members}"
        )
        # Ensure old/wrong names are not present
        assert "FAILURE" not in actual_members, "Use FAILED, not FAILURE"
        assert "ERROR" not in actual_members, "Use FAILED, not ERROR"

    @pytest.mark.unit
    def test_recipe_result_output_property(self):
        """RecipeResult.output must aggregate step outputs as a string."""
        from amplihack.recipes.models import RecipeResult, StepResult, StepStatus

        result = RecipeResult(
            recipe_name="test",
            success=True,
            step_results=[
                StepResult(step_id="s1", status=StepStatus.COMPLETED, output="hello"),
                StepResult(step_id="s2", status=StepStatus.COMPLETED, output="world"),
            ],
        )
        assert "hello" in result.output
        assert "world" in result.output

    @pytest.mark.unit
    def test_recipe_result_subscript(self):
        """RecipeResult supports subscripting (result[:N]) via __getitem__."""
        from amplihack.recipes.models import RecipeResult, StepResult, StepStatus

        result = RecipeResult(
            recipe_name="test",
            success=True,
            step_results=[
                StepResult(
                    step_id="s1",
                    status=StepStatus.COMPLETED,
                    output="a" * 100,
                ),
            ],
        )
        truncated = result[:10]
        assert len(truncated) == 10
        assert isinstance(truncated, str)


# ---------------------------------------------------------------------------
# Context Argument Syntax
# ---------------------------------------------------------------------------


class TestContextArgumentSyntax:
    """Verify skills use -c key=value syntax, not JSON."""

    @pytest.mark.unit
    def test_no_json_context_in_skills(self):
        """Skills must not use --context '{\"key\": \"value\"}' (JSON not supported)."""
        json_context_pattern = re.compile(r"--context\s+['\"]?\{", re.IGNORECASE)
        violations: list[tuple[Path, int, str]] = []
        for md_file in _collect_skill_md_files():
            content = md_file.read_text(encoding="utf-8")
            for lineno, line in enumerate(content.splitlines(), start=1):
                if json_context_pattern.search(line):
                    violations.append((md_file, lineno, line.strip()))

        assert violations == [], (
            "Found JSON --context syntax (use -c key=value instead):\n"
            + "\n".join(f"  {v[0].relative_to(REPO_ROOT)}:{v[1]}: {v[2]}" for v in violations)
        )

    @pytest.mark.unit
    def test_no_json_context_in_documentation(self):
        """Documentation must not show JSON --context syntax as correct usage.

        Lines inside ❌ / 'Common Mistakes' sections are negative examples
        and are excluded.
        """
        json_context_pattern = re.compile(r"--context\s+['\"]?\{", re.IGNORECASE)
        for doc_path in [HOWTO_DOC, INDEX_DOC]:
            if not doc_path.exists():
                continue
            content = doc_path.read_text(encoding="utf-8")
            lines = content.splitlines()
            in_wrong_section = False
            violations = []

            for lineno, line in enumerate(lines, start=1):
                stripped = line.strip()
                if stripped.startswith("### ❌") or stripped.startswith("## Common Mistakes"):
                    in_wrong_section = True
                    continue
                if stripped.startswith("### ") and "❌" not in stripped:
                    in_wrong_section = False
                if stripped.startswith("## ") and "Common Mistakes" not in stripped:
                    in_wrong_section = False

                if not json_context_pattern.search(line):
                    continue

                if in_wrong_section:
                    continue
                if any(
                    w in line.lower()
                    for w in ["wrong", "incorrect", "❌", "not supported", "# wrong"]
                ):
                    continue
                violations.append((lineno, line.strip()))

            assert violations == [], (
                f"{doc_path.relative_to(REPO_ROOT)} uses JSON context as if correct:\n"
                + "\n".join(f"  :{v[0]}: {v[1]}" for v in violations)
            )


# ---------------------------------------------------------------------------
# Recipe Discovery Integration
# ---------------------------------------------------------------------------


class TestRecipeDiscovery:
    """Verify recipe discovery finds bundled recipes by name."""

    @pytest.mark.unit
    def test_find_recipe_quality_audit_cycle(self):
        """find_recipe() must locate quality-audit-cycle in the bundle."""
        from amplihack.recipes.discovery import find_recipe

        result = find_recipe("quality-audit-cycle", search_dirs=[RECIPE_BUNDLE_DIR])
        assert result is not None, "find_recipe('quality-audit-cycle') returned None"
        assert result.name == "quality-audit-cycle.yaml"

    @pytest.mark.unit
    def test_find_recipe_returns_none_for_nonexistent(self):
        """find_recipe() must return None for missing recipes."""
        from amplihack.recipes.discovery import find_recipe

        result = find_recipe("this-recipe-does-not-exist-xyz", search_dirs=[RECIPE_BUNDLE_DIR])
        assert result is None

    @pytest.mark.unit
    def test_find_recipe_default_workflow(self):
        """find_recipe() must locate default-workflow in the bundle."""
        from amplihack.recipes.discovery import find_recipe

        result = find_recipe("default-workflow", search_dirs=[RECIPE_BUNDLE_DIR])
        assert result is not None
        assert result.name == "default-workflow.yaml"


# ---------------------------------------------------------------------------
# Documentation Accuracy
# ---------------------------------------------------------------------------


class TestDocumentationAccuracy:
    """Verify the howto doc matches actual CLI and model interfaces."""

    @pytest.mark.unit
    def test_howto_doc_exists(self):
        """invoke-recipes-from-skills.md must exist."""
        assert HOWTO_DOC.is_file(), f"Missing: {HOWTO_DOC}"

    @pytest.mark.unit
    def test_howto_shows_recipe_run_not_execute(self):
        """Howto doc must demonstrate 'recipe run' as the primary command."""
        content = HOWTO_DOC.read_text(encoding="utf-8")
        assert "recipe run" in content, "Howto doc should show 'recipe run' as the correct verb"

    @pytest.mark.unit
    def test_howto_documents_c_flag(self):
        """Howto doc must document -c as a context flag."""
        content = HOWTO_DOC.read_text(encoding="utf-8")
        assert "-c " in content or "-c\n" in content, (
            "Howto doc should document -c flag for context variables"
        )

    @pytest.mark.unit
    def test_howto_documents_context_flag(self):
        """Howto doc must document --context as alias for -c."""
        content = HOWTO_DOC.read_text(encoding="utf-8")
        assert "--context" in content, "Howto doc should document --context as alias for -c"

    @pytest.mark.unit
    def test_howto_uses_correct_step_result_fields(self):
        """Any Python examples in howto must use step_id, not step_name."""
        content = HOWTO_DOC.read_text(encoding="utf-8")
        # If the doc references StepResult fields, it must use step_id
        if "step_name" in content:
            pytest.fail("Howto doc uses 'step_name' — should be 'step_id'")

    @pytest.mark.unit
    def test_howto_uses_correct_step_status(self):
        """Any Python examples must use StepStatus.FAILED, not .FAILURE."""
        content = HOWTO_DOC.read_text(encoding="utf-8")
        if "StepStatus.FAILURE" in content:
            pytest.fail("Howto doc uses 'StepStatus.FAILURE' — should be 'StepStatus.FAILED'")

    @pytest.mark.unit
    def test_howto_uses_correct_recipe_result_fields(self):
        """Any Python examples must use step_results, not steps_executed."""
        content = HOWTO_DOC.read_text(encoding="utf-8")
        if "steps_executed" in content:
            pytest.fail("Howto doc uses 'steps_executed' — should be 'step_results'")

    @pytest.mark.unit
    def test_index_doc_recipe_section_uses_run(self):
        """index.md recipe quick-start must use 'recipe run'."""
        if not INDEX_DOC.exists():
            pytest.skip("index.md not found")
        content = INDEX_DOC.read_text(encoding="utf-8")
        if "recipe execute" in content.lower():
            # Allow in "wrong" examples
            lines = content.splitlines()
            for i, line in enumerate(lines):
                if "recipe execute" in line.lower():
                    if not any(w in line.lower() for w in ["wrong", "incorrect", "❌"]):
                        pytest.fail(f"index.md:{i + 1} uses 'recipe execute' as correct usage")


# ---------------------------------------------------------------------------
# CLI Context Parsing (unit)
# ---------------------------------------------------------------------------


class TestCLIContextParsing:
    """Verify parse_context_args handles -c key=value correctly."""

    @pytest.mark.unit
    def test_parse_context_single_pair(self):
        """parse_context_args must handle a single key=value."""
        from amplihack.recipe_cli.context import parse_context_args

        context, errors = parse_context_args([["target_path=src/amplihack"]])
        assert context == {"target_path": "src/amplihack"}
        assert errors == []

    @pytest.mark.unit
    def test_parse_context_multiple_pairs(self):
        """parse_context_args must handle multiple -c flags."""
        from amplihack.recipe_cli.context import parse_context_args

        context, errors = parse_context_args(
            [
                ["target_path=src/amplihack"],
                ["min_cycles=3"],
                ["max_cycles=6"],
            ]
        )
        assert context == {
            "target_path": "src/amplihack",
            "min_cycles": "3",
            "max_cycles": "6",
        }
        assert errors == []

    @pytest.mark.unit
    def test_parse_context_preserves_spaces(self):
        """parse_context_args must preserve spaces in values."""
        from amplihack.recipe_cli.context import parse_context_args

        context, errors = parse_context_args([["task=Fix bug (#123)"]])
        assert context["task"] == "Fix bug (#123)"
        assert errors == []

    @pytest.mark.unit
    def test_parse_context_empty_list(self):
        """parse_context_args must handle empty list (no -c flags)."""
        from amplihack.recipe_cli.context import parse_context_args

        context, errors = parse_context_args([])
        assert context == {}
        assert errors == []


# ---------------------------------------------------------------------------
# Skill-Recipe Consistency (integration)
# ---------------------------------------------------------------------------


class TestSkillRecipeConsistency:
    """Cross-cutting checks that skill files are consistent with the recipe system."""

    @pytest.mark.integration
    def test_run_recipe_by_name_only_in_python_blocks(self):
        """run_recipe_by_name must only appear in python code blocks, not bash."""
        # Match bash/shell blocks that contain run_recipe_by_name
        bash_pattern = re.compile(r"```(?:bash|shell|sh)\n(.*?)```", re.DOTALL)
        violations: list[tuple[Path, str]] = []
        for md_file in _collect_skill_md_files():
            content = md_file.read_text(encoding="utf-8")
            for m in bash_pattern.finditer(content):
                block = m.group(1)
                # Only flag if it looks like a bare shell invocation
                # (not a Python snippet pasted into a bash block)
                if "run_recipe_by_name" in block and "python" not in block.lower():
                    violations.append((md_file.relative_to(REPO_ROOT), block[:80].strip()))
        assert violations == [], (
            "Bash code blocks use SDK function run_recipe_by_name "
            "without Python context:\n" + "\n".join(f"  {v[0]}: {v[1]}" for v in violations)
        )

    @pytest.mark.integration
    def test_run_recipe_by_name_importable(self):
        """run_recipe_by_name must be importable from amplihack.recipes."""
        from amplihack.recipes import run_recipe_by_name

        assert callable(run_recipe_by_name)

    @pytest.mark.integration
    def test_run_recipe_by_name_accepts_expected_kwargs(self):
        """run_recipe_by_name signature must accept the kwargs skills rely on."""
        import inspect

        from amplihack.recipes import run_recipe_by_name

        sig = inspect.signature(run_recipe_by_name)
        params = set(sig.parameters.keys())
        expected = {"name", "user_context", "dry_run", "recipe_dirs", "working_dir"}
        assert expected.issubset(params), f"run_recipe_by_name missing params: {expected - params}"


# ---------------------------------------------------------------------------
# CLI Loader: Bare Name Resolution
# ---------------------------------------------------------------------------


class TestCLILoaderBareName:
    """Verify load_recipe_definition resolves bare recipe names via find_recipe."""

    @pytest.mark.integration
    def test_bare_name_resolves_to_bundled_recipe(self):
        """A bare recipe name like 'quality-audit-cycle' should resolve."""
        from amplihack.recipe_cli.loader import load_recipe_definition

        recipe, path = load_recipe_definition("quality-audit-cycle")
        assert path.is_file(), f"Resolved path does not exist: {path}"
        assert path.suffix == ".yaml"
        assert recipe.name == "quality-audit-cycle"

    @pytest.mark.integration
    def test_bare_name_default_workflow(self):
        """The default-workflow recipe should resolve by bare name."""
        from amplihack.recipe_cli.loader import load_recipe_definition

        recipe, path = load_recipe_definition("default-workflow")
        assert path.is_file()
        assert "default-workflow" in path.stem

    @pytest.mark.integration
    def test_full_path_still_works(self):
        """Explicit YAML paths must still work."""
        from amplihack.recipe_cli.loader import load_recipe_definition

        full_path = str(RECIPE_BUNDLE_DIR / "quality-audit-cycle.yaml")
        recipe, path = load_recipe_definition(full_path)
        assert path.is_file()

    @pytest.mark.unit
    def test_is_bare_recipe_name(self):
        """_is_bare_recipe_name correctly classifies inputs."""
        from amplihack.recipe_cli.loader import _is_bare_recipe_name

        assert _is_bare_recipe_name("quality-audit-cycle") is True
        assert _is_bare_recipe_name("default-workflow") is True
        assert _is_bare_recipe_name("quality-audit-cycle.yaml") is False
        assert _is_bare_recipe_name("path/to/recipe") is False
        assert _is_bare_recipe_name("/absolute/path") is False
