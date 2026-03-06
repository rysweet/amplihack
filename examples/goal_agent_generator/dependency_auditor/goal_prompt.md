# Goal: Dependency Security Auditor

Audit project dependencies for security vulnerabilities, license issues, and outdated packages.

## Constraints

- Must complete audit within 15 minutes
- Should check PyPI, npm, Maven depending on project
- Must identify high/critical severity CVEs
- Should respect license requirements

## Success Criteria

- Scans all dependencies (direct and transitive)
- Identifies packages with known CVEs
- Checks for deprecated packages
- Validates license compatibility
- Reports outdated dependencies
- Suggests safe upgrade paths
- Generates security report with CVSS scores

## Context

Dependency auditing includes:

- Running safety, pip-audit for Python
- Checking npm audit for Node.js
- Querying CVE databases
- Validating licenses
- Finding update paths
