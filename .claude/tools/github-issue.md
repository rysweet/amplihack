# GitHub Issue Tool

## Purpose

Create GitHub issues from structured prompts with proper formatting and labeling.

## Contract

- **Inputs**:
  - title: Issue title (string, required)
  - body: Issue body in markdown (string, required)
  - labels: Array of label names (string[], optional)
  - assignees: Array of GitHub usernames (string[], optional)
  - milestone: Milestone name or number (string/number, optional)

- **Outputs**:
  - success: Boolean indicating creation status
  - issue_url: URL of created issue (if successful)
  - issue_number: Issue number (if successful)
  - error: Error message (if failed)

- **Side Effects**:
  - Creates issue in GitHub repository
  - Sends notifications to watchers/assignees

## Usage

```bash
# Using GitHub CLI (gh)
gh issue create \
  --title "Feature: Add dark mode" \
  --body "$(cat prompt.md)" \
  --label "enhancement,ui" \
  --assignee "username"
```

## Implementation Notes

### Required Setup

- GitHub CLI (`gh`) must be installed and authenticated
- Repository must be initialized with git
- User must have write permissions

### Command Structure

```bash
gh issue create [options]
```

### Options Mapping

- `--title` - Issue title
- `--body` - Issue description (supports markdown)
- `--label` - Comma-separated labels
- `--assignee` - Comma-separated assignees
- `--milestone` - Milestone name/number
- `--project` - Project board name/number

### Error Handling

- Check `gh` authentication status first
- Verify repository has remote configured
- Handle rate limiting gracefully
- Provide clear error messages

### Label Management

Common labels to consider:

- `enhancement` - New features
- `bug` - Bug fixes
- `refactor` - Code improvements
- `documentation` - Doc updates
- `testing` - Test additions
- `performance` - Performance improvements
- `security` - Security fixes

### Body Formatting

The tool should preserve markdown formatting:

- Headers (`#`, `##`, etc.)
- Lists (ordered and unordered)
- Code blocks with syntax highlighting
- Checkboxes for task lists
- Links and references

## Integration with PromptWriter

The PromptWriter agent can use this tool by:

1. Generating the structured prompt
2. Formatting it as markdown
3. Calling the GitHub CLI with appropriate parameters
4. Returning the issue URL to the user

## Example Usage

```bash
# Create issue from PromptWriter output
PROMPT_BODY="# Feature: User Authentication

## Objective
Implement secure user authentication system.

## Requirements
- [ ] Email/password login
- [ ] JWT token management
- [ ] Password reset flow

## Success Criteria
- [ ] Users can register and login
- [ ] Sessions persist appropriately
- [ ] Security best practices followed"

gh issue create \
  --title "Feature: User Authentication" \
  --body "$PROMPT_BODY" \
  --label "enhancement,security" \
  --assignee "@me"
```

## Validation

Before creating an issue:

1. Verify title is not empty
2. Verify body has content
3. Check labels exist in repository
4. Validate assignees are valid users
5. Confirm milestone exists (if specified)

## Response Handling

Parse the command output to extract:

- Issue number from success message
- Issue URL from output
- Error details from stderr

Return structured response for calling agent.
