# amplihack Architecture Reference

## 1. Four Extensibility Mechanisms

| Mechanism | Invoked By                     | Method                      | Purpose           |
| --------- | ------------------------------ | --------------------------- | ----------------- |
| Workflow  | Commands, Skills, Agents       | Read file, follow steps     | Process blueprint |
| Command   | User, Commands, Skills, Agents | `/cmd` OR SlashCommand tool | Entry point       |
| Skill     | Auto-discovery                 | Triggers OR Skill tool      | Auto-capability   |
| Agent     | Commands, Skills, Agents       | Task tool + subagent_type   | Delegation        |

**Invocation Examples:**

- Command: `SlashCommand(command="/ultrathink task")`
- Skill: `Skill(skill="mermaid-diagram-generator")`
- Agent: `Task([{subagent_type: "architect", ...}])`
- Workflow: Read DEFAULT_WORKFLOW.md, follow steps

## 2. Five-Layer Architecture

```
Layer 5: Integration    │ MCP, GitHub, CI/CD
Layer 4: User          │ CLAUDE.md, preferences
Layer 3: Content       │ Workflows, agents, commands
Layer 2: Framework     │ Task, SlashCommand tools
Layer 1: Runtime       │ Logs, metrics, state
```

**Paths:**

- L1: `.claude/runtime/`
- L2: Core tools
- L3: `.claude/{workflow,agents,commands,skills}/`
- L4: `CLAUDE.md`, `USER_PREFERENCES.md`
- L5: MCP servers, hooks

## 3. DEFAULT_WORKFLOW (23 Steps)

**Planning (0-5):** 0. Read workflow + classify

1. prompt-writer clarifies
2. architect designs
3. Git branch
4. Module specs
5. Implementation order

**Implementation (6-12):** 6. builder codes 7. Pre-commit hooks 8. tester generates tests 9. Run tests 10. reviewer checks 11. security audit 12. optimizer check

**Integration (13-18):** 13. Git commit 14. Push remote 15. Create PR 16. CI check 17. Fix CI 18. Request review

**Completion (19-22):** 19. Address feedback 20. Final validation 21. Merge PR 22. Cleanup docs

**UltraThink:**

- Reads DEFAULT_WORKFLOW.md
- Creates task entries
- Delegates to agents
- Tracks progress
- Ensures compliance

## 4. Agent System

**Core:** architect, builder, reviewer, tester
**Specialized:** fix-agent, knowledge-archaeologist, prompt-writer, philosophy-guardian
**Diagnostic:** pre-commit-diagnostic, ci-diagnostic-workflow, environment-diagnostic

**Parallel Patterns:**

```
Feature: [architect, security, database, api-designer, tester]
Review: [analyzer, security, optimizer, patterns, reviewer]
Debug: [analyzer, environment, patterns, logs]
```

**Delegation Rules:**

- Design → architect
- Code → builder
- Quality → reviewer
- Tests → tester
- Performance → optimizer
- Security → security
- Unclear → prompt-writer
- Compliance → philosophy-guardian

## 5. Hook System

**Active Hooks:**

1. pre-commit: Quality check before commit
2. continuous-work: Auto re-exec on changes (`/amplihack:lock`)
3. ci-webhook: Listen for CI updates
4. session-logger: Log to `.claude/runtime/logs/`
5. git-integration: Validate before push

## 6. Composition Rules

**Valid:**

- Commands → Workflows: `/ultrathink` reads DEFAULT_WORKFLOW.md
- Commands → Commands: `/improve` invokes `/amplihack:reflect`
- Commands → Agents: `/analyze` delegates to analyzer
- Skills → Agents: `test-gap-analyzer` invokes tester
- Agents → Skills: architect invokes `mermaid-diagram-generator`
- Workflows → Agents: Step 1 uses prompt-writer

**Avoid:**

- Circular dependencies
- Deep nesting (>3 levels)
- Sequential when parallel works
- Over-orchestration

## 7. Integration Patterns

**MCP Servers:**

- docker-mcp: Container management
- workiq: M365 Copilot access

**GitHub:**

- gh CLI (preferred): `gh pr create`, `gh issue list`
- API (fallback): ci_status.py, github_issue.py

**CI/CD:**

- Pre-commit: Local validation, 80% CI catch
- Actions: CI on push, monitored by agent
- Continuous: Watch changes, auto re-run
