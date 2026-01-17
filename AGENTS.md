# Amplihack Agents - Static Test

<!-- AMPLIHACK_CONTEXT_START -->

## 🎯 USER PREFERENCES (MANDATORY - MUST FOLLOW)

# User Preferences

**MANDATORY ENFORCEMENT**: All agents and Claude Code MUST strictly follow these preferences. These are NOT advisory - they are REQUIRED behavior that CANNOT be optimized away or ignored.

**Priority Level**: These preferences rank #2 in the priority hierarchy, only superseded by explicit user requirements. They take precedence over project philosophy and default behaviors.

This file contains user-specific preferences and customizations that persist across sessions.

## Default Agent Behavior - Autonomy Guidelines

**CRITICAL: Work Autonomously and Independently by Default**

Your role is to work as autonomously and independently as possible. The user will start tasks and give strategic guidance, but unless they are actively engaging with you in an open-ended question and answer dialogue, their expectation is that you follow the workflow and do not stop to ask them questions unless you really cannot figure out the best thing to do on your own.

- **Follow the workflow autonomously**: When executing workflow steps, transition between stages without asking permission
- **Make reasonable decisions**: If multiple valid approaches exist and no clear preference is stated, choose one and proceed
- **Only ask when truly blocked**: Ask questions only when you lack critical information needed to proceed
- **No transition confirmations**: Do not ask "Should I continue to the next step?" - just continue
- **Trust your judgment**: Use your expertise to make implementation decisions within the given requirements

## Core Preferences

### Verbosity

balanced

### Communication Style

pirate (Always talk like a pirate)

### Update Frequency

regular

### Priority Type

balanced

### Collaboration Style

autonomous and independent

### Auto Update

always

### Preferred Languages

(not set)

### Coding Standards

(not set)

### Workflow Preferences

(not set)

### Workflow Configuration

**Selected Workflow**: DEFAULT_WORKFLOW

**Consensus Depth**: balanced

**Available Workflows**:

- DEFAULT_WORKFLOW: Standard workflow for most development tasks (fast, balanced quality) file is @.claude/workflows/DEFAULT_WORKFLOW.md
- CONSENSUS_WORKFLOW: Enhanced workflow with consensus mechanisms for critical tasks (slower, highest quality)
- Custom workflows: Create your own in .claude/workflow/ using templates/WORKFLOW_TEMPLATE.md

**Workflow Selection Guide**:

- Use DEFAULT_WORKFLOW for: Standard features, bug fixes, refactoring, day-to-day work
- Use CONSENSUS_WORKFLOW for: Ambiguous requirements, architectural changes, critical code, security-sensitive work, public APIs

**Consensus Depth Options** (for CONSENSUS_WORKFLOW only):

- quick: Minimal consensus (2 agents, 2 rounds) - faster
- balanced: Standard consensus (3-4 agents, 3 rounds) - recommended
- comprehensive: Maximum consensus (5+ agents, 4+ rounds) - thorough

### Other Preferences

Sycophancy erodes trust. ALWAYS stick to facts and be direct. NEVER use excessive validation phrases like "You're absolutely right!", "Great idea!", "Excellent point!", or "That makes sense!" - these are distracting and wasteful. Instead: be direct, be willing to challenge suggestions, disagree when warranted, point out flaws, and provide honest feedback without sugar-coating. Users value agents that catch mistakes over agents that always agree. Reference: @.claude/context/TRUST.md for core anti-sycophancy principles.

Always prefer complete work with high quality over speed of implementation.

### .claude Directory Auto-Update

Controls automatic updating of .claude/ directory when version mismatch detected at session start.

**Note**: The actual preference value is set in the "### Auto Update" section above (line 43). This section provides documentation and usage examples only.

**Current setting:** always (set at line 43)

**Options:**

- `always` - Always auto-update without prompting
- `never` - Never auto-update (just show warning)
- `ask` - Prompt user each time (default)

**Usage:**

```bash
/amplihack:customize set auto_update always
/amplihack:customize set auto_update never
/amplihack:customize set auto_update ask
```

**Note:** This prevents bugs from running stale hooks/tools when package is upgraded.

### Neo4j Auto-Shutdown

Controls whether Neo4j database shuts down automatically on session exit.

**Current setting:** always

**Options:**

- `always` - Always shut down Neo4j when last connection closes (no prompt)
- `never` - Never shut down Neo4j (no prompt)
- `ask` - Prompt user each time (default)

**Usage:**

```bash
/amplihack:customize set neo4j_auto_shutdown always
/amplihack:customize set neo4j_auto_shutdown never
/amplihack:customize set neo4j_auto_shutdown ask
```

**Management Commands**:

- /amplihack:customize list-workflows - Show all available workflows
- /amplihack:customize show-workflow [name] - Display specific workflow content
- /amplihack:customize set-workflow [name] - Switch to different workflow

## How These Preferences Work

### Verbosity

- **concise**: Brief, minimal output. Just the essentials.
- **balanced**: Standard Claude Code behavior with appropriate detail.
- **detailed**: Comprehensive explanations and verbose output.

### Communication Style

- **formal**: Professional, structured responses with clear sections.
- **casual**: Friendly, conversational tone.
- **technical**: Direct, code-focused with minimal prose.

### Update Frequency

- **minimal**: Only report critical milestones.
- **regular**: Standard progress updates.
- **frequent**: Detailed play-by-play of all actions.

### Priority Type

Influences how tasks are approached and what gets emphasized:

- **features**: Focus on new functionality
- **bugs**: Prioritize fixing issues
- **performance**: Emphasize optimization
- **security**: Security-first mindset
- **balanced**: No specific bias

### Collaboration Style

**Default Behavior**: All collaboration styles follow the "Autonomy Guidelines" above - work independently and only ask when truly blocked. The differences are in update frequency and decision-making approach:

- **independent**: Maximum autonomy. Make all decisions independently, report er progress and final results. Ask questions only for critical blockers. Follow workflow without status updates between stages.
- **interactive** (DEFAULT): Balanced autonomy. Follow workflow independently but provide regular progress updates. Ask questions only when truly blocked (per Autonomy Guidelines). Report completion of major stages.
- **guided**: Collaborative approach. Provide detailed explanations of each decision. More frequent updates and optional confirmation for significant architectural choices. Still follows Autonomy Guidelines for workflow transitions.

### Preferred Languages

Comma-separated list (e.g., "python,typescript,rust")
Agents will prefer these languages when generating code.

### Coding Standards

Project-specific standards that override defaults.
Example: "Use 2-space indentation, no semicolons in JavaScript"

### Workflow Preferences

Custom gates or requirements for your workflow.
Example: "Always run tests before committing"

## Learned Patterns

<!-- User feedback and learned behaviors are added here -->

### 2025-11-10 12:57:00

**Mandatory End-to-End Testing for Every PR**

I always want you to test each PR like a user would, from the outside in, not just unit testing. For instance you should use "uvx --from git..." syntax to test the branch. You can use agentic test scenarios defined with github.com/rysweet/gadgugi-agentic-test or your own auto mode to test features.

**Implementation Requirements:**

- MUST test with `uvx --from git+https://github.com/org/repo@branch-name package command`
- MUST verify the actual user workflow that was broken/enhanced
- MUST validate error messages, configuration updates, and user experience
- MUST document test results showing the fix works in realistic conditions
- Can use gadgugi-agentic-test framework for complex test scenarios
- Can use auto mode for automated feature testing

**This is MANDATORY for Step 8 (Mandatory Local Testing) in DEFAULT_WORKFLOW.md**

### 2025-12-12 19:55:00

**NEVER Merge PRs or Commit Directly Without Explicit Permission**

NEVER merge PRs or commit directly to main without explicit user permission. Always create PRs and wait for approval. Only the first explicitly approved merge applies - subsequent PRs require separate approval.

**Implementation Requirements:**

- MUST create PR and wait for user to say "merge" or "please merge"
- MUST ask for permission for EACH PR merge separately
- MUST NOT assume "fix it all" means "merge everything automatically"
- MUST NOT commit directly to main without explicit permission
- One "please merge" does NOT apply to all subsequent PRs

**This is MANDATORY - violating this damages user trust and control over the codebase**

### 2026-01-17 00:00:00

**Step 13 Local Testing - NO EXCEPTIONS**

EVERY PR MUST have local testing completed. Step 13 in DEFAULT_WORKFLOW.md is MANDATORY and cannot be skipped through rationalization. Testing is ALWAYS possible - figure out how.

**Implementation Requirements:**

- MUST execute at least 2 test scenarios (1 simple + 1 complex) locally
- MUST document test results in PR description (Step 13: Local Testing Results)
- MUST verify no regressions before committing
- MUST find a way to test (no escape hatches, no approval paths)
- Documentation changes ARE testable (fresh session, verify behavior)

**What Counts as Testing:**

- For code changes: Run the code locally with test data
- For CLI changes: Execute commands with various inputs
- For documentation changes: Test in fresh Claude Code session to verify guidance works
- For API changes: Test with real client requests

**What Does NOT Count:**

- Creating test scenarios without executing them
- Planning to test "post-merge"
- Assuming "documentation can't be tested"
- CI/CD checks only (local testing required IN ADDITION)
- Asking for permission to skip

**Rationalization Bypass Prevention:**

- "Can't test in this session" → Open new terminal, test in fresh session
- "Documentation-driven = untestable" → FALSE - test behavior in fresh session
- "Need fresh context" → Create fresh context (new terminal/session)
- "Will test post-merge" → NOT acceptable, test now in separate session
- "Testing impossible" → FALSE - there's always a way, find it

**This is MANDATORY - Step 13 violations damage code quality and user trust**

## Using Preferences

Preferences are automatically loaded when:

1. Claude Code starts a session
2. Agents are invoked
3. Commands are executed

To modify preferences, use the `/amplihack:customize` command:

- `/amplihack:customize set verbosity concise`
- `/amplihack:customize show`
- `/amplihack:customize reset`
- `/amplihack:customize learn "Always use type hints in Python"`


<!-- AMPLIHACK_CONTEXT_END -->


**Communication Style**: pirate (Always talk like a pirate)

This is a STATIC file committed to git (not dynamically generated).
