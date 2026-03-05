"""MemoryConfig — configuration resolution for the Memory facade.

Resolution order (highest to lowest priority):
    1. Explicit kwargs passed to Memory.__init__
    2. Environment variables (AMPLIHACK_MEMORY_*)
    3. YAML config file (~/.amplihack/memory.yaml or AMPLIHACK_MEMORY_CONFIG)
    4. Built-in defaults
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


_DEFAULT_BACKEND = "cognitive"
_DEFAULT_TOPOLOGY = "single"
_DEFAULT_KUZU_BUFFER_MB = 256
_DEFAULT_REPLICATION_FACTOR = 3
_DEFAULT_QUERY_FANOUT = 5
_DEFAULT_GOSSIP_ENABLED = True
_DEFAULT_GOSSIP_ROUNDS = 3
_DEFAULT_MODEL = None


def _default_config_path() -> Path:
    env_path = os.environ.get("AMPLIHACK_MEMORY_CONFIG")
    if env_path:
        return Path(env_path)
    return Path.home() / ".amplihack" / "memory.yaml"


@dataclass
class MemoryConfig:
    """All configuration fields for the Memory facade."""

    agent_name: str = ""
    backend: str = _DEFAULT_BACKEND
    topology: str = _DEFAULT_TOPOLOGY
    storage_path: str | None = None
    shared_hive: Any | None = None
    model: str | None = _DEFAULT_MODEL
    kuzu_buffer_pool_mb: int = _DEFAULT_KUZU_BUFFER_MB
    replication_factor: int = _DEFAULT_REPLICATION_FACTOR
    query_fanout: int = _DEFAULT_QUERY_FANOUT
    gossip_enabled: bool = _DEFAULT_GOSSIP_ENABLED
    gossip_rounds: int = _DEFAULT_GOSSIP_ROUNDS

    @classmethod
    def from_env(cls) -> "MemoryConfig":
        """Build a MemoryConfig from environment variables.

        Only sets fields for which env vars are present; all others remain at
        the dataclass defaults so callers can overlay them later.
        """
        kwargs: dict[str, Any] = {}

        backend = os.environ.get("AMPLIHACK_MEMORY_BACKEND")
        if backend is not None:
            kwargs["backend"] = backend

        topology = os.environ.get("AMPLIHACK_MEMORY_TOPOLOGY")
        if topology is not None:
            kwargs["topology"] = topology

        storage_path = os.environ.get("AMPLIHACK_MEMORY_STORAGE_PATH")
        if storage_path is not None:
            kwargs["storage_path"] = storage_path

        kuzu_mb = os.environ.get("AMPLIHACK_MEMORY_KUZU_BUFFER_MB")
        if kuzu_mb is not None:
            kwargs["kuzu_buffer_pool_mb"] = int(kuzu_mb)

        replication = os.environ.get("AMPLIHACK_MEMORY_REPLICATION")
        if replication is not None:
            kwargs["replication_factor"] = int(replication)

        fanout = os.environ.get("AMPLIHACK_MEMORY_QUERY_FANOUT")
        if fanout is not None:
            kwargs["query_fanout"] = int(fanout)

        gossip = os.environ.get("AMPLIHACK_MEMORY_GOSSIP")
        if gossip is not None:
            kwargs["gossip_enabled"] = gossip.strip().lower() in ("1", "true", "yes")

        gossip_rounds = os.environ.get("AMPLIHACK_MEMORY_GOSSIP_ROUNDS")
        if gossip_rounds is not None:
            kwargs["gossip_rounds"] = int(gossip_rounds)

        return cls(**kwargs)

    @classmethod
    def from_file(cls, path: str | Path | None = None) -> "MemoryConfig":
        """Load a MemoryConfig from a YAML file.

        Returns a default MemoryConfig if the file does not exist.
        """
        if path is None:
            path = _default_config_path()
        path = Path(path)
        if not path.exists():
            return cls()

        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError:
            return cls()

        with path.open() as fh:
            data = yaml.safe_load(fh) or {}

        kwargs: dict[str, Any] = {}
        _str_fields = ("backend", "topology", "storage_path", "model")
        _int_fields = ("kuzu_buffer_pool_mb", "replication_factor", "query_fanout", "gossip_rounds")
        _bool_fields = ("gossip_enabled",)

        for f in _str_fields:
            if f in data:
                kwargs[f] = str(data[f])
        for f in _int_fields:
            if f in data:
                kwargs[f] = int(data[f])
        for f in _bool_fields:
            if f in data:
                val = data[f]
                if isinstance(val, bool):
                    kwargs[f] = val
                else:
                    kwargs[f] = str(val).lower() in ("1", "true", "yes")

        return cls(**kwargs)

    @classmethod
    def resolve(
        cls,
        agent_name: str = "",
        *,
        config_file: str | Path | None = None,
        **kwargs: Any,
    ) -> "MemoryConfig":
        """Merge all config sources in priority order.

        Priority (highest first): explicit kwargs > env vars > file > defaults.
        """
        # Start from file defaults
        cfg = cls.from_file(config_file)
        cfg.agent_name = agent_name

        # Overlay env vars — check presence directly so that even values that
        # match the built-in defaults override the file config.
        _env_map = {
            "backend": ("AMPLIHACK_MEMORY_BACKEND", str),
            "topology": ("AMPLIHACK_MEMORY_TOPOLOGY", str),
            "storage_path": ("AMPLIHACK_MEMORY_STORAGE_PATH", str),
            "kuzu_buffer_pool_mb": ("AMPLIHACK_MEMORY_KUZU_BUFFER_MB", int),
            "replication_factor": ("AMPLIHACK_MEMORY_REPLICATION", int),
            "query_fanout": ("AMPLIHACK_MEMORY_QUERY_FANOUT", int),
            "gossip_rounds": ("AMPLIHACK_MEMORY_GOSSIP_ROUNDS", int),
        }
        for field_name, (env_key, converter) in _env_map.items():
            raw = os.environ.get(env_key)
            if raw is not None:
                setattr(cfg, field_name, converter(raw))

        gossip_raw = os.environ.get("AMPLIHACK_MEMORY_GOSSIP")
        if gossip_raw is not None:
            cfg.gossip_enabled = gossip_raw.strip().lower() in ("1", "true", "yes")

        # Overlay explicit kwargs (highest priority)
        for key, val in kwargs.items():
            if val is not None and hasattr(cfg, key):
                setattr(cfg, key, val)

        # Apply derived defaults
        if cfg.storage_path is None:
            cfg.storage_path = f"/tmp/amplihack-memory/{agent_name}" if agent_name else "/tmp/amplihack-memory/default"

        return cfg


__all__ = ["MemoryConfig"]
