"""Tests for the opt-in Rust CLI trial helper."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from amplihack.rust_trial import (
    TRIAL_BINARY_ENV,
    TRIAL_HOME_ENV,
    build_trial_env,
    find_rust_cli_binary,
    main,
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
    result = find_rust_cli_binary()
    assert result == binary.resolve()


def test_find_rust_cli_binary_uses_bundled_binary(tmp_path, monkeypatch):
    binary = _write_executable(tmp_path / ".claude" / "bin" / "amplihack")
    monkeypatch.delenv(TRIAL_BINARY_ENV, raising=False)
    monkeypatch.setattr("amplihack.rust_trial._bundled_binary_path", lambda: binary)
    monkeypatch.setattr("amplihack.rust_trial.shutil.which", lambda _: None)
    result = find_rust_cli_binary()
    assert result == binary.resolve()


def test_build_trial_env_creates_isolated_dirs(tmp_path):
    env = build_trial_env(tmp_path / "trial-home")
    assert env["HOME"].endswith("trial-home")
    assert env["XDG_CONFIG_HOME"].endswith("trial-home/.config")
    assert Path(env["HOME"]).is_dir()
    assert Path(env["XDG_CONFIG_HOME"]).is_dir()


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


def test_main_runs_rust_binary_in_isolated_home(tmp_path, monkeypatch, capsys):
    binary = _write_executable(tmp_path / "amplihack")
    captured: dict[str, object] = {}

    def fake_run(cmd, env, check):  # type: ignore[no-untyped-def]
        captured["cmd"] = cmd
        captured["env"] = env
        captured["check"] = check
        return SimpleNamespace(returncode=7)

    monkeypatch.setattr("amplihack.rust_trial.find_rust_cli_binary", lambda: binary)
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
    monkeypatch.setattr("amplihack.rust_trial.find_rust_cli_binary", lambda: None)
    exit_code = main(["recipe", "list"])
    assert exit_code == 1
    assert "Rust CLI binary not found" in capsys.readouterr().err


def test_main_errors_when_trial_home_missing_path(capsys):
    exit_code = main(["--trial-home"])
    assert exit_code == 2
    assert "--trial-home requires a path" in capsys.readouterr().err
