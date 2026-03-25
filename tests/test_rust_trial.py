"""Tests for the opt-in Rust CLI trial helper."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from amplihack.rust_trial import (
    RUST_RELEASES_API,
    TRIAL_BINARY_ENV,
    TRIAL_HOME_ENV,
    InstallOptions,
    _ensure_trial_copilot_config,
    _expected_release_asset_name,
    _select_release_asset,
    _target_triple,
    _update_shell_profile_path,
    build_trial_env,
    download_latest_release_binary,
    ensure_trial_dependencies,
    find_rust_cli_binary,
    install_rust_cli,
    main,
    parse_install_args,
    parse_trial_args,
)


def _write_executable(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def test_find_rust_cli_binary_prefers_env_override(tmp_path, monkeypatch):
    binary = _write_executable(tmp_path / "custom-amplihack")
    monkeypatch.setenv(TRIAL_BINARY_ENV, str(binary))
    monkeypatch.setattr(
        "amplihack.rust_trial._is_rust_cli_binary", lambda candidate: candidate == binary
    )
    result = find_rust_cli_binary(tmp_path / "trial")
    assert result == binary.resolve()


def test_find_rust_cli_binary_uses_bundled_binary(tmp_path, monkeypatch):
    binary = _write_executable(tmp_path / ".claude" / "bin" / "amplihack")
    monkeypatch.delenv(TRIAL_BINARY_ENV, raising=False)
    monkeypatch.setattr("amplihack.rust_trial._bundled_binary_path", lambda: binary)
    monkeypatch.setattr("amplihack.rust_trial.shutil.which", lambda _: None)
    monkeypatch.setattr(
        "amplihack.rust_trial._is_rust_cli_binary", lambda candidate: candidate == binary
    )
    result = find_rust_cli_binary(tmp_path / "trial")
    assert result == binary.resolve()


def test_target_triple_for_current_platform():
    assert _target_triple() in {
        "x86_64-unknown-linux-gnu",
        "aarch64-unknown-linux-gnu",
        "x86_64-apple-darwin",
        "aarch64-apple-darwin",
    }
    assert _expected_release_asset_name().startswith("amplihack-")
    assert _expected_release_asset_name().endswith(".tar.gz")


def test_select_release_asset_prefers_newest_snapshot_creation_time():
    asset_name = _expected_release_asset_name()
    tag_name, asset_url = _select_release_asset(
        [
            {
                "tag_name": "snapshot-republished-old",
                "created_at": "2026-03-02T12:00:00Z",
                "published_at": "2026-03-06T12:00:00Z",
                "assets": [
                    {
                        "name": asset_name,
                        "browser_download_url": "https://example.invalid/old.tar.gz",
                    }
                ],
            },
            {
                "tag_name": "snapshot-newer-build",
                "created_at": "2026-03-05T12:00:00Z",
                "published_at": "2026-03-05T12:00:00Z",
                "assets": [
                    {
                        "name": asset_name,
                        "browser_download_url": "https://example.invalid/new.tar.gz",
                    }
                ],
            },
        ]
    )

    assert tag_name == "snapshot-newer-build"
    assert asset_url == "https://example.invalid/new.tar.gz"


def test_select_release_asset_uses_publish_time_when_creation_time_missing():
    asset_name = _expected_release_asset_name()
    tag_name, asset_url = _select_release_asset(
        [
            {
                "tag_name": "snapshot-earlier-publish",
                "published_at": "2026-03-05T12:00:00Z",
                "assets": [
                    {
                        "name": asset_name,
                        "browser_download_url": "https://example.invalid/earlier.tar.gz",
                    }
                ],
            },
            {
                "tag_name": "snapshot-later-publish",
                "published_at": "2026-03-06T12:00:00Z",
                "assets": [
                    {
                        "name": asset_name,
                        "browser_download_url": "https://example.invalid/later.tar.gz",
                    }
                ],
            },
        ]
    )

    assert tag_name == "snapshot-later-publish"
    assert asset_url == "https://example.invalid/later.tar.gz"


def test_select_release_asset_skips_draft_releases():
    asset_name = _expected_release_asset_name()
    tag_name, asset_url = _select_release_asset(
        [
            {
                "tag_name": "snapshot-draft",
                "draft": True,
                "created_at": "2026-03-07T12:00:00Z",
                "published_at": "2026-03-07T12:00:00Z",
                "assets": [
                    {
                        "name": asset_name,
                        "browser_download_url": "https://example.invalid/draft.tar.gz",
                    }
                ],
            },
            {
                "tag_name": "snapshot-public",
                "created_at": "2026-03-06T12:00:00Z",
                "published_at": "2026-03-06T12:00:00Z",
                "assets": [
                    {
                        "name": asset_name,
                        "browser_download_url": "https://example.invalid/public.tar.gz",
                    }
                ],
            },
        ]
    )

    assert tag_name == "snapshot-public"
    assert asset_url == "https://example.invalid/public.tar.gz"


def test_download_latest_release_binary_extracts_asset(tmp_path, monkeypatch):
    release_tag = "snapshot-deadbeef"
    archive_path = tmp_path / _expected_release_asset_name()

    import tarfile

    with tarfile.open(archive_path, "w:gz") as archive:
        binary = _write_executable(tmp_path / "staged" / "amplihack")
        archive.add(binary, arcname="amplihack")

    monkeypatch.setattr(
        "amplihack.rust_trial._github_json",
        lambda url: (
            [
                {
                    "tag_name": release_tag,
                    "assets": [
                        {
                            "name": _expected_release_asset_name(),
                            "browser_download_url": "https://example.invalid/amplihack.tar.gz",
                        }
                    ],
                }
            ]
            if url == RUST_RELEASES_API
            else []
        ),
    )
    monkeypatch.setattr(
        "amplihack.rust_trial._download_to_file",
        lambda url, destination: destination.write_bytes(archive_path.read_bytes()),
    )
    monkeypatch.setattr(
        "amplihack.rust_trial._is_rust_cli_binary",
        lambda candidate: candidate.name == "amplihack" and candidate.exists(),
    )

    result = download_latest_release_binary(tmp_path / "trial-home")
    assert result.name == "amplihack"
    assert result.exists()


def test_build_trial_env_creates_isolated_dirs(tmp_path):
    env = build_trial_env(tmp_path / "trial-home")
    assert env["HOME"].endswith("trial-home")
    assert env["XDG_CONFIG_HOME"].endswith("trial-home/.config")
    assert env["PATH"].split(":")[0].endswith("trial-home/.npm-global/bin")
    assert Path(env["HOME"]).is_dir()
    assert Path(env["XDG_CONFIG_HOME"]).is_dir()
    assert Path(env["HOME"]).joinpath(".npm-global", "bin").is_dir()


def test_ensure_trial_dependencies_skips_non_copilot(tmp_path, monkeypatch):
    called: list[str] = []

    monkeypatch.setattr(
        "amplihack.launcher.copilot.check_copilot",
        lambda **_kwargs: called.append("check") or False,
    )
    monkeypatch.setattr(
        "amplihack.launcher.copilot.install_copilot",
        lambda **_kwargs: called.append("install") or True,
    )

    ensure_trial_dependencies(
        ["recipe", "list"], tmp_path / "trial-home", build_trial_env(tmp_path)
    )

    assert called == []


def test_ensure_trial_copilot_config_creates_empty_config(tmp_path):
    config_path = _ensure_trial_copilot_config(
        trial_home=tmp_path / "trial-home",
        source_home=tmp_path / "host-home",
    )

    assert config_path.read_text(encoding="utf-8") == "{}\n"


def test_ensure_trial_copilot_config_copies_existing_host_config(tmp_path):
    host_home = tmp_path / "host-home"
    source_config = host_home / ".copilot" / "config.json"
    source_config.parent.mkdir(parents=True, exist_ok=True)
    source_config.write_text('{"installed_plugins":["amplihack"]}\n', encoding="utf-8")

    config_path = _ensure_trial_copilot_config(
        trial_home=tmp_path / "trial-home",
        source_home=host_home,
    )

    assert config_path.read_text(encoding="utf-8") == '{"installed_plugins":["amplihack"]}\n'


def test_ensure_trial_dependencies_installs_copilot_into_trial_home(tmp_path, monkeypatch):
    trial_home = tmp_path / "trial-home"
    env = build_trial_env(trial_home)
    captured: dict[str, object] = {}

    monkeypatch.setattr("amplihack.launcher.copilot.check_copilot", lambda **_kwargs: False)

    def fake_install(*, env, home):  # type: ignore[no-untyped-def]
        captured["env"] = env
        captured["home"] = home
        return True

    monkeypatch.setattr("amplihack.launcher.copilot.install_copilot", fake_install)

    ensure_trial_dependencies(["copilot"], trial_home, env)

    assert captured["home"] == trial_home
    assert captured["env"] is env
    assert env["PATH"].split(":")[0] == str(trial_home / ".npm-global" / "bin")
    assert (trial_home / ".copilot" / "config.json").is_file()


def test_ensure_trial_dependencies_errors_when_copilot_install_fails(tmp_path, monkeypatch):
    trial_home = tmp_path / "trial-home"
    env = build_trial_env(trial_home)

    monkeypatch.setattr("amplihack.launcher.copilot.check_copilot", lambda **_kwargs: False)
    monkeypatch.setattr("amplihack.launcher.copilot.install_copilot", lambda **_kwargs: False)

    try:
        ensure_trial_dependencies(["copilot"], trial_home, env)
    except RuntimeError as exc:
        assert "Failed to install GitHub Copilot CLI" in str(exc)
    else:
        raise AssertionError("Expected ensure_trial_dependencies() to raise RuntimeError")


def test_parse_trial_args_supports_custom_home():
    trial_home, forwarded = parse_trial_args(
        ["--trial-home", "/tmp/amplihack-rust-e2e", "recipe", "list"]
    )
    assert trial_home == Path("/tmp/amplihack-rust-e2e")
    assert forwarded == ["recipe", "list"]


def test_parse_trial_args_defaults_to_rust_help(monkeypatch, tmp_path):
    monkeypatch.setenv(TRIAL_HOME_ENV, str(tmp_path / "trial-home"))
    trial_home, forwarded = parse_trial_args([])
    assert trial_home == tmp_path / "trial-home"
    assert forwarded == ["--help"]


def test_parse_install_args_supports_force_and_no_bootstrap(tmp_path):
    options = parse_install_args(
        ["--install-dir", str(tmp_path / "bin"), "--force", "--no-bootstrap"]
    )
    assert options.install_dir == tmp_path / "bin"
    assert options.force is True
    assert options.bootstrap is False


def test_update_shell_profile_path_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("SHELL", "/bin/bash")

    assert _update_shell_profile_path(tmp_path / ".local" / "bin") is True
    assert _update_shell_profile_path(tmp_path / ".local" / "bin") is True

    bashrc = tmp_path / ".bashrc"
    content = bashrc.read_text(encoding="utf-8")
    assert content.count('export PATH="$HOME/.local/bin:$PATH"') == 1


def test_install_rust_cli_copies_binary_and_bootstraps(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    source_binary = _write_executable(tmp_path / "release" / "amplihack")
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        "amplihack.rust_trial.download_latest_release_binary",
        lambda _trial_home: source_binary,
    )

    def fake_run(cmd, check):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        captured["check"] = check
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("amplihack.rust_trial.subprocess.run", fake_run)

    installed = install_rust_cli(
        tmp_path / "trial-home", InstallOptions(install_dir=tmp_path / ".local" / "bin")
    )

    assert installed == (tmp_path / ".local" / "bin" / "amplihack").resolve()
    assert installed.exists()
    assert captured["cmd"] == [str(installed), "install"]
    assert captured["check"] is False
    assert 'export PATH="$HOME/.local/bin:$PATH"' in (tmp_path / ".bashrc").read_text(
        encoding="utf-8"
    )


def test_install_rust_cli_refuses_to_overwrite_non_amplihack_binary(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    install_dir = tmp_path / ".local" / "bin"
    install_dir.mkdir(parents=True, exist_ok=True)
    _write_executable(install_dir / "amplihack")
    source_binary = _write_executable(tmp_path / "release" / "amplihack")

    monkeypatch.setattr(
        "amplihack.rust_trial.download_latest_release_binary",
        lambda _trial_home: source_binary,
    )
    monkeypatch.setattr(
        "amplihack.rust_trial._is_rust_cli_binary",
        lambda candidate: candidate == source_binary,
    )

    try:
        install_rust_cli(tmp_path / "trial-home", InstallOptions(install_dir=install_dir))
    except RuntimeError as exc:
        assert "Refusing to overwrite non-amplihack binary" in str(exc)
    else:
        raise AssertionError("Expected install_rust_cli() to refuse overwriting unknown binary")


def test_main_runs_rust_binary_in_isolated_home(tmp_path, monkeypatch, capsys):
    binary = _write_executable(tmp_path / "amplihack")
    captured: dict[str, object] = {}

    def fake_run(cmd, env, check):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        captured["env"] = env
        captured["check"] = check
        return SimpleNamespace(returncode=7)

    monkeypatch.setattr("amplihack.rust_trial.find_rust_cli_binary", lambda _trial_home: binary)
    monkeypatch.setattr("amplihack.rust_trial.subprocess.run", fake_run)

    exit_code = main(["--trial-home", str(tmp_path / "trial"), "recipe", "list"])

    assert exit_code == 7
    assert captured["cmd"] == [str(binary), "recipe", "list"]
    env = captured["env"]
    assert isinstance(env, dict)
    assert env["HOME"].endswith("/trial")
    assert env["XDG_CONFIG_HOME"].endswith("/trial/.config")
    assert captured["check"] is False
    stderr = capsys.readouterr().err
    assert "Using isolated HOME=" in stderr


def test_main_errors_loudly_when_binary_missing(capsys, monkeypatch):
    def fail(_trial_home):  # type: ignore[no-untyped-def]
        raise FileNotFoundError("Rust CLI binary not found")

    monkeypatch.setattr("amplihack.rust_trial.find_rust_cli_binary", fail)
    exit_code = main(["recipe", "list"])
    assert exit_code == 1
    assert "Rust CLI binary not found" in capsys.readouterr().err


def test_main_errors_when_trial_home_missing_path(capsys):
    exit_code = main(["--trial-home"])
    assert exit_code == 2
    assert "--trial-home requires a path" in capsys.readouterr().err


def test_main_install_command_runs_global_bootstrap(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    installed = tmp_path / ".local" / "bin" / "amplihack"
    captured: dict[str, object] = {}

    def fake_install(trial_home, options):  # type: ignore[no-untyped-def]
        captured["trial_home"] = trial_home
        captured["options"] = options
        installed.parent.mkdir(parents=True, exist_ok=True)
        installed.write_text("binary", encoding="utf-8")
        return installed

    monkeypatch.setattr("amplihack.rust_trial.install_rust_cli", fake_install)

    exit_code = main(["--trial-home", str(tmp_path / "trial"), "install", "--no-bootstrap"])

    assert exit_code == 0
    assert captured["trial_home"] == tmp_path / "trial"
    options = captured["options"]
    assert isinstance(options, InstallOptions)
    assert options.bootstrap is False
    assert "Installed Rust CLI at" in capsys.readouterr().err
