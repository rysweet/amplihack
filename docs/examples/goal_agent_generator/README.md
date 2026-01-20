# Goal-Seeking Agent Generator Examples

This directory contains real-world examples demonstrating how to create autonomous agents for various use cases.

---

## Featured Examples

### 1. Azure Kubernetes SRE Agent

**Directory:** `aks_sre_example/`
**Domain:** Monitoring (Complex)
**Purpose:** Autonomous AKS cluster monitoring and remediation

**What It Does:**

- Monitors pod and node health
- Detects failures and resource issues
- Performs automated remediation
- Creates incident reports

**Learn:** Comprehensive goal prompts, SRE principles, complex scenarios

---

### 2. GitHub PR Manager

**Directory:** `github_pr_manager/`
**Domain:** Testing/Automation (Moderate)
**Purpose:** Automated PR review, labeling, and merging

**What It Does:**

- Reviews PRs for quality
- Applies labels automatically
- Checks CI before merging
- Creates release notes

**Learn:** GitHub integration, workflow automation

---

### 3. Security Vulnerability Scanner

**Directory:** `security_scanner/`
**Domain:** Security (Moderate)
**Purpose:** Scan Python code for OWASP vulnerabilities

**What It Does:**

- Detects SQL injection
- Finds hardcoded secrets
- Checks dependency CVEs
- Generates security reports

**Learn:** Security scanning, OWASP guidelines

---

### 4. Test Coverage Analyzer

**Directory:** `test_coverage_analyzer/`
**Domain:** Data Processing/Testing (Moderate)
**Purpose:** Analyze and improve test coverage

**What It Does:**

- Identifies untested code
- Suggests test cases
- Follows testing pyramid
- Prioritizes by risk

**Learn:** Test automation, coverage analysis

---

### 5. API Documentation Generator

**Directory:** `api_documentation_generator/`
**Domain:** Data Processing (Moderate)
**Purpose:** Generate OpenAPI docs from code

**What It Does:**

- Analyzes API routes
- Generates OpenAPI spec
- Creates code examples
- Documents authentication

**Learn:** API documentation, OpenAPI standards

---

### 6. Dependency Auditor

**Directory:** `dependency_auditor/`
**Domain:** Security (Moderate)
**Purpose:** Audit dependencies for vulnerabilities and licenses

**What It Does:**

- Scans all dependencies
- Identifies CVEs
- Checks licenses
- Suggests upgrades

**Learn:** Dependency management, security auditing

---

## How to Use These Examples

### Quick Start

```bash
# Pick an example
cd examples/goal_agent_generator/github_pr_manager

# Generate the agent
amplihack new --file goal_prompt.md --verbose

# Run it
cd ../../goal_agents/testing-github-pull-request-agent
python main.py
```

### Customize for Your Needs

1. **Copy the prompt:** `cp example/goal_prompt.md my_custom_goal.md`
2. **Edit:** Modify constraints, criteria, context
3. **Generate:** `amplihack new --file my_custom_goal.md`
4. **Test:** `python goal_agents/your-agent/main.py`
5. **Iterate:** Refine prompt based on results

---

## Example Comparison

| Example          | Domain     | Complexity | Phases | Duration | Skills |
| ---------------- | ---------- | ---------- | ------ | -------- | ------ |
| AKS SRE          | Monitoring | Complex    | 4      | 2h 36m   | 2      |
| PR Manager       | Testing    | Moderate   | 4      | 1h 12m   | 2      |
| Security Scanner | Security   | Moderate   | 4      | 1h 12m   | 2      |
| Test Coverage    | Data       | Moderate   | 4      | 1h 12m   | 2      |
| API Docs         | Data       | Moderate   | 4      | 1h 12m   | 2      |
| Dependency Audit | Security   | Moderate   | 4      | 1h 12m   | 2      |

**Insight:** All examples use 4-phase structure, but complexity affects duration and max turns.

---

## What You'll Learn

### From These Examples:

**Goal Prompt Writing:**

- How to structure prompts
- What level of detail works best
- How to define constraints
- How to write success criteria

**Domain Classification:**

- Security vs Testing vs Data vs Monitoring
- How domain affects skill matching
- Complexity levels (simple/moderate/complex)

**Agent Generation:**

- What gets generated automatically
- How skills are matched
- How phases are planned
- How configuration is determined

**Execution:**

- How AutoMode works
- What agents can accomplish
- How to monitor progress
- When to intervene

---

## Tips for Creating Your Own

### 1. Start with Examples

Copy and modify these examples rather than starting from scratch.

### 2. Be Specific

Vague goals → vague agents. Specific goals → focused agents.

### 3. Include Context

The more context you provide, the better the agent understands the task.

### 4. Define Success

Clear success criteria help the agent know when it's done.

### 5. Test and Iterate

Generate, run, observe, refine prompt, regenerate.

---

## Next Steps

1. Try generating each example agent
2. Inspect what gets created
3. Run an agent with a real task
4. Customize a prompt for your needs
5. Create your own agent!

---

**All examples are production-ready and demonstrate different aspects of the Goal-Seeking Agent Generator.**
