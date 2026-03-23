"""Tests for amplihack-hive CLI commands."""

from __future__ import annotations

import json
import os
import signal
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.cli.hive import (
    _config_path,
    _hive_dir,
    _is_running,
    _load_config,
    _load_pids,
    _save_config,
    _save_pids,
    cmd_add_agent,
    cmd_create,
    cmd_status,
    cmd_stop,
    main,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_hives(tmp_path, monkeypatch):
    """Redirect hive directory to a temp location."""
    import amplihack.cli.hive as hive_module
    monkeypatch.setattr(hive_module, "_HIVES_DIR", tmp_path / "hives")
    return tmp_path / "hives"


# ---------------------------------------------------------------------------
# Tests: create
# ---------------------------------------------------------------------------


class TestCreate:
    def test_create_makes_config(self, tmp_hives):
        rc = main(["create", "--name", "myhive", "--agents", "2"])
        assert rc == 0
        cfg_path = tmp_hives / "myhive" / "config.yaml"
        assert cfg_path.exists()

    def test_create_sets_agent_count(self, tmp_hives):
        main(["create", "--name", "testhive", "--agents", "3"])
        import amplihack.cli.hive as m
        cfg = m._load_config("testhive")
        assert len(cfg["agents"]) == 3

    def test_create_agent_names(self, tmp_hives):
        main(["create", "--name", "namehive", "--agents", "2"])
        import amplihack.cli.hive as m
        cfg = m._load_config("namehive")
        names = [a["name"] for a in cfg["agents"]]
        assert names == ["agent_0", "agent_1"]

    def test_create_with_transport(self, tmp_hives):
        main([
            "create", "--name", "azurehive", "--agents", "1",
            "--transport", "azure_service_bus",
            "--connection-string", "Endpoint=sb://test",
        ])
        import amplihack.cli.hive as m
        cfg = m._load_config("azurehive")
        assert cfg["transport"] == "azure_service_bus"
        assert cfg["connection_string"] == "Endpoint=sb://test"

    def test_create_default_transport_is_local(self, tmp_hives):
        main(["create", "--name", "localhive", "--agents", "1"])
        import amplihack.cli.hive as m
        cfg = m._load_config("localhive")
        assert cfg["transport"] == "local"

    def test_create_returns_0(self, tmp_hives):
        rc = main(["create", "--name", "rchive", "--agents", "1"])
        assert rc == 0


# ---------------------------------------------------------------------------
# Tests: add-agent
# ---------------------------------------------------------------------------


class TestAddAgent:
    def _setup_hive(self, name: str) -> None:
        main(["create", "--name", name, "--agents", "1"])

    def test_add_agent_appends(self, tmp_hives):
        self._setup_hive("addhive")
        rc = main([
            "add-agent", "--hive", "addhive",
            "--agent-name", "new_agent",
            "--prompt", "You are a tester",
        ])
        assert rc == 0
        import amplihack.cli.hive as m
        cfg = m._load_config("addhive")
        names = [a["name"] for a in cfg["agents"]]
        assert "new_agent" in names

    def test_add_agent_with_kuzu_db(self, tmp_hives):
        self._setup_hive("kuzuhive")
        main([
            "add-agent", "--hive", "kuzuhive",
            "--agent-name", "kuzu_agent",
            "--prompt", "You are a DB agent",
            "--kuzu-db", "/tmp/test.kuzu",
        ])
        import amplihack.cli.hive as m
        cfg = m._load_config("kuzuhive")
        kuzu_agents = [a for a in cfg["agents"] if a.get("kuzu_db")]
        assert len(kuzu_agents) == 1
        assert kuzu_agents[0]["kuzu_db"] == "/tmp/test.kuzu"

    def test_add_agent_duplicate_returns_1(self, tmp_hives):
        main(["create", "--name", "duphive", "--agents", "1"])
        rc = main([
            "add-agent", "--hive", "duphive",
            "--agent-name", "agent_0",
            "--prompt", "Duplicate",
        ])
        assert rc == 1

    def test_add_agent_missing_hive_returns_1(self, tmp_hives):
        rc = main([
            "add-agent", "--hive", "nonexistent",
            "--agent-name", "x",
            "--prompt", "y",
        ])
        assert rc == 1


# ---------------------------------------------------------------------------
# Tests: status
# ---------------------------------------------------------------------------


class TestStatus:
    def test_status_prints_agents(self, tmp_hives, capsys):
        main(["create", "--name", "statushive", "--agents", "2"])
        rc = main(["status", "--hive", "statushive"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "statushive" in captured.out
        assert "agent_0" in captured.out
        assert "agent_1" in captured.out

    def test_status_shows_stopped_for_dead_pids(self, tmp_hives, capsys):
        main(["create", "--name", "deadhive", "--agents", "1"])
        import amplihack.cli.hive as m
        # Save a fake PID that isn't running
        _save_pids("deadhive", {"agent_0": 999999999})
        main(["status", "--hive", "deadhive"])
        captured = capsys.readouterr()
        assert "stopped" in captured.out


# ---------------------------------------------------------------------------
# Tests: stop
# ---------------------------------------------------------------------------


class TestStop:
    def test_stop_no_pids_returns_0(self, tmp_hives, capsys):
        main(["create", "--name", "nopidshive", "--agents", "1"])
        rc = main(["stop", "--hive", "nopidshive"])
        assert rc == 0

    def test_stop_sends_sigterm(self, tmp_hives):
        main(["create", "--name", "stophive", "--agents", "1"])
        import amplihack.cli.hive as m

        # Simulate a running process by using os.getpid() (our own PID)
        # but mock os.kill so we don't actually kill ourselves
        _save_pids("stophive", {"agent_0": os.getpid()})

        killed = []
        original_kill = os.kill

        def mock_kill(pid, sig):
            if sig == signal.SIGTERM:
                killed.append(pid)
            # Don't raise for our own PID

        with patch("amplihack.cli.hive.os.kill", side_effect=mock_kill):
            # Also mock _is_running to say process is running
            with patch("amplihack.cli.hive._is_running", return_value=True):
                rc = main(["stop", "--hive", "stophive"])

        assert rc == 0
        assert os.getpid() in killed

    def test_stop_clears_pids(self, tmp_hives):
        main(["create", "--name", "clearpidshive", "--agents", "1"])
        import amplihack.cli.hive as m
        _save_pids("clearpidshive", {"agent_0": 999999999})

        # Mock _is_running to return False (already gone)
        with patch("amplihack.cli.hive._is_running", return_value=False):
            main(["stop", "--hive", "clearpidshive"])

        pids = _load_pids("clearpidshive")
        assert pids == {}


# ---------------------------------------------------------------------------
# Tests: helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_is_running_own_pid(self):
        assert _is_running(os.getpid()) is True

    def test_is_running_nonexistent(self):
        assert _is_running(999999999) is False

    def test_load_config_missing_raises(self, tmp_hives):
        with pytest.raises(FileNotFoundError):
            _load_config("does_not_exist")

    def test_save_and_load_pids(self, tmp_hives):
        main(["create", "--name", "pidhive", "--agents", "1"])
        _save_pids("pidhive", {"agent_0": 12345})
        pids = _load_pids("pidhive")
        assert pids["agent_0"] == 12345


# ---------------------------------------------------------------------------
# Tests: main entry point
# ---------------------------------------------------------------------------


class TestMain:
    def test_main_no_args_returns_0(self, tmp_hives):
        rc = main([])
        assert rc == 0

    def test_main_unknown_command_returns_nonzero(self, tmp_hives):
        # argparse will print error and exit — expect SystemExit or return code
        with pytest.raises(SystemExit):
            main(["unknown-command"])
