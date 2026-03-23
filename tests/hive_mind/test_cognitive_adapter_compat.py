from __future__ import annotations

from pathlib import Path

from amplihack.agents.goal_seeking import cognitive_adapter as cognitive_adapter_module


def test_cognitive_adapter_skips_tuning_kwargs_for_legacy_memory(
    monkeypatch, tmp_path: Path
) -> None:
    captured: dict[str, object] = {}

    class LegacyCognitiveMemory:
        def __init__(self, agent_name: str, db_path: str, buffer_pool_size: int = 0) -> None:
            captured.update(
                {
                    "agent_name": agent_name,
                    "db_path": db_path,
                    "buffer_pool_size": buffer_pool_size,
                }
            )

        def close(self) -> None:
            return None

    monkeypatch.setattr(cognitive_adapter_module, "HAS_COGNITIVE_MEMORY", True)
    monkeypatch.setattr(cognitive_adapter_module, "CognitiveMemory", LegacyCognitiveMemory)

    adapter = cognitive_adapter_module.CognitiveAdapter("legacy-agent", db_path=tmp_path)

    assert adapter.backend_type == "cognitive"
    assert captured == {
        "agent_name": "legacy-agent",
        "db_path": str(tmp_path / "kuzu_db"),
        "buffer_pool_size": cognitive_adapter_module.KUZU_BUFFER_POOL_SIZE,
    }


def test_cognitive_adapter_passes_tuning_kwargs_when_supported(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    class TunedCognitiveMemory:
        def __init__(
            self,
            agent_name: str,
            db_path: str,
            buffer_pool_size: int = 0,
            similarity_threshold: float | None = None,
            max_edges_per_node: int | None = None,
            hop_depth: int | None = None,
        ) -> None:
            captured.update(
                {
                    "agent_name": agent_name,
                    "db_path": db_path,
                    "buffer_pool_size": buffer_pool_size,
                    "similarity_threshold": similarity_threshold,
                    "max_edges_per_node": max_edges_per_node,
                    "hop_depth": hop_depth,
                }
            )

        def close(self) -> None:
            return None

    monkeypatch.setattr(cognitive_adapter_module, "HAS_COGNITIVE_MEMORY", True)
    monkeypatch.setattr(cognitive_adapter_module, "CognitiveMemory", TunedCognitiveMemory)

    adapter = cognitive_adapter_module.CognitiveAdapter("tuned-agent", db_path=tmp_path)

    assert adapter.backend_type == "cognitive"
    assert captured == {
        "agent_name": "tuned-agent",
        "db_path": str(tmp_path / "kuzu_db"),
        "buffer_pool_size": cognitive_adapter_module.KUZU_BUFFER_POOL_SIZE,
        "similarity_threshold": cognitive_adapter_module.SIMILARITY_THRESHOLD,
        "max_edges_per_node": cognitive_adapter_module.MAX_EDGES_PER_NODE,
        "hop_depth": cognitive_adapter_module.HOP_DEPTH,
    }
