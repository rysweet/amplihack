# Goal: Python Security Vulnerability Scanner

Scan Python codebases for common security vulnerabilities following OWASP guidelines.

## Constraints

- Must complete scan within 15 minutes
- Should check for OWASP Top 10 vulnerabilities
- Must provide remediation guidance
- Should generate structured reports

## Success Criteria

- Detects SQL injection vulnerabilities (string concatenation in queries)
- Finds hardcoded secrets and credentials
- Identifies insecure dependencies (known CVEs)
- Checks for XSS vulnerabilities
- Detects command injection risks
- Reports path traversal vulnerabilities
- Generates actionable fix recommendations

## Context

Security scanning for Python projects checking:

- SQL injection patterns (f-strings in queries, string concat)
- Hardcoded secrets (API keys, passwords in code)
- Dependency vulnerabilities (outdated packages with CVEs)
- Command injection (shell=True, os.system with user input)
- Path traversal (user input in file paths)
