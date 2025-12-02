#!/usr/bin/env python3
"""Tests for trace log analyzer."""

import json
import sys
from pathlib import Path

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from tool import TraceLogAnalyzer


@pytest.fixture
def analyzer():
    """Create analyzer instance."""
    return TraceLogAnalyzer()


@pytest.fixture
def sample_jsonl(tmp_path):
    """Create sample JSONL log file."""
    log_file = tmp_path / "sample.jsonl"

    entries = [
        {
            "request": {
                "body": {"messages": [{"role": "user", "content": "Fix the authentication bug"}]}
            }
        },
        {
            "request": {
                "body": {
                    "messages": [
                        {"role": "user", "content": "Create a new feature for user profiles"}
                    ]
                }
            }
        },
        {
            "request": {
                "body": {
                    "messages": [
                        {
                            "role": "user",
                            "content": "<system-reminder>This is system generated</system-reminder>",
                        }
                    ]
                }
            }
        },
    ]

    with open(log_file, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry) + "\n")

    return log_file


def test_parse_valid_jsonl(analyzer, sample_jsonl):
    """Test parsing valid JSONL file."""
    entries = analyzer.parse_jsonl_file(sample_jsonl)

    assert len(entries) == 3
    assert isinstance(entries[0], dict)


def test_parse_malformed_jsonl(analyzer, tmp_path):
    """Test handling malformed JSONL."""
    log_file = tmp_path / "malformed.jsonl"

    with open(log_file, "w") as f:
        f.write('{"valid": "entry"}\n')
        f.write("invalid json line\n")
        f.write('{"another": "valid"}\n')

    entries = analyzer.parse_jsonl_file(log_file)

    # Should skip invalid line
    assert len(entries) == 2


def test_is_system_generated(analyzer):
    """Test system message detection."""
    assert analyzer.is_system_generated("<system-reminder>Test</system-reminder>")
    assert analyzer.is_system_generated("SessionStart: 2025-11-22")
    assert analyzer.is_system_generated("foo")
    assert not analyzer.is_system_generated("Fix the bug")


def test_extract_user_messages(analyzer, sample_jsonl):
    """Test user message extraction."""
    entries = analyzer.parse_jsonl_file(sample_jsonl)
    messages = analyzer.extract_user_messages(entries)

    # Should extract 2 messages (excluding system-generated)
    assert len(messages) == 2
    assert "Fix the authentication bug" in messages
    assert "Create a new feature for user profiles" in messages


def test_categorize_request(analyzer):
    """Test request categorization."""
    # Fix/debug category
    categories = analyzer.categorize_request("Fix the authentication bug")
    assert "fix_debug" in categories

    # Implement category
    categories = analyzer.categorize_request("Create a new user feature")
    assert "implement" in categories

    # Testing category
    categories = analyzer.categorize_request("Run the pytest suite")
    assert "testing" in categories

    # Slash command
    categories = analyzer.categorize_request("/analyze the codebase")
    assert "slash_command" in categories

    # Question
    categories = analyzer.categorize_request("Should we use TypeScript?")
    assert "question" in categories


def test_extract_task_verbs(analyzer):
    """Test task verb extraction."""
    verbs = analyzer.extract_task_verbs("Fix the bug and implement the feature")
    assert "fix" in verbs
    assert "implement" in verbs

    verbs = analyzer.extract_task_verbs("Analyze and optimize the code")
    assert "analyze" in verbs
    assert "optimize" in verbs


def test_identify_decision_patterns(analyzer):
    """Test decision pattern identification."""
    messages = [
        "Do it all - implement everything",
        "I prefer working autonomously",
        "Merge it when ready",
        "Make sure to verify all edge cases",
        "Please add tests",
    ]

    patterns = analyzer.identify_decision_patterns(messages)

    assert "completeness_required" in patterns
    assert len(patterns["completeness_required"]) > 0

    assert "high_autonomy" in patterns
    assert len(patterns["high_autonomy"]) > 0

    assert "merge_instructions" in patterns
    assert len(patterns["merge_instructions"]) > 0

    assert "quality_emphasis" in patterns
    assert len(patterns["quality_emphasis"]) > 0

    assert "polite_requests" in patterns
    assert len(patterns["polite_requests"]) > 0


def test_extract_key_phrases(analyzer):
    """Test key phrase extraction."""
    messages = [
        "This is a test message for analysis",
        "This is a test message for analysis",
        "Another unique message here",
    ]

    phrases = analyzer.extract_key_phrases(messages, min_length=10, max_length=100)

    # Repeated phrase should have count > 1
    assert phrases.most_common(1)[0][1] >= 2


def test_analyze_with_empty_directory(analyzer, tmp_path):
    """Test analysis with empty directory."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    # Should not crash with empty directory
    result = analyzer.analyze(empty_dir, sample_size=5)

    assert result["total_messages"] == 0
    assert result["file_stats"] == []


def test_analyze_with_sample_logs(analyzer, tmp_path):
    """Test full analysis workflow."""
    # Create sample log files
    log_dir = tmp_path / "logs"
    log_dir.mkdir()

    for i in range(3):
        log_file = log_dir / f"log_{i}.jsonl"
        entry = {
            "request": {"body": {"messages": [{"role": "user", "content": f"Fix bug number {i}"}]}}
        }
        with open(log_file, "w") as f:
            f.write(json.dumps(entry) + "\n")

    result = analyzer.analyze(log_dir, sample_size=5)

    assert result["total_messages"] == 3
    assert len(result["file_stats"]) == 3
    assert "fix_debug" in result["categories"]


def test_generate_report(analyzer, tmp_path):
    """Test report generation."""
    from collections import Counter

    output = tmp_path / "report.md"

    analysis = {
        "file_stats": [
            {"file": "test.jsonl", "total_entries": 10, "user_messages": 5, "size_mb": 0.1}
        ],
        "total_messages": 100,
        "categories": Counter({"fix_debug": 30, "implement": 40}),
        "task_verbs": Counter({"fix": 30, "create": 40}),
        "top_short_requests": [("Fix bug", 10), ("Create feature", 8)],
        "top_key_phrases": [("Test phrase", 5)],
        "slash_commands": [("/analyze", 3)],
        "decision_patterns": {
            "completeness_required": ["Do it all"],
            "high_autonomy": ["Work independently"],
        },
        "sample_messages": {
            "all": ["Message 1", "Message 2"],
            "long": ["Long message here"],
            "short": ["Short"],
        },
    }

    analyzer.generate_report(analysis, output)

    assert output.exists()
    content = output.read_text()

    # Verify key sections
    assert "# Claude-Trace Log Analysis Report" in content
    assert "Executive Summary" in content
    assert "Request Categories" in content
    assert "Most Common Task Verbs" in content
    assert "Decision Patterns" in content
    assert "Key Insights" in content


def test_content_blocks_extraction(analyzer):
    """Test extraction from content blocks format."""
    entries = [
        {
            "request": {
                "body": {
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "First part"},
                                {"type": "text", "text": "Second part"},
                            ],
                        }
                    ]
                }
            }
        }
    ]

    messages = analyzer.extract_user_messages(entries)

    assert len(messages) == 1
    assert "First part Second part" in messages[0]


def test_various_message_formats(analyzer):
    """Test handling various message formats."""
    entries = [
        # Format 1: request.body.messages
        {"request": {"body": {"messages": [{"role": "user", "content": "Message 1"}]}}},
        # Format 2: request.messages
        {"request": {"messages": [{"role": "user", "content": "Message 2"}]}},
        # Format 3: messages at root
        {"messages": [{"role": "user", "content": "Message 3"}]},
    ]

    messages = analyzer.extract_user_messages(entries)

    assert len(messages) == 3
    assert "Message 1" in messages
    assert "Message 2" in messages
    assert "Message 3" in messages


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
