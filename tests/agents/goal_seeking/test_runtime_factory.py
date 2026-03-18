from pathlib import Path
from unittest.mock import MagicMock, patch


def test_create_goal_agent_runtime_wraps_mini_with_bound_answer_mode(tmp_path: Path):
    mock_learning_agent = MagicMock()
    runtime_backend = MagicMock()
    runtime_backend._learning_agent = mock_learning_agent

    with patch(
        "amplihack.agents.goal_seeking.runtime_factory.OODAGoalSeekingAgent",
        return_value=runtime_backend,
        create=True,
    ) as mock_goal_agent:
        from amplihack.agents.goal_seeking.runtime_factory import create_goal_agent_runtime

        runtime = create_goal_agent_runtime(
            agent_name="mini-agent",
            sdk="mini",
            storage_path=tmp_path,
            answer_mode="agentic",
        )

    mock_goal_agent.assert_called_once()
    assert runtime._agent is mock_learning_agent
    runtime_backend.answer_question.return_value = "Agentic answer"
    assert runtime.answer_question("What happened?") == "Agentic answer"
    runtime_backend.answer_question.assert_called_once_with("What happened?", answer_mode="agentic")


def test_create_goal_agent_runtime_can_return_raw_goal_runtime(tmp_path: Path):
    runtime_backend = MagicMock()

    with patch(
        "amplihack.agents.goal_seeking.runtime_factory.OODAGoalSeekingAgent",
        return_value=runtime_backend,
        create=True,
    ):
        from amplihack.agents.goal_seeking.runtime_factory import create_goal_agent_runtime

        runtime = create_goal_agent_runtime(
            agent_name="azure-agent",
            sdk="mini",
            storage_path=tmp_path,
            bind_answer_mode=False,
        )

    assert runtime is runtime_backend


def test_create_goal_agent_runtime_uses_sdk_factory_for_non_mini(tmp_path: Path):
    sdk_agent = MagicMock()

    with patch(
        "amplihack.agents.goal_seeking.sdk_adapters.factory.create_agent",
        return_value=sdk_agent,
    ) as mock_create_agent:
        from amplihack.agents.goal_seeking.runtime_factory import create_goal_agent_runtime

        runtime = create_goal_agent_runtime(
            agent_name="copilot-agent",
            sdk="copilot",
            model="gpt-5",
            storage_path=tmp_path,
            bind_answer_mode=False,
        )

    assert runtime is sdk_agent
    mock_create_agent.assert_called_once_with(
        name="copilot-agent",
        sdk="copilot",
        model="gpt-5",
        storage_path=tmp_path,
        enable_memory=True,
        enable_eval=False,
    )
