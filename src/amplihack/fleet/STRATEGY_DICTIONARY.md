# Fleet Director Strategy Dictionary

Reference document for the fleet director's decision engine. Read before every decision cycle.
Based on analysis of 140+ real sessions and observed tool/strategy usage patterns.

---

## STRATEGY INDEX

| # | Strategy | Trigger |
|---|----------|---------|
| 1 | Workflow Compliance Check | Adopting/monitoring any session |
| 2 | Outside-In Testing Gate | Task marked complete, PR ready |
| 3 | Philosophy Enforcement | Reviewing agent output or PR |
| 4 | Parallel Agent Investigation | Understanding unfamiliar codebase |
| 5 | Multi-Agent Review | Important PR needs review |
| 6 | Lock Mode for Deep Work | Complex task requiring 2+ hours focus |
| 7 | Goal Measurement | End of task cycle |
| 8 | Quality Audit Cycle | Feature implementation complete |
| 9 | Pre-Commit Diagnostic | Pre-commit hooks failing |
| 10 | CI Diagnostic Recovery | CI fails after push |
| 11 | Worktree Isolation | New task assignment |
| 12 | Investigation Before Implementation | Unfamiliar code area |
| 13 | Architect-First Design | New feature or system change |
| 14 | Sprint Planning with PM | Backlog prioritization needed |
| 15 | N-Version for Critical Code | Security/mission-critical implementation |
| 16 | Debate for Architecture Decisions | Complex trade-off with no clear winner |
| 17 | Dry-Run Validation | Before any live action on sessions |
| 18 | Session Adoption Protocol | Taking over existing sessions |
| 19 | Morning Briefing | Session start / operator check-in |
| 20 | Escalation Protocol | Low confidence or repeated failures |

---

## STRATEGIES

### 1. Workflow Compliance Check

**When:** Adopting or monitoring any session. First thing to verify after connecting to an agent.

**Action:** Check that the agent is following DEFAULT_WORKFLOW.md (22 steps). Scan for:
- Step 0 (Issue/Branch) completed
- Step 6 (Architect review) not skipped
- Step 8 (Testing) has real results
- Step 13 (Local testing) has documented output -- mandatory per user preferences

If steps were skipped, inject a reminder: "You skipped Step N. Execute it now before proceeding."

**Example:**
```
Director observes session-7 pushed a PR without test results.
→ Director sends: "Step 13 (Local Testing) is mandatory. Run at least 2 test
  scenarios and document results in the PR description before this can merge."
→ Agent executes tests, updates PR.
```

---

### 2. Outside-In Testing Gate

**When:** Before marking any task as ACHIEVED. Before approving any PR for merge readiness.

**Action:** Verify outside-in testing was performed:
1. Check PR description for "Step 13: Local Testing Results" section
2. Look for `uvx --from git+...` test commands in session logs
3. If missing, invoke skill `outside-in-testing` or instruct agent to run end-to-end tests

Minimum: 1 simple scenario + 1 complex scenario with documented output.

**Example:**
```
Director reviews PR #142, finds no test results section.
→ Director instructs agent: "Run outside-in testing. Execute:
   uvx --from git+https://github.com/org/repo@branch package-name --help
   Then test the actual user workflow that changed."
→ Agent runs tests, pastes results into PR.
```

---

### 3. Philosophy Enforcement

**When:** Reviewing completed agent output. Spotting signs of over-engineering: deep abstraction layers, placeholder code, TODO comments, swallowed exceptions.

**Action:** Invoke `philosophy-guardian` agent on the changed files. Check for:
- Ruthless simplicity violations (unnecessary abstractions)
- Zero-BS violations (stubs, NotImplementedError, TODOs in code)
- Dead code, unused imports
- Proportionality violations (58 tests for 2 lines of code)

**Example:**
```
Director sees builder created a 4-layer abstraction for a config reader.
→ Director invokes philosophy-guardian on the module.
→ Guardian reports: "3 unnecessary abstraction layers. Direct implementation
   would be 40 lines vs current 180."
→ Director instructs agent to simplify.
```

---

### 4. Parallel Agent Investigation

**When:** Need to understand a codebase or system with multiple independent modules. Unfamiliar territory. Pre-implementation research.

**Action:** Launch multiple `analyzer` agents in parallel, each examining a different module or concern:
```
[analyzer(module_a), analyzer(module_b), analyzer(module_c)]
```
Synthesize results to build a complete system picture before any implementation begins.

**Example:**
```
Task: "Add caching to the API layer"
→ Director launches in parallel:
   - analyzer on API routes (understand endpoints)
   - analyzer on data layer (understand current data flow)
   - analyzer on config system (understand how settings work)
→ Results synthesized into implementation plan.
```

---

### 5. Multi-Agent Review

**When:** PR touches security-sensitive code, public APIs, core architecture, or changes affecting multiple modules. Any PR with 500+ lines changed.

**Action:** Invoke three reviewers in parallel:
```
[reviewer(code_quality), security(vulnerability_scan), philosophy-guardian(simplicity)]
```
Collect all findings, deduplicate, post consolidated review to PR.

**Example:**
```
PR #98 adds JWT authentication (security-sensitive).
→ Director launches:
   - reviewer: checks code quality, test coverage, error handling
   - security: checks token validation, timing attacks, secret storage
   - philosophy-guardian: checks for over-engineering
→ Combined review posted as single PR comment with sections.
```

---

### 6. Lock Mode for Deep Work

**When:** Agent is working on a complex task requiring sustained focus (2+ hours). Architectural redesign, large refactoring, deep debugging.

**Action:** Use `/amplihack:lock` to mark the session as protected. Set task status to `in_progress` with a lock flag. Prevent the director from interrupting with status checks or reassignments.

Check back only at the estimated completion time or if the agent signals it is stuck.

**Example:**
```
Agent session-3 is redesigning the database schema (estimated 3 hours).
→ Director: /amplihack:lock session-3 --duration 3h --reason "schema redesign"
→ Director skips session-3 in monitoring cycles until lock expires.
→ After 3h, director checks: "Lock expired on session-3. Checking status."
```

---

### 7. Goal Measurement

**When:** After each task cycle completes. When an agent reports "done." During periodic health checks.

**Action:** Compare agent output against original task requirements. Classify as:
- `GOAL_STATUS: ACHIEVED` -- all requirements met, tests pass, PR ready
- `GOAL_STATUS: PARTIAL` -- some requirements met, specify what remains
- `GOAL_STATUS: NOT_ACHIEVED` -- requirements not met, specify gaps

Track measurement in fleet state for reporting.

**Example:**
```
Task: "Add pagination to /api/users endpoint"
Agent reports done. Director checks:
- [x] Endpoint accepts page/limit params → YES
- [x] Response includes total_count → YES
- [ ] Tests cover edge cases (page=0, limit=10000) → NO
→ GOAL_STATUS: PARTIAL
→ Director: "Missing edge case tests for page=0 and limit=10000. Add them."
```

---

### 8. Quality Audit Cycle

**When:** Feature implementation is complete and passing tests. Before final PR approval. Periodically on mature codebases.

**Action:** Invoke skill `quality-audit-workflow`:
1. Audit identifies issues (complexity, duplication, missing tests)
2. Create fix tasks from audit findings
3. Agent addresses fixes
4. Re-audit to confirm resolution

Iterate until audit is clean or remaining issues are documented as accepted.

**Example:**
```
Feature "user notifications" is complete.
→ Director invokes quality-audit-workflow on src/notifications/
→ Audit finds: 2 untested error paths, 1 duplicated validation block
→ Director creates fix tasks, agent resolves them
→ Re-audit: clean. Feature approved.
```

---

### 9. Pre-Commit Diagnostic

**When:** Agent reports pre-commit hook failures. Commit attempt rejected by local hooks. Formatting, linting, or type-check errors blocking commit.

**Action:** Invoke `pre-commit-diagnostic` agent. It will:
1. Parse hook output to identify all failures
2. Auto-fix formatting issues (black, ruff, prettier)
3. Fix linting issues (unused imports, type errors)
4. Re-run hooks to verify all pass

Do not proceed to push until all hooks pass.

**Example:**
```
Agent session-5: "Pre-commit failed: ruff found 3 issues, black reformatted 2 files"
→ Director invokes pre-commit-diagnostic agent
→ Agent auto-fixes all issues, re-runs hooks
→ All hooks pass. Agent commits successfully.
```

---

### 10. CI Diagnostic Recovery

**When:** CI pipeline fails after push. PR checks show red. Agent is stuck on CI failures.

**Action:** Invoke `ci-diagnostic-workflow` agent:
1. Check CI status with `gh run view`
2. Download and parse failure logs
3. Identify root cause (test failure, lint, build error, dependency)
4. Apply fix
5. Push and re-check
6. Iterate until all checks pass

Never auto-merge. Report "PR is mergeable" and wait for human approval.

**Example:**
```
PR #77 CI failed: test_auth_flow assertion error.
→ Director invokes ci-diagnostic-workflow
→ Agent identifies: test expects old response format, code changed format
→ Agent updates test, pushes fix commit
→ CI re-runs, all green. Director reports: "PR #77 is now mergeable."
```

---

### 11. Worktree Isolation

**When:** Starting a new task. Multiple tasks running in parallel. Need to prevent branch conflicts between sessions.

**Action:** Create an isolated git worktree for the task:
1. Use `EnterWorktree` or `worktree-manager` agent
2. Create worktree in `.claude/worktrees/` with a task-specific branch
3. Agent works exclusively in the worktree
4. On completion, PR is created from the worktree branch

Prevents: merge conflicts, accidental cross-task pollution, lost work.

**Example:**
```
Two tasks: "Add caching" and "Fix auth bug"
→ Director creates worktree for each:
   - .claude/worktrees/add-caching/ (branch: feat/add-caching)
   - .claude/worktrees/fix-auth/ (branch: fix/auth-bug)
→ Each agent works in isolation. No conflicts.
```

---

### 12. Investigation Before Implementation

**When:** Task involves code the agent has not previously worked with. Bug in an unfamiliar module. Feature touching multiple unknown systems.

**Action:** Run INVESTIGATION_WORKFLOW before DEFAULT_WORKFLOW:
1. Clarify investigation scope
2. Discover and map code structure (Glob, Grep, Read)
3. Deep dive with `knowledge-archaeologist` agent
4. Verify understanding with examples
5. Synthesize findings into a brief report
6. Then proceed to implementation with full context

**Example:**
```
Task: "Fix race condition in job scheduler"
Agent has never seen the scheduler code.
→ Director: "Run investigation workflow on src/scheduler/ first."
→ Agent maps: JobQueue, Worker, Dispatcher classes and their interactions
→ Agent identifies the race condition location
→ Then proceeds to DEFAULT_WORKFLOW for the fix with full understanding.
```

---

### 13. Architect-First Design

**When:** New feature requiring 100+ lines of code. System-level changes. API additions. Database schema changes.

**Action:** Invoke `architect` agent before `builder`:
1. Architect produces: module boundaries, public contracts, data models, error handling strategy
2. Director reviews architect output for philosophy compliance
3. Hand specification to `builder` agent for implementation
4. `reviewer` validates implementation matches spec

Sequential chain: architect → builder → reviewer

**Example:**
```
Task: "Add webhook notification system"
→ Director invokes architect: design the webhook module
→ Architect produces: WebhookManager class, event model, retry strategy, API endpoints
→ Director checks: spec is simple, self-contained, regeneratable
→ Director hands spec to builder: "Implement this specification exactly."
→ Builder produces code. Reviewer validates.
```

---

### 14. Sprint Planning with PM

**When:** Multiple tasks in backlog need prioritization. Start of a work session with queued tasks. Operator asks "what should we work on next?"

**Action:** Use `pm-architect` skill/agent to:
1. Review all open issues/tasks
2. Assess priority (urgency, dependencies, impact)
3. Recommend execution order
4. Estimate complexity for each task
5. Assign tasks to available fleet sessions

**Example:**
```
Backlog has 8 tasks. 3 fleet sessions available.
→ Director invokes pm-architect: "Prioritize these 8 tasks."
→ PM recommends: #45 (blocker, 2h), #42 (high, 4h), #48 (medium, 1h)
→ Director assigns: session-1=#45, session-2=#42, session-3=#48
→ Remaining tasks queued for next available session.
```

---

### 15. N-Version for Critical Code

**When:** Implementing security-critical code (auth, crypto, token validation). Core algorithms where correctness is paramount. Mission-critical features where a bug has high cost.

**Action:** Use `/amplihack:n-version` workflow:
1. Generate 3 independent implementations (different approaches)
2. Run all against the same test suite
3. Compare outputs, performance, and code quality
4. Select the best implementation
5. Discard the others

Cost: 3-4x execution time. Benefit: 30-65% error reduction.

**Example:**
```
Task: "Implement rate limiter for API"
→ Director: /amplihack:n-version "Implement rate limiter"
→ Version A: Token bucket algorithm
→ Version B: Sliding window counter
→ Version C: Fixed window with burst
→ All tested. Version B wins: simplest, correct, best performance.
```

---

### 16. Debate for Architecture Decisions

**When:** Complex trade-off with no obvious answer. "Should we use X or Y?" Multiple valid approaches with different strengths. Team disagreement on approach.

**Action:** Use `/amplihack:debate` workflow:
1. Frame the question clearly
2. Assign perspectives: security, performance, simplicity, maintainability
3. Each perspective argues its case with evidence
4. Structured rebuttal round
5. Convergence on a decision with documented rationale

Cost: 2-3x execution time. Benefit: 40-70% better decision quality.

**Example:**
```
Question: "Should fleet state use SQLite or in-memory dict with JSON persistence?"
→ Director: /amplihack:debate "SQLite vs JSON for fleet state"
→ Simplicity perspective: JSON -- fewer dependencies, easier debugging
→ Performance perspective: SQLite -- concurrent access, query capability
→ Maintenance perspective: JSON -- human-readable, git-friendly
→ Decision: JSON with SQLite migration path. Documented in DECISIONS.md.
```

---

### 17. Dry-Run Validation

**When:** Before the director takes any live action that modifies sessions, sends commands to agents, or changes fleet state. Especially before destructive operations.

**Action:** Run the decision through dry-run mode:
1. Log what WOULD happen without executing
2. Check: Does this action match operator intent?
3. Check: Could this action cause harm? (kill session, force push, delete branch)
4. If confidence > 0.8 and non-destructive: proceed
5. If confidence < 0.8 or destructive: escalate to human

**Example:**
```
Director decides to kill stuck session-4 and reassign its task.
→ Dry-run output:
   "WOULD: Terminate session-4 (running 6h, last activity 2h ago)"
   "WOULD: Reassign task #55 to new session-5"
   "WOULD: Create worktree for session-5"
→ Director checks: session-4 has uncommitted changes!
→ Director adjusts: save worktree first, THEN terminate.
```

---

### 18. Session Adoption Protocol

**When:** Director starts and finds existing running sessions. Taking over management of sessions started by another director or manually by operator.

**Action:** Follow the adoption sequence:
1. **Scan**: List all active Claude sessions (`fleet ps`)
2. **Infer**: Read each session's recent commands and output to determine current task
3. **Track**: Create fleet state records for each session (task, branch, status)
4. **Observe**: Monitor for 1 cycle without sending any commands
5. **Adopt**: After observation, begin normal management

Never disrupt a session mid-operation during adoption.

**Example:**
```
Director starts. Finds 3 running sessions.
→ Scan: session-1 (active, last cmd 5m ago), session-2 (active, 30m ago), session-3 (idle, 2h ago)
→ Infer: session-1 is implementing auth, session-2 is debugging tests, session-3 might be stuck
→ Track: Create records for all 3
→ Observe: Wait 1 cycle
→ Adopt: session-1 and session-2 look healthy. Check on session-3.
```

---

### 19. Morning Briefing

**When:** Start of a work session. Operator asks for status. After significant downtime (8+ hours since last activity).

**Action:** Collect and present:
1. **Completed**: Tasks finished since last briefing, PRs merged
2. **In Progress**: Active sessions and their current tasks
3. **Blocked**: Sessions stuck, CI failures, unresolved issues
4. **Queue**: Tasks waiting for assignment
5. **Cost**: Estimated token/cost usage if available
6. **Recommendations**: What to work on next (invoke pm-architect if needed)

**Example:**
```
Operator: "What's the status?"
→ Director:
   COMPLETED: Task #45 (auth fix) -- PR #99 merged
   IN PROGRESS: session-2 on task #42 (caching) -- 60% complete
   BLOCKED: session-3 hit CI failure on PR #101
   QUEUE: Tasks #48, #49, #50 waiting
   RECOMMENDATION: Unblock session-3 first (CI fix), then assign #48.
```

---

### 20. Escalation Protocol

**When:**
- Director confidence < 0.6 on any decision
- Destructive operation detected (force push, branch delete, session kill with unsaved work)
- Same issue recurs 3+ times despite fixes
- Agent stuck for > 2 hours with no progress
- Security-sensitive operation (credential handling, permission changes)
- Cost exceeds budget threshold

**Action:** Do NOT act. Instead:
1. Log the situation with full context
2. Present to operator with options (not just the problem)
3. Wait for explicit human decision
4. Execute only what the human approves

**Example:**
```
Session-6 has failed CI 3 times on the same test.
→ Director: "ESCALATION: session-6 has failed CI 3 times on test_webhook_retry.
   Root cause unclear after 3 fix attempts.
   Options:
   A) Run investigation workflow on the test module
   B) Skip this test and document as known issue
   C) Reassign to a fresh session with investigation-first strategy
   Awaiting your decision."
```

---

## CAPABILITIES REFERENCE

### Core Agents (7)

Located in `~/.amplihack/.claude/agents/amplihack/core/`

| Agent | Purpose |
|-------|---------|
| `architect` | System design, problem decomposition, module specifications |
| `builder` | Code implementation from specifications |
| `reviewer` | Code review, quality checks, philosophy compliance |
| `tester` | Test generation, validation, coverage analysis |
| `api-designer` | API contract definitions, endpoint design |
| `optimizer` | Performance analysis, bottleneck identification |
| `guide` | User guidance, documentation, onboarding |

### Specialized Agents (30)

Located in `~/.amplihack/.claude/agents/amplihack/specialized/`

| Agent | Purpose |
|-------|---------|
| `ambiguity` | Resolve unclear requirements |
| `amplifier-cli-architect` | CLI application design |
| `analyzer` | Deep code analysis and understanding |
| `azure-kubernetes-expert` | AKS deployment and configuration |
| `ci-diagnostic-workflow` | CI failure diagnosis and fix iteration |
| `cleanup` | Code simplification, dead code removal |
| `concept-extractor` | Extract concepts from codebases |
| `database` | Schema design, query optimization |
| `documentation-writer` | Documentation generation |
| `fallback-cascade` | Graceful degradation implementation |
| `fix-agent` | Rapid fix for common error patterns |
| `iac-planner` | Infrastructure-as-code planning |
| `insight-synthesizer` | Synthesize findings across analyses |
| `integration` | External service connections |
| `knowledge-archaeologist` | Deep investigation of existing code |
| `mcp-server-builder` | MCP server implementation |
| `multi-agent-debate` | Structured multi-perspective debate |
| `n-version-validator` | N-version implementation comparison |
| `openapi-scaffolder` | OpenAPI spec generation and scaffolding |
| `patterns` | Pattern recognition, reusable solutions |
| `philosophy-guardian` | Philosophy compliance, simplicity validation |
| `pre-commit-diagnostic` | Pre-commit hook failure auto-fix |
| `preference-reviewer` | User preference compliance check |
| `prompt-writer` | Prompt engineering and refinement |
| `rust-programming-expert` | Rust implementation specialist |
| `security` | Vulnerability assessment, security review |
| `socratic-reviewer` | Question-driven code review |
| `visualization-architect` | Architecture diagrams, visual docs |
| `worktree-manager` | Git worktree lifecycle management |
| `xpia-defense` | Cross-plugin injection attack defense |

### Workflow Agents (2)

Located in `~/.amplihack/.claude/agents/amplihack/workflows/`

| Agent | Purpose |
|-------|---------|
| `amplihack-improvement-workflow` | Framework self-improvement |
| `prompt-review-workflow` | Prompt quality review |

### Workflows (11)

Located in `~/.amplihack/.claude/workflow/`

| Workflow | Steps | Purpose |
|----------|-------|---------|
| `DEFAULT_WORKFLOW` | 22 | Standard development (branch, implement, test, PR) |
| `INVESTIGATION_WORKFLOW` | 6 | Deep code understanding and documentation |
| `CONSENSUS_WORKFLOW` | Multi-round | Multi-agent consensus for critical decisions |
| `CASCADE_WORKFLOW` | 3-tier | Graceful degradation: optimal → pragmatic → minimal |
| `DEBATE_WORKFLOW` | 4-round | Multi-perspective structured debate |
| `N_VERSION_WORKFLOW` | Generate+Select | Multiple independent implementations compared |
| `SIMPLIFIED_WORKFLOW` | Reduced | Lightweight workflow for small changes |
| `VERIFICATION_WORKFLOW` | Verify | Post-implementation verification |
| `OPS_WORKFLOW` | Varies | Administrative and operational tasks |
| `Q&A_WORKFLOW` | 1 | Simple question-answer (respond directly) |
| `CONSENSUS_WORKFLOWS_OVERVIEW` | -- | Reference doc for consensus patterns |

### Key Skills

| Skill | Usage Count | Purpose |
|-------|-------------|---------|
| `quality-audit-workflow` | 13 | Find issues, create fixes, iterate to clean |
| `dev-orchestrator` | 4 | Classify task, decompose, execute via recipe runner |
| `outside-in-testing` | 1 | End-to-end user-perspective testing |
| `pm-architect` | -- | Backlog prioritization and sprint planning |
| `mermaid-diagram-generator` | -- | Architecture and flow diagrams |
| `philosophy-compliance-workflow` | -- | Full philosophy audit |
| `test-gap-analyzer` | -- | Find untested code paths |
| `smart-test` | -- | Intelligent test generation |
| `session-learning` | -- | Cross-session knowledge capture |
| `multitask` | -- | Parallel workstream execution |
| `ultrathink-orchestrator` | -- | Full workflow orchestration |

### Key Commands

| Command | Purpose |
|---------|---------|
| `/dev <task>` | Default entry point for development tasks (invokes dev-orchestrator) |
| `/fix [pattern] [scope]` | Intelligent fix dispatch (import, ci, test, config, quality, logic) |
| `/analyze <path>` | Comprehensive code review for philosophy compliance |
| `/improve [target]` | Self-improvement and learning capture |
| `/amplihack:n-version <task>` | N-version programming for critical code |
| `/amplihack:debate <question>` | Multi-agent debate for decisions |
| `/amplihack:cascade <task>` | Fallback cascade for resilient operations |
| `/amplihack:lock` | Protect session from interruptions |
| `/amplihack:unlock` | Release session protection |
| `/amplihack:reflect` | Capture learnings and discoveries |

### Key Tools (by observed frequency)

| Tool | Frequency | Primary Use |
|------|-----------|-------------|
| `Bash` | 1282 | Commands, git operations, testing |
| `Read` | 342 | File reading, context gathering |
| `Edit` | 297 | Code modification |
| `Grep` | 89 | Content search, pattern finding |
| `Agent/Task` | 169 | Agent delegation (49 Agent + 120 Task) |
| `Skill` | 21 | Skill invocation |
| `Glob` | -- | File pattern matching |
| `Write` | -- | File creation |

---

## DECISION QUICK-REFERENCE

```
New task arrives
  → Is code unfamiliar?  YES → Strategy 12 (Investigation First)
  → Is it 100+ lines?    YES → Strategy 13 (Architect First)
  → Is it security-critical? YES → Strategy 15 (N-Version)
  → Otherwise            → DEFAULT_WORKFLOW directly

Task complete
  → Strategy 2 (Outside-In Testing Gate)
  → Strategy 7 (Goal Measurement)
  → Strategy 3 (Philosophy Enforcement)

PR ready
  → Is it 500+ lines or security-sensitive? YES → Strategy 5 (Multi-Agent Review)
  → Otherwise → Standard reviewer

Something broken
  → Pre-commit hooks? → Strategy 9 (Pre-Commit Diagnostic)
  → CI failed?        → Strategy 10 (CI Diagnostic Recovery)
  → 3+ failures?      → Strategy 20 (Escalation Protocol)

Architectural question
  → Clear trade-off?  → Strategy 16 (Debate)
  → Need prioritization? → Strategy 14 (Sprint Planning)

Director action
  → Always → Strategy 17 (Dry-Run Validation) first
  → Confidence < 0.6 → Strategy 20 (Escalation Protocol)
```
