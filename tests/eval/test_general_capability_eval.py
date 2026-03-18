from pathlib import Path
from unittest.mock import MagicMock, patch


def test_create_agent_uses_runtime_factory_for_mini(tmp_path: Path):
    from amplihack.eval.general_capability_eval import GeneralCapabilityEval

    with patch(
        "amplihack.agents.goal_seeking.runtime_factory.create_goal_agent_runtime",
        return_value=MagicMock(),
    ) as mock_create_runtime:
        evaluator = GeneralCapabilityEval(
            agent_name="mini-eval",
            sdk="mini",
            model="claude-opus-4-6",
            storage_path=tmp_path,
        )
        evaluator._create_agent()

    mock_create_runtime.assert_called_once_with(
        agent_name="mini-eval",
        sdk="mini",
        use_hierarchical=True,
        storage_path=tmp_path,
        model="claude-opus-4-6",
        bind_answer_mode=False,
    )


def test_create_agent_uses_runtime_factory_for_copilot(tmp_path: Path):
    from amplihack.eval.general_capability_eval import GeneralCapabilityEval

    with patch(
        "amplihack.agents.goal_seeking.runtime_factory.create_goal_agent_runtime",
        return_value=MagicMock(),
    ) as mock_create_runtime:
        evaluator = GeneralCapabilityEval(
            agent_name="copilot-eval",
            sdk="copilot",
            storage_path=tmp_path,
        )
        evaluator._create_agent()

    mock_create_runtime.assert_called_once_with(
        agent_name="copilot-eval",
        sdk="copilot",
        use_hierarchical=True,
        storage_path=tmp_path,
        bind_answer_mode=False,
    )
