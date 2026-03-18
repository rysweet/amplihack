"""Security tests for run_recipe_by_name working_dir validation and kwargs warnings.

Covers:
- SEC-03: working_dir must be validated by a new _validate_working_dir() helper
          before the Rust runner is invoked.  Shell metacharacters, non-existent
          paths, and file paths must all be rejected with ValueError.
- SEC-05: Unknown **kwargs passed to run_recipe_by_name must emit a
          DeprecationWarning naming the offending parameter.  Known-good calls
          must not emit any DeprecationWarning.

All tests are expected to FAIL against the current implementation because
the features they specify are NOT YET implemented.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from unittest.mock import patch

import pytest

_RECIPES_PKG = "amplihack.recipes"
_VALIDATION_PKG = "amplihack.recipes._validation"


def _noop_rust_runner(**kwargs):
    """Stub Rust runner that returns a minimal success RecipeResult."""
    from amplihack.recipes.models import RecipeResult, StepStatus

    return RecipeResult(
        recipe_name=kwargs.get("name", "stub"),
        steps=[],
        status=StepStatus.SUCCESS,
    )


# ============================================================================
# SEC-03: _validate_working_dir helper
# ============================================================================


class TestValidateWorkingDirHelper:
    """Specification for the _validate_working_dir(path) helper function."""

    def test_helper_is_importable(self):
        """_validate_working_dir must be importable from amplihack.recipes._validation."""
        from amplihack.recipes._validation import _validate_working_dir  # noqa: F401

    def test_valid_directory_returns_path_object(self, tmp_path):
        """A valid existing directory must return a pathlib.Path."""
        from amplihack.recipes._validation import _validate_working_dir

        result = _validate_working_dir(str(tmp_path))
        assert isinstance(result, Path)

    def test_valid_directory_path_matches_input(self, tmp_path):
        """The returned Path must resolve to the same directory as the input."""
        from amplihack.recipes._validation import _validate_working_dir

        result = _validate_working_dir(str(tmp_path))
        assert result.resolve() == tmp_path.resolve()

    def test_nonexistent_path_raises_value_error(self):
        """A path that does not exist must raise ValueError."""
        from amplihack.recipes._validation import _validate_working_dir

        with pytest.raises(ValueError, match="(?i)(not exist|no such|invalid|does not)"):
            _validate_working_dir("/tmp/__amplihack_nonexistent_xyzzy__")

    def test_file_path_raises_value_error(self, tmp_path):
        """Passing a file path instead of a directory must raise ValueError."""
        from amplihack.recipes._validation import _validate_working_dir

        f = tmp_path / "file.txt"
        f.write_text("x")
        with pytest.raises(ValueError, match="(?i)(not a dir|file|directory)"):
            _validate_working_dir(str(f))

    @pytest.mark.parametrize(
        "metachar",
        [";", "&", "|", "$", "(", ")", "{", "}", "[", "]", "<", ">", "\\", '"', "'"],
    )
    def test_shell_metacharacter_raises_value_error(self, metachar, tmp_path):
        """Any shell metacharacter in the path must raise ValueError (CWE-78 guard)."""
        from amplihack.recipes._validation import _validate_working_dir

        with pytest.raises(ValueError, match="(?i)(metachar|invalid|shell|forbidden|character)"):
            _validate_working_dir(str(tmp_path) + metachar + "injected")

    def test_semicolon_injection_raises_value_error(self, tmp_path):
        """Classic '; rm -rf /' pattern must be rejected before any path resolution."""
        from amplihack.recipes._validation import _validate_working_dir

        with pytest.raises(ValueError):
            _validate_working_dir(str(tmp_path) + "; rm -rf /")

    def test_dollar_subshell_raises_value_error(self, tmp_path):
        """$() subshell pattern in a working_dir path must be rejected."""
        from amplihack.recipes._validation import _validate_working_dir

        with pytest.raises(ValueError):
            _validate_working_dir(str(tmp_path) + "/$(malicious)")

    def test_backtick_raises_value_error(self, tmp_path):
        """Backtick command substitution in working_dir path must be rejected."""
        from amplihack.recipes._validation import _validate_working_dir

        with pytest.raises(ValueError):
            _validate_working_dir(str(tmp_path) + "/`whoami`")

    def test_pipe_raises_value_error(self, tmp_path):
        """Pipe character in working_dir path must be rejected."""
        from amplihack.recipes._validation import _validate_working_dir

        with pytest.raises(ValueError):
            _validate_working_dir(str(tmp_path) + "| cat /etc/passwd")


# ============================================================================
# SEC-03: run_recipe_by_name must call _validate_working_dir
# ============================================================================


class TestRunRecipeByNameCallsValidation:
    """run_recipe_by_name must delegate working_dir validation to _validate_working_dir."""

    def test_run_recipe_calls_validate_working_dir(self, tmp_path):
        """run_recipe_by_name must invoke _validate_working_dir with the working_dir arg."""
        validate_calls: list[str] = []

        def tracking_validate(path: str) -> Path:
            validate_calls.append(path)
            return Path(path)

        with (
            patch(_VALIDATION_PKG + "._validate_working_dir", side_effect=tracking_validate),
            patch(_RECIPES_PKG + ".run_recipe_via_rust", side_effect=_noop_rust_runner),
        ):
            from amplihack.recipes import run_recipe_by_name

            run_recipe_by_name("stub-recipe", working_dir=str(tmp_path))

        assert validate_calls, "run_recipe_by_name did not call _validate_working_dir"
        assert validate_calls[0] == str(tmp_path)

    def test_invalid_working_dir_raises_before_rust_is_called(self):
        """If _validate_working_dir raises ValueError, the Rust runner must NOT be called."""
        rust_calls: list = []

        def tracking_rust(**kwargs):
            rust_calls.append(kwargs)
            return _noop_rust_runner(**kwargs)

        with (
            patch(
                _VALIDATION_PKG + "._validate_working_dir",
                side_effect=ValueError("bad path"),
            ),
            patch(_RECIPES_PKG + ".run_recipe_via_rust", side_effect=tracking_rust),
        ):
            from amplihack.recipes import run_recipe_by_name

            with pytest.raises(ValueError):
                run_recipe_by_name("stub-recipe", working_dir="/nonexistent; rm -rf /")

        assert not rust_calls, "Rust runner must NOT be called when working_dir is invalid"

    def test_metachar_working_dir_propagates_value_error(self, tmp_path):
        """run_recipe_by_name must propagate ValueError from _validate_working_dir."""
        from amplihack.recipes import run_recipe_by_name

        with patch(_RECIPES_PKG + ".run_recipe_via_rust", side_effect=_noop_rust_runner):
            with pytest.raises(ValueError):
                run_recipe_by_name("stub-recipe", working_dir=str(tmp_path) + "; evil")

    def test_default_working_dir_dot_is_validated(self):
        """The default working_dir='.' must also be validated (regression guard)."""
        validate_calls: list[str] = []

        def tracking_validate(path: str) -> Path:
            validate_calls.append(path)
            return Path(path).resolve()

        with (
            patch(_VALIDATION_PKG + "._validate_working_dir", side_effect=tracking_validate),
            patch(_RECIPES_PKG + ".run_recipe_via_rust", side_effect=_noop_rust_runner),
        ):
            from amplihack.recipes import run_recipe_by_name

            run_recipe_by_name("stub-recipe")

        assert validate_calls, "Default '.' working_dir must also be validated"
        assert validate_calls[0] == "."


# ============================================================================
# SEC-05: DeprecationWarning for unknown kwargs
# ============================================================================


class TestDeprecationWarningForUnknownKwargs:
    """run_recipe_by_name must warn callers about unknown keyword arguments."""

    def test_unknown_kwarg_emits_deprecation_warning(self, tmp_path):
        """run_recipe_by_name('foo', adapter='old') must emit DeprecationWarning."""
        from amplihack.recipes import run_recipe_by_name

        with patch(_RECIPES_PKG + ".run_recipe_via_rust", side_effect=_noop_rust_runner):
            with pytest.warns(DeprecationWarning):
                run_recipe_by_name("stub-recipe", working_dir=str(tmp_path), adapter="old")

    def test_deprecation_warning_mentions_parameter_name(self, tmp_path):
        """The DeprecationWarning message must contain the unknown kwarg name."""
        from amplihack.recipes import run_recipe_by_name

        with patch(_RECIPES_PKG + ".run_recipe_via_rust", side_effect=_noop_rust_runner):
            with pytest.warns(DeprecationWarning, match="adapter"):
                run_recipe_by_name("stub-recipe", working_dir=str(tmp_path), adapter="old")

    def test_multiple_unknown_kwargs_each_emit_warning(self, tmp_path):
        """Each unrecognised kwarg must produce its own DeprecationWarning."""
        from amplihack.recipes import run_recipe_by_name

        with patch(_RECIPES_PKG + ".run_recipe_via_rust", side_effect=_noop_rust_runner):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                run_recipe_by_name(
                    "stub-recipe",
                    working_dir=str(tmp_path),
                    adapter="old",
                    engine="legacy",
                )

        deprecations = [x for x in w if issubclass(x.category, DeprecationWarning)]
        messages = {str(d.message) for d in deprecations}
        assert any("adapter" in s for s in messages), (
            f"'adapter' not mentioned in DeprecationWarning messages: {messages!r}"
        )
        assert any("engine" in s for s in messages), (
            f"'engine' not mentioned in DeprecationWarning messages: {messages!r}"
        )

    def test_no_unknown_kwargs_emits_no_deprecation_warning(self, tmp_path):
        """run_recipe_by_name with only known parameters must NOT emit DeprecationWarning."""
        from amplihack.recipes import run_recipe_by_name

        with patch(_RECIPES_PKG + ".run_recipe_via_rust", side_effect=_noop_rust_runner):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                run_recipe_by_name(
                    "stub-recipe",
                    working_dir=str(tmp_path),
                    dry_run=True,
                    progress=False,
                )

        deprecations = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert not deprecations, (
            f"Unexpected DeprecationWarning(s): {[str(d.message) for d in deprecations]!r}"
        )

    def test_all_documented_kwargs_are_not_flagged(self, tmp_path):
        """None of the documented named parameters must trigger DeprecationWarning."""
        from amplihack.recipes import run_recipe_by_name

        known = dict(
            user_context={"key": "val"},
            dry_run=False,
            recipe_dirs=None,
            working_dir=str(tmp_path),
            auto_stage=True,
            progress=False,
        )
        with patch(_RECIPES_PKG + ".run_recipe_via_rust", side_effect=_noop_rust_runner):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                run_recipe_by_name("stub-recipe", **known)

        deprecations = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert not deprecations, (
            f"Known parameters must not produce DeprecationWarning; "
            f"got: {[str(d.message) for d in deprecations]!r}"
        )
