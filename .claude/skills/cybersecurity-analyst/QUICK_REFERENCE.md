# Cybersecurity Analyst - Quick Reference

## TL;DR

Analyze systems through security lenses: threat modeling (STRIDE), vulnerability assessment, cryptography validation, access control, incident response, and application security. Apply defense-in-depth and assume breach mentality to protect confidentiality, integrity, and availability.

## When to Use

**Perfect For:**

- System and application security design
- Threat modeling and risk assessment
- Code review for security vulnerabilities
- Incident response and forensics
- Compliance assessment (SOC 2, GDPR, HIPAA)
- Security architecture review
- Penetration testing scoping
- Cryptography implementation review
- Access control design

**Skip If:**

- System has no security requirements
- Working with purely public, non-sensitive data
- Focused on pure functionality without threat context

## Core Frameworks

### CIA Triad

The foundation of security:

- **Confidentiality** - Prevent unauthorized information disclosure
- **Integrity** - Prevent unauthorized modification
- **Availability** - Ensure authorized users can access system

### STRIDE Threat Model

Six threat categories:

1. **Spoofing** - Impersonating user/system (authentication)
2. **Tampering** - Modifying data/code (integrity)
3. **Repudiation** - Denying actions (logging/audit)
4. **Information Disclosure** - Exposing data (confidentiality)
5. **Denial of Service** - Making unavailable (availability)
6. **Elevation of Privilege** - Gaining unauthorized access (authorization)

### OWASP Top 10 (2021)

Most critical web vulnerabilities:

1. Broken Access Control
2. Cryptographic Failures
3. Injection
4. Insecure Design
5. Security Misconfiguration
6. Vulnerable and Outdated Components
7. Identification and Authentication Failures
8. Software and Data Integrity Failures
9. Security Logging and Monitoring Failures
10. Server-Side Request Forgery (SSRF)

### Defense in Depth

Multiple security layers:

- **Perimeter** - Firewall, VPN
- **Network** - Segmentation, IDS/IPS
- **Host** - Endpoint protection, hardening
- **Application** - Input validation, secure coding
- **Data** - Encryption, access control
- **User** - MFA, least privilege, training

## Quick Analysis Steps

### Step 1: Asset and Trust Boundary Identification (5 min)

- What assets need protection? (data, systems, users)
- What are the trust boundaries? (internet/DMZ, DMZ/internal, user/admin)
- Who are potential attackers? (external, insider, nation-state)
- What's the impact if compromised? (financial, reputation, legal)

### Step 2: STRIDE Threat Modeling (10 min)

For each component/interface:

- **S**: Can attacker impersonate? (weak auth, no MFA)
- **T**: Can data be tampered? (no integrity checks, MITM)
- **R**: Can actions be denied? (no audit logging)
- **I**: Can data be leaked? (no encryption, excessive permissions)
- **D**: Can service be disrupted? (no rate limiting, resource exhaustion)
- **E**: Can privileges be escalated? (injection flaws, broken access control)

### Step 3: Vulnerability Identification (10 min)

Check for common vulnerabilities:

- **Input validation** - SQL injection, XSS, command injection
- **Authentication** - Weak passwords, no MFA, session fixation
- **Authorization** - Broken access control, insecure direct object references
- **Cryptography** - Weak algorithms, hardcoded keys, plain text passwords
- **Configuration** - Default credentials, unnecessary services, verbose errors
- **Dependencies** - Known CVEs, outdated libraries

### Step 4: Attack Surface Assessment (7 min)

- List all entry points (APIs, forms, file uploads, network ports)
- Identify external vs. internal interfaces
- Map unauthenticated vs. authenticated access
- Count input sources requiring validation
- Prioritize highest-risk interfaces

### Step 5: Security Controls Evaluation (10 min)

Assess existing controls:

- **Prevention** - Input validation, access control, encryption
- **Detection** - Logging, monitoring, anomaly detection
- **Response** - Incident response plan, backup/recovery
- **Gaps** - What's missing? What's weak?

### Step 6: Risk Prioritization and Recommendations (8 min)

- Calculate risk: Likelihood × Impact
- Prioritize by CVSS score or qualitative risk (Critical, High, Medium, Low)
- Recommend mitigations (prevent, detect, respond)
- Quick wins vs. long-term hardening
- Ensure defense in depth

## Key Security Principles

### Least Privilege

Give minimum necessary permissions:

- Users: Only access they need for their job
- Services: Run with minimal OS privileges
- APIs: Scoped tokens, not full access
- Databases: Specific grants, not root

### Fail Securely

On error, default to secure state:

- Authentication failure → Deny access (not grant)
- Authorization error → Deny (not allow)
- Crypto error → Reject (not continue insecurely)

### Never Trust Input

All input is malicious until validated:

- Validate on server side (not just client)
- Whitelist, don't blacklist
- Encode output to prevent XSS
- Use parameterized queries to prevent SQLi

### Defense in Depth

Never rely on single security control - layer multiple defenses.

## Common Vulnerabilities

### Injection Flaws

**SQL Injection**: Attacker injects SQL into queries

- **Prevention**: Parameterized queries, ORMs, input validation

**Command Injection**: Attacker executes OS commands

- **Prevention**: Avoid system calls, validate/sanitize input, use safe APIs

**XSS (Cross-Site Scripting)**: Attacker injects malicious scripts

- **Prevention**: Output encoding, Content Security Policy, HTTPOnly cookies

### Broken Authentication

- **Weak passwords**: No complexity requirements
- **No MFA**: Single factor is insufficient
- **Session fixation/hijacking**: Predictable session IDs

**Prevention**: Strong password policy, MFA, secure session management

### Broken Access Control

- **IDOR (Insecure Direct Object References)**: Access objects by guessing IDs
- **Path traversal**: Access unauthorized files (../../../etc/passwd)
- **Missing authorization**: Forgot to check permissions

**Prevention**: Validate authorization on every request, use indirect references

### Sensitive Data Exposure

- **Unencrypted data**: Plain text passwords, credit cards
- **Weak crypto**: MD5, DES, ECB mode
- **Insecure transmission**: HTTP instead of HTTPS

**Prevention**: Encrypt at rest and in transit, use strong algorithms (AES-256, SHA-256, Argon2)

## Resources

### Quick Checklists

- **OWASP Top 10** - Most critical web vulnerabilities
- **OWASP ASVS** - Application Security Verification Standard
- **CIS Benchmarks** - Hardening guides for systems

### Essential Tools

- **Burp Suite** - Web security testing
- **OWASP ZAP** - Automated vulnerability scanning
- **Snyk/Dependabot** - Dependency vulnerability checking
- **Nmap** - Network reconnaissance
- **Wireshark** - Network traffic analysis

### Learning Resources

- **PortSwigger Web Security Academy** - Free web security training
- **OWASP Cheat Sheets** - Quick security guidance
- **HackerOne/BugCrowd** - Bug bounty programs for practice

## Red Flags

**Major Security Issues:**

- Passwords in plain text or weak hashes (MD5, SHA-1)
- No input validation on user-supplied data
- Hardcoded secrets (API keys, passwords) in code
- Default credentials not changed
- No HTTPS (HTTP only)
- Missing authentication/authorization checks
- Verbose error messages exposing system details
- SQL queries built with string concatenation
- Outdated dependencies with known CVEs
- No security logging or monitoring

## Integration Tips

Combine with other skills:

- **Computer Scientist** - Cryptography theory, complexity
- **Lawyer** - Compliance and regulatory requirements
- **Systems Thinker** - Attack propagation and cascading failures
- **Psychologist** - Social engineering and human factors
- **Engineer** - Secure implementation and hardening

## Success Metrics

You've done this well when:

- All components threat modeled with STRIDE
- Critical vulnerabilities identified and prioritized
- Defense in depth applied (multiple layers)
- Cryptography uses modern, secure algorithms
- All inputs validated, all outputs encoded
- Least privilege enforced throughout
- Security logging captures relevant events
- Incident response plan defined
- Dependencies scanned for known CVEs
- Compliance requirements mapped and met
- Risk assessment completed with prioritized remediation
