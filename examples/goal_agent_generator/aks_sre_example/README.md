# Example: Azure Kubernetes SRE Agent

This example demonstrates how to create an autonomous Site Reliability Engineering agent for Azure Kubernetes Service using the Goal-Seeking Agent Generator.

---

## What This Agent Does

**Purpose:** Autonomous AKS cluster monitoring and remediation

**Capabilities:**

- Monitors pod and node health
- Detects common failure patterns
- Performs automated remediation
- Creates incident reports
- Tracks SLO/SLI metrics

**Domain:** Monitoring (complex)
**Estimated Duration:** 2 hours 36 minutes
**Phases:** 4 (Setup → Collect → Analyze → Alert)

---

## How to Create This Agent

### Step 1: Review the Goal Prompt

See `goal_prompt.md` - A comprehensive SRE agent specification including:

- Clear objective (AKS cluster monitoring)
- Technical constraints (Azure CLI, kubectl, least-privilege)
- Operational constraints (no disruption, detailed reports)
- Success criteria (monitoring, detection, remediation, reporting)
- Context (SRE principles, example scenarios, integration points)

**Key Elements:**

- **Specific:** Exactly what the agent should do
- **Measurable:** Clear success criteria
- **Realistic:** 5-minute health checks, 10-minute remediation
- **Comprehensive:** All scenarios and integrations listed

### Step 2: Generate the Agent

```bash
amplihack new --file examples/goal_agent_generator/aks_sre_example/goal_prompt.md --verbose
```

**Output:**

```
[1/4] Analyzing goal prompt...
  Goal: Azure Kubernetes Service SRE Agent
  Domain: monitoring
  Complexity: complex

[2/4] Creating execution plan...
  Phases: 4
  Estimated duration: 2 hours 36 minutes
  Required skills: data-processor, monitor, generic-executor

  Phase 1: Setup Monitors (30 min)
  Phase 2: Data Collection (30 min)
  Phase 3: Analysis (30 min)
  Phase 4: Alerting (30 min)

[3/4] Matching skills...
  Skills matched: 2
    - data-processor (100% match)
    - monitor (80% match)

[4/4] Assembling agent bundle...
  Bundle name: monitoring-azure-kubernetes-service-agent

✓ Goal agent created successfully in 0.1s
```

**Generation Time:** < 0.1 seconds

### Step 3: Inspect Generated Agent

```bash
cd goal_agents/monitoring-azure-kubernetes-service-agent
ls -la
```

**Structure:**

```
monitoring-azure-kubernetes-service-agent/
├── main.py                    # Executable entry point
├── README.md                  # Agent documentation
├── prompt.md                  # Original goal (preserved)
├── agent_config.json          # Complete configuration
├── .claude/
│   ├── agents/                # Matched skills
│   │   ├── data-processor.md
│   │   └── monitor.md
│   └── context/
│       ├── goal.json
│       └── execution_plan.json
└── logs/                      # Created at runtime
```

### Step 4: Review Configuration

```bash
cat agent_config.json | jq .
```

**Key Config:**

- **Bundle ID:** Unique identifier
- **Domain:** monitoring
- **Complexity:** complex
- **Phase Count:** 4
- **Skills:** data-processor, monitor
- **Max Turns:** 18 (auto-calculated: 15 base + 20% for extra phases)
- **Capabilities:** configuration, instrumentation, data-collection, aggregation, analysis, anomaly-detection, alerting, notification

### Step 5: Run the Agent

```bash
python main.py
```

**Expected Execution:**

```
Starting monitoring-azure-kubernetes-service-agent...
Goal: Azure Kubernetes Service SRE Agent
Estimated duration: 2 hours 36 minutes

[AUTO CLAUDE] Starting auto mode with Claude SDK (max 18 turns)

Turn 1: Setting up monitors...
  → Checking Azure CLI availability
  → Getting AKS cluster credentials
  → Configuring kubectl context

Turn 2: Collecting cluster data...
  → kubectl get pods --all-namespaces
  → kubectl get nodes
  → Checking pod statuses

Turn 3: Analyzing for issues...
  → Found: 2 pods in CrashLoopBackOff
  → Found: 1 node with MemoryPressure
  → Analyzing logs for crash patterns

Turn 4: Performing remediation...
  → Restarting pod: app-backend-7d9f8b-x7k2p
  → Scaling node pool: default-pool +1 node
  → Creating incident report

...

Turn 12: Generating SRE report...
  → Summary: 3 issues detected, 2 remediated, 1 escalated
  → SLO: 99.95% (target: 99.9%) ✓
  → Recommendations: 5 generated

✓ Goal achieved successfully!
```

---

## What Gets Generated

### Main Script (main.py)

Executable Python script that:

1. Loads the goal prompt
2. Initializes AutoMode with Claude SDK
3. Executes with 18 turns (complex goal = more turns)
4. Reports progress and completion

### Documentation (README.md)

Generated README includes:

- Goal description
- Domain and complexity
- 4-phase execution plan with estimates
- Matched skills (data-processor, monitor)
- Usage instructions
- Requirements

### Configuration (agent_config.json)

Complete metadata:

- Unique bundle ID
- Domain: monitoring
- Complexity: complex
- Required capabilities (8 total)
- Execution plan (4 phases)
- AutoMode config (18 max turns)

### Original Prompt (prompt.md)

Your original goal preserved for reference and regeneration

---

## Why This Example Works Well

### Comprehensive Goal Definition

The prompt includes:

- ✅ Clear objective (AKS SRE monitoring)
- ✅ Specific constraints (technical, operational, performance)
- ✅ Measurable success criteria (monitoring, detection, remediation, reporting)
- ✅ Rich context (SRE principles, example scenarios, integrations)

### Appropriate Complexity

**Classified as "complex"** because:

- Multiple integration points (Azure CLI, kubectl, Monitor, GitHub, PagerDuty)
- Continuous operation (not one-shot task)
- Multiple phases with dependencies
- Requires domain expertise (SRE, Kubernetes, Azure)

**Result:** 18 max turns (vs 5 for simple, 10 for moderate)

### Good Skill Matching

**data-processor (100% match):**

- Handles metric collection and aggregation
- Processes pod/node status data
- Structures incident reports

**monitor (80% match):**

- Security monitoring capabilities
- Anomaly detection
- Alert generation

### Clear Phase Plan

**Phase 1: Setup Monitors** (30 min)

- Configure Azure CLI
- Set up kubectl context
- Establish monitoring baselines

**Phase 2: Data Collection** (30 min)

- Query pod statuses
- Check node health
- Gather metrics

**Phase 3: Analysis** (30 min)

- Detect anomalies
- Identify failures
- Classify severity

**Phase 4: Alerting** (30 min)

- Create incidents
- Send notifications
- Generate reports

---

## Potential Use Cases for AKS SRE Agent

1. **Continuous Monitoring:**
   - Run agent every 5 minutes via cron
   - Detect issues early
   - Auto-remediate common problems

2. **Incident Response:**
   - Trigger on PagerDuty alert
   - Agent investigates and remediates
   - Escalates if can't resolve

3. **Cluster Health Audits:**
   - Run daily comprehensive checks
   - Generate SRE reports
   - Track SLO/SLI trends

4. **Deployment Validation:**
   - Run after each deployment
   - Verify cluster health
   - Rollback if issues detected

5. **Capacity Planning:**
   - Analyze resource usage patterns
   - Recommend scaling decisions
   - Prevent resource exhaustion

---

## Customization Ideas

### Modify the Prompt

**Add specific checks:**

```markdown
## Additional Success Criteria

- Validates PodDisruptionBudgets exist
- Checks HorizontalPodAutoscaler configs
- Monitors certificate expiry (<30 days)
```

### Adjust Time Constraints

```markdown
## Constraints

- Health check cycle: < 2 minutes (faster)
- Issue detection: < 30 seconds (more responsive)
```

### Add Integration Points

```markdown
**Integration Points:**

- Datadog (custom metrics)
- Splunk (log aggregation)
- ServiceNow (ticketing)
```

### Change Domain Focus

```markdown
# Goal: AKS Security Auditor

Focus on security instead of SRE...
```

---

## What You Learn from This Example

1. **Comprehensive prompts work best**
   - Rich context helps agent understand domain
   - Specific examples guide execution
   - Clear criteria enable validation

2. **Complexity classification matters**
   - Complex goals get more turns (18 vs 5)
   - Domain affects skill matching
   - Time estimates help planning

3. **Skill library is key**
   - Matched skills (data-processor, monitor) provide capabilities
   - More skills = better agent performance
   - Can add custom skills to library

4. **Generated agents are ready to use**
   - No manual configuration needed
   - Complete documentation included
   - Executable immediately

---

## Try It Yourself

1. **Copy the goal prompt**: `examples/goal_agent_generator/aks_sre_example/goal_prompt.md`

2. **Customize for your use case**:
   - Change cluster names
   - Add specific checks
   - Adjust time constraints
   - Modify integration points

3. **Generate your agent**:

   ```bash
   amplihack new --file my_custom_aks_goal.md
   ```

4. **Run and iterate**:
   ```bash
   cd goal_agents/your-agent
   python main.py
   # Review results, refine prompt, regenerate
   ```

---

## Files in This Example

- `goal_prompt.md` - The complete AKS SRE goal specification
- `README.md` - This documentation
- `GENERATED_OUTPUT.md` - Sample of what gets generated (see below)

---

## Generated Output Sample

See what the tool creates from this prompt:

**Agent Name:** `monitoring-azure-kubernetes-service-agent`
**Bundle ID:** `d2742b7b-f4e4-47b0-8916-4f3db9a4e3b8`
**Max Turns:** 18 (complex goal)
**Skills:** 2 matched
**Phases:** 4 (Setup → Collect → Analyze → Alert)
**Total Capabilities:** 8 (configuration, instrumentation, data-collection, aggregation, analysis, anomaly-detection, alerting, notification)

**Agent successfully created and ready to run!**

---

**This example demonstrates the power of the Goal-Seeking Agent Generator - from comprehensive SRE requirements to executable agent in < 0.1 seconds!**
