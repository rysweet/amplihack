# Decision Record Template

## Quick Copy Template

```markdown
## [TIMESTAMP] - [COMPONENT]
**Decision**:
**Reasoning**:
**Alternatives**:
**Impact**:
**Next Steps**:
---
```

## Detailed Examples

### Task Start Decision
```markdown
## 2025-01-16 14:30:00 - Task Start
**Decision**: Begin implementing user authentication feature
**Reasoning**: Core requirement for application security
**Alternatives**: Use existing auth service, delay implementation
**Impact**: Creates new auth module, adds login/logout endpoints
**Next Steps**: Use architect agent to design auth architecture
---
```

### Agent Delegation Decision
```markdown
## 2025-01-16 14:31:00 - Agent Delegation
**Decision**: Use architect agent for auth system design
**Reasoning**: Complex security requirements need proper analysis
**Alternatives**: Direct implementation, use security agent only
**Impact**: Will create detailed specifications before coding
**Next Steps**: Provide requirements to architect agent
---
```

### Technical Approach Decision
```markdown
## 2025-01-16 14:35:00 - Technical Approach
**Decision**: Implement JWT-based authentication
**Reasoning**: Stateless, scalable, industry standard
**Alternatives**: Session-based auth, OAuth2, API keys
**Impact**: Requires JWT library, token refresh logic
**Next Steps**: Builder agent to implement JWT handlers
---
```

### Error Handling Decision
```markdown
## 2025-01-16 14:45:00 - Error Recovery
**Decision**: Add retry logic for database connections
**Reasoning**: Transient network issues causing failures
**Alternatives**: Fail fast, circuit breaker pattern
**Impact**: More resilient but adds complexity
**Next Steps**: Implement exponential backoff retry
---
```

### Completion Decision
```markdown
## 2025-01-16 15:00:00 - Task Complete
**Decision**: Mark authentication feature as complete
**Reasoning**: All tests passing, requirements met
**Alternatives**: Additional security hardening
**Impact**: Feature ready for production
**Next Steps**: Update DISCOVERIES.md with learnings
---
```

## Decision Types to Record

### Always Record
- Task starts and completions
- Agent invocations
- Architecture/design choices
- Technology selections
- Error recovery strategies
- Approach changes/pivots

### Context Dependent
- Performance optimizations (if significant)
- Refactoring decisions (if major)
- Dependency additions (if new)
- Configuration changes (if impactful)

## Anti-Patterns to Avoid

### Too Vague
❌ "Decided to fix the bug"
✅ "Decided to fix null pointer exception in UserService.getProfile() by adding validation"

### No Reasoning
❌ "Using Redis for caching"
✅ "Using Redis for caching because we need distributed cache across multiple servers"

### Missing Alternatives
❌ "Implementing REST API"
✅ "Implementing REST API (considered GraphQL but REST is simpler for CRUD operations)"

## Remember

- Decisions are for learning and audit trails
- Future you will thank current you for good records
- Teams benefit from understanding reasoning
- Good decisions can be reused as patterns