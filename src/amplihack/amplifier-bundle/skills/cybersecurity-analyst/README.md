# Cybersecurity Analyst

## Overview

The Cybersecurity Analyst brings security-first thinking, threat modeling, and defense-in-depth principles to protect systems, data, and users. This skill analyzes threats, vulnerabilities, and risks across technical, human, and organizational dimensions to design secure systems and respond to security incidents.

Cybersecurity is not just about technology - it encompasses cryptography, network security, application security, human factors, legal compliance, and risk management. Modern security requires understanding attacker motivations, techniques, and economics while building defense strategies that balance security with usability and business needs.

This skill combines offensive security thinking (how attackers exploit systems) with defensive security practices (how to prevent, detect, and respond to attacks) to provide comprehensive security analysis.

## Core Capabilities

### 1. Threat Modeling

Systematically identifies potential threats, attack vectors, and security risks for systems, applications, and organizations. Threat modeling reveals vulnerabilities before attackers exploit them.

**Methodologies:**

- **STRIDE** - Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege
- **PASTA** - Process for Attack Simulation and Threat Analysis
- **Attack Trees** - Hierarchical diagrams of attack paths
- **Kill Chain** - Stages of cyber attacks (reconnaissance → delivery → exploitation → control)
- **MITRE ATT&CK** - Knowledge base of adversary tactics and techniques

### 2. Vulnerability Assessment

Identifies weaknesses in systems that could be exploited by attackers. Combines automated scanning with manual analysis to discover security flaws.

**Vulnerability Categories:**

- **Injection flaws** - SQL injection, command injection, XSS
- **Broken authentication/authorization** - Weak credentials, session management
- **Sensitive data exposure** - Unencrypted data, weak crypto
- **Security misconfiguration** - Default credentials, unnecessary services
- **Known vulnerabilities** - Unpatched CVEs, outdated dependencies
- **Design flaws** - Architectural security weaknesses

### 3. Cryptography Analysis

Evaluates cryptographic implementations, key management, and protocols. Ensures proper use of encryption, hashing, digital signatures, and random number generation.

**Key Areas:**

- **Encryption** - AES, RSA, elliptic curves (proper algorithms, key lengths, modes)
- **Hashing** - SHA-256, bcrypt, Argon2 (password storage, integrity)
- **Key management** - Generation, storage, rotation, destruction
- **TLS/SSL** - Certificate validation, protocol versions, cipher suites
- **PKI** - Public key infrastructure and certificate authorities

### 4. Access Control and Identity Management

Analyzes authentication, authorization, and identity systems to ensure proper access controls.

**Principles:**

- **Least privilege** - Minimum necessary permissions
- **Separation of duties** - No single person has complete control
- **Defense in depth** - Multiple layers of security
- **Zero trust** - Never trust, always verify
- **MFA/2FA** - Multi-factor authentication requirements

### 5. Security Monitoring and Incident Response

Designs detection mechanisms and response procedures for security incidents.

**Components:**

- **Logging and monitoring** - SIEM, IDS/IPS, anomaly detection
- **Incident response** - Preparation, detection, containment, eradication, recovery, lessons learned
- **Forensics** - Evidence collection and analysis
- **Threat intelligence** - Understanding attacker TTPs (Tactics, Techniques, Procedures)

### 6. Application Security (AppSec)

Applies security principles throughout software development lifecycle.

**Practices:**

- **Secure coding** - Input validation, output encoding, parameterized queries
- **SAST/DAST** - Static and dynamic application security testing
- **Dependency scanning** - Known vulnerabilities in libraries
- **Security testing** - Penetration testing, fuzzing, red team exercises
- **Secure SDLC** - Security requirements, design review, code review

## Use Cases

### System and Application Design

Apply security principles during design phase to build secure systems from the ground up. Threat model architectures before implementation to identify and mitigate risks early.

### Code Review and Security Testing

Review code for security vulnerabilities, test applications for exploitable flaws, and scan dependencies for known CVEs. Conduct penetration testing to validate security controls.

### Incident Response and Forensics

Respond to security incidents, contain breaches, analyze attacker behavior, collect forensic evidence, and implement remediation to prevent recurrence.

### Compliance and Risk Management

Assess compliance with security standards (SOC 2, ISO 27001, GDPR, HIPAA, PCI-DSS), evaluate risk posture, and prioritize security investments based on threat and impact.

### Security Architecture Review

Evaluate security architectures for defense-in-depth, identify single points of failure, assess attack surface, and recommend security improvements.

## Key Methods

### Method 1: STRIDE Threat Modeling

Apply STRIDE to identify threats:

1. **Spoofing** - Attacker impersonates user/system
2. **Tampering** - Unauthorized modification of data
3. **Repudiation** - Denying actions without proof
4. **Information Disclosure** - Exposing sensitive information
5. **Denial of Service** - Making system unavailable
6. **Elevation of Privilege** - Gaining unauthorized permissions

For each component, ask: What STRIDE threats apply?

### Method 2: Attack Surface Analysis

Map all entry points and assess risk:

1. Enumerate interfaces (APIs, UI, network services)
2. Identify input sources (user input, file uploads, API calls)
3. Map trust boundaries (internal vs. external, privileged vs. unprivileged)
4. Assess attack complexity and likelihood
5. Prioritize reduction of attack surface

### Method 3: Defense in Depth

Layer security controls:

1. **Perimeter** - Firewalls, VPN, network segmentation
2. **Network** - IDS/IPS, network monitoring
3. **Host** - Endpoint protection, hardening, patching
4. **Application** - Input validation, secure coding, WAF
5. **Data** - Encryption at rest and in transit
6. **User** - Strong authentication, least privilege, training

### Method 4: Risk Assessment (CVSS)

Quantify vulnerability severity using Common Vulnerability Scoring System:

- **Base score** - Intrinsic qualities of vulnerability
- **Temporal score** - Current exploit availability
- **Environmental score** - Impact in specific environment
- Prioritize remediation by risk score

### Method 5: Security Testing Pyramid

Test security at multiple levels:

1. **Unit tests** - Security test cases for functions
2. **Integration tests** - Security of component interactions
3. **SAST** - Static analysis of source code
4. **DAST** - Dynamic testing of running application
5. **Penetration testing** - Manual security testing by experts

## Resources

### Essential Reading

- **"The Web Application Hacker's Handbook"** - Comprehensive web security
- **"Threat Modeling: Designing for Security"** - Adam Shostack
- **"The Tangled Web"** - Browser security by Michal Zalewski
- **"Security Engineering"** - Ross Anderson (comprehensive security principles)
- **OWASP Top 10** - Most critical web application security risks

### Key Frameworks

- **OWASP** - Open Web Application Security Project resources
- **NIST Cybersecurity Framework** - Risk management framework
- **CIS Controls** - Prioritized security best practices
- **MITRE ATT&CK** - Adversary tactics and techniques
- **STRIDE/DREAD** - Threat modeling methodologies

### Standards and Compliance

- **PCI-DSS** - Payment card industry security
- **GDPR** - European data protection regulation
- **HIPAA** - Healthcare data security (US)
- **SOC 2** - Service organization security controls
- **ISO 27001** - Information security management

### Tools

- **Burp Suite** - Web application security testing
- **Metasploit** - Penetration testing framework
- **Wireshark** - Network protocol analyzer
- **Nmap** - Network scanning and enumeration
- **OWASP ZAP** - Web app vulnerability scanner
- **Snyk/Dependabot** - Dependency vulnerability scanning

## Links

- [Agent Implementation](/Users/ryan/src/Fritmp/amplihack/.claude/skills/cybersecurity-analyst/cybersecurity-analyst.md)
- [Quick Reference](/Users/ryan/src/Fritmp/amplihack/.claude/skills/cybersecurity-analyst/QUICK_REFERENCE.md)
- [All Skills](/Users/ryan/src/Fritmp/amplihack/.claude/skills/README.md)

## Best Practices

**Do:**

- Assume breach (defense in depth)
- Practice least privilege
- Validate all input, encode all output
- Use secure defaults
- Keep security simple (complexity is the enemy)
- Log security events
- Encrypt sensitive data (at rest and in transit)
- Keep dependencies updated
- Threat model during design
- Security test before deployment

**Don't:**

- Rely on security through obscurity
- Roll your own crypto
- Store passwords in plain text or weak hashes
- Trust client-side validation
- Ignore security in development
- Disable security features for convenience
- Use default credentials
- Forget about human factors (social engineering)
- Assume you'll never be attacked

## Integration with Amplihack

Security aligns with amplihack's ruthless simplicity - complex systems have more attack surface and are harder to secure. Simple, well-understood security controls are more effective than elaborate schemes. Security-first thinking ensures long-term sustainability by protecting against threats that could destroy trust and viability.

## Key Security Principles

1. **Defense in Depth** - Multiple layers of security
2. **Least Privilege** - Minimum necessary permissions
3. **Fail Securely** - Errors should default to secure state
4. **Complete Mediation** - Check every access
5. **Separation of Privilege** - Multiple conditions for access
6. **Open Design** - Security should not depend on secrecy of design
7. **Economy of Mechanism** - Keep security simple
8. **Psychological Acceptability** - Security should be usable
