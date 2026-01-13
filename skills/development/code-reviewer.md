# Code Reviewer

Systematic code review methodology focusing on security, performance, and maintainability.

## When to Use

- Reviewing pull requests
- Auditing existing codebase
- Pre-merge quality gates
- Learning from others' code
- Teaching code quality standards

## Review Priority Order

Always review in this order to catch critical issues first:

```
1. SECURITY      - Can this be exploited?
2. CORRECTNESS   - Does it work correctly?
3. PERFORMANCE   - Will it scale?
4. MAINTAINABILITY - Can others understand it?
5. STYLE         - Does it follow conventions?
```

## Security Focus Areas

### Input Validation

```python
# BAD: Direct use of user input
query = f"SELECT * FROM users WHERE id = {user_input}"

# GOOD: Parameterized queries
query = "SELECT * FROM users WHERE id = ?"
cursor.execute(query, (user_input,))
```

**Checklist:**
```
[ ] All user inputs validated and sanitized
[ ] SQL queries use parameterized statements
[ ] No command injection vulnerabilities (subprocess, exec)
[ ] No path traversal vulnerabilities
[ ] HTML output properly escaped (XSS prevention)
[ ] JSON/XML parsing handles malicious input
```

### Authentication & Authorization

```python
# BAD: Missing authorization check
@app.route('/admin/users')
def list_users():
    return get_all_users()

# GOOD: Explicit authorization
@app.route('/admin/users')
@require_role('admin')
def list_users():
    return get_all_users()
```

**Checklist:**
```
[ ] All endpoints require authentication (unless public)
[ ] Authorization checked for every action
[ ] No privilege escalation paths
[ ] Session tokens properly managed
[ ] Password handling follows best practices
[ ] API keys not hardcoded
```

### Secrets Management

```python
# BAD: Hardcoded secrets
API_KEY = "sk-1234567890abcdef"

# GOOD: Environment variables
API_KEY = os.environ.get('API_KEY')
if not API_KEY:
    raise ValueError("API_KEY not configured")
```

**Checklist:**
```
[ ] No secrets in source code
[ ] No secrets in logs
[ ] Secrets loaded from environment/vault
[ ] .env files in .gitignore
[ ] No accidental secret commits in git history
```

## Performance Considerations

### Database Operations

```python
# BAD: N+1 query problem
for user in users:
    orders = db.query(Order).filter_by(user_id=user.id).all()

# GOOD: Eager loading
users = db.query(User).options(joinedload(User.orders)).all()
```

**Checklist:**
```
[ ] No N+1 query patterns
[ ] Appropriate indexes for query patterns
[ ] Large result sets paginated
[ ] Transactions used appropriately
[ ] Connection pooling configured
[ ] No unnecessary queries in loops
```

### Memory & CPU

```python
# BAD: Loading entire file into memory
data = open('large_file.csv').read()

# GOOD: Streaming/chunked processing
with open('large_file.csv') as f:
    for line in f:
        process(line)
```

**Checklist:**
```
[ ] Large data processed in chunks/streams
[ ] No unnecessary data copies
[ ] Caches have size limits and eviction
[ ] Heavy computations optimized or async
[ ] No blocking operations in async code
[ ] Resource cleanup (files, connections closed)
```

### Concurrency

```python
# BAD: Race condition
if cache.get(key) is None:
    cache.set(key, compute_value())  # Multiple threads may compute

# GOOD: Atomic operation
cache.setdefault(key, lambda: compute_value())
```

**Checklist:**
```
[ ] Thread safety for shared resources
[ ] No race conditions in critical sections
[ ] Proper locking (minimal scope)
[ ] Deadlock-free lock ordering
[ ] Async/await used correctly
```

## Maintainability Assessment

### Code Clarity

```python
# BAD: Unclear intent
def p(d, k):
    return d.get(k, d.get('default', None))

# GOOD: Clear naming and structure
def get_config_value(config: dict, key: str) -> Optional[str]:
    """Get config value with fallback to default."""
    return config.get(key, config.get('default'))
```

**Checklist:**
```
[ ] Functions do one thing
[ ] Names are descriptive and consistent
[ ] Complex logic has comments explaining WHY
[ ] No magic numbers (use named constants)
[ ] Reasonable function length (<50 lines)
[ ] Reasonable file length (<500 lines)
```

### Error Handling

```python
# BAD: Swallowing exceptions
try:
    risky_operation()
except:
    pass

# GOOD: Specific handling with logging
try:
    risky_operation()
except ConnectionError as e:
    logger.warning(f"Connection failed: {e}, retrying...")
    retry_operation()
except ValueError as e:
    logger.error(f"Invalid data: {e}")
    raise
```

**Checklist:**
```
[ ] Exceptions caught at appropriate level
[ ] No bare except clauses
[ ] Errors logged with context
[ ] User-facing errors are helpful
[ ] Critical errors don't fail silently
[ ] Resources cleaned up in finally/context managers
```

### Testing

```python
# BAD: Test with no assertions
def test_user_creation():
    user = create_user("test@example.com")

# GOOD: Clear assertions
def test_user_creation():
    user = create_user("test@example.com")
    assert user.email == "test@example.com"
    assert user.id is not None
    assert user.created_at <= datetime.now()
```

**Checklist:**
```
[ ] New code has tests
[ ] Tests cover happy path and error cases
[ ] Tests are readable and maintainable
[ ] No flaky tests (time-dependent, order-dependent)
[ ] Mocking used appropriately (not excessively)
[ ] Edge cases covered
```

### API Design

```python
# BAD: Inconsistent API
def get_user(id): ...
def fetch_orders(user_id): ...
def retrieve_products(): ...

# GOOD: Consistent patterns
def get_user(id: int) -> User: ...
def get_orders(user_id: int) -> list[Order]: ...
def get_products() -> list[Product]: ...
```

**Checklist:**
```
[ ] Consistent naming conventions
[ ] Consistent parameter ordering
[ ] Consistent return types
[ ] Backwards compatibility maintained
[ ] Breaking changes clearly documented
[ ] API versioned appropriately
```

## Review Checklist Format

### For Each File Changed

```markdown
## File: `path/to/file.py`

### Security
- [ ] No injection vulnerabilities
- [ ] Input validation present
- [ ] Authorization checked

### Correctness
- [ ] Logic is correct
- [ ] Edge cases handled
- [ ] Error handling appropriate

### Performance
- [ ] No N+1 queries
- [ ] No memory leaks
- [ ] No blocking operations

### Maintainability
- [ ] Code is readable
- [ ] Tests included
- [ ] Documentation updated
```

### Summary Template

```markdown
## Review Summary

**Overall Assessment**: [Approve / Request Changes / Comment]

### Critical Issues (must fix)
1. [Issue description with line reference]

### Suggestions (should consider)
1. [Suggestion with rationale]

### Nits (optional)
1. [Minor style/preference items]

### Positive Feedback
- [What was done well]
```

## Common Code Smells

### Complexity Smells

| Smell | Indicator | Fix |
|-------|-----------|-----|
| Long Method | >30 lines | Extract methods |
| Long Parameter List | >4 params | Use object/config |
| Nested Conditionals | >3 levels deep | Early returns, extract |
| God Class | >500 lines, many responsibilities | Split into focused classes |

### Duplication Smells

| Smell | Indicator | Fix |
|-------|-----------|-----|
| Copy-Paste Code | Same logic in multiple places | Extract to shared function |
| Similar Classes | Classes with same structure | Extract base class/mixin |
| Repeated Conditions | Same if-check everywhere | Extract to helper |

### Coupling Smells

| Smell | Indicator | Fix |
|-------|-----------|-----|
| Feature Envy | Method uses other class more than own | Move method |
| Inappropriate Intimacy | Accessing private members | Use public interface |
| Message Chains | a.b().c().d() | Introduce delegating method |

## Review Etiquette

### Do

```
- Be specific: "Line 42: this could cause SQL injection" 
- Explain why: "This blocks the event loop because..."
- Suggest solutions: "Consider using asyncio.gather() instead"
- Acknowledge good work: "Nice use of the strategy pattern here"
- Ask questions: "I'm not sure I understand the intent here, could you explain?"
```

### Don't

```
- Be vague: "This code is bad"
- Be condescending: "Obviously you should..."
- Bikeshed: Spending 10 comments on formatting
- Block on style: When linters handle it
- Demand changes for preferences: "I would have done it differently"
```

## Quick Review Commands

```bash
# Check for common security issues
grep -r "exec(" --include="*.py"
grep -r "eval(" --include="*.py"
grep -r "subprocess" --include="*.py"

# Find TODOs and FIXMEs
grep -rn "TODO\|FIXME\|HACK\|XXX" --include="*.py"

# Check for hardcoded secrets patterns
grep -rE "(password|secret|api_key|token)\s*=" --include="*.py"

# Find long functions (rough estimate)
grep -c "def " *.py | awk -F: '$2 > 20 {print}'

# Check test coverage
pytest --cov --cov-report=term-missing
```
