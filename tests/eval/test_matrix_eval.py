from pathlib import Path
from unittest.mock import MagicMock, patch


def test_create_agent_uses_runtime_factory_for_mini(tmp_path: Path):
    from amplihack.eval.matrix_eval import AgentConfig, _create_agent

    with patch(
        "amplihack.agents.goal_seeking.runtime_factory.create_goal_agent_runtime",
        return_value=MagicMock(),
    ) as mock_create_runtime:
        _create_agent(AgentConfig(name="mini", sdk="mini"), "claude-opus-4-6", tmp_path)

    mock_create_runtime.assert_called_once_with(
        agent_name="matrix_mini",
        sdk="mini",
        instructions="You are a learning agent. Learn facts and answer questions accurately.",
        model="claude-opus-4-6",
        storage_path=tmp_path,
        use_hierarchical=True,
    )


def test_create_agent_uses_runtime_factory_for_copilot(tmp_path: Path):
    from amplihack.eval.matrix_eval import AgentConfig, _create_agent

    with patch(
        "amplihack.agents.goal_seeking.runtime_factory.create_goal_agent_runtime",
        return_value=MagicMock(),
    ) as mock_create_runtime:
        _create_agent(AgentConfig(name="copilot", sdk="copilot"), "gpt-5", tmp_path)

    mock_create_runtime.assert_called_once_with(
        agent_name="matrix_copilot",
        sdk="copilot",
        instructions="You are a learning agent. Learn facts and answer questions accurately.",
        model="gpt-5",
        storage_path=tmp_path,
        use_hierarchical=True,
    )


def test_create_agent_keeps_multi_agent_special_case(tmp_path: Path):
    from amplihack.eval.matrix_eval import AgentConfig, _create_agent

    with patch(
        "amplihack.agents.goal_seeking.sub_agents.multi_agent.MultiAgentLearningAgent",
        return_value=MagicMock(),
    ) as mock_multi:
        _create_agent(
            AgentConfig(
                name="multiagent-copilot",
                sdk="copilot",
                multi_agent=True,
                enable_spawning=True,
            ),
            "gpt-5",
            tmp_path,
        )

    mock_multi.assert_called_once_with(
        agent_name="matrix_multiagent-copilot",
        model="gpt-5",
        storage_path=tmp_path,
        use_hierarchical=True,
        enable_spawning=True,
    )
