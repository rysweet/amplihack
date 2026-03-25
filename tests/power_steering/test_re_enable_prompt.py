from amplihack.power_steering import re_enable_prompt


def test_prompt_re_enable_defaults_yes_without_tty(monkeypatch, tmp_path, capsys):
    runtime_dir = tmp_path / ".claude" / "runtime"
    disabled_file = runtime_dir / "power-steering" / ".disabled"
    disabled_file.parent.mkdir(parents=True)
    disabled_file.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        re_enable_prompt,
        "get_shared_runtime_dir",
        lambda project_root: str(runtime_dir),
    )
    monkeypatch.setattr(re_enable_prompt, "_is_noninteractive_terminal", lambda: True)

    prompted = False

    def fail_if_prompted(*args, **kwargs):
        nonlocal prompted
        prompted = True
        raise AssertionError("non-interactive launches must not prompt")

    monkeypatch.setattr(re_enable_prompt, "_get_input_with_timeout", fail_if_prompted)

    result = re_enable_prompt.prompt_re_enable_if_disabled(project_root=tmp_path)

    captured = capsys.readouterr()
    assert result is True
    assert prompted is False
    assert not disabled_file.exists()
    assert "Power-Steering is currently disabled." not in captured.out
    assert "Power-Steering re-enabled" in captured.out
