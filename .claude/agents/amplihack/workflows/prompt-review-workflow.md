# Prompt Review Workflow

## Purpose

Define the integration pattern between PromptWriter and Architect agents for prompt review and refinement.

## Workflow Steps

### 1. Initial Prompt Generation

```
User -> PromptWriter: "Create prompt for [requirement]"
PromptWriter: Analyzes requirements
PromptWriter: Generates structured prompt
PromptWriter: Assesses complexity
```

### 2. Review Decision

```
If complexity == "Complex" OR user requests review:
  PromptWriter -> Architect: "Please review this prompt"
  Architect: Reviews for:
    - Architectural soundness
    - Module boundaries
    - Simplicity opportunities
    - Philosophy compliance
  Architect -> PromptWriter: Feedback/Approval
```

### 3. Refinement (if needed)

```
If Architect suggests changes:
  PromptWriter: Incorporates feedback
  PromptWriter: Regenerates prompt
  PromptWriter -> Architect: "Updated prompt"
  Architect: Final approval
```

### 4. Publication (optional)

```
If user wants GitHub issue:
  PromptWriter: Formats for GitHub
  PromptWriter -> GitHub Tool: Create issue
  GitHub Tool: Returns issue URL
  PromptWriter -> User: "Created issue #XXX: [URL]"
```

## Integration Examples

### Simple Task Flow

```markdown
User: "Create a prompt for adding user search functionality"

PromptWriter:

1. Generates prompt
2. Complexity: Simple
3. No review needed
4. Returns prompt to user
```

### Complex Task Flow

```markdown
User: "Create a prompt for migrating database from SQL to NoSQL"

PromptWriter:

1. Generates prompt
2. Complexity: Complex
3. "This involves architecture changes. Requesting review..."
4. Sends to Architect

Architect:

1. Reviews migration approach
2. Suggests phased approach
3. Returns feedback

PromptWriter:

1. Updates prompt with phases
2. Returns refined prompt
3. Offers: "Would you like me to create a GitHub issue?"
```

### Direct Review Request

```markdown
User: "Create a prompt for API refactoring and have architect review it"

PromptWriter:

1. Generates prompt
2. Immediately sends to Architect
3. Waits for review
4. Returns reviewed prompt
```

## Decision Criteria

### When to Auto-Request Review

- Multiple module interactions
- Database schema changes
- API contract modifications
- Security-sensitive features
- Performance-critical paths

### When to Skip Review

- UI-only changes
- Simple CRUD operations
- Documentation updates
- Test additions
- Bug fixes with clear scope

## Communication Patterns

### PromptWriter to Architect

```markdown
"I've generated a prompt for [task]. It involves [complexity indicators].
Please review for architectural soundness.

[Full prompt]

Specific concerns:

- [Concern 1]
- [Concern 2]"
```

### Architect to PromptWriter

```markdown
"Prompt review complete.

Strengths:

- [What's good]

Suggestions:

- [Improvement 1]
- [Improvement 2]

Verdict: [Approved/Needs Revision]"
```

### PromptWriter to User

```markdown
"I've generated a structured prompt for your requirement.

Complexity: [Simple/Medium/Complex]
Review Status: [Reviewed by Architect/No review needed]

[Full prompt]

Options:

1. Use this prompt as-is
2. Create GitHub issue
3. Request modifications"
```

## Error Handling

### Review Timeout

If Architect doesn't respond (shouldn't happen in practice):

- PromptWriter proceeds with warning
- Notes prompt is unreviewed
- Suggests manual review

### GitHub Creation Failure

If issue creation fails:

- Return formatted prompt anyway
- Provide manual creation instructions
- Include error details

## Metrics to Track

- Prompts generated
- Review requests made
- Reviews incorporated
- Issues created successfully
- Average prompt complexity
- Most common prompt types

## Best Practices

1. **Always assess complexity** - Don't skip the complexity check
2. **Err on side of review** - When unsure, request review
3. **Keep prompts focused** - One objective per prompt
4. **Document decisions** - Note why review was/wasn't requested
5. **Iterate quickly** - Don't over-optimize initial prompts

## Future Enhancements (NOT NOW)

These are noted but NOT for implementation:

- Prompt templates library
- Historical prompt analysis
- Auto-labeling based on content
- Prompt complexity scoring
- Integration with project management tools

Remember: This workflow enables quality without bureaucracy. Keep it simple and effective.
