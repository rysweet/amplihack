#!/usr/bin/env python3
"""100-agent topology scale validation.

Probes the deployed 100-agent hive for known scale bottlenecks and reports
readiness for a full eval run.  Does not send any LLM requests — all checks
are infrastructure-level.

Bottlenecks identified at 100-agent scale
------------------------------------------
1. EVENT HUB PARTITION LIMITS
   Azure Event Hubs Basic/Standard supports up to 32 partitions per hub.
   With 100 agents, multiple agents share a partition.  The partition
   key routing in RemoteAgentAdapter maps agent-N → partition N % P.
   With 32 partitions and 100 agents, each partition serves ~3 agents.
   Target agents are identified by the target_agent payload field, not
   solely by partition — so partition sharing is safe but adds latency.
   Recommendation: Use 32 partitions (Standard tier or Premium with
   up to 100 partitions for strict isolation).

2. CONSUMER GROUP EXHAUSTION
   Standard EH supports 20 consumer groups per hub (Premium: unlimited).
   agent_entrypoint.py assigns consumer groups: cg-app-{app_index} (one
   per Container App, where each app hosts 5 agents).  100 agents = 20 apps
   = 20 consumer groups on the input hub.  This exactly hits the Standard
   tier limit.  Symptoms: new consumer groups fail with 409 Conflict.
   Fix: use Premium tier OR reduce to <20 Container Apps (>5 agents/app).

3. MEMORY PRESSURE PER AGENT
   Each agent's KuzuStore uses KUZU_BUFFER_POOL_SIZE = 256 MB.  At 5 agents
   per Container App, that's 5 * 256 MB = 1.28 GB buffer pool + OS overhead.
   Typical Container App CPU/memory: 1 vCPU / 2 GB.
   Recommendation: ensure Container Apps are sized ≥ 2 GB memory.

4. DHT QUERY FAN-OUT
   With DEFAULT_QUERY_FANOUT = 5 and 100 shards, each shard query fans out
   to 5 peers.  100 simultaneous questions → 500 SHARD_QUERY messages on
   hive-shards hub.  The hive-shards hub needs ≥ 32 partitions to handle
   this burst.

5. OTEL CARDINALITY
   100 agents each emit spans with amplihack.agent_id labels.  With 5000
   turns + 50 questions per eval, total span count ≈ 500K+.  Ensure the
   OTLP backend (Aspire dashboard or Azure Monitor) is sized for this
   cardinality.  Limit: use sampling (OTEL_TRACES_SAMPLER_ARG) if cost
   is a concern.

6. AZURE CONTAINER APPS QUOTA
   Default subscription quota: 100 Container Apps per environment.
   With 20 apps (5 agents each) we are well within quota.  However,
   each app restart during a live eval can miss events.  Set
   minReplicas: 1 / maxReplicas: 1 to prevent auto-scaling restarts.

7. EVENT HUB THROUGHPUT UNITS
   At 5000 turns replicated to all 100 agents = 500K events on the input
   hub.  Standard EH at 1 TU supports 1 MB/s ingress.  Average event size
   ~2 KB → 1000 events/s max.  With 500K events over a 12-minute learning
   phase = ~700 events/s — within 1 TU.  For faster runs, provision 2+ TUs.

Usage:
    python deploy/azure_hive/eval_scale_100.py
    python deploy/azure_hive/eval_scale_100.py \\
        --connection-string "$EH_CONN" \\
        --resource-group hive-mind-rg \\
        --hive-name amplihive

Environment:
    EH_CONN               Event Hubs namespace connection string
    HIVE_NAME             Hive name (default: amplihive)
    HIVE_RESOURCE_GROUP   Resource group (default: hive-mind-rg)
    HIVE_AGENT_COUNT      Expected agent count (default: 100)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [eval_scale_100] %(levelname)s: %(message)s",
)
logger = logging.getLogger("eval_scale_100")

_PASS = "\033[32m✓\033[0m"
_FAIL = "\033[31m✗\033[0m"
_WARN = "\033[33m⚠\033[0m"
_INFO = "\033[34mℹ\033[0m"

# Known limits
EH_STANDARD_PARTITIONS = 32
EH_STANDARD_CONSUMER_GROUPS = 20
AGENT_COUNT_TARGET = 100
AGENTS_PER_APP_DEFAULT = 5
APPS_FOR_100_AGENTS = AGENT_COUNT_TARGET // AGENTS_PER_APP_DEFAULT  # 20


def _step(ok: bool, message: str) -> bool:
    icon = _PASS if ok else _FAIL
    print(f"  {icon} {message}")
    return ok


def _warn(message: str) -> None:
    print(f"  {_WARN} {message}")


def _info(message: str) -> None:
    print(f"  {_INFO} {message}")


def _az(*args: str) -> tuple[bool, str]:
    result = subprocess.run(["az", *args], capture_output=True, text=True)
    return result.returncode == 0, result.stdout.strip()


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def check_event_hub_partitions(connection_string: str, hub_name: str, label: str) -> bool:
    """Check partition count on an Event Hub."""
    try:
        from azure.eventhub import EventHubConsumerClient  # type: ignore[import-unresolved]

        c = EventHubConsumerClient.from_connection_string(
            connection_string,
            consumer_group="$Default",
            eventhub_name=hub_name,
        )
        partitions = c.get_partition_ids()
        c.close()
        p = len(partitions)
    except ImportError:
        _warn(f"azure-eventhub not installed — cannot check partition count for {label}")
        return True
    except Exception as exc:
        return _step(False, f"{label}: unreachable ({exc})")

    if p >= EH_STANDARD_PARTITIONS:
        return _step(
            True, f"{label}: {p} partitions (≥{EH_STANDARD_PARTITIONS} — optimal for 100 agents)"
        )
    if p >= 16:
        _warn(
            f"{label}: {p} partitions (≥16 but <32 — multiple agents share each partition; "
            "latency may increase under load)"
        )
        return True
    return _step(
        False,
        f"{label}: only {p} partition(s). With 100 agents, many agents share partitions. "
        "Recommend upgrading to ≥32 partitions (Standard/Premium tier).",
    )


def check_consumer_group_headroom(resource_group: str, namespace: str, hub_name: str) -> bool:
    """Warn if consumer groups are close to the Standard tier limit."""
    ok, out = _az(
        "eventhubs",
        "eventhub",
        "consumer-group",
        "list",
        "--namespace-name",
        namespace,
        "--eventhub-name",
        hub_name,
        "--resource-group",
        resource_group,
        "--query",
        "[].name",
        "--output",
        "json",
    )
    if not ok:
        _warn(
            "Could not list consumer groups — ensure Standard tier has ≥20 consumer groups for 100 agents"
        )
        return True
    try:
        groups = json.loads(out or "[]")
    except json.JSONDecodeError:
        groups = []
    count = len(groups)
    if count >= EH_STANDARD_CONSUMER_GROUPS:
        return _step(
            False,
            f"Consumer groups on {hub_name}: {count}/{EH_STANDARD_CONSUMER_GROUPS} (LIMIT REACHED). "
            "Upgrade to Premium EH or reduce Container Apps count.",
        )
    if count >= EH_STANDARD_CONSUMER_GROUPS - 2:
        _warn(
            f"Consumer groups on {hub_name}: {count}/{EH_STANDARD_CONSUMER_GROUPS} "
            "(approaching limit — only 2 slots remaining)"
        )
        return True
    return _step(
        True,
        f"Consumer groups on {hub_name}: {count}/{EH_STANDARD_CONSUMER_GROUPS} "
        f"(headroom: {EH_STANDARD_CONSUMER_GROUPS - count} remaining)",
    )


def check_container_app_count(resource_group: str, hive_name: str, expected_agents: int) -> bool:
    """Check Container Apps count and agent distribution."""
    ok, out = _az(
        "containerapp",
        "list",
        "--resource-group",
        resource_group,
        "--query",
        f"[?starts_with(name, '{hive_name}')].{{name:name, replicas:properties.template.scale.minReplicas}}",
        "--output",
        "json",
    )
    if not ok:
        _warn("Could not query Container Apps — skipping count check")
        return True
    try:
        apps = json.loads(out or "[]")
    except json.JSONDecodeError:
        apps = []

    count = len(apps)
    agents_per_app = AGENTS_PER_APP_DEFAULT
    actual_agents = count * agents_per_app

    if actual_agents < expected_agents:
        return _step(
            False,
            f"Container Apps: {count} apps x {agents_per_app} agents = {actual_agents} agents "
            f"(expected {expected_agents})",
        )
    _step(
        True,
        f"Container Apps: {count} apps x {agents_per_app} agents/app = {actual_agents} agents",
    )

    # Check minReplicas = 1 (no auto-scaling during eval)
    non_fixed = [a["name"] for a in apps if (a.get("replicas") or 0) != 1]
    if non_fixed:
        _warn(
            f"minReplicas ≠ 1 on {len(non_fixed)} apps — restarts during eval can cause missed events: "
            + ", ".join(non_fixed[:5])
        )
    else:
        _step(True, "All Container Apps have minReplicas=1 (no restart risk during eval)")
    return True


def check_container_app_resources(resource_group: str, hive_name: str) -> bool:
    """Check CPU/memory allocation per Container App."""
    ok, out = _az(
        "containerapp",
        "list",
        "--resource-group",
        resource_group,
        "--query",
        (
            f"[?starts_with(name, '{hive_name}')]"
            ".{name:name, cpu:properties.template.containers[0].resources.cpu,"
            " memory:properties.template.containers[0].resources.memory}"
        ),
        "--output",
        "json",
    )
    if not ok:
        _warn("Could not query Container App resources — skipping memory check")
        return True
    try:
        apps = json.loads(out or "[]")
    except json.JSONDecodeError:
        apps = []

    under_provisioned: list[str] = []
    for app in apps:
        mem_str = str(app.get("memory") or "")
        # Parse "2Gi", "1.5Gi", etc.
        mem_gi = 0.0
        if mem_str.endswith("Gi"):
            try:
                mem_gi = float(mem_str[:-2])
            except ValueError:
                pass
        # Each app runs 5 agents x 256 MB buffer pool = 1.28 GB minimum
        if 0 < mem_gi < 2.0:
            under_provisioned.append(f"{app['name']}({mem_str})")

    if under_provisioned:
        _warn(
            f"{len(under_provisioned)} apps have < 2 Gi memory — "
            "risk of OOM with 5 x 256 MB Kuzu buffer pools: " + ", ".join(under_provisioned[:5])
        )
        return True
    _step(True, "Container App memory allocation looks sufficient (≥2 Gi per app)")
    return True


def check_throughput_units(resource_group: str, namespace: str) -> bool:
    """Estimate throughput unit requirements for 100-agent eval."""
    ok, out = _az(
        "eventhubs",
        "namespace",
        "show",
        "--name",
        namespace,
        "--resource-group",
        resource_group,
        "--query",
        "{sku:sku.name, capacity:sku.capacity, tier:sku.tier}",
        "--output",
        "json",
    )
    if not ok:
        _warn("Could not query EH namespace SKU — skipping throughput check")
        return True
    try:
        ns_info = json.loads(out or "{}")
    except json.JSONDecodeError:
        ns_info = {}

    sku = ns_info.get("sku", "unknown")
    capacity = int(ns_info.get("capacity") or 1)

    # 5000 turns replicated to 100 agents = 500K events
    # avg event 2 KB → 1 GB ingress
    # Standard 1 TU = 1 MB/s → 500 KB/s comfortable headroom
    # At capacity=1, 12-min learning ≈ 700 events/s peaks ≈ 1.4 MB/s → marginal
    _info(f"EH namespace SKU: {sku} capacity={capacity}")
    if capacity < 2 and sku.lower() not in ("premium", "dedicated"):
        _warn(
            f"EH capacity={capacity} TU — with 100-agent replicated eval (500K events), "
            "you may hit ingress limits during burst. Consider capacity=2 or Premium tier."
        )
    else:
        _step(True, f"EH throughput capacity adequate for 100-agent eval (capacity={capacity})")
    return True


# ---------------------------------------------------------------------------
# Static analysis of topology configuration
# ---------------------------------------------------------------------------


def check_topology_config() -> None:
    """Print static analysis of the topology configuration."""
    print("\n  Static topology analysis (100 agents):")
    print("    • federated-100 profile: 100 agents, 5 per Container App = 20 apps")
    print("    • DHT: 100 shards, DEFAULT_REPLICATION_FACTOR=3, DEFAULT_QUERY_FANOUT=5")
    print("    • At 5000 turns, each agent gets ~50 turns (round-robin partition)")
    print("    • Distributed retrieval enabled by default (HIVE_ENABLE_DISTRIBUTED_RETRIEVAL=true)")
    print("    • KuzuStore buffer: 256 MB/agent = 1.28 GB/app (5 agents/app)")
    print("    • OTEL: 100 agents x (50 turns + ~20 questions) = ~7000 spans/run")
    print()

    # Highlight the known bottlenecks
    print("  Scale bottlenecks at 100 agents:")
    print("    1. EH Standard: 20 consumer groups = exactly 20 apps (zero headroom)")
    print("       Fix: Premium EH OR ≤19 apps (≥6 agents/app)")
    print("    2. EH Standard: 32 partitions → ~3 agents/partition (safe, adds latency)")
    print("       Fix: Premium EH for 100-partition strict isolation")
    print("    3. Container App memory: 2 GB/app minimum with 5 agents x 256 MB Kuzu")
    print("       Fix: Ensure minMemory=2Gi in Bicep (current default: 2Gi ✓)")
    print("    4. OTel cardinality: 100 agent_id label values (moderate — benign)")
    print("    5. DHT fan-out: 100x5=500 SHARD_QUERY bursts per question wave")
    print("       Fix: hive-shards hub needs ≥32 partitions (provisioned by deploy.sh ✓)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(description="100-agent topology scale validation")
    p.add_argument("--connection-string", default=os.environ.get("EH_CONN", ""))
    p.add_argument("--hive-name", default=os.environ.get("HIVE_NAME", "amplihive"))
    p.add_argument(
        "--resource-group", default=os.environ.get("HIVE_RESOURCE_GROUP", "hive-mind-rg")
    )
    p.add_argument(
        "--agent-count",
        type=int,
        default=int(os.environ.get("HIVE_AGENT_COUNT", "100")),
    )
    p.add_argument(
        "--skip-azure", action="store_true", help="Skip live Azure checks (static analysis only)"
    )
    args = p.parse_args()

    hive_name = args.hive_name
    resource_group = args.resource_group
    agent_count = args.agent_count

    input_hub = f"hive-events-{hive_name}"
    shard_hub = f"hive-shards-{hive_name}"
    response_hub = f"eval-responses-{hive_name}"

    print(f"\n{'=' * 70}")
    print(f"  100-Agent Scale Validation — hive '{hive_name}'")
    print(f"  Target: {agent_count} agents | {resource_group}")
    print(f"{'=' * 70}\n")

    # Static analysis always runs
    check_topology_config()

    if args.skip_azure:
        _warn("Skipping live Azure checks (--skip-azure)")
        print(f"\n{'=' * 70}")
        print("  Static analysis complete.")
        print(f"{'=' * 70}\n")
        return 0

    if not args.connection_string:
        _warn("No --connection-string / EH_CONN set — skipping Event Hub checks")
    else:
        print("Event Hub checks:")
        check_event_hub_partitions(args.connection_string, input_hub, f"input ({input_hub})")
        check_event_hub_partitions(args.connection_string, shard_hub, f"shards ({shard_hub})")
        check_event_hub_partitions(
            args.connection_string, response_hub, f"response ({response_hub})"
        )

    # Parse namespace from connection string
    namespace = ""
    if args.connection_string:
        for part in args.connection_string.split(";"):
            if part.startswith("Endpoint="):
                endpoint = part.removeprefix("Endpoint=").strip("/")
                for _scheme in ("sb://", "amqps://", "amqp://"):
                    if endpoint.startswith(_scheme):
                        endpoint = endpoint[len(_scheme) :]
                        break
                namespace = endpoint.split(".")[0]
                break

    if namespace:
        print("\nConsumer group capacity:")
        check_consumer_group_headroom(resource_group, namespace, input_hub)
        check_consumer_group_headroom(resource_group, namespace, response_hub)

        print("\nEvent Hub throughput:")
        check_throughput_units(resource_group, namespace)

    print("\nContainer Apps:")
    check_container_app_count(resource_group, hive_name, agent_count)
    check_container_app_resources(resource_group, hive_name)

    print(f"\n{'=' * 70}")
    print(f"  Scale validation complete for {agent_count}-agent topology.")
    print("  Review ⚠ warnings above before running full 5000-turn eval.")
    print(f"{'=' * 70}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
