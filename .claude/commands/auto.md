# Auto Command - Autonomous Agentic Loop

**Purpose**: Execute autonomous multi-turn agentic loops for complex tasks that require iteration, self-correction, and progress evaluation.

## Usage

```
/auto <prompt>
```

## What This Command Does

The auto command runs an autonomous agentic loop that:

1. **Clarifies the objective** with evaluation criteria
2. **Creates an execution plan** identifying parallel opportunities
3. **Executes iteratively** with progress evaluation
4. **Adapts dynamically** based on results
5. **Completes autonomously** when objective is achieved

Unlike single-turn commands, `/auto` will continue working until the task is complete or max iterations reached.

## When to Use Auto Mode

**Use `/auto` for:**

- Complex multi-step implementations
- Tasks requiring iteration and refinement
- Problems where the path isn't immediately clear
- Work that needs self-correction and adaptation
- Tasks that span multiple files/modules

**Don't use `/auto` for:**

- Simple single-step tasks (use direct prompt instead)
- Quick questions or information requests
- Code review or analysis only (use `/analyze`)
- Tasks where you want step-by-step control

## How It Works

### Turn 1: Clarify Objective

The first turn clarifies your objective and defines evaluation criteria:

```
Input: "implement user authentication"
Output:
  Objective: Implement secure user authentication system
  Criteria:
  - Password hashing with bcrypt
  - Login/logout endpoints
  - Session management
  - Input validation
  - Unit tests with 80%+ coverage
```

### Turn 2: Create Plan

The second turn creates a detailed execution plan:

```
Plan:
1. Design authentication module structure
2. Implement password hashing utilities (parallel: write tests)
3. Create login endpoint (parallel: logout endpoint)
4. Implement session management
5. Add input validation
6. Integration testing
7. Documentation
```

### Turns 3+: Execute & Evaluate

Remaining turns execute the plan and evaluate progress:

```
Turn 3: Execute
- Create auth module structure
- Implement password hashing
Evaluate: Incomplete - need endpoints

Turn 4: Execute
- Implement login endpoint
- Implement logout endpoint
Evaluate: Incomplete - need session management

Turn 5: Execute
- Implement session management
- Add validation
Evaluate: Incomplete - need tests

Turn 6: Execute
- Write unit tests
- Run test suite
Evaluate: COMPLETE - all criteria met ✓
```

## Configuration

**Default Settings:**

- Max turns: 10
- Auto hooks: session_start, stop
- Logging: `.claude/runtime/logs/auto_<timestamp>/`

**Completion Detection:**

The loop completes when evaluation contains:

- "evaluation: complete"
- "objective achieved"
- "all criteria met"

Or when max turns reached.

## Examples

### Basic Usage

```
/auto implement user authentication with bcrypt and tests
```

This will:

1. Clarify requirements (secure auth, bcrypt, tests)
2. Plan implementation steps
3. Execute iteratively until complete
4. Evaluate after each turn
5. Complete when all criteria met

### Complex Feature

```
/auto add real-time notifications using websockets with fallback to polling
```

This will:

1. Clarify technical requirements and fallback strategy
2. Plan websocket implementation + polling fallback
3. Execute both paths with testing
4. Iterate until both methods work correctly
5. Complete when fully functional with tests

### Bug Fix with Investigation

```
/auto fix the memory leak in the proxy connection pool
```

This will:

1. Clarify symptoms and success criteria
2. Plan investigation and fix strategy
3. Investigate code iteratively
4. Apply and test fixes
5. Verify memory leak resolved

### Refactoring Task

```
/auto refactor the authentication module to be more modular with better error handling
```

This will:

1. Clarify modularity goals and error handling patterns
2. Plan refactoring steps preserving functionality
3. Execute refactoring incrementally
4. Test after each change
5. Complete when modular and tested

## Integration with Workflow

Auto mode complements the standard workflow:

**For Quick Tasks:**

```
/auto implement feature X
→ Direct implementation without PR workflow
```

**For Full Feature Development:**

```
/ultrathink implement feature X with PR
→ Uses 14-step workflow + agents
→ Creates issue, branch, PR
→ Full review and merge process
```

**For Iterative Development:**

```
/auto prototype solution for X
→ Rapid iteration to working prototype
→ Then optionally: /ultrathink finalize with tests and PR
```

## Comparison with Other Commands

### /auto vs direct prompt

**Direct prompt:**

- Single turn execution
- No iteration or refinement
- Best for simple tasks

**/auto:**

- Multi-turn execution
- Iterative refinement
- Self-correcting
- Best for complex tasks

### /auto vs /ultrathink

**/ultrathink:**

- Follows 14-step workflow
- Creates issues, branches, PRs
- Full git workflow integration
- Multi-agent coordination
- Best for production features

**/auto:**

- Flexible iteration count
- No git workflow (can be added if needed)
- Simple agentic loop
- Best for rapid development/prototyping

### /auto vs /fix

**/fix:**

- Specialized for error resolution
- Pattern-based approach
- Quick fixes prioritized
- CI/test failure focus

**/auto:**

- General purpose iteration
- Goal-driven approach
- Complex implementations
- Full feature development

## Best Practices

### 1. Be Specific in Your Prompt

**Good:**

```
/auto implement JWT authentication with refresh tokens, using Redis for token storage, and include rate limiting
```

**Less Good:**

```
/auto add auth
```

### 2. Include Success Criteria

**Good:**

```
/auto implement caching layer with 90%+ hit rate, automatic invalidation, and monitoring
```

**Less Good:**

```
/auto add caching
```

### 3. Let It Run

Auto mode works best when allowed to iterate without interruption. Trust the evaluation logic to determine completion.

### 4. Use for Appropriate Complexity

**Too Simple (use direct prompt):**

```
/auto add a print statement
```

**Good Fit:**

```
/auto implement comprehensive error handling across the API layer with proper logging and user-facing messages
```

### 5. Chain with Other Commands

```
# Prototype rapidly
/auto prototype websocket notification system

# Then formalize
/ultrathink finalize websocket feature with tests and PR
```

## Logging and Debugging

All auto mode sessions log to:

```
.claude/runtime/logs/auto_claude_<timestamp>/
  auto.log           # Execution log
  turn_N_output.txt  # Output from each turn
```

Review logs to understand:

- How objective was clarified
- What plan was created
- Execution progress each turn
- Evaluation decisions
- Why completion was reached

## Troubleshooting

### Loop Exits Before Complete

**Symptom:** Auto mode exits at max turns without completing

**Solutions:**

- Increase max turns if task is genuinely complex
- Simplify the initial prompt
- Break into smaller sub-tasks
- Check evaluation criteria aren't too strict

### Wrong Interpretation

**Symptom:** Auto mode misunderstands objective

**Solutions:**

- Provide more detailed prompt
- Include explicit requirements
- Specify technical constraints
- Add concrete examples

### Premature Completion

**Symptom:** Auto mode completes before task fully done

**Solutions:**

- More rigorous success criteria in prompt
- Specify "with comprehensive tests"
- List all requirements explicitly
- Include validation requirements

## Advanced Usage

### Custom Max Turns

For very complex tasks requiring more iteration:

```
/auto [prompt with note: use 20 turns if needed]
```

### Parallel Execution Hints

Guide the planner to identify parallelization:

```
/auto implement both REST and GraphQL APIs - note these can be done in parallel
```

### Intermediate Checkpoints

Ask for validation at key points:

```
/auto implement payment processing - validate design before implementation
```

## Philosophy Alignment

Auto mode embodies key framework principles:

**Ruthless Simplicity:**

- Simple agentic loop (no over-engineering)
- Clear objective → plan → execute → evaluate
- Minimal abstractions

**Zero-BS:**

- No stubs or TODOs
- Working code at each iteration
- Real validation and testing

**Adaptive Intelligence:**

- Self-correcting based on results
- Dynamic plan adjustment
- Learns from each turn's output

## Remember

Auto mode is a power tool for autonomous execution. It works best when:

- Given clear objectives with success criteria
- Used for appropriately complex tasks
- Allowed to iterate without interruption
- Trusted to self-evaluate and adapt

For simple tasks, use direct prompts. For production features with full workflow, use `/ultrathink`. For iterative development and prototyping, use `/auto`.

---

**Start by providing a clear objective. Auto mode will handle the rest.**
