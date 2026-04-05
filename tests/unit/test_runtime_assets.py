from unittest.mock import patch

from amplihack.runtime_assets import iter_runtime_roots, resolve_asset_path

# ---------------------------------------------------------------------------
# iter_runtime_roots tests
# ---------------------------------------------------------------------------


def test_iter_runtime_roots_returns_only_directories(tmp_path):
    """iter_runtime_roots should exclude non-directory paths."""
    real_dir = tmp_path / "valid-root"
    real_dir.mkdir()
    file_path = tmp_path / "not-a-dir"
    file_path.write_text("I'm a file")

    with (
        patch("src.amplihack.runtime_assets.os.environ.get", return_value=None),
        patch("src.amplihack.runtime_assets.Path.home", return_value=real_dir),
        patch("src.amplihack.runtime_assets.Path.cwd", return_value=real_dir),
    ):
        roots = iter_runtime_roots()

    for root in roots:
        assert root.is_dir(), f"iter_runtime_roots returned non-directory: {root}"


def test_iter_runtime_roots_deduplicates(tmp_path):
    """Duplicate resolved paths should appear only once."""
    dir_a = tmp_path / "root-a"
    dir_a.mkdir()

    with (
        patch("src.amplihack.runtime_assets.os.environ.get", return_value=str(dir_a)),
        patch("src.amplihack.runtime_assets.Path.home", return_value=dir_a),
        patch("src.amplihack.runtime_assets.Path.cwd", return_value=dir_a),
    ):
        roots = iter_runtime_roots()

    resolved_roots = [r.resolve() for r in roots]
    assert len(resolved_roots) == len(set(resolved_roots)), (
        f"Duplicate roots found: {resolved_roots}"
    )


def test_iter_runtime_roots_excludes_file_paths(tmp_path):
    """A file (not directory) set as AMPLIHACK_HOME should be excluded."""
    file_as_root = tmp_path / "regular-file"
    file_as_root.write_text("not a directory")
    fallback_dir = tmp_path / "fallback"
    fallback_dir.mkdir()

    with (
        patch("src.amplihack.runtime_assets.os.environ.get", return_value=str(file_as_root)),
        patch("src.amplihack.runtime_assets.Path.home", return_value=fallback_dir),
        patch("src.amplihack.runtime_assets.Path.cwd", return_value=fallback_dir),
    ):
        roots = iter_runtime_roots()

    resolved = {r.resolve() for r in roots}
    assert file_as_root.resolve() not in resolved, "File path should not appear in runtime roots"


def test_iter_runtime_roots_includes_amplihack_home(tmp_path):
    """AMPLIHACK_HOME directory should be first in the returned roots."""
    custom_root = tmp_path / "custom-amplihack"
    custom_root.mkdir()

    with (
        patch("src.amplihack.runtime_assets.os.environ.get", return_value=str(custom_root)),
        patch("src.amplihack.runtime_assets.Path.home", return_value=tmp_path),
        patch("src.amplihack.runtime_assets.Path.cwd", return_value=tmp_path),
    ):
        roots = iter_runtime_roots()

    assert len(roots) >= 1
    assert roots[0].resolve() == custom_root.resolve(), (
        f"AMPLIHACK_HOME should be first root, got {roots[0]}"
    )


# ---------------------------------------------------------------------------
# resolve_asset_path tests
# ---------------------------------------------------------------------------


def test_resolve_asset_path_prefers_home_runtime_root(tmp_path):
    home_root = tmp_path / "home-runtime"
    package_root = tmp_path / "package-runtime"

    home_helper = home_root / "amplifier-bundle" / "tools" / "orch_helper.py"
    home_helper.parent.mkdir(parents=True, exist_ok=True)
    home_helper.write_text("# home helper\n")

    package_helper = package_root / "amplifier-bundle" / "tools" / "orch_helper.py"
    package_helper.parent.mkdir(parents=True, exist_ok=True)
    package_helper.write_text("# package helper\n")

    resolved = resolve_asset_path("helper-path", [home_root, package_root])

    assert resolved == home_helper


def test_resolve_asset_path_finds_hooks_in_home_claude_layout(tmp_path):
    home_root = tmp_path / "home-runtime"
    hooks_dir = home_root / ".claude" / "tools" / "amplihack" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    (hooks_dir / "dev_intent_router.py").write_text("# hook\n")

    resolved = resolve_asset_path("hooks-dir", [home_root])

    assert resolved == hooks_dir


def test_resolve_asset_path_raises_for_missing_assets(tmp_path):
    empty_root = tmp_path / "empty"
    empty_root.mkdir()

    try:
        resolve_asset_path("session-tree-path", [empty_root])
    except FileNotFoundError as exc:
        assert "session-tree-path" in str(exc)
    else:
        raise AssertionError("Expected FileNotFoundError for missing runtime asset")
