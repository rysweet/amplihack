"""Smoke tests for the pinned RemoteAgentAdapter compatibility wrappers."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SRC_ROOT = _REPO_ROOT / "src"
_DEPLOY_WRAPPER_PATH = _REPO_ROOT / "deploy" / "azure_hive" / "remote_agent_adapter.py"

if str(_SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(_SRC_ROOT))


def _load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class TestRemoteAgentAdapterWrapper:
    def test_deploy_wrapper_exposes_remote_agent_adapter(self):
        module = _load_module(
            _DEPLOY_WRAPPER_PATH,
            "deploy.azure_hive.remote_agent_adapter_test",
        )

        assert hasattr(module, "RemoteAgentAdapter")
        assert module.RemoteAgentAdapter.__name__ == "RemoteAgentAdapter"

    def test_eval_distributed_adapter_exposes_remote_agent_adapter(self):
        from amplihack.eval.distributed_adapter import RemoteAgentAdapter

        assert RemoteAgentAdapter.__name__ == "RemoteAgentAdapter"
