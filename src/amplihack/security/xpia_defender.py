"""
XPIA Defender Core Implementation

Core security validation logic for detecting and preventing
Cross-Prompt Injection Attacks (XPIA).
"""

import json
import logging
import os
import re

# Import from specifications
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from .xpia_defense_interface import (
    ContentType,
    RiskLevel,
    SecurityConfiguration,
    SecurityLevel,
    ThreatDetection,
    ThreatType,
    ValidationContext,
    ValidationResult,
    XPIADefenseInterface,
)
from .xpia_patterns import (
    AttackPattern,
    PatternCategory,
    PromptPatterns,
    URLPatterns,
    XPIAPatterns,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class XPIADefender(XPIADefenseInterface):
    """
    Core XPIA Defense implementation

    Provides comprehensive security validation for various content types
    with configurable security levels.
    """

    def __init__(self, config: SecurityConfiguration | None = None):
        """Initialize XPIA Defender with configuration"""
        self.config = config or self._load_config_from_env()
        self.patterns = XPIAPatterns()
        self.whitelist = self._load_whitelist()
        self.blacklist = self._load_blacklist()
        self._security_events: list[dict[str, Any]] = []

        logger.info(f"XPIA Defender initialized with security level: {self.config.security_level}")

    def _load_config_from_env(self) -> SecurityConfiguration:
        """Load configuration from environment variables"""
        config = SecurityConfiguration()

        # Load security level
        level_str = os.getenv("XPIA_SECURITY_LEVEL", "MODERATE")
        level_map = {
            "STRICT": SecurityLevel.STRICT,
            "HIGH": SecurityLevel.HIGH,
            "MODERATE": SecurityLevel.MEDIUM,
            "MEDIUM": SecurityLevel.MEDIUM,
            "LENIENT": SecurityLevel.LOW,
            "LOW": SecurityLevel.LOW,
        }
        config.security_level = level_map.get(level_str.upper(), SecurityLevel.MEDIUM)

        # Load enabled state
        config.enabled = os.getenv("XPIA_ENABLED", "true").lower() != "false"

        # Load feature flags
        config.bash_validation = os.getenv("XPIA_BASH_VALIDATION", "true").lower() == "true"
        config.content_scanning = os.getenv("XPIA_CONTENT_SCANNING", "true").lower() == "true"
        config.logging_enabled = os.getenv("XPIA_LOGGING", "true").lower() == "true"

        return config

    def _load_whitelist(self) -> set[str]:
        """Load domain whitelist from environment or file"""
        whitelist = set()

        # Load from environment
        env_whitelist = os.getenv("XPIA_WHITELIST_DOMAINS", "")
        if env_whitelist:
            whitelist.update(domain.strip() for domain in env_whitelist.split(","))

        # Load from file if exists
        whitelist_file = os.getenv("XPIA_WHITELIST_FILE", ".xpia_whitelist")
        if os.path.exists(whitelist_file):
            with open(whitelist_file) as f:
                whitelist.update(line.strip() for line in f if line.strip())

        # Default safe domains
        whitelist.update(
            [
                "github.com",
                "microsoft.com",
                "azure.com",
                "openai.com",
                "anthropic.com",
                "stackoverflow.com",
                "python.org",
                "nodejs.org",
                "npmjs.com",
                "pypi.org",
            ]
        )

        return whitelist

    def _load_blacklist(self) -> set[str]:
        """Load domain blacklist from environment or file"""
        blacklist = set()

        # Load from environment
        env_blacklist = os.getenv("XPIA_BLACKLIST_DOMAINS", "")
        if env_blacklist:
            blacklist.update(domain.strip() for domain in env_blacklist.split(","))

        # Load from file if exists
        blacklist_file = os.getenv("XPIA_BLACKLIST_FILE", ".xpia_blacklist")
        if os.path.exists(blacklist_file):
            with open(blacklist_file) as f:
                blacklist.update(line.strip() for line in f if line.strip())

        return blacklist

    async def validate_content(
        self,
        content: str,
        content_type: ContentType,
        context: ValidationContext | None = None,
        security_level: SecurityLevel | None = None,
    ) -> ValidationResult:
        """
        Validate arbitrary content for security threats
        """
        if not self.config.enabled:
            return self._create_pass_result("XPIA validation disabled")

        security_level = security_level or self.config.security_level
        threats: list[ThreatDetection] = []

        # Detect attack patterns
        detected_patterns = self.patterns.detect_patterns(content)

        for pattern in detected_patterns:
            if self._should_flag_pattern(pattern, security_level):
                threats.append(self._pattern_to_threat(pattern, content))

        # Check for excessive length
        if PromptPatterns.is_excessive_length(content):
            threats.append(
                ThreatDetection(
                    threat_type=ThreatType.INJECTION,
                    severity=RiskLevel.MEDIUM,
                    description="Content exceeds safe length limit",
                    mitigation="Truncate or summarize content",
                )
            )

        # Determine overall risk level
        risk_level = self._calculate_risk_level(threats)

        # Generate recommendations
        recommendations = self._generate_recommendations(threats, security_level)

        # Log security event if needed
        if self.config.logging_enabled and threats:
            self._log_security_event(content_type, threats, context)

        return ValidationResult(
            is_valid=risk_level != RiskLevel.CRITICAL,
            risk_level=risk_level,
            threats=threats,
            recommendations=recommendations,
            metadata={
                "content_type": content_type.value,
                "security_level": security_level.value,
                "patterns_detected": len(detected_patterns),
            },
            timestamp=datetime.now(),
        )

    async def validate_bash_command(
        self,
        command: str,
        arguments: list[str] | None = None,
        context: ValidationContext | None = None,
    ) -> ValidationResult:
        """
        Validate bash commands for security threats
        """
        if not self.config.bash_validation:
            return self._create_pass_result("Bash validation disabled")

        threats: list[ThreatDetection] = []
        full_command = f"{command} {' '.join(arguments or [])}"

        # Check for dangerous commands
        dangerous_commands = [
            "rm -rf /",
            "mkfs",
            "dd if=/dev/zero",
            "fork bomb",
            ":(){ :|:& };:",
            "> /dev/sda",
            "chmod 777 /",
        ]

        for danger in dangerous_commands:
            if danger in full_command:
                threats.append(
                    ThreatDetection(
                        threat_type=ThreatType.MALICIOUS_CODE,
                        severity=RiskLevel.CRITICAL,
                        description=f"Dangerous command detected: {danger}",
                        mitigation="Block execution immediately",
                    )
                )

        # Check for privilege escalation attempts
        privilege_escalation_patterns = [
            r"\bsudo\s+su\b",
            r"\bchmod\s+777\s+/etc",
            r"\busermod\s+-[aG]+\s+sudo",
            r"\bsu\s+-\b",
        ]

        for pattern in privilege_escalation_patterns:
            if re.search(pattern, full_command):
                threats.append(
                    ThreatDetection(
                        threat_type=ThreatType.PRIVILEGE_ESCALATION,
                        severity=RiskLevel.HIGH,
                        description="Privilege escalation attempt detected",
                        mitigation="Block and review command",
                    )
                )

        # Check for command injection patterns
        injection_patterns = [
            r";\s*rm",
            r"&&\s*curl",
            r"\|\s*nc",
            r"`.*`",
            r"\$\(.*\)",
            r">\s*/dev/",
        ]

        for pattern in injection_patterns:
            if re.search(pattern, full_command):
                threats.append(
                    ThreatDetection(
                        threat_type=ThreatType.INJECTION,
                        severity=RiskLevel.HIGH,
                        description="Command injection pattern detected",
                        mitigation="Sanitize command input",
                    )
                )

        # Validate using general content validation
        content_result = await self.validate_content(
            full_command, ContentType.COMMAND, context, self.config.security_level
        )

        threats.extend(content_result.threats)

        risk_level = self._calculate_risk_level(threats)

        return ValidationResult(
            is_valid=risk_level not in [RiskLevel.HIGH, RiskLevel.CRITICAL],
            risk_level=risk_level,
            threats=threats,
            recommendations=content_result.recommendations,
            metadata={
                "command": command,
                "arguments": arguments,
            },
            timestamp=datetime.now(),
        )

    async def validate_agent_communication(
        self,
        source_agent: str,
        target_agent: str,
        message: dict[str, Any],
        message_type: str = "task",
    ) -> ValidationResult:
        """
        Validate inter-agent communication for security
        """
        if not self.config.agent_communication:
            return self._create_pass_result("Agent communication validation disabled")

        threats: list[ThreatDetection] = []

        # Extract and validate message content
        message_str = json.dumps(message)

        # Check for privilege escalation attempts
        if "sudo" in message_str or "admin" in message_str or "root" in message_str:
            threats.append(
                ThreatDetection(
                    threat_type=ThreatType.PRIVILEGE_ESCALATION,
                    severity=RiskLevel.MEDIUM,
                    description="Potential privilege escalation in agent message",
                    mitigation="Review agent permissions",
                )
            )

        # Validate message content
        content_result = await self.validate_content(
            message_str,
            ContentType.DATA,
            ValidationContext(source=source_agent),
            self.config.security_level,
        )

        threats.extend(content_result.threats)

        risk_level = self._calculate_risk_level(threats)

        return ValidationResult(
            is_valid=risk_level != RiskLevel.CRITICAL,
            risk_level=risk_level,
            threats=threats,
            recommendations=content_result.recommendations,
            metadata={
                "source_agent": source_agent,
                "target_agent": target_agent,
                "message_type": message_type,
            },
            timestamp=datetime.now(),
        )

    def get_configuration(self) -> SecurityConfiguration:
        """Get current security configuration"""
        return self.config

    async def update_configuration(self, config: SecurityConfiguration) -> bool:
        """Update security configuration"""
        self.config = config
        logger.info(f"Configuration updated: {config.security_level}")
        return True

    def register_hook(self, registration) -> str:
        """Register a security hook"""
        # Hook registration would be implemented here
        # For now, return a placeholder ID
        return f"hook_{datetime.now().timestamp()}"

    def unregister_hook(self, hook_id: str) -> bool:
        """Unregister a security hook"""
        # Hook unregistration would be implemented here
        return True

    async def health_check(self) -> dict[str, Any]:
        """Perform health check and return status"""
        return {
            "status": "healthy",
            "enabled": self.config.enabled,
            "security_level": self.config.security_level.value,
            "patterns_loaded": len(self.patterns.patterns),
            "whitelist_size": len(self.whitelist),
            "blacklist_size": len(self.blacklist),
            "events_logged": len(self._security_events),
        }

    # Helper methods

    def _should_flag_pattern(self, pattern: AttackPattern, security_level: SecurityLevel) -> bool:
        """Determine if a pattern should be flagged based on security level"""
        severity_levels = {
            "low": 1,
            "medium": 2,
            "high": 3,
            "critical": 4,
        }

        security_thresholds = {
            SecurityLevel.LOW: 3,  # Only flag high and critical
            SecurityLevel.MEDIUM: 2,  # Flag medium and above
            SecurityLevel.HIGH: 1,  # Flag all patterns
            SecurityLevel.STRICT: 1,  # Flag all patterns
        }

        pattern_level = severity_levels.get(pattern.severity, 0)
        threshold = security_thresholds.get(security_level, 2)

        return pattern_level >= threshold

    def _pattern_to_threat(self, pattern: AttackPattern, content: str) -> ThreatDetection:
        """Convert attack pattern to threat detection"""
        threat_type_map = {
            PatternCategory.PROMPT_OVERRIDE: ThreatType.INJECTION,
            PatternCategory.INSTRUCTION_INJECTION: ThreatType.INJECTION,
            PatternCategory.CONTEXT_MANIPULATION: ThreatType.INJECTION,
            PatternCategory.DATA_EXFILTRATION: ThreatType.DATA_EXFILTRATION,
            PatternCategory.SYSTEM_ESCAPE: ThreatType.PRIVILEGE_ESCALATION,
            PatternCategory.ROLE_HIJACKING: ThreatType.SOCIAL_ENGINEERING,
            PatternCategory.ENCODING_BYPASS: ThreatType.INJECTION,
            PatternCategory.CHAIN_ATTACKS: ThreatType.INJECTION,
        }

        severity_map = {
            "low": RiskLevel.LOW,
            "medium": RiskLevel.MEDIUM,
            "high": RiskLevel.HIGH,
            "critical": RiskLevel.CRITICAL,
        }

        # Find match location
        match = pattern.pattern.search(content)
        location = None
        if match:
            location = {
                "start": match.start(),
                "end": match.end(),
            }

        return ThreatDetection(
            threat_type=threat_type_map.get(pattern.category, ThreatType.INJECTION),
            severity=severity_map.get(pattern.severity, RiskLevel.MEDIUM),
            description=f"{pattern.name}: {pattern.description}",
            location=location,
            mitigation=pattern.mitigation,
        )

    def _calculate_risk_level(self, threats: list[ThreatDetection]) -> RiskLevel:
        """Calculate overall risk level from threats"""
        if not threats:
            return RiskLevel.NONE

        # Get highest severity
        severities = [threat.severity for threat in threats]

        if RiskLevel.CRITICAL in severities:
            return RiskLevel.CRITICAL
        if RiskLevel.HIGH in severities:
            return RiskLevel.HIGH
        if RiskLevel.MEDIUM in severities:
            return RiskLevel.MEDIUM
        if RiskLevel.LOW in severities:
            return RiskLevel.LOW
        return RiskLevel.NONE

    def _generate_recommendations(
        self, threats: list[ThreatDetection], security_level: SecurityLevel
    ) -> list[str]:
        """Generate security recommendations based on threats"""
        recommendations = []

        if not threats:
            recommendations.append("Content appears safe for processing")
            return recommendations

        # Group threats by type
        threat_types = set(threat.threat_type for threat in threats)

        if ThreatType.INJECTION in threat_types:
            recommendations.append("Sanitize input to remove injection attempts")
            recommendations.append("Consider using parameterized queries or templates")

        if ThreatType.PRIVILEGE_ESCALATION in threat_types:
            recommendations.append("Review and restrict privilege requirements")
            recommendations.append("Implement least privilege principle")

        if ThreatType.DATA_EXFILTRATION in threat_types:
            recommendations.append("Block access to sensitive data")
            recommendations.append("Implement data access controls")

        if ThreatType.MALICIOUS_CODE in threat_types:
            recommendations.append("Block code execution immediately")
            recommendations.append("Quarantine suspicious content")

        if security_level == SecurityLevel.STRICT:
            recommendations.append("Consider manual review before processing")

        return recommendations

    def _log_security_event(
        self,
        content_type: ContentType,
        threats: list[ThreatDetection],
        context: ValidationContext | None,
    ):
        """Log security event for audit"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "content_type": content_type.value,
            "threat_count": len(threats),
            "threats": [
                {
                    "type": threat.threat_type.value,
                    "severity": threat.severity.value,
                    "description": threat.description,
                }
                for threat in threats
            ],
            "context": {
                "source": context.source if context else "unknown",
                "session_id": context.session_id if context else None,
            }
            if context
            else None,
        }

        self._security_events.append(event)

        if self.config.logging_enabled:
            logger.warning(f"Security event: {json.dumps(event)}")

    def _create_pass_result(self, reason: str) -> ValidationResult:
        """Create a passing validation result"""
        return ValidationResult(
            is_valid=True,
            risk_level=RiskLevel.NONE,
            threats=[],
            recommendations=[reason],
            metadata={"reason": reason},
            timestamp=datetime.now(),
        )


class WebFetchXPIADefender(XPIADefender):
    """
    Specialized XPIA Defender for WebFetch tool

    Adds URL and prompt validation specific to WebFetch operations.
    """

    async def validate_webfetch_request(
        self, url: str, prompt: str, context: ValidationContext | None = None
    ) -> ValidationResult:
        """
        Validate WebFetch request (URL + prompt)
        """
        threats: list[ThreatDetection] = []

        # Validate URL
        url_threats = await self._validate_url(url)
        threats.extend(url_threats)

        # Validate prompt
        prompt_result = await self.validate_content(
            prompt, ContentType.USER_INPUT, context, self.config.security_level
        )
        threats.extend(prompt_result.threats)

        # Check for combined attacks (URL + prompt)
        combined_threats = self._check_combined_attacks(url, prompt)
        threats.extend(combined_threats)

        risk_level = self._calculate_risk_level(threats)

        return ValidationResult(
            is_valid=risk_level not in [RiskLevel.HIGH, RiskLevel.CRITICAL],
            risk_level=risk_level,
            threats=threats,
            recommendations=self._generate_webfetch_recommendations(threats, url),
            metadata={
                "url": url,
                "prompt_length": len(prompt),
                "domain": urlparse(url).netloc,
            },
            timestamp=datetime.now(),
        )

    async def _validate_url(self, url: str) -> list[ThreatDetection]:
        """Validate URL for security threats"""
        threats = []

        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            path = parsed.path.lower()

            # Check blacklist
            if domain in self.blacklist:
                threats.append(
                    ThreatDetection(
                        threat_type=ThreatType.MALICIOUS_CODE,
                        severity=RiskLevel.CRITICAL,
                        description=f"Domain {domain} is blacklisted",
                        mitigation="Block request immediately",
                    )
                )

            # Check for malicious keywords in URL path
            malicious_keywords = [
                "malware",
                "payload",
                "exploit",
                "backdoor",
                "trojan",
                "virus",
                "ransomware",
            ]
            for keyword in malicious_keywords:
                if keyword in path:
                    threats.append(
                        ThreatDetection(
                            threat_type=ThreatType.MALICIOUS_CODE,
                            severity=RiskLevel.CRITICAL,
                            description=f"URL path contains malicious keyword: {keyword}",
                            mitigation="Block request immediately",
                        )
                    )

            # Check suspicious domain patterns
            if URLPatterns.is_suspicious_domain(domain):
                threats.append(
                    ThreatDetection(
                        threat_type=ThreatType.DATA_EXFILTRATION,
                        severity=RiskLevel.HIGH,
                        description=f"Suspicious domain pattern: {domain}",
                        mitigation="Verify domain legitimacy",
                    )
                )

            # Check suspicious parameters
            if URLPatterns.has_suspicious_params(url):
                threats.append(
                    ThreatDetection(
                        threat_type=ThreatType.INJECTION,
                        severity=RiskLevel.HIGH,
                        description="URL contains suspicious parameters",
                        mitigation="Sanitize URL parameters",
                    )
                )

            # Check for local/private addresses including AWS metadata
            import ipaddress

            is_private = False
            try:
                ip = ipaddress.ip_address(domain)
                is_private = ip.is_private or ip.is_loopback or ip.is_link_local
            except ValueError:
                # Not an IP, check domain names
                is_private = domain in ["localhost", "0.0.0.0", "::1"]

            # Explicitly block AWS metadata service
            if domain == "169.254.169.254":
                threats.append(
                    ThreatDetection(
                        threat_type=ThreatType.PRIVILEGE_ESCALATION,
                        severity=RiskLevel.CRITICAL,
                        description="Blocked AWS metadata service access",
                        mitigation="AWS metadata access not allowed",
                    )
                )
            elif is_private:
                threats.append(
                    ThreatDetection(
                        threat_type=ThreatType.PRIVILEGE_ESCALATION,
                        severity=RiskLevel.HIGH,
                        description="URL points to local/private address",
                        mitigation="Block access to local resources",
                    )
                )

        except Exception as e:
            threats.append(
                ThreatDetection(
                    threat_type=ThreatType.MALICIOUS_CODE,
                    severity=RiskLevel.MEDIUM,
                    description=f"Invalid URL format: {e!s}",
                    mitigation="Validate URL format",
                )
            )

        return threats

    def _check_combined_attacks(self, url: str, prompt: str) -> list[ThreatDetection]:
        """Check for attacks that combine URL and prompt"""
        threats = []

        # Check if prompt references the URL in suspicious ways
        if "ignore" in prompt.lower() and url in prompt:
            threats.append(
                ThreatDetection(
                    threat_type=ThreatType.INJECTION,
                    severity=RiskLevel.HIGH,
                    description="Prompt attempts to override URL validation",
                    mitigation="Process URL and prompt separately",
                )
            )

        # Check for exfiltration attempts
        if ("send" in prompt.lower() or "post" in prompt.lower()) and (
            "data" in prompt.lower() or "information" in prompt.lower()
        ):
            threats.append(
                ThreatDetection(
                    threat_type=ThreatType.DATA_EXFILTRATION,
                    severity=RiskLevel.HIGH,
                    description="Potential data exfiltration attempt",
                    mitigation="Block data transmission",
                )
            )

        return threats

    def _generate_webfetch_recommendations(
        self, threats: list[ThreatDetection], url: str
    ) -> list[str]:
        """Generate WebFetch-specific recommendations"""
        recommendations = self._generate_recommendations(threats, self.config.security_level)

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        if domain not in self.whitelist and not threats:
            recommendations.append(f"Consider adding {domain} to whitelist if trusted")

        if threats:
            recommendations.append("Consider fetching from trusted sources only")
            recommendations.append("Validate content after fetch before processing")

        return recommendations
