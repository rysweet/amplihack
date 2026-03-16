"""Tests for _common_launcher_startup() — the consolidated launcher initialization.

Verifies that all 5 startup steps run correctly and in order for every
launcher path (launch, claude, RustyClawd, copilot, codex, amplifier).

Covers:
- Idempotency guard (double-call safe for RustyClawd → launch_command)
- subprocess_safe skip
- Nesting detection and auto-staging
- Framework staging (_ensure_amplihack_staged)
- Rust recipe runner check (_ensure_rust_recipe_runner)
- SDK dependency check
- Power-steering re-enable prompt
"""

import argparse
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest


def _make_args(**overrides) -> argparse.Namespace:
    """Build a minimal args Namespace for testing."""
    defaults = {
        "command": "launch",
        "verbose": False,
        "quiet": False,
        "subprocess_safe": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


# ---------------------------------------------------------------------------
# Patch targets — all inside amplihack.cli
# ---------------------------------------------------------------------------
_NESTING_DETECTOR = "amplihack.cli.NestingDetector"
_AUTO_STAGER = "amplihack.cli.AutoStager"
_ENSURE_STAGED = "amplihack.cli._ensure_amplihack_staged"
_ENSURE_RUST = "amplihack.cli._ensure_rust_recipe_runner"
_ENSURE_SDK = "amplihack.cli.ensure_sdk_deps"
_POWER_STEERING = "amplihack.cli.prompt_re_enable_if_disabled"


def _patch_all_steps():
    """Return a dict of patches that mock all startup steps.

    The nesting detector and auto-stager are imported locally inside the
    function, so we patch at the module level where they'll be resolved.
    """
    mock_nesting_result = MagicMock(
        is_nested=False,
        requires_staging=False,
        parent_session_id=None,
    )
    mock_detector = MagicMock()
    mock_detector.detect_nesting.return_value = mock_nesting_result

    mock_sdk_result = MagicMock(all_ok=True, missing=[])

    return {
        "amplihack.launcher.nesting_detector.NestingDetector": MagicMock(
            return_value=mock_detector
        ),
        "amplihack.launcher.auto_stager.AutoStager": MagicMock(),
        _ENSURE_STAGED: MagicMock(),
        _ENSURE_RUST: MagicMock(),
        "amplihack.dep_check.ensure_sdk_deps": MagicMock(return_value=mock_sdk_result),
        "amplihack.power_steering.re_enable_prompt.prompt_re_enable_if_disabled": MagicMock(),
    }


# ---------------------------------------------------------------------------
# Core behavior tests
# ---------------------------------------------------------------------------


class TestIdempotency:
    """_common_launcher_startup must be safe to call multiple times."""

    def test_second_call_is_noop(self):
        """When called twice on the same args, second call does nothing."""
        from amplihack.cli import _common_launcher_startup

        args = _make_args()

        with (
            patch(_ENSURE_STAGED) as mock_staged,
            patch(_ENSURE_RUST) as mock_rust,
            patch(
                "amplihack.launcher.nesting_detector.NestingDetector",
                return_value=MagicMock(
                    detect_nesting=MagicMock(
                        return_value=MagicMock(
                            is_nested=False, requires_staging=False, parent_session_id=None
                        )
                    )
                ),
            ),
            patch("amplihack.dep_check.ensure_sdk_deps", side_effect=ImportError),
            patch(
                "amplihack.power_steering.re_enable_prompt.prompt_re_enable_if_disabled",
                side_effect=ImportError,
            ),
        ):
            _common_launcher_startup(args)
            _common_launcher_startup(args)  # second call

            # Each step should only run once
            mock_staged.assert_called_once()
            mock_rust.assert_called_once()

    def test_startup_done_flag_set(self):
        """After first call, _startup_done flag is set on args."""
        from amplihack.cli import _common_launcher_startup

        args = _make_args()

        with (
            patch(_ENSURE_STAGED),
            patch(_ENSURE_RUST),
            patch(
                "amplihack.launcher.nesting_detector.NestingDetector",
                return_value=MagicMock(
                    detect_nesting=MagicMock(
                        return_value=MagicMock(
                            is_nested=False, requires_staging=False, parent_session_id=None
                        )
                    )
                ),
            ),
            patch("amplihack.dep_check.ensure_sdk_deps", side_effect=ImportError),
            patch(
                "amplihack.power_steering.re_enable_prompt.prompt_re_enable_if_disabled",
                side_effect=ImportError,
            ),
        ):
            assert not getattr(args, "_startup_done", False)
            _common_launcher_startup(args)
            assert args._startup_done is True


class TestSubprocessSafe:
    """subprocess_safe mode must skip all initialization."""

    def test_skips_all_steps(self):
        """With subprocess_safe=True, no startup steps run."""
        from amplihack.cli import _common_launcher_startup

        args = _make_args(subprocess_safe=True)

        with (
            patch(_ENSURE_STAGED) as mock_staged,
            patch(_ENSURE_RUST) as mock_rust,
        ):
            _common_launcher_startup(args)

            mock_staged.assert_not_called()
            mock_rust.assert_not_called()

    def test_startup_done_flag_still_set(self):
        """Even in subprocess_safe, the idempotency flag is set."""
        from amplihack.cli import _common_launcher_startup

        args = _make_args(subprocess_safe=True)
        _common_launcher_startup(args)
        assert args._startup_done is True


class TestNestingDetection:
    """Nesting detection must run and auto-stage if needed."""

    def test_nesting_result_stored_on_args(self):
        """The nesting result is stored as args._nesting_result."""
        from amplihack.cli import _common_launcher_startup

        args = _make_args()
        mock_result = MagicMock(is_nested=False, requires_staging=False, parent_session_id=None)

        with (
            patch(
                "amplihack.launcher.nesting_detector.NestingDetector",
                return_value=MagicMock(detect_nesting=MagicMock(return_value=mock_result)),
            ),
            patch(_ENSURE_STAGED),
            patch(_ENSURE_RUST),
            patch("amplihack.dep_check.ensure_sdk_deps", side_effect=ImportError),
            patch(
                "amplihack.power_steering.re_enable_prompt.prompt_re_enable_if_disabled",
                side_effect=ImportError,
            ),
        ):
            _common_launcher_startup(args)
            assert args._nesting_result is mock_result

    def test_auto_staging_triggered_when_nested(self):
        """When nesting requires staging, AutoStager is invoked and cwd changes."""
        from amplihack.cli import _common_launcher_startup

        args = _make_args()
        mock_nesting = MagicMock(
            is_nested=True, requires_staging=True, parent_session_id="parent-123"
        )
        mock_staging_result = MagicMock(temp_root=Path("/tmp/staged"))

        mock_detector = MagicMock()
        mock_detector.detect_nesting.return_value = mock_nesting

        mock_stager = MagicMock()
        mock_stager.stage_for_nested_execution.return_value = mock_staging_result

        with (
            patch(
                "amplihack.launcher.nesting_detector.NestingDetector",
                return_value=mock_detector,
            ),
            patch(
                "amplihack.launcher.auto_stager.AutoStager",
                return_value=mock_stager,
            ),
            patch("amplihack.cli.os.chdir") as mock_chdir,
            patch(_ENSURE_STAGED),
            patch(_ENSURE_RUST),
            patch("amplihack.dep_check.ensure_sdk_deps", side_effect=ImportError),
            patch(
                "amplihack.power_steering.re_enable_prompt.prompt_re_enable_if_disabled",
                side_effect=ImportError,
            ),
        ):
            _common_launcher_startup(args)
            mock_stager.stage_for_nested_execution.assert_called_once()
            mock_chdir.assert_called_once_with(Path("/tmp/staged"))

    def test_no_staging_when_not_nested(self):
        """When not nested, AutoStager is NOT invoked."""
        from amplihack.cli import _common_launcher_startup

        args = _make_args()
        mock_nesting = MagicMock(is_nested=False, requires_staging=False, parent_session_id=None)

        with (
            patch(
                "amplihack.launcher.nesting_detector.NestingDetector",
                return_value=MagicMock(detect_nesting=MagicMock(return_value=mock_nesting)),
            ),
            patch("amplihack.launcher.auto_stager.AutoStager") as mock_stager_cls,
            patch(_ENSURE_STAGED),
            patch(_ENSURE_RUST),
            patch("amplihack.dep_check.ensure_sdk_deps", side_effect=ImportError),
            patch(
                "amplihack.power_steering.re_enable_prompt.prompt_re_enable_if_disabled",
                side_effect=ImportError,
            ),
        ):
            _common_launcher_startup(args)
            mock_stager_cls.return_value.stage_for_nested_execution.assert_not_called()


class TestStartupStepsOrder:
    """All 5 startup steps must run in correct order."""

    def test_all_steps_called(self):
        """Verify staging, rust runner, SDK deps, and power-steering all run."""
        from amplihack.cli import _common_launcher_startup

        args = _make_args()
        call_order = []

        mock_nesting = MagicMock(is_nested=False, requires_staging=False, parent_session_id=None)
        mock_sdk_result = MagicMock(all_ok=True, missing=[])

        with (
            patch(
                "amplihack.launcher.nesting_detector.NestingDetector",
                return_value=MagicMock(detect_nesting=MagicMock(return_value=mock_nesting)),
            ),
            patch(
                _ENSURE_STAGED,
                side_effect=lambda: call_order.append("staged"),
            ),
            patch(
                _ENSURE_RUST,
                side_effect=lambda: call_order.append("rust"),
            ),
            patch(
                "amplihack.dep_check.ensure_sdk_deps",
                side_effect=lambda: (call_order.append("sdk"), mock_sdk_result)[-1],
            ),
            patch(
                "amplihack.power_steering.re_enable_prompt.prompt_re_enable_if_disabled",
                side_effect=lambda: call_order.append("power_steering"),
            ),
        ):
            _common_launcher_startup(args)

            assert call_order == ["staged", "rust", "sdk", "power_steering"]

    def test_sdk_dep_failure_is_nonfatal(self):
        """SDK dep check failure doesn't stop startup."""
        from amplihack.cli import _common_launcher_startup

        args = _make_args()

        with (
            patch(
                "amplihack.launcher.nesting_detector.NestingDetector",
                return_value=MagicMock(
                    detect_nesting=MagicMock(
                        return_value=MagicMock(
                            is_nested=False,
                            requires_staging=False,
                            parent_session_id=None,
                        )
                    )
                ),
            ),
            patch(_ENSURE_STAGED),
            patch(_ENSURE_RUST) as mock_rust,
            patch(
                "amplihack.dep_check.ensure_sdk_deps",
                side_effect=RuntimeError("dep check broke"),
            ),
            patch(
                "amplihack.power_steering.re_enable_prompt.prompt_re_enable_if_disabled"
            ) as mock_ps,
        ):
            # Should NOT raise
            _common_launcher_startup(args)

            # Downstream steps still ran
            mock_rust.assert_called_once()
            mock_ps.assert_called_once()

    def test_power_steering_failure_is_nonfatal(self):
        """Power-steering prompt failure doesn't stop startup."""
        from amplihack.cli import _common_launcher_startup

        args = _make_args()

        with (
            patch(
                "amplihack.launcher.nesting_detector.NestingDetector",
                return_value=MagicMock(
                    detect_nesting=MagicMock(
                        return_value=MagicMock(
                            is_nested=False,
                            requires_staging=False,
                            parent_session_id=None,
                        )
                    )
                ),
            ),
            patch(_ENSURE_STAGED) as mock_staged,
            patch(_ENSURE_RUST) as mock_rust,
            patch("amplihack.dep_check.ensure_sdk_deps", side_effect=ImportError),
            patch(
                "amplihack.power_steering.re_enable_prompt.prompt_re_enable_if_disabled",
                side_effect=RuntimeError("power steering broke"),
            ),
        ):
            # Should NOT raise
            _common_launcher_startup(args)

            # Upstream steps still ran
            mock_staged.assert_called_once()
            mock_rust.assert_called_once()


class TestEnsureRustRecipeRunner:
    """Tests for the _ensure_rust_recipe_runner helper."""

    def test_prints_success_when_installed(self, capsys):
        """When binary is available, prints success message."""
        from amplihack.cli import _ensure_rust_recipe_runner

        with patch("amplihack.recipes.rust_runner.ensure_rust_recipe_runner", return_value=True):
            _ensure_rust_recipe_runner()

        captured = capsys.readouterr()
        assert "Rust recipe runner available" in captured.out

    def test_prints_warning_when_not_installed(self, capsys):
        """When binary is missing, prints install instructions."""
        from amplihack.cli import _ensure_rust_recipe_runner

        with patch("amplihack.recipes.rust_runner.ensure_rust_recipe_runner", return_value=False):
            _ensure_rust_recipe_runner()

        captured = capsys.readouterr()
        assert "not installed" in captured.out
        assert "rustup.rs" in captured.out

    def test_import_error_is_nonfatal(self):
        """If rust_runner module can't be imported, doesn't crash."""
        from amplihack.cli import _ensure_rust_recipe_runner

        with patch(
            "amplihack.recipes.rust_runner.ensure_rust_recipe_runner",
            side_effect=ImportError("no module"),
        ):
            # Should NOT raise
            _ensure_rust_recipe_runner()


# ---------------------------------------------------------------------------
# Integration-style: verify each command path calls _common_launcher_startup
# ---------------------------------------------------------------------------


class TestAllLauncherPathsCallStartup:
    """Every launcher command must call _common_launcher_startup."""

    @pytest.mark.parametrize(
        "command",
        ["launch", "claude", "copilot", "codex", "amplifier"],
    )
    def test_command_calls_common_startup(self, command):
        """Each launcher command invokes _common_launcher_startup."""
        from amplihack.cli import main

        args = _make_args(command=command, skip_update_check=True, no_proxy=True)

        patches = {
            "amplihack.cli.parse_args_with_passthrough": MagicMock(return_value=(args, [])),
            "amplihack.cli._common_launcher_startup": MagicMock(),
            "amplihack.cli.is_uvx_deployment": MagicMock(return_value=False),
            "amplihack.cli.cleanup_legacy_skills": MagicMock(),
        }

        import contextlib

        with contextlib.ExitStack() as stack:
            mock_startup = None
            for target, mock_obj in patches.items():
                m = stack.enter_context(patch(target, mock_obj))
                if target == "amplihack.cli._common_launcher_startup":
                    mock_startup = m

            try:
                main()
            except (SystemExit, Exception):
                # Commands will fail after startup (unmocked launchers), that's fine
                pass

            mock_startup.assert_called_once_with(args)

    def test_rustyclawd_calls_startup_twice_but_idempotent(self):
        """RustyClawd calls startup in its own block then via launch_command().

        The idempotency guard in _common_launcher_startup ensures only the
        first call actually runs the init steps.
        """
        from amplihack.cli import main

        args = _make_args(command="RustyClawd", skip_update_check=True, no_proxy=True)

        patches = {
            "amplihack.cli.parse_args_with_passthrough": MagicMock(return_value=(args, [])),
            "amplihack.cli._common_launcher_startup": MagicMock(),
            "amplihack.cli.is_uvx_deployment": MagicMock(return_value=False),
            "amplihack.cli.cleanup_legacy_skills": MagicMock(),
        }

        import contextlib

        with contextlib.ExitStack() as stack:
            mock_startup = None
            for target, mock_obj in patches.items():
                m = stack.enter_context(patch(target, mock_obj))
                if target == "amplihack.cli._common_launcher_startup":
                    mock_startup = m

            try:
                main()
            except (SystemExit, Exception):
                pass

            # Called twice: once from RustyClawd block, once from launch_command()
            assert mock_startup.call_count == 2
            # Both calls use the same args object
            for c in mock_startup.call_args_list:
                assert c == call(args)
