"""
XPIA Configuration Management

Centralized configuration for XPIA defense system with
environment variable support and defaults.
"""

import os

# Import from specifications
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .xpia_defense_interface import RiskLevel, SecurityConfiguration, SecurityLevel


@dataclass
class XPIAConfig:
    """
    Complete XPIA configuration with environment variable support
    """

    # Core settings
    enabled: bool = field(
        default_factory=lambda: os.getenv("XPIA_ENABLED", "true").lower() != "false"
    )
    security_level: str = field(
        default_factory=lambda: os.getenv("XPIA_SECURITY_LEVEL", "MODERATE")
    )
    verbose_feedback: bool = field(
        default_factory=lambda: os.getenv("XPIA_VERBOSE_FEEDBACK", "false").lower() == "true"
    )

    # Blocking thresholds
    block_on_high_risk: bool = field(
        default_factory=lambda: os.getenv("XPIA_BLOCK_HIGH_RISK", "true").lower() == "true"
    )
    block_on_critical: bool = field(
        default_factory=lambda: os.getenv("XPIA_BLOCK_CRITICAL", "true").lower() == "true"
    )

    # Feature flags
    validate_webfetch: bool = field(
        default_factory=lambda: os.getenv("XPIA_VALIDATE_WEBFETCH", "true").lower() == "true"
    )
    validate_bash: bool = field(
        default_factory=lambda: os.getenv("XPIA_VALIDATE_BASH", "true").lower() == "true"
    )
    validate_agents: bool = field(
        default_factory=lambda: os.getenv("XPIA_VALIDATE_AGENTS", "true").lower() == "true"
    )

    # Logging
    log_security_events: bool = field(
        default_factory=lambda: os.getenv("XPIA_LOG_EVENTS", "true").lower() == "true"
    )
    log_file: Optional[str] = field(default_factory=lambda: os.getenv("XPIA_LOG_FILE"))

    # Domain lists
    whitelist_domains: List[str] = field(default_factory=list)
    blacklist_domains: List[str] = field(default_factory=list)
    whitelist_file: Optional[str] = field(default_factory=lambda: os.getenv("XPIA_WHITELIST_FILE"))
    blacklist_file: Optional[str] = field(default_factory=lambda: os.getenv("XPIA_BLACKLIST_FILE"))

    # Limits
    max_prompt_length: int = field(
        default_factory=lambda: int(os.getenv("XPIA_MAX_PROMPT_LENGTH", "10000"))
    )
    max_url_length: int = field(
        default_factory=lambda: int(os.getenv("XPIA_MAX_URL_LENGTH", "2048"))
    )

    def __post_init__(self):
        """Load additional configuration after initialization"""
        self._load_domain_lists()
        self._validate_config()

    def _load_domain_lists(self):
        """Load domain whitelist and blacklist from files and environment"""
        # Load whitelist from environment
        env_whitelist = os.getenv("XPIA_WHITELIST_DOMAINS", "")
        if env_whitelist:
            self.whitelist_domains.extend(
                domain.strip() for domain in env_whitelist.split(",") if domain.strip()
            )

        # Load whitelist from file
        if self.whitelist_file and Path(self.whitelist_file).exists():
            with open(self.whitelist_file) as f:
                self.whitelist_domains.extend(
                    line.strip() for line in f if line.strip() and not line.startswith("#")
                )

        # Load blacklist from environment
        env_blacklist = os.getenv("XPIA_BLACKLIST_DOMAINS", "")
        if env_blacklist:
            self.blacklist_domains.extend(
                domain.strip() for domain in env_blacklist.split(",") if domain.strip()
            )

        # Load blacklist from file
        if self.blacklist_file and Path(self.blacklist_file).exists():
            with open(self.blacklist_file) as f:
                self.blacklist_domains.extend(
                    line.strip() for line in f if line.strip() and not line.startswith("#")
                )

        # Add default safe domains to whitelist
        default_safe_domains = [
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
            "docs.python.org",
            "developer.mozilla.org",
            "w3.org",
        ]
        self.whitelist_domains.extend(default_safe_domains)

        # Remove duplicates
        self.whitelist_domains = list(set(self.whitelist_domains))
        self.blacklist_domains = list(set(self.blacklist_domains))

    def _validate_config(self):
        """Validate configuration settings"""
        valid_levels = ["STRICT", "HIGH", "MODERATE", "MEDIUM", "LENIENT", "LOW"]
        if self.security_level.upper() not in valid_levels:
            raise ValueError(
                f"Invalid security level: {self.security_level}. Must be one of: {valid_levels}"
            )

        if self.max_prompt_length < 100:
            raise ValueError("Max prompt length must be at least 100 characters")

        if self.max_url_length < 10:
            raise ValueError("Max URL length must be at least 10 characters")

    def to_security_configuration(self) -> SecurityConfiguration:
        """Convert to SecurityConfiguration for interface compatibility"""
        level_map = {
            "STRICT": SecurityLevel.STRICT,
            "HIGH": SecurityLevel.HIGH,
            "MODERATE": SecurityLevel.MEDIUM,
            "MEDIUM": SecurityLevel.MEDIUM,
            "LENIENT": SecurityLevel.LOW,
            "LOW": SecurityLevel.LOW,
        }

        config = SecurityConfiguration()
        config.security_level = level_map[self.security_level.upper()]
        config.enabled = self.enabled
        config.bash_validation = self.validate_bash
        config.agent_communication = self.validate_agents
        config.content_scanning = True
        config.logging_enabled = self.log_security_events

        # Set block thresholds based on settings
        if self.block_on_critical:
            config.block_threshold = RiskLevel.CRITICAL
        elif self.block_on_high_risk:
            config.block_threshold = RiskLevel.HIGH
        else:
            config.block_threshold = RiskLevel.CRITICAL

        return config

    def get_security_level_enum(self) -> SecurityLevel:
        """Get SecurityLevel enum value"""
        level_map = {
            "STRICT": SecurityLevel.STRICT,
            "HIGH": SecurityLevel.HIGH,
            "MODERATE": SecurityLevel.MEDIUM,
            "MEDIUM": SecurityLevel.MEDIUM,
            "LENIENT": SecurityLevel.LOW,
            "LOW": SecurityLevel.LOW,
        }
        return level_map[self.security_level.upper()]

    def should_block_risk_level(self, risk_level: RiskLevel) -> bool:
        """Determine if a risk level should be blocked"""
        if risk_level == RiskLevel.CRITICAL and self.block_on_critical:
            return True
        if risk_level == RiskLevel.HIGH and self.block_on_high_risk:
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "enabled": self.enabled,
            "security_level": self.security_level,
            "verbose_feedback": self.verbose_feedback,
            "block_on_high_risk": self.block_on_high_risk,
            "block_on_critical": self.block_on_critical,
            "validate_webfetch": self.validate_webfetch,
            "validate_bash": self.validate_bash,
            "validate_agents": self.validate_agents,
            "log_security_events": self.log_security_events,
            "log_file": self.log_file,
            "whitelist_domains_count": len(self.whitelist_domains),
            "blacklist_domains_count": len(self.blacklist_domains),
            "max_prompt_length": self.max_prompt_length,
            "max_url_length": self.max_url_length,
        }


# Global configuration instance
_global_config: Optional[XPIAConfig] = None


def get_config() -> XPIAConfig:
    """Get or create global XPIA configuration"""
    global _global_config
    if _global_config is None:
        _global_config = XPIAConfig()
    return _global_config


def reload_config() -> XPIAConfig:
    """Reload configuration from environment"""
    global _global_config
    _global_config = XPIAConfig()
    return _global_config


def set_config(config: XPIAConfig):
    """Set global configuration"""
    global _global_config
    _global_config = config


# Example .env file content
EXAMPLE_ENV_FILE = """
# XPIA Defense Configuration

# Core Settings
XPIA_ENABLED=true
XPIA_SECURITY_LEVEL=MODERATE  # STRICT, HIGH, MODERATE, LENIENT, LOW
XPIA_VERBOSE_FEEDBACK=false

# Blocking Thresholds
XPIA_BLOCK_HIGH_RISK=true
XPIA_BLOCK_CRITICAL=true

# Feature Flags
XPIA_VALIDATE_WEBFETCH=true
XPIA_VALIDATE_BASH=true
XPIA_VALIDATE_AGENTS=true

# Logging
XPIA_LOG_EVENTS=true
XPIA_LOG_FILE=/var/log/xpia/security.log

# Domain Lists (comma-separated)
XPIA_WHITELIST_DOMAINS=example.com,trusted-site.org
XPIA_BLACKLIST_DOMAINS=malware.com,phishing.net

# Domain List Files
XPIA_WHITELIST_FILE=.xpia_whitelist
XPIA_BLACKLIST_FILE=.xpia_blacklist

# Limits
XPIA_MAX_PROMPT_LENGTH=10000
XPIA_MAX_URL_LENGTH=2048
"""


def create_example_env_file(filepath: str = ".env.xpia.example"):
    """Create an example environment file"""
    with open(filepath, "w") as f:
        f.write(EXAMPLE_ENV_FILE)
    return filepath
