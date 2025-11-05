"""Smoke tests for orchestration infrastructure.

These tests verify the orchestration modules can be imported and have correct structure.
Full integration tests require spawning Claude subprocesses and are better done manually.
"""

import sys
from pathlib import Path

# Add orchestration to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude/tools/amplihack"))


def test_claude_process_imports():
    """Verify ClaudeProcess and ProcessResult can be imported."""
    from orchestration.claude_process import ClaudeProcess, ProcessResult

    assert ClaudeProcess is not None
    assert ProcessResult is not None


def test_execution_helpers_import():
    """Verify execution helper functions can be imported."""
    from orchestration.execution import (
        run_batched,
        run_parallel,
        run_sequential,
        run_with_fallback,
    )

    assert run_parallel is not None
    assert run_sequential is not None
    assert run_with_fallback is not None
    assert run_batched is not None


def test_session_imports():
    """Verify OrchestratorSession can be imported."""
    from orchestration.session import OrchestratorSession

    assert OrchestratorSession is not None


def test_pattern_orchestrators_import():
    """Verify pattern orchestrators can be imported."""
    from orchestration.patterns.cascade import run_cascade
    from orchestration.patterns.debate import run_debate
    from orchestration.patterns.n_version import run_n_version

    assert run_n_version is not None
    assert run_debate is not None
    assert run_cascade is not None


def test_process_result_structure():
    """Verify ProcessResult has expected fields."""
    from orchestration.claude_process import ProcessResult

    result = ProcessResult(exit_code=0, output="test", stderr="", duration=1.0, process_id="test")

    assert result.exit_code == 0
    assert result.output == "test"
    assert result.stderr == ""
    assert result.duration == 1.0
    assert result.process_id == "test"


def test_session_creation():
    """Verify OrchestratorSession can be created."""
    from orchestration.session import OrchestratorSession

    session = OrchestratorSession(pattern_name="test", working_dir=Path.cwd())

    assert session.pattern_name == "test"
    assert session.working_dir == Path.cwd()
    assert session.session_id.startswith("test_")
    assert session.log_dir.exists()


def test_claude_process_signature():
    """Verify ClaudeProcess constructor signature."""
    from orchestration.claude_process import ClaudeProcess

    # Should not raise on valid args
    process = ClaudeProcess(
        prompt="test prompt",
        process_id="test_process",
        working_dir=Path.cwd(),
        log_dir=Path.cwd() / ".claude/runtime/logs",
        model=None,
        stream_output=True,
        timeout=None,
    )

    assert process.prompt == "test prompt"
    assert process.process_id == "test_process"


def test_n_version_signature():
    """Verify run_n_version has expected signature."""
    import inspect

    from orchestration.patterns.n_version import run_n_version

    sig = inspect.signature(run_n_version)
    params = list(sig.parameters.keys())

    # Should have these parameters
    assert "task_prompt" in params
    assert "n" in params
    assert "model" in params
    assert "working_dir" in params


def test_debate_signature():
    """Verify run_debate has expected signature."""
    import inspect

    from orchestration.patterns.debate import run_debate

    sig = inspect.signature(run_debate)
    params = list(sig.parameters.keys())

    # Should have these parameters
    assert "decision_question" in params
    assert "perspectives" in params
    assert "rounds" in params
    assert "working_dir" in params


def test_cascade_signature():
    """Verify run_cascade has expected signature."""
    import inspect

    from orchestration.patterns.cascade import run_cascade

    sig = inspect.signature(run_cascade)
    params = list(sig.parameters.keys())

    # Should have these parameters
    assert "task_prompt" in params
    assert "fallback_strategy" in params
    assert "timeout_strategy" in params
    assert "working_dir" in params
