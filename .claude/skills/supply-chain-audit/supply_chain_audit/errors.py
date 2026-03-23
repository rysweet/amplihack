# File: supply_chain_audit/errors.py
"""Named error conditions for supply-chain-audit (from contracts.md §Error Conditions)."""


class SupplyChainAuditError(Exception):
    """Base class for all supply-chain-audit errors."""

    error_code: str = "UNKNOWN"

    def __init__(self, message: str, error_code: str | None = None):
        self.error_code = error_code or self.__class__.error_code
        super().__init__(message)


class InvalidScopeError(SupplyChainAuditError):
    """INVALID_SCOPE: unrecognized --scope value rejected before any file reads."""

    error_code = "INVALID_SCOPE"

    def __init__(self, scope: str, valid_scopes: list[str]):
        valid = ", ".join(sorted(valid_scopes))
        message = (
            f"INVALID_SCOPE: '{scope}' is not a recognized scope. "
            f"Valid scopes: all, containers, credentials, dotnet, gha, go, node, python, rust. "
            f"Full list: {valid}"
        )
        super().__init__(message, "INVALID_SCOPE")


class PathTraversalError(SupplyChainAuditError):
    """PATH_TRAVERSAL: path contains ../, null bytes, or an escaping symlink."""

    error_code = "PATH_TRAVERSAL"

    def __init__(self, path: str):
        message = (
            f"PATH_TRAVERSAL: Rejected audit root '{path}' — "
            f"path contains '..' segments, null bytes, or a symlink that escapes the root."
        )
        super().__init__(message, "PATH_TRAVERSAL")


class ToolTimeoutError(SupplyChainAuditError):
    """TOOL_TIMEOUT: external tool exceeded timeout; audit continues in degraded mode."""

    error_code = "TOOL_TIMEOUT"

    def __init__(self, tool: str, timeout: int):
        message = f"TOOL_TIMEOUT: '{tool}' exceeded {timeout}s timeout; running in degraded mode"
        super().__init__(message, "TOOL_TIMEOUT")


class AcceptedRisksOverflowError(SupplyChainAuditError):
    """ACCEPTED_RISKS_OVERFLOW: .supply-chain-accepted-risks.yml exceeds 64KB."""

    error_code = "ACCEPTED_RISKS_OVERFLOW"

    def __init__(self, size: int):
        message = (
            f"ACCEPTED_RISKS_OVERFLOW: .supply-chain-accepted-risks.yml is {size:,} bytes "
            f"(max 65,536). Please split the file by year or archive resolved entries "
            f"to a separate archive file."
        )
        super().__init__(message, "ACCEPTED_RISKS_OVERFLOW")


class XpiaEscalationError(SupplyChainAuditError):
    """XPIA_ESCALATION: prompt injection attempt detected in scanned content."""

    error_code = "XPIA_ESCALATION"

    def __init__(self, file: str):
        # Do NOT include scanned content in the message — XPIA safety invariant
        message = (
            f"XPIA_ESCALATION: Possible prompt injection markers detected in scanned file "
            f"'{file}'. Audit aborted. Escalate to xpia-defense skill for investigation."
        )
        super().__init__(message, "XPIA_ESCALATION")
