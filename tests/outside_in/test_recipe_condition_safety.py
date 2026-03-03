"""Outside-in tests for recipe file consistency and safe condition evaluation.

Verifies:
1. All recipe YAML conditions use only safe AST nodes (no function calls)
2. The repo root amplifier-bundle/recipes/ stays in sync with the package source
3. Recipe runner can load and evaluate all conditions without errors

Fixes issue #2828: stale repo root smart-orchestrator.yaml with broken conditions.
"""

import ast
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_BUNDLE_RECIPES = REPO_ROOT / "amplifier-bundle" / "recipes"
SRC_BUNDLE_RECIPES = REPO_ROOT / "src" / "amplihack" / "amplifier-bundle" / "recipes"

# AST node types allowed by the safe expression evaluator (from context.py)
SAFE_NODES = (
    ast.Expression,
    ast.Compare,
    ast.BoolOp,
    ast.And,
    ast.Or,
    ast.UnaryOp,
    ast.Not,
    ast.Name,
    ast.Attribute,
    ast.Constant,
    ast.Load,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.In,
    ast.NotIn,
    ast.Subscript,
    ast.Index,
)


def _collect_recipe_conditions(recipe_dir: Path) -> list[tuple[str, str, str]]:
    """Collect all condition expressions from recipe YAML files.

    Returns list of (recipe_name, step_id, condition_text).
    """
    conditions = []
    for yaml_path in sorted(recipe_dir.glob("*.yaml")):
        with open(yaml_path) as f:
            try:
                recipe = yaml.safe_load(f)
            except yaml.YAMLError:
                continue
        if not recipe or "steps" not in recipe:
            continue
        for step in recipe["steps"]:
            condition = step.get("condition", "").strip()
            if condition:
                conditions.append((yaml_path.stem, step.get("id", "?"), condition))
    return conditions


class TestRecipeConditionSafety:
    """All recipe conditions must use only safe AST nodes."""

    @pytest.fixture(params=["repo_root", "src"])
    def recipe_dir(self, request):
        """Test both recipe directories."""
        if request.param == "repo_root":
            return REPO_BUNDLE_RECIPES
        return SRC_BUNDLE_RECIPES

    def test_no_function_calls_in_conditions(self, recipe_dir):
        """No recipe condition should contain ast.Call nodes (function calls)."""
        if not recipe_dir.exists():
            pytest.skip(f"{recipe_dir} not found")

        violations = []
        for recipe_name, step_id, condition in _collect_recipe_conditions(recipe_dir):
            try:
                tree = ast.parse(condition, mode="eval")
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        violations.append(f"{recipe_name}/{step_id}: {condition[:80]}")
                        break
            except SyntaxError:
                violations.append(f"{recipe_name}/{step_id}: SYNTAX ERROR: {condition[:80]}")

        assert not violations, (
            "Recipe conditions contain function calls (unsafe for evaluator):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_all_conditions_use_safe_nodes_only(self, recipe_dir):
        """All AST nodes in conditions must be in the safe whitelist."""
        if not recipe_dir.exists():
            pytest.skip(f"{recipe_dir} not found")

        violations = []
        for recipe_name, step_id, condition in _collect_recipe_conditions(recipe_dir):
            try:
                tree = ast.parse(condition, mode="eval")
                for node in ast.walk(tree):
                    if not isinstance(node, SAFE_NODES):
                        violations.append(
                            f"{recipe_name}/{step_id}: unsafe node {type(node).__name__} in: {condition[:80]}"
                        )
                        break
            except SyntaxError:
                violations.append(f"{recipe_name}/{step_id}: SYNTAX ERROR: {condition[:80]}")

        assert not violations, "Recipe conditions contain unsafe AST nodes:\n" + "\n".join(
            f"  - {v}" for v in violations
        )


class TestRecipeFileSync:
    """Repo root and src/ recipe files must stay in sync."""

    def test_smart_orchestrator_in_sync(self):
        """smart-orchestrator.yaml must be identical in repo root and src/."""
        repo_copy = REPO_BUNDLE_RECIPES / "smart-orchestrator.yaml"
        src_copy = SRC_BUNDLE_RECIPES / "smart-orchestrator.yaml"

        if not repo_copy.exists() or not src_copy.exists():
            pytest.skip("One or both recipe copies not found")

        repo_content = repo_copy.read_text()
        src_content = src_copy.read_text()

        assert repo_content == src_content, (
            "smart-orchestrator.yaml is out of sync between "
            "amplifier-bundle/recipes/ and src/amplihack/amplifier-bundle/recipes/. "
            "The repo root copy is the development source; ensure fixes are applied there."
        )

    def test_all_recipes_in_sync(self):
        """All recipe files present in both locations must be identical."""
        if not REPO_BUNDLE_RECIPES.exists() or not SRC_BUNDLE_RECIPES.exists():
            pytest.skip("Recipe directories not found")

        repo_recipes = {f.name for f in REPO_BUNDLE_RECIPES.glob("*.yaml")}
        src_recipes = {f.name for f in SRC_BUNDLE_RECIPES.glob("*.yaml")}
        common = repo_recipes & src_recipes

        out_of_sync = []
        for name in sorted(common):
            repo_content = (REPO_BUNDLE_RECIPES / name).read_text()
            src_content = (SRC_BUNDLE_RECIPES / name).read_text()
            if repo_content != src_content:
                out_of_sync.append(name)

        assert not out_of_sync, (
            "Recipe files out of sync between repo root and src/:\n"
            + "\n".join(f"  - {f}" for f in out_of_sync)
        )


class TestRecipeRunnerConditionEval:
    """Recipe runner can evaluate all conditions without errors."""

    def test_smart_orchestrator_conditions_evaluate(self):
        """All smart-orchestrator conditions should evaluate without safety errors."""
        from amplihack.recipes.context import RecipeContext

        recipe_path = REPO_BUNDLE_RECIPES / "smart-orchestrator.yaml"
        if not recipe_path.exists():
            pytest.skip("smart-orchestrator.yaml not found")

        ctx = RecipeContext()
        # Set typical context variables
        ctx.set("task_type", "Development")
        ctx.set("workstream_count", "1")
        ctx.set("force_single_workstream", "false")
        ctx.set("recursion_guard", "ALLOWED")
        ctx.set("round_1_result", "")
        ctx.set("round_2_result", "")
        ctx.set("round_3_result", "")
        ctx.set("decomposition_json", "{}")

        safety_errors = []
        for _, step_id, condition in _collect_recipe_conditions(REPO_BUNDLE_RECIPES):
            try:
                ctx.evaluate(condition)
            except ValueError as e:
                # ValueError = safety violation (unsafe nodes, dunder access)
                safety_errors.append(f"{step_id}: {e}")
            except NameError:
                # NameError = missing variable — expected for steps that
                # depend on prior step outputs not in our test context
                pass

        assert not safety_errors, "Condition safety errors (unsafe AST nodes):\n" + "\n".join(
            f"  - {e}" for e in safety_errors
        )
