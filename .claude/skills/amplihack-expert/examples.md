# amplihack Usage Examples

## Example 1: Feature Development

**Task:** Add JWT auth to API

```
User: "Add JWT authentication to the API"
→ /ultrathink (DEFAULT_WORKFLOW)

Steps:
1. prompt-writer → Clarify (endpoints, expiration, refresh)
2. architect → Design (middleware, service, specs)
3-5. Git branch, implementation order
6. builder → Code (middleware.py, jwt_service.py)
7-9. Pre-commit, tests, validation
10. reviewer → Compliance ✓
13-15. Commit, push, PR
16. CI green ✓
```

## Example 2: Investigation

**Task:** Understand agent system

```
User: "How does agent delegation work?"
→ /ultrathink (INVESTIGATION_WORKFLOW)

Phases:
1. Scope: Agent delegation architecture
2. knowledge-archaeologist discovers agents/
3. Deep dive: Task tool patterns, parallel exec
4. Verify: Multi-agent examples
5. Synthesize: Architecture report
6. Document: ARCHITECTURE_agent-system.md
```

## Example 3: Rapid Fix

**Task:** Import error

```
User: "ModuleNotFoundError: No module named 'requests'"
→ /fix import QUICK

Actions:
✓ Detect: Missing dependency
✓ Install: pip install requests
✓ Update: requirements.txt
Duration: 30s
```

## Example 4: Parallel Review

**Task:** Comprehensive review

```
User: "Review auth module"
→ Parallel agents: [analyzer, security, optimizer, patterns, reviewer]

Results (90s):
✓ analyzer: Well-structured
✓ security: JWT best practices
✓ optimizer: O(1) validation
✓ patterns: Factory pattern
✓ reviewer: 92% compliance
```

## Example 5: Document-Driven Development

**Task:** Large feature (15+ files)

```
User: "Implement rate limiting"
→ /amplihack:ddd:prime

Phases:
0. Plan: 15 files, API.md, ARCHITECTURE.md
1. Retcon docs: Describe AS IF exists
2. Review: User approves design
3. Architect: Specs from docs
4. Builder: Code matches docs
5. Finish: Tests, no drift
```

## Command Selection Guide

| Request                   | Command               | Workflow               |
| ------------------------- | --------------------- | ---------------------- |
| Add feature               | /ultrathink           | DEFAULT_WORKFLOW       |
| How X works               | /ultrathink           | INVESTIGATION_WORKFLOW |
| Fix error                 | /fix                  | FIX_WORKFLOW           |
| Large feature (10+ files) | /amplihack:ddd:1-plan | DDD_WORKFLOW           |
| Critical code             | /amplihack:n-version  | N_VERSION_WORKFLOW     |
| Decision                  | /amplihack:debate     | DEBATE_WORKFLOW        |
