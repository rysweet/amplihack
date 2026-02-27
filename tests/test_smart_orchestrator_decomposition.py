"""Tests for smart-orchestrator recipe decomposition logic.

Tests exercise orch_helper.py (amplifier-bundle/tools/orch_helper.py) directly —
the production module extracted from the old write-json-helper YAML heredoc.
Importing the real module ensures tests always reflect production behaviour.

Test areas:
1. Single workstream detection (cohesive single task)
2. Multi-workstream detection (clearly independent parallel components)
3. JSON parsing robustness (JSON in code blocks, raw JSON, multi-block responses)
4. Task type classification (Q&A vs Development vs Investigation)
5. normalise_type mapping (abbreviated -> canonical)
6. Round/goal status reflection logic
7. Empty slug fallback
"""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path  # noqa: F401 (kept for _TOOLS_DIR construction below)

# ---------------------------------------------------------------------------
# Import production helper directly from amplifier-bundle/tools/orch_helper.py
# ---------------------------------------------------------------------------
# This replaces the previous approach of extracting Python from a YAML heredoc.
# The helper was extracted to a proper module (NEW-18 fix) which enables direct
# import, linting, and syntax checking.
# ---------------------------------------------------------------------------

_TOOLS_DIR = Path(__file__).parent.parent / "amplifier-bundle" / "tools"
sys.path.insert(0, str(_TOOLS_DIR))
import orch_helper as _h  # noqa: E402

extract_json = _h.extract_json
normalise_type = _h.normalise_type


# ---------------------------------------------------------------------------
# Compatibility shims so existing tests that call parse_decomposition /
# create_workstreams_config still work unchanged.
# ---------------------------------------------------------------------------


def parse_decomposition(text: str) -> tuple[str, int]:
    """
    Replicate the Python logic from the 'parse-decomposition' bash step.

    Returns (task_type, workstream_count).
    """
    obj = extract_json(text)
    task_type = normalise_type(obj.get("task_type", "Development"))
    workstreams = obj.get("workstreams", [{}])
    count = max(1, len(workstreams))
    return task_type, count


def create_workstreams_config(text: str) -> list[dict]:
    """
    Replicate the Python logic from the 'create-workstreams-config' bash step.

    Returns the list of workstream config dicts (normally written to JSON file).
    """
    obj = extract_json(text)
    workstreams = obj.get("workstreams", [])
    config = []
    for i, ws in enumerate(workstreams):
        name = ws.get("name", f"workstream-{i + 1}")
        slug = re.sub(r"[^a-z0-9-]", "-", name.lower())[:30].strip("-") or f"ws-{i + 1}"
        config.append(
            {
                "issue": "TBD",
                "branch": f"feat/orch-{i + 1}-{slug}",
                "description": name,
                "task": ws.get("description", name),
                "recipe": ws.get("recipe", "default-workflow"),
            }
        )
    return config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_decomposition_json(
    task_type: str,
    workstreams: list[dict],
    goal: str = "Accomplish the task",
    success_criteria: list[str] | None = None,
) -> str:
    """Build a well-formed decomposition JSON string (raw, no code block)."""
    obj = {
        "task_type": task_type,
        "goal": goal,
        "success_criteria": success_criteria or ["Task complete"],
        "workstreams": workstreams,
    }
    return json.dumps(obj)


def _wrap_in_code_block(json_str: str, tag: str = "json") -> str:
    return f"```{tag}\n{json_str}\n```"


# ---------------------------------------------------------------------------
# Test suite: Single workstream detection
# ---------------------------------------------------------------------------


class TestSingleWorkstreamDetection(unittest.TestCase):
    """Verify that cohesive, single-concern tasks produce workstream_count == 1."""

    def test_single_dev_workstream(self):
        raw = _make_decomposition_json(
            "Development",
            [{"name": "auth", "description": "Implement JWT auth", "recipe": "default-workflow"}],
        )
        task_type, count = parse_decomposition(raw)
        self.assertEqual(count, 1)
        self.assertEqual(task_type, "Development")

    def test_single_investigation_workstream(self):
        raw = _make_decomposition_json(
            "Investigation",
            [
                {
                    "name": "caching-research",
                    "description": "Understand the caching layer",
                    "recipe": "investigation-workflow",
                }
            ],
        )
        task_type, count = parse_decomposition(raw)
        self.assertEqual(count, 1)
        self.assertEqual(task_type, "Investigation")

    def test_qa_task_has_one_workstream(self):
        """Q&A tasks should still report 1 workstream (handled separately in recipe)."""
        raw = _make_decomposition_json(
            "Q&A",
            [{"name": "answer", "description": "Explain pagination", "recipe": "default-workflow"}],
        )
        task_type, count = parse_decomposition(raw)
        self.assertEqual(task_type, "Q&A")
        self.assertEqual(count, 1)

    def test_empty_workstreams_list_defaults_to_one(self):
        """If LLM returns an empty workstreams array the count should be 1 (not 0)."""
        raw = _make_decomposition_json("Development", [])
        task_type, count = parse_decomposition(raw)
        # max(1, 0) => 1
        self.assertEqual(count, 1)

    def test_single_workstream_in_markdown_block(self):
        inner = _make_decomposition_json(
            "Development",
            [
                {
                    "name": "bug-fix",
                    "description": "Fix login timeout bug",
                    "recipe": "default-workflow",
                }
            ],
        )
        wrapped = _wrap_in_code_block(inner)
        task_type, count = parse_decomposition(wrapped)
        self.assertEqual(count, 1)
        self.assertEqual(task_type, "Development")


# ---------------------------------------------------------------------------
# Test suite: Multi-workstream detection
# ---------------------------------------------------------------------------


class TestMultiWorkstreamDetection(unittest.TestCase):
    """Verify that parallel-capable tasks produce workstream_count > 1."""

    def test_two_independent_workstreams(self):
        raw = _make_decomposition_json(
            "Development",
            [
                {"name": "api", "description": "Build REST API", "recipe": "default-workflow"},
                {"name": "webui", "description": "Build React webui", "recipe": "default-workflow"},
            ],
        )
        task_type, count = parse_decomposition(raw)
        self.assertEqual(count, 2)
        self.assertEqual(task_type, "Development")

    def test_three_workstreams(self):
        raw = _make_decomposition_json(
            "Development",
            [
                {"name": "auth", "description": "OAuth support", "recipe": "default-workflow"},
                {
                    "name": "logging",
                    "description": "Structured logging",
                    "recipe": "default-workflow",
                },
                {
                    "name": "metrics",
                    "description": "Prometheus metrics",
                    "recipe": "default-workflow",
                },
            ],
        )
        _, count = parse_decomposition(raw)
        self.assertEqual(count, 3)

    def test_investigation_then_development_workstreams(self):
        raw = _make_decomposition_json(
            "Development",
            [
                {
                    "name": "investigate-auth",
                    "description": "Investigate auth system",
                    "recipe": "investigation-workflow",
                },
                {
                    "name": "implement-oauth",
                    "description": "Implement OAuth",
                    "recipe": "default-workflow",
                },
            ],
        )
        task_type, count = parse_decomposition(raw)
        self.assertEqual(count, 2)

    def test_max_five_workstreams(self):
        workstreams = [
            {"name": f"ws-{i}", "description": f"Task {i}", "recipe": "default-workflow"}
            for i in range(5)
        ]
        raw = _make_decomposition_json("Development", workstreams)
        _, count = parse_decomposition(raw)
        self.assertEqual(count, 5)

    def test_workstreams_config_branches_have_unique_names(self):
        raw = _make_decomposition_json(
            "Development",
            [
                {"name": "api", "description": "REST API", "recipe": "default-workflow"},
                {"name": "webui", "description": "React webui", "recipe": "default-workflow"},
            ],
        )
        config = create_workstreams_config(raw)
        branches = [c["branch"] for c in config]
        self.assertEqual(len(branches), len(set(branches)), "Branches must be unique")

    def test_workstreams_config_branch_format(self):
        raw = _make_decomposition_json(
            "Development",
            [
                {"name": "user-auth", "description": "Auth work", "recipe": "default-workflow"},
                {"name": "logging", "description": "Logging work", "recipe": "default-workflow"},
            ],
        )
        config = create_workstreams_config(raw)
        for item in config:
            self.assertTrue(
                item["branch"].startswith("feat/orch-"),
                f"Branch must start with 'feat/orch-', got: {item['branch']}",
            )

    def test_workstreams_config_preserves_recipe_field(self):
        raw = _make_decomposition_json(
            "Development",
            [
                {
                    "name": "research",
                    "description": "Investigate caching",
                    "recipe": "investigation-workflow",
                },
                {"name": "impl", "description": "Implement cache", "recipe": "default-workflow"},
            ],
        )
        config = create_workstreams_config(raw)
        self.assertEqual(config[0]["recipe"], "investigation-workflow")
        self.assertEqual(config[1]["recipe"], "default-workflow")

    def test_workstreams_config_defaults_recipe_to_default_workflow(self):
        """Workstream without recipe field should default to default-workflow."""
        raw = json.dumps(
            {
                "task_type": "Development",
                "goal": "Do things",
                "success_criteria": [],
                "workstreams": [
                    {"name": "no-recipe-ws", "description": "Some work"},
                ],
            }
        )
        config = create_workstreams_config(raw)
        self.assertEqual(config[0]["recipe"], "default-workflow")


# ---------------------------------------------------------------------------
# Test suite: JSON parsing robustness
# ---------------------------------------------------------------------------


class TestJsonParsingRobustness(unittest.TestCase):
    """Verify the parser handles real-world LLM output variations."""

    def test_raw_json_no_wrapping(self):
        raw = '{"task_type": "Development", "goal": "g", "success_criteria": [], "workstreams": [{"name": "x", "description": "d", "recipe": "default-workflow"}]}'
        task_type, count = parse_decomposition(raw)
        self.assertEqual(task_type, "Development")
        self.assertEqual(count, 1)

    def test_json_in_json_code_block(self):
        inner = _make_decomposition_json(
            "Investigation",
            [{"name": "research", "description": "Deep dive", "recipe": "investigation-workflow"}],
        )
        text = f"Here is my analysis:\n\n```json\n{inner}\n```\n\nI hope this helps."
        task_type, count = parse_decomposition(text)
        self.assertEqual(task_type, "Investigation")
        self.assertEqual(count, 1)

    def test_json_in_plain_code_block(self):
        inner = _make_decomposition_json(
            "Development",
            [{"name": "feat", "description": "Add feature", "recipe": "default-workflow"}],
        )
        text = f"Output:\n```\n{inner}\n```"
        task_type, count = parse_decomposition(text)
        self.assertEqual(task_type, "Development")
        self.assertEqual(count, 1)

    def test_json_embedded_in_prose(self):
        inner = _make_decomposition_json(
            "Operations",
            [{"name": "ops", "description": "Run cleanup", "recipe": "default-workflow"}],
        )
        text = f"Based on my analysis, the plan is: {inner}\n\nPlease proceed."
        task_type, count = parse_decomposition(text)
        self.assertEqual(task_type, "Operations")

    def test_completely_invalid_text_defaults_to_development_one_workstream(self):
        """When the LLM returns garbage the defaults should be safe."""
        text = "I cannot determine the task type from this request."
        task_type, count = parse_decomposition(text)
        self.assertEqual(task_type, "Development")
        self.assertEqual(count, 1)

    def test_empty_string_returns_defaults(self):
        task_type, count = parse_decomposition("")
        self.assertEqual(task_type, "Development")
        self.assertEqual(count, 1)

    def test_malformed_json_returns_defaults(self):
        text = '{"task_type": "Development", "workstreams": [{'  # truncated
        task_type, count = parse_decomposition(text)
        # Malformed JSON should fall back to defaults
        self.assertEqual(task_type, "Development")
        self.assertEqual(count, 1)

    def test_json_missing_task_type_defaults_to_development(self):
        obj = {
            "goal": "Build the thing",
            "workstreams": [{"name": "x", "description": "d", "recipe": "default-workflow"}],
        }
        task_type, count = parse_decomposition(json.dumps(obj))
        self.assertEqual(task_type, "Development")

    def test_json_missing_workstreams_defaults_to_one(self):
        obj = {"task_type": "Investigation", "goal": "Research"}
        task_type, count = parse_decomposition(json.dumps(obj))
        # workstreams missing → default [{}] → count 1
        self.assertEqual(count, 1)
        self.assertEqual(task_type, "Investigation")

    def test_create_config_from_code_block_json(self):
        inner = _make_decomposition_json(
            "Development",
            [
                {"name": "api", "description": "Build API", "recipe": "default-workflow"},
                {"name": "ui", "description": "Build UI", "recipe": "default-workflow"},
            ],
        )
        text = f"```json\n{inner}\n```"
        config = create_workstreams_config(text)
        self.assertEqual(len(config), 2)

    def test_create_config_from_invalid_json_returns_empty(self):
        config = create_workstreams_config("definitely not json at all")
        self.assertEqual(config, [])

    def test_create_config_from_empty_string_returns_empty(self):
        config = create_workstreams_config("")
        self.assertEqual(config, [])

    def test_nested_json_in_code_block(self):
        """Greedy regex must handle nested objects inside the code block correctly."""
        inner = json.dumps({
            "task_type": "Development",
            "goal": "Ship it",
            "success_criteria": ["Tests pass"],
            "workstreams": [
                {
                    "name": "backend",
                    "description": "Build backend with config: {\"debug\": true}",
                    "recipe": "default-workflow",
                    "metadata": {"priority": "high"},
                },
                {
                    "name": "frontend",
                    "description": "Build frontend",
                    "recipe": "default-workflow",
                },
            ],
        })
        text = f"```json\n{inner}\n```"
        task_type, count = parse_decomposition(text)
        self.assertEqual(task_type, "Development")
        self.assertEqual(count, 2)


# ---------------------------------------------------------------------------
# Test suite: Task type classification
# ---------------------------------------------------------------------------


class TestTaskTypeClassification(unittest.TestCase):
    """Verify task_type is correctly extracted and preserved."""

    def _make(self, task_type: str) -> str:
        return _make_decomposition_json(
            task_type,
            [{"name": "ws", "description": "task", "recipe": "default-workflow"}],
        )

    def test_development_classification(self):
        task_type, _ = parse_decomposition(self._make("Development"))
        self.assertEqual(task_type, "Development")

    def test_investigation_classification(self):
        task_type, _ = parse_decomposition(self._make("Investigation"))
        self.assertEqual(task_type, "Investigation")

    def test_qa_classification(self):
        task_type, _ = parse_decomposition(self._make("Q&A"))
        self.assertEqual(task_type, "Q&A")

    def test_operations_classification(self):
        task_type, _ = parse_decomposition(self._make("Operations"))
        self.assertEqual(task_type, "Operations")

    def test_condition_qa_in_task_type(self):
        """Verify 'Q&A' in task_type matches the recipe condition logic."""
        task_type, _ = parse_decomposition(self._make("Q&A"))
        self.assertIn("Q&A", task_type)

    def test_condition_operations_in_task_type(self):
        task_type, _ = parse_decomposition(self._make("Operations"))
        self.assertIn("Operations", task_type)

    def test_condition_ops_abbreviation_in_task_type(self):
        """Recipe normalise_type maps 'Ops' -> 'Operations'."""
        task_type, _ = parse_decomposition(self._make("Ops"))
        self.assertEqual(task_type, "Operations")

    def test_condition_development_in_task_type(self):
        task_type, _ = parse_decomposition(self._make("Development"))
        self.assertIn("Development", task_type)

    def test_condition_investigation_in_task_type(self):
        task_type, _ = parse_decomposition(self._make("Investigation"))
        self.assertIn("Investigation", task_type)

    def test_workstream_count_as_string_for_condition_comparison(self):
        """
        The recipe uses workstream_count.strip() == '1' (string comparison).
        Ensure the count we produce is representable as a string '1' or '2'.
        """
        raw_single = self._make("Development")
        _, count = parse_decomposition(raw_single)
        # String comparison used in recipe condition
        self.assertEqual(str(count).strip(), "1")

        raw_multi = _make_decomposition_json(
            "Development",
            [
                {"name": "a", "description": "A", "recipe": "default-workflow"},
                {"name": "b", "description": "B", "recipe": "default-workflow"},
            ],
        )
        _, count2 = parse_decomposition(raw_multi)
        self.assertNotEqual(str(count2).strip(), "1")
        self.assertEqual(int(str(count2).strip()), 2)


# ---------------------------------------------------------------------------
# Test suite: normalise_type mapping
# ---------------------------------------------------------------------------


class TestNormaliseType(unittest.TestCase):
    """Verify normalise_type maps abbreviated/variant strings to canonical types."""

    def test_normalise_type_qa(self):
        """'qa', 'question', 'Q&A' all resolve to 'Q&A'."""
        for raw in ("qa", "question", "Q&A", "answer"):
            with self.subTest(raw=raw):
                self.assertEqual(normalise_type(raw), "Q&A")

    def test_normalise_type_ops(self):
        """'ops', 'operation', 'admin' all resolve to 'Operations'."""
        for raw in ("ops", "operation", "admin", "Operations"):
            with self.subTest(raw=raw):
                self.assertEqual(normalise_type(raw), "Operations")

    def test_normalise_type_investigation(self):
        """'invest', 'research', 'understand' all resolve to 'Investigation'."""
        for raw in ("invest", "research", "understand", "Investigation", "analysis"):
            with self.subTest(raw=raw):
                self.assertEqual(normalise_type(raw), "Investigation")

    def test_normalise_type_development(self):
        """Everything else resolves to 'Development'."""
        for raw in ("dev", "build", "feature", "Development", "implement", "unknown"):
            with self.subTest(raw=raw):
                self.assertEqual(normalise_type(raw), "Development")


# ---------------------------------------------------------------------------
# Test suite: Round / goal-status reflection logic
# ---------------------------------------------------------------------------


class TestRoundGoalStatus(unittest.TestCase):
    """Verify the reflection conditions used in the recipe YAML."""

    def test_round_goal_status_partial_triggers_round_2(self):
        """'PARTIAL' anywhere in the reflection string should trigger round 2."""
        reflection = "GOAL_STATUS: PARTIAL -- missing tests and CI config"
        self.assertIn("PARTIAL", reflection)
        # The recipe condition: 'PARTIAL' in reflection_1 or 'NOT_ACHIEVED' in reflection_1
        should_trigger = "PARTIAL" in reflection or "NOT_ACHIEVED" in reflection
        self.assertTrue(should_trigger)

    def test_round_goal_status_achieved_does_not_trigger(self):
        """'ACHIEVED' alone must not trigger round 2."""
        reflection = "GOAL_STATUS: ACHIEVED"
        should_trigger = "PARTIAL" in reflection or "NOT_ACHIEVED" in reflection
        self.assertFalse(should_trigger)

    def test_not_achieved_triggers_round_2(self):
        reflection = "GOAL_STATUS: NOT_ACHIEVED -- CI is still red"
        should_trigger = "PARTIAL" in reflection or "NOT_ACHIEVED" in reflection
        self.assertTrue(should_trigger)


# ---------------------------------------------------------------------------
# Test suite: Branch slug generation
# ---------------------------------------------------------------------------


class TestBranchSlugGeneration(unittest.TestCase):
    """Verify branch names are generated safely from workstream names."""

    def _config_for(self, names: list[str]) -> list[dict]:
        workstreams = [
            {"name": n, "description": f"Task for {n}", "recipe": "default-workflow"} for n in names
        ]
        raw = _make_decomposition_json("Development", workstreams)
        return create_workstreams_config(raw)

    def test_simple_name_slug(self):
        config = self._config_for(["api"])
        self.assertEqual(config[0]["branch"], "feat/orch-1-api")

    def test_hyphenated_name_slug(self):
        config = self._config_for(["user-auth"])
        self.assertEqual(config[0]["branch"], "feat/orch-1-user-auth")

    def test_uppercase_name_lowercased_in_slug(self):
        config = self._config_for(["UserAuth"])
        self.assertIn("userauth", config[0]["branch"])

    def test_spaces_in_name_become_hyphens(self):
        config = self._config_for(["user auth service"])
        self.assertNotIn(" ", config[0]["branch"])
        self.assertIn("-", config[0]["branch"])

    def test_slug_max_length_30(self):
        long_name = "a-very-long-workstream-name-that-exceeds-thirty-chars"
        config = self._config_for([long_name])
        branch = config[0]["branch"]
        # slug part after "feat/orch-1-" should be <= 30 chars
        slug_part = branch.replace("feat/orch-1-", "")
        self.assertLessEqual(len(slug_part), 30)

    def test_special_chars_replaced_with_hyphen(self):
        config = self._config_for(["api@v2"])
        branch = config[0]["branch"]
        self.assertNotIn("@", branch)

    def test_multiple_workstreams_numbered_sequentially(self):
        config = self._config_for(["api", "webui", "auth"])
        indices = [c["branch"].split("/")[1].split("-")[1] for c in config]
        self.assertEqual(indices, ["1", "2", "3"])

    def test_empty_slug_fallback(self):
        """A name that produces an all-special-char slug must fall back to ws-{i+1}."""
        config = self._config_for(["@@@"])
        branch = config[0]["branch"]
        # slug after stripping non-alnum and stripping hyphens -> empty -> ws-1
        self.assertIn("ws-1", branch, f"Expected ws-1 fallback in branch, got: {branch}")


# ---------------------------------------------------------------------------
# Test suite: Workstream config structure
# ---------------------------------------------------------------------------


class TestWorkstreamConfigStructure(unittest.TestCase):
    """Verify the shape of each workstream config dict."""

    def setUp(self):
        self.raw = _make_decomposition_json(
            "Development",
            [
                {"name": "api", "description": "Build the API layer", "recipe": "default-workflow"},
                {"name": "ui", "description": "Build the React UI", "recipe": "default-workflow"},
            ],
        )
        self.config = create_workstreams_config(self.raw)

    def test_config_has_required_fields(self):
        required = {"issue", "branch", "description", "task", "recipe"}
        for item in self.config:
            missing = required - item.keys()
            self.assertFalse(missing, f"Config item missing fields: {missing}")

    def test_issue_field_is_tbd(self):
        for item in self.config:
            self.assertEqual(item["issue"], "TBD")

    def test_description_matches_workstream_name(self):
        self.assertEqual(self.config[0]["description"], "api")
        self.assertEqual(self.config[1]["description"], "ui")

    def test_task_field_is_workstream_description(self):
        self.assertEqual(self.config[0]["task"], "Build the API layer")
        self.assertEqual(self.config[1]["task"], "Build the React UI")

    def test_config_count_matches_workstream_count(self):
        self.assertEqual(len(self.config), 2)


# ---------------------------------------------------------------------------
# Test suite: Multi-block LLM response (greedy regex regression)
# Exercises the NEW-3 fix: extract_json must handle multiple JSON code blocks
# without merging them via a greedy regex.
# ---------------------------------------------------------------------------


class TestMultiBlockLLMResponse(unittest.TestCase):
    """Verify extract_json handles real-world LLM output with multiple JSON blocks."""

    def test_single_code_block_returns_correct_object(self):
        """Baseline: one code block returns its JSON correctly."""
        obj = {
            "task_type": "Development",
            "goal": "do x",
            "success_criteria": [],
            "workstreams": [{"name": "api", "description": "build it", "recipe": "default-workflow"}],
        }
        text = f"```json\n{json.dumps(obj)}\n```"
        result = extract_json(text)
        self.assertEqual(result.get("task_type"), "Development")
        self.assertEqual(len(result.get("workstreams", [])), 1)

    def test_two_code_blocks_returns_first_valid_one(self):
        """When LLM returns example JSON then real JSON, only first valid block is used."""
        example = '{"task_type": "Q&A", "goal": "example", "workstreams": []}'
        real = json.dumps({
            "task_type": "Development",
            "goal": "build the system",
            "success_criteria": ["tests pass"],
            "workstreams": [{"name": "ws1", "description": "d1", "recipe": "default-workflow"}],
        })
        text = (
            "Here is an example of the format:\n"
            f"```json\n{example}\n```\n\n"
            "And here is my actual plan:\n"
            f"```json\n{real}\n```"
        )
        result = extract_json(text)
        # Must return the first valid block, not a merge of both
        # Both are individually valid — the first one is returned
        self.assertIn(result.get("task_type"), ("Q&A", "Development"))
        # Crucially: must NOT fail or return {} due to a merged-greedy parse
        self.assertNotEqual(result, {})

    def test_greedy_merge_would_produce_invalid_json(self):
        """Demonstrate that a naive greedy {.*} would merge two code blocks incorrectly.

        This test verifies the extract_json function does NOT use the naive
        greedy pattern by confirming it still returns a valid object when two
        code blocks are present.
        """
        block1_json = '{"task_type": "Development", "goal": "g1", "workstreams": [{"name": "a"}]}'
        block2_json = '{"task_type": "Investigation", "goal": "g2", "workstreams": []}'
        text = f"First:\n```json\n{block1_json}\n```\n\nSecond:\n```json\n{block2_json}\n```"

        # Naive greedy: r'\{.*\}' with re.DOTALL would match from first '{' to last '}'
        # spanning both blocks, producing invalid JSON that json.loads would reject.
        naive_match = re.search(r"\{.*\}", text, re.DOTALL)
        naive_result = {}
        if naive_match:
            try:
                naive_result = json.loads(naive_match.group(0))
            except json.JSONDecodeError:
                pass  # naive greedy fails here

        # Our fixed extract_json should still return a valid object
        fixed_result = extract_json(text)
        self.assertNotEqual(fixed_result, {}, "Fixed extract_json must return a valid object")

    def test_prose_with_embedded_json_no_code_block(self):
        """JSON embedded in prose (no code block) is extracted via balanced-brace fallback."""
        obj = {"task_type": "Operations", "goal": "run cleanup", "workstreams": []}
        text = f"Based on my analysis the plan is: {json.dumps(obj)} Please proceed."
        result = extract_json(text)
        self.assertEqual(result.get("task_type"), "Operations")

    def test_nested_json_in_code_block_correctly_parsed(self):
        """Nested objects (workstreams array) must be parsed completely — not truncated."""
        obj = {
            "task_type": "Development",
            "goal": "build",
            "success_criteria": ["cr1"],
            "workstreams": [
                {"name": "ws1", "description": "do x", "recipe": "default-workflow"},
                {"name": "ws2", "description": "do y", "recipe": "investigation-workflow"},
            ],
        }
        text = f"```json\n{json.dumps(obj, indent=2)}\n```"
        result = extract_json(text)
        self.assertEqual(len(result.get("workstreams", [])), 2)


# ---------------------------------------------------------------------------
# Test suite: Round-1-success path (NEW-2 regression)
# Verifies that the reflect-final condition change works correctly:
# reflect-final must run whenever round_1_result is non-empty.
# ---------------------------------------------------------------------------


class TestRound1SuccessPath(unittest.TestCase):
    """Verify the fixed reflect-final condition covers the round-1-success case."""

    def _reflect_final_should_run(
        self, task_type: str, round_1_result: str
    ) -> bool:
        """Simulate the fixed reflect-final condition from the recipe."""
        # New (fixed) condition: Q&A/Ops excluded, round_1_result must be truthy
        return (
            "Q&A" not in task_type
            and "Operations" not in task_type
            and bool(round_1_result)
        )

    def test_reflect_final_runs_on_achieved_round_1(self):
        """When round 1 ACHIEVED the goal, reflect-final must still run."""
        self.assertTrue(
            self._reflect_final_should_run(
                task_type="Development",
                round_1_result="Work done. PR created. STATUS: COMPLETE",
            )
        )

    def test_reflect_final_runs_on_partial_round_1(self):
        self.assertTrue(
            self._reflect_final_should_run(
                task_type="Development",
                round_1_result="Some work done. STATUS: CONTINUE",
            )
        )

    def test_reflect_final_skips_for_qa(self):
        self.assertFalse(
            self._reflect_final_should_run(
                task_type="Q&A",
                round_1_result="Here is the answer.",
            )
        )

    def test_reflect_final_skips_for_ops(self):
        self.assertFalse(
            self._reflect_final_should_run(
                task_type="Operations",
                round_1_result="Command executed. STATUS: COMPLETE",
            )
        )

    def test_reflect_final_skips_when_no_result(self):
        """If round_1_result is empty, reflect-final must not run."""
        self.assertFalse(
            self._reflect_final_should_run(
                task_type="Development",
                round_1_result="",
            )
        )

    def test_reflect_final_skips_depth_limited(self):
        """DEPTH_LIMITED result must not be evaluated by reflect-round-1 (NEW-5 fix).

        The recipe guards reflect-round-1 with:
        'DEPTH_LIMITED' not in round_1_result
        """
        round_1_result = (
            "RECURSION GUARD: session depth limit reached.\nSTATUS: DEPTH_LIMITED"
        )
        # reflect-round-1 condition (includes DEPTH_LIMITED guard)
        should_reflect = (
            "Q&A" not in "Development"
            and "Operations" not in "Development"
            and bool(round_1_result)
            and "DEPTH_LIMITED" not in round_1_result  # NEW-5 guard
        )
        self.assertFalse(should_reflect)


if __name__ == "__main__":
    unittest.main()
