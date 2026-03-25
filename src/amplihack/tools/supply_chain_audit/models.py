# File: src/amplihack/tools/supply_chain_audit/models.py
"""Data models for supply chain audit tool.

Dataclasses for Advisory, IOCSet, Evidence, IOCMatch, WorkflowRun,
RunAnalysis, RepoVerdict, and AuditReport.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

VALID_ATTACK_VECTORS = {"actions", "pypi", "npm", "container"}
VALID_SIGNALS = {"safe", "risk", "compromised", "unknown"}
VALID_VERDICTS = {"SAFE", "COMPROMISED", "INCONCLUSIVE"}
VALID_CONFIDENCE = {"HIGH", "MEDIUM", "LOW"}
VALID_IOC_TYPES = {"domain", "ip", "file_pattern"}
VALID_FOUND_IN = {"run_log", "workflow_file", "lockfile"}


@dataclass
class IOCSet:
    """Indicator-of-compromise patterns for an advisory."""

    domains: list[str] = field(default_factory=list)
    ips: list[str] = field(default_factory=list)
    file_patterns: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        """Return True when all IOC lists are empty."""
        return not self.domains and not self.ips and not self.file_patterns


@dataclass
class Advisory:
    """A known supply chain incident with exposure window and IOCs."""

    id: str
    title: str
    description: str
    attack_vector: str
    exposure_window_start: datetime
    exposure_window_end: datetime
    compromised_versions: list[str]
    package_name: str
    safe_versions: list[str] = field(default_factory=list)
    safe_shas: list[str] = field(default_factory=list)
    iocs: IOCSet = field(default_factory=IOCSet)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("id must not be empty")
        if self.attack_vector not in VALID_ATTACK_VECTORS:
            raise ValueError(
                f"attack_vector must be one of {VALID_ATTACK_VECTORS}, got {self.attack_vector!r}"
            )
        if self.exposure_window_end < self.exposure_window_start:
            raise ValueError("exposure_window end must not be before start")
        if not self.compromised_versions:
            raise ValueError("compromised_versions must not be empty")


@dataclass
class Evidence:
    """A single analysis signal from audit inspection."""

    type: str
    detail: str
    signal: str

    def __post_init__(self) -> None:
        if self.signal not in VALID_SIGNALS:
            raise ValueError(f"signal must be one of {VALID_SIGNALS}, got {self.signal!r}")


@dataclass
class IOCMatch:
    """A found indicator of compromise in logs or files."""

    ioc_type: str
    pattern: str
    found_in: str
    run_id: int | None
    line: str

    def __post_init__(self) -> None:
        if self.ioc_type not in VALID_IOC_TYPES:
            raise ValueError(f"ioc_type must be one of {VALID_IOC_TYPES}, got {self.ioc_type!r}")
        if self.found_in not in VALID_FOUND_IN:
            raise ValueError(f"found_in must be one of {VALID_FOUND_IN}, got {self.found_in!r}")


@dataclass
class WorkflowRun:
    """Metadata for a single GitHub Actions workflow run."""

    run_id: int
    workflow_name: str
    workflow_file: str
    created_at: datetime
    head_sha: str
    status: str
    conclusion: str

    def in_window(self, start: datetime, end: datetime) -> bool:
        """Check if this run falls within an exposure window."""
        return start <= self.created_at <= end


@dataclass
class RunAnalysis:
    """Per-run evidence and IOC matches."""

    run_id: int
    evidence: list[Evidence] = field(default_factory=list)
    ioc_matches: list[IOCMatch] = field(default_factory=list)

    def has_compromised_signal(self) -> bool:
        """Return True if any evidence has a 'compromised' signal."""
        return any(e.signal == "compromised" for e in self.evidence)


@dataclass
class RepoVerdict:
    """Summary verdict for a single repository."""

    repo: str
    verdict: str
    confidence: str
    evidence: list[Evidence]
    workflow_runs_analyzed: int
    ioc_matches: list[IOCMatch]

    def __post_init__(self) -> None:
        if self.verdict not in VALID_VERDICTS:
            raise ValueError(f"verdict must be one of {VALID_VERDICTS}, got {self.verdict!r}")
        if self.confidence not in VALID_CONFIDENCE:
            raise ValueError(
                f"confidence must be one of {VALID_CONFIDENCE}, got {self.confidence!r}"
            )


@dataclass
class AuditReport:
    """Top-level envelope for a complete supply chain audit."""

    advisory_id: str
    advisory_title: str
    scan_timestamp: datetime
    repos_scanned: int
    summary: dict[str, int]
    verdicts: list[RepoVerdict]

    def has_compromised(self) -> bool:
        """Return True if any repo has COMPROMISED verdict."""
        return any(v.verdict == "COMPROMISED" for v in self.verdicts)

    def has_inconclusive(self) -> bool:
        """Return True if any repo has INCONCLUSIVE verdict."""
        return any(v.verdict == "INCONCLUSIVE" for v in self.verdicts)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "advisory_id": self.advisory_id,
            "advisory_title": self.advisory_title,
            "scan_timestamp": self.scan_timestamp.isoformat(),
            "repos_scanned": self.repos_scanned,
            "summary": self.summary,
            "verdicts": [
                {
                    "repo": v.repo,
                    "verdict": v.verdict,
                    "confidence": v.confidence,
                    "workflow_runs_analyzed": v.workflow_runs_analyzed,
                    "evidence": [
                        {
                            "type": e.type,
                            "detail": e.detail,
                            "signal": e.signal,
                        }
                        for e in v.evidence
                    ],
                    "ioc_matches": [
                        {
                            "ioc_type": m.ioc_type,
                            "pattern": m.pattern,
                            "found_in": m.found_in,
                            "run_id": m.run_id,
                            "line": m.line,
                        }
                        for m in v.ioc_matches
                    ],
                }
                for v in self.verdicts
            ],
        }
