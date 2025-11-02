#!/usr/bin/env python3
"""
Comprehensive test suite for PreToolUse hook.
Tests agent detection, logging, and performance.
"""

import json
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add hook directory to path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".claude/tools/amplihack/hooks"))

from pre_tool_use import PreToolUseHook


class TestAgentDetection:
    """Test agent detection from various sources."""

    def setup_method(self):
        """Setup test instance."""
        self.hook = PreToolUseHook()

    def test_extract_agent_from_core_path(self):
        """Test extracting agent name from core agent path."""
        path = ".claude/agents/amplihack/core/architect.md"
        agent_name = self.hook.extract_agent_from_path(path)
        assert agent_name == "architect"

    def test_extract_agent_from_specialized_path(self):
        """Test extracting agent name from specialized agent path."""
        path = ".claude/agents/amplihack/specialized/fix-agent.md"
        agent_name = self.hook.extract_agent_from_path(path)
        assert agent_name == "fix-agent"

    def test_extract_agent_from_workflow_path(self):
        """Test extracting agent name from workflow path."""
        path = ".claude/agents/amplihack/workflows/ci-diagnostic-workflow.md"
        agent_name = self.hook.extract_agent_from_path(path)
        assert agent_name == "ci-diagnostic-workflow"

    def test_extract_agent_from_absolute_path(self):
        """Test extracting agent from absolute path."""
        path = "/home/user/project/.claude/agents/amplihack/core/builder.md"
        agent_name = self.hook.extract_agent_from_path(path)
        assert agent_name == "builder"

    def test_extract_agent_from_windows_path(self):
        """Test extracting agent from Windows-style path."""
        path = r"C:\project\.claude\agents\amplihack\core\reviewer.md"
        agent_name = self.hook.extract_agent_from_path(path)
        assert agent_name == "reviewer"

    def test_extract_agent_no_match(self):
        """Test no agent found in non-agent path."""
        path = ".claude/context/PHILOSOPHY.md"
        agent_name = self.hook.extract_agent_from_path(path)
        assert agent_name is None

    def test_is_valid_agent_name_known_agents(self):
        """Test validation of known agent names."""
        assert self.hook._is_valid_agent_name("architect")
        assert self.hook._is_valid_agent_name("builder")
        assert self.hook._is_valid_agent_name("reviewer")

    def test_is_valid_agent_name_with_suffixes(self):
        """Test validation of names with common agent suffixes."""
        assert self.hook._is_valid_agent_name("custom-agent")
        assert self.hook._is_valid_agent_name("test-workflow")
        assert self.hook._is_valid_agent_name("fix-diagnostic")
        assert self.hook._is_valid_agent_name("api-architect")
        assert self.hook._is_valid_agent_name("rust-expert")

    def test_is_valid_agent_name_invalid_format(self):
        """Test rejection of invalid agent name formats."""
        assert not self.hook._is_valid_agent_name("")
        assert not self.hook._is_valid_agent_name("Agent123")
        assert not self.hook._is_valid_agent_name("UPPERCASE")
        assert not self.hook._is_valid_agent_name("has_underscore")


class TestTaskToolDetection:
    """Test agent detection from Task tool invocations."""

    def setup_method(self):
        """Setup test instance."""
        self.hook = PreToolUseHook()

    def test_detect_task_tool_with_file_reference(self):
        """Test detecting agent from Task tool with file reference."""
        tool_use = {
            "name": "Task",
            "input": {"task": "@.claude/agents/amplihack/core/architect.md"},
        }
        agent_name = self.hook.detect_task_tool_agent(tool_use)
        assert agent_name == "architect"

    def test_detect_task_tool_with_agent_mention(self):
        """Test detecting agent from Task tool with agent name in prompt."""
        tool_use = {
            "name": "Task",
            "input": {"task": "Use the builder agent to implement this feature"},
        }
        agent_name = self.hook.detect_task_tool_agent(tool_use)
        assert agent_name == "builder"

    def test_detect_task_tool_with_multiple_agents(self):
        """Test detecting first agent when multiple mentioned."""
        tool_use = {
            "name": "Task",
            "input": {
                "task": "Use architect agent to design, then builder to implement"
            },
        }
        agent_name = self.hook.detect_task_tool_agent(tool_use)
        # Should detect first mentioned agent
        assert agent_name in ["architect", "builder"]

    def test_detect_task_tool_no_agent(self):
        """Test no detection when Task tool has no agent reference."""
        tool_use = {"name": "Task", "input": {"task": "Generic task description"}}
        agent_name = self.hook.detect_task_tool_agent(tool_use)
        assert agent_name is None

    def test_detect_non_task_tool(self):
        """Test no detection for non-Task tools."""
        tool_use = {"name": "Read", "input": {"file_path": "some_file.py"}}
        agent_name = self.hook.detect_task_tool_agent(tool_use)
        assert agent_name is None


class TestToolParameterDetection:
    """Test agent detection from tool parameters."""

    def setup_method(self):
        """Setup test instance."""
        self.hook = PreToolUseHook()

    def test_detect_from_read_tool(self):
        """Test detecting agent from Read tool file_path parameter."""
        tool_use = {
            "name": "Read",
            "input": {"file_path": ".claude/agents/amplihack/core/tester.md"},
        }
        agent_name = self.hook.detect_agent_from_tool_parameters(tool_use)
        assert agent_name == "tester"

    def test_detect_from_slash_command(self):
        """Test detecting agent from SlashCommand."""
        tool_use = {
            "name": "SlashCommand",
            "input": {"command": "/fix using fix-agent"},
        }
        agent_name = self.hook.detect_agent_from_tool_parameters(tool_use)
        assert agent_name == "fix-agent"

    def test_no_detection_from_other_tools(self):
        """Test no detection from tools without agent references."""
        tool_use = {"name": "Write", "input": {"file_path": "output.txt", "content": "data"}}
        agent_name = self.hook.detect_agent_from_tool_parameters(tool_use)
        assert agent_name is None


class TestMainDetectionLogic:
    """Test the main agent detection orchestration."""

    def setup_method(self):
        """Setup test instance."""
        self.hook = PreToolUseHook()

    def test_detect_via_task_tool(self):
        """Test detection prioritizes Task tool."""
        input_data = {
            "toolUse": {
                "name": "Task",
                "input": {"task": "@.claude/agents/amplihack/core/optimizer.md"},
            }
        }
        agent_name = self.hook.detect_agent_invocation(input_data)
        assert agent_name == "optimizer"

    def test_detect_via_read_tool_fallback(self):
        """Test detection falls back to tool parameters."""
        input_data = {
            "toolUse": {
                "name": "Read",
                "input": {"file_path": ".claude/agents/amplihack/specialized/security.md"},
            }
        }
        agent_name = self.hook.detect_agent_invocation(input_data)
        assert agent_name == "security"

    def test_no_detection(self):
        """Test no detection when no agent reference found."""
        input_data = {
            "toolUse": {"name": "Bash", "input": {"command": "ls -la"}}
        }
        agent_name = self.hook.detect_agent_invocation(input_data)
        assert agent_name is None


class TestLogging:
    """Test subagent logging functionality."""

    def setup_method(self):
        """Setup test instance with temporary log directory."""
        # Create temporary directory for logs
        self.temp_dir = tempfile.mkdtemp()
        self.hook = PreToolUseHook()

        # Override log directories to use temp
        self.hook.metrics_dir = Path(self.temp_dir)
        self.hook.subagent_log = Path(self.temp_dir) / "subagent_start.jsonl"

    def test_log_subagent_start_creates_file(self):
        """Test that logging creates the JSONL file."""
        tool_use = {
            "name": "Task",
            "id": "test-123",
            "input": {"task": "Test agent invocation"},
        }
        context = {"hook_event": "PreToolUse", "detected_via": "Task"}

        self.hook.log_subagent_start("architect", tool_use, context)

        assert self.hook.subagent_log.exists()

    def test_log_subagent_start_format(self):
        """Test that logged data has correct format."""
        tool_use = {
            "name": "Task",
            "id": "test-456",
            "input": {"task": "Design the system architecture"},
        }
        context = {"hook_event": "PreToolUse", "detected_via": "Task"}

        self.hook.log_subagent_start("architect", tool_use, context)

        # Read the logged entry
        with open(self.hook.subagent_log, "r") as f:
            line = f.readline()
            entry = json.loads(line)

        # Verify required fields
        assert "timestamp" in entry
        assert "session_id" in entry
        assert entry["agent_type"] == "architect"
        assert entry["tool_name"] == "Task"
        assert "prompt" in entry
        assert "context" in entry
        assert entry["context"]["tool_id"] == "test-456"
        assert entry["context"]["hook_event"] == "PreToolUse"

    def test_log_multiple_entries(self):
        """Test logging multiple agent invocations."""
        agents = ["architect", "builder", "reviewer"]

        for agent in agents:
            tool_use = {
                "name": "Task",
                "id": f"test-{agent}",
                "input": {"task": f"Task for {agent}"},
            }
            context = {"hook_event": "PreToolUse"}
            self.hook.log_subagent_start(agent, tool_use, context)

        # Verify all entries logged
        with open(self.hook.subagent_log, "r") as f:
            lines = f.readlines()

        assert len(lines) == 3

        # Verify each agent logged
        logged_agents = []
        for line in lines:
            entry = json.loads(line)
            logged_agents.append(entry["agent_type"])

        assert set(logged_agents) == set(agents)

    def test_truncate_long_prompt(self):
        """Test that long prompts are truncated."""
        long_prompt = "A" * 1000
        truncated = self.hook.truncate_text(long_prompt, max_length=500)

        assert len(truncated) == 500
        assert truncated.endswith("...")

    def test_no_truncate_short_prompt(self):
        """Test that short prompts are not truncated."""
        short_prompt = "Short prompt"
        result = self.hook.truncate_text(short_prompt, max_length=500)

        assert result == short_prompt


class TestProcessMethod:
    """Test the main process method."""

    def setup_method(self):
        """Setup test instance."""
        self.temp_dir = tempfile.mkdtemp()
        self.hook = PreToolUseHook()
        self.hook.metrics_dir = Path(self.temp_dir)
        self.hook.subagent_log = Path(self.temp_dir) / "subagent_start.jsonl"

    def test_process_with_agent_detection(self):
        """Test processing with agent detection logs correctly."""
        input_data = {
            "toolUse": {
                "name": "Task",
                "id": "test-789",
                "input": {"task": "@.claude/agents/amplihack/core/builder.md"},
            }
        }

        result = self.hook.process(input_data)

        # Should return empty dict (allow execution)
        assert result == {}

        # Should have logged the agent
        assert self.hook.subagent_log.exists()

        with open(self.hook.subagent_log, "r") as f:
            entry = json.loads(f.readline())

        assert entry["agent_type"] == "builder"

    def test_process_without_agent_detection(self):
        """Test processing without agent detection."""
        input_data = {
            "toolUse": {"name": "Bash", "id": "test-999", "input": {"command": "pwd"}}
        }

        result = self.hook.process(input_data)

        # Should return empty dict (allow execution)
        assert result == {}

        # Should not have logged anything
        assert not self.hook.subagent_log.exists()

    def test_process_always_allows_execution(self):
        """Test that process always returns empty dict to allow execution."""
        test_cases = [
            {
                "toolUse": {
                    "name": "Task",
                    "input": {"task": "@.claude/agents/amplihack/core/architect.md"},
                }
            },
            {"toolUse": {"name": "Read", "input": {"file_path": "test.py"}}},
            {"toolUse": {"name": "Write", "input": {"file_path": "output.txt"}}},
        ]

        for input_data in test_cases:
            result = self.hook.process(input_data)
            assert result == {}, f"Failed for {input_data['toolUse']['name']}"


class TestPerformance:
    """Test performance requirements."""

    def setup_method(self):
        """Setup test instance."""
        self.temp_dir = tempfile.mkdtemp()
        self.hook = PreToolUseHook()
        self.hook.metrics_dir = Path(self.temp_dir)
        self.hook.subagent_log = Path(self.temp_dir) / "subagent_start.jsonl"

    def test_detection_performance(self):
        """Test that detection completes within 50ms."""
        input_data = {
            "toolUse": {
                "name": "Task",
                "id": "perf-test",
                "input": {"task": "@.claude/agents/amplihack/core/architect.md"},
            }
        }

        start_time = time.time()
        self.hook.detect_agent_invocation(input_data)
        duration_ms = (time.time() - start_time) * 1000

        assert duration_ms < 50, f"Detection took {duration_ms}ms, expected < 50ms"

    def test_logging_performance(self):
        """Test that logging completes within 50ms."""
        tool_use = {
            "name": "Task",
            "id": "perf-test-log",
            "input": {"task": "Performance test"},
        }
        context = {"hook_event": "PreToolUse"}

        start_time = time.time()
        self.hook.log_subagent_start("architect", tool_use, context)
        duration_ms = (time.time() - start_time) * 1000

        assert duration_ms < 50, f"Logging took {duration_ms}ms, expected < 50ms"

    def test_full_process_performance(self):
        """Test that full process method completes within 50ms."""
        input_data = {
            "toolUse": {
                "name": "Task",
                "id": "perf-full",
                "input": {"task": "@.claude/agents/amplihack/core/builder.md"},
            }
        }

        start_time = time.time()
        self.hook.process(input_data)
        duration_ms = (time.time() - start_time) * 1000

        assert duration_ms < 50, f"Process took {duration_ms}ms, expected < 50ms"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def setup_method(self):
        """Setup test instance."""
        self.hook = PreToolUseHook()

    def test_empty_input_data(self):
        """Test handling of empty input data."""
        agent_name = self.hook.detect_agent_invocation({})
        assert agent_name is None

    def test_missing_tool_use_key(self):
        """Test handling of missing toolUse key."""
        input_data = {"someOtherKey": "value"}
        agent_name = self.hook.detect_agent_invocation(input_data)
        assert agent_name is None

    def test_empty_tool_input(self):
        """Test handling of empty tool input."""
        tool_use = {"name": "Task", "input": {}}
        agent_name = self.hook.detect_task_tool_agent(tool_use)
        assert agent_name is None

    def test_malformed_path(self):
        """Test handling of malformed file paths."""
        path = "///invalid///.md"
        agent_name = self.hook.extract_agent_from_path(path)
        assert agent_name is None

    def test_very_long_prompt(self):
        """Test handling of extremely long prompts."""
        very_long = "A" * 10000
        truncated = self.hook.truncate_text(very_long, max_length=500)
        assert len(truncated) == 500

    def test_unicode_in_agent_name(self):
        """Test handling of unicode characters in paths."""
        path = ".claude/agents/café-agent.md"
        # Should not detect as valid agent name
        agent_name = self.hook.extract_agent_from_path(path)
        # Unicode names don't match our pattern
        assert agent_name is None or not self.hook._is_valid_agent_name(agent_name)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
