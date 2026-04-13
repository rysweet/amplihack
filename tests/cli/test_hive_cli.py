from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import Mock, patch

import amplihack.cli.hive as hive


def test_start_azure_requires_agents():
    args = argparse.Namespace(hive="prod-hive")

    result = hive._start_azure("prod-hive", {"agents": []}, args)

    assert result == 1


def test_start_azure_uses_custom_profile_and_event_hubs_transport():
    args = argparse.Namespace(hive="prod-hive")
    config = {
        "agents": [{"name": "agent-0"}, {"name": "agent-1"}, {"name": "agent-2"}],
        "transport": "azure_service_bus",
        "connection_string": "Endpoint=sb://legacy/",
        "storage_path": "/tmp/prod-hive",
    }
    deploy_script = Path("/tmp/deploy.sh")
    completed = Mock(returncode=0)

    with (
        patch.object(hive, "_find_deploy_script", return_value=deploy_script),
        patch.object(hive.subprocess, "run", return_value=completed) as run_mock,
    ):
        result = hive._start_azure("prod-hive", config, args)

    assert result == 0
    env = run_mock.call_args.kwargs["env"]
    assert env["HIVE_TRANSPORT"] == "azure_event_hubs"
    assert env["HIVE_DEPLOYMENT_PROFILE"] == "custom"
    assert env["HIVE_AGENT_COUNT"] == "3"
    assert env["HIVE_AGENTS_PER_APP"] == "3"


def test_start_azure_respects_existing_agents_per_app_env(monkeypatch):
    args = argparse.Namespace(hive="prod-hive")
    config = {"agents": [{"name": f"agent-{i}"} for i in range(8)]}
    deploy_script = Path("/tmp/deploy.sh")
    completed = Mock(returncode=0)

    monkeypatch.setenv("HIVE_AGENTS_PER_APP", "2")

    with (
        patch.object(hive, "_find_deploy_script", return_value=deploy_script),
        patch.object(hive.subprocess, "run", return_value=completed) as run_mock,
    ):
        result = hive._start_azure("prod-hive", config, args)

    assert result == 0
    env = run_mock.call_args.kwargs["env"]
    assert env["HIVE_AGENTS_PER_APP"] == "2"
