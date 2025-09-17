# Input Validation Instructions

## CRITICAL: Validate Input Before Processing

Before executing ANY task, you MUST verify that you have received proper input. This is a safety mechanism to prevent accidental invocations and ensure proper usage.

### Input Check Process

1. **Check for Input Presence**
   - Verify that you have received a task, prompt, specifications, or parameters
   - Look for specific instructions about what to do
   - Confirm the input contains actionable content

2. **Handle Missing Input**

   If NO input or parameters are provided, you MUST:

   a) **DO NOT proceed with any task execution**
   b) **DO NOT make assumptions about what the user wants**
   c) **IMMEDIATELY provide helpful usage information**

### Required Response for Missing Input

When invoked without proper input, respond with:

```
I need specific input to proceed. This [agent/command] requires:

- **Required**: [describe what input is needed]
- **Purpose**: [explain what this agent/command does]
- **Usage**: [provide usage example]

Examples:
[Provide 1-2 concrete examples of proper invocation]

Please provide the necessary input and try again.
```

### Input Validation Examples

#### Good Input (Proceed with task):
- "Build a user authentication module"
- "Analyze the security of the login system"
- "Review this code for philosophy compliance: [code]"
- Detailed specifications or requirements
- Specific file paths or targets

#### Bad Input (Stop and provide help):
- Empty string or whitespace only
- Generic phrases like "do something" or "help"
- No arguments when arguments are required
- Unclear or ambiguous requests without specifics

### Special Cases

1. **Commands with Optional Parameters**: If the command has optional parameters, proceed with defaults but confirm with user
2. **Interactive Agents**: May prompt for clarification, but still need initial input
3. **Analysis Agents**: Must have a target to analyze (path, code, or specification)

### Implementation Checklist

When implementing input validation:
- [ ] Check input exists and is not empty
- [ ] Verify input contains actionable content
- [ ] Provide clear usage instructions if input is missing
- [ ] Include concrete examples of proper usage
- [ ] Never proceed without valid input

## Remember

This validation is for safety and usability. It prevents:
- Accidental agent invocations
- Wasted computational resources
- Confusing or incorrect outputs
- User frustration from unclear behavior

Always fail gracefully with helpful information rather than attempting to guess user intent.