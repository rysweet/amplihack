# Auto-Mode Slash Command

## Command Definition
`/auto-mode [action] [parameters...]`

## Description
The `/auto-mode` command provides control and interaction with the Auto-Mode feature, which enables persistent conversation analysis and improvement suggestions using the Claude Agent SDK.

## Actions

### `start` - Start Auto-Mode Session
```bash
/auto-mode start [--config CONFIG_NAME] [--user-id USER_ID]
```

Starts a new auto-mode session with persistent analysis capabilities.

**Parameters:**
- `--config CONFIG_NAME`: Use specific configuration preset (optional)
- `--user-id USER_ID`: Specify user identifier (optional, auto-detected if not provided)

**Examples:**
```bash
/auto-mode start
/auto-mode start --config aggressive_analysis
/auto-mode start --user-id dev_user_123 --config learning_mode
```

### `status` - Check Auto-Mode Status
```bash
/auto-mode status [--detailed] [--session-id SESSION_ID]
```

Shows current auto-mode status, active sessions, and metrics.

**Parameters:**
- `--detailed`: Show detailed analysis and quality metrics
- `--session-id SESSION_ID`: Show status for specific session

**Examples:**
```bash
/auto-mode status
/auto-mode status --detailed
/auto-mode status --session-id abc123-def456
```

### `stop` - Stop Auto-Mode Session
```bash
/auto-mode stop [--session-id SESSION_ID] [--save-insights]
```

Stops an active auto-mode session.

**Parameters:**
- `--session-id SESSION_ID`: Specific session to stop (optional, stops current if not provided)
- `--save-insights`: Save learned insights for future sessions

**Examples:**
```bash
/auto-mode stop
/auto-mode stop --session-id abc123-def456 --save-insights
```

### `configure` - Configure Auto-Mode Settings
```bash
/auto-mode configure [SETTING] [VALUE] [--session-id SESSION_ID]
```

Configure auto-mode behavior and preferences.

**Available Settings:**
- `analysis_frequency`: How often to perform analysis (`low`, `normal`, `high`, `adaptive`)
- `intervention_threshold`: Confidence threshold for suggestions (`0.0` - `1.0`)
- `background_mode`: Enable/disable background analysis (`true`, `false`)
- `learning_mode`: Enable/disable user preference learning (`true`, `false`)
- `privacy_level`: Privacy protection level (`strict`, `balanced`, `permissive`)

**Examples:**
```bash
/auto-mode configure analysis_frequency adaptive
/auto-mode configure intervention_threshold 0.8
/auto-mode configure background_mode false
```

### `analyze` - Request Manual Analysis
```bash
/auto-mode analyze [--type TYPE] [--scope SCOPE] [--output FORMAT]
```

Request immediate conversation analysis.

**Parameters:**
- `--type TYPE`: Analysis type (`quick`, `comprehensive`, `quality`, `patterns`)
- `--scope SCOPE`: Analysis scope (`current`, `session`, `recent`)
- `--output FORMAT`: Output format (`summary`, `detailed`, `json`)

**Examples:**
```bash
/auto-mode analyze
/auto-mode analyze --type comprehensive --output detailed
/auto-mode analyze --type quality --scope current
```

### `insights` - View Learning Insights
```bash
/auto-mode insights [--category CATEGORY] [--export FORMAT]
```

View learned insights and patterns.

**Parameters:**
- `--category CATEGORY`: Filter by category (`preferences`, `patterns`, `optimizations`)
- `--export FORMAT`: Export format (`text`, `json`, `markdown`)

**Examples:**
```bash
/auto-mode insights
/auto-mode insights --category preferences
/auto-mode insights --category patterns --export json
```

### `feedback` - Provide Feedback
```bash
/auto-mode feedback [--rating RATING] [--comment "COMMENT"] [--suggestion-id ID]
```

Provide feedback on auto-mode suggestions and behavior.

**Parameters:**
- `--rating RATING`: Rating from 1-5
- `--comment "COMMENT"`: Detailed feedback comment
- `--suggestion-id ID`: Feedback on specific suggestion

**Examples:**
```bash
/auto-mode feedback --rating 4 --comment "Helpful suggestions but too frequent"
/auto-mode feedback --suggestion-id sugg_123 --rating 5
```

### `summary` - Generate Session Summary
```bash
/auto-mode summary [--format FORMAT] [--include SECTIONS]
```

Generate a summary of the current session with insights and recommendations.

**Parameters:**
- `--format FORMAT`: Output format (`brief`, `detailed`, `report`)
- `--include SECTIONS`: Sections to include (`analysis`, `insights`, `recommendations`, `metrics`)

**Examples:**
```bash
/auto-mode summary
/auto-mode summary --format detailed --include analysis,insights
```

### `help` - Show Help Information
```bash
/auto-mode help [COMMAND]
```

Show help information for auto-mode commands.

**Examples:**
```bash
/auto-mode help
/auto-mode help start
/auto-mode help configure
```

## Configuration Presets

### `default`
- Analysis frequency: adaptive
- Intervention threshold: 0.7
- Background mode: enabled
- Learning mode: enabled
- Privacy level: balanced

### `aggressive_analysis`
- Analysis frequency: high
- Intervention threshold: 0.5
- Background mode: enabled
- Learning mode: enabled
- Privacy level: balanced

### `minimal_intervention`
- Analysis frequency: low
- Intervention threshold: 0.9
- Background mode: enabled
- Learning mode: enabled
- Privacy level: strict

### `learning_mode`
- Analysis frequency: adaptive
- Intervention threshold: 0.6
- Background mode: enabled
- Learning mode: enabled
- Privacy level: balanced
- Focus on educational suggestions

### `privacy_focused`
- Analysis frequency: normal
- Intervention threshold: 0.8
- Background mode: disabled
- Learning mode: disabled
- Privacy level: strict

## Response Formats

### Status Response
```json
{
  "auto_mode_status": "active|inactive|paused",
  "session_id": "abc123-def456",
  "uptime": "15m 30s",
  "analysis_cycles": 12,
  "current_quality_score": 0.78,
  "active_interventions": 2,
  "sdk_connection": "connected|disconnected|error"
}
```

### Analysis Response
```json
{
  "analysis_timestamp": "2025-01-14T10:30:00Z",
  "quality_score": 0.78,
  "quality_dimensions": {
    "clarity": 0.85,
    "effectiveness": 0.72,
    "engagement": 0.80
  },
  "detected_patterns": ["systematic_approach", "learning_focused"],
  "improvement_opportunities": [
    {
      "area": "efficiency",
      "priority": "medium",
      "suggestion": "Consider batching similar operations"
    }
  ],
  "satisfaction_signals": {
    "overall": "positive",
    "confidence": 0.82
  }
}
```

### Insights Response
```json
{
  "user_preferences": {
    "communication_style": "technical",
    "detail_level": "high",
    "preferred_tools": ["bash", "edit", "read"]
  },
  "learned_patterns": [
    {
      "pattern": "prefers_systematic_implementation",
      "confidence": 0.9,
      "evidence_count": 5
    }
  ],
  "optimizations": [
    {
      "area": "workflow",
      "suggestion": "Use multi-tool calls for parallel operations",
      "impact": "high"
    }
  ]
}
```

## Error Handling

### Common Errors
- `auto_mode_not_initialized`: Auto-mode system not initialized
- `session_not_found`: Specified session ID not found
- `invalid_configuration`: Invalid configuration parameter
- `sdk_connection_error`: Claude Agent SDK connection issues
- `permission_denied`: Insufficient permissions for operation

### Error Response Format
```json
{
  "error": "session_not_found",
  "message": "Session abc123-def456 not found",
  "suggestion": "Use '/auto-mode status' to see active sessions",
  "recovery_options": ["start_new_session", "check_session_list"]
}
```

## Integration Notes

### Claude Code Integration
- Command is automatically registered with Claude Code command system
- Supports both interactive and non-interactive execution
- Integrates with existing session management
- Respects user preferences and privacy settings

### Security Considerations
- All user data is handled according to privacy level settings
- Session isolation between different users
- Audit logging for all auto-mode operations
- Secure storage of learned insights and preferences

### Performance Considerations
- Background analysis is designed to be non-intrusive
- Adaptive analysis frequency based on conversation activity
- Efficient caching of analysis results
- Graceful degradation when SDK is unavailable