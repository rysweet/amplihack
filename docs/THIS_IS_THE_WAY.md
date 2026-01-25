# The Amplihack Way: Effective Strategies for AI-Agent Development

This guide distills hard-won insights for working effectively with amplihack and Claude Code. These aren't theoretical best practices—they're battle-tested strategies that transform how you approach complex development challenges.

## Understanding Capability vs. Context

Amplihack isn't yet capable of doing all of the things we will eventually be able to do with it, but it's also not stuck in its current state. It is highly capable of helping improve itself for those who have the patience and willingness to help it learn.

### When Tasks Don't Complete: Two Root Causes

If you've made an ask of amplihack that is too challenging for it to complete within a few requests, your requests likely have one or both of the following problems:

1. **Too challenging for current capabilities** - The task genuinely exceeds what amplihack can reliably accomplish right now
2. **Not enough of the _right_ context** - Missing information that would enable completion

### The Context Solution Space is Bigger Than You Think

The "not enough context" problem has a _very_ big space. It could be that more context on the details of your ask are required, but it could _also_ mean that **metacognitive strategies** as part of its context can be provided to overcome the "too challenging for current capabilities" issue.

**Example:** If you ask amplihack to go off and perform an action on a collection of a hundred files, it likely will only get partially through that on its own (though it's getting better, so maybe it can by now). **BUT** if you tell it to:

1. Write an agent that will read in the list of files
2. Create a file for tracking status
3. Have that agent iterate through each file
4. Perform whatever action you need (great place to have it also create an agent to do that processing)

Then you are likely to get 100% completion. Technically, this is "just" giving it the context it needs to drive this behavior. This is why I'd consider this a context solution (whereas the lack of agents and pre-provided context hints about the use of agents, without user guidance, would be in the "too challenging for current capabilities" area).

## Decomposition: Breaking Down Big Swings

### Building Systems That Are Too Large

If you are trying to build a new system (maybe a "consensus workflow orchestrator" or agents for managing your documentation) and that system doesn't end up achieving all you hope for, consider that maybe your system is trying to do too much in too large of a swing.

**Ask yourself:** What can you decompose and break apart into smaller, useful units?

**The Pattern:**

1. Have amplihack help solve for and build agents for tackling those smaller units first
2. Then, go back to your larger scenario and ask it to create it again
3. This time provide the agents you had it create

This is a bit of a "cognitive offloading" that reduces the complexity (and token capacity and attention challenges) of trying to do it all in one larger "space".

**Bonus Value:** Those smaller agents usually also provide re-use value for other scenarios. Contributed back or shared with others extend their value further.

### The Persistence Principle

**If something is too big to get it to do reliably, don't give up.**

Lean in, leverage the decomposition ideas above, and keep plowing forward. Amplihack is continuously improving and can help improve itself with patience and willingness to guide it through learning.

## Using /amplihack:ultrathink for Complex Tasks

The `/amplihack:ultrathink` command is your power tool for complex, multi-step development tasks. It orchestrates multiple specialized agents in parallel to execute your workflow efficiently.

### When to Use UltraThink

**Perfect for:**

- Multi-step features requiring planning, implementation, testing, and documentation
- Complex refactoring across multiple modules
- Creating new features that need architecture design first
- Tasks that benefit from parallel agent execution

**Skip for:**

- Single file edits
- Simple bug fixes
- Straightforward documentation updates
- Quick configuration changes

### UltraThink Best Practices

**1. Be Specific About Requirements:**

```
/amplihack:ultrathink Add user authentication with JWT tokens. Must support:
- Token refresh mechanism
- Role-based access control
- Session management
- Secure password hashing with bcrypt
```

**2. Provide Context:**

```
/amplihack:ultrathink Looking at @src/api/endpoints.py, add rate limiting.
Use the existing middleware pattern and integrate with Redis.
Follow the pattern in @src/middleware/auth.py.
```

**3. Trust the Workflow:**
UltraThink follows the DEFAULT_WORKFLOW.md pattern:

- Creates GitHub issues
- Sets up worktrees
- Implements with TDD
- Runs tests and pre-commit hooks
- Creates and reviews PRs

Let it orchestrate—don't micromanage the steps.

## Working with Agents

### The Agent Library

Amplihack provides specialized agents for different tasks. Understanding when to use each one accelerates development.

**Core Workflow Agents:**

- **prompt-writer**: Clarify and structure task requirements
- **architect**: Design system architecture and module structure
- **builder**: Implement code from specifications
- **reviewer**: Code review and quality checks
- **cleanup**: Ruthless simplification and philosophy compliance

**Specialized Agents:**

- **knowledge-builder**: Build comprehensive knowledge bases
- **worktree-manager**: Manage git worktrees and branches
- **ci-diagnostic-workflow**: Debug CI/CD failures
- **security**: Security review and vulnerability analysis
- **optimizer**: Performance optimization

### Agent Invocation Patterns

**Direct invocation** for specific tasks:

```
Can you have the security agent review @src/auth/jwt.py for vulnerabilities?
```

**Workflow invocation** for complex tasks:

```
/amplihack:ultrathink [task description]
# UltraThink will invoke appropriate agents automatically
```

**Parallel agent execution** for speed:

```
Please run these agents in parallel:
1. reviewer agent on @src/api/
2. security agent on @src/auth/
3. optimizer agent on @src/database/queries.py
```

## Philosophy: Ruthless Simplicity

Amplihack follows the philosophy documented in `~/.amplihack/.claude/context/PHILOSOPHY.md`. Understanding and applying these principles makes you vastly more effective.

### The Core Principles in Practice

**1. Start Minimal, Grow as Needed**

❌ **Don't do this:**

```python
# Create generic, future-proof abstraction
class DataStore(ABC):
    @abstractmethod
    def save(self): pass
    @abstractmethod
    def load(self): pass
    @abstractmethod
    def query(self): pass
    @abstractmethod
    def delete(self): pass
```

✅ **Do this:**

```python
# Simple, direct implementation
def save_config(config: dict, path: Path) -> None:
    path.write_text(json.dumps(config))

def load_config(path: Path) -> dict:
    return json.loads(path.read_text())
```

**2. No Placeholders or TODOs**

❌ **Don't do this:**

```python
def process_data(data):
    # TODO: Add validation
    # TODO: Handle edge cases
    pass  # Implement later
```

✅ **Do this:**

```python
def process_data(data: list[dict]) -> list[dict]:
    if not data:
        raise ValueError("Data cannot be empty")
    return [item for item in data if item.get("valid", False)]
```

**3. Explicit Error Handling**

❌ **Don't do this:**

```python
try:
    result = dangerous_operation()
except:
    pass  # Silent failure
```

✅ **Do this:**

```python
try:
    result = dangerous_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise OperationError(f"Failed to process: {e}") from e
```

### Invoking the Cleanup Agent

The cleanup agent is your philosophy enforcement tool. Use it liberally:

```
Please have the cleanup agent review @src/new_feature/ and apply ruthless simplification.
The user requirement was: [state the explicit requirement]
Remove any complexity that doesn't directly serve this requirement.
```

**Key:** Always provide the original user requirement to prevent over-simplification.

## Working with Worktrees

Amplihack uses git worktrees for parallel development. This enables working on multiple features simultaneously without branch switching.

### The Worktree Pattern

**Standard structure:**

```
./worktrees/
├── feat/issue-123-auth-system/
├── feat/issue-456-api-refactor/
├── fix/issue-789-rate-limit-bug/
└── docs/issue-101-user-guide/
```

**Using the worktree-manager agent:**

```
Please have the worktree-manager create a worktree for implementing user authentication.
This is for issue #123.
```

The agent will:

1. Create worktree at `./worktrees/feat/issue-123-user-authentication/`
2. Create and push branch `feat/issue-123-user-authentication`
3. Set up tracking with remote

### Working Across Worktrees

**Switch between worktrees:**

```bash
cd worktrees/feat/issue-123-auth-system/
# Work on auth

cd ../feat/issue-456-api-refactor/
# Work on API
```

**Cleanup merged worktrees:**

```bash
git worktree prune
```

## Handling Context Limits

When working with large codebases, context limits become real constraints.

### Strategies for Context Management

**1. Use Targeted Reads**

```
Read just the files I need:
@src/auth/jwt.py
@src/auth/tokens.py
@tests/test_auth.py

Not the entire src/ directory.
```

**2. Leverage Agent Memory**

```
First, have the knowledge-builder agent create a knowledge base of @src/api/.
Then use that knowledge base for subsequent questions.
```

**3. Work in Vertical Slices**

```
Let's implement user registration end-to-end first:
- API endpoint
- Database model
- Business logic
- Tests

Then we'll do login as a separate slice.
```

**4. Use Session State**

Maintain `ai_working/session_state.md` with current context:

```markdown
## Current Focus

Implementing JWT authentication

## Recent Decisions

- Using RS256 algorithm (not HS256) for better key management
- Token expiry: 15 minutes access, 7 days refresh
- Storing refresh tokens in Redis, not database

## Next Steps

1. Implement token refresh endpoint
2. Add middleware for token validation
3. Write integration tests
```

## Testing Strategy

Amplihack enforces test-driven development through the workflow.

### The Testing Pyramid

```
     /\      10% End-to-End
    /  \     30% Integration
   /    \    60% Unit
  /______\
```

**Unit tests** for business logic:

```python
def test_generate_jwt_token():
    token = generate_jwt(user_id="123", role="admin")
    payload = decode_jwt(token)
    assert payload["user_id"] == "123"
    assert payload["role"] == "admin"
```

**Integration tests** for system interactions:

```python
def test_authentication_flow(client):
    # Register
    response = client.post("/auth/register", json=user_data)
    assert response.status_code == 201

    # Login
    response = client.post("/auth/login", json=credentials)
    token = response.json()["access_token"]

    # Access protected endpoint
    response = client.get("/api/profile", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
```

**End-to-end tests** for critical flows:

```python
def test_complete_user_journey():
    # Registration → Login → Profile Update → Logout
    # Tests entire user lifecycle
```

### Test-First Development

Let the tester agent write failing tests before implementation:

```
/amplihack:ultrathink Implement password reset functionality.

Step 1: Have tester agent write tests for:
- Request reset email
- Validate reset token
- Update password with valid token
- Reject expired tokens

Step 2: Have builder agent make tests pass.
```

## CI/CD and Pre-commit Hooks

Amplihack's workflow enforces quality gates through CI/CD and pre-commit hooks.

### Pre-commit Hook Success

**If pre-commit fails:**

1. The workflow will automatically fix what it can (formatting, imports)
2. Review the changes
3. Fix any remaining issues (type errors, linting)
4. Re-run: `pre-commit run --all-files`

**Common failures:**

- **Ruff linting**: Code style violations
- **Type checking**: mypy or pyright errors
- **Import sorting**: isort violations
- **Formatting**: Black/Prettier violations

**Using the pre-commit-diagnostic agent:**

```
Pre-commit is failing on the type-check hook.
Can you have the pre-commit-diagnostic agent investigate and fix it?
```

### CI/CD Failure Diagnosis

**If CI fails after PR creation:**

```
PR #123 has failing CI checks.
Can you have the ci-diagnostic-workflow agent investigate and fix the issues?
```

The agent will:

1. Fetch CI logs
2. Identify failure root cause
3. Implement fixes
4. Verify fixes locally
5. Push updates to PR

## Continuous Improvement

Amplihack improves itself through usage. You're part of that process.

### Contributing to Amplihack

**Found a useful pattern?** Document it in `docs/DISCOVERIES.md`:

```markdown
## [Problem Title] (YYYY-MM-DD)

### Issue

[What went wrong]

### Solution

[How you fixed it]

### Key Learnings

[What you learned]
```

**Created a useful agent?** Consider contributing:

1. Document the agent's purpose and use cases
2. Provide examples of invocation
3. Test with multiple scenarios
4. Submit a PR

**Improved a workflow?** Update the relevant documentation:

- `DEFAULT_WORKFLOW.md` for process improvements
- `PHILOSOPHY.md` for principle refinements
- `THIS_IS_THE_WAY.md` for practical patterns

## Key Takeaways

### Shift Your Mindset

- **Context over capability** - Most "limitations" are actually context gaps
- **Decomposition over monoliths** - Break big problems into agent-solvable steps
- **Philosophy-first** - Ruthless simplicity beats clever complexity
- **Agents over manual work** - Encode workflows in reusable agents

### Practical Strategies

1. **For complex tasks** - Use `/amplihack:ultrathink` to orchestrate the full workflow
2. **For batch operations** - Have amplihack build an agent with status tracking and iteration
3. **For large systems** - Build smaller useful components first, then compose them
4. **When stuck** - Don't give up, provide metacognitive strategies as context
5. **After success** - Document learnings in DISCOVERIES.md for future reference

### The Amplihack Philosophy

Amplihack is highly capable of helping improve itself. Your patience and willingness to guide it through learning doesn't just solve your immediate problem—it makes the system better for everyone.

**Don't give up. Lean in. Keep plowing forward.**

The challenges you overcome today become capabilities amplihack has tomorrow.

## Further Reading

- **PHILOSOPHY.md** - Core principles and the Brick Philosophy
- **DISCOVERIES.md** - Documented problems and solutions
- **DEFAULT_WORKFLOW.md** - The multi-step development workflow
- **agents/** - Specialized agent documentation
