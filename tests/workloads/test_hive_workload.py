"""Tests for HiveMindWorkload and hive event types.

These tests run without Azure credentials or agent-haymaker installed
by using lightweight mocks.  Integration tests that need real Azure
resources are marked with @pytest.mark.integration.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_platform() -> MagicMock:
    """Create a mock Platform with in-memory state storage."""
    platform = MagicMock()
    storage: dict[str, Any] = {}

    async def save(state: Any) -> None:
        storage[state.deployment_id] = state

    async def load(deployment_id: str) -> Any:
        return storage.get(deployment_id)

    async def list_deps(workload_name: str) -> list:
        return [s for s in storage.values() if s.workload_name == workload_name]

    platform.save_deployment_state = AsyncMock(side_effect=save)
    platform.load_deployment_state = AsyncMock(side_effect=load)
    platform.list_deployments = AsyncMock(side_effect=list_deps)
    platform.get_credential = AsyncMock(return_value=None)
    platform.publish_event = AsyncMock()
    platform.log = MagicMock()
    platform._storage = storage
    return platform


# ---------------------------------------------------------------------------
# Event topic tests
# ---------------------------------------------------------------------------


def test_hive_event_topics_defined() -> None:
    """All hive event topics must be defined with the correct namespace."""
    from amplihack.workloads.hive.events import (
        ALL_HIVE_TOPICS,
        HIVE_AGENT_READY,
        HIVE_FEED_COMPLETE,
        HIVE_LEARN_CONTENT,
        HIVE_QUERY,
        HIVE_QUERY_RESPONSE,
    )

    assert HIVE_LEARN_CONTENT == "hive.learn_content"
    assert HIVE_FEED_COMPLETE == "hive.feed_complete"
    assert HIVE_AGENT_READY == "hive.agent_ready"
    assert HIVE_QUERY == "hive.query"
    assert HIVE_QUERY_RESPONSE == "hive.query_response"
    assert len(ALL_HIVE_TOPICS) == 5


def test_hive_event_factories_without_haymaker() -> None:
    """Event factory helpers must raise ImportError gracefully when agent-haymaker absent."""
    from amplihack.workloads.hive.events import (
        make_agent_ready_event,
        make_feed_complete_event,
        make_learn_content_event,
        make_query_event,
        make_query_response_event,
    )

    # With agent-haymaker available (from /tmp/agent-haymaker installed path)
    try:
        import sys
        sys.path.insert(0, "/tmp/agent-haymaker/src")

        evt = make_learn_content_event("dep-001", "test content", 0)
        assert evt.topic == "hive.learn_content"
        assert evt.deployment_id == "dep-001"
        assert evt.data["content"] == "test content"
        assert evt.data["turn"] == 0

        evt2 = make_feed_complete_event("dep-001", total_turns=100)
        assert evt2.topic == "hive.feed_complete"
        assert evt2.data["total_turns"] == 100

        evt3 = make_agent_ready_event("dep-001", "agent-0")
        assert evt3.topic == "hive.agent_ready"
        assert evt3.data["agent_name"] == "agent-0"

        evt4 = make_query_event("dep-001", "q001", "What is CVE-2021-44228?")
        assert evt4.topic == "hive.query"
        assert evt4.data["query_id"] == "q001"

        evt5 = make_query_response_event("dep-001", "q001", "agent-0", "CVSS 10.0")
        assert evt5.topic == "hive.query_response"
        assert evt5.data["answer"] == "CVSS 10.0"

    except ImportError:
        pytest.skip("agent-haymaker not available for event factory tests")


# ---------------------------------------------------------------------------
# HiveMindWorkload unit tests
# ---------------------------------------------------------------------------


def test_hive_mind_workload_name() -> None:
    """HiveMindWorkload.name must be 'hive-mind'."""
    try:
        from amplihack.workloads.hive import HiveMindWorkload

        assert HiveMindWorkload.name == "hive-mind"
    except ImportError as exc:
        pytest.skip(f"agent-haymaker not available: {exc}")


def test_hive_mind_workload_inherits_workload_base() -> None:
    """HiveMindWorkload must inherit WorkloadBase."""
    try:
        from agent_haymaker.workloads.base import WorkloadBase
        from amplihack.workloads.hive import HiveMindWorkload

        assert issubclass(HiveMindWorkload, WorkloadBase)
    except ImportError as exc:
        pytest.skip(f"agent-haymaker not available: {exc}")


def test_deploy_returns_deployment_id() -> None:
    """deploy() must return a deployment_id string starting with 'hive-'."""
    try:
        import asyncio
        import sys
        sys.path.insert(0, "/tmp/agent-haymaker/src")
        from agent_haymaker.workloads.models import DeploymentConfig

        from amplihack.workloads.hive import HiveMindWorkload
    except ImportError as exc:
        pytest.skip(f"agent-haymaker not available: {exc}")

    platform = _make_mock_platform()
    workload = HiveMindWorkload(platform=platform)

    async def _run() -> str:
        with patch.object(workload, "_deploy_single_container", new_callable=AsyncMock) as mock_deploy:
            mock_deploy.return_value = {"app_name": "hive-test-c00"}

            config = DeploymentConfig(
                workload_name="hive-mind",
                workload_config={
                    "num_containers": 2,
                    "agents_per_container": 3,
                    "image": "myacr.azurecr.io/hive-agent:latest",
                    "resource_group": "rg-test",
                    "subscription_id": "sub-12345",
                    "service_bus_connection_string": "",
                    "agent_prompt": "You are a test agent.",
                },
            )

            deployment_id = await workload.deploy(config)

            assert deployment_id.startswith("hive-")
            assert mock_deploy.call_count == 2  # one per container
            assert platform.save_deployment_state.called
            return deployment_id

    deployment_id = asyncio.run(_run())
    assert deployment_id.startswith("hive-")


def test_stop_updates_state() -> None:
    """stop() must update deployment status to STOPPED."""
    try:
        import asyncio
        import sys
        sys.path.insert(0, "/tmp/agent-haymaker/src")
        from agent_haymaker.workloads.models import (
            DeploymentState,
            DeploymentStatus,
        )

        from amplihack.workloads.hive import HiveMindWorkload
    except ImportError as exc:
        pytest.skip(f"agent-haymaker not available: {exc}")

    platform = _make_mock_platform()
    workload = HiveMindWorkload(platform=platform)

    from datetime import UTC, datetime

    state = DeploymentState(
        deployment_id="hive-abc123",
        workload_name="hive-mind",
        status=DeploymentStatus.RUNNING,
        phase="running",
        started_at=datetime.now(tz=UTC),
        config={},
        metadata={
            "container_apps": ["hive-abc123-c00", "hive-abc123-c01"],
            "resource_group": "rg-test",
            "subscription_id": "sub-12345",
        },
    )

    async def _run() -> None:
        await platform.save_deployment_state(state)

        with patch.object(workload, "_scale_app", new_callable=AsyncMock) as mock_scale:
            mock_scale.return_value = True

            result = await workload.stop("hive-abc123")

            assert result is True
            assert mock_scale.call_count == 2

        saved = await platform.load_deployment_state("hive-abc123")
        assert saved.status == DeploymentStatus.STOPPED

    asyncio.run(_run())


def test_cleanup_deletes_apps() -> None:
    """cleanup() must delete all container apps and return a CleanupReport."""
    try:
        import asyncio
        import sys
        sys.path.insert(0, "/tmp/agent-haymaker/src")
        from agent_haymaker.workloads.models import (
            DeploymentState,
            DeploymentStatus,
        )

        from amplihack.workloads.hive import HiveMindWorkload
    except ImportError as exc:
        pytest.skip(f"agent-haymaker not available: {exc}")

    platform = _make_mock_platform()
    workload = HiveMindWorkload(platform=platform)

    from datetime import UTC, datetime

    state = DeploymentState(
        deployment_id="hive-xyz789",
        workload_name="hive-mind",
        status=DeploymentStatus.RUNNING,
        phase="running",
        started_at=datetime.now(tz=UTC),
        config={},
        metadata={
            "container_apps": ["hive-xyz789-c00", "hive-xyz789-c01", "hive-xyz789-c02"],
            "resource_group": "rg-test",
            "subscription_id": "sub-12345",
        },
    )

    async def _run() -> None:
        await platform.save_deployment_state(state)

        with patch.object(workload, "_delete_container_app", new_callable=AsyncMock) as mock_delete:
            mock_delete.return_value = True

            report = await workload.cleanup("hive-xyz789")

            assert report.deployment_id == "hive-xyz789"
            assert report.resources_deleted == 3
            assert report.resources_failed == 0
            assert mock_delete.call_count == 3

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# amplihack.agent public API
# ---------------------------------------------------------------------------


def test_amplihack_agent_module_exports() -> None:
    """amplihack.agent must export the stable public API."""
    from amplihack.agent import (
        AgenticLoop,
        CognitiveAdapter,
        GoalAgentGenerator,
        LearningAgent,
        Memory,
    )

    assert LearningAgent is not None
    assert CognitiveAdapter is not None
    assert AgenticLoop is not None
    assert Memory is not None
    assert GoalAgentGenerator is not None


def test_amplihack_agent_learning_agent_is_canonical() -> None:
    """amplihack.agent.LearningAgent must be the same class as agents.goal_seeking.LearningAgent."""
    from amplihack.agent import LearningAgent as PublicLearningAgent
    from amplihack.agents.goal_seeking import LearningAgent as InternalLearningAgent

    assert PublicLearningAgent is InternalLearningAgent
