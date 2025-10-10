# Auto-Mode Command

Auto-mode provides persistent analysis and autonomous progression through objectives using the Claude Agent SDK for real-time conversation analysis.

## Purpose

Auto-mode monitors Claude Code sessions, analyzes progress toward user objectives, and automatically generates next prompts to maintain momentum and ensure completion of complex tasks.

## Command Usage

```
/amplihack:auto-mode <command> [options]
```

### Commands

**Start Auto-Mode Session:**

```
/amplihack:auto-mode start "Objective description" [--working-dir /path] [--max-iterations 50]
```

**Process Claude Output:**

```
/amplihack:auto-mode process "Claude output text" [--session-id <id>]
```

**Check Progress:**

```
/amplihack:auto-mode status [--session-id <id>]
```

**Pause/Resume:**

```
/amplihack:auto-mode pause [--session-id <id>]
/amplihack:auto-mode resume [--session-id <id>]
```

**Stop Session:**

```
/amplihack:auto-mode stop [--session-id <id>]
```

## Examples

### Starting Auto-Mode

```
/amplihack:auto-mode start "Build a REST API with authentication, user management, and data persistence"
```

### Processing Progress

When Claude Code produces output, auto-mode analyzes it:

```
/amplihack:auto-mode process "I've implemented the authentication system with JWT tokens and password hashing."
```

Auto-mode will:

1. Analyze the progress toward the objective
2. Evaluate code quality and completeness
3. Generate the next logical prompt
4. Provide confidence scores and recommendations

### Checking Status

```
/amplihack:auto-mode status
```

Returns:

- Current iteration and progress percentage
- Confidence in current approach
- Milestones achieved
- Next recommended actions
- Session health metrics

## Core Features

### Real-Time Analysis

- **Progress Evaluation**: Measures advancement toward objectives
- **Quality Assessment**: Reviews code quality and best practices
- **Next Prompt Generation**: Creates specific, actionable next steps
- **Error Diagnosis**: Identifies and suggests fixes for issues
- **Objective Alignment**: Ensures work stays focused on goals

### Intelligent Prompt Templates

- **Objective Clarification**: When goals are unclear
- **Progress Assessment**: Regular progress check-ins
- **Next Action**: Specific implementation steps
- **Error Resolution**: Debugging and problem-solving
- **Quality Review**: Code review and improvement

### Session Management

- **Persistent State**: Sessions survive restarts
- **Conversation History**: Full context preservation
- **Milestone Tracking**: Progress checkpoint recording
- **Error Recovery**: Graceful handling of failures
- **Resource Management**: Automatic cleanup and optimization

### Error Handling & Security

- **Circuit Breakers**: Protect against cascade failures
- **Retry Logic**: Automatic recovery from transient errors
- **Security Validation**: Input sanitization and threat detection
- **Rate Limiting**: Prevent abuse and resource exhaustion

## Configuration

### Auto-Mode Config

```python
AutoModeConfig(
    max_iterations=50,              # Maximum analysis iterations
    iteration_timeout_seconds=300,  # Timeout per iteration
    min_confidence_threshold=0.6,   # Minimum confidence to continue
    auto_progression_enabled=True,  # DEFAULT: Enables automatic progression (the core purpose of auto-mode)
    persistence_enabled=True,       # Session state persistence
    state_sync_interval_seconds=30  # Background sync frequency
)
```

**Note**: `auto_progression_enabled=True` is the default and core behavior - disabling it defeats the purpose of auto-mode.

### Analysis Engine Config

```python
AnalysisConfig(
    batch_size=10,                  # Entries per SDK call
    max_analysis_length=8000,       # Max chars to analyze
    confidence_threshold=0.6,       # Minimum result confidence
    enable_caching=True,            # Cache analysis results
    analysis_timeout_seconds=60     # SDK call timeout
)
```

## Integration Points

### Claude Agent SDK

- Uses `mcp__ide__executeCode` for real AI analysis
- Persistent conversation management
- Session recovery and state synchronization
- Secure authentication and error handling

### Workflow Integration

- Follows DEFAULT_WORKFLOW.md steps automatically
- Coordinates with amplihack agents at each stage
- Maintains compliance with project philosophy
- Integrates with existing slash commands

### TDD Integration

- Monitors test implementation progress
- Ensures test-first development practices
- Validates test coverage and quality
- Suggests additional test scenarios

## Output Format

### Progress Analysis

```json
{
  "iteration": 5,
  "confidence": 0.85,
  "progress_percentage": 60,
  "findings": [
    "Authentication system implemented successfully",
    "Database schema needs optimization",
    "Missing input validation in user endpoints"
  ],
  "recommendations": [
    "Add comprehensive input validation",
    "Optimize database queries for user lookup",
    "Implement rate limiting for auth endpoints"
  ],
  "next_prompt": "Please add input validation to the user management endpoints with proper error handling and security checks.",
  "quality_score": 0.78,
  "milestones_achieved": 3,
  "estimated_completion": "70%"
}
```

### Session Status

```json
{
  "session_id": "uuid-here",
  "state": "active",
  "current_iteration": 12,
  "total_iterations": 50,
  "objective": "Build a REST API...",
  "working_directory": "/project",
  "uptime": "45 minutes",
  "milestones": [
    {
      "iteration": 5,
      "description": "Authentication system completed",
      "confidence": 0.9,
      "timestamp": "2025-01-15T10:30:00Z"
    }
  ],
  "error_count": 0,
  "last_analysis": {
    "confidence": 0.85,
    "quality_score": 0.78,
    "timestamp": "2025-01-15T10:45:00Z"
  }
}
```

## Best Practices

### Effective Objectives

- **Specific**: Clear, detailed requirements
- **Measurable**: Observable completion criteria
- **Achievable**: Realistic scope and timeline
- **Relevant**: Aligned with project goals
- **Time-bound**: Defined completion expectations

### Monitoring Progress

- Check status regularly during development
- Review milestone achievements for quality
- Monitor confidence scores for potential issues
- Use error analysis for improvement opportunities

### Troubleshooting

- Low confidence scores may indicate unclear objectives
- High error counts suggest environmental issues
- Slow progress might need objective refinement
- Quality issues may require architecture review

## Implementation Details

### Real AI Analysis

Auto-mode uses the Claude Agent SDK to perform genuine AI analysis of Claude Code output. This is not pattern matching or simulation - it's real Claude AI understanding context, evaluating progress, and making informed recommendations.

### Security & Reliability

- All inputs are validated and sanitized
- Circuit breakers prevent cascade failures
- Retry logic handles transient errors
- Session state is persisted securely
- Rate limiting prevents abuse

### Performance Optimization

- Analysis results are cached intelligently
- Batch processing reduces SDK calls
- Background tasks handle maintenance
- Resource cleanup prevents memory leaks

---

**Note**: Auto-mode requires Claude Agent SDK access via `mcp__ide__executeCode`. Ensure proper authentication and network connectivity for optimal operation.
