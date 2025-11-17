"""Integration tests for project_initializer with session_start hook.

Tests the full integration flow:
1. Session start triggers initialization
2. End-to-end initialization flow
3. Real project detection scenarios
4. Hook integration behavior
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from amplihack.utils.project_initializer import ProjectInitializer, ProjectState


class TestSessionStartIntegration:
    """Test integration with session_start hook."""

    def test_session_start_initializes_missing_project_md(self, tmp_path, monkeypatch):
        """Integration 1: Session start initializes missing PROJECT.md."""
        # Setup - mock the hook environment
        monkeypatch.chdir(tmp_path)

        # Create hook processor mock
        class MockHookProcessor:
            def __init__(self):
                self.project_root = tmp_path
                self.metrics = {}

            def log(self, msg, level="INFO"):
                pass

            def save_metric(self, key, value):
                self.metrics[key] = value

        hook = MockHookProcessor()

        # Execute the initialization logic (simulating session_start.py)
        from amplihack.utils.project_initializer import ProjectInitializer

        initializer = ProjectInitializer(hook.project_root)
        if initializer.should_initialize():
            success = initializer.initialize(use_sdk=False)
            hook.save_metric("project_md_initialized", success)

        # Verify
        project_md = tmp_path / ".claude" / "context" / "PROJECT.md"
        assert project_md.exists()
        assert hook.metrics["project_md_initialized"] is True

    def test_session_start_skips_valid_project_md(self, tmp_path, monkeypatch):
        """Integration 2: Session start skips valid PROJECT.md."""
        # Setup - create valid PROJECT.md
        project_md = tmp_path / ".claude" / "context" / "PROJECT.md"
        project_md.parent.mkdir(parents=True)
        project_md.write_text("""
# Project: Existing Valid Project

This project has real content that should not be overwritten.
We're building a web application with specific requirements.
        """)

        monkeypatch.chdir(tmp_path)

        # Create hook processor mock
        class MockHookProcessor:
            def __init__(self):
                self.project_root = tmp_path
                self.metrics = {}
                self.logs = []

            def log(self, msg, level="INFO"):
                self.logs.append((msg, level))

            def save_metric(self, key, value):
                self.metrics[key] = value

        hook = MockHookProcessor()
        original_content = project_md.read_text()

        # Execute
        from amplihack.utils.project_initializer import ProjectInitializer

        initializer = ProjectInitializer(hook.project_root)
        if initializer.should_initialize():
            success = initializer.initialize(use_sdk=False)
            hook.log("Initializing PROJECT.md...")
            hook.save_metric("project_md_initialized", success)
        else:
            hook.log("PROJECT.md already configured")
            hook.save_metric("project_md_initialized", False)

        # Verify - content unchanged
        assert project_md.read_text() == original_content
        assert hook.metrics["project_md_initialized"] is False
        assert any("already configured" in log[0] for log in hook.logs)

    def test_session_start_replaces_amplihack_description(self, tmp_path, monkeypatch):
        """Integration 3: Session start replaces amplihack self-description."""
        # Setup - create PROJECT.md with amplihack description
        project_md = tmp_path / ".claude" / "context" / "PROJECT.md"
        project_md.parent.mkdir(parents=True)
        project_md.write_text("""
# Project: Microsoft Hackathon 2025 - Agentic Coding Framework

This project is developing an advanced agentic coding framework that leverages
AI agents to accelerate software development through intelligent automation.

## Agent-Powered Development

Building the future of AI-assisted coding.
        """)

        monkeypatch.chdir(tmp_path)

        # Create hook processor mock
        class MockHookProcessor:
            def __init__(self):
                self.project_root = tmp_path
                self.metrics = {}
                self.logs = []

            def log(self, msg, level="INFO"):
                self.logs.append((msg, level))

            def save_metric(self, key, value):
                self.metrics[key] = value

        hook = MockHookProcessor()

        # Execute
        from amplihack.utils.project_initializer import ProjectInitializer

        initializer = ProjectInitializer(hook.project_root)
        if initializer.should_initialize():
            hook.log("Initializing PROJECT.md...")
            success = initializer.initialize(use_sdk=False)
            if success:
                hook.log("✅ PROJECT.md initialized")
                hook.save_metric("project_md_initialized", True)
            else:
                hook.log("⚠️ PROJECT.md initialization failed", "WARNING")
                hook.save_metric("project_md_initialized", False)

        # Verify - content replaced
        new_content = project_md.read_text()
        assert "Agentic Coding Framework" not in new_content
        assert "[Your Project Name]" in new_content
        assert hook.metrics["project_md_initialized"] is True
        assert any("initialized" in log[0] for log in hook.logs)

        # Verify backup created
        backup_path = project_md.with_suffix(".md.backup")
        assert backup_path.exists()
        assert "Agentic Coding Framework" in backup_path.read_text()

    def test_session_start_handles_errors_gracefully(self, tmp_path, monkeypatch):
        """Integration 4: Session start handles initialization errors gracefully."""
        # Setup
        monkeypatch.chdir(tmp_path)

        # Create hook processor mock
        class MockHookProcessor:
            def __init__(self):
                self.project_root = tmp_path
                self.metrics = {}
                self.logs = []

            def log(self, msg, level="INFO"):
                self.logs.append((msg, level))

            def save_metric(self, key, value):
                self.metrics[key] = value

        hook = MockHookProcessor()

        # Make directory creation fail
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude").chmod(0o444)  # Read-only

        # Execute
        try:
            from amplihack.utils.project_initializer import ProjectInitializer

            initializer = ProjectInitializer(hook.project_root)
            if initializer.should_initialize():
                hook.log("Initializing PROJECT.md...")
                success = initializer.initialize(use_sdk=False)
                if success:
                    hook.log("✅ PROJECT.md initialized")
                    hook.save_metric("project_md_initialized", True)
                else:
                    hook.log("⚠️ PROJECT.md initialization failed", "WARNING")
                    hook.save_metric("project_md_initialized", False)
        except Exception as e:
            hook.log(f"PROJECT.md initialization error: {e}", "ERROR")
            hook.save_metric("project_md_initialized", False)

        # Verify - error handled gracefully
        assert hook.metrics["project_md_initialized"] is False
        assert any(log[1] in ["WARNING", "ERROR"] for log in hook.logs)

        # Cleanup
        (tmp_path / ".claude").chmod(0o755)


class TestEndToEndFlow:
    """Test complete end-to-end initialization flows."""

    def test_fresh_project_initialization(self, tmp_path):
        """E2E: Fresh project gets initialized with template."""
        # Setup - empty project directory
        initializer = ProjectInitializer(tmp_path)

        # Verify initial state
        state, reason = initializer.detect_state()
        assert state == ProjectState.MISSING

        # Execute initialization
        success = initializer.initialize(use_sdk=False)

        # Verify final state
        assert success
        state, reason = initializer.detect_state()
        assert state == ProjectState.DESCRIBES_AMPLIHACK  # Template has placeholders

        # Verify content
        content = initializer.project_md.read_text()
        assert "[Your Project Name]" in content
        assert "Quick Start" in content

    def test_amplihack_installation_overwrites_old_project_md(self, tmp_path):
        """E2E: Installing amplihack in existing project with old PROJECT.md."""
        # Setup - simulate old PROJECT.md from previous amplihack version
        project_md = tmp_path / ".claude" / "context" / "PROJECT.md"
        project_md.parent.mkdir(parents=True)
        project_md.write_text("""
# Project: Microsoft Hackathon 2025 - Agentic Coding Framework

## Overview

This project is developing an advanced agentic coding framework...

## Core Objectives

### 1. Agent-Powered Development
        """)

        initializer = ProjectInitializer(tmp_path)

        # Verify detected as amplihack description
        state, reason = initializer.detect_state()
        assert state == ProjectState.DESCRIBES_AMPLIHACK

        # Execute initialization
        success = initializer.initialize(use_sdk=False)

        # Verify replacement
        assert success
        new_content = project_md.read_text()
        assert "Microsoft Hackathon" not in new_content
        assert "[Your Project Name]" in new_content

        # Verify backup
        backup = project_md.with_suffix(".md.backup")
        assert backup.exists()
        assert "Microsoft Hackathon" in backup.read_text()

    def test_user_customized_project_preserved(self, tmp_path):
        """E2E: User-customized PROJECT.md is never overwritten."""
        # Setup - user has customized their PROJECT.md
        project_md = tmp_path / ".claude" / "context" / "PROJECT.md"
        project_md.parent.mkdir(parents=True)
        custom_content = """
# Project: My E-Commerce Platform

## Overview

This is a Django-based e-commerce platform for selling artisan crafts.

## Architecture

### Key Components

- **Django Backend**: REST API with DRF
- **React Frontend**: SPA with TypeScript
- **PostgreSQL**: Primary data store
- **Redis**: Caching and session management

## Development Guidelines

We follow PEP 8 and have 90%+ test coverage requirements.
        """
        project_md.write_text(custom_content)

        initializer = ProjectInitializer(tmp_path)

        # Verify detected as valid user content
        state, reason = initializer.detect_state()
        assert state == ProjectState.VALID_USER_CONTENT

        # Execute initialization (should skip)
        success = initializer.initialize(use_sdk=False)

        # Verify content unchanged
        assert success  # Returns True (no action needed)
        assert project_md.read_text() == custom_content

        # Verify no backup created
        backup = project_md.with_suffix(".md.backup")
        assert not backup.exists()

    def test_sdk_generation_with_real_project_context(self, tmp_path):
        """E2E: SDK generation uses actual project context."""
        # Setup - create a realistic project structure
        (tmp_path / "pyproject.toml").write_text("""
[tool.poetry]
name = "my-fastapi-app"
version = "0.1.0"
        """)
        (tmp_path / "README.md").write_text("# FastAPI Application")
        (tmp_path / "src").mkdir()
        (tmp_path / "tests").mkdir()
        (tmp_path / "Makefile").write_text("test:\n\tpytest")

        # Mock SDK response
        mock_anthropic = MagicMock()
        mock_client = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="""
# Project: FastAPI Application

## Overview

Based on the project structure, this is a Python FastAPI application.

## Architecture

### Key Components

- **API Server**: FastAPI backend
- **Testing**: Pytest test suite

### Technology Stack

- **Language**: Python
- **Framework**: FastAPI
- **Testing**: Pytest
        """)]
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        initializer = ProjectInitializer(tmp_path)

        # Execute with SDK
        with patch.dict('sys.modules', {'anthropic': mock_anthropic}):
            with patch.dict('os.environ', {'ANTHROPIC_API_KEY': 'test-key'}):
                success = initializer.initialize(use_sdk=True)

        # Verify SDK was called with context
        assert success
        content = initializer.project_md.read_text()
        assert "FastAPI Application" in content
        assert "[Your Project Name]" not in content  # Not the template

        # Verify SDK received project context
        call_args = mock_client.messages.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "pyproject.toml" in prompt or "Python project" in prompt


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_multiple_session_starts_idempotent(self, tmp_path):
        """Multiple session starts don't cause issues."""
        # Setup
        initializer = ProjectInitializer(tmp_path)

        # Execute multiple initializations
        success1 = initializer.initialize(use_sdk=False)
        success2 = initializer.initialize(use_sdk=False)
        success3 = initializer.initialize(use_sdk=False)

        # Verify all succeed
        assert success1 is True
        assert success2 is True
        assert success3 is True

        # Verify only one PROJECT.md
        assert initializer.project_md.exists()

    def test_parallel_session_starts_safe(self, tmp_path):
        """Parallel session starts don't corrupt file."""
        # Setup
        init1 = ProjectInitializer(tmp_path)
        init2 = ProjectInitializer(tmp_path)

        # Execute in sequence (simulating parallel in same process)
        success1 = init1.initialize(use_sdk=False)
        success2 = init2.initialize(use_sdk=False)

        # Verify both succeed
        assert success1 is True
        assert success2 is True

        # Verify valid content
        content = init1.project_md.read_text()
        assert len(content) > 100
        assert "[Your Project Name]" in content

    def test_corrupted_project_md_gets_replaced(self, tmp_path):
        """Corrupted or invalid PROJECT.md gets replaced."""
        # Setup - create corrupted/invalid content
        project_md = tmp_path / ".claude" / "context" / "PROJECT.md"
        project_md.parent.mkdir(parents=True)
        project_md.write_text("corrupted\x00\x01\x02")  # Invalid content

        initializer = ProjectInitializer(tmp_path)

        # Execute
        state, _ = initializer.detect_state()
        # Even if readable, should be detected as invalid (too short)
        success = initializer.initialize(use_sdk=False)

        # Verify replacement
        assert success
        content = project_md.read_text()
        assert "\x00" not in content
        assert "[Your Project Name]" in content

    def test_migration_from_old_amplihack_version(self, tmp_path):
        """Migration from old amplihack with old PROJECT.md format."""
        # Setup - old format from before PR #1278
        project_md = tmp_path / ".claude" / "context" / "PROJECT.md"
        project_md.parent.mkdir(parents=True)
        project_md.write_text("""
# Project: Microsoft Hackathon 2025 - Agentic Coding Framework

## Overview

This project is developing an advanced agentic coding framework that leverages
AI agents to accelerate software development through intelligent automation,
code generation, and collaborative problem-solving.

## Mission

Create a development environment where AI agents work alongside developers...
        """)

        initializer = ProjectInitializer(tmp_path)

        # Verify detected correctly
        state, reason = initializer.detect_state()
        assert state == ProjectState.DESCRIBES_AMPLIHACK
        assert "amplihack framework" in reason

        # Execute migration
        success = initializer.initialize(use_sdk=False)

        # Verify migrated
        assert success
        new_content = project_md.read_text()
        assert "Mission" not in new_content
        assert "[Your Project Name]" in new_content

        # Verify old content backed up
        backup = project_md.with_suffix(".md.backup")
        assert backup.exists()
        assert "Mission" in backup.read_text()


class TestMetricsAndLogging:
    """Test that integration properly tracks metrics."""

    def test_successful_init_tracked(self, tmp_path):
        """Successful initialization tracked in metrics."""
        metrics = {}

        def save_metric(key, value):
            metrics[key] = value

        # Execute
        initializer = ProjectInitializer(tmp_path)
        success = initializer.initialize(use_sdk=False)
        save_metric("project_md_initialized", success)

        # Verify
        assert metrics["project_md_initialized"] is True

    def test_skipped_init_tracked(self, tmp_path):
        """Skipped initialization (valid content) tracked."""
        # Setup
        project_md = tmp_path / ".claude" / "context" / "PROJECT.md"
        project_md.parent.mkdir(parents=True)
        project_md.write_text("""
# Real Project

This is a real project with valid user content that should not be overwritten.
We're building a web application with specific requirements and detailed information
about the architecture, components, and technology stack.
        """)

        metrics = {}

        def save_metric(key, value):
            metrics[key] = value

        # Execute
        initializer = ProjectInitializer(tmp_path)
        if initializer.should_initialize():
            save_metric("project_md_initialized", True)
        else:
            save_metric("project_md_initialized", False)

        # Verify
        assert metrics["project_md_initialized"] is False

    def test_failed_init_tracked(self, tmp_path):
        """Failed initialization tracked in metrics."""
        # Setup - make initialization fail
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude").chmod(0o444)

        metrics = {}

        def save_metric(key, value):
            metrics[key] = value

        # Execute
        try:
            initializer = ProjectInitializer(tmp_path)
            success = initializer.initialize(use_sdk=False)
            save_metric("project_md_initialized", success)
        except Exception:
            save_metric("project_md_initialized", False)

        # Verify
        assert metrics["project_md_initialized"] is False

        # Cleanup
        (tmp_path / ".claude").chmod(0o755)
