# Security Review

Security assessment methodology for identifying and mitigating vulnerabilities.

## When to Use

- Reviewing code changes for security issues
- Auditing existing codebase security
- Pre-release security assessment
- After a security incident
- Implementing new authentication/authorization
- Handling sensitive data

## OWASP Top 10 Checklist

### A01: Broken Access Control

```python
# VULNERABLE: Missing authorization check
@app.route('/admin/users/<user_id>/delete')
def delete_user(user_id):
    db.delete_user(user_id)  # Anyone can delete!
    return "Deleted"

# SECURE: Proper authorization
@app.route('/admin/users/<user_id>/delete')
@require_role('admin')
def delete_user(user_id):
    db.delete_user(user_id)
    return "Deleted"
```

**Checklist:**
```
[ ] Authentication required for protected resources
[ ] Authorization checked for every action
[ ] No direct object reference vulnerabilities (IDOR)
[ ] Access control enforced server-side
[ ] Default deny policy implemented
[ ] CORS configured restrictively
```

### A02: Cryptographic Failures

```python
# VULNERABLE: Weak hashing
password_hash = hashlib.md5(password.encode()).hexdigest()

# SECURE: Strong password hashing
from passlib.hash import argon2
password_hash = argon2.hash(password)

# VULNERABLE: Hardcoded secrets
API_KEY = "sk-12345abcdef"

# SECURE: Environment variables
API_KEY = os.environ.get('API_KEY')
```

**Checklist:**
```
[ ] Strong password hashing (bcrypt, argon2, scrypt)
[ ] No hardcoded secrets in code
[ ] Secrets in environment variables or vault
[ ] TLS/HTTPS for data in transit
[ ] Encryption for sensitive data at rest
[ ] Proper key management
[ ] No deprecated crypto algorithms (MD5, SHA1, DES)
```

### A03: Injection

```python
# VULNERABLE: SQL injection
query = f"SELECT * FROM users WHERE id = {user_input}"
cursor.execute(query)

# SECURE: Parameterized queries
query = "SELECT * FROM users WHERE id = ?"
cursor.execute(query, (user_input,))

# VULNERABLE: Command injection
os.system(f"ping {user_input}")

# SECURE: Use subprocess with list args
subprocess.run(['ping', '-c', '1', user_input], check=True)
```

**Checklist:**
```
[ ] Parameterized queries for all database operations
[ ] No string concatenation in queries
[ ] Input validated before use
[ ] ORM used properly (no raw queries with user input)
[ ] Shell commands avoid user input
[ ] If user input in commands, strict whitelist validation
```

### A04: Insecure Design

**Checklist:**
```
[ ] Security requirements defined upfront
[ ] Threat modeling performed
[ ] Defense in depth implemented
[ ] Fail-secure defaults
[ ] Rate limiting on sensitive operations
[ ] Account lockout after failed attempts
[ ] Secure password reset flow
```

### A05: Security Misconfiguration

```python
# VULNERABLE: Debug mode in production
app.run(debug=True)

# SECURE: Environment-based configuration
app.run(debug=os.environ.get('ENV') == 'development')

# VULNERABLE: Verbose error messages
@app.errorhandler(Exception)
def handle_error(e):
    return str(e), 500  # Exposes internals

# SECURE: Generic error messages
@app.errorhandler(Exception)
def handle_error(e):
    logger.exception("Internal error")
    return "An error occurred", 500
```

**Checklist:**
```
[ ] Debug mode disabled in production
[ ] Default credentials changed
[ ] Unnecessary features disabled
[ ] Security headers configured
[ ] Error messages don't leak information
[ ] Directory listing disabled
[ ] Framework security settings reviewed
```

### A06: Vulnerable Components

```bash
# Check for vulnerabilities
pip-audit  # Python
npm audit  # JavaScript
cargo audit  # Rust

# Keep dependencies updated
pip install --upgrade package
npm update
```

**Checklist:**
```
[ ] Dependencies regularly updated
[ ] Known vulnerabilities checked (pip-audit, npm audit)
[ ] Only necessary dependencies included
[ ] Dependency pinning for reproducibility
[ ] Security advisories monitored
```

### A07: Authentication Failures

```python
# VULNERABLE: Weak session management
session_id = str(random.randint(1, 1000000))

# SECURE: Cryptographically secure tokens
import secrets
session_id = secrets.token_urlsafe(32)

# VULNERABLE: No rate limiting
@app.route('/login', methods=['POST'])
def login():
    if check_password(request.form['password']):
        return create_session()

# SECURE: With rate limiting
from flask_limiter import Limiter
limiter = Limiter(app)

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    if check_password(request.form['password']):
        return create_session()
```

**Checklist:**
```
[ ] Strong session tokens (cryptographically secure)
[ ] Session expiration implemented
[ ] Sessions invalidated on logout
[ ] Password complexity requirements
[ ] Rate limiting on authentication endpoints
[ ] Account lockout after failed attempts
[ ] MFA available for sensitive accounts
[ ] Secure "remember me" implementation
```

### A08: Data Integrity Failures

**Checklist:**
```
[ ] Integrity checks on critical data
[ ] Signed tokens (JWT) verified properly
[ ] CI/CD pipeline secured
[ ] Code signing for releases
[ ] Supply chain security considered
```

### A09: Logging & Monitoring Failures

```python
# VULNERABLE: Logging sensitive data
logger.info(f"User logged in: {username}, password: {password}")

# SECURE: Sanitized logging
logger.info(f"User logged in: {username}")

# SECURE: Security event logging
logger.warning(f"Failed login attempt for user: {username}")
logger.warning(f"Unauthorized access attempt by user: {user_id}")
```

**Checklist:**
```
[ ] Security events logged (login, access, failures)
[ ] No sensitive data in logs (passwords, tokens, PII)
[ ] Logs protected from tampering
[ ] Alerting on suspicious activity
[ ] Log retention policy defined
[ ] Audit trail for sensitive operations
```

### A10: Server-Side Request Forgery (SSRF)

```python
# VULNERABLE: Fetching arbitrary URLs
@app.route('/fetch')
def fetch_url():
    url = request.args.get('url')
    return requests.get(url).text  # Can access internal services!

# SECURE: URL validation
ALLOWED_HOSTS = ['api.trusted.com', 'cdn.trusted.com']

@app.route('/fetch')
def fetch_url():
    url = request.args.get('url')
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_HOSTS:
        return "Invalid URL", 400
    return requests.get(url).text
```

**Checklist:**
```
[ ] User-provided URLs validated
[ ] Allowlist for external services
[ ] Internal network access blocked
[ ] URL scheme restricted (http/https only)
[ ] Redirects not followed blindly
```

## Input Validation Patterns

### Validation Strategies

```python
# Whitelist validation (preferred)
ALLOWED_STATUSES = {'pending', 'active', 'completed'}
if status not in ALLOWED_STATUSES:
    raise ValueError(f"Invalid status: {status}")

# Regex validation
import re
EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
if not EMAIL_PATTERN.match(email):
    raise ValueError("Invalid email format")

# Type validation with Pydantic
from pydantic import BaseModel, EmailStr, conint

class UserCreate(BaseModel):
    email: EmailStr
    age: conint(ge=0, le=150)
    role: Literal['user', 'admin']
```

### Sanitization

```python
# HTML escaping
from markupsafe import escape
safe_html = escape(user_input)

# SQL escaping (prefer parameterized queries)
# Don't do this - use parameterized queries instead

# Path sanitization
import os
safe_path = os.path.basename(user_filename)  # Strip directory components

# URL sanitization
from urllib.parse import quote
safe_url_param = quote(user_input)
```

## Authentication/Authorization Review

### Authentication Checklist

```
PASSWORDS
[ ] Minimum length (12+ characters)
[ ] Complexity requirements or strength meter
[ ] Bcrypt/Argon2/scrypt for hashing
[ ] Salt per password (automatic with above)
[ ] No password hints or security questions

SESSIONS
[ ] Secure, httponly cookies
[ ] Session regeneration on auth change
[ ] Absolute and idle timeout
[ ] Logout invalidates session server-side

MFA (if applicable)
[ ] TOTP implementation correct
[ ] Recovery codes available
[ ] MFA enforced for sensitive operations
```

### Authorization Checklist

```
ACCESS CONTROL
[ ] Every endpoint has authorization check
[ ] Authorization on server side (not just UI)
[ ] Default deny policy
[ ] Least privilege principle applied

ROLES & PERMISSIONS
[ ] Role hierarchy correct
[ ] Permission checks use AND not OR by default
[ ] No privilege escalation paths
[ ] Admin functions protected

DATA ACCESS
[ ] Users can only access their own data
[ ] No IDOR vulnerabilities
[ ] Consistent ownership checks
```

## Secrets Management

### Secrets Checklist

```
[ ] No secrets in source code
[ ] No secrets in git history
[ ] Secrets in environment variables or vault
[ ] .env files in .gitignore
[ ] Different secrets per environment
[ ] Secrets rotated regularly
[ ] Logging doesn't include secrets
```

### Finding Exposed Secrets

```bash
# Search for hardcoded secrets
grep -rE "(password|secret|api_key|token)\s*=\s*['\"]" --include="*.py"
grep -rE "-----BEGIN.*PRIVATE KEY-----" .

# Use specialized tools
# pip install detect-secrets
detect-secrets scan .

# GitLeaks for git history
# gitleaks detect --source .

# truffleHog for git history
# trufflehog git file://./
```

### Secrets Remediation

```bash
# If secret committed to git:
# 1. Rotate the secret immediately
# 2. Remove from history (if needed)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/secret" \
  --prune-empty --tag-name-filter cat -- --all

# 3. Force push (coordinate with team)
git push origin --force --all

# Better: use BFG Repo-Cleaner
bfg --delete-files sensitive.txt
```

## Common Vulnerabilities

### Path Traversal

```python
# VULNERABLE
@app.route('/files/<filename>')
def get_file(filename):
    return send_from_directory('/uploads', filename)
    # Request: /files/../../../etc/passwd

# SECURE
import os
@app.route('/files/<filename>')
def get_file(filename):
    # Ensure filename has no directory components
    safe_filename = os.path.basename(filename)
    filepath = os.path.join('/uploads', safe_filename)
    # Verify path is within allowed directory
    if not filepath.startswith('/uploads/'):
        abort(400)
    return send_file(filepath)
```

### Cross-Site Scripting (XSS)

```python
# VULNERABLE: Rendering user input as HTML
@app.route('/profile')
def profile():
    return f"<h1>Welcome, {request.args.get('name')}</h1>"
    # URL: /profile?name=<script>alert('xss')</script>

# SECURE: Use templating with auto-escaping
from flask import render_template
@app.route('/profile')
def profile():
    return render_template('profile.html', name=request.args.get('name'))
    # Jinja2 auto-escapes by default
```

### Insecure Deserialization

```python
# VULNERABLE: pickle with untrusted data
import pickle
data = pickle.loads(user_input)  # Can execute arbitrary code!

# SECURE: Use safe formats
import json
data = json.loads(user_input)  # Safe
```

## Security Review Checklist

### Quick Security Review

```
[ ] All user input validated
[ ] Parameterized database queries
[ ] No secrets in code
[ ] Authentication on all protected endpoints
[ ] Authorization checked for actions
[ ] Sensitive data encrypted/hashed
[ ] Error messages don't leak info
[ ] Logging doesn't include secrets
[ ] Dependencies checked for vulnerabilities
```

### Deep Security Review

```
AUTHENTICATION
[ ] Password policy enforced
[ ] Session management secure
[ ] Password reset secure
[ ] Rate limiting on auth endpoints

AUTHORIZATION
[ ] Every action authorized
[ ] No IDOR vulnerabilities
[ ] Privilege escalation tested
[ ] Default deny policy

DATA PROTECTION
[ ] Sensitive data encrypted at rest
[ ] TLS for data in transit
[ ] PII handled per regulations
[ ] Data retention policy

INJECTION
[ ] SQL injection tested
[ ] Command injection tested
[ ] Path traversal tested
[ ] XSS tested

INFRASTRUCTURE
[ ] Security headers configured
[ ] HTTPS enforced
[ ] Secrets management secure
[ ] Logging and monitoring
```

## Security Testing Commands

```bash
# Dependency vulnerabilities
pip-audit
npm audit
cargo audit

# Secret detection
detect-secrets scan .
gitleaks detect

# Static analysis
bandit -r src/  # Python security linter
semgrep --config=p/security-audit .

# Web vulnerability scanning
nikto -h http://localhost:8080
sqlmap -u "http://localhost:8080/search?q=test"
```
