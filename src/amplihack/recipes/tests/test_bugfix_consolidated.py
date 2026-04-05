"""TDD tests for consolidated bugfix PR (issues #3551, #3548, #3291, #3298).

These tests define the contracts for each fix. They are written BEFORE the
implementation and should:
  - FAIL against the current (unfixed) codebase
  - PASS once all fixes are applied

Test proportionality: 4 bugs x ~3 tests each = ~12 tests total.
Testing pyramid: 100% unit/contract tests (no integration or E2E needed —
these are YAML content and shell behavior contracts).

Bug summary:
  #3551 — Branch name >200 chars silently fails gh CLI
  #3548 — classify-and-decompose recurses into dev-orchestrator
  #3291 — step-02c hangs on large context
  #3298 — SKILL.md documents outdated AMPLIHACK_HOME behavior
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="These tests require bash and Unix paths",
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[4]  # src/amplihack/recipes/tests -> repo root
DEFAULT_WORKFLOW = REPO_ROOT / "amplifier-bundle" / "recipes" / "default-workflow.yaml"
SMART_ORCHESTRATOR = REPO_ROOT / "amplifier-bundle" / "recipes" / "smart-orchestrator.yaml"
SKILL_MD = REPO_ROOT / ".claude" / "skills" / "dev-orchestrator" / "SKILL.md"


def _load_yaml(path: Path) -> dict:
    """Load a YAML recipe file."""
    content = path.read_text(encoding="utf-8")
    return yaml.safe_load(content)


def _find_step(recipe: dict, step_id: str) -> dict | None:
    """Find a step by ID in a recipe's steps list."""
    for step in recipe.get("steps", []):
        if step.get("id") == step_id:
            return step
    return None


# ===========================================================================
# BUG #3551: Branch name truncation guard
# ===========================================================================


class TestBranchNameTruncation:
    """Verify that assembled BRANCH_NAME is capped at 200 characters.

    Current behavior: slug is cut to 50 chars but the full
    `{{branch_prefix}}/issue-{{issue_number}}-<slug>` is not length-checked.
    gh CLI rejects branch names >~250 chars.

    Expected fix: After assembling BRANCH_NAME, if len > 200, truncate to
    200 chars, strip trailing hyphen, and emit a warning to stderr.
    """

    @staticmethod
    def _extract_branch_script() -> str:
        """Extract the branch assembly script from the actual YAML step-04.

        This ensures the test exercises the real truncation code path —
        if the YAML changes, the test automatically picks up the change.
        """
        content = DEFAULT_WORKFLOW.read_text(encoding="utf-8")
        recipe = yaml.safe_load(content)
        step04 = next(s for s in recipe["steps"] if s.get("id") == "step-04-setup-worktree")
        cmd = step04["command"]

        # Extract from TASK_SLUG assignment through BRANCH_NAME finalization.
        lines = cmd.split("\n")
        start = next(i for i, l in enumerate(lines) if "TASK_SLUG=$(" in l)
        # End at the line after the git-check-ref-format fallback block
        end = None
        depth = 0
        for i in range(start, len(lines)):
            line = lines[i].strip()
            if line.startswith("if ") and line.endswith("; then"):
                depth += 1
            if line == "fi":
                depth -= 1
                if depth <= 0:
                    end = i + 1
                    break
        assert end is not None, "Could not find end of branch assembly block in YAML"

        # Replace template vars with positional args for test invocation
        block = "\n".join(lines[start:end])
        block = block.replace("{{task_description}}", "$1")
        block = block.replace("{{branch_prefix}}", "$2")
        block = block.replace("{{issue_number}}", "$3")
        # Remove the heredoc TASK_DESC pattern (already handled by $1)
        script = textwrap.dedent(f"""\
            TASK_DESC="$1"
            {block}
            printf '%s' "$BRANCH_NAME"
        """)
        return script.strip()

    def _assemble_branch(
        self, task_desc: str, branch_prefix: str = "feat", issue_number: str = "42"
    ) -> tuple[str, str]:
        """Run the branch assembly pipeline extracted from the YAML and return (branch_name, stderr)."""
        script = self._extract_branch_script()
        result = subprocess.run(
            ["bash", "-c", script, "--", task_desc, branch_prefix, issue_number],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout, result.stderr

    def test_normal_branch_under_200_chars(self) -> None:
        """Normal branch names should be unaffected."""
        branch, _ = self._assemble_branch("fix login bug", "feat", "42")
        assert len(branch) <= 200
        assert "fix-login-bug" in branch

    def test_long_branch_prefix_exceeds_200_chars(self) -> None:
        """When branch_prefix is very long, total should be capped at 200.

        FAILS NOW: No total-length guard exists. The branch name will be
        >200 chars because branch_prefix alone is 180 chars.
        PASSES AFTER FIX: Truncation guard caps at 200.
        """
        long_prefix = "a" * 180  # 180 char prefix
        branch, stderr = self._assemble_branch("fix login bug", long_prefix, "42")
        # After fix: branch must be ≤200 chars
        assert len(branch) <= 200, (
            f"Branch name is {len(branch)} chars, exceeds 200-char limit: {branch[:80]}..."
        )

    def test_truncation_emits_warning(self) -> None:
        """When truncation occurs, a warning should appear on stderr.

        FAILS NOW: No warning is emitted because no truncation happens.
        PASSES AFTER FIX: Warning on stderr when branch name is truncated.
        """
        long_prefix = "a" * 180
        branch, stderr = self._assemble_branch("fix login bug", long_prefix, "42")
        assert "WARNING" in stderr or "truncat" in stderr.lower(), (
            f"Expected truncation warning on stderr, got: {stderr!r}"
        )

    def test_truncated_name_has_no_trailing_hyphen(self) -> None:
        """After truncation, the branch name must not end with a hyphen.

        FAILS NOW: No truncation code exists.
        PASSES AFTER FIX: Trailing hyphen stripped after truncation.
        """
        long_prefix = "a" * 180
        branch, _ = self._assemble_branch("fix-some-really-long-thing", long_prefix, "42")
        if len(branch) > 0:
            assert not branch.endswith("-"), (
                f"Branch name ends with hyphen after truncation: {branch[-20:]}"
            )
            assert len(branch) <= 200

    def test_yaml_contains_branch_length_guard(self) -> None:
        """The default-workflow.yaml step-04 shell code must contain a BRANCH_NAME length check.

        FAILS NOW: No length check on BRANCH_NAME exists (only slug is cut to 50).
        PASSES AFTER FIX: Shell code checks ${#BRANCH_NAME} > 200.
        """
        content = DEFAULT_WORKFLOW.read_text(encoding="utf-8")
        # Must contain an explicit BRANCH_NAME length check — not just any "200"
        assert "${#BRANCH_NAME}" in content, (
            "default-workflow.yaml must contain ${#BRANCH_NAME} length guard "
            "after branch assembly (not just slug truncation)"
        )


# ===========================================================================
# BUG #3548: Anti-recursion guard in classify-and-decompose
# ===========================================================================


class TestClassifyAntiRecursion:
    """Verify classify-and-decompose prompt blocks skill/workflow invocation.

    Current behavior: Prompt says "Do NOT implement, build, code" but does
    not explicitly forbid invoking skills or workflows, allowing the agent
    to recurse into dev-orchestrator.

    Expected fix: Add explicit instruction blocking skill/workflow invocation.
    """

    def _get_classify_prompt(self) -> str:
        """Extract the classify-and-decompose step prompt from smart-orchestrator.yaml."""
        recipe = _load_yaml(SMART_ORCHESTRATOR)
        step = _find_step(recipe, "classify-and-decompose")
        assert step is not None, "classify-and-decompose step not found"
        return step.get("prompt", "")

    def test_prompt_blocks_skill_invocation(self) -> None:
        """Prompt must explicitly forbid invoking skills.

        FAILS NOW: Prompt only says "Do NOT implement, build, code..."
        PASSES AFTER FIX: Prompt includes "Do NOT invoke any skills".
        """
        prompt = self._get_classify_prompt()
        prompt_lower = prompt.lower()
        assert "skill" in prompt_lower and ("invoke" in prompt_lower or "call" in prompt_lower), (
            "classify-and-decompose prompt must explicitly forbid invoking skills. "
            f"Current prompt fragment: {prompt[:200]}..."
        )

    def test_prompt_blocks_workflow_invocation(self) -> None:
        """Prompt must explicitly forbid invoking workflows in prohibition context.

        FAILS NOW: "workflow" only appears as recipe type, not in a prohibition.
        PASSES AFTER FIX: Prompt includes "Do NOT invoke any ... workflows".
        """
        prompt = self._get_classify_prompt()
        prompt_lower = prompt.lower()
        # Must contain "workflow" near "invoke" or "do not invoke" — not just
        # as a recipe type reference like "default-workflow"
        has_prohibition = (
            "do not invoke" in prompt_lower and "workflow" in prompt_lower
        ) or "not invoke any" in prompt_lower
        assert has_prohibition, (
            "classify-and-decompose prompt must explicitly forbid invoking workflows "
            "in a prohibition context (not just mentioning 'default-workflow' as recipe type)."
        )

    def test_prompt_blocks_orchestrator_invocation(self) -> None:
        """Prompt must explicitly name dev-orchestrator as forbidden to invoke.

        FAILS NOW: "orchestrator" only appears in "task orchestrator" self-description.
        PASSES AFTER FIX: Prompt includes "Do NOT call dev-orchestrator".
        """
        prompt = self._get_classify_prompt()
        # Must mention dev-orchestrator in a prohibition, not just "task orchestrator"
        assert "dev-orchestrator" in prompt.lower(), (
            "classify-and-decompose prompt must explicitly name 'dev-orchestrator' "
            "as forbidden (not just 'task orchestrator' self-description)."
        )

    def test_prompt_emphasizes_json_only_output(self) -> None:
        """Prompt must stress that ONLY JSON output is acceptable.

        Verifies the existing "Output exactly this JSON" is complemented by
        a stronger "Return ONLY the JSON" instruction.
        """
        prompt = self._get_classify_prompt()
        prompt_lower = prompt.lower()
        assert "only" in prompt_lower and "json" in prompt_lower, (
            "Prompt must emphasize JSON-only output"
        )


# ===========================================================================
# BUG #4169: step-02b-analyze-codebase indefinite hang (no timeout)
# ===========================================================================


class TestStep02bAnalyzeCodebaseTimeout:
    """Verify step-02b-analyze-codebase has a timeout to prevent indefinite hangs.

    Root cause: The step has no `timeout` field. The Rust recipe runner enforces
    timeouts only when the field is present. Without it, the amplihack:architect
    agent invocation waits forever in AMPLIHACK_NONINTERACTIVE=1 mode.

    Reproduction log: /tmp/amplihack-recipe-smart-orchestrator-2773659.log shows
    step-02b-analyze-codebase emitting "start" but never "done" or "error".

    Fix: Add `timeout: 600` to step-02b-analyze-codebase in default-workflow.yaml.
    """

    def _get_step_02b(self) -> dict:
        """Extract step-02b from default-workflow.yaml."""
        recipe = _load_yaml(DEFAULT_WORKFLOW)
        step = _find_step(recipe, "step-02b-analyze-codebase")
        assert step is not None, "step-02b-analyze-codebase not found"
        return step

    def test_step_has_timeout(self) -> None:
        """step-02b must have a timeout field to prevent indefinite hangs.

        Without a timeout, the Rust runner waits forever for the agent subprocess.
        PASSES: timeout field is present and positive.
        """
        step = self._get_step_02b()
        assert "timeout" in step, (
            "step-02b-analyze-codebase must have a 'timeout' field to prevent hangs. "
            "Issue #4169: step starts but never emits 'done' or 'error' in non-interactive mode."
        )
        timeout_val = step["timeout"]
        assert isinstance(timeout_val, (int, float)), (
            f"timeout must be numeric, got {type(timeout_val).__name__}"
        )
        assert timeout_val > 0, "timeout must be positive"


# ===========================================================================
# BUG #3291: step-02c context size guard and timeout
# ===========================================================================


class TestStep02cContextGuard:
    """Verify step-02c has timeout and context size protection.

    Current behavior: Agent step has no timeout or context guard. If
    accumulated codebase_analysis is very large, the agent hangs indefinitely.

    Expected fix: Add timeout: 60 to the step YAML. Add prompt instruction
    about summarizing context exceeding 100KB.
    """

    def _get_step_02c(self) -> dict:
        """Extract step-02c from default-workflow.yaml."""
        recipe = _load_yaml(DEFAULT_WORKFLOW)
        step = _find_step(recipe, "step-02c-resolve-ambiguity")
        assert step is not None, "step-02c-resolve-ambiguity not found"
        return step

    def test_step_has_timeout(self) -> None:
        """step-02c must have a timeout field to prevent indefinite hangs.

        FAILS NOW: No timeout field on the step.
        PASSES AFTER FIX: timeout: 60 (or similar) is set.
        """
        step = self._get_step_02c()
        assert "timeout" in step, (
            "step-02c-resolve-ambiguity must have a 'timeout' field to prevent hangs"
        )
        timeout_val = step["timeout"]
        assert isinstance(timeout_val, (int, float)), (
            f"timeout must be numeric, got {type(timeout_val).__name__}"
        )
        assert timeout_val > 0, "timeout must be positive"

    def test_prompt_instructs_context_summarization(self) -> None:
        """step-02c prompt must instruct agent to summarize large context.

        FAILS NOW: Prompt has no mention of context size or summarization.
        PASSES AFTER FIX: Prompt mentions summarizing when context is large.
        """
        step = self._get_step_02c()
        prompt = step.get("prompt", "")
        prompt_lower = prompt.lower()
        assert "summar" in prompt_lower, (
            "step-02c prompt must instruct agent to summarize large context. "
            f"Current prompt: {prompt[:200]}..."
        )

    def test_prompt_mentions_context_size_threshold(self) -> None:
        """step-02c prompt should reference a size threshold (e.g., 100KB).

        FAILS NOW: No size threshold mentioned.
        PASSES AFTER FIX: Prompt mentions 100KB or similar threshold.
        """
        step = self._get_step_02c()
        prompt = step.get("prompt", "")
        assert "100" in prompt or "KB" in prompt or "size" in prompt.lower(), (
            "step-02c prompt should reference a context size threshold"
        )


# ===========================================================================
# BUG #3298: SKILL.md AMPLIHACK_HOME documentation
# ===========================================================================


class TestSkillMdAmplihackHome:
    """Verify SKILL.md documents AMPLIHACK_HOME auto-detection behavior.

    Current behavior: Says "must point to the amplihack repo root" — outdated.

    Expected fix: Document auto-detection algorithm. Mention that
    AMPLIHACK_HOME is auto-detected from the working directory and only
    needs manual setting when auto-detection fails.
    """

    def _read_skill_md(self) -> str:
        """Read SKILL.md content."""
        return SKILL_MD.read_text(encoding="utf-8")

    def test_does_not_say_must_point_to_repo_root(self) -> None:
        """SKILL.md must NOT say 'must point to the amplihack repo root'.

        FAILS NOW: Line 266 says exactly this.
        PASSES AFTER FIX: Updated to describe auto-detection.
        """
        content = self._read_skill_md()
        assert "must point to the amplihack repo root" not in content, (
            "SKILL.md still contains outdated 'must point to the amplihack repo root' text"
        )

    def test_documents_auto_detection(self) -> None:
        """SKILL.md must mention auto-detection for AMPLIHACK_HOME.

        FAILS NOW: Only describes manual setting.
        PASSES AFTER FIX: Documents auto-detection behavior.
        """
        content = self._read_skill_md().lower()
        assert "auto-detect" in content or "auto detect" in content or "automatically" in content, (
            "SKILL.md must document AMPLIHACK_HOME auto-detection behavior"
        )

    def test_documents_fallback_instruction(self) -> None:
        """SKILL.md must explain what to do when auto-detection fails.

        FAILS NOW: Only says to set it to repo root.
        PASSES AFTER FIX: Mentions setting to directory containing amplifier-bundle/.
        """
        content = self._read_skill_md()
        assert "amplifier-bundle" in content, (
            "SKILL.md must mention amplifier-bundle/ as the key directory marker"
        )
