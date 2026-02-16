# Parallel Task Orchestration - User Guide

Ahoy matey! This guide be showin' ye when and how to use parallel task orchestration to scale complex software development through concurrent AI agents.

## Quick Start

**What It Is**: Deploy multiple Claude Code agents simultaneously to work on independent sub-tasks from a master GitHub issue.

**When to Use**: Large features that naturally split into 5+ independent tasks (different modules/files).

**Basic Command**:
```bash
/amplihack:parallel-orchestrate <issue-number>
```

## When to Use Parallel Orchestration

### ✅ Perfect Use Cases

#### 1. Modular Feature Development

**Example**: E-commerce shopping cart

```
Master Issue: "Implement Shopping Cart System"

Sub-Tasks (Independent):
✅ Cart data model (models/cart.py)
✅ Cart API endpoints (api/cart.py)
✅ Cart UI components (ui/cart/)
✅ Cart persistence layer (db/cart.py)
✅ Cart integration tests (tests/cart/)

Why Parallel Works:
- Each task touches different files
- No shared state between tasks
- Can be merged independently
```

**Expected Result**: 5 agents complete in ~25 minutes vs ~125 minutes sequential (5x speedup)

#### 2. Multi-Module Refactoring

**Example**: TypeScript migration

```
Master Issue: "Migrate JavaScript to TypeScript - Phase 1"

Sub-Tasks (Independent):
✅ Convert utils/ directory
✅ Convert models/ directory
✅ Convert services/ directory
✅ Convert api/ directory
✅ Update build configuration

Why Parallel Works:
- Directories are independent
- Standard conversion process per module
- No cross-module dependencies
```

#### 3. Bug Bash Results

**Example**: Quarterly bug fixes

```
Master Issue: "Q4 Bug Bash - Critical Fixes"

Sub-Tasks (Independent):
✅ Fix auth redirect loop (auth/redirect.py)
✅ Fix payment calculation error (payment/calc.py)
✅ Fix email template rendering (email/template.py)
✅ Fix export timeout (export/worker.py)
✅ Fix search pagination (search/paginate.py)

Why Parallel Works:
- Bugs in different subsystems
- No shared code between fixes
- Each fix independently testable
```

#### 4. Documentation Generation

**Example**: API documentation project

```
Master Issue: "Complete REST API Documentation"

Sub-Tasks (Independent):
✅ Document authentication endpoints
✅ Document user management endpoints
✅ Document payment processing endpoints
✅ Document reporting endpoints
✅ Create code examples and tutorials

Why Parallel Works:
- Documentation per module/API
- No dependencies between docs
- Can be reviewed independently
```

### ❌ Poor Use Cases

#### 1. Tightly Coupled Features

**Bad Example**: User authentication system

```
Master Issue: "Add User Authentication"

Sub-Tasks (DEPENDENT):
❌ Create user model
❌ Add password hashing (needs user model)
❌ Create login endpoint (needs user model + hashing)
❌ Add JWT tokens (needs login endpoint)
❌ Add session management (needs JWT)

Why Parallel FAILS:
- Sequential dependencies (A → B → C → D → E)
- Each task builds on previous
- Must run sequentially
```

**Solution**: Use standard workflow sequentially or break into fewer, larger independent tasks

#### 2. Shared Critical Files

**Bad Example**: Core utility refactoring

```
Master Issue: "Refactor Core Utilities"

Sub-Tasks (CONFLICTING):
❌ Refactor string utils (utils/string.py)
❌ Refactor date utils (utils/date.py)
❌ Refactor validation utils (utils/validate.py)

All modify: utils/__init__.py (CONFLICT!)

Why Parallel FAILS:
- All tasks modify shared __init__.py
- Guaranteed merge conflicts
- Coordination overhead > time savings
```

**Solution**: Sequential execution or restructure to avoid shared files

#### 3. Integration-Heavy Features

**Bad Example**: Payment flow integration

```
Master Issue: "Integrate Stripe Payment Flow"

Sub-Tasks (INTEGRATED):
❌ Add payment form
❌ Add Stripe API client
❌ Add payment processing
❌ Add webhook handlers
❌ Add payment UI feedback

Why Parallel FAILS:
- All components must integrate tightly
- Cannot test independently
- Integration testing needed before splitting
```

**Solution**: Build integration first, then parallelize enhancements

### Decision Framework

Use this checklist to decide:

```
Parallel Orchestration Checklist:

□ Sub-tasks touch DIFFERENT files/modules (minimal overlap)
□ Sub-tasks have NO sequential dependencies
□ Sub-tasks can be TESTED independently
□ Sub-tasks can be MERGED independently
□ At least 5+ sub-tasks identified
□ Tasks have SIMILAR complexity (no single 3x outlier)
□ Time savings > orchestration overhead (~10 minutes)

If 6-7 checked: ✅ Use parallel orchestration
If 4-5 checked: ⚠️ Consider carefully
If < 4 checked: ❌ Use sequential workflow
```

## How to Prepare a Master Issue

### Step 1: Write Clear Sub-Task Descriptions

**Good Format**:

```markdown
## Sub-Tasks

- [ ] **Add user authentication module**: Create `auth/` directory with login, logout, session management. Include unit tests.
- [ ] **Add authorization middleware**: Create `middleware/auth.py` with role-based access control. Include integration tests.
- [ ] **Implement JWT token generation**: Create `auth/jwt.py` with token creation, validation, refresh logic. Include tests.
- [ ] **Add user management API**: Create `api/users.py` with CRUD endpoints for user accounts. Include API tests.
- [ ] **Create authentication documentation**: Document all auth endpoints in `docs/api/auth.md` with examples.
```

**Key Elements**:
- ✅ Clear, actionable title
- ✅ Specific file/directory locations
- ✅ Testing requirements
- ✅ One responsibility per task

**Bad Format**:

```markdown
## Sub-Tasks

- [ ] Auth stuff
- [ ] API things
- [ ] Tests
- [ ] Docs
```

**Problems**:
- ❌ Vague descriptions
- ❌ No file locations
- ❌ Unclear scope
- ❌ Not actionable

### Step 2: Verify Independence

**Manual Validation**:

1. **File Overlap Check**:
   ```bash
   # List all files mentioned in sub-tasks
   # Verify no file appears in multiple tasks
   ```

2. **Dependency Analysis**:
   ```
   Task A depends on Task B if:
   - Task A imports code from Task B
   - Task A tests functionality added by Task B
   - Task A builds upon Task B's data structures
   ```

3. **Integration Points**:
   ```
   Identify where tasks connect:
   - Shared interfaces
   - Common utilities
   - Shared configuration

   Ensure connections are MINIMAL and WELL-DEFINED
   ```

### Step 3: Balance Complexity

**Estimate Complexity**:

| Task | Files | LOC Est | Tests | Complexity | Est Time |
|------|-------|---------|-------|------------|----------|
| Auth module | 3 | 200 | 10 | Medium | 15min |
| Auth middleware | 1 | 50 | 5 | Low | 10min |
| JWT implementation | 2 | 150 | 8 | Medium | 15min |
| User API | 2 | 180 | 12 | Medium | 18min |
| Documentation | 1 | 100 | 0 | Low | 12min |

**Good Balance**: Most tasks 10-18 minutes (no outliers > 2x average)

**Poor Balance**:
```
Task 1: 5 minutes
Task 2: 8 minutes
Task 3: 60 minutes (BLOCKER!)
Task 4: 7 minutes
```

**Solution**: Split Task 3 into smaller chunks or run separately

## Running Your First Orchestration

### Step 1: Dry Run Validation

Always start with a dry run:

```bash
/amplihack:parallel-orchestrate 1234 --dry-run
```

**Review Output**:
```
🔍 DRY RUN MODE
🚀 Parsed 5 sub-tasks from issue #1234

Sub-tasks identified:
1. Add authentication module (complexity: medium, files: 3)
2. Add authorization middleware (complexity: low, files: 1)
3. Implement JWT tokens (complexity: medium, files: 2)
4. Add user management API (complexity: medium, files: 2)
5. Create integration tests (complexity: medium, files: 1)

Independence validation:
✅ No file conflicts detected
✅ No sequential dependencies
✅ Balanced complexity (avg 15min per task)

Estimated duration: 18 minutes parallel vs 75 minutes sequential
Recommendation: ✅ Proceed with orchestration
```

**Decision Points**:
- ✅ If all validations pass → proceed
- ⚠️ If warnings appear → review and address
- ❌ If critical issues found → restructure issue

### Step 2: Start Small

**First Orchestration**:
```bash
# Limit to 3 agents first
/amplihack:parallel-orchestrate 1234 --max-workers 3
```

**Why Start Small**:
- Validate coordination works
- Test your sub-task quality
- Identify any hidden dependencies
- Learn the monitoring workflow

### Step 3: Monitor Progress

**Watch in Real-Time**:
```bash
# Terminal 1: Run orchestration
/amplihack:parallel-orchestrate 1234

# Terminal 2: Watch status files
watch -n 5 'cat .claude/runtime/parallel/1234/*.status.json'

# Terminal 3: Tail logs
tail -f .claude/runtime/logs/orch-1234-*/session.log
```

**What to Watch For**:
- ✅ Agents starting successfully
- ✅ Regular status updates (every 30s)
- ✅ PR creation within timeout period
- ⚠️ Agents stalling (no updates > 5min)
- ❌ Multiple agents failing with same error

### Step 4: Handle Results

**Success Path**:
```
🎉 All agents succeeded!
→ Review PRs for quality
→ Run CI on all PRs
→ Merge PRs sequentially
→ Close master issue
```

**Partial Success Path** (80%+ complete):
```
⚠️ 4/5 agents succeeded
→ Review successful PRs (merge ready)
→ Check failure diagnostic issue
→ Fix underlying problem
→ Retry failed task: /amplihack:parallel-orchestrate 1238 --retry
```

**Failure Path** (< 80% complete):
```
❌ Major failures detected
→ Review all agent logs
→ Identify common failure pattern
→ Fix root cause (issue structure? dependencies?)
→ Consider sequential workflow instead
```

## Best Practices

### 1. Sub-Task Granularity

**Too Large** (> 30min per task):
```
❌ Implement entire authentication system
   → Too broad, likely has internal dependencies
   → Agents will timeout
   → Hard to review PRs
```

**Too Small** (< 5min per task):
```
❌ Add single import statement
   → Orchestration overhead > task time
   → Not worth parallelizing
   → Just do it sequentially
```

**Just Right** (10-20min per task):
```
✅ Implement JWT token generation module
   → Clear scope
   → Independent functionality
   → Reasonable PR size
   → Good balance of parallelism and overhead
```

### 2. Acceptance Criteria

**Every sub-task MUST have**:
```markdown
## Acceptance Criteria
- [ ] Implementation complete
- [ ] Unit tests passing (> 80% coverage)
- [ ] Integration tests passing
- [ ] Documentation updated
- [ ] Code follows project style
- [ ] No new warnings/errors
```

**Why Critical**:
- Agents know when task is "done"
- Reduces partial implementations
- Ensures consistent quality
- Makes PRs reviewable

### 3. Error Recovery Strategy

**Plan for Failures**:
```
Expect 10-20% failure rate on first run

Common Failures:
- Import conflicts (15%)
- Test timeouts (20%)
- GitHub API errors (5%)
- Agent timeouts (10%)
- Configuration issues (5%)

Budget extra time for:
- Failure investigation (10min per failure)
- Fix implementation (20min per failure)
- Retry execution (original task time)
```

### 4. Resource Planning

**System Resources**:
```
Per Agent:
- Memory: ~500MB
- CPU: ~20%
- Disk: ~100MB temp files

For 5 Agents:
- Memory: 2.5GB required
- CPU: 100% (1 core)
- Disk: 500MB

Recommendation:
- System: >= 8GB RAM
- Max agents: <= CPU cores
- Disk space: >= 5GB free
```

**GitHub API Limits**:
```
Per Orchestration (5 agents):
- Sub-issue creation: 5 calls
- PR creation: 5 calls
- Status updates: 25 calls
- Total: ~35 API calls

Rate Limits:
- Authenticated: 5,000/hour
- Typical usage: 35-50 calls per orchestration
- Can run ~100 orchestrations per hour
```

## Common Pitfalls and Solutions

### Pitfall 1: Hidden Dependencies

**Problem**:
```
Looked independent but weren't:
- Task A creates utility function
- Task B imports that function
- Task B fails because A not merged yet
```

**Solution**:
```
1. Identify shared code upfront
2. Create shared utilities FIRST (sequential)
3. THEN parallelize tasks using those utilities
```

**Prevention**:
```bash
# Before orchestration, check imports
/amplihack:analyze src/ --check-dependencies

# Review shared module list
# Create shared code first if needed
```

### Pitfall 2: Test Environment Conflicts

**Problem**:
```
Multiple agents running tests simultaneously:
- Database port conflicts
- Cache collisions
- Temp file conflicts
```

**Solution**:
```python
# Each agent uses isolated test environment
# Configure in agent setup:
TEST_DB_PORT = 5432 + agent_id
CACHE_DIR = f".cache/agent-{agent_id}"
TEMP_DIR = f"/tmp/agent-{agent_id}"
```

### Pitfall 3: Unbalanced Task Complexity

**Problem**:
```
Task 1: 5min
Task 2: 5min
Task 3: 60min (agent-3 still running)
Task 4: 5min
Task 5: 5min

Agents 1,2,4,5 idle waiting for agent-3!
```

**Solution**:
```
Pre-orchestration:
1. Estimate task complexity
2. Split large tasks into sub-sub-tasks
3. Aim for < 2x variance in task times

Or use batching:
Batch 1: Tasks 1,2,4,5 (5min each)
Batch 2: Task 3 (60min) ← runs alone
```

### Pitfall 4: Merge Conflicts

**Problem**:
```
All PRs created successfully
But merging causes conflicts:
- Shared configuration files
- Import statement additions
- Dependency version bumps
```

**Solution**:
```
1. Review ALL PRs before merging any
2. Merge in logical order (base features first)
3. Resolve conflicts during merge, not during orchestration
4. Consider squash merging to simplify
```

## Advanced Techniques

### Technique 1: Staged Orchestration

**Use Case**: Large features with dependency layers

```markdown
## Phase 1: Foundation (Parallel)
- [ ] Data models
- [ ] Database migrations
- [ ] API client setup

↓ MERGE ALL, THEN:

## Phase 2: Core Features (Parallel)
- [ ] Feature A implementation
- [ ] Feature B implementation
- [ ] Feature C implementation

↓ MERGE ALL, THEN:

## Phase 3: Integration (Sequential)
- [ ] Integration tests
- [ ] E2E tests
- [ ] Documentation
```

**Commands**:
```bash
# Phase 1
/amplihack:parallel-orchestrate 1000  # Foundation tasks

# Wait for merge, then Phase 2
/amplihack:parallel-orchestrate 1001  # Core features

# Phase 3 (sequential)
# Standard workflow
```

### Technique 2: Mixed Orchestration

**Use Case**: Some tasks parallel, others sequential

```markdown
## Independent Tasks (Parallel)
- [ ] Add feature A
- [ ] Add feature B
- [ ] Add feature C

## Sequential Tasks (After merge)
- [ ] Integration testing
- [ ] Performance optimization
- [ ] Documentation
```

**Commands**:
```bash
# Parallel phase
/amplihack:parallel-orchestrate 2000 --tasks 1,2,3

# After merge, sequential phase
# Use standard workflow for tasks 4,5,6
```

### Technique 3: Retry with Adjustments

**Use Case**: Orchestration failed, need to retry with changes

```bash
# Initial run (some failures)
/amplihack:parallel-orchestrate 3000

# Review failures, adjust:
# - Increase timeout for slow tasks
# - Reduce max_workers if resource-constrained
# - Fix shared dependency issues

# Retry with adjustments
/amplihack:parallel-orchestrate 3000 --retry \
  --timeout 3600 \
  --max-workers 3
```

## Measuring Success

### Metrics to Track

**Throughput**:
```
Time Savings = Sequential Time - Parallel Time
Speedup Ratio = Sequential Time / Parallel Time

Example:
Sequential: 90 minutes (5 tasks × 18min)
Parallel: 22 minutes (longest task + overhead)
Speedup: 4.1x
```

**Quality**:
```
Success Rate = Successful Agents / Total Agents
Target: >= 80%

PR Merge Rate = Merged PRs / Created PRs
Target: >= 90%

Rework Rate = PRs requiring changes / Total PRs
Target: <= 20%
```

**Efficiency**:
```
Orchestration Overhead = Parallel Time - Longest Task Time
Target: <= 10 minutes

Resource Utilization = Active Agent Time / Total Agent Time
Target: >= 70%
```

### Continuous Improvement

**After Each Orchestration**:
```
1. Review metrics dashboard
2. Identify failure patterns
3. Improve sub-task definitions
4. Refine complexity estimates
5. Update team playbook
```

**Monthly Review**:
```
- Total orchestrations: X
- Average speedup: Yx
- Success rate: Z%
- Common failure patterns: [list]
- Top improvements needed: [list]
```

## Team Adoption

### Rollout Plan

**Week 1-2: Learn**
```
- Read documentation
- Run example orchestrations
- Practice on small features (3 tasks)
```

**Week 3-4: Practice**
```
- Orchestrate real features (5 tasks)
- Share learnings in team meetings
- Document team-specific patterns
```

**Week 5+: Scale**
```
- Regular orchestration for suitable features
- Refine best practices
- Train new team members
```

### Team Guidelines

**When Team Member Creates Master Issue**:
```markdown
## Orchestration Checklist

Before creating master issue:
- [ ] Feature naturally splits into 5+ independent tasks
- [ ] Each task has clear acceptance criteria
- [ ] File overlap minimal (< 10%)
- [ ] No sequential dependencies
- [ ] Complexity balanced (no task > 2x average)
- [ ] Test environment isolated

Label: `parallel-orchestration-ready`
```

**When Team Member Reviews PRs**:
```markdown
## PR Review Checklist (Orchestrated Tasks)

- [ ] Tests passing
- [ ] Meets acceptance criteria from sub-issue
- [ ] No unintended file changes
- [ ] Documentation complete
- [ ] Follows project style
- [ ] Ready to merge independently

Note: Review ALL orchestrated PRs before merging ANY
```

## Troubleshooting Guide

### Quick Diagnostic

**If orchestration fails, check in order**:

1. **Master Issue Format**
   ```bash
   # Verify parseable sub-tasks
   /amplihack:parallel-orchestrate <issue> --dry-run
   ```

2. **System Resources**
   ```bash
   free -h  # Check memory
   df -h    # Check disk
   top      # Check CPU
   ```

3. **GitHub API Access**
   ```bash
   gh auth status
   gh api rate_limit
   ```

4. **Agent Logs**
   ```bash
   tail -100 .claude/runtime/logs/orch-*/agent-*.log
   ```

5. **Status Files**
   ```bash
   cat .claude/runtime/parallel/<issue>/*.status.json
   ```

### Common Error Messages

**"Parse failed: No sub-tasks found"**
```
Problem: Master issue format not recognized
Solution: Add checklist or numbered list of sub-tasks
```

**"Validation failed: Dependencies detected"**
```
Problem: Sub-tasks not independent
Solution: Review dependencies, restructure or use sequential
```

**"Agent timeout after 30min"**
```
Problem: Task took longer than expected
Solution: Increase timeout with --timeout 3600
```

**"GitHub API rate limit exceeded"**
```
Problem: Too many API calls in short time
Solution: Wait 1 hour or authenticate with higher-limit token
```

**"Import error: module not found"**
```
Problem: Agent missing dependencies
Solution: Ensure shared code exists before orchestration
```

## Further Reading

- **Skill Documentation**: `.claude/skills/parallel-task-orchestrator/SKILL.md` - Deep technical details
- **Command Reference**: `.claude/commands/amplihack/parallel-orchestrate.md` - Complete command documentation
- **Technical Reference**: `docs/parallel-orchestration/TECHNICAL_REFERENCE.md` - API and protocol specs
- **Examples**: `docs/parallel-orchestration/EXAMPLES.md` - Real-world case studies

---

**Remember**: Parallel orchestration be a powerful tool, but not every task be fittin' fer parallel work. Use yer judgment, start small, and scale as ye learn what works fer yer codebase! ⚓