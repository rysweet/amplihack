# User Requirement Priority System

## Priority Hierarchy (MANDATORY)

When agents encounter conflicting guidance, follow this strict priority order:

1. **EXPLICIT USER REQUIREMENTS** (HIGHEST PRIORITY - NEVER OVERRIDE)
2. **IMPLICIT USER PREFERENCES** (From USER_PREFERENCES.md)
3. **PROJECT PHILOSOPHY** (Simplicity, modularity, etc.)
4. **DEFAULT BEHAVIORS** (LOWEST PRIORITY)

## Explicit User Requirement Recognition

### What Constitutes an Explicit Requirement

**EXPLICIT** (Must be preserved):

- "ALL files" - User specifically requested completeness
- "Include everything" - User wants comprehensive coverage
- "Don't simplify X" - User explicitly forbids simplification
- "Keep the Y component" - User wants specific elements retained
- Quoted specifications: "use this exact format"
- Numbered lists of specific requirements
- "Must have" statements

**IMPLICIT** (Can be optimized within reason):

- General requests without specifics
- "Make it better" without constraints
- "Improve performance" (method is flexible)
- "Add feature X" (implementation approach flexible)

### Examples

**EXPLICIT - NEVER OVERRIDE:**

```
User: "I need ALL files included in the deployment"
→ Agent must include ALL files, cannot optimize to "essential only"

User: "Keep the authentication module even if it seems redundant"
→ Agent must preserve it regardless of philosophy
```

**IMPLICIT - CAN OPTIMIZE:**

```
User: "Improve the deployment process"
→ Agent can choose method as long as it improves the process

User: "Make the code cleaner"
→ Agent can apply philosophy principles
```

## Agent Behavior Rules

### For ALL Agents

1. **Before taking any action**, scan the original user request for explicit requirements
2. **If explicit requirements exist**, preserve them completely
3. **Philosophy applies only to HOW**, not WHAT to implement
4. **When in doubt**, ask for clarification rather than override

### For Simplification/Cleanup Agents

**CRITICAL RULE**: Before removing or simplifying anything, check:

1. Was this element explicitly requested by the user?
2. Is this element required to fulfill an explicit user requirement?
3. Would removing this violate a direct user instruction?

If YES to any → **DO NOT REMOVE/SIMPLIFY**

### For All Workflow Steps

Each workflow step must include:

```markdown
## User Requirement Check

- [ ] Explicit requirements identified from user request
- [ ] Current action preserves all explicit requirements
- [ ] Philosophy applied only to HOW, not WHAT
```

## Implementation Pattern

### Task Context Preservation

When invoking agents, always include explicit requirements in the prompt:

```
EXPLICIT USER REQUIREMENTS (MUST PRESERVE):
- [List each explicit requirement from user]
- [These cannot be optimized away]

IMPLICIT PREFERENCES:
- [Preferences that can be balanced with philosophy]

Your task: [specific task] while preserving ALL explicit requirements above.
```

### Validation Questions

Before finalizing any action, agents must ask:

1. Does this action preserve every explicit user requirement?
2. Am I optimizing HOW to implement, not changing WHAT to implement?
3. Would the user be surprised by this change?
4. Have I maintained the user's explicit constraints?

## Error Prevention

### Common Violations to Prevent

1. **Scope Reduction**: User asks for "everything", agent delivers "essentials"
2. **Requirement Substitution**: User asks for A, agent provides "better" B
3. **Premature Optimization**: Simplifying before understanding user intent
4. **Philosophy Override**: Applying simplicity when user wants completeness

### Warning Signs

- User says "explicitly" or "specifically"
- User lists exact requirements
- User says "don't simplify" or "keep all"
- User provides quotes or exact formats
- User emphasizes with CAPS or repetition

## Remember

- **User explicit requirements are sacred** - they override all other guidance
- **Philosophy guides HOW to implement** - not WHAT to implement
- **When unclear** - ask, don't assume
- **Simplicity is good** - but not at the cost of user requirements
- **Agents serve user intent** - not abstract principles

This system ensures agents remain helpful and aligned with philosophy while never countermanding explicit user requirements.
