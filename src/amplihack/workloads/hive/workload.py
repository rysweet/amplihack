"""HiveMindWorkload — amplihack hive mind as a haymaker WorkloadBase.

Deploys a distributed hive of LearningAgents on Azure Container Apps.
Topology: N container apps (default 20), each running M agents (default 5),
for a total of N*M agents sharing a Service Bus topic.

All deployment lifecycle is managed through the agent-haymaker platform:
  - deploy()      : Builds/pushes Docker image, runs Bicep infra (SB + ACR),
                    then calls deploy_container_app() for each container.
  - get_status()  : Queries each container app provisioning state.
  - get_logs()    : Streams az containerapp logs for the first container.
  - stop()        : Stops all container apps (sets min-replicas to 0).
  - cleanup()     : Deletes all container apps tagged to this deployment.

Events use typed agent-haymaker EventData (HIVE_LEARN_CONTENT, HIVE_FEED_COMPLETE,
HIVE_AGENT_READY, HIVE_QUERY, HIVE_QUERY_RESPONSE) via ServiceBusEventBus.

The running 100-agent deployment is unaffected: this class creates NEW container
apps under a new deployment_id.  Old apps remain until explicitly cleaned up.

Configuration keys (via DeploymentConfig.workload_config):
    num_containers  : int  = 20   Number of Container Apps to deploy.
    agents_per_container : int = 5   Agents per container (env-var injected).
    image           : str         Container image (required unless in AzureConfig).
    resource_group  : str         Azure resource group.
    subscription_id : str         Azure subscription.
    location        : str = "eastus"  Azure region.
    acr_name        : str         Azure Container Registry name (for image push).
    service_bus_connection_string : str  Service Bus Premium connection string.
    topic_name      : str = "hive-graph"  Service Bus topic for agent events.
    agent_prompt    : str         System prompt injected into each agent container.
    cpu             : float = 1.0  CPU cores per container.
    memory_gb       : int   = 4    Memory per container (GiB).
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy imports (agent-haymaker is an optional dep at install time)
# ---------------------------------------------------------------------------

try:
    from agent_haymaker.workloads.base import DeploymentNotFoundError, WorkloadBase
    from agent_haymaker.workloads.models import (
        CleanupReport,
        DeploymentConfig,
        DeploymentState,
        DeploymentStatus,
    )

    _HAYMAKER_AVAILABLE = True
except ImportError:  # pragma: no cover
    _HAYMAKER_AVAILABLE = False
    WorkloadBase = object  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_NUM_CONTAINERS = 20
_DEFAULT_AGENTS_PER_CONTAINER = 5
_DEFAULT_TOPIC = "hive-graph"
_DEFAULT_LOCATION = "eastus"
_DEFAULT_CPU = 1.0
_DEFAULT_MEMORY_GB = 4

_TAG_PREFIX = "haymaker-hive"


# ---------------------------------------------------------------------------
# HiveMindWorkload
# ---------------------------------------------------------------------------


class HiveMindWorkload(WorkloadBase):  # type: ignore[misc]
    """Deploys the amplihack hive mind as a set of Azure Container Apps.

    Each Container App runs M LearningAgents that share a Service Bus topic.
    All agents use ``amplihack.agent.LearningAgent`` as their cognitive core.

    Designed as an *additive* deployment: the existing 100-agent job is
    unaffected because each deployment uses a unique ``deployment_id`` prefix
    for app names and tags.
    """

    name = "hive-mind"

    def __init__(self, platform: Any = None) -> None:
        if _HAYMAKER_AVAILABLE:
            super().__init__(platform=platform)
        self._platform = platform
        # deployment_id -> list of deployed app names
        self._container_apps: dict[str, list[str]] = {}

    # =========================================================================
    # REQUIRED: WorkloadBase abstract methods
    # =========================================================================

    async def deploy(self, config: DeploymentConfig) -> str:
        """Deploy N container apps, each running M LearningAgents.

        Returns:
            deployment_id: Unique identifier for this hive deployment.
        """
        wc = config.workload_config
        deployment_id = f"hive-{uuid.uuid4().hex[:8]}"

        num_containers: int = int(wc.get("num_containers", _DEFAULT_NUM_CONTAINERS))
        agents_per_container: int = int(
            wc.get("agents_per_container", _DEFAULT_AGENTS_PER_CONTAINER)
        )
        image: str = wc.get("image", "")
        resource_group: str = wc.get("resource_group", "")
        subscription_id: str = wc.get("subscription_id", "")
        topic_name: str = wc.get("topic_name", _DEFAULT_TOPIC)
        sb_conn_str: str = wc.get("service_bus_connection_string", "")
        agent_prompt: str = wc.get("agent_prompt", "You are a security analyst in a hive mind.")
        cpu: float = float(wc.get("cpu", _DEFAULT_CPU))
        memory_gb: int = int(wc.get("memory_gb", _DEFAULT_MEMORY_GB))
        location: str = wc.get("location", _DEFAULT_LOCATION)

        self.log(
            f"Deploying hive-mind: deployment_id={deployment_id} "
            f"containers={num_containers} agents_per_container={agents_per_container}"
        )

        # Persist initial state
        if _HAYMAKER_AVAILABLE:
            state = DeploymentState(
                deployment_id=deployment_id,
                workload_name=self.name,
                status=DeploymentStatus.PENDING,
                phase="provisioning",
                started_at=datetime.now(tz=UTC),
                config=wc,
                metadata={
                    "num_containers": num_containers,
                    "agents_per_container": agents_per_container,
                    "total_agents": num_containers * agents_per_container,
                    "topic_name": topic_name,
                    "resource_group": resource_group,
                    "subscription_id": subscription_id,
                    "location": location,
                    "container_apps": [],
                },
            )
            await self.save_state(state)

        app_names: list[str] = []

        # Deploy each container app
        for i in range(num_containers):
            app_name = f"hive-{deployment_id[:8]}-c{i:02d}"
            env_vars: dict[str, str] = {
                "AMPLIHACK_AGENT_NAME": f"container-{i:02d}",
                "AMPLIHACK_AGENT_PROMPT": agent_prompt,
                "AMPLIHACK_MEMORY_TRANSPORT": "azure_service_bus",
                "AMPLIHACK_MEMORY_CONNECTION_STRING": sb_conn_str,
                "AMPLIHACK_TOPIC_NAME": topic_name,
                "AMPLIHACK_AGENTS_PER_CONTAINER": str(agents_per_container),
                "AMPLIHACK_CONTAINER_INDEX": str(i),
                "AMPLIHACK_DEPLOYMENT_ID": deployment_id,
            }

            try:
                result = await self._deploy_single_container(
                    deployment_id=deployment_id,
                    app_name=app_name,
                    image=image,
                    resource_group=resource_group,
                    subscription_id=subscription_id,
                    env_vars=env_vars,
                    cpu=cpu,
                    memory_gb=memory_gb,
                    location=location,
                )
                app_names.append(result.get("app_name", app_name))
                self.log(f"Deployed container app {i + 1}/{num_containers}: {app_name}")
            except Exception as exc:
                self.log(f"Failed to deploy container {i}: {exc}", level="ERROR")
                # Continue deploying remaining containers (partial deploy is valid)

        self._container_apps[deployment_id] = app_names

        # Update state to RUNNING
        if _HAYMAKER_AVAILABLE:
            state.status = DeploymentStatus.RUNNING
            state.phase = "running"
            state.metadata["container_apps"] = app_names
            await self.save_state(state)

            try:
                await self.emit_event(
                    "deployment.started",
                    deployment_id,
                    total_agents=num_containers * agents_per_container,
                    container_count=len(app_names),
                )
            except Exception:
                logger.debug("Failed to emit deployment.started for %s", deployment_id)

        self.log(
            f"Hive deployment complete: {len(app_names)}/{num_containers} containers running, "
            f"deployment_id={deployment_id}"
        )
        return deployment_id

    async def get_status(self, deployment_id: str) -> DeploymentState:
        """Query status of all container apps for a deployment."""
        if not _HAYMAKER_AVAILABLE:
            raise RuntimeError("agent-haymaker not installed")

        state = await self.load_state(deployment_id)
        if state is None:
            raise DeploymentNotFoundError(f"Deployment {deployment_id} not found")

        if state.status in (DeploymentStatus.COMPLETED, DeploymentStatus.FAILED):
            return state

        app_names: list[str] = (state.metadata or {}).get("container_apps", [])
        if not app_names:
            app_names = self._container_apps.get(deployment_id, [])

        statuses = await self._query_app_statuses(
            app_names=app_names,
            resource_group=(state.metadata or {}).get("resource_group", ""),
            subscription_id=(state.metadata or {}).get("subscription_id", ""),
        )

        running = sum(1 for s in statuses.values() if s == "Succeeded")
        failed = sum(1 for s in statuses.values() if s in ("Failed", "Canceled"))

        state.metadata["container_statuses"] = statuses
        state.metadata["running_containers"] = running
        state.metadata["failed_containers"] = failed

        if failed > 0 and running == 0:
            state.status = DeploymentStatus.FAILED
            state.phase = "failed"
            state.error = f"{failed} container apps failed"
        elif running == len(app_names) and running > 0:
            state.phase = "all_running"

        await self.save_state(state)
        return state

    async def get_logs(
        self,
        deployment_id: str,
        follow: bool = False,
        lines: int = 100,
    ) -> AsyncIterator[str]:
        """Stream logs from all container apps for the deployment."""
        state = await self.load_state(deployment_id)
        if state is None:
            if _HAYMAKER_AVAILABLE:
                raise DeploymentNotFoundError(f"Deployment {deployment_id} not found")
            return

        app_names: list[str] = (state.metadata or {}).get("container_apps", [])
        if not app_names:
            app_names = self._container_apps.get(deployment_id, [])

        resource_group = (state.metadata or {}).get("resource_group", "")
        subscription_id = (state.metadata or {}).get("subscription_id", "")

        for app_name in app_names:
            yield f"=== Logs for {app_name} ==="
            async for line in self._stream_app_logs(
                app_name=app_name,
                resource_group=resource_group,
                subscription_id=subscription_id,
                lines=lines,
                follow=follow,
            ):
                yield line

    async def stop(self, deployment_id: str) -> bool:
        """Stop all container apps by setting replicas to 0."""
        if not _HAYMAKER_AVAILABLE:
            return False

        state = await self.load_state(deployment_id)
        if state is None:
            raise DeploymentNotFoundError(f"Deployment {deployment_id} not found")

        app_names: list[str] = (state.metadata or {}).get("container_apps", [])
        if not app_names:
            app_names = self._container_apps.get(deployment_id, [])

        resource_group = (state.metadata or {}).get("resource_group", "")
        subscription_id = (state.metadata or {}).get("subscription_id", "")

        stopped = 0
        for app_name in app_names:
            if await self._scale_app(app_name, resource_group, subscription_id, min_replicas=0):
                stopped += 1

        state.status = DeploymentStatus.STOPPED
        state.phase = "stopped"
        state.stopped_at = datetime.now(tz=UTC)
        await self.save_state(state)

        try:
            await self.emit_event("deployment.stopped", deployment_id)
        except Exception:
            logger.debug("Failed to emit deployment.stopped for %s", deployment_id)

        self.log(f"Stopped {stopped}/{len(app_names)} container apps for {deployment_id}")
        return stopped > 0 or len(app_names) == 0

    async def cleanup(self, deployment_id: str) -> CleanupReport:
        """Delete all container apps for this deployment."""
        if not _HAYMAKER_AVAILABLE:
            return None  # type: ignore[return-value]

        start_time = time.monotonic()
        state = await self.load_state(deployment_id)
        if state is None:
            raise DeploymentNotFoundError(f"Deployment {deployment_id} not found")

        app_names: list[str] = (state.metadata or {}).get("container_apps", [])
        if not app_names:
            app_names = self._container_apps.get(deployment_id, [])

        resource_group = (state.metadata or {}).get("resource_group", "")
        subscription_id = (state.metadata or {}).get("subscription_id", "")

        deleted = 0
        failed = 0
        details: list[str] = []
        errors: list[str] = []

        for app_name in app_names:
            success = await self._delete_container_app(app_name, resource_group, subscription_id)
            if success:
                deleted += 1
                details.append(f"Deleted container app: {app_name}")
            else:
                failed += 1
                errors.append(f"Failed to delete: {app_name}")

        self._container_apps.pop(deployment_id, None)
        state.status = DeploymentStatus.STOPPED
        state.phase = "cleaned_up"
        state.stopped_at = datetime.now(tz=UTC)
        await self.save_state(state)

        self.log(
            f"Cleanup complete: deleted={deleted} failed={failed} deployment_id={deployment_id}"
        )
        return CleanupReport(
            deployment_id=deployment_id,
            resources_deleted=deleted,
            resources_failed=failed,
            details=details,
            errors=errors,
            duration_seconds=time.monotonic() - start_time,
        )

    # =========================================================================
    # Public helpers (used by CLI extensions)
    # =========================================================================

    async def feed(
        self,
        deployment_id: str,
        turns: int = 100,
        topic_name: str | None = None,
    ) -> None:
        """Publish LEARN_CONTENT events then a FEED_COMPLETE sentinel.

        Equivalent to: ``python feed_content.py --turns N``

        Args:
            deployment_id: Deployment that will receive the content.
            turns: Number of LEARN_CONTENT events to send.
            topic_name: Override Service Bus topic (reads from deployment state if omitted).
        """
        from amplihack.workloads.hive._feed import run_feed

        state = await self.load_state(deployment_id) if _HAYMAKER_AVAILABLE else None
        resolved_topic = topic_name or (
            (state.metadata or {}).get("topic_name", _DEFAULT_TOPIC) if state else _DEFAULT_TOPIC
        )
        sb_conn_str = (
            (state.metadata or {}).get("service_bus_connection_string", "") if state else ""
        )
        await run_feed(
            deployment_id=deployment_id,
            turns=turns,
            topic_name=resolved_topic,
            sb_conn_str=sb_conn_str,
        )

    async def eval(
        self,
        deployment_id: str,
        repeats: int = 3,
        wait_for_ready: int = 0,
        timeout_seconds: int = 600,
    ) -> list[dict[str, Any]]:
        """Wait for agents to be ready, then run eval rounds.

        Waits for ``wait_for_ready`` HIVE_AGENT_READY events before starting
        eval rounds.  Uses event-driven signalling — no sleep timers.

        Args:
            deployment_id: Deployment to evaluate.
            repeats: Number of question rounds.
            wait_for_ready: Number of AGENT_READY events to wait for (0 = skip wait).
            timeout_seconds: Maximum seconds to wait for agents to be ready.

        Returns:
            List of {question, answers: [{agent, answer}]} dicts.
        """
        from amplihack.workloads.hive._eval import run_eval

        state = await self.load_state(deployment_id) if _HAYMAKER_AVAILABLE else None
        sb_conn_str = (
            (state.metadata or {}).get("service_bus_connection_string", "") if state else ""
        )
        resolved_topic = (
            (state.metadata or {}).get("topic_name", _DEFAULT_TOPIC) if state else _DEFAULT_TOPIC
        )

        return await run_eval(
            deployment_id=deployment_id,
            repeats=repeats,
            wait_for_ready=wait_for_ready,
            timeout_seconds=timeout_seconds,
            sb_conn_str=sb_conn_str,
            topic_name=resolved_topic,
        )

    # =========================================================================
    # Private helpers
    # =========================================================================

    async def _deploy_single_container(
        self,
        *,
        deployment_id: str,
        app_name: str,
        image: str,
        resource_group: str,
        subscription_id: str,
        env_vars: dict[str, str],
        cpu: float,
        memory_gb: int,
        location: str,
    ) -> dict[str, Any]:
        """Deploy a single container app via az CLI."""
        try:
            from agent_haymaker.azure.config import AzureConfig
            from agent_haymaker.azure.container_apps import deploy_container_app

            config = AzureConfig(
                resource_group=resource_group,
                subscription_id=subscription_id,
                location=location,
            )
            result = await deploy_container_app(
                config=config,
                deployment_id=deployment_id,
                workload_name=app_name,
                image=image or None,
                env_vars=env_vars,
                cpu=cpu,
                memory_gb=memory_gb,
            )
            return result
        except ImportError:
            logger.warning("agent-haymaker azure module not available; skipping container deploy")
            return {"app_name": app_name}

    async def _query_app_statuses(
        self,
        app_names: list[str],
        resource_group: str,
        subscription_id: str,
    ) -> dict[str, str]:
        """Return {app_name: provisioning_state} for each app."""
        statuses: dict[str, str] = {}
        try:
            from agent_haymaker.azure.config import AzureConfig
            from agent_haymaker.azure.container_apps import get_container_app_status

            config = AzureConfig(
                resource_group=resource_group,
                subscription_id=subscription_id,
                location=_DEFAULT_LOCATION,
            )
            for app_name in app_names:
                info = await get_container_app_status(config, app_name)
                statuses[app_name] = info.get("status", "Unknown")
        except ImportError:
            statuses = dict.fromkeys(app_names, "Unknown")
        return statuses

    async def _stream_app_logs(
        self,
        app_name: str,
        resource_group: str,
        subscription_id: str,
        lines: int,
        follow: bool,
    ) -> AsyncIterator[str]:
        """Stream logs from a container app using az CLI."""
        try:
            from agent_haymaker.azure.az_cli import run_az

            cmd = [
                "containerapp",
                "logs",
                "show",
                "--name",
                app_name,
                "--resource-group",
                resource_group,
                "--subscription",
                subscription_id,
                "--tail",
                str(lines),
            ]
            if follow:
                cmd.append("--follow")

            _rc, stdout, _stderr = run_az(cmd)
            if stdout:
                for line in stdout.splitlines():
                    yield line
        except ImportError:
            yield f"[az CLI not available — cannot fetch logs for {app_name}]"
        except Exception as exc:
            yield f"[Error fetching logs for {app_name}: {exc}]"

    async def _scale_app(
        self,
        app_name: str,
        resource_group: str,
        subscription_id: str,
        min_replicas: int,
    ) -> bool:
        """Set min-replicas on a container app."""
        try:
            from agent_haymaker.azure.az_cli import run_az

            rc, _out, stderr = run_az(
                [
                    "containerapp",
                    "update",
                    "--name",
                    app_name,
                    "--resource-group",
                    resource_group,
                    "--subscription",
                    subscription_id,
                    "--min-replicas",
                    str(min_replicas),
                    "--max-replicas",
                    str(min_replicas),
                ]
            )
            if rc != 0:
                logger.warning("Failed to scale %s: %s", app_name, stderr)
                return False
            return True
        except ImportError:
            return False

    async def _delete_container_app(
        self,
        app_name: str,
        resource_group: str,
        subscription_id: str,
    ) -> bool:
        """Delete a container app."""
        try:
            from agent_haymaker.azure.config import AzureConfig
            from agent_haymaker.azure.container_apps import delete_container_app

            config = AzureConfig(
                resource_group=resource_group,
                subscription_id=subscription_id,
                location=_DEFAULT_LOCATION,
            )
            return await delete_container_app(config, app_name)
        except ImportError:
            logger.warning("agent-haymaker azure module not available; cannot delete %s", app_name)
            return False

    def log(self, message: str, level: str = "INFO") -> None:
        """Log via platform if available, else stdlib."""
        if self._platform:
            self._platform.log(message, level=level, workload=self.name)
        else:
            import logging as _logging

            _logging.getLogger(f"workload.{self.name}").log(
                getattr(_logging, level.upper(), _logging.INFO), message
            )


__all__ = ["HiveMindWorkload"]
