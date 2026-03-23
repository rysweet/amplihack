"""Tests for recipe progress banners in YAML recipe files.

Verifies that progress banners are correctly placed in the prompts of
specific recipe steps that require them.  These tests act as regression
guards so any future YAML edit cannot silently break the banner contract.

Contract enforced:
- Banner is the first line of the prompt block (no leading whitespace before it)
- Format is exactly: === [RECIPE PROGRESS] Step: <step-id> ===
- A blank line follows the banner before the main prompt body
- The step-id token in the banner matches the step's ``id:`` field verbatim
- YAML parses without errors after banner insertion
- Original prompt body is preserved verbatim below the blank separator line
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

#: Matches the exact banner format.
_BANNER_PREFIX = "=== [RECIPE PROGRESS] Step: "
_BANNER_SUFFIX = " ==="


def _project_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).resolve().parents[3]


def _recipe_path(recipe_filename: str) -> Path:
    """Resolve a recipe YAML filename to its primary path in amplifier-bundle."""
    path = _project_root() / "amplifier-bundle" / "recipes" / recipe_filename
    if path.exists():
        return path
    # Fallback to src-embedded copy
    fallback = (
        _project_root() / "src" / "amplihack" / "amplifier-bundle" / "recipes" / recipe_filename
    )
    return fallback


def _load_recipe(recipe_filename: str) -> dict:
    """Parse and return the YAML recipe as a dict."""
    path = _recipe_path(recipe_filename)
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _find_step(recipe: dict, step_id: str) -> dict:
    """Return the step dict matching *step_id*, or raise KeyError."""
    for step in recipe.get("steps", []):
        if step.get("id") == step_id:
            return step
    raise KeyError(f"Step {step_id!r} not found in recipe")


def _expected_banner(step_id: str) -> str:
    """Return the expected banner line for a given step ID."""
    return f"{_BANNER_PREFIX}{step_id}{_BANNER_SUFFIX}"


# ---------------------------------------------------------------------------
# Tests for smart-orchestrator.yaml  →  classify-and-decompose
# ---------------------------------------------------------------------------

SMART_ORCHESTRATOR = "smart-orchestrator.yaml"
CLASSIFY_STEP_ID = "classify-and-decompose"


class TestSmartOrchestratorBanner:
    """Banner contract for classify-and-decompose in smart-orchestrator.yaml."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self._recipe = _load_recipe(SMART_ORCHESTRATOR)
        self._step = _find_step(self._recipe, CLASSIFY_STEP_ID)
        self._prompt: str = self._step["prompt"]
        self._lines = self._prompt.splitlines()

    def test_yaml_parses_without_error(self) -> None:
        """YAML must be loadable via yaml.safe_load with no exceptions."""
        assert isinstance(self._recipe, dict)

    def test_banner_is_first_line(self) -> None:
        """Banner must be the very first line of the prompt block."""
        assert len(self._lines) >= 1
        assert self._lines[0] == _expected_banner(CLASSIFY_STEP_ID), (
            f"Expected first line to be the banner, got: {self._lines[0]!r}"
        )

    def test_banner_format_exact(self) -> None:
        """Banner format must match === [RECIPE PROGRESS] Step: <step-id> === exactly."""
        banner = self._lines[0]
        assert banner.startswith(_BANNER_PREFIX), f"Missing prefix in {banner!r}"
        assert banner.endswith(_BANNER_SUFFIX), f"Missing suffix in {banner!r}"
        assert not banner.startswith(" "), "Banner must not have leading whitespace"

    def test_step_id_in_banner_matches_id_field(self) -> None:
        """Step ID embedded in banner must match the step's id: field verbatim."""
        banner = self._lines[0]
        # Extract step-id from banner: strip prefix and suffix
        extracted = banner[len(_BANNER_PREFIX) : -len(_BANNER_SUFFIX)]
        assert extracted == CLASSIFY_STEP_ID, (
            f"Banner step-id {extracted!r} does not match id field {CLASSIFY_STEP_ID!r}"
        )

    def test_blank_line_follows_banner(self) -> None:
        """A blank line must appear immediately after the banner."""
        assert len(self._lines) >= 2, "Prompt must have at least 2 lines"
        assert self._lines[1] == "", f"Expected blank line after banner, got: {self._lines[1]!r}"

    def test_prompt_body_preserved(self) -> None:
        """Original prompt body must appear below the blank separator."""
        # The body starts at line index 2 (after banner + blank line)
        body = "\n".join(self._lines[2:])
        assert len(body) > 0, "Prompt body must not be empty after banner insertion"
        # The original prompt must still contain key phrases from the specification
        assert "intelligent task orchestrator" in body
        assert "structured orchestration plan" in body

    def test_exactly_one_banner_in_prompt(self) -> None:
        """Prompt must contain exactly one progress banner (no duplicates)."""
        count = sum(1 for line in self._lines if _BANNER_PREFIX in line)
        assert count == 1, f"Expected exactly 1 banner, found {count}"

    def test_banner_contains_no_template_vars(self) -> None:
        """Banner line must not contain {{ }} template variables."""
        banner = self._lines[0]
        assert "{{" not in banner and "}}" not in banner, (
            f"Banner must be a static literal; found template vars in: {banner!r}"
        )


# ---------------------------------------------------------------------------
# Tests for default-workflow.yaml  →  step-02-clarify-requirements
# ---------------------------------------------------------------------------

DEFAULT_WORKFLOW = "default-workflow.yaml"
CLARIFY_STEP_ID = "step-02-clarify-requirements"


class TestDefaultWorkflowBanner:
    """Banner contract for step-02-clarify-requirements in default-workflow.yaml."""

    @pytest.fixture(autouse=True)
    def _load(self) -> None:
        self._recipe = _load_recipe(DEFAULT_WORKFLOW)
        self._step = _find_step(self._recipe, CLARIFY_STEP_ID)
        self._prompt: str = self._step["prompt"]
        self._lines = self._prompt.splitlines()

    def test_yaml_parses_without_error(self) -> None:
        """YAML must be loadable via yaml.safe_load with no exceptions."""
        assert isinstance(self._recipe, dict)

    def test_banner_is_first_line(self) -> None:
        """Banner must be the very first line of the prompt block."""
        assert len(self._lines) >= 1
        assert self._lines[0] == _expected_banner(CLARIFY_STEP_ID), (
            f"Expected first line to be the banner, got: {self._lines[0]!r}"
        )

    def test_banner_format_exact(self) -> None:
        """Banner format must match === [RECIPE PROGRESS] Step: <step-id> === exactly."""
        banner = self._lines[0]
        assert banner.startswith(_BANNER_PREFIX), f"Missing prefix in {banner!r}"
        assert banner.endswith(_BANNER_SUFFIX), f"Missing suffix in {banner!r}"
        assert not banner.startswith(" "), "Banner must not have leading whitespace"

    def test_step_id_in_banner_matches_id_field(self) -> None:
        """Step ID embedded in banner must match the step's id: field verbatim."""
        banner = self._lines[0]
        extracted = banner[len(_BANNER_PREFIX) : -len(_BANNER_SUFFIX)]
        assert extracted == CLARIFY_STEP_ID, (
            f"Banner step-id {extracted!r} does not match id field {CLARIFY_STEP_ID!r}"
        )

    def test_blank_line_follows_banner(self) -> None:
        """A blank line must appear immediately after the banner."""
        assert len(self._lines) >= 2, "Prompt must have at least 2 lines"
        assert self._lines[1] == "", f"Expected blank line after banner, got: {self._lines[1]!r}"

    def test_prompt_body_preserved(self) -> None:
        """Original prompt body must appear below the blank separator."""
        body = "\n".join(self._lines[2:])
        assert len(body) > 0, "Prompt body must not be empty after banner insertion"
        # Key phrases from the original prompt body must be present
        assert "Step 2" in body or "Clarify" in body or "Requirements" in body

    def test_exactly_one_banner_in_prompt(self) -> None:
        """Prompt must contain exactly one progress banner (no duplicates)."""
        count = sum(1 for line in self._lines if _BANNER_PREFIX in line)
        assert count == 1, f"Expected exactly 1 banner, found {count}"

    def test_banner_contains_no_template_vars(self) -> None:
        """Banner line must not contain {{ }} template variables."""
        banner = self._lines[0]
        assert "{{" not in banner and "}}" not in banner, (
            f"Banner must be a static literal; found template vars in: {banner!r}"
        )


# ---------------------------------------------------------------------------
# Cross-file consistency tests
# ---------------------------------------------------------------------------


class TestBannerConsistency:
    """Both recipe files must use identical banner format."""

    def test_same_banner_format_across_files(self) -> None:
        """Banner prefix and suffix must be identical across all recipe files."""
        smart = _load_recipe(SMART_ORCHESTRATOR)
        default = _load_recipe(DEFAULT_WORKFLOW)

        smart_step = _find_step(smart, CLASSIFY_STEP_ID)
        default_step = _find_step(default, CLARIFY_STEP_ID)

        smart_banner = smart_step["prompt"].splitlines()[0]
        default_banner = default_step["prompt"].splitlines()[0]

        # Both should start and end with identical sentinel tokens
        assert smart_banner.startswith(_BANNER_PREFIX)
        assert smart_banner.endswith(_BANNER_SUFFIX)
        assert default_banner.startswith(_BANNER_PREFIX)
        assert default_banner.endswith(_BANNER_SUFFIX)

    def test_banners_are_distinct_step_ids(self) -> None:
        """Each banner must embed a different step-id (no copy-paste duplication)."""
        smart = _load_recipe(SMART_ORCHESTRATOR)
        default = _load_recipe(DEFAULT_WORKFLOW)

        smart_banner = _find_step(smart, CLASSIFY_STEP_ID)["prompt"].splitlines()[0]
        default_banner = _find_step(default, CLARIFY_STEP_ID)["prompt"].splitlines()[0]

        smart_id = smart_banner[len(_BANNER_PREFIX) : -len(_BANNER_SUFFIX)]
        default_id = default_banner[len(_BANNER_PREFIX) : -len(_BANNER_SUFFIX)]

        assert smart_id != default_id, "Banners must embed distinct step IDs"
        assert smart_id == CLASSIFY_STEP_ID
        assert default_id == CLARIFY_STEP_ID
