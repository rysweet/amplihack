#!/usr/bin/env python3
"""
Delta transcript analyzer for power-steering.

Analyzes new transcript content since the last block to determine if
previous failures have been addressed. Uses simple heuristics as a
fallback when LLM-based analysis is unavailable.

Philosophy:
- Ruthlessly Simple: Single responsibility - delta analysis only
- Fail-Open: Never block users due to bugs
- Zero-BS: No stubs, every function works
- Modular: Self-contained brick with standard library only
- LLM-first, heuristics as fallback

Public API (the "studs"):
    DeltaAnalyzer: Analyzes delta transcript since last block
"""

from collections.abc import Callable

# Import models
try:
    from .power_steering_models import DeltaAnalysisResult, FailureEvidence
except ImportError:
    from power_steering_models import DeltaAnalysisResult, FailureEvidence

# Import constants
try:
    from .power_steering_constants import CLAIM_KEYWORDS
except ImportError:
    from power_steering_constants import CLAIM_KEYWORDS

# Import fallback heuristics
try:
    from .fallback_heuristics import AddressedChecker
except ImportError:
    from fallback_heuristics import AddressedChecker

__all__ = ["DeltaAnalyzer"]


class DeltaAnalyzer:
    """Analyzes new transcript content since last block.

    This is the key component for turn-aware analysis - instead of
    looking at the ENTIRE transcript each time, we look ONLY at
    the delta (new content) and see if it addresses previous failures.

    NOTE: This class provides FALLBACK analysis using simple heuristics.
    The primary path uses LLM-based analysis via claude_power_steering.py:
    - analyze_claims_sync() for completion claim detection
    - analyze_if_addressed_sync() for failure address checking

    This fallback exists for when Claude SDK is unavailable.

    Philosophy:
    - Standard library only (no external deps)
    - Fail-open (errors don't block user)
    - Single responsibility (delta analysis only)
    - LLM-first, heuristics as fallback
    """

    def __init__(self, log: Callable[[str], None] | None = None):
        """Initialize delta analyzer.

        Args:
            log: Optional logging callback
        """
        self.log = log or (lambda msg, level="INFO": None)
        self._fallback_checker = AddressedChecker()

    def analyze_delta(
        self,
        delta_messages: list[dict],
        previous_failures: list[FailureEvidence],
    ) -> DeltaAnalysisResult:
        """Analyze new transcript content against previous failures.

        Args:
            delta_messages: New transcript messages since last block
            previous_failures: List of failures from previous block

        Returns:
            DeltaAnalysisResult with what the delta addresses
        """
        addressed: dict[str, str] = {}
        claims: list[str] = []

        # Extract all text from delta
        delta_text = self._extract_all_text(delta_messages)

        # Detect claims
        claims = self._detect_claims(delta_text)

        # Check if delta addresses each previous failure
        for failure in previous_failures:
            evidence = self._check_if_addressed(
                failure,
                delta_text,
                delta_messages,
            )
            if evidence:
                addressed[failure.consideration_id] = evidence

        # Generate summary
        summary = self._summarize_delta(delta_messages, addressed, claims)

        return DeltaAnalysisResult(
            new_content_addresses_failures=addressed,
            new_claims_detected=claims,
            new_content_summary=summary,
        )

    def _extract_all_text(self, messages: list[dict]) -> str:
        """Extract all text content from messages."""
        texts = []
        for msg in messages:
            content = self._extract_message_content(msg)
            if content:
                texts.append(content)
        return "\n".join(texts)

    def _extract_message_content(self, msg: dict) -> str:
        """Extract text from a single message."""
        content = msg.get("content", msg.get("message", ""))

        if isinstance(content, str):
            return content

        if isinstance(content, dict):
            inner = content.get("content", "")
            if isinstance(inner, str):
                return inner
            if isinstance(inner, list):
                return self._extract_from_blocks(inner)

        if isinstance(content, list):
            return self._extract_from_blocks(content)

        return ""

    def _extract_from_blocks(self, blocks: list) -> str:
        """Extract text from content blocks."""
        texts = []
        for block in blocks:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    texts.append(str(block.get("text", "")))
        return " ".join(texts)

    def _detect_claims(self, text: str) -> list[str]:
        """Detect completion claims in text (FALLBACK - simple keyword matching).

        NOTE: This is a fallback method. The primary path uses LLM-based
        analysis via analyze_claims_sync() in claude_power_steering.py.

        Args:
            text: Text to search

        Returns:
            List of detected claim strings with context
        """
        claims = []
        text_lower = text.lower()

        for keyword in CLAIM_KEYWORDS:
            if keyword in text_lower:
                idx = text_lower.find(keyword)
                start = max(0, idx - 50)
                end = min(len(text), idx + len(keyword) + 50)
                context = text[start:end].strip()
                claim_text = f"...{context}..."
                if claim_text not in claims:
                    claims.append(claim_text)

        if claims:
            self.log(f"[Fallback] Detected {len(claims)} completion claims in delta")

        return claims

    def _check_if_addressed(
        self,
        failure: FailureEvidence,
        delta_text: str,
        delta_messages: list[dict],
    ) -> str | None:
        """Check if the delta addresses a specific failure.

        Uses heuristics based on consideration type to determine if
        the new content shows the concern was addressed.

        Args:
            failure: Previous failure to check
            delta_text: All text from delta
            delta_messages: Delta messages (for structured analysis)

        Returns:
            Evidence string if addressed, None otherwise
        """
        return self._fallback_checker.check_if_addressed(
            consideration_id=failure.consideration_id, delta_text=delta_text
        )

    def _summarize_delta(
        self,
        messages: list[dict],
        addressed: dict[str, str],
        claims: list[str],
    ) -> str:
        """Generate brief summary of delta content.

        Returns:
            Human-readable summary string
        """
        num_messages = len(messages)
        num_addressed = len(addressed)
        num_claims = len(claims)

        parts = [f"{num_messages} new messages"]

        if num_addressed > 0:
            parts.append(f"{num_addressed} concerns addressed")

        if num_claims > 0:
            parts.append(f"{num_claims} completion claims")

        return ", ".join(parts)
