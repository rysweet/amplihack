# Cybersecurity Analyst - Domain Validation Quiz

## Purpose

This quiz validates that the cybersecurity analyst applies security frameworks correctly, identifies vulnerabilities and threats, and provides well-grounded analysis. Each scenario requires demonstration of security reasoning, threat modeling, and evidence-based risk assessment.

---

## Scenario 1: Zero-Day Vulnerability Disclosure

**Event Description**:
A security researcher discovers a remote code execution vulnerability in a widely-used web server software (nginx) affecting versions from the past 3 years. The vulnerability allows attackers to execute arbitrary code by sending specially crafted HTTP headers. The researcher has not yet publicly disclosed the vulnerability but has contacted the vendor. The vendor acknowledges the issue and estimates 2 weeks for a patch. The researcher debates immediate public disclosure versus coordinated disclosure.

**Analysis Task**:
Analyze the vulnerability disclosure decision and broader security implications.

### Expected Analysis Elements

- [ ] **Vulnerability Assessment**:
  - Remote Code Execution (RCE) - highest severity class
  - CVSS scoring framework (likely 9.0+ critical)
  - Attack vector: Network-based, no authentication required
  - Impact: Complete system compromise

- [ ] **Threat Modeling**:
  - Attack surface: All exposed nginx servers
  - Threat actors: Nation-state APTs, ransomware groups, opportunistic attackers
  - Time-to-exploit after disclosure (hours to days)
  - Weaponization potential for botnets, ransomware

- [ ] **Disclosure Trade-offs**:
  - **Immediate disclosure**: Public awareness, but attackers can exploit before patches
  - **Coordinated disclosure**: Vendor time to patch, but vulnerability remains secret longer
  - **Responsible disclosure**: 90-day window standard
  - Risk of independent discovery or leak

- [ ] **Risk Assessment**:
  - Scope: Millions of servers potentially affected
  - Exploitability: High (network-accessible, no auth required)
  - Impact: Data breach, ransomware, botnet recruitment
  - Cascading effects: Supply chain, dependent services

- [ ] **Mitigation Strategies**:
  - Immediate: WAF rules, network segmentation, IDS signatures
  - Short-term: Vendor patch deployment
  - Long-term: Vulnerability management programs, version lifecycle
  - Compensating controls during patch window

- [ ] **Stakeholder Analysis**:
  - Vendor: Reputation risk, legal liability
  - Organizations: Patch management burden, potential breach
  - Researcher: Ethical obligations, legal protections (CFAA concerns)
  - Public: Right to know vs. protection from exploitation

- [ ] **Historical Context**:
  - Heartbleed (OpenSSL 2014): Mass exploitation, industry response
  - EternalBlue (SMB 2017): NSA exploit leaked, WannaCry ransomware
  - Log4Shell (2021): Rapid weaponization, widespread impact
  - Full disclosure vs. responsible disclosure debates

### Evaluation Criteria

- **Domain Accuracy** (0-10): Correct application of vulnerability assessment, CVSS, threat modeling
- **Analytical Depth** (0-10): Thoroughness of risk analysis, disclosure trade-offs, mitigation strategies
- **Insight Specificity** (0-10): Clear recommendations, specific mitigation measures
- **Historical Grounding** (0-10): References to precedent vulnerabilities, disclosure outcomes
- **Reasoning Clarity** (0-10): Logical flow from threat assessment to recommendations

**Minimum Passing Score**: 35/50

---

## Scenario 2: Ransomware Incident Response

**Event Description**:
At 3:00 AM, a hospital's IT systems begin displaying ransomware encryption screens. Initial investigation reveals: 60% of workstations encrypted, file servers compromised, backup systems partially affected. The ransom note demands $5 million in cryptocurrency for decryption keys, with 48-hour deadline. Electronic health records are inaccessible, affecting patient care. Law enforcement has been notified. Backups from 48 hours ago are available but potentially infected.

**Analysis Task**:
Analyze the incident and develop response strategy.

### Expected Analysis Elements

- [ ] **Incident Classification**:
  - Ransomware attack (encryption malware)
  - Critical infrastructure target (healthcare)
  - Active incident requiring immediate response
  - Potential data exfiltration (double extortion)

- [ ] **Immediate Response Actions**:
  - Containment: Isolate affected systems, segment networks
  - Preserve evidence: Forensic imaging, log collection
  - Activate incident response team
  - Communication protocols (internal, external, regulatory)
  - Patient safety prioritization

- [ ] **Technical Analysis**:
  - Malware identification (strain, variant, encryption method)
  - Initial access vector (phishing, vulnerability, credential compromise)
  - Lateral movement analysis (how did it spread)
  - Persistence mechanisms
  - Data exfiltration assessment

- [ ] **Decision Framework: Pay or Not Pay**:
  - **Against payment**: Funds criminals, no guarantee of decryption, legal concerns (OFAC sanctions)
  - **For payment**: Immediate restoration, patient care continuity
  - Alternative: Restore from backups (if clean and recent)
  - Insurance coverage considerations
  - Negotiation dynamics

- [ ] **Recovery Strategy**:
  - Backup restoration plan (verify integrity first)
  - System rebuild vs. decrypt decision
  - Critical services prioritization (life-safety first)
  - Validation and testing before production
  - Timeline and resource requirements

- [ ] **Regulatory and Legal**:
  - HIPAA breach notification (HHS, patients, media)
  - FBI/CISA reporting requirements
  - State attorney general notifications
  - Civil liability concerns
  - Insurance claims

- [ ] **Post-Incident Improvements**:
  - Root cause analysis
  - Security control gaps (MFA, network segmentation, backup isolation)
  - User training (phishing awareness)
  - Incident response plan refinement

- [ ] **Historical Context**:
  - WannaCry (2017): NHS impact, global disruption
  - NotPetya (2017): Masquerading as ransomware, destructive intent
  - Colonial Pipeline (2021): Critical infrastructure, payment decision
  - Healthcare sector targeting trends

### Evaluation Criteria

- **Domain Accuracy** (0-10): Correct application of incident response framework, containment strategies
- **Analytical Depth** (0-10): Thoroughness of technical analysis, decision framework, recovery planning
- **Insight Specificity** (0-10): Clear action priorities, specific containment measures
- **Historical Grounding** (0-10): References to similar incidents, industry best practices
- **Reasoning Clarity** (0-10): Logical prioritization and decision-making process

**Minimum Passing Score**: 35/50

---

## Scenario 3: Cloud Infrastructure Misconfiguration

**Event Description**:
A security audit reveals that a company's AWS S3 bucket containing customer data (names, emails, purchase history) has been publicly accessible for 8 months. The bucket stored logs and analytics data from the company's e-commerce platform. Web scraping evidence suggests automated bots have been indexing public S3 buckets and may have discovered this data. No evidence of malicious use yet, but data exposure is confirmed. The company has 50,000 active customers.

**Analysis Task**:
Analyze the data breach scenario and response requirements.

### Expected Analysis Elements

- [ ] **Incident Classification**:
  - Data breach (unauthorized exposure of PII)
  - Misconfiguration vulnerability (human error)
  - Exposure duration: 8 months
  - Scope: 50,000 customers

- [ ] **Technical Root Cause**:
  - S3 bucket policy misconfiguration (public read permissions)
  - Lack of access controls and monitoring
  - Infrastructure-as-Code (IaC) review gap
  - Missing automated compliance checks

- [ ] **Data Sensitivity Assessment**:
  - PII exposed: Names, emails, purchase history
  - Regulatory classification: Personal data under GDPR, CCPA
  - Potential harms: Phishing, identity theft, competitive intelligence
  - Data minimization principle violation

- [ ] **Breach Notification Requirements**:
  - **GDPR**: 72-hour notification to supervisory authority
  - **CCPA**: Consumer notification without unreasonable delay
  - **State laws**: Varies by state (e.g., California, New York)
  - Affected individual notification
  - Credit monitoring offerings (depending on data types)

- [ ] **Risk Assessment**:
  - Likelihood of exploitation: High (bot indexing confirmed)
  - Impact severity: Moderate (no financial data, but PII exposed)
  - Reputational damage: Significant (customer trust erosion)
  - Regulatory penalties: GDPR fines up to 4% revenue
  - Civil litigation risk: Class action potential

- [ ] **Remediation Actions**:
  - Immediate: Restrict bucket access, audit all other buckets
  - Short-term: Implement S3 bucket policies, AWS Config rules
  - Long-term: Infrastructure security review, IaC validation, least privilege
  - Monitoring: CloudTrail logging, automated compliance scanning

- [ ] **Defense in Depth Failures**:
  - Preventive controls: IAM policies, bucket policies
  - Detective controls: AWS Config, CloudTrail monitoring
  - Corrective controls: Automated remediation
  - Administrative controls: Security training, change management

- [ ] **Historical Context**:
  - Capital One breach (2019): S3 misconfiguration, SSRF vulnerability
  - Uber data breach (2016): S3 credentials exposed on GitHub
  - Verizon/NICE Systems (2017): 14M customer records exposed via S3
  - Industry pattern: Misconfigurations are leading cloud breach cause

### Evaluation Criteria

- **Domain Accuracy** (0-10): Correct application of breach notification requirements, cloud security principles
- **Analytical Depth** (0-10): Thoroughness of root cause, risk assessment, remediation strategy
- **Insight Specificity** (0-10): Clear notification timeline, specific remediation measures
- **Historical Grounding** (0-10): References to similar cloud breaches, regulatory outcomes
- **Reasoning Clarity** (0-10): Logical flow from incident to response to prevention

**Minimum Passing Score**: 35/50

---

## Scenario 4: Supply Chain Attack via Dependency

**Event Description**:
A popular npm package (10 million weekly downloads) used in thousands of applications releases version 2.3.5 containing malicious code. The code exfiltrates environment variables (potentially including API keys, credentials) to an attacker-controlled server. The malicious version was published after the maintainer's account was compromised through credential stuffing. The package remained compromised for 72 hours before detection. Your organization uses this package in 15 production applications.

**Analysis Task**:
Analyze the supply chain attack and organizational response.

### Expected Analysis Elements

- [ ] **Attack Classification**:
  - Supply chain attack (software supply chain)
  - Dependency confusion/poisoning variant
  - Account takeover as initial access
  - Widespread impact (thousands of downstream users)

- [ ] **Attack Vector Analysis**:
  - Initial access: Credential stuffing (poor password hygiene, no MFA)
  - Malicious payload: Environment variable exfiltration
  - Distribution: NPM package manager, automatic updates
  - Persistence: Semver auto-update rules (^2.3.0 pulls 2.3.5)

- [ ] **Blast Radius Assessment**:
  - Direct impact: 10M weekly downloads
  - Downstream: Thousands of applications
  - Your organization: 15 production applications affected
  - Data at risk: API keys, database credentials, secrets
  - Lateral movement potential: Compromised credentials enable further attacks

- [ ] **Immediate Response**:
  - Identify affected applications (dependency tree analysis)
  - Rotate all potentially exposed credentials
  - Downgrade to last known good version (2.3.4)
  - Network forensics: Check for data exfiltration
  - Incident response activation

- [ ] **Credential Compromise Assessment**:
  - Inventory exposed environment variables per application
  - Credential scope: Database, APIs, cloud providers, third-party services
  - Privilege levels: Admin vs. read-only
  - Blast radius from compromised credentials
  - Evidence of exploitation (log analysis)

- [ ] **Supply Chain Security Gaps**:
  - Dependency pinning vs. automatic updates
  - Software Bill of Materials (SBOM) missing
  - Package integrity verification (checksums, signatures)
  - Dependency scanning and vulnerability management
  - Least privilege for service accounts

- [ ] **Prevention and Detection**:
  - Software Composition Analysis (SCA) tools
  - Dependency lock files (package-lock.json)
  - Runtime monitoring for anomalous behavior
  - Secrets management (vault, no hardcoded credentials)
  - Network egress monitoring

- [ ] **Historical Context**:
  - SolarWinds (2020): Build system compromise, nation-state attack
  - Codecov (2021): Bash uploader script compromised
  - Event-stream npm incident (2018): Bitcoin wallet theft
  - UA-Parser-JS npm attack (2021): Cryptocurrency mining
  - Growing trend: 650% increase in supply chain attacks (2021)

### Evaluation Criteria

- **Domain Accuracy** (0-10): Correct application of supply chain security, credential management
- **Analytical Depth** (0-10): Thoroughness of blast radius, credential assessment, prevention
- **Insight Specificity** (0-10): Clear response actions, specific detection measures
- **Historical Grounding** (0-10): References to supply chain attacks, industry trends
- **Reasoning Clarity** (0-10): Logical flow from detection to containment to prevention

**Minimum Passing Score**: 35/50

---

## Scenario 5: Insider Threat Investigation

**Event Description**:
Security alerts flag unusual activity: A software engineer with database access has been running queries to download large customer datasets after business hours. The engineer's access is legitimate for their role, but the volume and timing are unusual. The engineer submitted resignation 2 weeks ago (effective in 2 weeks) and will join a competitor. HR confirms no non-compete agreement exists. Legal is concerned about trade secret theft. No evidence of data exfiltration outside the network yet, but USB activity is detected on the engineer's workstation.

**Analysis Task**:
Analyze the potential insider threat and response strategy.

### Expected Analysis Elements

- [ ] **Threat Classification**:
  - Insider threat (malicious or negligent)
  - Elevated access (legitimate database permissions)
  - Potential trade secret theft
  - Pre-departure risk indicator (resignation, competitor)

- [ ] **Behavioral Analysis**:
  - Indicators: Unusual hours, large data access, USB activity
  - Baseline deviation: Compare to normal work patterns
  - Intent assessment: Malicious (theft) vs. innocent (work completion)
  - Motivations: Financial gain, competitive advantage, revenge
  - Opportunity: Legitimate access, notice period window

- [ ] **Data at Risk**:
  - Customer data: PII, contact information, purchase behavior
  - Trade secrets: Proprietary algorithms, business intelligence
  - Intellectual property: Code, architecture, processes
  - Competitive intelligence: Pricing, strategy, customer relationships

- [ ] **Investigation Approach**:
  - Non-disruptive monitoring (avoid alerting suspect)
  - Log analysis: Database queries, file access, network traffic, USB devices
  - Endpoint forensics: File activity, email, cloud storage uploads
  - Correlation with business value data
  - Legal considerations: Privacy, consent, jurisdiction

- [ ] **Immediate Actions**:
  - Enhanced monitoring (not immediate revocation, to gather evidence)
  - Coordinate with HR, Legal, Management
  - Document everything (for potential litigation)
  - Revoke access strategically (when sufficient evidence or risk threshold)
  - Network egress controls (DLP, email monitoring)

- [ ] **Legal and HR Coordination**:
  - Trade secret protections (state laws, federal DTSA)
  - Civil litigation options (injunction, damages)
  - Criminal referral (if warranted - 18 USC 1831)
  - HR exit interview strategy
  - Non-disparagement and IP agreements at departure

- [ ] **Preventive Controls**:
  - User and Entity Behavior Analytics (UEBA)
  - Data Loss Prevention (DLP) systems
  - Least privilege access (why such broad database access?)
  - Pre-departure access reviews
  - Exit interview security components

- [ ] **Historical Context**:
  - Waymo vs. Uber (2017): Stolen self-driving car trade secrets
  - Tesla trade secret theft cases: Employees to Chinese competitors
  - Insider threats: 34% of data breaches (Verizon DBIR)
  - Average cost: $15.4M per insider threat incident (Ponemon)

### Evaluation Criteria

- **Domain Accuracy** (0-10): Correct application of insider threat frameworks, investigation techniques
- **Analytical Depth** (0-10): Thoroughness of behavioral analysis, legal considerations, evidence gathering
- **Insight Specificity** (0-10): Clear investigation steps, specific monitoring measures
- **Historical Grounding** (0-10): References to insider threat cases, industry statistics
- **Reasoning Clarity** (0-10): Logical balance between monitoring and action, legal coordination

**Minimum Passing Score**: 35/50

---

## Overall Quiz Assessment

### Scoring Summary

| Scenario                  | Max Score | Passing Score |
| ------------------------- | --------- | ------------- |
| 1. Zero-Day Disclosure    | 50        | 35            |
| 2. Ransomware Response    | 50        | 35            |
| 3. Cloud Misconfiguration | 50        | 35            |
| 4. Supply Chain Attack    | 50        | 35            |
| 5. Insider Threat         | 50        | 35            |
| **Total**                 | **250**   | **175**       |

### Passing Criteria

To demonstrate cybersecurity analyst competence:

- **Minimum per scenario**: 35/50 (70%)
- **Overall minimum**: 175/250 (70%)
- **Must pass at least 4 of 5 scenarios**

### Evaluation Dimensions

Each scenario is scored on:

1. **Domain Accuracy** (0-10): Correct application of security frameworks and methodologies
2. **Analytical Depth** (0-10): Thoroughness and sophistication of threat analysis
3. **Insight Specificity** (0-10): Clear, actionable security recommendations
4. **Historical Grounding** (0-10): Use of precedents, attack patterns, industry data
5. **Reasoning Clarity** (0-10): Logical flow, coherent risk assessment

### What High-Quality Analysis Looks Like

**Excellent (45-50 points)**:

- Applies multiple security frameworks accurately (NIST, MITRE ATT&CK, Kill Chain)
- Considers technical, operational, legal, and business dimensions
- Makes specific, prioritized recommendations with timelines
- Cites relevant precedents, CVEs, and industry statistics
- Clear logical flow from threat assessment to risk evaluation to response
- Acknowledges uncertainties and residual risks
- Identifies non-obvious attack vectors or defenses

**Good (35-44 points)**:

- Applies key security frameworks correctly
- Considers main technical and business impacts
- Makes reasonable response recommendations
- References some precedents or industry practices
- Clear reasoning
- Provides useful security insights

**Needs Improvement (<35 points)**:

- Misapplies security concepts or frameworks
- Ignores critical risks or response actions
- Vague or technically incorrect recommendations
- Lacks grounding in real-world attacks or defenses
- Unclear or illogical reasoning
- Superficial threat analysis

---

## Using This Quiz

### For Self-Assessment

1. Attempt each scenario analysis
2. Compare your analysis to expected elements
3. Score yourself honestly on each dimension
4. Identify areas for improvement

### For Automated Testing (Claude Agent SDK)

```python
from claude_agent_sdk import Agent, TestHarness

agent = Agent.load("cybersecurity-analyst")
quiz = load_quiz_scenarios("tests/quiz.md")

results = []
for scenario in quiz.scenarios:
    analysis = agent.analyze(scenario.event)
    score = evaluate_analysis(analysis, scenario.expected_elements)
    results.append({"scenario": scenario.name, "score": score})

assert sum(r["score"] for r in results) >= 175  # Overall passing
assert sum(1 for r in results if r["score"] >= 35) >= 4  # At least 4 scenarios pass
```

### For Continuous Improvement

- Add new scenarios as security incidents evolve
- Update expected elements as threat landscape changes
- Refine scoring criteria based on analyst performance patterns
- Use failures to improve cybersecurity analyst skill

---

**Quiz Version**: 1.0.0
**Last Updated**: 2025-11-16
**Status**: Production Ready
