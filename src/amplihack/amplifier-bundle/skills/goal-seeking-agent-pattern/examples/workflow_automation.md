# Example: Workflow Automation with Goal-Seeking Agents

## Scenario: Release Workflow Automation

### Problem Statement

Manual release workflows are:

- **Time-consuming**: 2-3 hours per release
- **Error-prone**: Easy to miss steps (tagging, changelogs, notifications)
- **Context-dependent**: Different steps for hotfixes vs features
- **Environment-specific**: Staging and production have different requirements
- **Recovery-intensive**: Failures require manual rollback

### Is Goal-Seeking Appropriate?

Apply the 5-question decision framework:

**Q1: Well-defined objective but flexible path?**

- **YES**: Objective is clear (release software to production)
- Multiple paths:
  - Hotfix: Skip QA staging, direct to production
  - Feature: Full staging validation, gradual rollout
  - Patch: Automated tests only, fast-track
- Success criteria: Deployed, tested, monitored

**Q2: Multiple phases with dependencies?**

- **YES**: 5 phases with clear dependencies
  1. Pre-release validation (tests, lint, security scan)
  2. Artifact creation (build, tag, changelog)
  3. Staging deployment (deploy, smoke tests)
  4. Production deployment (gradual rollout, health checks)
  5. Post-release (monitoring, notifications, documentation)

**Q3: Autonomous recovery valuable?**

- **YES**: Failures are common and recoverable
  - Build failures: Retry with clean cache
  - Deployment failures: Rollback to previous version
  - Test failures: Re-run flaky tests
  - Monitoring issues: Wait and retry
- Human intervention is slow (especially after-hours)

**Q4: Context affects approach?**

- **YES**: Release strategy varies by:
  - Change type (hotfix/feature/patch)
  - Environment (staging/production)
  - System state (healthy/degraded)
  - Time of day (business hours/off-hours)

**Q5: Complexity justified?**

- **YES**: Problem is frequent and valuable
  - Frequency: 2-3 releases per week
  - Manual time: 2-3 hours per release
  - Value: 4-6 hours saved per week
  - High value: Reduces release anxiety, enables more frequent releases

**Conclusion**: All 5 YES → Goal-seeking agent is appropriate

## Goal-Seeking Agent Design

### Goal Definition

```markdown
# Goal: Automate Software Release Workflow

## Objective

Execute end-to-end release workflow from code freeze to production deployment,
adapting strategy based on change type (hotfix/feature/patch) and environment health.

## Success Criteria

- All pre-release validations pass (tests, lint, security)
- Artifacts created and versioned (Docker image, Git tag, changelog)
- Staging deployment successful with smoke tests passing
- Production deployment completes with health checks passing
- Post-release monitoring shows no regressions
- Stakeholders notified of release status

## Constraints

- Zero downtime for production deployment
- Rollback capability at any phase
- Must complete within 60 minutes
- Security scans must pass before production
- Requires human approval for production (no auto-deploy)

## Context

- Frequency: 2-3 times per week
- Priority: High (blocking features/fixes)
- Scale: Medium (10-20 microservices)
```

### Execution Plan

```python
from amplihack.goal_agent_generator import ObjectivePlanner, PromptAnalyzer

# Analyze goal
analyzer = PromptAnalyzer()
goal_def = analyzer.analyze_text(goal_text)

# Generate plan
planner = ObjectivePlanner()
plan = planner.generate_plan(goal_def)

# Result: 5-phase execution plan
```

**Phase 1: Pre-Release Validation** (15 minutes, parallel)

- Run test suite (unit, integration, e2e)
- Execute linters and formatters
- Run security vulnerability scan
- Validate API contracts
- Check database migration scripts

Dependencies: None
Parallel-safe: Yes (tests/lint/security can run concurrently)
Success indicators:

- All tests pass (100%)
- No linting violations
- No security vulnerabilities (or approved exceptions)
- API contracts compatible
- Migrations validated

**Phase 2: Artifact Creation** (10 minutes, depends on Phase 1)

- Build Docker images
- Create Git tag (semantic versioning)
- Generate changelog from commits
- Package release notes
- Upload artifacts to registry

Dependencies: Phase 1 (validation must pass)
Parallel-safe: No (artifacts depend on validation)
Success indicators:

- Docker images built and pushed
- Git tag created
- Changelog generated
- Artifacts in registry

**Phase 3: Staging Deployment** (15 minutes, depends on Phase 2)

- Deploy to staging environment
- Run smoke tests
- Execute integration tests
- Monitor metrics for 5 minutes
- Verify health checks

Dependencies: Phase 2 (artifacts must exist)
Parallel-safe: No (production waits for staging validation)
Success indicators:

- Staging deployment successful
- Smoke tests pass
- Integration tests pass
- Metrics within normal range
- Health checks passing

**Phase 4: Production Deployment** (15 minutes, depends on Phase 3)

- Gradual rollout (10% → 50% → 100%)
- Monitor metrics at each stage
- Verify health checks continuously
- Run production smoke tests
- Confirm zero errors

Dependencies: Phase 3 (staging must pass)
Parallel-safe: No (production is final critical phase)
Success indicators:

- Gradual rollout completes
- No error rate increase
- Latency within SLA
- Health checks passing
- Smoke tests pass

**Phase 5: Post-Release** (5 minutes, depends on Phase 4)

- Update documentation
- Send notifications (Slack, email)
- Create release announcement
- Update monitoring dashboards
- Archive release artifacts

Dependencies: Phase 4 (deployment must succeed)
Parallel-safe: Yes (documentation/notifications can run concurrently)
Success indicators:

- Documentation updated
- Stakeholders notified
- Release announcement published
- Dashboards updated

**Total Duration**: 60 minutes (estimated)

### Implementation

```python
from amplihack.goal_agent_generator import (
    PromptAnalyzer,
    ObjectivePlanner,
    SkillSynthesizer,
    AgentAssembler,
    GoalAgentPackager,
)
from pathlib import Path

# Step 1: Define goal
goal_text = """
Automate software release workflow:
- Pre-release validation (tests, lint, security)
- Artifact creation (build, tag, changelog)
- Staging deployment with smoke tests
- Production deployment with gradual rollout
- Post-release monitoring and notifications

Adapt strategy based on change type (hotfix/feature/patch).
"""

# Step 2: Analyze and plan
analyzer = PromptAnalyzer()
goal_def = analyzer.analyze_text(goal_text)

planner = ObjectivePlanner()
execution_plan = planner.generate_plan(goal_def)

# Step 3: Synthesize skills
synthesizer = SkillSynthesizer()
skills = synthesizer.synthesize(execution_plan)

# Result: 5 skills identified
# - validator: Pre-release validation
# - builder: Artifact creation
# - deployer: Staging/production deployment
# - monitor: Health checks and metrics
# - documenter: Post-release tasks

# Step 4: Assemble agent
assembler = AgentAssembler()
agent_bundle = assembler.assemble(
    goal_definition=goal_def,
    execution_plan=execution_plan,
    skills=skills,
    bundle_name="release-workflow-agent"
)

# Step 5: Package for deployment
packager = GoalAgentPackager()
packager.package(
    bundle=agent_bundle,
    output_dir=Path(".claude/agents/goal-driven/release-workflow-agent")
)

print(f"Agent created: {agent_bundle.name}")
print(f"Phases: {len(execution_plan.phases)}")
print(f"Skills: {[s.name for s in skills]}")
print(f"Estimated duration: {execution_plan.total_estimated_duration}")
```

### Adaptive Behavior

The agent adapts based on context:

**Hotfix Release** (urgent bug fix):

```python
# Phase 1: Minimal validation (skip long-running tests)
if release_type == "hotfix":
    validation_scope = "critical-tests-only"
    # Run only tests related to fix
    # Skip full integration suite

# Phase 3: Skip staging (go direct to production)
if release_type == "hotfix" and severity == "critical":
    skip_staging = True
    # Deploy directly to production with extra monitoring

# Phase 4: Faster rollout (urgency vs safety trade-off)
if release_type == "hotfix":
    rollout_schedule = [50, 100]  # Skip 10% stage
```

**Feature Release** (standard):

```python
# Phase 1: Full validation
if release_type == "feature":
    validation_scope = "comprehensive"
    # Run all tests, security scans, performance tests

# Phase 3: Full staging validation
if release_type == "feature":
    staging_duration = 15  # minutes
    # Run extensive smoke tests and integration tests

# Phase 4: Gradual rollout
if release_type == "feature":
    rollout_schedule = [10, 25, 50, 100]  # Cautious rollout
```

**Degraded Environment** (system issues):

```python
# If environment is degraded, delay release
if environment_health < HEALTH_THRESHOLD:
    escalate(
        reason="Environment health below threshold",
        current_health=environment_health,
        recommendation="Wait for health to improve or proceed with extra caution"
    )

# If proceeding, add extra monitoring
if user_approves_risky_release:
    monitoring_intensity = "high"
    rollback_readiness = "immediate"
```

### Error Recovery

The agent implements three recovery strategies:

**Strategy 1: Retry with Backoff** (transient failures)

```python
# Build failures (network issues, resource contention)
@retry(max_attempts=3, backoff=exponential)
def build_artifacts():
    try:
        docker_build()
        docker_push()
    except NetworkError:
        # Retry automatically
        raise
    except DiskSpaceError:
        # Not transient, escalate
        escalate("Disk space exhausted, cannot build")
```

**Strategy 2: Alternative Strategy** (approach failures)

```python
# Deployment strategy failures
def deploy_to_production():
    strategies = [
        gradual_rollout_strategy,
        blue_green_deployment_strategy,
        rolling_update_strategy
    ]

    for strategy in strategies:
        try:
            return strategy.execute()
        except StrategyFailedError as e:
            log_failure(strategy, e)
            continue  # Try next strategy

    escalate("All deployment strategies failed")
```

**Strategy 3: Rollback** (safety mechanism)

```python
# Automatic rollback on health check failures
def monitor_deployment_health():
    for check in health_checks:
        if not check.passing():
            # Initiate automatic rollback
            rollback_deployment()
            escalate(
                reason="Health checks failing after deployment",
                failed_checks=[check.name for check in health_checks if not check.passing()],
                action_taken="Automatic rollback completed"
            )
```

### Execution Example

```
Release Workflow Agent: Starting

Phase 1: Pre-Release Validation [In Progress]
├── Running test suite... ✓ COMPLETED (458 tests, 0 failures, 12 minutes)
├── Executing linters... ✓ COMPLETED (0 violations, 2 minutes)
├── Security scan... ✗ FAILED (1 medium vulnerability found)
│   └── Analyzing vulnerability...
│   └── Checking for approved exceptions...
│   └── Found approved exception (CVE-2023-12345, expires 2025-12-01)
│   └── ✓ PASS (approved exception)
└── Validating migrations... ✓ COMPLETED (3 migrations validated, 1 minute)

Phase 1: ✓ COMPLETED (15 minutes)

Phase 2: Artifact Creation [In Progress]
├── Building Docker image... ✓ COMPLETED (image: app:v1.2.3, 6 minutes)
├── Creating Git tag... ✓ COMPLETED (tag: v1.2.3, 10 seconds)
├── Generating changelog... ✓ COMPLETED (15 commits since v1.2.2, 30 seconds)
└── Pushing to registry... ✓ COMPLETED (registry.example.com/app:v1.2.3, 3 minutes)

Phase 2: ✓ COMPLETED (10 minutes)

Phase 3: Staging Deployment [In Progress]
├── Deploying to staging... ✓ COMPLETED (3 replicas, 4 minutes)
├── Running smoke tests... ✓ COMPLETED (12/12 tests passed, 3 minutes)
├── Integration tests... ✓ COMPLETED (25/25 tests passed, 5 minutes)
└── Monitoring metrics... ✓ PASS (error rate: 0%, latency: 45ms avg, 3 minutes)

Phase 3: ✓ COMPLETED (15 minutes)

Phase 4: Production Deployment [HUMAN APPROVAL REQUIRED]

┌─────────────────────────────────────────────────────────────────┐
│ Production Deployment Ready                                     │
│                                                                 │
│ Release: v1.2.3                                                │
│ Changes: 15 commits (3 features, 2 bug fixes)                 │
│ Staging: All tests passed                                      │
│ Health: Environment healthy                                    │
│                                                                 │
│ Rollout Plan:                                                  │
│ - 10% of traffic (2 minutes)                                   │
│ - 50% of traffic (5 minutes)                                   │
│ - 100% of traffic (final)                                      │
│                                                                 │
│ Approve deployment? (yes/no)                                   │
└─────────────────────────────────────────────────────────────────┘

User: yes

Phase 4: Production Deployment [In Progress]
├── Rollout stage 1 (10%)... ✓ COMPLETED (1 replica, 2 minutes)
│   └── Metrics: error rate 0%, latency 48ms avg
├── Rollout stage 2 (50%)... ✓ COMPLETED (5 replicas, 5 minutes)
│   └── Metrics: error rate 0%, latency 46ms avg
└── Rollout stage 3 (100%)... ✓ COMPLETED (10 replicas, 5 minutes)
    └── Metrics: error rate 0%, latency 47ms avg

Phase 4: ✓ COMPLETED (12 minutes)

Phase 5: Post-Release [In Progress]
├── Updating documentation... ✓ COMPLETED (CHANGELOG.md, README.md, 1 minute)
├── Sending notifications...
│   ├── Slack (#releases): ✓ SENT
│   └── Email (stakeholders): ✓ SENT
├── Creating announcement... ✓ COMPLETED (blog post draft, 1 minute)
└── Updating dashboards... ✓ COMPLETED (Grafana dashboard updated, 30 seconds)

Phase 5: ✓ COMPLETED (3 minutes)

Release Workflow: ✓ SUCCESS (55 minutes total)

Summary:
- Version: v1.2.3
- Changes: 15 commits (3 features, 2 bug fixes)
- Tests: 495 passed, 0 failures
- Staging: All smoke and integration tests passed
- Production: Gradual rollout completed, all metrics healthy
- Documentation: Updated and stakeholders notified

Next steps:
- Monitor production for next 24 hours
- Address any user-reported issues
- Plan next release
```

### Failure Scenario: Staging Tests Fail

```
Phase 3: Staging Deployment [In Progress]
├── Deploying to staging... ✓ COMPLETED (3 replicas, 4 minutes)
├── Running smoke tests... ✗ FAILED (2/12 tests failed)
│   └── Failed tests:
│       - test_user_login: Connection timeout
│       - test_payment_flow: 500 Internal Server Error
│   └── Diagnosing failures...
│   └── Root cause: Database connection pool exhausted
│   └── Applying fix: Increasing connection pool size
│   └── Redeploying with fix...
│   └── Re-running smoke tests... ✓ COMPLETED (12/12 tests passed, 3 minutes)
├── Integration tests... ✓ COMPLETED (25/25 tests passed, 5 minutes)
└── Monitoring metrics... ✓ PASS (error rate: 0%, latency: 45ms avg, 3 minutes)

Phase 3: ✓ COMPLETED (18 minutes, 1 retry)
```

### Failure Scenario: Production Rollout Issues

```
Phase 4: Production Deployment [In Progress]
├── Rollout stage 1 (10%)... ✓ COMPLETED (1 replica, 2 minutes)
│   └── Metrics: error rate 0%, latency 48ms avg
├── Rollout stage 2 (50%)... ✗ FAILED (error rate spike detected)
│   └── Error rate: 5% (threshold: 1%)
│   └── Initiating automatic rollback...
│   └── Rollback completed: All traffic on v1.2.2
│   └── Investigating root cause...
│   └── Root cause: Missing environment variable in production config
│   └── Escalating to human for investigation

Phase 4: ✗ FAILED (5 minutes, automatic rollback completed)

┌─────────────────────────────────────────────────────────────────┐
│ Production Deployment Failed - Rolled Back                      │
│                                                                 │
│ Release: v1.2.3                                                │
│ Failure: Error rate spike during 50% rollout                   │
│ Root Cause: Missing environment variable (DB_POOL_SIZE)        │
│ Action Taken: Automatic rollback to v1.2.2                     │
│                                                                 │
│ Current State:                                                  │
│ - Production: Running v1.2.2 (stable)                          │
│ - Staging: Running v1.2.3 (working)                            │
│ - Error rate: 0% (normal)                                      │
│                                                                 │
│ Recommended Actions:                                            │
│ 1. Add DB_POOL_SIZE to production environment config           │
│ 2. Re-run staging tests with production-like config            │
│ 3. Retry deployment after fix                                  │
│                                                                 │
│ Resume command:                                                 │
│ amplihack goal-agent-generator execute \                       │
│   --agent-path .claude/agents/goal-driven/release-workflow-agent \
│   --resume-from-phase 4                                        │
└─────────────────────────────────────────────────────────────────┘
```

## Lessons Learned

**Benefits Realized**:

1. **Time savings**: 55 minutes automated vs 2-3 hours manual
2. **Consistency**: Same workflow every time, no missed steps
3. **Autonomous recovery**: Automatic retries and rollbacks
4. **Adaptability**: Different strategies for hotfixes vs features
5. **Safety**: Human approval gate for production, automatic rollback on failures

**Challenges Encountered**:

1. **Initial setup**: 4 hours to define goal, phases, and error handling
2. **Testing**: Needed to test failure scenarios (staging failures, production rollbacks)
3. **Environment differences**: Staging and production configs diverged
4. **Monitoring integration**: Required connecting to multiple monitoring systems

**Philosophy Compliance**:

- **Ruthless simplicity**: 5 clear phases, no unnecessary complexity
- **Single responsibility**: Each phase has one job (validate, build, deploy, monitor, notify)
- **Modularity**: Skills (validator, builder, deployer, monitor, documenter) are reusable
- **Regeneratable**: Can rebuild agent from goal definition

**When to Use This Pattern**:

- Repeated frequently (2-3+ times per week)
- High value from automation (hours saved, reduced errors)
- Multiple execution paths (hotfix, feature, patch)
- Recoverable failures (retry, alternative strategies, rollback)
- Clear success criteria (tests pass, metrics healthy, stakeholders notified)

**When NOT to Use**:

- One-time releases (simple script suffices)
- Fully manual process required (compliance, audit)
- Execution time is negligible (< 10 minutes manual)
- No variation in workflow (same steps every time)
- Failures always require human investigation
