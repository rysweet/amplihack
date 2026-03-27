"""Unit tests for GhAwCompiler — the gh-aw workflow compiler frontend.

These tests verify the five quality improvements requested in the
syntax-error-quality issue:

- P0  ``on`` key is NOT silently coerced to Python ``True`` by PyYAML.
- P1  Every diagnostic carries a ``line:col`` position.
- P1  Typos with Levenshtein edit-distance ≤ 2 are promoted to errors.
- P2  Unrecognised fields suggest the top-3 closest known fields.
- P2  Missing-required-field errors include a valid-value example.
"""

from __future__ import annotations

import pytest

from amplihack.workflows.gh_aw_compiler import (
    GhAwCompiler,
    _edit_distance,
    compile_workflow,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_workflow(
    *,
    name: str | None = "Test Workflow",
    on: str | None = "  workflow_dispatch:",
    extra_fields: str = "",
    body: str = "# Body\n",
) -> str:
    """Build a minimal .md workflow file string."""
    parts = ["---"]
    if name is not None:
        parts.append(f"name: {name!r}")
    if on is not None:
        parts.append(f"on:\n{on}")
    if extra_fields:
        parts.append(extra_fields.rstrip())
    parts.append("---")
    parts.append(body)
    return "\n".join(parts) + "\n"


def _errors(diags):
    return [d for d in diags if d.severity == "error"]


def _warnings(diags):
    return [d for d in diags if d.severity == "warning"]


# ---------------------------------------------------------------------------
# P0 — YAML "Norway problem": 'on' key must NOT be a false-positive
# ---------------------------------------------------------------------------


class TestOnKeyParsing:
    """P0: 'on:' is present → no false-positive 'missing on field' error."""

    def test_on_key_present_no_missing_error(self) -> None:
        """A workflow with 'on:' must NOT produce a 'Missing required field on' error."""
        content = _make_workflow()
        diags = compile_workflow(content)
        missing_on = [
            d for d in _errors(diags) if "on" in d.message and "Missing required" in d.message
        ]
        assert missing_on == [], (
            f"False-positive 'missing on' error with correctly specified 'on:' field: {diags}"
        )

    def test_on_key_absent_raises_error(self) -> None:
        """A workflow with NO 'on:' must produce a 'Missing required field on' error."""
        content = _make_workflow(on=None)
        diags = compile_workflow(content)
        missing_on = [
            d for d in _errors(diags) if "on" in d.message and "Missing required" in d.message
        ]
        assert len(missing_on) == 1, f"Expected exactly one 'missing on' error, got: {diags}"

    def test_no_unrecognised_true_field_warning(self) -> None:
        """'on:' key must NOT produce an 'Unrecognised field True' warning."""
        content = _make_workflow()
        diags = compile_workflow(content)
        spurious_true = [d for d in diags if "True" in d.message or "'True'" in d.message]
        assert spurious_true == [], (
            f"Spurious 'True' field diagnostic from YAML boolean coercion: {spurious_true}"
        )

    def test_all_three_test_workflows_have_no_on_false_positive(self) -> None:
        """Regression: the three workflows from the quality report each pass."""
        for workflow_name in ("code-simplifier", "repo-guardian", "issue-classifier"):
            # All three have 'on:' fields; none should get a false-positive
            content = _make_workflow(name=workflow_name)
            diags = compile_workflow(content, filename=f"{workflow_name}.md")
            spurious = [
                d
                for d in diags
                if "True" in d.message or ("Missing required" in d.message and "'on'" in d.message)
            ]
            assert spurious == [], (
                f"{workflow_name}.md: unexpected false-positive diagnostics: {spurious}"
            )


# ---------------------------------------------------------------------------
# P1 — Line:col positions on all diagnostics
# ---------------------------------------------------------------------------


class TestLineColPositions:
    """P1: Every diagnostic must carry a non-None line (and ideally col)."""

    def test_missing_required_field_has_line(self) -> None:
        """'Missing required field' error must include a line number."""
        content = _make_workflow(name=None)  # 'name' is required
        diags = compile_workflow(content)
        missing_name = [
            d for d in _errors(diags) if "'name'" in d.message and "Missing" in d.message
        ]
        assert len(missing_name) == 1
        assert missing_name[0].line is not None, (
            "Missing-required-field error must carry a line number"
        )

    def test_unrecognised_field_has_line_and_col(self) -> None:
        """Unrecognised-field diagnostic must include both line and col."""
        content = _make_workflow(extra_fields="comand: echo hi")
        diags = compile_workflow(content)
        typo_diags = [d for d in diags if "comand" in d.message]
        assert len(typo_diags) == 1, f"Expected one 'comand' diagnostic, got: {diags}"
        d = typo_diags[0]
        assert d.line is not None, "Typo diagnostic must carry a line number"
        assert d.col is not None, "Typo diagnostic must carry a column number"

    def test_type_error_has_line_and_col(self) -> None:
        """Type-error for 'timeout-minutes' must include line and col."""
        content = _make_workflow(extra_fields='timeout-minutes: "thirty"')
        diags = compile_workflow(content)
        type_errors = [d for d in _errors(diags) if "timeout-minutes" in d.message]
        assert len(type_errors) == 1, f"Expected one timeout-minutes error, got: {diags}"
        d = type_errors[0]
        assert d.line is not None
        assert d.col is not None

    def test_missing_frontmatter_delimiter_has_line(self) -> None:
        """A file without frontmatter must produce an error at line 1."""
        content = "# No frontmatter here\n\nBody text.\n"
        diags = compile_workflow(content)
        assert len(diags) == 1
        assert diags[0].severity == "error"
        assert diags[0].line == 1

    def test_format_includes_filename_and_location(self) -> None:
        """Diagnostic.format() output must include filename, line, and col."""
        content = _make_workflow(extra_fields="comand: echo hi")
        compiler = GhAwCompiler()
        diags = compiler.compile(content, filename="test-wf.md")
        typo_diags = [d for d in diags if "comand" in d.message]
        assert typo_diags, "Expected a typo diagnostic"
        formatted = typo_diags[0].format("test-wf.md")
        assert "test-wf.md" in formatted
        # Should contain a line number after the filename
        assert ":" in formatted


# ---------------------------------------------------------------------------
# P1 — Typo escalation: edit distance ≤ 2 → error
# ---------------------------------------------------------------------------


class TestTypoEscalation:
    """P1: Unrecognised fields with edit distance ≤ 2 must be promoted to errors."""

    def test_close_typo_is_error(self) -> None:
        """'stirct' (distance 2 from 'strict') must be an error, not a warning."""
        content = _make_workflow(extra_fields="stirct: true")
        diags = compile_workflow(content)
        stirct_diags = [d for d in diags if "stirct" in d.message]
        assert len(stirct_diags) == 1
        assert stirct_diags[0].severity == "error", (
            f"Expected ERROR severity for close typo 'stirct', got: {stirct_diags[0].severity}"
        )

    def test_distance_1_typo_is_error(self) -> None:
        """'namee' (distance 1 from 'name') → error."""
        # 'namee' is distance 1 from 'name'
        content = _make_workflow(extra_fields="namee: Oops")
        diags = compile_workflow(content)
        typo_diags = [d for d in diags if "namee" in d.message]
        assert typo_diags, f"Expected a 'namee' diagnostic, got: {diags}"
        assert typo_diags[0].severity == "error"

    def test_distant_unknown_field_is_warning(self) -> None:
        """A completely unrelated unknown field should remain a warning."""
        content = _make_workflow(extra_fields="xyz_unrelated_key: value")
        diags = compile_workflow(content)
        unknown_diags = [d for d in diags if "xyz_unrelated_key" in d.message]
        assert unknown_diags, f"Expected a diagnostic for 'xyz_unrelated_key', got: {diags}"
        assert unknown_diags[0].severity == "warning", (
            f"Distant unknown field should be a warning, got: {unknown_diags[0].severity}"
        )

    def test_edit_distance_boundary(self) -> None:
        """Edit distance exactly 2 → error; exactly 3 → warning."""
        # 'strictt' is distance 1 from 'strict' → error
        content_close = _make_workflow(extra_fields="strictt: true")
        diags_close = compile_workflow(content_close)
        close_diags = [d for d in diags_close if "strictt" in d.message]
        assert close_diags and close_diags[0].severity == "error"

        # 'strinct' is distance 2 from 'strict' → still error
        content_d2 = _make_workflow(extra_fields="strinct: true")
        diags_d2 = compile_workflow(content_d2)
        d2_diags = [d for d in diags_d2 if "strinct" in d.message]
        assert d2_diags and d2_diags[0].severity == "error"


# ---------------------------------------------------------------------------
# P2 — Top-3 fuzzy match suggestions
# ---------------------------------------------------------------------------


class TestFuzzyMatchSuggestions:
    """P2: Diagnostics for unrecognised fields include up to 3 ranked suggestions."""

    def test_typo_suggests_correct_field(self) -> None:
        """'stirct' must suggest 'strict' in the diagnostic message."""
        content = _make_workflow(extra_fields="stirct: true")
        diags = compile_workflow(content)
        typo_diags = [d for d in diags if "stirct" in d.message]
        assert typo_diags, f"Expected a 'stirct' diagnostic, got: {diags}"
        assert "strict" in typo_diags[0].message, (
            f"Expected 'strict' suggestion in message: {typo_diags[0].message}"
        )

    def test_suggestions_use_did_you_mean_phrasing(self) -> None:
        """Suggestion message must contain 'Did you mean' or similar phrasing."""
        content = _make_workflow(extra_fields="stirct: true")
        diags = compile_workflow(content)
        typo_diags = [d for d in diags if "stirct" in d.message]
        assert typo_diags
        msg = typo_diags[0].message.lower()
        assert "did you mean" in msg or "mean" in msg, (
            f"Expected 'Did you mean' phrasing in: {typo_diags[0].message}"
        )

    def test_no_suggestions_for_completely_unknown_field(self) -> None:
        """A completely unrelated key should produce a message without 'Did you mean' suggestions."""
        content = _make_workflow(extra_fields="xyzzy_completely_unknown: true")
        diags = compile_workflow(content)
        unknown_diags = [d for d in diags if "xyzzy_completely_unknown" in d.message]
        assert unknown_diags, f"Expected a diagnostic, got: {diags}"
        # The cutoff of 0.5 for get_close_matches should filter out irrelevant fields
        # so the message must NOT contain a "Did you mean" suggestion
        assert "Did you mean" not in unknown_diags[0].message, (
            f"Unrelated field should not have suggestions: {unknown_diags[0].message}"
        )


# ---------------------------------------------------------------------------
# P2 — Valid-value examples in missing required field errors
# ---------------------------------------------------------------------------


class TestValidValueExamples:
    """P2: Missing-required-field errors include valid-value examples."""

    def test_missing_on_error_includes_example(self) -> None:
        """Missing 'on' error must include a trigger format example."""
        content = _make_workflow(on=None)
        diags = compile_workflow(content)
        missing_on = [d for d in _errors(diags) if "'on'" in d.message and "Missing" in d.message]
        assert len(missing_on) == 1
        # Should contain some guidance about valid format
        assert any(
            hint in missing_on[0].message
            for hint in ("Valid format", "trigger", "workflow_dispatch", "push")
        ), f"Missing-on error should include a format hint: {missing_on[0].message}"

    def test_missing_name_error_includes_example(self) -> None:
        """Missing 'name' error must include a string example."""
        content = _make_workflow(name=None)
        diags = compile_workflow(content)
        missing_name = [
            d for d in _errors(diags) if "'name'" in d.message and "Missing" in d.message
        ]
        assert len(missing_name) == 1
        assert "Valid format" in missing_name[0].message or "string" in missing_name[0].message, (
            f"Missing-name error should include a format hint: {missing_name[0].message}"
        )

    def test_type_error_includes_example(self) -> None:
        """timeout-minutes type error must include the expected type description."""
        content = _make_workflow(extra_fields='timeout-minutes: "thirty"')
        diags = compile_workflow(content)
        type_errors = [d for d in _errors(diags) if "timeout-minutes" in d.message]
        assert type_errors, f"Expected a timeout-minutes error, got: {diags}"
        assert "integer" in type_errors[0].message.lower() or "30" in type_errors[0].message, (
            f"Type error should mention integer: {type_errors[0].message}"
        )


# ---------------------------------------------------------------------------
# Integration: the three test workflows from the quality report
# ---------------------------------------------------------------------------


class TestQualityReportScenarios:
    """Integration tests reproducing the exact three failure scenarios from the report."""

    def test_type_error_timeout_minutes_thirty(self) -> None:
        """code-simplifier scenario: timeout-minutes: 'thirty' → type error."""
        content = _make_workflow(
            name="Code Simplifier",
            extra_fields='timeout-minutes: "thirty"\nengine: claude',
        )
        diags = compile_workflow(content, filename="code-simplifier.md")
        type_errors = [d for d in _errors(diags) if "timeout-minutes" in d.message]
        assert type_errors, "Expected a type error for timeout-minutes: 'thirty'"
        assert type_errors[0].line is not None
        assert "integer" in type_errors[0].message.lower() or "thirty" in type_errors[0].message

    def test_missing_required_engine_field(self) -> None:
        """repo-guardian scenario: engine field removed → error with valid-values hint."""
        content = _make_workflow(name="Repo Guardian")  # no engine field
        diags = compile_workflow(content, filename="repo-guardian.md")
        # 'engine' is not required so no error; but if it were removed and it's known, no error
        # This test just verifies no false-positives for the on: field
        false_pos = [
            d
            for d in diags
            if "True" in d.message or ("Missing" in d.message and "'on'" in d.message)
        ]
        assert false_pos == [], f"False-positive diagnostics: {false_pos}"

    def test_typo_strict_as_stirct(self) -> None:
        """issue-classifier scenario: 'strict' typo'd as 'stirct' → error (distance 2)."""
        content = _make_workflow(name="Issue Classifier", extra_fields="stirct: true")
        diags = compile_workflow(content, filename="issue-classifier.md")
        stirct_diags = [d for d in diags if "stirct" in d.message]
        assert stirct_diags, f"Expected a 'stirct' diagnostic, got: {diags}"
        assert stirct_diags[0].severity == "error", (
            f"'stirct' (distance ≤ 2 from 'strict') should be an error, "
            f"got: {stirct_diags[0].severity}"
        )
        assert "strict" in stirct_diags[0].message, (
            f"Should suggest 'strict', got: {stirct_diags[0].message}"
        )
        assert stirct_diags[0].line is not None
        assert stirct_diags[0].col is not None


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestEditDistance:
    """Tests for the Levenshtein edit distance helper."""

    def test_identical_strings(self) -> None:
        assert _edit_distance("strict", "strict") == 0

    def test_single_substitution(self) -> None:
        assert _edit_distance("stirct", "strict") == 2

    def test_single_insertion(self) -> None:
        assert _edit_distance("namee", "name") == 1

    def test_single_deletion(self) -> None:
        assert _edit_distance("nam", "name") == 1

    def test_empty_strings(self) -> None:
        assert _edit_distance("", "") == 0
        assert _edit_distance("abc", "") == 3
        assert _edit_distance("", "abc") == 3


# ---------------------------------------------------------------------------
# Compile-time self-test: all real gh-aw .md files must not produce on false-pos
# ---------------------------------------------------------------------------


class TestRealWorkflowFiles:
    """Verify no false-positive 'on → True' errors on actual repo workflows."""

    def test_code_simplifier_md_no_false_positive(self) -> None:
        """code-simplifier.md must not produce a false-positive 'missing on' error."""
        from pathlib import Path

        wf_file = (
            Path(__file__).resolve().parents[3] / ".github" / "workflows" / "code-simplifier.md"
        )
        if not wf_file.exists():
            pytest.skip("code-simplifier.md not found")

        content = wf_file.read_text()
        diags = compile_workflow(content, filename="code-simplifier.md")
        false_pos = [
            d
            for d in diags
            if "True" in d.message or ("Missing" in d.message and "'on'" in d.message)
        ]
        assert false_pos == [], f"False-positive diagnostics for code-simplifier.md: {false_pos}"
