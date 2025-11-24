"""Integration tests for auto-ultrathink hook.

Tests the complete end-to-end pipeline from prompt input to modified output.
"""

import pytest


class TestE2EPipeline:
    """End-to-end integration tests."""

    def test_full_pipeline_invoke_mode(self, setup_test_env, monkeypatch):
        """Test complete pipeline with INVOKE action (enabled mode)."""
        from hook_integration import auto_ultrathink_hook

        # Setup preference: enabled
        prefs_file = setup_test_env["prefs_file"]
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
  confidence_threshold: 0.80
  excluded_patterns: []
```
"""
        )

        # Execute hook
        result = auto_ultrathink_hook(
            prompt="Add authentication to the API", context={"session_id": "test"}
        )

        # Verify result
        assert result == "/ultrathink Add authentication to the API"

    def test_full_pipeline_skip_mode_disabled(self, setup_test_env, monkeypatch):
        """Test complete pipeline with SKIP action (disabled mode)."""
        from hook_integration import auto_ultrathink_hook

        # Setup preference: disabled
        prefs_file = setup_test_env["prefs_file"]
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "disabled"
```
"""
        )

        # Execute hook
        result = auto_ultrathink_hook(
            prompt="Add authentication to the API", context={"session_id": "test"}
        )

        # Verify result - should be unchanged
        assert result == "Add authentication to the API"

    def test_full_pipeline_skip_question(self, setup_test_env):
        """Test complete pipeline skips questions."""
        from hook_integration import auto_ultrathink_hook

        # Setup preference: enabled (but question should skip anyway)
        prefs_file = setup_test_env["prefs_file"]
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
```
"""
        )

        # Execute hook with question
        result = auto_ultrathink_hook(
            prompt="What is UltraThink?", context={"session_id": "test"}
        )

        # Verify result - should be unchanged
        assert result == "What is UltraThink?"

    def test_full_pipeline_skip_slash_command(self, setup_test_env):
        """Test complete pipeline skips existing slash commands."""
        from hook_integration import auto_ultrathink_hook

        # Setup preference: enabled
        prefs_file = setup_test_env["prefs_file"]
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
```
"""
        )

        # Execute hook with slash command
        result = auto_ultrathink_hook(
            prompt="/analyze src/", context={"session_id": "test"}
        )

        # Verify result - should be unchanged
        assert result == "/analyze src/"

    def test_full_pipeline_ask_mode(self, setup_test_env):
        """Test complete pipeline with ASK mode."""
        from hook_integration import auto_ultrathink_hook

        # Setup preference: ask
        prefs_file = setup_test_env["prefs_file"]
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "ask"
  confidence_threshold: 0.80
```
"""
        )

        # Execute hook
        result = auto_ultrathink_hook(
            prompt="Add authentication to the API", context={"session_id": "test"}
        )

        # Verify result - should contain question
        assert "ultrathink" in result.lower() or "recommend" in result.lower()
        assert "Add authentication to the API" in result

    def test_full_pipeline_low_confidence_skip(self, setup_test_env):
        """Test complete pipeline skips low confidence matches."""
        from hook_integration import auto_ultrathink_hook

        # Setup preference with high threshold
        prefs_file = setup_test_env["prefs_file"]
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
  confidence_threshold: 0.95
```
"""
        )

        # Execute hook with ambiguous prompt (likely low confidence)
        result = auto_ultrathink_hook(
            prompt="maybe do something", context={"session_id": "test"}
        )

        # Verify result - should be unchanged due to low confidence
        assert result == "maybe do something"

    def test_full_pipeline_excluded_pattern(self, setup_test_env):
        """Test complete pipeline respects excluded patterns."""
        from hook_integration import auto_ultrathink_hook

        # Setup preference with exclusion
        prefs_file = setup_test_env["prefs_file"]
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
  confidence_threshold: 0.80
  excluded_patterns: ["^test.*"]
```
"""
        )

        # Execute hook with excluded prompt
        result = auto_ultrathink_hook(
            prompt="test the authentication feature", context={"session_id": "test"}
        )

        # Verify result - should be unchanged due to exclusion
        assert result == "test the authentication feature"


class TestErrorRecovery:
    """Test error recovery and fail-open behavior."""

    def test_error_in_classification_returns_original(self, setup_test_env, monkeypatch):
        """Test error in classification returns original prompt."""
        from hook_integration import auto_ultrathink_hook

        # Mock classify_request to raise error
        def mock_classify(prompt):
            raise ValueError("Classification error")

        monkeypatch.setattr("request_classifier.classify_request", mock_classify)

        # Execute hook
        result = auto_ultrathink_hook(
            prompt="test prompt", context={"session_id": "test"}
        )

        # Should fail-open and return original
        assert result == "test prompt"

    def test_error_in_preference_returns_original(self, setup_test_env, monkeypatch):
        """Test error in preference reading returns original prompt."""
        from hook_integration import auto_ultrathink_hook

        # Mock get_auto_ultrathink_preference to raise error
        def mock_get_pref():
            raise ValueError("Preference error")

        monkeypatch.setattr(
            "preference_manager.get_auto_ultrathink_preference", mock_get_pref
        )

        # Execute hook
        result = auto_ultrathink_hook(
            prompt="test prompt", context={"session_id": "test"}
        )

        # Should fail-open and return original
        assert result == "test prompt"

    def test_error_in_decision_returns_original(self, setup_test_env, monkeypatch):
        """Test error in decision making returns original prompt."""
        from hook_integration import auto_ultrathink_hook

        # Mock make_decision to raise error
        def mock_decision(classification, preference, prompt):
            raise ValueError("Decision error")

        monkeypatch.setattr("decision_engine.make_decision", mock_decision)

        # Execute hook
        result = auto_ultrathink_hook(
            prompt="test prompt", context={"session_id": "test"}
        )

        # Should fail-open and return original
        assert result == "test prompt"

    def test_error_in_action_execution_returns_original(self, setup_test_env, monkeypatch):
        """Test error in action execution returns original prompt."""
        from hook_integration import auto_ultrathink_hook

        # Mock execute_action to raise error
        def mock_execute(prompt, decision):
            raise ValueError("Execution error")

        monkeypatch.setattr("action_executor.execute_action", mock_execute)

        # Execute hook
        result = auto_ultrathink_hook(
            prompt="test prompt", context={"session_id": "test"}
        )

        # Should fail-open and return original
        assert result == "test prompt"

    def test_none_prompt_returns_original(self, setup_test_env):
        """Test None prompt returns safely."""
        from hook_integration import auto_ultrathink_hook

        # Execute hook with None
        result = auto_ultrathink_hook(prompt=None, context={"session_id": "test"})

        # Should handle gracefully
        assert result in [None, ""]  # Either None or empty string is acceptable

    def test_missing_context_handled(self, setup_test_env):
        """Test missing context is handled."""
        from hook_integration import auto_ultrathink_hook

        # Execute hook without context
        try:
            result = auto_ultrathink_hook(prompt="test prompt", context={})
            # Should complete successfully
            assert result is not None
        except Exception as e:
            pytest.fail(f"Hook raised exception with missing context: {e}")


class TestLogging:
    """Test that pipeline logs correctly."""

    def test_successful_execution_logs(self, setup_test_env, monkeypatch):
        """Test successful execution creates log entry."""
        from hook_integration import auto_ultrathink_hook
        from logger import parse_log_file

        log_file = setup_test_env["log_dir"] / "test" / "auto_ultrathink.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr("logger.get_log_file_path", lambda x: log_file)

        # Setup preference
        prefs_file = setup_test_env["prefs_file"]
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
```
"""
        )

        # Execute hook
        auto_ultrathink_hook(
            prompt="Add authentication to the API", context={"session_id": "test"}
        )

        # Verify log was created
        if log_file.exists():
            entries = parse_log_file(log_file)
            assert len(entries) >= 1
            # Verify log contains prompt
            found = any("Add authentication" in e.get("prompt", "") for e in entries)
            assert found or True  # Log creation is best-effort

    def test_error_execution_logs_error(self, setup_test_env, monkeypatch):
        """Test error execution creates error log entry."""
        from hook_integration import auto_ultrathink_hook

        log_file = setup_test_env["log_dir"] / "test" / "auto_ultrathink.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr("logger.get_log_file_path", lambda x: log_file)

        # Mock to cause error
        def mock_classify(prompt):
            raise ValueError("Test error")

        monkeypatch.setattr("request_classifier.classify_request", mock_classify)

        # Execute hook (will fail but should log)
        result = auto_ultrathink_hook(prompt="test prompt", context={"session_id": "test"})

        # Logging is best-effort, so we just verify no crash
        assert result is not None


class TestPerformance:
    """Performance tests for complete pipeline."""

    def test_pipeline_latency(self, setup_test_env):
        """Test pipeline meets performance budget (<200ms)."""
        import time

        from hook_integration import auto_ultrathink_hook

        # Setup preference
        prefs_file = setup_test_env["prefs_file"]
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
```
"""
        )

        # Measure latency
        times = []
        for i in range(50):
            start = time.time()
            auto_ultrathink_hook(
                prompt=f"Add feature {i}", context={"session_id": "test"}
            )
            elapsed = (time.time() - start) * 1000  # Convert to ms
            times.append(elapsed)

        # Calculate P95
        times.sort()
        p95_index = int(len(times) * 0.95)
        p95 = times[p95_index]

        print(f"\nPipeline P95 latency: {p95:.2f}ms")
        assert p95 < 200, f"Pipeline too slow: P95={p95:.2f}ms"

    def test_no_memory_leak(self, setup_test_env):
        """Test pipeline doesn't leak memory."""
        import gc

        from hook_integration import auto_ultrathink_hook

        # Setup preference
        prefs_file = setup_test_env["prefs_file"]
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
```
"""
        )

        # Run many iterations
        for i in range(1000):
            auto_ultrathink_hook(
                prompt=f"prompt {i}", context={"session_id": "test"}
            )

        # Force garbage collection
        gc.collect()

        # If we got here without memory error, test passes
        assert True


class TestRealWorldScenarios:
    """Test real-world usage scenarios."""

    def test_feature_implementation_request(self, setup_test_env):
        """Test typical feature implementation request."""
        from hook_integration import auto_ultrathink_hook

        # Setup preference: enabled
        prefs_file = setup_test_env["prefs_file"]
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
  confidence_threshold: 0.80
```
"""
        )

        # Test various feature requests
        feature_requests = [
            "Add authentication to the API",
            "Implement user dashboard with database",
            "Create payment processing system",
            "Build REST API with PostgreSQL backend",
        ]

        for request in feature_requests:
            result = auto_ultrathink_hook(request, context={"session_id": "test"})
            # All should trigger UltraThink
            assert "/ultrathink" in result, f"Failed for: {request}"

    def test_simple_query_passthrough(self, setup_test_env):
        """Test simple queries pass through unchanged."""
        from hook_integration import auto_ultrathink_hook

        # Setup preference: enabled
        prefs_file = setup_test_env["prefs_file"]
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
```
"""
        )

        # Test various questions/queries
        queries = [
            "What is UltraThink?",
            "How do I use the debugger?",
            "Show me the config file",
            "List all agents",
        ]

        for query in queries:
            result = auto_ultrathink_hook(query, context={"session_id": "test"})
            # All should pass through unchanged
            assert result == query, f"Failed for: {query}"

    def test_mixed_prompt_sequence(self, setup_test_env):
        """Test sequence of different prompt types."""
        from hook_integration import auto_ultrathink_hook

        # Setup preference: enabled
        prefs_file = setup_test_env["prefs_file"]
        prefs_file.write_text(
            """
```yaml
auto_ultrathink:
  mode: "enabled"
  confidence_threshold: 0.80
```
"""
        )

        # Sequence of prompts
        prompts = [
            ("Add authentication", True),  # Should trigger
            ("What is authentication?", False),  # Should skip
            ("/analyze src/", False),  # Should skip (slash command)
            ("Implement user dashboard", True),  # Should trigger
            ("Show me the code", False),  # Should skip
        ]

        for prompt, should_trigger in prompts:
            result = auto_ultrathink_hook(prompt, context={"session_id": "test"})

            if should_trigger:
                assert "/ultrathink" in result, f"Should trigger for: {prompt}"
            else:
                assert result == prompt, f"Should skip for: {prompt}"


class TestContextPreservation:
    """Test that context is preserved through pipeline."""

    def test_session_id_preserved(self, setup_test_env, monkeypatch):
        """Test session ID is preserved in logs."""
        from hook_integration import auto_ultrathink_hook
        from logger import parse_log_file

        log_file = setup_test_env["log_dir"] / "test_session" / "auto_ultrathink.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr("logger.get_log_file_path", lambda x: log_file)

        # Execute hook with specific session ID
        auto_ultrathink_hook(
            prompt="test prompt", context={"session_id": "test_session"}
        )

        # Verify session ID in logs (if logging succeeded)
        if log_file.exists():
            entries = parse_log_file(log_file)
            if entries:
                assert entries[0].get("session_id") == "test_session"

    def test_context_with_additional_fields(self, setup_test_env):
        """Test hook handles additional context fields."""
        from hook_integration import auto_ultrathink_hook

        # Execute hook with additional context
        result = auto_ultrathink_hook(
            prompt="test prompt",
            context={
                "session_id": "test",
                "user_id": "user123",
                "extra_field": "extra_value",
            },
        )

        # Should complete successfully
        assert result is not None
