"""
Claude Agent SDK Integration Package

Provides integration components for connecting with Claude Agent SDK
for persistent conversation analysis and auto-mode functionality.
"""

from .analysis_engine import (
    AnalysisConfig,
    AnalysisError,
    AnalysisRequest,
    AnalysisResult,
    AnalysisType,
    ConversationAnalysisEngine,
    SDKConnectionError,
)
from .error_handling import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    ErrorHandlingManager,
    ErrorSeverity,
    MaxRetriesExceededError,
    RecoveryStrategy,
    RetryConfig,
    SecurityValidator,
    SecurityViolationError,
    with_retry,
)
from .prompt_coordinator import (
    PromptContext,
    PromptCoordinator,
    PromptTemplate,
    PromptType,
    PromptValidationError,
    RenderedPrompt,
    TemplateRenderError,
)
from .session_manager import (
    AuthenticationError,
    ConversationMessage,
    SDKSessionManager,
    SessionConfig,
    SessionRecoveryError,
    SessionState,
)
from .state_integration import (
    AutoModeConfig,
    AutoModeOrchestrator,
    AutoModeState,
    ProgressMilestone,
    StateIntegrationError,
    StateSnapshot,
)

__all__ = [
    # Session Management
    "SDKSessionManager",
    "SessionConfig",
    "SessionState",
    "ConversationMessage",
    "SessionRecoveryError",
    "AuthenticationError",
    # Analysis Engine
    "ConversationAnalysisEngine",
    "AnalysisConfig",
    "AnalysisType",
    "AnalysisRequest",
    "AnalysisResult",
    "SDKConnectionError",
    "AnalysisError",
    # Prompt Coordination
    "PromptCoordinator",
    "PromptTemplate",
    "PromptType",
    "PromptContext",
    "RenderedPrompt",
    "TemplateRenderError",
    "PromptValidationError",
    # State Integration
    "AutoModeOrchestrator",
    "AutoModeConfig",
    "AutoModeState",
    "StateSnapshot",
    "ProgressMilestone",
    "StateIntegrationError",
    # Error Handling
    "ErrorHandlingManager",
    "CircuitBreaker",
    "RetryConfig",
    "ErrorSeverity",
    "RecoveryStrategy",
    "SecurityValidator",
    "SecurityViolationError",
    "CircuitBreakerOpenError",
    "MaxRetriesExceededError",
    "with_retry",
]
