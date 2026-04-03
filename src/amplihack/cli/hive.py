"""amplihack-hive — CLI for managing distributed hive mind deployments.

Commands:
    create     Scaffold a new hive config file
    add-agent  Append an agent definition to an existing hive config
    start      Start all agents (locally as subprocesses, or on Azure)
    status     Show running agent PIDs and fact counts
    stop       Terminate all running agents

Hive config format (~/.amplihack/hives/NAME/config.yaml):
    name: my-hive
    transport: azure_service_bus
    connection_string: Endpoint=sb://...
    storage_path: /data/hive
    shard_backend: kuzu
    agents:
      - name: agent_0
        prompt: "You are a security analyst"
        kuzu_db: /path/to/existing.db   # optional
      - name: agent_1
        prompt: "You are a network engineer"

Usage:
    amplihack-hive create --name my-hive --agents 3
    amplihack-hive add-agent --hive my-hive --agent-name agent_3 --prompt "You are an SRE"
    amplihack-hive start --hive my-hive [--target local|azure]
    amplihack-hive status --hive my-hive
    amplihack-hive stop --hive my-hive
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_HIVES_DIR = Path.home() / ".amplihack" / "hives"
_PID_FILENAME = "pids.json"


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _hive_dir(name: str) -> Path:
    return _HIVES_DIR / name


def _config_path(name: str) -> Path:
    return _hive_dir(name) / "config.yaml"


def _pid_path(name: str) -> Path:
    return _hive_dir(name) / _PID_FILENAME


def _load_config(name: str) -> dict[str, Any]:
    """Load hive config YAML. Raises FileNotFoundError if missing."""
    path = _config_path(name)
    if not path.exists():
        raise FileNotFoundError(
            f"Hive '{name}' not found. Run: amplihack-hive create --name {name}"
        )
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        # Fallback: parse very simple YAML manually won't scale; just raise
        raise ImportError("PyYAML is required. Install with: pip install pyyaml")
    with path.open() as fh:
        return yaml.safe_load(fh) or {}


def _save_config(name: str, config: dict[str, Any]) -> None:
    """Save hive config to YAML file."""
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        raise ImportError("PyYAML is required. Install with: pip install pyyaml")
    path = _config_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        yaml.safe_dump(config, fh, default_flow_style=False, sort_keys=False)


def _load_pids(name: str) -> dict[str, int]:
    """Load saved agent PIDs."""
    pid_file = _pid_path(name)
    if not pid_file.exists():
        return {}
    try:
        return json.loads(pid_file.read_text())
    except Exception:
        return {}


def _save_pids(name: str, pids: dict[str, int]) -> None:
    pid_file = _pid_path(name)
    pid_file.write_text(json.dumps(pids, indent=2))


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------


def cmd_create(args: argparse.Namespace) -> int:
    """Create a new hive config scaffold.

    Creates ~/.amplihack/hives/NAME/config.yaml with N placeholder agents.
    """
    name = args.name
    n_agents = args.agents
    transport = getattr(args, "transport", "local")
    connection_string = getattr(args, "connection_string", "")
    storage_path = getattr(args, "storage_path", f"/data/hive/{name}")
    shard_backend = getattr(args, "shard_backend", "memory")

    config: dict[str, Any] = {
        "name": name,
        "transport": transport,
        "connection_string": connection_string,
        "storage_path": storage_path,
        "shard_backend": shard_backend,
        "agents": [
            {
                "name": f"agent_{i}",
                "prompt": f"You are agent {i} in the {name} hive.",
            }
            for i in range(n_agents)
        ],
    }

    if _config_path(name).exists():
        print(f"Warning: hive '{name}' already exists. Overwriting config.", file=sys.stderr)

    _save_config(name, config)
    print(f"Created hive '{name}' with {n_agents} agents at {_config_path(name)}")
    return 0


def cmd_add_agent(args: argparse.Namespace) -> int:
    """Add an agent entry to an existing hive config."""
    hive_name = args.hive
    agent_name = args.agent_name
    prompt = args.prompt
    kuzu_db = getattr(args, "kuzu_db", None)

    config = _load_config(hive_name)

    if "agents" not in config:
        config["agents"] = []

    # Check for duplicate name
    existing_names = {a.get("name") for a in config["agents"]}
    if agent_name in existing_names:
        print(f"Error: agent '{agent_name}' already exists in hive '{hive_name}'.", file=sys.stderr)
        return 1

    agent: dict[str, Any] = {"name": agent_name, "prompt": prompt}
    if kuzu_db:
        agent["kuzu_db"] = kuzu_db

    config["agents"].append(agent)
    _save_config(hive_name, config)
    print(f"Added agent '{agent_name}' to hive '{hive_name}'")
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    """Start agents for a hive.

    Local target: launches each agent as a subprocess using agent_entrypoint.py.
    Azure target: delegates to deploy/azure_hive/deploy.sh.
    """
    hive_name = args.hive
    target = getattr(args, "target", "local")

    config = _load_config(hive_name)

    if target == "azure":
        return _start_azure(hive_name, config, args)

    return _start_local(hive_name, config)


def _start_local(hive_name: str, config: dict[str, Any]) -> int:
    """Launch each agent as a local subprocess."""
    agents = config.get("agents", [])
    if not agents:
        print(f"No agents defined in hive '{hive_name}'.", file=sys.stderr)
        return 1

    pids: dict[str, int] = _load_pids(hive_name)
    transport = config.get("transport", "local")
    connection_string = config.get("connection_string", "")
    storage_path = config.get("storage_path", f"/tmp/amplihack-hive/{hive_name}")

    # Find agent_entrypoint.py relative to this file or installed location
    entrypoint = _find_entrypoint()

    new_pids: dict[str, int] = {}
    for agent in agents:
        agent_name = agent.get("name", "unknown")
        if agent_name in pids and _is_running(pids[agent_name]):
            print(f"  {agent_name}: already running (pid={pids[agent_name]})")
            new_pids[agent_name] = pids[agent_name]
            continue

        env = dict(os.environ)
        env["AMPLIHACK_AGENT_NAME"] = agent_name
        env["AMPLIHACK_AGENT_PROMPT"] = agent.get("prompt", "")
        env["AMPLIHACK_MEMORY_TRANSPORT"] = transport
        env["AMPLIHACK_MEMORY_CONNECTION_STRING"] = connection_string
        env["AMPLIHACK_MEMORY_STORAGE_PATH"] = os.path.join(storage_path, agent_name)
        if agent.get("kuzu_db"):
            env["AMPLIHACK_KUZU_DB"] = agent["kuzu_db"]

        proc = subprocess.Popen(
            [sys.executable, entrypoint],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        new_pids[agent_name] = proc.pid
        print(f"  Started {agent_name} (pid={proc.pid})")

    _save_pids(hive_name, new_pids)
    print(f"Hive '{hive_name}' started with {len(new_pids)} agents.")
    return 0


def _start_azure(hive_name: str, config: dict[str, Any], args: argparse.Namespace) -> int:
    """Delegate Azure deployment to deploy.sh."""
    # Find deploy.sh
    deploy_script = _find_deploy_script()
    if deploy_script is None:
        print(
            "Error: deploy/azure_hive/deploy.sh not found. Run from the amplihack repo root.",
            file=sys.stderr,
        )
        return 1

    env = dict(os.environ)
    env["HIVE_NAME"] = hive_name
    env["HIVE_TRANSPORT"] = config.get("transport", "azure_service_bus")
    env["HIVE_CONNECTION_STRING"] = config.get("connection_string", "")
    env["HIVE_STORAGE_PATH"] = config.get("storage_path", f"/data/hive/{hive_name}")
    env["HIVE_AGENT_COUNT"] = str(len(config.get("agents", [])))

    print(f"Deploying hive '{hive_name}' to Azure...")
    result = subprocess.run(["bash", str(deploy_script)], env=env)
    return result.returncode


def cmd_status(args: argparse.Namespace) -> int:
    """Show running agents and their fact counts."""
    hive_name = args.hive
    config = _load_config(hive_name)
    pids = _load_pids(hive_name)
    agents = config.get("agents", [])

    print(f"Hive: {hive_name}")
    print(f"Transport: {config.get('transport', 'local')}")
    print(f"Agents: {len(agents)}")
    print()

    if not agents:
        print("No agents defined.")
        return 0

    print(f"{'Agent':<20} {'Status':<12} {'PID':<10} {'Facts':<10}")
    print("-" * 55)

    for agent in agents:
        agent_name = agent.get("name", "?")
        pid = pids.get(agent_name)
        if pid and _is_running(pid):
            status = "running"
            facts = _get_fact_count(hive_name, agent_name, config)
        else:
            status = "stopped"
            facts = "-"
            pid = pid or "-"
        print(f"{agent_name:<20} {status:<12} {pid!s:<10} {facts!s:<10}")

    return 0


def cmd_stop(args: argparse.Namespace) -> int:
    """Terminate all running agents for a hive."""
    hive_name = args.hive
    pids = _load_pids(hive_name)

    if not pids:
        print(f"No running agents found for hive '{hive_name}'.")
        return 0

    stopped = 0
    for agent_name, pid in list(pids.items()):
        if _is_running(pid):
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"  Stopped {agent_name} (pid={pid})")
                stopped += 1
            except ProcessLookupError:
                print(f"  {agent_name} (pid={pid}) already gone")
            except PermissionError:
                print(f"  Cannot stop {agent_name} (pid={pid}): permission denied", file=sys.stderr)

    # Clear pids file
    _save_pids(hive_name, {})
    print(f"Stopped {stopped} agent(s) in hive '{hive_name}'.")
    return 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_running(pid: int) -> bool:
    """Check if a process with the given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def _get_fact_count(hive_name: str, agent_name: str, config: dict[str, Any]) -> str:
    """Try to get fact count from agent's local store. Returns '-' on failure."""
    storage_path = config.get("storage_path", f"/tmp/amplihack-hive/{hive_name}")
    agent_storage = os.path.join(storage_path, agent_name, "graph_store")
    if not os.path.exists(agent_storage):
        return "0"
    # For in-memory or inaccessible stores, just return unknown
    return "?"


def _find_entrypoint() -> str:
    """Find agent_entrypoint.py in the deploy directory or package."""
    candidates = [
        # Installed as part of the package
        Path(__file__).parent.parent.parent.parent
        / "deploy"
        / "azure_hive"
        / "agent_entrypoint.py",
        # Development: repo root
        Path(__file__).parent.parent.parent.parent.parent
        / "deploy"
        / "azure_hive"
        / "agent_entrypoint.py",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    # Fallback: create a minimal inline entrypoint script
    return _get_inline_entrypoint()


def _get_inline_entrypoint() -> str:
    """Write an inline entrypoint to a temp file if deploy dir not found."""
    import tempfile

    script = '''#!/usr/bin/env python3
"""Inline agent entrypoint for local hive start."""
import os, sys, time, logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s: %(message)s")
logger = logging.getLogger("agent")
agent_name = os.environ.get("AMPLIHACK_AGENT_NAME", "agent")
prompt = os.environ.get("AMPLIHACK_AGENT_PROMPT", "You are a helpful agent.")
transport = os.environ.get("AMPLIHACK_MEMORY_TRANSPORT", "local")
conn_str = os.environ.get("AMPLIHACK_MEMORY_CONNECTION_STRING", "")
logger.info("Agent %s starting (transport=%s)", agent_name, transport)
try:
    from amplihack.memory.facade import Memory
    mem = Memory(agent_name, memory_transport=transport, memory_connection_string=conn_str)
    mem.remember(f"Agent {agent_name} initialized. Prompt: {prompt}")
    logger.info("Agent %s memory initialized", agent_name)
    # Simple OODA loop placeholder - just keep alive
    while True:
        time.sleep(10)
        logger.debug("Agent %s heartbeat", agent_name)
except KeyboardInterrupt:
    pass
except Exception as e:
    logger.exception("Agent %s failed: %s", agent_name, e)
    sys.exit(1)
'''
    tmp = tempfile.NamedTemporaryFile(suffix="_agent_entrypoint.py", delete=False, mode="w")
    tmp.write(script)
    tmp.close()
    return tmp.name


def _find_deploy_script() -> Path | None:
    """Find deploy/azure_hive/deploy.sh."""
    candidates = [
        Path(__file__).parent.parent.parent.parent / "deploy" / "azure_hive" / "deploy.sh",
        Path(__file__).parent.parent.parent.parent.parent / "deploy" / "azure_hive" / "deploy.sh",
        Path.cwd() / "deploy" / "azure_hive" / "deploy.sh",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="amplihack-hive",
        description="Manage distributed hive mind deployments.",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # create
    p_create = subparsers.add_parser("create", help="Create a new hive config")
    p_create.add_argument("--name", required=True, help="Hive name")
    p_create.add_argument(
        "--agents", type=int, default=1, help="Number of initial agents (default: 1)"
    )
    p_create.add_argument(
        "--transport",
        default="local",
        choices=["local", "redis", "azure_service_bus"],
        help="Event transport (default: local)",
    )
    p_create.add_argument(
        "--connection-string",
        dest="connection_string",
        default="",
        help="Connection string for Azure Service Bus or Redis URL",
    )
    p_create.add_argument(
        "--storage-path",
        dest="storage_path",
        default="",
        help="Storage path for agent data",
    )
    p_create.add_argument(
        "--shard-backend",
        dest="shard_backend",
        default="memory",
        choices=["memory", "kuzu"],
        help="Graph store backend (default: memory)",
    )

    # add-agent
    p_add = subparsers.add_parser("add-agent", help="Add an agent to an existing hive")
    p_add.add_argument("--hive", required=True, help="Hive name")
    p_add.add_argument("--agent-name", dest="agent_name", required=True, help="Agent name")
    p_add.add_argument("--prompt", required=True, help="Agent system prompt")
    p_add.add_argument(
        "--kuzu-db",
        dest="kuzu_db",
        default=None,
        help="Path to existing Kuzu database to mount",
    )

    # start
    p_start = subparsers.add_parser("start", help="Start hive agents")
    p_start.add_argument("--hive", required=True, help="Hive name")
    p_start.add_argument(
        "--target",
        default="local",
        choices=["local", "azure"],
        help="Deployment target (default: local)",
    )

    # status
    p_status = subparsers.add_parser("status", help="Show hive agent status")
    p_status.add_argument("--hive", required=True, help="Hive name")

    # stop
    p_stop = subparsers.add_parser("stop", help="Stop all hive agents")
    p_stop.add_argument("--hive", required=True, help="Hive name")

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    # Set defaults for optional fields that may be missing
    if args.command == "create" and not args.storage_path:
        args.storage_path = f"/data/hive/{args.name}"

    commands = {
        "create": cmd_create,
        "add-agent": cmd_add_agent,
        "start": cmd_start,
        "status": cmd_status,
        "stop": cmd_stop,
    }

    fn = commands.get(args.command)
    if fn is None:
        parser.print_help()
        return 1

    try:
        return fn(args)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        logger.exception("Unexpected error")
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
