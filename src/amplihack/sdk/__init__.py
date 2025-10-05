"""
Claude Agent SDK Integration Package

Provides integration components for connecting with Claude Agent SDK
for persistent conversation analysis and auto-mode functionality.
"""

from .session_manager import (
    SDKSessionManager,
    SessionConfig,
    SessionState,
    ConversationMessage,
    SessionRecoveryError,
    AuthenticationError
)

from .analysis_engine import (
    ConversationAnalysisEngine,
    AnalysisConfig,
    AnalysisType,
    AnalysisRequest,
    AnalysisResult,
    SDKConnectionError,
    AnalysisError
)

from .prompt_coordinator import (
    PromptCoordinator,
    PromptTemplate,
    PromptType,
    PromptContext,
    RenderedPrompt,
    TemplateRenderError,
    PromptValidationError
)

from .state_integration import (
    AutoModeOrchestrator,
    AutoModeConfig,
    AutoModeState,
    StateSnapshot,
    ProgressMilestone,
    StateIntegrationError
)

from .error_handling import (
    ErrorHandlingManager,
    CircuitBreaker,
    RetryConfig,
    ErrorSeverity,
    RecoveryStrategy,
    SecurityValidator,
    SecurityViolationError,
    CircuitBreakerOpenError,
    MaxRetriesExceededError,
    with_retry
)

__all__ = [
    # Session Management
    'SDKSessionManager',
    'SessionConfig',
    'SessionState',
    'ConversationMessage',
    'SessionRecoveryError',
    'AuthenticationError',

    # Analysis Engine
    'ConversationAnalysisEngine',
    'AnalysisConfig',
    'AnalysisType',
    'AnalysisRequest',
    'AnalysisResult',
    'SDKConnectionError',
    'AnalysisError',

    # Prompt Coordination
    'PromptCoordinator',
    'PromptTemplate',
    'PromptType',
    'PromptContext',
    'RenderedPrompt',
    'TemplateRenderError',
    'PromptValidationError',

    # State Integration
    'AutoModeOrchestrator',
    'AutoModeConfig',
    'AutoModeState',
    'StateSnapshot',
    'ProgressMilestone',
    'StateIntegrationError',

    # Error Handling
    'ErrorHandlingManager',
    'CircuitBreaker',
    'RetryConfig',
    'ErrorSeverity',
    'RecoveryStrategy',
    'SecurityValidator',
    'SecurityViolationError',
    'CircuitBreakerOpenError',
    'MaxRetriesExceededError',
    'with_retry'
]