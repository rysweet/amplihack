"""
Test suite for AutoModeCommandHandler.

Tests the /auto-mode slash command functionality including:
- Command parsing and validation
- Action routing and execution
- Parameter handling and validation
- Error handling and recovery
- Integration with orchestrator
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from amplihack.auto_mode.command_handler import (
    AutoModeCommandHandler,
    CommandResult
)
from amplihack.auto_mode.orchestrator import AutoModeOrchestrator, OrchestratorConfig


class TestCommandParsing:
    """Test command argument parsing"""

    @pytest.fixture
    def handler(self):
        return AutoModeCommandHandler()

    def test_parse_simple_action(self, handler):
        """Test parsing simple action command"""
        args = handler._parse_args("start")

        assert args['action'] == 'start'

    def test_parse_action_with_long_options(self, handler):
        """Test parsing action with long options"""
        args = handler._parse_args("start --config learning_mode --user-id test_user")

        assert args['action'] == 'start'
        assert args['config'] == 'learning_mode'
        assert args['user-id'] == 'test_user'

    def test_parse_action_with_boolean_options(self, handler):
        """Test parsing action with boolean options"""
        args = handler._parse_args("status --detailed")

        assert args['action'] == 'status'
        assert args['detailed'] is True

    def test_parse_action_with_positional_args(self, handler):
        """Test parsing action with positional arguments"""
        args = handler._parse_args("configure analysis_frequency adaptive")

        assert args['action'] == 'configure'
        assert args['positional'] == ['analysis_frequency', 'adaptive']

    def test_parse_complex_command(self, handler):
        """Test parsing complex command with mixed arguments"""
        args = handler._parse_args('analyze --type comprehensive --output json --scope current')

        assert args['action'] == 'analyze'
        assert args['type'] == 'comprehensive'
        assert args['output'] == 'json'
        assert args['scope'] == 'current'

    def test_parse_quoted_arguments(self, handler):
        """Test parsing arguments with quotes"""
        args = handler._parse_args('feedback --comment "This is helpful but too frequent"')

        assert args['action'] == 'feedback'
        assert args['comment'] == "This is helpful but too frequent"

    def test_parse_empty_command(self, handler):
        """Test parsing empty command defaults to help"""
        args = handler._parse_args("")

        assert args['action'] == 'help'

    def test_parse_invalid_command(self, handler):
        """Test parsing invalid command syntax"""
        # Should not raise exception, returns None
        args = handler._parse_args("start --invalid-syntax 'unclosed quote")

        # Parser should handle gracefully
        assert args is None or 'action' in args


class TestStartCommand:
    """Test 'start' command functionality"""

    @pytest.fixture
    def handler(self):
        return AutoModeCommandHandler()

    @pytest.mark.asyncio
    async def test_start_command_success(self, handler):
        """Test successful start command execution"""
        # Mock orchestrator initialization and session creation
        mock_orchestrator = AsyncMock(spec=AutoModeOrchestrator)
        mock_orchestrator.initialize.return_value = True
        mock_orchestrator.start_session.return_value = "test_session_123"

        with patch('amplihack.auto_mode.command_handler.AutoModeOrchestrator', return_value=mock_orchestrator):
            result = await handler._handle_start(
                args={'action': 'start', 'config': 'default'},
                context={'user_id': 'test_user', 'conversation_context': {}}
            )

        assert result.success is True
        assert 'session_id' in result.data
        assert result.data['session_id'] == "test_session_123"
        assert result.data['user_id'] == 'test_user'

    @pytest.mark.asyncio
    async def test_start_command_initialization_failure(self, handler):
        """Test start command with orchestrator initialization failure"""
        mock_orchestrator = AsyncMock(spec=AutoModeOrchestrator)
        mock_orchestrator.initialize.return_value = False

        with patch('amplihack.auto_mode.command_handler.AutoModeOrchestrator', return_value=mock_orchestrator):
            result = await handler._handle_start(
                args={'action': 'start'},
                context={'user_id': 'test_user'}
            )

        assert result.success is False
        assert result.error_code == "initialization_failed"

    @pytest.mark.asyncio
    async def test_start_command_with_custom_config(self, handler):
        """Test start command with custom configuration"""
        mock_orchestrator = AsyncMock(spec=AutoModeOrchestrator)
        mock_orchestrator.initialize.return_value = True
        mock_orchestrator.start_session.return_value = "test_session_123"

        with patch('amplihack.auto_mode.command_handler.AutoModeOrchestrator', return_value=mock_orchestrator):
            result = await handler._handle_start(
                args={'action': 'start', 'config': 'aggressive_analysis', 'user-id': 'custom_user'},
                context={'conversation_context': {}}
            )

        assert result.success is True
        assert result.data['config'] == 'aggressive_analysis'
        assert result.data['user_id'] == 'custom_user'

    @pytest.mark.asyncio
    async def test_start_command_exception_handling(self, handler):
        """Test start command exception handling"""
        mock_orchestrator = AsyncMock(spec=AutoModeOrchestrator)
        mock_orchestrator.initialize.side_effect = Exception("Test exception")

        with patch('amplihack.auto_mode.command_handler.AutoModeOrchestrator', return_value=mock_orchestrator):
            result = await handler._handle_start(
                args={'action': 'start'},
                context={'user_id': 'test_user'}
            )

        assert result.success is False
        assert result.error_code == "start_failed"
        assert "Test exception" in result.message


class TestStopCommand:
    """Test 'stop' command functionality"""

    @pytest.fixture
    def handler_with_orchestrator(self):
        handler = AutoModeCommandHandler()
        handler.orchestrator = AsyncMock(spec=AutoModeOrchestrator)
        return handler

    @pytest.mark.asyncio
    async def test_stop_specific_session(self, handler_with_orchestrator):
        """Test stopping specific session"""
        handler = handler_with_orchestrator
        handler.orchestrator.stop_session.return_value = True

        result = await handler._handle_stop(
            args={'action': 'stop', 'session-id': 'test_session_123'},
            context={'user_id': 'test_user'}
        )

        assert result.success is True
        assert result.data['session_id'] == 'test_session_123'
        handler.orchestrator.stop_session.assert_called_once_with('test_session_123')

    @pytest.mark.asyncio
    async def test_stop_all_user_sessions(self, handler_with_orchestrator):
        """Test stopping all sessions for a user"""
        handler = handler_with_orchestrator

        # Mock active sessions
        from amplihack.auto_mode.session import SessionState
        mock_session1 = SessionState(session_id="session1", user_id="test_user")
        mock_session2 = SessionState(session_id="session2", user_id="test_user")
        mock_session3 = SessionState(session_id="session3", user_id="other_user")

        handler.orchestrator.active_sessions = {
            "session1": mock_session1,
            "session2": mock_session2,
            "session3": mock_session3
        }
        handler.orchestrator.stop_session.return_value = True

        result = await handler._handle_stop(
            args={'action': 'stop'},
            context={'user_id': 'test_user'}
        )

        assert result.success is True
        assert result.data['stopped_sessions'] == 2
        assert handler.orchestrator.stop_session.call_count == 2

    @pytest.mark.asyncio
    async def test_stop_no_orchestrator(self, handler_with_orchestrator):
        """Test stop command when orchestrator is not running"""
        handler = AutoModeCommandHandler()  # No orchestrator

        result = await handler._handle_stop(
            args={'action': 'stop'},
            context={'user_id': 'test_user'}
        )

        assert result.success is False
        assert result.error_code == "not_running"

    @pytest.mark.asyncio
    async def test_stop_nonexistent_session(self, handler_with_orchestrator):
        """Test stopping non-existent session"""
        handler = handler_with_orchestrator
        handler.orchestrator.stop_session.return_value = False

        result = await handler._handle_stop(
            args={'action': 'stop', 'session-id': 'nonexistent'},
            context={'user_id': 'test_user'}
        )

        assert result.success is False
        assert result.error_code == "stop_failed"


class TestStatusCommand:
    """Test 'status' command functionality"""

    @pytest.fixture
    def handler_with_orchestrator(self):
        handler = AutoModeCommandHandler()
        handler.orchestrator = AsyncMock(spec=AutoModeOrchestrator)
        return handler

    @pytest.mark.asyncio
    async def test_status_general(self, handler_with_orchestrator):
        """Test general status command"""
        handler = handler_with_orchestrator
        handler.orchestrator.state.value = "active"
        handler.orchestrator.active_sessions = {"session1": Mock(), "session2": Mock()}
        handler.orchestrator.get_metrics.return_value = {
            'total_sessions': 5,
            'total_analysis_cycles': 50,
            'total_interventions': 10,
            'average_quality_score': 0.75,
            'uptime_seconds': 3600
        }
        handler.orchestrator.sdk_client.get_connection_status.return_value = {
            'connection_state': 'connected'
        }

        result = await handler._handle_status(
            args={'action': 'status'},
            context={'user_id': 'test_user'}
        )

        assert result.success is True
        assert result.data['status'] == 'active'
        assert result.data['active_sessions'] == 2
        assert result.data['total_sessions'] == 5
        assert result.data['sdk_connection'] == 'connected'

    @pytest.mark.asyncio
    async def test_status_detailed(self, handler_with_orchestrator):
        """Test detailed status command"""
        handler = handler_with_orchestrator
        handler.orchestrator.state.value = "active"
        handler.orchestrator.active_sessions = {"session1": Mock()}
        handler.orchestrator.get_metrics.return_value = {'total_sessions': 1}
        handler.orchestrator.sdk_client.get_connection_status.return_value = {'connection_state': 'connected'}
        handler.orchestrator.get_session_status.return_value = {
            'session_id': 'session1',
            'status': 'active'
        }

        result = await handler._handle_status(
            args={'action': 'status', 'detailed': True},
            context={'user_id': 'test_user'}
        )

        assert result.success is True
        assert 'detailed_metrics' in result.data
        assert 'sdk_status' in result.data
        assert 'active_session_details' in result.data

    @pytest.mark.asyncio
    async def test_status_specific_session(self, handler_with_orchestrator):
        """Test status for specific session"""
        handler = handler_with_orchestrator
        handler.orchestrator.get_session_status.return_value = {
            'session_id': 'test_session',
            'user_id': 'test_user',
            'status': 'active'
        }

        result = await handler._handle_status(
            args={'action': 'status', 'session-id': 'test_session'},
            context={'user_id': 'test_user'}
        )

        assert result.success is True
        assert result.data['session_id'] == 'test_session'

    @pytest.mark.asyncio
    async def test_status_nonexistent_session(self, handler_with_orchestrator):
        """Test status for non-existent session"""
        handler = handler_with_orchestrator
        handler.orchestrator.get_session_status.return_value = None

        result = await handler._handle_status(
            args={'action': 'status', 'session-id': 'nonexistent'},
            context={'user_id': 'test_user'}
        )

        assert result.success is False
        assert result.error_code == "session_not_found"

    @pytest.mark.asyncio
    async def test_status_no_orchestrator(self):
        """Test status when orchestrator is not running"""
        handler = AutoModeCommandHandler()  # No orchestrator

        result = await handler._handle_status(
            args={'action': 'status'},
            context={'user_id': 'test_user'}
        )

        assert result.success is True
        assert result.data['status'] == 'inactive'
        assert result.data['active_sessions'] == 0


class TestConfigureCommand:
    """Test 'configure' command functionality"""

    @pytest.fixture
    def handler_with_orchestrator(self):
        handler = AutoModeCommandHandler()
        handler.orchestrator = Mock(spec=AutoModeOrchestrator)
        handler.orchestrator.config = OrchestratorConfig()
        return handler

    @pytest.mark.asyncio
    async def test_configure_show_current(self, handler_with_orchestrator):
        """Test showing current configuration"""
        handler = handler_with_orchestrator

        result = await handler._handle_configure(
            args={'action': 'configure'},
            context={'user_id': 'test_user'}
        )

        assert result.success is True
        assert 'analysis_frequency' in result.data
        assert 'intervention_threshold' in result.data
        assert 'background_mode' in result.data

    @pytest.mark.asyncio
    async def test_configure_analysis_frequency(self, handler_with_orchestrator):
        """Test configuring analysis frequency"""
        handler = handler_with_orchestrator

        result = await handler._handle_configure(
            args={'action': 'configure', 'positional': ['analysis_frequency', 'high']},
            context={'user_id': 'test_user'}
        )

        assert result.success is True
        assert handler.orchestrator.config.analysis_interval_seconds == 15.0

    @pytest.mark.asyncio
    async def test_configure_intervention_threshold(self, handler_with_orchestrator):
        """Test configuring intervention threshold"""
        handler = handler_with_orchestrator

        result = await handler._handle_configure(
            args={'action': 'configure', 'positional': ['intervention_threshold', '0.8']},
            context={'user_id': 'test_user'}
        )

        assert result.success is True
        assert handler.orchestrator.config.intervention_confidence_threshold == 0.8

    @pytest.mark.asyncio
    async def test_configure_boolean_setting(self, handler_with_orchestrator):
        """Test configuring boolean setting"""
        handler = handler_with_orchestrator

        result = await handler._handle_configure(
            args={'action': 'configure', 'positional': ['background_mode', 'false']},
            context={'user_id': 'test_user'}
        )

        assert result.success is True
        assert handler.orchestrator.config.background_analysis_enabled is False

    @pytest.mark.asyncio
    async def test_configure_invalid_setting(self, handler_with_orchestrator):
        """Test configuring invalid setting"""
        handler = handler_with_orchestrator

        result = await handler._handle_configure(
            args={'action': 'configure', 'positional': ['invalid_setting', 'value']},
            context={'user_id': 'test_user'}
        )

        assert result.success is False
        assert result.error_code == "config_failed"

    @pytest.mark.asyncio
    async def test_configure_missing_value(self, handler_with_orchestrator):
        """Test configure command with missing value"""
        handler = handler_with_orchestrator

        result = await handler._handle_configure(
            args={'action': 'configure', 'positional': ['analysis_frequency']},
            context={'user_id': 'test_user'}
        )

        assert result.success is False
        assert result.error_code == "missing_value"

    @pytest.mark.asyncio
    async def test_configure_no_orchestrator(self):
        """Test configure when orchestrator is not running"""
        handler = AutoModeCommandHandler()  # No orchestrator

        result = await handler._handle_configure(
            args={'action': 'configure'},
            context={'user_id': 'test_user'}
        )

        assert result.success is False
        assert result.error_code == "not_running"


class TestAnalyzeCommand:
    """Test 'analyze' command functionality"""

    @pytest.fixture
    def handler_with_orchestrator(self):
        handler = AutoModeCommandHandler()
        handler.orchestrator = AsyncMock(spec=AutoModeOrchestrator)
        return handler

    @pytest.mark.asyncio
    async def test_analyze_command_success(self, handler_with_orchestrator):
        """Test successful analyze command"""
        handler = handler_with_orchestrator

        # Mock active session
        from amplihack.auto_mode.session import SessionState
        from amplihack.auto_mode.analysis import ConversationAnalysis

        mock_session = SessionState(session_id="test_session", user_id="test_user")
        handler.orchestrator.active_sessions = {"test_session": mock_session}

        mock_analysis = ConversationAnalysis(
            quality_score=0.8,
            conversation_length=10
        )
        handler.orchestrator.analysis_engine.analyze_conversation.return_value = mock_analysis

        result = await handler._handle_analyze(
            args={'action': 'analyze', 'type': 'comprehensive', 'output': 'summary'},
            context={'user_id': 'test_user'}
        )

        assert result.success is True
        assert "Quality: 0.80/1.0" in result.message

    @pytest.mark.asyncio
    async def test_analyze_json_output(self, handler_with_orchestrator):
        """Test analyze command with JSON output"""
        handler = handler_with_orchestrator

        from amplihack.auto_mode.session import SessionState
        from amplihack.auto_mode.analysis import ConversationAnalysis

        mock_session = SessionState(session_id="test_session", user_id="test_user")
        handler.orchestrator.active_sessions = {"test_session": mock_session}

        mock_analysis = ConversationAnalysis(quality_score=0.75)
        handler.orchestrator.analysis_engine.analyze_conversation.return_value = mock_analysis

        result = await handler._handle_analyze(
            args={'action': 'analyze', 'output': 'json'},
            context={'user_id': 'test_user'}
        )

        assert result.success is True
        assert 'quality_score' in result.data
        assert result.data['quality_score'] == 0.75

    @pytest.mark.asyncio
    async def test_analyze_no_active_session(self, handler_with_orchestrator):
        """Test analyze command with no active session"""
        handler = handler_with_orchestrator
        handler.orchestrator.active_sessions = {}

        result = await handler._handle_analyze(
            args={'action': 'analyze'},
            context={'user_id': 'test_user'}
        )

        assert result.success is False
        assert result.error_code == "no_session"


class TestHelpCommand:
    """Test 'help' command functionality"""

    @pytest.fixture
    def handler(self):
        return AutoModeCommandHandler()

    @pytest.mark.asyncio
    async def test_general_help(self, handler):
        """Test general help command"""
        result = await handler._handle_help(
            args={'action': 'help'},
            context={'user_id': 'test_user'}
        )

        assert result.success is True
        assert "Auto-Mode Help" in result.message
        assert "Available actions:" in result.message

    @pytest.mark.asyncio
    async def test_specific_command_help(self, handler):
        """Test help for specific command"""
        result = await handler._handle_help(
            args={'action': 'help', 'positional': ['start']},
            context={'user_id': 'test_user'}
        )

        assert result.success is True
        assert "Auto-Mode Start" in result.message
        assert "--config" in result.message

    @pytest.mark.asyncio
    async def test_help_for_unknown_command(self, handler):
        """Test help for unknown command"""
        result = await handler._handle_help(
            args={'action': 'help', 'positional': ['unknown_command']},
            context={'user_id': 'test_user'}
        )

        assert result.success is True
        assert "No help available" in result.message


class TestCommandIntegration:
    """Test overall command handler integration"""

    @pytest.fixture
    def handler(self):
        return AutoModeCommandHandler()

    @pytest.mark.asyncio
    async def test_handle_command_routing(self, handler):
        """Test command routing to appropriate handlers"""
        context = {'user_id': 'test_user'}

        # Test each action routes correctly
        actions_to_test = ['start', 'stop', 'status', 'configure', 'analyze', 'help']

        for action in actions_to_test:
            result = await handler.handle_command(action, context)
            # All should return CommandResult (success or failure)
            assert isinstance(result, CommandResult)

    @pytest.mark.asyncio
    async def test_handle_unknown_action(self, handler):
        """Test handling unknown action"""
        result = await handler.handle_command("unknown_action", {'user_id': 'test_user'})

        assert result.success is False
        assert result.error_code == "unknown_action"

    @pytest.mark.asyncio
    async def test_handle_invalid_syntax(self, handler):
        """Test handling invalid command syntax"""
        result = await handler.handle_command("start --invalid 'unclosed", {'user_id': 'test_user'})

        assert result.success is False
        assert result.error_code == "invalid_syntax"

    @pytest.mark.asyncio
    async def test_command_history_recording(self, handler):
        """Test that commands are recorded in history"""
        context = {'user_id': 'test_user'}

        initial_count = len(handler.command_history)

        await handler.handle_command("help", context)

        assert len(handler.command_history) == initial_count + 1
        assert handler.command_history[-1]['action'] == 'help'
        assert handler.command_history[-1]['user_id'] == 'test_user'

    @pytest.mark.asyncio
    async def test_config_presets_available(self, handler):
        """Test that configuration presets are available"""
        preset_names = ['default', 'aggressive_analysis', 'minimal_intervention', 'learning_mode', 'privacy_focused']

        for preset_name in preset_names:
            assert preset_name in handler.config_presets
            assert isinstance(handler.config_presets[preset_name], OrchestratorConfig)


if __name__ == "__main__":
    pytest.main([__file__])