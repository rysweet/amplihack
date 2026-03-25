"""TDD tests for amplihack.worktree.git_utils module.

Contract defined here:
  1. Import produces zero bytes on stderr
  2. get_shared_runtime_dir() returns a str (path-like)
  3. Result is deterministic for the same input (LRU cache)
  4. Main-repo scenario: returns project_root/.claude/runtime
  5. Worktree scenario: returns main_repo/.claude/runtime
  6. Fail-open: git failure → returns project_root/.claude/runtime
  7. Fail-open: timeout → returns project_root/.claude/runtime
  8. Fail-open: not a git repo (non-zero exit) → returns default
  9. Fail-open: empty git output → returns default
 10. __all__ exports only get_shared_runtime_dir

 Security contract (implemented):
 11. Created directory has 0o700 (owner-only) permissions
 12. AMPLIHACK_RUNTIME_DIR env-var overrides the default path
 13. AMPLIHACK_RUNTIME_DIR outside allowed roots (home / /tmp) raises RuntimeError
 14. AMPLIHACK_RUNTIME_DIR within home dir is accepted
"""

from __future__ import annotations

import stat
import subprocess
import sys
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clear_lru_cache() -> None:
    """Clear the LRU cache on get_shared_runtime_dir between tests."""
    from amplihack.worktree.git_utils import get_shared_runtime_dir

    get_shared_runtime_dir.cache_clear()


def _make_git_result(stdout: str, returncode: int = 0) -> CompletedProcess:
    return CompletedProcess(
        args=["git", "rev-parse", "--git-common-dir"],
        returncode=returncode,
        stdout=stdout,
        stderr="",
    )


# ---------------------------------------------------------------------------
# 1. Zero-stderr import
# ---------------------------------------------------------------------------
class TestZeroStderrImport:
    """Importing the module must not write anything to stderr."""

    def test_import_produces_zero_stderr(self, capsys):
        """Importing amplihack.worktree.git_utils must produce no stderr output."""
        # Force re-import to catch any module-level side effects.
        import importlib

        # Remove from cache so the import machinery runs again
        import amplihack.worktree.git_utils as _mod

        importlib.reload(_mod)

        captured = capsys.readouterr()
        assert captured.err == "", (
            f"Import of amplihack.worktree.git_utils wrote to stderr: {captured.err!r}"
        )

    def test_import_via_subprocess_produces_zero_stderr(self):
        """Subprocess import must produce exactly zero bytes on stderr."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import amplihack.worktree.git_utils",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.stderr == "", f"Subprocess import produced stderr: {result.stderr!r}"


# ---------------------------------------------------------------------------
# 2 & 3. Return type and determinism
# ---------------------------------------------------------------------------
class TestReturnTypeAndDeterminism:
    """get_shared_runtime_dir must return str and cache results."""

    def setup_method(self):
        _clear_lru_cache()

    def teardown_method(self):
        _clear_lru_cache()

    def test_returns_str(self, tmp_path):
        """Return type must be str (not Path)."""
        with patch("subprocess.run", return_value=_make_git_result(".git")):
            from amplihack.worktree.git_utils import get_shared_runtime_dir

            result = get_shared_runtime_dir(str(tmp_path))
        assert isinstance(result, str), f"Expected str, got {type(result)}"

    def test_result_ends_with_claude_runtime(self, tmp_path):
        """Returned path must end with .claude/runtime."""
        with patch("subprocess.run", return_value=_make_git_result(".git")):
            from amplihack.worktree.git_utils import get_shared_runtime_dir

            result = get_shared_runtime_dir(str(tmp_path))
        assert result.endswith(".claude/runtime") or result.endswith(".claude\\runtime"), (
            f"Result does not end with .claude/runtime: {result!r}"
        )

    def test_result_is_deterministic_same_input(self, tmp_path):
        """Same input must yield the same result (LRU cache)."""
        from amplihack.worktree.git_utils import get_shared_runtime_dir

        call_count = 0

        def fake_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return _make_git_result(".git")

        with patch("subprocess.run", side_effect=fake_run):
            r1 = get_shared_runtime_dir(str(tmp_path))
            r2 = get_shared_runtime_dir(str(tmp_path))

        assert r1 == r2
        assert call_count == 1, (
            "subprocess.run was called more than once for identical input — "
            "LRU cache appears to be bypassed"
        )

    def test_different_inputs_produce_different_results(self, tmp_path):
        """Different project roots must produce different results."""
        from amplihack.worktree.git_utils import get_shared_runtime_dir

        root_a = tmp_path / "alpha"
        root_b = tmp_path / "beta"
        root_a.mkdir()
        root_b.mkdir()

        with patch("subprocess.run", return_value=_make_git_result(".git")):
            ra = get_shared_runtime_dir(str(root_a))
            rb = get_shared_runtime_dir(str(root_b))

        assert ra != rb


# ---------------------------------------------------------------------------
# 4. Main-repo path resolution
# ---------------------------------------------------------------------------
class TestMainRepoResolution:
    """In a main repo, must return project_root/.claude/runtime."""

    def setup_method(self):
        _clear_lru_cache()

    def teardown_method(self):
        _clear_lru_cache()

    def test_main_repo_returns_project_root_runtime(self, tmp_path):
        """When git says .git (relative → same repo), return project_root/.claude/runtime."""
        from amplihack.worktree.git_utils import get_shared_runtime_dir

        # In a main repo git --git-common-dir returns ".git" (relative path)
        with patch("subprocess.run", return_value=_make_git_result(".git")):
            result = get_shared_runtime_dir(str(tmp_path))

        expected = str(tmp_path.resolve() / ".claude" / "runtime")
        assert result == expected, f"Expected {expected!r}, got {result!r}"

    def test_main_repo_accepts_path_object(self, tmp_path):
        """Should accept a pathlib.Path as project_root, not just str."""
        from amplihack.worktree.git_utils import get_shared_runtime_dir

        with patch("subprocess.run", return_value=_make_git_result(".git")):
            result = get_shared_runtime_dir(tmp_path)  # Pass Path, not str

        expected = str(tmp_path.resolve() / ".claude" / "runtime")
        assert result == expected


# ---------------------------------------------------------------------------
# 5. Worktree path resolution
# ---------------------------------------------------------------------------
class TestWorktreeResolution:
    """In a git worktree, must return main_repo/.claude/runtime."""

    def setup_method(self):
        _clear_lru_cache()

    def teardown_method(self):
        _clear_lru_cache()

    def test_worktree_uses_main_repo_runtime(self, tmp_path):
        """When git-common-dir points to a .git outside project_root, return main_repo/.claude/runtime."""
        from amplihack.worktree.git_utils import get_shared_runtime_dir

        # Simulate: main_repo is tmp_path/main, worktree is tmp_path/worktrees/feat
        main_repo = tmp_path / "main"
        main_repo.mkdir()
        worktree = tmp_path / "worktrees" / "feat"
        worktree.mkdir(parents=True)

        # git rev-parse --git-common-dir in a worktree returns absolute path to main .git
        main_git = main_repo / ".git"
        main_git.mkdir()

        with patch(
            "subprocess.run",
            return_value=_make_git_result(str(main_git)),
        ):
            result = get_shared_runtime_dir(str(worktree))

        expected = str(main_repo / ".claude" / "runtime")
        assert result == expected, f"Expected {expected!r}, got {result!r}"

    def test_worktree_non_dot_git_common_dir(self, tmp_path):
        """When git-common-dir is a path that doesn't end in '.git', use it as main_repo root."""
        from amplihack.worktree.git_utils import get_shared_runtime_dir

        main_repo = tmp_path / "main"
        main_repo.mkdir()
        worktree = tmp_path / "worktrees" / "feat"
        worktree.mkdir(parents=True)

        # Some git configurations return the bare repo path (not ending in .git)
        with patch(
            "subprocess.run",
            return_value=_make_git_result(str(main_repo)),
        ):
            result = get_shared_runtime_dir(str(worktree))

        expected = str(main_repo / ".claude" / "runtime")
        assert result == expected, f"Expected {expected!r}, got {result!r}"


# ---------------------------------------------------------------------------
# 6. Fail-open: subprocess failures
# ---------------------------------------------------------------------------
class TestFailOpenSubprocessFailures:
    """Subprocess failures must never raise — always return the default path."""

    def setup_method(self):
        _clear_lru_cache()

    def teardown_method(self):
        _clear_lru_cache()

    def test_git_nonzero_exit_returns_default(self, tmp_path):
        """Non-zero git returncode → return project_root/.claude/runtime."""
        from amplihack.worktree.git_utils import get_shared_runtime_dir

        not_git = _make_git_result("", returncode=128)  # git's "not a repo" exit code
        with patch("subprocess.run", return_value=not_git):
            result = get_shared_runtime_dir(str(tmp_path))

        expected = str(tmp_path.resolve() / ".claude" / "runtime")
        assert result == expected

    def test_git_empty_stdout_returns_default(self, tmp_path):
        """Empty git stdout → return project_root/.claude/runtime."""
        from amplihack.worktree.git_utils import get_shared_runtime_dir

        empty = _make_git_result("", returncode=0)
        with patch("subprocess.run", return_value=empty):
            result = get_shared_runtime_dir(str(tmp_path))

        expected = str(tmp_path.resolve() / ".claude" / "runtime")
        assert result == expected

    def test_git_whitespace_only_stdout_returns_default(self, tmp_path):
        """Whitespace-only git stdout → return project_root/.claude/runtime."""
        from amplihack.worktree.git_utils import get_shared_runtime_dir

        whitespace = _make_git_result("   \n\t  ", returncode=0)
        with patch("subprocess.run", return_value=whitespace):
            result = get_shared_runtime_dir(str(tmp_path))

        expected = str(tmp_path.resolve() / ".claude" / "runtime")
        assert result == expected

    def test_git_not_found_filenotfounderror_returns_default(self, tmp_path):
        """FileNotFoundError (git not installed) → return project_root/.claude/runtime."""
        from amplihack.worktree.git_utils import get_shared_runtime_dir

        with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
            result = get_shared_runtime_dir(str(tmp_path))

        expected = str(tmp_path.resolve() / ".claude" / "runtime")
        assert result == expected

    def test_generic_exception_returns_default(self, tmp_path):
        """Any unexpected exception → return project_root/.claude/runtime."""
        from amplihack.worktree.git_utils import get_shared_runtime_dir

        with patch("subprocess.run", side_effect=RuntimeError("unexpected")):
            result = get_shared_runtime_dir(str(tmp_path))

        expected = str(tmp_path.resolve() / ".claude" / "runtime")
        assert result == expected


# ---------------------------------------------------------------------------
# 7. Fail-open: timeout
# ---------------------------------------------------------------------------
class TestFailOpenTimeout:
    """Subprocess timeout must never raise — return the default path."""

    def setup_method(self):
        _clear_lru_cache()

    def teardown_method(self):
        _clear_lru_cache()

    def test_timeout_returns_default(self, tmp_path):
        """subprocess.TimeoutExpired → return project_root/.claude/runtime."""
        from amplihack.worktree.git_utils import get_shared_runtime_dir

        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=5),
        ):
            result = get_shared_runtime_dir(str(tmp_path))

        expected = str(tmp_path.resolve() / ".claude" / "runtime")
        assert result == expected

    def test_timeout_does_not_raise(self, tmp_path):
        """TimeoutExpired must never propagate to caller."""
        from amplihack.worktree.git_utils import get_shared_runtime_dir

        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=5),
        ):
            try:
                get_shared_runtime_dir(str(tmp_path))
            except subprocess.TimeoutExpired:
                pytest.fail("TimeoutExpired was not caught — fail-open contract violated")


# ---------------------------------------------------------------------------
# 8. Module API surface
# ---------------------------------------------------------------------------
class TestModuleApiSurface:
    """Module must export only what the design spec declares."""

    def test_all_exports_only_get_shared_runtime_dir(self):
        """__all__ must contain exactly ['get_shared_runtime_dir']."""
        import amplihack.worktree.git_utils as m

        assert hasattr(m, "__all__")
        assert list(m.__all__) == ["get_shared_runtime_dir"], (
            f"Unexpected __all__ contents: {m.__all__!r}"
        )

    def test_get_shared_runtime_dir_is_callable(self):
        """get_shared_runtime_dir must be a callable."""
        from amplihack.worktree.git_utils import get_shared_runtime_dir

        assert callable(get_shared_runtime_dir)

    def test_worktree_package_importable(self):
        """amplihack.worktree must be importable as a package."""
        import amplihack.worktree  # noqa: F401

    def test_worktree_init_exports_nothing_sensitive(self):
        """amplihack.worktree.__init__ must not inadvertently shadow git_utils."""
        import amplihack.worktree as pkg

        # The __init__.py is intentionally minimal; git_utils is a sub-module
        assert not hasattr(pkg, "get_shared_runtime_dir") or callable(
            getattr(pkg, "get_shared_runtime_dir", None)
        ), "If re-exported, must remain callable"


# ---------------------------------------------------------------------------
# 9. _collect_dep_status: zero output, correct result shape
# ---------------------------------------------------------------------------
class TestCollectDepStatus:
    """_collect_dep_status() must be quiet and return the correct shape."""

    def test_returns_dep_check_result(self):
        """_collect_dep_status must return a DepCheckResult instance."""
        from amplihack.dep_check import DepCheckResult, _collect_dep_status

        result = _collect_dep_status()
        assert isinstance(result, DepCheckResult)

    def test_produces_no_stderr(self, capsys):
        """_collect_dep_status must not write to stderr."""
        from amplihack.dep_check import _collect_dep_status

        _collect_dep_status()
        captured = capsys.readouterr()
        assert captured.err == "", f"_collect_dep_status() wrote to stderr: {captured.err!r}"

    def test_produces_no_stdout(self, capsys):
        """_collect_dep_status must not write to stdout."""
        from amplihack.dep_check import _collect_dep_status

        _collect_dep_status()
        captured = capsys.readouterr()
        assert captured.out == "", f"_collect_dep_status() wrote to stdout: {captured.out!r}"

    def test_missing_package_goes_to_missing_list(self):
        """A missing package must appear in result.missing, not result.available."""
        from unittest.mock import patch

        from amplihack.dep_check import _collect_dep_status

        fake_deps = {"totally_nonexistent_xyz_pkg": "totally-nonexistent-xyz-pkg"}
        with patch("amplihack.dep_check.SDK_DEPENDENCIES", fake_deps):
            result = _collect_dep_status()

        assert "totally_nonexistent_xyz_pkg" in result.missing
        assert "totally_nonexistent_xyz_pkg" not in result.available
        assert not result.all_ok

    def test_installed_package_goes_to_available_list(self):
        """A present package must appear in result.available, not result.missing."""
        from unittest.mock import patch

        from amplihack.dep_check import _collect_dep_status

        fake_deps = {"json": "json"}  # json is always present
        with patch("amplihack.dep_check.SDK_DEPENDENCIES", fake_deps):
            result = _collect_dep_status()

        assert "json" in result.available
        assert "json" not in result.missing
        assert result.all_ok

    def test_empty_sdk_dependencies_returns_all_ok(self):
        """With no deps registered, result must be all_ok=True."""
        from unittest.mock import patch

        from amplihack.dep_check import _collect_dep_status

        with patch("amplihack.dep_check.SDK_DEPENDENCIES", {}):
            result = _collect_dep_status()

        assert result.all_ok
        assert result.available == []
        assert result.missing == []


# ---------------------------------------------------------------------------
# 10. check_sdk_dep: no WARNING print on missing package
# ---------------------------------------------------------------------------
class TestCheckSdkDepNoWarningPrint:
    """check_sdk_dep must not print to stderr for missing packages."""

    def test_missing_package_produces_no_stderr(self, capsys):
        """check_sdk_dep('nonexistent') must not write to stderr."""
        from amplihack.dep_check import check_sdk_dep

        check_sdk_dep("nonexistent_package_that_will_never_exist_xyz123")
        captured = capsys.readouterr()
        assert captured.err == "", (
            f"check_sdk_dep() wrote to stderr for missing package: {captured.err!r}"
        )

    def test_missing_package_produces_no_stdout(self, capsys):
        """check_sdk_dep('nonexistent') must not write to stdout."""
        from amplihack.dep_check import check_sdk_dep

        check_sdk_dep("nonexistent_package_that_will_never_exist_xyz123")
        captured = capsys.readouterr()
        assert captured.out == "", (
            f"check_sdk_dep() wrote to stdout for missing package: {captured.out!r}"
        )

    def test_subprocess_import_check_sdk_dep_no_stderr(self):
        """Subprocess call to check_sdk_dep must produce zero stderr bytes."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from amplihack.dep_check import check_sdk_dep; "
                    "check_sdk_dep('nonexistent_pkg_xyz_never_exists')"
                ),
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.stderr == "", f"check_sdk_dep subprocess wrote to stderr: {result.stderr!r}"


# ---------------------------------------------------------------------------
# 11. microsoft_sdk: no WARNING print on import (no agent_framework)
# ---------------------------------------------------------------------------
class TestMicrosoftSdkNoWarningOnImport:
    """microsoft_sdk must not print a WARNING when agent_framework is absent."""

    def test_import_produces_no_agent_framework_warning(self, capsys):
        """Import of microsoft_sdk must not emit the 'agent_framework not available' WARNING.

        Note: other modules (e.g. amplihack_memory) may emit their own WARNINGs
        on first import; we scope this assertion to the specific warning that was
        removed from microsoft_sdk.py (issue #2660 / the no-silent-fallbacks fix).
        """
        import importlib

        import amplihack.agents.goal_seeking.sdk_adapters.microsoft_sdk as m

        importlib.reload(m)
        captured = capsys.readouterr()
        assert "agent_framework not available" not in captured.err, (
            f"microsoft_sdk still emits 'agent_framework not available' WARNING: {captured.err!r}"
        )

    def test_has_agent_framework_flag_is_bool(self):
        """_HAS_AGENT_FRAMEWORK must be a bool regardless of whether SDK is present."""
        from amplihack.agents.goal_seeking.sdk_adapters.microsoft_sdk import _HAS_AGENT_FRAMEWORK

        assert isinstance(_HAS_AGENT_FRAMEWORK, bool)

    def test_agent_framework_absent_flag_is_false(self):
        """When agent_framework cannot be imported, _HAS_AGENT_FRAMEWORK must be False."""
        import importlib
        import importlib.util

        if importlib.util.find_spec("agent_framework") is not None:
            pytest.skip("agent_framework IS installed; testing absent-SDK branch only")

        from amplihack.agents.goal_seeking.sdk_adapters.microsoft_sdk import _HAS_AGENT_FRAMEWORK

        assert _HAS_AGENT_FRAMEWORK is False

    def test_instantiation_without_agent_framework_raises_import_error(self):
        """MicrosoftGoalSeekingAgent() must raise ImportError when SDK is absent, not NameError."""
        import importlib.util

        if importlib.util.find_spec("agent_framework") is not None:
            pytest.skip("agent_framework IS installed")

        from amplihack.agents.goal_seeking.sdk_adapters.microsoft_sdk import (
            MicrosoftGoalSeekingAgent,
        )

        with pytest.raises(ImportError, match="agent-framework-core not installed"):
            MicrosoftGoalSeekingAgent(name="test")


# ---------------------------------------------------------------------------
# 12. re_enable_prompt: single import, no try/except chain
# ---------------------------------------------------------------------------
class TestReEnablePromptImport:
    """re_enable_prompt must import from amplihack.worktree.git_utils directly."""

    def test_import_produces_no_stderr(self, capsys):
        """Import of re_enable_prompt must produce zero stderr."""
        import importlib

        import amplihack.power_steering.re_enable_prompt as m

        importlib.reload(m)
        captured = capsys.readouterr()
        assert captured.err == "", f"re_enable_prompt import wrote to stderr: {captured.err!r}"

    def test_subprocess_import_re_enable_prompt_no_stderr(self):
        """Subprocess import of re_enable_prompt must produce zero stderr bytes."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import amplihack.power_steering.re_enable_prompt",
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.stderr == "", (
            f"re_enable_prompt subprocess import wrote to stderr: {result.stderr!r}"
        )

    def test_no_git_utils_fallback_warning_in_source(self):
        """re_enable_prompt source must not contain the old /tmp fallback lambda."""
        src = (
            Path(__file__).parents[1]
            / "src"
            / "amplihack"
            / "power_steering"
            / "re_enable_prompt.py"
        )
        content = src.read_text(encoding="utf-8")
        assert "lambda" not in content or "/tmp/amplihack" not in content, (
            "Old /tmp lambda fallback found in re_enable_prompt.py — "
            "should have been removed by the single-import fix"
        )
        assert "git_utils not available" not in content, (
            "Old WARNING text 'git_utils not available' still present in re_enable_prompt.py"
        )


# ---------------------------------------------------------------------------
# Security contract tests (previously xfail, now implemented)
# ---------------------------------------------------------------------------


class TestDirectoryPermissions:
    """get_shared_runtime_dir must create the runtime dir with 0o700 permissions."""

    def setup_method(self):
        _clear_lru_cache()

    def teardown_method(self):
        _clear_lru_cache()

    def test_created_directory_has_owner_only_permissions(self, tmp_path):
        """Runtime dir created by get_shared_runtime_dir must have mode 0o700."""
        from amplihack.worktree.git_utils import get_shared_runtime_dir

        with patch("subprocess.run", return_value=_make_git_result(".git")):
            runtime_str = get_shared_runtime_dir(str(tmp_path))

        runtime = Path(runtime_str)
        assert runtime.exists(), "get_shared_runtime_dir did not create the directory"

        mode = stat.S_IMODE(runtime.stat().st_mode)
        assert mode == 0o700, (
            f"Runtime directory {runtime} has mode {oct(mode)}, expected 0o700 (owner-only). "
            "World-readable runtime dirs leak sensitive power-steering state."
        )

    def test_intermediate_dot_claude_directory_has_restricted_permissions(self, tmp_path):
        """Intermediate .claude dir must also not be world-readable."""
        from amplihack.worktree.git_utils import get_shared_runtime_dir

        with patch("subprocess.run", return_value=_make_git_result(".git")):
            runtime_str = get_shared_runtime_dir(str(tmp_path))

        dot_claude = Path(runtime_str).parent
        assert dot_claude.exists(), ".claude directory not created"
        mode = stat.S_IMODE(dot_claude.stat().st_mode)
        # At minimum should not be world-writable
        assert not (mode & 0o002), f".claude dir {dot_claude} is world-writable (mode {oct(mode)})"


class TestEnvVarOverride:
    """AMPLIHACK_RUNTIME_DIR env-var must override the computed runtime dir."""

    def setup_method(self):
        _clear_lru_cache()

    def teardown_method(self):
        _clear_lru_cache()

    def test_env_var_within_home_overrides_result(self, tmp_path, monkeypatch):
        """AMPLIHACK_RUNTIME_DIR set to a home-relative path must be returned."""
        custom = Path.home() / ".amplihack_test_runtime_dir_xyz"
        monkeypatch.setenv("AMPLIHACK_RUNTIME_DIR", str(custom))

        from amplihack.worktree.git_utils import get_shared_runtime_dir

        with patch("subprocess.run", return_value=_make_git_result(".git")):
            result = get_shared_runtime_dir(str(tmp_path))

        assert result == str(custom), (
            f"AMPLIHACK_RUNTIME_DIR was not honoured. Got {result!r}, expected {str(custom)!r}"
        )

    def test_env_var_within_tmp_overrides_result(self, tmp_path, monkeypatch):
        """AMPLIHACK_RUNTIME_DIR set to a /tmp-relative path must be returned."""
        custom = Path("/tmp/amplihack_test_runtime_xyz")
        monkeypatch.setenv("AMPLIHACK_RUNTIME_DIR", str(custom))

        from amplihack.worktree.git_utils import get_shared_runtime_dir

        with patch("subprocess.run", return_value=_make_git_result(".git")):
            result = get_shared_runtime_dir(str(tmp_path))

        assert result == str(custom), (
            f"AMPLIHACK_RUNTIME_DIR was not honoured. Got {result!r}, expected {str(custom)!r}"
        )


class TestEnvVarPathValidation:
    """AMPLIHACK_RUNTIME_DIR outside allowed roots must raise RuntimeError."""

    def setup_method(self):
        _clear_lru_cache()

    def teardown_method(self):
        _clear_lru_cache()

    def test_env_var_outside_home_and_tmp_raises_runtime_error(self, tmp_path, monkeypatch):
        """AMPLIHACK_RUNTIME_DIR pointing to /etc must raise RuntimeError."""
        monkeypatch.setenv("AMPLIHACK_RUNTIME_DIR", "/etc/amplihack_malicious")

        from amplihack.worktree.git_utils import get_shared_runtime_dir

        with pytest.raises(RuntimeError, match="AMPLIHACK_RUNTIME_DIR"):
            with patch("subprocess.run", return_value=_make_git_result(".git")):
                get_shared_runtime_dir(str(tmp_path))

    def test_env_var_path_traversal_raises_runtime_error(self, tmp_path, monkeypatch):
        """AMPLIHACK_RUNTIME_DIR with path traversal (../../etc) must raise RuntimeError."""
        home = Path.home()
        traversal = str(home / ".." / ".." / "etc" / "passwd")
        monkeypatch.setenv("AMPLIHACK_RUNTIME_DIR", traversal)

        from amplihack.worktree.git_utils import get_shared_runtime_dir

        with pytest.raises(RuntimeError, match="AMPLIHACK_RUNTIME_DIR"):
            with patch("subprocess.run", return_value=_make_git_result(".git")):
                get_shared_runtime_dir(str(tmp_path))
