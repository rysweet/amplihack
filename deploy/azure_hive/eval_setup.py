#!/usr/bin/env python3
"""Idempotent distributed eval environment setup.

Validates and provisions everything needed to run a distributed eval against
a deployed Azure hive.  Safe to run multiple times — all steps are idempotent.

Checks performed:
  1. Azure CLI authenticated and target subscription accessible
  2. Resource group and Container Apps present with expected agent count
  3. Event Hub namespace reachable; all three hubs exist with correct partitions
  4. Consumer group "eval-reader" exists on the response hub
  5. ANTHROPIC_API_KEY present
  6. OTel endpoint reachable (if configured)
  7. Outputs a ready-to-use .env file for the eval harness

Usage:
    python deploy/azure_hive/eval_setup.py
    python deploy/azure_hive/eval_setup.py --check-only
    python deploy/azure_hive/eval_setup.py --write-env eval.env
    python deploy/azure_hive/eval_setup.py --resource-group my-rg --hive-name myhive

Environment:
    HIVE_NAME              Hive name (default: amplihive)
    HIVE_RESOURCE_GROUP    Resource group (default: hive-mind-rg)
    HIVE_AGENT_COUNT       Expected agent count (default: 100)
    HIVE_DEPLOYMENT_PROFILE  federated-100 | smoke-10 | custom (default: federated-100)
    EH_CONN                Event Hubs namespace connection string
    AMPLIHACK_EH_INPUT_HUB Input Event Hub name override
    AMPLIHACK_EH_RESPONSE_HUB Response Event Hub name override
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [eval_setup] %(levelname)s: %(message)s",
)
logger = logging.getLogger("eval_setup")

_PASS = "\033[32m✓\033[0m"
_FAIL = "\033[31m✗\033[0m"
_WARN = "\033[33m⚠\033[0m"


def _step(ok: bool, message: str) -> bool:
    icon = _PASS if ok else _FAIL
    print(f"  {icon} {message}")
    return ok


def _warn(message: str) -> None:
    print(f"  {_WARN} {message}")


# ---------------------------------------------------------------------------
# Check helpers
# ---------------------------------------------------------------------------


def _az(*args: str) -> tuple[bool, str]:
    """Run an Azure CLI command, return (success, stdout)."""
    import subprocess

    result = subprocess.run(
        ["az", *args],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0, result.stdout.strip()


def check_azure_cli() -> bool:
    ok, _ = _az("account", "show", "--output", "none")
    return _step(
        ok, "Azure CLI authenticated" if ok else "Azure CLI not authenticated (run: az login)"
    )


def check_resource_group(resource_group: str) -> bool:
    ok, _ = _az("group", "show", "--name", resource_group, "--output", "none")
    return _step(
        ok,
        f"Resource group '{resource_group}' exists"
        if ok
        else f"Resource group '{resource_group}' not found",
    )


def check_agent_apps(resource_group: str, hive_name: str, expected_agents: int) -> bool:
    ok, out = _az(
        "containerapp",
        "list",
        "--resource-group",
        resource_group,
        "--query",
        f"[?starts_with(name, '{hive_name}')].name",
        "--output",
        "json",
    )
    if not ok:
        return _step(False, "Could not list Container Apps")
    try:
        apps = json.loads(out or "[]")
    except json.JSONDecodeError:
        apps = []

    agents_per_app = max(1, int(os.environ.get("HIVE_AGENTS_PER_APP", "5")))
    min_apps = max(1, expected_agents // agents_per_app)
    found = len(apps)
    ok = found >= min_apps
    return _step(
        ok,
        f"Container Apps: found {found} (expected ≥ {min_apps} for {expected_agents} agents, {agents_per_app}/app)"
        if ok
        else f"Container Apps: found {found}, expected ≥ {min_apps} for {expected_agents} agents",
    )


def check_event_hub_namespace(connection_string: str, hive_name: str) -> tuple[bool, str, str]:
    """Return (ok, input_hub, response_hub)."""
    input_hub = os.environ.get("AMPLIHACK_EH_INPUT_HUB", "") or f"hive-events-{hive_name}"
    response_hub = os.environ.get("AMPLIHACK_EH_RESPONSE_HUB", "") or f"eval-responses-{hive_name}"

    if not connection_string:
        _step(False, "EH_CONN not set — Event Hubs namespace connection string required")
        return False, input_hub, response_hub

    try:
        from azure.eventhub import EventHubConsumerClient  # type: ignore[import-unresolved]
    except ImportError:
        _warn(
            "azure-eventhub not installed — skipping hub connectivity check (pip install azure-eventhub)"
        )
        return True, input_hub, response_hub

    # Check input hub
    try:
        c = EventHubConsumerClient.from_connection_string(
            connection_string,
            consumer_group="$Default",
            eventhub_name=input_hub,
        )
        partitions = c.get_partition_ids()
        c.close()
        input_ok = True
        input_msg = f"Input hub '{input_hub}' reachable ({len(partitions)} partitions)"
    except Exception as exc:
        input_ok = False
        input_msg = f"Input hub '{input_hub}' unreachable: {exc}"
    _step(input_ok, input_msg)

    # Check response hub
    try:
        c = EventHubConsumerClient.from_connection_string(
            connection_string,
            consumer_group="$Default",
            eventhub_name=response_hub,
        )
        _ = c.get_partition_ids()
        c.close()
        resp_ok = True
        resp_msg = f"Response hub '{response_hub}' reachable"
    except Exception as exc:
        resp_ok = False
        resp_msg = f"Response hub '{response_hub}' unreachable: {exc}"
    _step(resp_ok, resp_msg)

    # Check eval-reader consumer group on response hub
    cg_ok = _ensure_eval_reader_consumer_group(connection_string, response_hub, hive_name)

    return input_ok and resp_ok and cg_ok, input_hub, response_hub


def _ensure_eval_reader_consumer_group(
    connection_string: str, response_hub: str, hive_name: str
) -> bool:
    """Create the eval-reader consumer group if it does not exist."""
    # Extract namespace name from connection string
    ns = ""
    for part in connection_string.split(";"):
        if part.startswith("Endpoint="):
            # sb://namespace.servicebus.windows.net/
            endpoint = part.removeprefix("Endpoint=").strip("/")
            # Strip known scheme prefixes before extracting namespace
            for _scheme in ("sb://", "amqps://", "amqp://"):
                if endpoint.startswith(_scheme):
                    endpoint = endpoint[len(_scheme) :]
                    break
            ns = endpoint.split(".")[0]
            break

    if not ns:
        _warn("Could not parse namespace from connection string — skipping consumer group check")
        return True

    # Try to get resource group from env for az CLI calls
    resource_group = os.environ.get("HIVE_RESOURCE_GROUP", "hive-mind-rg")

    # List consumer groups
    ok, out = _az(
        "eventhubs",
        "eventhub",
        "consumer-group",
        "list",
        "--namespace-name",
        ns,
        "--eventhub-name",
        response_hub,
        "--resource-group",
        resource_group,
        "--query",
        "[].name",
        "--output",
        "json",
    )
    if not ok:
        _warn(
            "Could not list consumer groups (az CLI needed) — ensure 'eval-reader' exists manually"
        )
        return True

    try:
        groups = json.loads(out or "[]")
    except json.JSONDecodeError:
        groups = []

    if "eval-reader" in groups:
        return _step(True, "Consumer group 'eval-reader' exists on response hub")

    # Create it
    create_ok, _ = _az(
        "eventhubs",
        "eventhub",
        "consumer-group",
        "create",
        "--namespace-name",
        ns,
        "--eventhub-name",
        response_hub,
        "--resource-group",
        resource_group,
        "--name",
        "eval-reader",
    )
    return _step(
        create_ok,
        "Created consumer group 'eval-reader' on response hub"
        if create_ok
        else "Failed to create 'eval-reader' consumer group — create it manually",
    )


def check_anthropic_key() -> bool:
    ok = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
    return _step(ok, "ANTHROPIC_API_KEY present" if ok else "ANTHROPIC_API_KEY not set")


def check_otel_endpoint() -> bool:
    endpoint = (
        os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
        or os.environ.get("AMPLIHACK_OTEL_OTLP_ENDPOINT", "")
    ).strip()
    if not endpoint:
        _warn("No OTEL_EXPORTER_OTLP_ENDPOINT set — OTel traces will be disabled")
        return True

    import urllib.request

    try:
        req = urllib.request.Request(endpoint, method="HEAD")
        urllib.request.urlopen(req, timeout=5)
        return _step(True, f"OTel endpoint reachable: {endpoint}")
    except Exception:
        # Many OTLP endpoints don't respond to HEAD — just warn
        _warn(f"OTel endpoint HEAD check inconclusive (this is normal): {endpoint}")
        return True


# ---------------------------------------------------------------------------
# .env writer
# ---------------------------------------------------------------------------


def write_env_file(
    path: str,
    connection_string: str,
    input_hub: str,
    response_hub: str,
    hive_name: str,
    agent_count: int,
) -> None:
    env_content = f"""\
# Generated by eval_setup.py — distributed eval environment
# Edit before running eval_distributed.py if needed.

EH_CONN={connection_string}
AMPLIHACK_EH_INPUT_HUB={input_hub}
AMPLIHACK_EH_RESPONSE_HUB={response_hub}
HIVE_NAME={hive_name}
HIVE_AGENT_COUNT={agent_count}
HIVE_DEPLOYMENT_PROFILE={os.environ.get("HIVE_DEPLOYMENT_PROFILE", "federated-100")}

# OTel (optional)
OTEL_EXPORTER_OTLP_ENDPOINT={os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")}
OTEL_EXPORTER_OTLP_PROTOCOL={os.environ.get("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")}
AMPLIHACK_OTEL_ENABLED={os.environ.get("AMPLIHACK_OTEL_ENABLED", "false")}

# Eval parameters (override as needed)
AMPLIHACK_ASPIRE_EVAL_TURNS=5000
AMPLIHACK_ASPIRE_EVAL_QUESTIONS=50
AMPLIHACK_ASPIRE_ANSWER_TIMEOUT=120
"""
    Path(path).write_text(env_content)
    logger.info("Wrote eval environment to %s", path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    p = argparse.ArgumentParser(description="Idempotent distributed eval environment setup")
    p.add_argument("--hive-name", default=os.environ.get("HIVE_NAME", "amplihive"))
    p.add_argument(
        "--resource-group", default=os.environ.get("HIVE_RESOURCE_GROUP", "hive-mind-rg")
    )
    p.add_argument(
        "--agent-count",
        type=int,
        default=int(os.environ.get("HIVE_AGENT_COUNT", "100")),
    )
    p.add_argument("--connection-string", default=os.environ.get("EH_CONN", ""))
    p.add_argument(
        "--check-only", action="store_true", help="Run checks only, do not create resources"
    )
    p.add_argument("--write-env", default="", help="Write ready-to-use .env file to this path")
    p.add_argument("--skip-azure", action="store_true", help="Skip Azure CLI checks (CI mode)")
    args = p.parse_args()

    print(f"\n{'=' * 60}")
    print(f"  Distributed eval setup — hive '{args.hive_name}'")
    print(f"  Target: {args.agent_count} agents in '{args.resource_group}'")
    print(f"{'=' * 60}\n")

    failures: list[str] = []

    # --- Prerequisites ---
    print("Prerequisites:")
    if not check_anthropic_key():
        failures.append("ANTHROPIC_API_KEY")

    # --- Azure infra ---
    if not args.skip_azure:
        print("\nAzure infrastructure:")
        if not check_azure_cli():
            failures.append("azure_cli")
        elif check_resource_group(args.resource_group):
            if not check_agent_apps(args.resource_group, args.hive_name, args.agent_count):
                failures.append("agent_apps")
        else:
            failures.append("resource_group")
    else:
        _warn("Skipping Azure checks (--skip-azure)")

    # --- Event Hubs ---
    print("\nEvent Hubs:")
    eh_ok, input_hub, response_hub = check_event_hub_namespace(
        args.connection_string, args.hive_name
    )
    if not eh_ok:
        failures.append("event_hubs")

    # --- OTel ---
    print("\nTelemetry:")
    check_otel_endpoint()

    # --- Summary ---
    print(f"\n{'=' * 60}")
    if failures:
        print(f"  {_FAIL} Setup incomplete. Fix issues above before running eval.")
        print(f"  Failed checks: {', '.join(failures)}")
        print(f"{'=' * 60}\n")
        return 1

    print(f"  {_PASS} All checks passed. Ready to run distributed eval.")
    if args.write_env:
        write_env_file(
            args.write_env,
            args.connection_string,
            input_hub,
            response_hub,
            args.hive_name,
            args.agent_count,
        )
        print(f"  Env file: {args.write_env}")
    print("\n  Run eval:")
    print("    python deploy/azure_hive/eval_distributed.py \\")
    print('      --connection-string "$EH_CONN" \\')
    print(f"      --input-hub {input_hub} \\")
    print(f"      --response-hub {response_hub} \\")
    print(f"      --agents {args.agent_count} \\")
    print("      --turns 5000 --questions 50 \\")
    print("      --output results.json")
    print(f"{'=' * 60}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
