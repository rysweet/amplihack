"""Tests for smart-orchestrator recipe decomposition logic.

Covers the Python logic embedded in the 'parse-decomposition' and
'create-workstreams-config' bash steps of smart-orchestrator.yaml.

These tests extract and exercise the parsing/decomposition functions directly,
without invoking the recipe runner, so they run fast and without external deps.

Test areas:
1. Single workstream detection (cohesive single task)
2. Multi-workstream detection (clearly independent parallel components)
3. JSON parsing robustness (JSON in code blocks, raw JSON, partial JSON)
4. Task type classification (Q&A vs Development vs Investigation)
"""

from __future__ import annotations

import json
import re
import unittest

# ---------------------------------------------------------------------------
# Extracted logic from parse-decomposition bash step (lines 88-115 of recipe)
# ---------------------------------------------------------------------------


def parse_decomposition(text: str) -> tuple[str, int]:
    """
    Replicate the Python logic from the 'parse-decomposition' bash step.

    Returns (task_type, workstream_count).
    """
    # Extract JSON from markdown code block or raw text
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not json_match:
        json_match = re.search(r'(\{[^{}]*"task_type"[^{}]*\})', text, re.DOTALL)
    if not json_match:
        # Try to find any JSON object
        json_match = re.search(r"(\{.*\})", text, re.DOTALL)

    try:
        if json_match:
            obj = json.loads(json_match.group(1))
        else:
            obj = {}
    except json.JSONDecodeError:
        obj = {}

    task_type = obj.get("task_type", "Development")
    workstreams = obj.get("workstreams", [{}])
    count = max(1, len(workstreams))

    return task_type, count


# ---------------------------------------------------------------------------
# Extracted logic from create-workstreams-config bash step (lines 183-215)
# ---------------------------------------------------------------------------


def create_workstreams_config(text: str) -> list[dict]:
    """
    Replicate the Python logic from the 'create-workstreams-config' bash step.

    Returns the list of workstream config dicts (normally written to JSON file).
    """
    # Extract JSON from the decomposition output
    json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not json_match:
        json_match = re.search(r"(\{.*\})", text, re.DOTALL)

    try:
        obj = json.loads(json_match.group(1)) if json_match else {}
    except Exception:
        obj = {}

    workstreams = obj.get("workstreams", [])
    config = []
    for i, ws in enumerate(workstreams):
        name = ws.get("name", f"workstream-{i + 1}")
        slug = re.sub(r"[^a-z0-9-]", "-", name.lower())[:30].strip("-")
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
        """Recipe checks for 'Ops' as well as 'Operations'."""
        task_type, _ = parse_decomposition(self._make("Ops"))
        self.assertIn("Ops", task_type)

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


if __name__ == "__main__":
    unittest.main()
