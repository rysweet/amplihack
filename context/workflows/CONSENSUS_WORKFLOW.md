---
name: CONSENSUS_WORKFLOW
version: 1.0.0
description: Enhanced workflow with multi-agent consensus at critical decision points
steps: 21
phases:
  - requirements-with-debate
  - design-with-consensus
  - n-version-implementation
  - expert-panel-refactoring
  - expert-panel-review
  - final-consensus-validation
success_criteria:
  - "All steps completed with consensus validation"
  - "Multi-agent debate for ambiguous requirements"
  - "Expert panel approval at critical gates"
  - "N-version programming for critical code"
  - "PR is mergeable with unanimous approval"
philosophy_alignment:
  - principle: Reduced Risk
    application: Multiple perspectives catch errors single approach misses
  - principle: Evidence-Based Decisions
    application: Consensus requires reasoned debate with supporting evidence
  - principle: Quality Over Speed
    application: Accept higher latency for correctness and thoroughness
references:
  workflows:
    - DEFAULT_WORKFLOW.md
    - DEBATE_WORKFLOW.md
    - N_VERSION_WORKFLOW.md
customizable: true
---

# Consensus-Augmented Workflow

This workflow enhances the default coding workflow with consensus mechanisms at critical decision points. Use this workflow when:

> **DEPRECATION WARNING**: Markdown workflows deprecated. See `docs/WORKFLOW_TO_SKILLS_MIGRATION.md`

- Requirements are ambiguous or complex
- Design decisions have significant architectural impact
- Multiple valid implementation approaches exist
- Critical code requires extra validation
- Maximum code quality and correctness are paramount

## How This Workflow Works

**This workflow extends DEFAULT_WORKFLOW.md with:**

- Multi-Agent Debate for ambiguous requirements and critical design decisions
- N-Version Programming for critical code paths
- Expert Panel reviews for refactoring and final PR review
- Consensus-driven decision making at key points

**Execution approach:**

- Use `/ultrathink` with this workflow selected in USER_PREFERENCES.md
- UltraThink reads this workflow and orchestrates consensus mechanisms
- Specialized agents collaborate through structured protocols
- Consensus ensures correctness and quality

## When This Workflow Applies

Use this workflow for:

- Complex features with architectural implications
- Mission-critical code requiring high reliability
- Ambiguous requirements needing clarification
- Security-sensitive implementations
- Performance-critical components
- Public APIs with long-term commitments

## The Consensus-Augmented Workflow

### Step 1: Rewrite and Clarify Requirements with Consensus

**CONSENSUS TRIGGER**: If requirements are ambiguous, complex, or involve multiple stakeholders

**Agent Orchestration:**

- [ ] **FIRST: Identify explicit user requirements** that CANNOT be optimized away
- [ ] **Always use** prompt-writer agent to clarify task requirements
- [ ] **Use** analyzer agent to understand existing codebase context
- [ ] **Use** ambiguity agent if requirements are unclear

**IF AMBIGUOUS → Multi-Agent Debate:**

- [ ] **Deploy** 3-5 specialized agents based on domain (architect, security, api-designer, database, tester)
- [ ] **Round 1**: Each agent presents their interpretation of requirements
- [ ] **Round 2**: Agents challenge each other's assumptions
- [ ] **Round 3**: Synthesize consensus view of requirements
- [ ] **Orchestrator**: Resolve any remaining conflicts and document final requirements

**Standard Tasks:**

- [ ] Remove all ambiguity from task description
- [ ] Define clear success criteria
- [ ] Document acceptance criteria with measurable outcomes
- [ ] **CRITICAL: Pass explicit requirements to ALL subsequent agents**

**Consensus Output**: Unified, unambiguous requirements document

### Step 2: Create GitHub Issue

- [ ] **Use** GitHub issue creation tool via agent
- [ ] Create issue using `gh issue create`
- [ ] Include clear problem description from consensus
- [ ] Define requirements and constraints
- [ ] Add success criteria with measurable outcomes
- [ ] Assign appropriate labels (consensus, critical, complex)
- [ ] Tag issue with consensus decision record reference

### Step 3: Setup Worktree and Branch

- [ ] **Always use** worktree-manager agent for worktree operations
- [ ] Create new git worktree in `./worktrees/{branch-name}` for isolated development
- [ ] Create branch with format: `feat/issue-{number}-{brief-description}`
- [ ] Command: `git worktree add ./worktrees/{branch-name} -b {branch-name}`
- [ ] Push branch to remote with tracking: `git push -u origin {branch-name}`
- [ ] Switch to new worktree directory: `cd ./worktrees/{branch-name}`
- [ ] Document consensus decisions in `@amplihack:runtime/logs/<session_id>/CONSENSUS_DECISIONS.md`

### Step 4: Research and Design with TDD (ALWAYS CONSENSUS)

**MANDATORY CONSENSUS TRIGGER**: Design decisions have long-term architectural impact

**Multi-Agent Debate for Architecture:**

- [ ] **Deploy design agents in parallel**: architect, api-designer, database, security, tester
- [ ] **Round 1 - Independent Analysis**: Each agent proposes their design approach
  - architect: System architecture, module boundaries, patterns
  - api-designer: API contracts, interfaces, integration points
  - database: Data models, schemas, query patterns
  - security: Threat model, security requirements, mitigations
  - tester: Testability analysis, test strategy, TDD approach
- [ ] **Round 2 - Cross-Examination**: Agents challenge each other's designs
  - Identify conflicts between designs
  - Question assumptions and trade-offs
  - Explore edge cases and failure modes
  - Debate scalability and maintainability
- [ ] **Round 3 - Consensus Building**: Synthesize unified design
  - Resolve conflicts through reasoned debate
  - Document trade-off decisions with rationale
  - Create integrated design specification
  - Ensure all agents agree on final approach
- [ ] **Orchestrator**: Finalize design and resolve deadlocks
  - Break ties when consensus cannot be reached
  - Document all dissenting opinions
  - Explain final decision rationale

**TDD with Consensus:**

- [ ] **Use** tester agent to write comprehensive failing tests based on consensus design
- [ ] Ensure tests cover all agreed-upon requirements
- [ ] Include edge cases identified during debate

**Design Documentation:**

- [ ] Document module specifications with consensus design
- [ ] Create detailed implementation plan with agent agreement
- [ ] Identify risks and dependencies from all perspectives
- [ ] Record consensus decision log with:
  - What was decided
  - Why (rationale from all agents)
  - Alternatives considered and rejected
  - Trade-offs accepted

**Consensus Output**: Unified, validated design specification

### Step 5: Implement the Solution (N-VERSION FOR CRITICAL CODE)

**CONSENSUS TRIGGER**: Implementation involves critical code paths (security, safety, financial, data integrity)

**Standard Implementation:**

- [ ] **Always use** builder agent to implement from specifications
- [ ] **Use** integration agent for external service connections
- [ ] Follow the consensus architecture design exactly
- [ ] Make failing tests pass iteratively
- [ ] Ensure all requirements are met

**IF CRITICAL CODE → N-Version Programming:**

- [ ] **Identify critical sections**: security checks, financial calculations, data integrity logic, safety-critical paths
- [ ] **Deploy multiple builder agents**: 2-3 independent implementations
- [ ] **Each builder**: Implements critical section independently from same spec
- [ ] **Cross-validation**: Compare implementations for:
  - Logic correctness
  - Edge case handling
  - Error handling approaches
  - Performance characteristics
- [ ] **Synthesize best solution**: Combine best aspects from each version
- [ ] **Verification**: All agents review final implementation
- [ ] **Consensus vote**: Majority approval required for critical code

**Implementation Quality:**

- [ ] Add comprehensive inline documentation
- [ ] Include error handling for all failure modes
- [ ] Log critical decision points for debugging
- [ ] Ensure zero stubs or placeholders

**Consensus Output**: Production-ready, consensus-validated implementation

### Step 6: Refactor and Simplify (EXPERT PANEL REVIEW)

**MANDATORY CONSENSUS TRIGGER**: Refactoring requires validation that simplification preserves requirements

**Expert Panel Review:**

- [ ] **Deploy refactoring panel**: cleanup agent, optimizer agent, reviewer agent, patterns agent
- [ ] **CRITICAL: Provide all agents with original user requirements**
- [ ] **Round 1 - Independent Review**: Each agent proposes simplifications
  - cleanup: Ruthless simplification opportunities WITHIN constraints
  - optimizer: Performance improvement opportunities
  - reviewer: Code quality and maintainability improvements
  - patterns: Pattern compliance and best practices
- [ ] **Round 2 - Validation**: Cross-check proposed changes
  - Verify no explicit user requirements are violated
  - Ensure simplifications don't introduce bugs
  - Validate performance improvements are safe
  - Confirm pattern compliance
- [ ] **Round 3 - Consensus on Changes**: Agree on final refactoring plan
  - All agents must approve each change
  - Document rationale for keeping complexity when necessary
  - Explain why certain simplifications were rejected

**Refactoring Execution:**

- [ ] Apply consensus-approved simplifications only
- [ ] Remove unnecessary abstractions (that weren't explicitly requested)
- [ ] Eliminate dead code (unless user explicitly wanted it)
- [ ] Simplify complex logic (without violating user specifications)
- [ ] Ensure single responsibility principle
- [ ] Verify no placeholders remain - no stubs, no TODOs, no swallowed exceptions, no unimplemented functions - follow the zero-BS principle.

**Final Validation:**

- [ ] **VALIDATE: All explicit user requirements still preserved**
- [ ] Run all tests to ensure refactoring didn't break functionality
- [ ] Performance benchmarks show no regressions
- [ ] All panel agents sign off on final state

**Consensus Output**: Simplified, optimized code with unanimous panel approval

### Step 7: Run Tests and Pre-commit Hooks

- [ ] **Use** pre-commit-diagnostic agent if hooks fail
- [ ] Run all unit tests (must pass with consensus-validated code)
- [ ] Execute `pre-commit run --all-files`
- [ ] Fix any linting issues
- [ ] Fix any formatting issues
- [ ] Resolve type checking errors
- [ ] Iterate until all checks pass
- [ ] Verify tests validate consensus requirements

### Step 8: Mandatory Local Testing (NOT in CI)

**CRITICAL: Test all changes locally in realistic scenarios BEFORE committing.**

- [ ] **Test simple use cases** - Basic functionality verification
- [ ] **Test complex use cases** - Edge cases and longer operations
- [ ] **Test consensus-critical paths** - Validate critical code sections work correctly
- [ ] **Test integration points** - External dependencies and APIs
- [ ] **Verify no regressions** - Ensure existing functionality still works
- [ ] **Document test results** - What was tested and results
- [ ] **Consensus validation**: If critical code, verify with multiple test scenarios
- [ ] **RULE: Never commit without local testing**

**Examples of required tests:**

- If proxy changes: Test simple and long requests locally
- If API changes: Test with real client requests
- If CLI changes: Run actual commands with various options
- If database changes: Test with actual data operations
- If critical code: Test all identified critical paths thoroughly

**Why this matters:**

- CI checks can't catch all real-world issues
- Local testing catches problems before they reach users
- Faster feedback loop than waiting for CI
- Prevents embarrassing failures after merge
- Validates consensus decisions in practice

### Step 9: Commit and Push

- [ ] Stage all changes
- [ ] Write detailed commit message referencing consensus decisions
- [ ] Reference issue number in commit
- [ ] Describe what changed and why (include consensus rationale)
- [ ] Note which consensus mechanisms were used
- [ ] Push to remote branch
- [ ] Verify push succeeded

**Commit Message Format:**

```
feat(scope): brief description

Detailed description of changes.

Consensus Mechanisms Used:
- Multi-Agent Debate: Requirements clarification
- Multi-Agent Debate: Architecture design
- N-Version Programming: [critical sections]
- Expert Panel: Refactoring review

Resolves #123
```

### Step 10: Open Pull Request

- [ ] Create PR using `gh pr create`
- [ ] Link to the GitHub issue
- [ ] Write comprehensive description including:
  - Consensus decisions made
  - Agents involved in debate/review
  - Rationale for key decisions
  - Trade-offs accepted
  - Critical code sections validated via N-Version
- [ ] Include detailed test plan covering consensus-critical paths
- [ ] Add screenshots if UI changes
- [ ] Request appropriate reviewers
- [ ] Tag PR with `consensus-validated` label

### Step 11: Review the PR (ALWAYS EXPERT PANEL)

**MANDATORY CONSENSUS TRIGGER**: Final PR review requires expert panel validation

**Expert Panel Review:**

- [ ] **Deploy review panel**: reviewer agent, security agent, optimizer agent, patterns agent, tester agent
- [ ] **Parallel independent reviews**:
  - reviewer: Comprehensive code review, philosophy compliance, requirements validation
  - security: Security vulnerability assessment, threat validation
  - optimizer: Performance analysis, bottleneck identification
  - patterns: Pattern compliance, best practices verification
  - tester: Test coverage analysis, test quality review
- [ ] **Consolidate findings**: Orchestrator synthesizes all review feedback
- [ ] **Prioritize issues**: Critical vs. nice-to-have improvements
- [ ] **Consensus on required changes**: Panel must agree on what's mandatory vs. optional

**Review Documentation:**

- [ ] Check code quality and standards
- [ ] Verify philosophy compliance
- [ ] Ensure adequate test coverage
- [ ] Validate consensus decisions were implemented correctly
- [ ] Ensure there are no TODOs, stubs, or swallowed exceptions, no unimplemented functions - follow the zero-BS principle.
- [ ] Post consolidated review as PR comment with:
  - Summary of panel consensus
  - Required changes (unanimous agreement needed)
  - Optional improvements (noted but not blocking)
  - Validation that consensus mechanisms were properly applied

**Consensus Output**: Unified review with clear action items

### Step 12: Implement Review Feedback

- [ ] Review all feedback comments from expert panel
- [ ] Think carefully about each one and decide how to address it
- [ ] **For required changes**: Must implement (panel consensus)
- [ ] **For optional changes**: Evaluate cost/benefit, may defer
- [ ] **Always use** builder agent to implement changes
- [ ] **Use** relevant specialized agents for specific feedback
- [ ] Address each review comment with response
- [ ] Push updates to PR
- [ ] Respond to review comments by posting replies
- [ ] Ensure all tests still pass after changes
- [ ] Ensure PR is still mergeable
- [ ] Request re-review from panel if significant changes

### Step 13: Philosophy Compliance Check (EXPERT PANEL)

**MANDATORY CONSENSUS TRIGGER**: Final philosophy validation requires expert panel

**Expert Panel Philosophy Review:**

- [ ] **Deploy compliance panel**: reviewer agent, patterns agent, cleanup agent
- [ ] **Parallel compliance checks**:
  - reviewer: Final philosophy validation, zero-BS verification
  - patterns: Pattern compliance, regeneratable design verification
  - cleanup: No dead code, no stubs, ruthless simplicity achieved
- [ ] **Consensus validation**:
  - All agents must agree code meets philosophy
  - Verify ruthless simplicity achieved WITHIN user requirements
  - Confirm bricks & studs pattern followed
  - Ensure zero-BS implementation (no stubs, no placeholders)
  - Verify all tests passing
  - Check documentation completeness

**Compliance Documentation:**

- [ ] Document that all agents approve philosophy compliance
- [ ] Note any areas where complexity is justified by user requirements
- [ ] Confirm consensus mechanisms added appropriate value
- [ ] Validate all consensus decisions were sound

**Consensus Output**: Unanimous philosophy compliance approval

### Step 14: Ensure PR is Mergeable

- [ ] Check CI status (all checks passing)
- [ ] **Always use** ci-diagnostic-workflow agent if CI fails
- [ ] Resolve any merge conflicts
- [ ] Verify all review comments addressed
- [ ] Confirm PR has panel approval (all experts approved)
- [ ] Validate consensus decisions documented in PR
- [ ] Notify that PR is ready to merge (with consensus validation badge)

**Mergeable Criteria:**

- All CI checks passing
- All tests passing
- Expert panel approval received
- No unresolved review comments
- Consensus decisions documented
- Philosophy compliance confirmed

### Step 15: Final Cleanup and Verification (EXPERT PANEL)

**MANDATORY CONSENSUS TRIGGER**: Final quality gate requires expert panel validation

**Expert Panel Final Review:**

- [ ] **CRITICAL: Provide all agents with original user requirements AGAIN**
- [ ] **Deploy final quality panel**: cleanup agent, reviewer agent, patterns agent
- [ ] **Final consensus validation**:
  - cleanup: Final quality pass WITHIN user constraints
  - reviewer: All changes comply with philosophy
  - patterns: Module boundaries remain clean, regeneratable design intact
- [ ] **Unanimous approval required**:
  - Remove any temporary artifacts or test files (unless user wanted them)
  - Eliminate unnecessary complexity (that doesn't violate user requirements)
  - Verify module boundaries remain clean
  - Ensure zero dead code or stub implementations (unless explicitly requested)

**Final Validation:**

- [ ] **FINAL CHECK: All explicit user requirements preserved**
- [ ] Confirm PR remains mergeable after cleanup
- [ ] All consensus mechanisms properly applied
- [ ] Consensus decisions yielded high-quality result
- [ ] Expert panel unanimously approves final state
- [ ] Document lessons learned from consensus process

**Consensus Output**: Production-ready, consensus-validated, philosophy-compliant code

## Consensus Mechanisms Reference

### Multi-Agent Debate

**When to use**: Ambiguous requirements, complex design decisions, architectural choices

**Process**:

1. Deploy 3-5 domain-relevant agents
2. Round 1: Independent analysis and proposals
3. Round 2: Cross-examination and challenge assumptions
4. Round 3: Synthesize consensus through reasoned debate
5. Orchestrator: Resolve deadlocks and document decisions

**Output**: Unified decision with documented rationale, alternatives considered, and trade-offs

### N-Version Programming

**When to use**: Critical code paths (security, financial, safety-critical, data integrity)

**Process**:

1. Identify critical code sections
2. Deploy 2-3 builder agents for independent implementation
3. Each implements same specification independently
4. Cross-validate implementations
5. Synthesize best approach
6. Consensus vote on final implementation

**Output**: Validated critical code with multiple independent reviews

### Expert Panel Review

**When to use**: Refactoring decisions, PR reviews, philosophy compliance checks

**Process**:

1. Deploy panel of relevant expert agents
2. Independent parallel reviews
3. Consolidate findings
4. Reach consensus on required vs. optional changes
5. Document unanimous decisions

**Output**: Comprehensive review with clear consensus on actions

## Customization

To customize this workflow:

1. Edit this file to modify consensus triggers or mechanisms
2. Adjust which steps require consensus (add/remove ALWAYS CONSENSUS markers)
3. Change consensus mechanism parameters (number of agents, rounds, etc.)
4. Save your changes
5. The updated workflow will be used when selected

## Performance vs. Quality Trade-off

**This workflow is slower but produces higher quality code:**

- More agent invocations = higher latency
- Multiple rounds of debate = more time
- Consensus building = additional overhead
- Expert panels = thorough but expensive reviews

**Use strategically**:

- Default workflow for most tasks (faster)
- Consensus workflow for critical/complex tasks (thorough)
- Switch via `/amplihack:customize set-workflow`

## Philosophy Integration

This workflow maintains all core philosophy principles:

- **Ruthless Simplicity**: Expert panels validate simplification
- **Bricks & Studs**: Architecture debate ensures clean boundaries
- **Zero-BS**: Multiple agents verify no stubs/placeholders
- **Regeneratable**: Design consensus ensures clear specifications
- **Test-Driven**: Consensus on test strategy before implementation

## Success Metrics

Consensus workflow succeeds when:

- All consensus triggers properly activated
- Multi-agent debates yield clear decisions
- N-Version validations catch potential issues
- Expert panels provide unanimous approval
- Consensus decisions documented and traceable
- Final code meets all requirements with high quality
- PR is mergeable with full validation

---

**Remember**: Consensus adds rigor but also latency. Use for tasks where correctness and quality justify the extra time investment.
