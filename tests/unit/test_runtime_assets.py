from src.amplihack.runtime_assets import resolve_asset_path


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
