# Security Documentation

> [Home](../index.md) > Security

Ahoy! This be where ye learn to keep yer ship secure from digital pirates.

## Quick Navigation

**Essential Security Practices:**

- [Security Recommendations](../SECURITY_RECOMMENDATIONS.md) - START HERE for security basics
- [Security Context Preservation](../SECURITY_CONTEXT_PRESERVATION.md) - Maintain security through sessions

**New in PR #1925 (Issue #1922):**

- [Token Sanitization Guide](./TOKEN_SANITIZATION_GUIDE.md) - Prevent token exposure in logs
- [Security API Reference](./SECURITY_API_REFERENCE.md) - Complete API documentation
- [Security Testing Guide](./SECURITY_TESTING_GUIDE.md) - How to test security features

---

## Security Features Overview

### Token Sanitization (NEW)

Automatically detect and redact sensitive tokens from logs, errors, and debug output.

**Quick Start**:

```python
from amplihack.proxy.security import TokenSanitizer

sanitizer = TokenSanitizer()
safe_msg = sanitizer.sanitize("Token: gho_abc123xyz")
# Output: "Token: [REDACTED-GITHUB-TOKEN]"
```

**Supported Token Types**:

- GitHub tokens (gho*, ghp*, ghs*, ghu*, ghr\_)
- OpenAI API keys (sk-, sk-proj-)
- Anthropic API keys (sk-ant-)
- Bearer tokens
- JWT tokens
- Azure keys and connection strings

**Documentation**:

- [Token Sanitization Guide](./TOKEN_SANITIZATION_GUIDE.md) - Usage examples and patterns
- [Security API Reference](./SECURITY_API_REFERENCE.md) - Complete API documentation

### Model Validation (NEW)

Unified model validation preventing routing conflicts and injection attacks.

**Features**:

- Type checking and validation
- Format verification (alphanumeric + hyphens/dots)
- Path traversal prevention
- Length limits (200 chars max)
- ASCII-only enforcement

**Implementation**: `ModelValidator` class in `src/amplihack/proxy/server.py`

### Input Validation (NEW)

Security-focused input validation for all external data.

**Features**:

- Model name validation (prevents injection)
- Length checks (reasonable limits)
- Character pattern validation
- Path traversal checks
- Newline/null byte detection

**Implementation**: `validate_model_name()` in `src/amplihack/proxy/github_models.py`

### Secure File Permissions (NEW)

Automatic secure permissions for sensitive files.

**Features**:

- Token files: 0600 (read/write owner only)
- Config directories: 0700 (rwx owner only)
- Automatic permission enforcement on save

**Implementation**: `save_token()` in `src/amplihack/proxy/github_auth.py`

---

## Security Audits & Reviews

Comprehensive security analysis:

- [Neo4j Cleanup Security Audit](NEO4J_CLEANUP_SECURITY_AUDIT.md) - Memory system security review

---

## Safe Operations

Guidelines for secure autonomous operations:

- [Auto Mode Safety](../AUTOMODE_SAFETY.md) - Autonomous operation guardrails
- [Passthrough Mode](../PASSTHROUGH_MODE.md) - Direct API access patterns

---

## Configuration Security

Secure configuration practices:

- [Profile Management](../PROFILE_MANAGEMENT.md) - Secure environment configurations
- [Proxy Configuration](../PROXY_CONFIG_GUIDE.md) - Network security setup
- [Hook Configuration](../HOOK_CONFIGURATION_GUIDE.md) - Secure hook customization

---

## Azure & Cloud Security

Cloud deployment security:

- [Azure Integration](../AZURE_INTEGRATION.md) - Secure Azure deployment
- [Test Azure Proxy](../TEST_AZURE_PROXY.md) - Validate secure proxy setup

---

## Memory System Security

Securing agent memory and knowledge:

- [Memory System Security](../memory/README.md) - Memory security overview
- [Neo4j Session Cleanup](../features/neo4j-session-cleanup.md) - Secure resource management

---

## Testing Security Features

How to test and validate security implementations:

- [Security Testing Guide](./SECURITY_TESTING_GUIDE.md) - Complete testing guide
- Test coverage requirements: 90% minimum for security code
- Testing pyramid: 60% unit, 30% integration, 10% E2E

**Run Security Tests**:

```bash
# All security tests
pytest tests/proxy/test_security_sanitization.py -v

# With coverage
pytest tests/proxy/test_security_sanitization.py \
  --cov=amplihack.proxy.security \
  --cov-fail-under=90
```

---

## Best Practices

Security principles and patterns:

- [Development Philosophy](../PHILOSOPHY.md) - Security-first thinking
- [Trust & Anti-Sycophancy](../../.claude/context/TRUST.md) - Honest, secure agent behavior
- [Workflow Enforcement](../workflow-enforcement.md) - Process security

### Quick Security Checklist

Before deploying:

- [ ] Tokens sanitized in all log output
- [ ] Input validation on all external data
- [ ] Secure file permissions (0600/0700)
- [ ] Model names validated
- [ ] Error messages sanitized
- [ ] Security tests pass (90% coverage)

---

## Related Documentation

- [Troubleshooting](../troubleshooting/README.md) - Security issue fixes
- [Features](../features/README.md) - Feature-specific security
- [Agents](../../.claude/agents/amplihack/specialized/security.md) - Security agent

---

## Security Issue Reporting

Found a security vulnerability? Report it:

1. **DO NOT** open a public GitHub issue
2. Email security issues to: [security contact TBD]
3. Include detailed reproduction steps
4. Allow 90 days for patch before disclosure

---

**Security First**: Always prioritize security over convenience. When in doubt, check [Security Recommendations](../SECURITY_RECOMMENDATIONS.md) first.

**New Features**: PR #1925 (Issue #1922) added comprehensive token sanitization, model validation, input validation, and secure file permissions. See documentation links above for complete details.
