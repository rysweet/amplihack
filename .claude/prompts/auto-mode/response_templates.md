# Auto-Mode Response Templates

## Template Categories

### 1. Background Analysis Updates
Templates for non-intrusive status updates during ongoing conversations.

#### Template: Silent Analysis
```
🔍 Auto-mode: Background analysis in progress...
Session: {session_id} | Cycle: {analysis_cycle} | Status: {status}
```

#### Template: Analysis Complete
```
✅ Auto-mode: Analysis cycle {cycle_number} completed
Quality Score: {quality_score}/1.0 | Opportunities: {opportunity_count}
[View Details] [Configure] [Disable]
```

### 2. Intervention Suggestions
Templates for suggesting improvements or clarifications.

#### Template: Clarification Suggestion
```
💡 Auto-mode suggests: Consider asking about {specific_area} to improve clarity.
Confidence: {confidence_score} | Impact: {impact_level}
[Apply Suggestion] [Modify] [Dismiss]
```

#### Template: Tool Recommendation
```
🛠️ Auto-mode recommends: Using {tool_name} might help with {specific_task}.
Reasoning: {brief_explanation}
[Use Tool] [Learn More] [Dismiss]
```

#### Template: Workflow Optimization
```
⚡ Auto-mode optimization: This process could be streamlined by {optimization}.
Potential time savings: {estimated_savings}
[Apply Optimization] [Preview] [Dismiss]
```

### 3. Session Summaries
Templates for end-of-session or periodic summaries.

#### Template: Session Summary
```
📊 Auto-mode Session Summary
Duration: {session_duration} | Messages: {message_count}
Goals Achieved: {goals_achieved}/{total_goals}
Quality Score: {overall_quality}/1.0

Key Insights:
{insights_list}

Recommendations for Next Session:
{recommendations_list}

[Detailed Report] [Save Insights] [Configure Auto-mode]
```

#### Template: Progress Report
```
📈 Auto-mode Progress Report
Sessions Analyzed: {session_count}
Average Quality: {avg_quality}/1.0
Top Improvement Areas: {improvement_areas}

Recent Optimizations:
{optimization_list}

[View Trends] [Export Data] [Settings]
```

### 4. User Preference Learning
Templates for capturing and confirming user preferences.

#### Template: Preference Detection
```
🎯 Auto-mode learned: You prefer {preference_type} = {preference_value}
Based on: {evidence_summary}
[Confirm] [Modify] [Ignore] [Don't learn this]
```

#### Template: Style Adaptation
```
🎨 Auto-mode adapted: Communication style adjusted to {style_preference}
Changes: {specific_changes}
[Keep Changes] [Revert] [Fine-tune]
```

### 5. Error Handling and Recovery
Templates for handling issues and recovery scenarios.

#### Template: Analysis Error
```
⚠️ Auto-mode encountered an issue during analysis
Error: {error_type} | Session: {session_id}
Fallback: {fallback_action}
[Retry] [Report Issue] [Disable Auto-mode]
```

#### Template: SDK Connection Issue
```
🔌 Auto-mode: Connection to Claude Agent SDK interrupted
Status: {connection_status} | Retry in: {retry_countdown}
Impact: {impact_description}
[Retry Now] [Work Offline] [Settings]
```

### 6. Configuration and Control
Templates for user control and configuration.

#### Template: Configuration Update
```
⚙️ Auto-mode configuration updated
Changes: {configuration_changes}
Effective: {effective_time}
[Test Configuration] [Revert] [Advanced Settings]
```

#### Template: Permission Request
```
🔐 Auto-mode requests permission: {permission_type}
Purpose: {permission_purpose}
Data Access: {data_scope}
[Grant] [Grant Once] [Deny] [Learn More]
```

## Template Variables

### Standard Variables
- `{session_id}`: Unique session identifier
- `{timestamp}`: Current timestamp
- `{user_id}`: User identifier (if available)
- `{quality_score}`: Conversation quality score (0.0-1.0)
- `{analysis_cycle}`: Current analysis cycle number

### Dynamic Content Variables
- `{insights_list}`: Generated list of insights
- `{recommendations_list}`: Generated recommendations
- `{improvement_areas}`: Identified improvement areas
- `{optimization_list}`: Recent optimizations applied

### User Context Variables
- `{user_preferences}`: Current user preferences
- `{conversation_context}`: Current conversation context
- `{session_history}`: Historical session data
- `{domain_expertise}`: Assessed user expertise level

## Template Usage Guidelines

### Timing
- Background updates: Non-intrusive, minimal UI impact
- Intervention suggestions: Only when high confidence + high impact
- Session summaries: End of natural conversation breaks
- Error messages: Immediate, with clear recovery options

### Tone
- Professional but friendly
- Concise and actionable
- Respectful of user autonomy
- Transparent about capabilities and limitations

### Personalization
- Adapt language to user's technical level
- Respect communication style preferences
- Adjust verbosity based on user feedback
- Maintain consistency with user's workflow patterns