# Goal-Seeking Agent Generator - User Guide

**Create autonomous agents from simple prompts**

---

## Quick Start

### 1. Write Your Goal

Create a markdown file describing what you want to accomplish:

```bash
cat > my_goal.md <<'EOF'
# Goal: Automated Security Audit

Scan Python code for security vulnerabilities and generate reports.

## Constraints
- Must complete within 30 minutes
- Should check for OWASP Top 10
- Must provide actionable recommendations

## Success Criteria
- Identifies at least 5 vulnerability types
- Generates prioritized report
- Includes code examples for fixes

## Context
This agent will help maintain secure codebases by automatically detecting common security issues.
EOF
```

### 2. Generate Your Agent

```bash
amplihack new --file my_goal.md --verbose
```

**Output:**

```
Generating goal agent from: my_goal.md

[1/4] Analyzing goal prompt...
  Goal: Automated Security Audit
  Domain: security-analysis
  Complexity: moderate

[2/4] Creating execution plan...
  Phases: 4
  Estimated duration: 45 minutes

[3/4] Matching skills...
  Skills matched: 3
    - security-analyzer (85% match)
    - documenter (100% match)
    - generic-executor (60% match)

[4/4] Assembling agent bundle...
  Bundle name: security-automated-security-audit-agent

✓ Goal agent created successfully in 0.1s

Agent directory: ./goal_agents/security-automated-security-audit-agent
```

### 3. Run Your Agent

```bash
cd ./goal_agents/security-automated-security-audit-agent
python main.py
```

The agent will autonomously pursue your goal!

---

## How It Works

### The Pipeline

```
Your Goal Prompt
       ↓
[1] Prompt Analysis → Extract goal, domain, constraints
       ↓
[2] Objective Planning → Generate multi-phase execution plan
       ↓
[3] Skill Matching → Find relevant skills from library
       ↓
[4] Agent Assembly → Combine into executable bundle
       ↓
  Your Agent!
```

### What Gets Analyzed

**From Your Prompt:**

- **Primary Goal**: What you want to accomplish
- **Domain**: Type of work (security, automation, data, etc.)
- **Constraints**: Time limits, technical requirements
- **Success Criteria**: How to know when done
- **Complexity**: Simple, moderate, or complex

**Generates:**

- **Execution Plan**: 3-5 phases with dependencies
- **Skill Set**: Matched capabilities from skill library
- **Configuration**: Auto-mode settings based on complexity
- **Documentation**: README with usage instructions

---

## Command Reference

### Basic Usage

```bash
amplihack new --file <prompt.md>
```

### All Options

```bash
amplihack new \
  --file <prompt.md>        # Required: Your goal prompt
  --output <directory>       # Optional: Where to create agent (default: ./goal_agents)
  --name <agent-name>        # Optional: Custom name (default: auto-generated)
  --skills-dir <directory>   # Optional: Custom skills location
  --verbose                  # Optional: Show detailed progress
```

### Examples

```bash
# Basic - uses defaults
amplihack new --file security_audit.md

# Custom output directory
amplihack new --file research.md --output ~/my-agents

# Custom name
amplihack new --file deploy.md --name my-deployer

# Verbose output
amplihack new --file audit.md --verbose

# All options
amplihack new \
  --file complex_task.md \
  --output ~/agents \
  --name task-agent \
  --verbose
```

---

## Writing Good Goal Prompts

### Essential Structure

```markdown
# Goal: [Clear, specific objective]

[Detailed description of what you want to accomplish]

## Constraints

- Technical limitations
- Time requirements
- Resource constraints

## Success Criteria

- How to measure success
- Expected outputs
- Quality standards

## Context

Additional background information
```

### Best Practices

**DO:**

- ✅ Be specific about the goal
- ✅ Include concrete success criteria
- ✅ Mention time constraints
- ✅ Provide relevant context
- ✅ List technical requirements

**DON'T:**

- ❌ Be too vague ("make things better")
- ❌ Combine multiple unrelated goals
- ❌ Omit success criteria
- ❌ Use jargon without explanation

### Example: Good vs Bad

**❌ Bad Prompt:**

```markdown
# Goal: Help with code

Make the code better.
```

**✅ Good Prompt:**

```markdown
# Goal: Refactor Authentication Module

Improve the authentication module by:

- Adding type hints
- Extracting duplicate logic
- Improving error messages

## Constraints

- Must maintain backward compatibility
- Should complete in 30 minutes
- No external dependencies

## Success Criteria

- All functions have type hints
- Code duplication < 5%
- Error messages include context
- All existing tests pass

## Context

Current auth module has grown organically and needs cleanup.
Files: src/auth/\*.py
```

---

## Domain Types

Agents are automatically classified into domains:

### Supported Domains

1. **data-processing**: Data ingestion, transformation, analysis
2. **security-analysis**: Vulnerability scanning, auditing, threat detection
3. **automation**: Workflow automation, scheduling, monitoring
4. **testing**: Test generation, validation, QA
5. **deployment**: Release management, publishing, distribution
6. **monitoring**: Metrics, alerts, observability
7. **integration**: API connections, webhooks, data sync
8. **reporting**: Dashboards, summaries, visualizations

**Domain determines:**

- Which skills get matched
- Execution plan structure
- Estimated duration
- Required capabilities

---

## Generated Agent Structure

### Directory Layout

```
my-agent/
├── main.py                    # Executable entry point
├── README.md                  # Agent documentation
├── prompt.md                  # Original goal (preserved)
├── agent_config.json          # Full configuration
├── .claude/
│   ├── agents/                # Matched skills (copied)
│   │   ├── security-analyzer.md
│   │   └── documenter.md
│   └── context/
│       ├── goal.json          # Structured goal data
│       └── execution_plan.json # Plan with phases
└── logs/                      # Execution logs (created at runtime)
```

### Key Files

#### main.py

Executable Python script that:

- Loads goal and execution plan
- Initializes AutoMode with Claude SDK
- Executes phases autonomously
- Reports progress and results

#### README.md

Generated documentation explaining:

- What the agent does
- How to run it
- Expected duration
- Success criteria

#### agent_config.json

Complete metadata:

- Bundle ID and version
- Domain and complexity
- Phase count and skill list
- Estimated duration
- Required capabilities

---

## Running Generated Agents

### Prerequisites

1. **amplihack installed**: `pip install amplihack`
2. **Claude API access**: Set `ANTHROPIC_API_KEY` environment variable
3. **Working directory**: Appropriate permissions

### Execution

```bash
cd <agent-directory>
python main.py
```

### What Happens

1. **Initialization**
   - Loads goal from prompt.md
   - Reads execution plan
   - Initializes AutoMode

2. **Autonomous Execution**
   - Follows phases in sequence
   - Uses available skills and tools
   - Tracks progress
   - Handles errors

3. **Completion**
   - Reports success/failure
   - Saves execution logs
   - Exits with appropriate code (0 = success)

### Monitoring Execution

**Logs:** Check `logs/` directory for detailed execution trace
**Progress:** Watch console output for phase updates
**Errors:** Check logs if agent fails

---

## Advanced Usage

### Custom Skills Directory

```bash
amplihack new \
  --file my_goal.md \
  --skills-dir ~/.claude/my-custom-skills
```

Uses skills from custom directory instead of default.

### Output Organization

```bash
# Organize by domain
amplihack new --file security.md --output ./agents/security
amplihack new --file data.md --output ./agents/data

# Result:
./agents/
├── security/
│   └── security-automated-audit-agent/
└── data/
    └── data-processing-pipeline-agent/
```

### Batch Generation

```bash
# Generate multiple agents
for goal in goals/*.md; do
    amplihack new --file "$goal" --verbose
done
```

---

## Troubleshooting

### "No skills matched"

**Problem:** No skills found for your goal's capabilities

**Solutions:**

- Check that `~/.amplihack/.claude/agents/amplihack/` exists
- Provide custom `--skills-dir` if using different location
- Simplify goal to match available skills

### "Bundle incomplete"

**Problem:** Agent validation failed

**Solutions:**

- Verify prompt file has clear goal and domain
- Check that all required fields are present
- Review verbose output for validation errors

### "Generated agent fails to run"

**Problem:** AutoMode import or execution error

**Solutions:**

- Ensure amplihack is installed: `pip install amplihack`
- Verify Claude API access: `echo $ANTHROPIC_API_KEY`
- Check main.py has executable permissions: `chmod +x main.py`

### "Agent doesn't accomplish goal"

**Problem:** Execution completes but goal not achieved

**Solutions:**

- Check logs/ directory for execution trace
- Review prompt - may be too vague or complex
- Adjust success criteria to be more specific
- Try simpler goal first

---

## Examples

### Example 1: Code Review Agent

**Goal:** `code_review.md`

```markdown
# Goal: Automated Python Code Review

Review Python files for common issues and suggest improvements.

## Constraints

- Must complete within 5 minutes
- Should check: type hints, error handling, complexity
- Must provide line-specific feedback

## Success Criteria

- Identifies at least 3 issue categories
- Provides specific line numbers
- Suggests concrete fixes
- Reports in structured format
```

**Command:**

```bash
amplihack new --file code_review.md --name code-reviewer
```

**Usage:**

```bash
cd goal_agents/code-reviewer
python main.py
# Agent autonomously reviews code and generates report
```

---

### Example 2: Documentation Researcher

**Goal:** `doc_research.md`

```markdown
# Goal: Technical Documentation Researcher

Research and summarize documentation on specific technologies.

## Constraints

- Must search multiple sources (official docs, GitHub, tutorials)
- Should complete within 15 minutes
- Must include code examples

## Success Criteria

- Finds at least 5 relevant sources
- Creates organized summary
- Includes practical examples
- Cites all sources
```

**Command:**

```bash
amplihack new --file doc_research.md --output ~/research-agents --verbose
```

---

### Example 3: Project Organizer

**Goal:** `organize.md`

```markdown
# Goal: Project Directory Organizer

Analyze project structure and suggest improvements.

## Constraints

- Must preserve all existing files
- Should follow common conventions
- Must complete within 10 minutes

## Success Criteria

- Identifies misplaced files
- Suggests logical structure
- Proposes naming improvements
- Creates migration plan
```

**Command:**

```bash
amplihack new --file organize.md
```

---

## Tips & Best Practices

### Goal Writing Tips

1. **Start Simple**: Test with simple goals before complex ones
2. **One Goal Per Agent**: Don't combine multiple objectives
3. **Concrete Criteria**: "Reduce complexity by 20%" better than "improve quality"
4. **Realistic Timeframes**: Match complexity to time constraints
5. **Provide Context**: Help the agent understand the domain

### Agent Usage Tips

1. **Check Logs**: Review logs/ directory after execution
2. **Iterate on Prompts**: Refine based on agent behavior
3. **Match to Skills**: Check available skills first
4. **Test Incrementally**: Start with simpler versions of goals

### Skill Library Tips

1. **Explore Skills**: Browse `~/.amplihack/.claude/agents/amplihack/` to see what's available
2. **Understand Capabilities**: Read skill docs to understand what they do
3. **Custom Skills**: Add your own to `~/.amplihack/.claude/agents/` if needed

---

## Performance

### Generation Time

- **Simple goals**: < 0.1 seconds
- **Complex goals**: < 0.2 seconds
- **Bottleneck**: None (instant)

### Agent Size

- **Typical agent**: 5-15 KB
- **With many skills**: Up to 50 KB
- **Minimal overhead**: Lightweight

### Execution Time

- **Simple tasks**: 5-15 minutes
- **Moderate tasks**: 15-45 minutes
- **Complex tasks**: 45-120 minutes
- **Depends on**: Goal complexity and Claude API response time

---

## FAQ

**Q: Can agents run without amplihack installed?**
A: No, generated agents currently require amplihack for AutoMode. This may be addressed in future versions.

**Q: How many agents can I create?**
A: Unlimited. Each agent is independent.

**Q: Can agents communicate with each other?**
A: Not in Phase 1 MVP. Multi-agent coordination is deferred pending evidence of need.

**Q: Do agents learn from previous executions?**
A: Not in Phase 1 MVP. Learning features are deferred pending evidence of need.

**Q: Can I modify generated agents?**
A: Yes! They're just Python scripts and markdown files. Customize as needed.

**Q: What if my goal doesn't match any skills?**
A: A generic executor will be used. Consider adding custom skills to `~/.amplihack/.claude/agents/`.

**Q: Can agents access the internet?**
A: Yes, if Claude SDK has access. Agents use same permissions as Claude.

**Q: How do I update agents?**
A: Regenerate from prompt. Update commands are deferred pending evidence of need.

---

## Getting Help

- **Documentation**: See `src/amplihack/goal_agent_generator/README.md`
- **Examples**: Check `examples/goal_agent_generator/`
- **Issues**: Report at https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues

---

## What's Next?

**Current:** Phase 1 MVP (validated, production-ready)

**Future Phases** (pending evidence of need):

- **Phase 2**: AI-generated custom skills (if skill gaps emerge)
- **Phase 3**: Multi-agent coordination (if complex goals require it)
- **Phase 4**: Learning from execution history (after 100+ runs)

**Philosophy:** Build based on evidence, not speculation.

---

**Last Updated:** 2025-11-11
**Version:** 1.0.0 (Phase 1 MVP)
