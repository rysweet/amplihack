"""Tests for agent_entrypoint.py."""

from __future__ import annotations

import importlib.util
import os
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Load agent_entrypoint as a module (not installed as package)
_ENTRYPOINT_PATH = Path(__file__).parent.parent / "agent_entrypoint.py"


def _load_entrypoint():
    spec = importlib.util.spec_from_file_location("agent_entrypoint", _ENTRYPOINT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestAgentEntrypoint:
    def test_entrypoint_file_exists(self):
        assert _ENTRYPOINT_PATH.exists()

    def test_entrypoint_has_main(self):
        mod = _load_entrypoint()
        assert hasattr(mod, "main")
        assert callable(mod.main)

    def test_missing_agent_name_exits_1(self, monkeypatch):
        monkeypatch.delenv("AMPLIHACK_AGENT_NAME", raising=False)
        mod = _load_entrypoint()
        with pytest.raises(SystemExit) as exc_info:
            mod.main()
        assert exc_info.value.code == 1

    def test_main_initializes_memory(self, monkeypatch):
        monkeypatch.setenv("AMPLIHACK_AGENT_NAME", "test-agent")
        monkeypatch.setenv("AMPLIHACK_MEMORY_TRANSPORT", "local")

        mock_memory_instance = MagicMock()
        mock_memory_instance.stats.return_value = {"fact_count": 0}
        mock_memory_instance.recall.return_value = []

        # Make the OODA loop exit after one iteration
        call_count = [0]
        original_sleep = time.sleep

        def fast_sleep(secs):
            call_count[0] += 1
            if call_count[0] > 2:
                raise KeyboardInterrupt

        mod = _load_entrypoint()

        with patch("amplihack.memory.facade.Memory", return_value=mock_memory_instance):
            with patch.object(mod, "_ooda_tick") as mock_tick:
                with patch("time.sleep", side_effect=fast_sleep):
                    try:
                        mod.main()
                    except (KeyboardInterrupt, SystemExit):
                        pass

        # Memory should have been constructed
        mock_memory_instance.remember.assert_called()

    def test_ooda_tick_logs_stats_every_10_ticks(self, monkeypatch):
        mod = _load_entrypoint()
        mock_mem = MagicMock()
        mock_mem.stats.return_value = {"fact_count": 5}
        mock_mem.recall.return_value = []

        # Tick 0 should call stats
        mod._ooda_tick("agent", "prompt", mock_mem, 0)
        mock_mem.stats.assert_called_once()

        # Tick 5 should NOT call stats
        mock_mem.stats.reset_mock()
        mod._ooda_tick("agent", "prompt", mock_mem, 5)
        mock_mem.stats.assert_not_called()

        # Tick 10 should call stats again
        mod._ooda_tick("agent", "prompt", mock_mem, 10)
        mock_mem.stats.assert_called_once()


class TestDockerfile:
    def test_dockerfile_exists(self):
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        assert dockerfile.exists()

    def test_dockerfile_has_python_base(self):
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile.read_text()
        assert "python:3.11-slim" in content

    def test_dockerfile_has_non_root_user(self):
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile.read_text()
        assert "useradd" in content
        assert "USER amplihack-agent" in content

    def test_dockerfile_installs_kuzu(self):
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile.read_text()
        assert "kuzu" in content

    def test_dockerfile_installs_sentence_transformers(self):
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile.read_text()
        assert "sentence-transformers" in content

    def test_dockerfile_has_entrypoint(self):
        dockerfile = Path(__file__).parent.parent / "Dockerfile"
        content = dockerfile.read_text()
        assert "agent_entrypoint.py" in content


class TestDeployScript:
    def test_deploy_sh_exists(self):
        deploy_sh = Path(__file__).parent.parent / "deploy.sh"
        assert deploy_sh.exists()

    def test_deploy_sh_is_executable(self):
        deploy_sh = Path(__file__).parent.parent / "deploy.sh"
        assert os.access(deploy_sh, os.X_OK)

    def test_deploy_sh_provisions_service_bus(self):
        deploy_sh = Path(__file__).parent.parent / "deploy.sh"
        content = deploy_sh.read_text()
        assert "ServiceBus" in content or "servicebus" in content.lower() or "service_bus" in content.lower()

    def test_deploy_sh_provisions_acr(self):
        deploy_sh = Path(__file__).parent.parent / "deploy.sh"
        content = deploy_sh.read_text()
        assert "acr" in content.lower() or "ContainerRegistry" in content

    def test_deploy_sh_provisions_file_share(self):
        deploy_sh = Path(__file__).parent.parent / "deploy.sh"
        content = deploy_sh.read_text()
        assert "file" in content.lower() and ("share" in content.lower() or "storage" in content.lower())

    def test_deploy_sh_has_container_apps(self):
        deploy_sh = Path(__file__).parent.parent / "deploy.sh"
        content = deploy_sh.read_text()
        assert "containerapp" in content.lower() or "Container App" in content

    def test_deploy_sh_groups_5_agents_per_app(self):
        deploy_sh = Path(__file__).parent.parent / "deploy.sh"
        content = deploy_sh.read_text()
        assert "AGENTS_PER_APP" in content

    def test_deploy_sh_has_cleanup_mode(self):
        deploy_sh = Path(__file__).parent.parent / "deploy.sh"
        content = deploy_sh.read_text()
        assert "--cleanup" in content


class TestBicep:
    def test_bicep_exists(self):
        bicep = Path(__file__).parent.parent / "main.bicep"
        assert bicep.exists()

    def test_bicep_has_container_apps_env(self):
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "managedEnvironments" in content

    def test_bicep_has_service_bus(self):
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "ServiceBus" in content or "servicebus" in content.lower()

    def test_bicep_has_file_share(self):
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "fileServices" in content or "fileShare" in content

    def test_bicep_has_container_registry(self):
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "ContainerRegistry" in content

    def test_bicep_has_agent_count_param(self):
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "agentCount" in content

    def test_bicep_has_agents_per_app_param(self):
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "agentsPerApp" in content

    def test_bicep_references_connection_string(self):
        bicep = Path(__file__).parent.parent / "main.bicep"
        content = bicep.read_text()
        assert "AMPLIHACK_MEMORY_CONNECTION_STRING" in content
