"""Cross-component orchestration integration tests for issue #4081.

Verifies handoff correctness between three components:
1. smart-orchestrator.yaml - Routes to default-workflow or investigation-workflow
2. default-workflow.yaml - 23-step workflow with worktree isolation
3. orchestrator.py - Parallel workstream orchestration (multitask)

PR #4101 integrated worktree isolation, resumable timeouts, and import scope
validation. These tests verify that orchestration routing, context propagation,
and worktree path handling are correct across all three components.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
RECIPES_DIR = REPO_ROOT / "amplifier-bundle" / "recipes"
SMART_ORCH_PATH = RECIPES_DIR / "smart-orchestrator.yaml"
DEFAULT_WF_PATH = RECIPES_DIR / "default-workflow.yaml"
ORCHESTRATOR_PATH = REPO_ROOT / ".claude" / "skills" / "multitask" / "orchestrator.py"
TOOLS_DIR = REPO_ROOT / "amplifier-bundle" / "tools"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

sys.path.insert(0, str(TOOLS_DIR))


def _load_yaml(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def _load_orchestrator_module():
    spec = importlib.util.spec_from_file_location("multitask_orchestrator", ORCHESTRATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _get_steps(recipe: dict) -> list[dict]:
    return recipe.get("steps", [])


def _find_step(steps: list[dict], step_id: str) -> dict | None:
    for s in steps:
        if s.get("id") == step_id:
            return s
    return None


# ---------------------------------------------------------------------------
# 1. Smart-orchestrator routes to default-workflow with correct context
# ---------------------------------------------------------------------------


class TestSmartOrchestratorRouting:
    """Verify smart-orchestrator correctly routes to default-workflow."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.recipe = _load_yaml(SMART_ORCH_PATH)
        self.steps = _get_steps(self.recipe)

    def test_single_development_routes_to_default_workflow(self):
        """Single Development workstream must route to default-workflow recipe."""
        step = _find_step(self.steps, "execute-single-round-1-development")
        assert step is not None, "execute-single-round-1-development step missing"
        assert step.get("recipe") == "default-workflow"
        assert step.get("type") == "recipe"

    def test_single_investigation_routes_to_investigation_workflow(self):
        """Single Investigation workstream must route to investigation-workflow."""
        step = _find_step(self.steps, "execute-single-round-1-investigation")
        assert step is not None, "execute-single-round-1-investigation step missing"
        assert step.get("recipe") == "investigation-workflow"

    def test_blocked_development_falls_back_to_default_workflow(self):
        """When recursion guard blocks parallel, fallback must use default-workflow."""
        step = _find_step(self.steps, "execute-single-fallback-blocked-development")
        assert step is not None, "execute-single-fallback-blocked-development step missing"
        assert step.get("recipe") == "default-workflow"
        cond = step.get("condition", "")
        assert "'BLOCKED' in recursion_guard" in cond

    def test_blocked_investigation_falls_back_to_investigation_workflow(self):
        """When recursion guard blocks parallel, investigation falls back correctly."""
        step = _find_step(self.steps, "execute-single-fallback-blocked-investigation")
        assert step is not None
        assert step.get("recipe") == "investigation-workflow"

    def test_context_variables_declared_for_default_workflow(self):
        """smart-orchestrator must declare task_description and repo_path in context."""
        ctx = self.recipe.get("context", {})
        assert "task_description" in ctx, "task_description not in smart-orchestrator context"
        assert "repo_path" in ctx, "repo_path not in smart-orchestrator context"

    def test_development_condition_handles_int_and_str_workstream_count(self):
        """Condition must handle workstream_count as both int 1 and string '1'."""
        step = _find_step(self.steps, "execute-single-round-1-development")
        cond = step["condition"]
        # Must compare against both int 1 and string '1' (fix #3606)
        assert "workstream_count == 1" in cond
        assert "workstream_count == '1'" in cond

    def test_detect_execution_gap_step_exists(self):
        """Adaptive error recovery must exist for when no execution path fires."""
        step = _find_step(self.steps, "detect-execution-gap")
        assert step is not None, "detect-execution-gap step missing"
        cond = step.get("condition", "")
        assert "not round_1_result" in cond

    def test_adaptive_fallback_routes_to_correct_recipe(self):
        """Adaptive fallback after execution gap must select correct recipe."""
        # The adaptive fallback step after detect-execution-gap
        # Check that adaptive_recipe routing exists
        found_adaptive = False
        for step in self.steps:
            cond = step.get("condition", "")
            if "adaptive_recipe" in cond and step.get("type") == "recipe":
                found_adaptive = True
                break
        assert found_adaptive, "No adaptive recipe fallback step found"


# ---------------------------------------------------------------------------
# 2. Default-workflow worktree setup produces correct structured output
# ---------------------------------------------------------------------------


class TestDefaultWorkflowWorktree:
    """Verify default-workflow worktree handling is correct for orchestrator use."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.recipe = _load_yaml(DEFAULT_WF_PATH)
        self.steps = _get_steps(self.recipe)

    def test_worktree_path_in_context(self):
        """default-workflow must declare worktree_path in its context block."""
        ctx = self.recipe.get("context", {})
        assert "worktree_path" in ctx

    def test_step_04_outputs_worktree_setup_json(self):
        """step-04-setup-worktree must output structured JSON with worktree_path."""
        step = _find_step(self.steps, "step-04-setup-worktree")
        assert step is not None, "step-04-setup-worktree missing"
        assert step.get("output") == "worktree_setup"
        assert step.get("parse_json") is True

    def test_step_04_json_contains_required_fields(self):
        """The bash script in step-04 must output worktree_path and branch_name."""
        step = _find_step(self.steps, "step-04-setup-worktree")
        command = step.get("command", "")
        # The heredoc JSON must contain these keys
        assert '"worktree_path"' in command
        assert '"branch_name"' in command
        assert '"created"' in command

    def test_downstream_steps_use_worktree_path(self):
        """Steps after worktree setup must use worktree_setup.worktree_path for cd."""
        step_ids_using_worktree = []
        for step in self.steps:
            cmd = step.get("command", "")
            prompt = step.get("prompt", "")
            if "worktree_setup.worktree_path" in cmd or "worktree_setup" in prompt:
                step_ids_using_worktree.append(step.get("id"))

        # At minimum: commit, PR creation, push steps must use worktree path
        assert len(step_ids_using_worktree) >= 5, (
            f"Only {len(step_ids_using_worktree)} steps reference worktree_setup, "
            f"expected at least 5: {step_ids_using_worktree}"
        )

    def test_worktree_fallback_to_repo_path(self):
        """Steps must fall back to repo_path when worktree is unavailable."""
        # Several bash steps use: cd {{worktree_setup.worktree_path}} 2>/dev/null || cd {{repo_path}}
        fallback_count = 0
        for step in self.steps:
            cmd = step.get("command", "")
            if "worktree_setup.worktree_path" in cmd and "repo_path" in cmd:
                fallback_count += 1
        assert fallback_count >= 2, (
            f"Only {fallback_count} steps have worktree -> repo_path fallback, expected >= 2"
        )

    def test_step_04_idempotency_guards(self):
        """Worktree setup must handle existing branch/worktree idempotently."""
        step = _find_step(self.steps, "step-04-setup-worktree")
        command = step.get("command", "")
        # Three-state guard from fix #3023
        assert "BRANCH_EXISTS" in command
        assert "WORKTREE_EXISTS" in command
        assert "CREATED=false" in command  # reuse path
        assert "CREATED=true" in command  # create path


# ---------------------------------------------------------------------------
# 3. Multitask orchestrator context propagation
# ---------------------------------------------------------------------------


class TestMultitaskOrchestratorContextPropagation:
    """Verify multitask orchestrator passes correct context to child workflows."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mod = _load_orchestrator_module()

    def test_recipe_launcher_passes_task_description(self, tmp_path):
        """Generated launcher must pass task_description to run_recipe_by_name."""
        ws = self.mod.Workstream(
            issue=42,
            branch="fix/test-branch",
            description="Test workstream",
            task="Implement feature X with proper error handling",
            recipe="default-workflow",
        )
        ws.work_dir = tmp_path / "ws-42"
        ws.work_dir.mkdir()
        ws.log_file = tmp_path / "log-42.txt"

        orch = self.mod.ParallelOrchestrator(
            repo_url="https://example.invalid/repo.git",
            tmp_base=str(tmp_path),
        )
        orch._write_recipe_launcher(ws)

        launcher = (ws.work_dir / "launcher.py").read_text()
        assert "task_description" in launcher
        assert "Implement feature X with proper error handling" in launcher

    def test_recipe_launcher_passes_repo_path(self, tmp_path):
        """Generated launcher must pass repo_path to run_recipe_by_name."""
        ws = self.mod.Workstream(
            issue=43,
            branch="fix/test-branch",
            description="Test",
            task="Test task",
            recipe="default-workflow",
        )
        ws.work_dir = tmp_path / "ws-43"
        ws.work_dir.mkdir()
        ws.log_file = tmp_path / "log-43.txt"

        orch = self.mod.ParallelOrchestrator(
            repo_url="https://example.invalid/repo.git",
            tmp_base=str(tmp_path),
        )
        orch._write_recipe_launcher(ws)

        launcher = (ws.work_dir / "launcher.py").read_text()
        assert '"repo_path": "."' in launcher

    def test_recipe_launcher_uses_specified_recipe(self, tmp_path):
        """Generated launcher must use the workstream's recipe, not hardcoded default."""
        ws = self.mod.Workstream(
            issue=44,
            branch="fix/test-branch",
            description="Investigation task",
            task="Research architecture",
            recipe="investigation-workflow",
        )
        ws.work_dir = tmp_path / "ws-44"
        ws.work_dir.mkdir()
        ws.log_file = tmp_path / "log-44.txt"

        orch = self.mod.ParallelOrchestrator(
            repo_url="https://example.invalid/repo.git",
            tmp_base=str(tmp_path),
        )
        orch._write_recipe_launcher(ws)

        launcher = (ws.work_dir / "launcher.py").read_text()
        assert "investigation-workflow" in launcher

    def test_shell_wrapper_propagates_session_tree_context(self, tmp_path):
        """run.sh must set AMPLIHACK_TREE_ID and AMPLIHACK_SESSION_DEPTH."""
        ws = self.mod.Workstream(
            issue=45,
            branch="fix/test-branch",
            description="Test",
            task="Test task",
            recipe="default-workflow",
        )
        ws.work_dir = tmp_path / "ws-45"
        ws.work_dir.mkdir()
        ws.log_file = tmp_path / "log-45.txt"

        orch = self.mod.ParallelOrchestrator(
            repo_url="https://example.invalid/repo.git",
            tmp_base=str(tmp_path),
        )
        orch._write_recipe_launcher(ws)

        run_sh = (ws.work_dir / "run.sh").read_text()
        assert "AMPLIHACK_TREE_ID" in run_sh
        assert "AMPLIHACK_SESSION_DEPTH" in run_sh

    def test_shell_wrapper_increments_session_depth(self, tmp_path):
        """Child workstreams must have depth = parent_depth + 1."""
        ws = self.mod.Workstream(
            issue=46,
            branch="fix/test-branch",
            description="Test",
            task="Test task",
        )
        ws.work_dir = tmp_path / "ws-46"
        ws.work_dir.mkdir()
        ws.log_file = tmp_path / "log-46.txt"

        with patch.dict("os.environ", {"AMPLIHACK_SESSION_DEPTH": "2"}):
            orch = self.mod.ParallelOrchestrator(
                repo_url="https://example.invalid/repo.git",
                tmp_base=str(tmp_path),
            )
            orch._write_recipe_launcher(ws)

        run_sh = (ws.work_dir / "run.sh").read_text()
        # Parent depth is 2, child must be 3
        # The shell wrapper uses unquoted export (export VAR=val)
        assert "AMPLIHACK_SESSION_DEPTH=3" in run_sh

    def test_add_workstream_creates_work_dir(self, tmp_path):
        """add_workstream must create the work directory."""
        orch = self.mod.ParallelOrchestrator(
            repo_url="https://example.invalid/repo.git",
            tmp_base=str(tmp_path),
        )
        ws = orch.add_workstream(
            issue=47,
            branch="fix/test",
            description="Test",
            task="Test task",
        )
        assert ws.work_dir.exists()
        assert ws.work_dir == tmp_path / "ws-47"

    def test_workstream_default_recipe_is_default_workflow(self):
        """Workstream default recipe must be 'default-workflow'."""
        ws = self.mod.Workstream(
            issue=1,
            branch="test",
            description="test",
            task="test",
        )
        assert ws.recipe == "default-workflow"


# ---------------------------------------------------------------------------
# 4. Task routing edge cases
# ---------------------------------------------------------------------------


class TestRoutingEdgeCases:
    """Test orchestration handoff edge cases: missing context, invalid paths."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.smart_orch = _load_yaml(SMART_ORCH_PATH)
        self.default_wf = _load_yaml(DEFAULT_WF_PATH)

    def test_smart_orchestrator_requires_nonempty_task_description(self):
        """smart-orchestrator must validate task_description is nonempty."""
        validation = self.smart_orch.get("context_validation", {})
        assert validation.get("task_description") == "nonempty"

    def test_smart_orchestrator_requires_git_repo(self):
        """smart-orchestrator must validate repo_path is a git repo."""
        validation = self.smart_orch.get("context_validation", {})
        assert validation.get("repo_path") == "git_repo"

    def test_preflight_checks_task_description_empty(self):
        """Preflight bash step must reject empty task_description."""
        step = _find_step(_get_steps(self.smart_orch), "preflight-validation")
        assert step is not None
        cmd = step.get("command", "")
        assert "task_description" in cmd or "TASK" in cmd

    def test_workstream_count_empty_treated_as_single(self):
        """When workstream_count is empty string, treat as single workstream."""
        step = _find_step(_get_steps(self.smart_orch), "execute-single-round-1-development")
        cond = step["condition"]
        assert "workstream_count == ''" in cond

    def test_default_workflow_context_has_all_output_fields(self):
        """default-workflow must declare all expected output context variables."""
        ctx = self.default_wf.get("context", {})
        required_outputs = [
            "worktree_path",
            "branch_name",
            "issue_number",
            "pr_url",
            "implementation",
        ]
        for field in required_outputs:
            assert field in ctx, f"Missing output context field: {field}"

    def test_orchestrator_safe_log_path_sanitizes_traversal(self, tmp_path):
        """Log path must sanitize traversal characters into underscores."""
        mod = _load_orchestrator_module()
        orch = mod.ParallelOrchestrator(
            repo_url="https://example.invalid/repo.git",
            tmp_base=str(tmp_path),
        )
        orch.tmp_base = tmp_path
        # Normal case works
        path = orch._safe_log_path(42)
        assert str(path).startswith(str(tmp_path.resolve()))

        # Traversal characters are sanitized to underscores by _SAFE_ID_RE,
        # so "../../etc/passwd" becomes "______etc_passwd" - stays within tmp_base
        path = orch._safe_log_path("../../etc/passwd")
        assert str(path).startswith(str(tmp_path.resolve()))
        assert ".." not in path.name

    def test_orchestrator_rejects_negative_issue_number(self):
        """add() must reject non-positive issue numbers."""
        mod = _load_orchestrator_module()
        orch = mod.ParallelOrchestrator(
            repo_url="https://example.invalid/repo.git",
        )
        with pytest.raises(ValueError, match="Invalid issue number"):
            orch.add(issue=-1, branch="b", description="d", task="t")

    def test_valid_delegates_is_frozen(self):
        """VALID_DELEGATES must be a frozenset (immutable)."""
        mod = _load_orchestrator_module()
        assert isinstance(mod.VALID_DELEGATES, frozenset)
        assert len(mod.VALID_DELEGATES) >= 2

    def test_smart_orchestrator_recursion_guard_exists(self):
        """Recursion guard step must exist to prevent infinite nesting."""
        step = _find_step(_get_steps(self.smart_orch), "derive-recursion-guard")
        assert step is not None, "derive-recursion-guard step missing from smart-orchestrator"

    def test_default_workflow_recursion_limits(self):
        """default-workflow must set recursion limits."""
        recursion = self.default_wf.get("recursion", {})
        assert recursion.get("max_depth", 0) > 0
        assert recursion.get("max_total_steps", 0) > 0


# ---------------------------------------------------------------------------
# 5. Cross-component contract verification
# ---------------------------------------------------------------------------


class TestCrossComponentContracts:
    """Verify the contracts between smart-orchestrator and default-workflow match."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.smart_orch = _load_yaml(SMART_ORCH_PATH)
        self.default_wf = _load_yaml(DEFAULT_WF_PATH)

    def test_context_keys_compatible(self):
        """Keys smart-orchestrator provides must be accepted by default-workflow."""
        orch_ctx = set(self.smart_orch.get("context", {}).keys())
        wf_ctx = set(self.default_wf.get("context", {}).keys())
        # These are the keys that must flow from orchestrator to workflow
        required_shared = {"task_description", "repo_path"}
        assert required_shared.issubset(orch_ctx), (
            f"smart-orchestrator missing: {required_shared - orch_ctx}"
        )
        assert required_shared.issubset(wf_ctx), (
            f"default-workflow missing: {required_shared - wf_ctx}"
        )

    def test_recipe_steps_reference_only_declared_recipes(self):
        """All recipe-type steps must reference known recipe files."""
        known_recipes = {p.stem for p in RECIPES_DIR.glob("*.yaml")}
        for step in _get_steps(self.smart_orch):
            if step.get("type") == "recipe":
                recipe_name = step.get("recipe", "")
                assert recipe_name in known_recipes, (
                    f"Step {step.get('id')} references unknown recipe: {recipe_name}"
                )

    def test_workstream_config_matches_default_workflow_expectations(self):
        """Workstream config created by smart-orchestrator must include recipe field."""
        # The create-workstreams-config step builds JSON with recipe field
        step = _find_step(_get_steps(self.smart_orch), "create-workstreams-config")
        if step is not None:
            cmd = step.get("command", "")
            assert '"recipe"' in cmd or "'recipe'" in cmd

    def test_all_worktree_cd_commands_are_safe(self):
        """All cd commands using worktree_path must be quoted or have fallback."""
        unsafe_count = 0
        for step in _get_steps(self.default_wf):
            cmd = step.get("command", "")
            if "worktree_setup.worktree_path" in cmd:
                lines = cmd.split("\n")
                for line in lines:
                    if "worktree_setup.worktree_path" in line and "cd " in line:
                        # Acceptable patterns:
                        # 1. cd "{{...}}" (quoted)
                        # 2. cd {{...}} 2>/dev/null (fallback on failure)
                        # 3. cd {{...}} && (chained - inline with other commands)
                        is_quoted = 'cd "{{' in line
                        has_fallback = "2>/dev/null" in line
                        is_chained = "&&" in line
                        if not (is_quoted or has_fallback or is_chained):
                            unsafe_count += 1
        assert unsafe_count == 0, f"{unsafe_count} unsafe cd commands found"
