# Goal Prompt Template

Use this template to write effective goal prompts for goal-seeking agents. A well-structured prompt helps the `PromptAnalyzer` extract accurate goal definitions and enables the `ObjectivePlanner` to create effective execution plans.

## Template Structure

```markdown
# Goal: [Concise Goal Title]

## Objective

[Clear statement of what needs to be achieved. Be specific about the desired outcome, not the implementation steps.]

[Optional: Additional context about why this goal is important or what problem it solves.]

## Success Criteria

- [Measurable criterion 1: How to verify goal is achieved]
- [Measurable criterion 2: Specific metrics or outcomes]
- [Measurable criterion 3: Quality thresholds]
- [Additional criteria as needed]

## Constraints

- [Technical constraint 1: Resource limits, time limits, etc.]
- [Operational constraint 2: Safety requirements, approval gates, etc.]
- [Business constraint 3: Compliance, audit requirements, etc.]
- [Additional constraints as needed]

## Context

- **Frequency**: [How often this goal will be executed: one-time, daily, per-feature, etc.]
- **Priority**: [Low, Medium, High, Critical]
- **Scale**: [Small, Medium, Large - data volume, system size, etc.]
- **Environment**: [Development, Staging, Production, All]
- [Additional context as needed]
```

## Filling Out the Template

### Section 1: Goal Title

**Purpose**: Concise, action-oriented summary (5-10 words)

**Good Examples**:

- "Automate Multi-Source Data Pipeline"
- "Generate Comprehensive Test Suite"
- "Deploy Microservices to Production"
- "Audit AKS Cluster Security"

**Bad Examples**:

- "Fix Everything" (too vague)
- "The System Should Process Data From Multiple Sources And Transform It" (too long)
- "Data" (not action-oriented)

**Tips**:

- Start with action verb (Automate, Generate, Deploy, Audit, etc.)
- Include key domain noun (Data Pipeline, Test Suite, Microservices, etc.)
- Keep under 10 words

### Section 2: Objective

**Purpose**: Clear statement of desired outcome (what, not how)

**Structure**:

1. Primary action and target (1-2 sentences)
2. Optional: Problem context (1 sentence)
3. Optional: High-level approach (1 sentence, if needed for clarity)

**Good Example**:

```markdown
## Objective

Collect data from three sources (S3, PostgreSQL, REST API), transform to common
schema, validate quality, and publish to data warehouse. Current manual process
takes 2-3 hours and is error-prone. Automate end-to-end pipeline with graceful
handling of source failures.
```

**Bad Example**:

```markdown
## Objective

First, we need to connect to S3 using boto3, then read all the Parquet files,
then parse them with pandas, then... [continues with implementation details]
```

**Tips**:

- Focus on **what** to achieve, not **how** to achieve it
- Avoid implementation details (libraries, tools, specific commands)
- Include success outcome clearly
- Mention key challenges if they affect approach

### Section 3: Success Criteria

**Purpose**: Measurable, verifiable outcomes that define success

**Characteristics**:

- **Measurable**: Can be verified programmatically or manually
- **Specific**: Clear threshold or condition
- **Verifiable**: Agent can check if met
- **Complete**: All criteria met = goal achieved

**Good Examples**:

```markdown
## Success Criteria

- All three data sources successfully ingested (100% success or logged failures)
- Data transformed with < 2% transformation failure rate
- Quality checks pass: completeness ≥ 95%, accuracy ≥ 98%, consistency = 100%
- Data published to warehouse without duplicates
- Pipeline completes within 30 minutes
- Quality report generated and stakeholders notified
```

**Bad Examples**:

```markdown
## Success Criteria

- Data looks good
- Everything works
- Pipeline is fast
```

**Tips**:

- Use numbers (percentages, counts, durations)
- Specify thresholds explicitly (≥ 95%, < 2%, = 100%)
- Include both functional and non-functional criteria
- Make criteria checkable by agent

### Section 4: Constraints

**Purpose**: Limitations, requirements, and boundaries

**Categories**:

1. **Technical**: Resource limits (memory, CPU, time), technology requirements
2. **Operational**: Safety requirements, approval gates, rollback needs
3. **Business**: Compliance, audit trails, data privacy
4. **Process**: Manual steps, human-in-the-loop requirements

**Good Examples**:

```markdown
## Constraints

- Must handle source unavailability gracefully (no pipeline failure)
- No data loss (failed records logged for manual review)
- Idempotent (safe to re-run without duplicates)
- Resource limits: 8GB RAM, 4 CPU cores
- Must complete within 30 minutes (blocking downstream jobs)
- Requires human approval before production deployment
- Must preserve data lineage (track source → warehouse)
```

**Bad Examples**:

```markdown
## Constraints

- Should be fast
- Don't break anything
- Use Python
```

**Tips**:

- Be specific about limits (8GB RAM, not "limited resources")
- Include safety requirements (rollback, approval gates)
- Mention idempotency if re-runs are expected
- Specify any "must NOT do" items

### Section 5: Context

**Purpose**: Additional information that affects execution strategy

**Key Fields**:

- **Frequency**: How often goal is executed (affects optimization trade-offs)
- **Priority**: Urgency level (affects mode selection, iteration limits)
- **Scale**: Size of problem (affects resource allocation, strategy)
- **Environment**: Where it runs (affects approach, safety measures)

**Good Example**:

```markdown
## Context

- **Frequency**: Daily (automated at 2 AM)
- **Priority**: High (blocking downstream analytics dashboards)
- **Scale**: Medium (100K-1M records per source, 3 sources)
- **Environment**: Production (data warehouse is production system)
- **Stakeholders**: Analytics team (5 people)
- **SLA**: Results must be available by 6 AM for morning reports
```

**Bad Example**:

```markdown
## Context

- It's important
- We need it soon
- Lots of data
```

**Tips**:

- Include frequency (affects investment in optimization)
- Specify priority (affects iteration limits, escalation)
- Quantify scale (affects strategy selection)
- Mention environment (affects safety measures)
- Note stakeholders if relevant (affects notifications)

## Complete Example: Data Pipeline

```markdown
# Goal: Automate Multi-Source Data Pipeline

## Objective

Collect data from three sources (S3 buckets, PostgreSQL database, REST API),
transform to common schema, validate quality, and publish to data warehouse.
Current manual process takes 2-3 hours daily and is error-prone. Automate
end-to-end pipeline with graceful handling of source failures.

## Success Criteria

- All available sources successfully ingested (100% of available sources or logged failures)
- Data transformed to target schema with < 2% transformation failure rate
- Quality checks pass: completeness ≥ 95%, accuracy ≥ 98%, consistency = 100%
- Data published to warehouse without duplicates
- Pipeline completes within 30 minutes
- Quality report generated (HTML format)
- Stakeholders notified (Slack #data-eng channel)

## Constraints

- Must handle source unavailability gracefully (log and continue with partial data)
- No data loss (failed records logged to failed_records.log for manual review)
- Idempotent (safe to re-run without creating duplicates, use run_id for deduplication)
- Resource limits: 8GB RAM, 4 CPU cores, 50GB disk
- Must preserve data lineage (track source → staging → warehouse)
- Must complete within 30 minutes (blocks morning analytics reports)
- No breaking changes to warehouse schema

## Context

- **Frequency**: Daily (automated at 2 AM UTC)
- **Priority**: High (blocking downstream analytics dashboards)
- **Scale**: Medium (100K-1M records per source, 3 sources, ~2GB raw data)
- **Environment**: Production (data warehouse is production Snowflake cluster)
- **Stakeholders**: Analytics team (5 people), notified via Slack
- **SLA**: Results must be available by 6 AM UTC for morning reports
- **History**: Previous implementation using Airflow, migrating to goal-seeking agent
```

## Domain-Specific Examples

### Example: Security Analysis

```markdown
# Goal: Comprehensive Application Security Audit

## Objective

Perform comprehensive security analysis of web application, identifying
vulnerabilities (SQL injection, XSS, CSRF, insecure dependencies),
generating prioritized remediation report.

## Success Criteria

- All OWASP Top 10 vulnerabilities checked
- Dependency vulnerabilities scanned (using safety, pip-audit)
- Security headers validated (using securityheaders.com API)
- Report generated with severity levels (Critical, High, Medium, Low)
- Remediation steps provided for each finding
- No critical vulnerabilities or documented risk acceptance

## Constraints

- Read-only analysis (no modifications to application)
- No production testing (only development/staging)
- Must complete within 15 minutes (blocking PR merge)
- API rate limits: 10 requests/min (securityheaders.com)
- Approved exception list: CVE-2023-12345 (expires 2025-12-01)

## Context

- **Frequency**: Per pull request (50-100 times per month)
- **Priority**: High (security gate for production)
- **Scale**: Small application (5K-10K lines of code, 50 dependencies)
- **Environment**: Development and Staging (never production)
- **Stakeholders**: Security team, development team
```

### Example: Deployment Automation

```markdown
# Goal: Automated Microservices Deployment Pipeline

## Objective

Deploy microservices to Kubernetes cluster with zero downtime, including
pre-deployment validation, gradual rollout, health monitoring, and automatic
rollback on failures.

## Success Criteria

- All pre-deployment checks pass (tests, linting, security scan, Docker build)
- Staging deployment successful with smoke tests passing
- Production deployment completes with gradual rollout (10% → 50% → 100%)
- Health checks passing at each rollout stage
- No error rate increase (< 0.1% throughout rollout)
- Latency within SLA (p95 < 200ms)
- Rollback executes automatically if health checks fail

## Constraints

- Zero downtime (users never see errors or downtime)
- Requires human approval before production deployment
- Must support rollback at any stage
- Resource limits: 10 pods maximum per service
- Must complete within 60 minutes
- Must preserve previous deployment (for rollback)
- No database schema changes (requires separate migration process)

## Context

- **Frequency**: 2-3 times per week (feature releases)
- **Priority**: High (user-facing services)
- **Scale**: Medium (10-20 microservices, 100-200 active pods)
- **Environment**: Kubernetes cluster (staging + production)
- **Stakeholders**: Development team, SRE team, product managers
- **SLA**: 99.9% uptime, p95 latency < 200ms
```

## Validation Checklist

Before using your goal prompt, verify:

**Goal Title**:

- [ ] Concise (5-10 words)
- [ ] Action-oriented (starts with verb)
- [ ] Includes key domain noun

**Objective**:

- [ ] Clearly states desired outcome
- [ ] Focuses on **what**, not **how**
- [ ] Provides sufficient context
- [ ] No implementation details (libraries, tools)

**Success Criteria**:

- [ ] All criteria are measurable
- [ ] Thresholds are specific (numbers, percentages)
- [ ] Agent can verify each criterion
- [ ] Criteria are complete (all met = success)

**Constraints**:

- [ ] Resource limits specified (if applicable)
- [ ] Safety requirements included
- [ ] Approval gates mentioned (if any)
- [ ] Time limits specified (if applicable)

**Context**:

- [ ] Frequency specified
- [ ] Priority indicated
- [ ] Scale quantified
- [ ] Environment noted
- [ ] Stakeholders mentioned (if relevant)

## Common Mistakes to Avoid

**Mistake 1: Implementation Details**

```markdown
BAD: "Use pandas to read CSV files, then use sklearn for transformation..."
GOOD: "Transform data to common schema with 98% success rate"
```

**Mistake 2: Vague Success Criteria**

```markdown
BAD: "Data should be good quality"
GOOD: "Completeness ≥ 95%, accuracy ≥ 98%, consistency = 100%"
```

**Mistake 3: Missing Constraints**

```markdown
BAD: "Deploy to production"
GOOD: "Deploy to production with human approval, zero downtime, rollback capability"
```

**Mistake 4: No Context**

```markdown
BAD: [No context provided]
GOOD: "Frequency: Daily, Priority: High, Scale: 1M records, Environment: Production"
```

**Mistake 5: Too Many Goals**

```markdown
BAD: "Collect data, analyze data, generate reports, send notifications, archive data,
optimize database, update documentation, train models, deploy to production..."
GOOD: Split into multiple focused goals
```

## Using the Template

**Step 1**: Copy template to new file

```bash
cp goal_prompt_template.md my-goal.md
```

**Step 2**: Fill in all sections (replace [placeholders])

**Step 3**: Validate using checklist above

**Step 4**: Generate agent

```bash
amplihack goal-agent-generator create \
  --prompt my-goal.md \
  --output .claude/agents/goal-driven/my-agent
```

**Step 5**: Review generated plan

```bash
cat .claude/agents/goal-driven/my-agent/plan.yaml
```

**Step 6**: Execute agent

```bash
amplihack goal-agent-generator execute \
  --agent-path .claude/agents/goal-driven/my-agent \
  --auto-mode
```

## Getting Help

If your goal prompt isn't generating good results:

1. **Check decision framework**: Use 5-question framework from SKILL.md Section 2
2. **Review examples**: See `examples/` directory for complete scenarios
3. **Simplify**: Start with simpler goal, add complexity incrementally
4. **Ask architect**: Use architect agent to refine goal definition

Remember: A well-written goal prompt is the foundation of an effective goal-seeking agent. Take time to make it clear, measurable, and complete.
