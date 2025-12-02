"""Semantic duplicate detection using Claude Code SDK.

This module provides intelligent duplicate detection using LLM semantic understanding
rather than simple text matching. It replaces the complex pattern-matching system
with a simpler, more effective semantic approach.

Key Features:
- Uses Claude Code SDK for semantic comparison
- Provides explanations for duplicate decisions
- LRU cache for efficiency
- Graceful fallback to difflib if SDK unavailable
"""

import asyncio
import hashlib
import json
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from typing import Dict, List, Optional


@dataclass
class DuplicateDetectionResult:
    """Result of duplicate detection analysis."""

    is_duplicate: bool
    similar_issues: List[Dict]
    confidence: float  # 0-1 similarity score
    reason: str

    def to_dict(self) -> Dict:
        """Convert to dictionary format."""
        return {
            "is_duplicate": self.is_duplicate,
            "similar_issues": self.similar_issues,
            "confidence": self.confidence,
            "reason": self.reason,
        }


class SemanticDuplicateDetector:
    """Semantic duplicate detector using Claude SDK."""

    def __init__(self):
        """Initialize the detector."""
        self._sdk_available = self._check_sdk_available()
        self._cache = {}  # Simple in-memory cache for session

    def _check_sdk_available(self) -> bool:
        """Check if Claude Code SDK is available."""
        import importlib.util

        return importlib.util.find_spec("claude_code_sdk") is not None

    @lru_cache(maxsize=128)
    def _content_hash(self, content: str) -> str:
        """Generate hash for content caching."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    async def detect_with_llm(
        self, new_content: str, existing_content: str, timeout_seconds: int = 120
    ) -> Optional[Dict]:
        """Use Claude SDK to semantically compare content."""
        if not self._sdk_available:
            return None

        try:
            from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient  # type: ignore

            prompt = f"""Analyze if these two GitHub issues are semantically duplicates.

NEW ISSUE:
{new_content[:1500]}  # Truncate for context window

EXISTING ISSUE:
{existing_content[:1500]}

Respond with JSON containing:
- is_duplicate: boolean (true if semantically the same issue)
- similarity_score: float 0-1 (how similar they are)
- explanation: string (brief explanation of decision)

Consider duplicates if they:
- Address the same bug or feature request
- Have the same root cause
- Would have the same solution

Don't consider duplicates if they:
- Are in different modules/areas
- Have different root causes
- Need different solutions"""

            # Use asyncio.wait_for for timeout handling
            async def _sdk_call():
                async with ClaudeSDKClient(
                    options=ClaudeCodeOptions(
                        system_prompt="You are an expert at identifying duplicate GitHub issues. Respond only with valid JSON.",
                        max_turns=1,
                    )
                ) as client:
                    await client.query(prompt)

                    response = ""
                    async for message in client.receive_response():
                        if hasattr(message, "content"):
                            content = getattr(message, "content", [])
                            if isinstance(content, list):
                                for block in content:
                                    if hasattr(block, "text"):
                                        response += getattr(block, "text", "")

                    # Parse JSON from response
                    if response:
                        # Strip markdown code blocks if present
                        response = response.strip()
                        if response.startswith("```json"):
                            response = response[7:]
                        if response.startswith("```"):
                            response = response[3:]
                        if response.endswith("```"):
                            response = response[:-3]

                        return json.loads(response.strip())
                    return None

            # Call with timeout
            return await asyncio.wait_for(_sdk_call(), timeout=timeout_seconds)

        except asyncio.TimeoutError:
            print(f"Claude SDK timed out after {timeout_seconds} seconds")
        except Exception as e:
            print(f"SDK detection failed: {e}")

        return None

    def fallback_detect(self, new_content: str, existing_content: str) -> Dict:
        """Fallback detection using difflib."""
        # Simple text similarity
        similarity = SequenceMatcher(None, new_content, existing_content).ratio()

        # Consider duplicate if >80% similar
        is_duplicate = similarity > 0.8

        explanation = (
            f"Text similarity: {similarity:.1%}. "
            f"{'High similarity suggests duplicate.' if is_duplicate else 'Different enough to be separate issue.'}"
        )

        return {
            "is_duplicate": is_duplicate,
            "similarity_score": similarity,
            "explanation": explanation,
        }

    async def detect_semantic_duplicate(
        self, title: str, body: str, existing_issues: List[Dict]
    ) -> DuplicateDetectionResult:
        """Main detection method."""
        if not existing_issues:
            return DuplicateDetectionResult(
                is_duplicate=False,
                similar_issues=[],
                confidence=0.0,
                reason="No existing issues to compare",
            )

        new_content = f"{title}\n{body}"
        most_similar_issue = None
        highest_similarity = 0.0
        best_explanation = ""

        for issue in existing_issues:
            existing_content = f"{issue.get('title', '')}\n{issue.get('body', '')}"

            # Try LLM detection first
            result = await self.detect_with_llm(new_content, existing_content)

            # Fallback to simple detection if LLM unavailable
            if result is None:
                result = self.fallback_detect(new_content, existing_content)

            similarity = result.get("similarity_score", 0.0)
            if similarity > highest_similarity:
                highest_similarity = similarity
                most_similar_issue = issue
                best_explanation = result.get("explanation", "")

                # Early exit if clear duplicate found
                if result.get("is_duplicate", False) and similarity > 0.9:
                    break

        # Determine if duplicate based on highest similarity
        is_duplicate = highest_similarity > 0.75  # Threshold for duplicate

        similar_issues = []
        if most_similar_issue:
            similar_issues = [most_similar_issue]

        return DuplicateDetectionResult(
            is_duplicate=is_duplicate,
            similar_issues=similar_issues,
            confidence=highest_similarity,
            reason=best_explanation or f"Similarity: {highest_similarity:.1%}",
        )


# Global detector instance
_detector = SemanticDuplicateDetector()


def check_duplicate_issue(
    title: str, body: str, pattern_type: Optional[str] = None, repository: str = "current"
) -> DuplicateDetectionResult:
    """Check if an issue is a duplicate of existing issues.

    This is the main entry point that matches the existing interface.
    """
    # For now, return empty list of existing issues
    # In production, this would fetch from GitHub API or cache
    existing_issues = []

    # Run async detection in sync context
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            _detector.detect_semantic_duplicate(title, body, existing_issues)
        )
        return result
    except Exception as e:
        # Return safe default on any error
        return DuplicateDetectionResult(
            is_duplicate=False,
            similar_issues=[],
            confidence=0.0,
            reason=f"Detection error: {e!s}",
        )


def store_new_issue(
    issue_id: str,
    title: str,
    body: str,
    pattern_type: Optional[str] = None,
    priority: str = "medium",
    repository: str = "current",
) -> None:
    """Store a new issue for future duplicate detection.

    This maintains interface compatibility but is simplified.
    In production, this would store to a persistent cache.
    """
    # For now, this is a no-op as we don't maintain persistent storage
    # Could be extended to store in a file or database


def get_performance_stats() -> Dict:
    """Get performance statistics for the detector."""
    return {
        "sdk_available": _detector._sdk_available,
        "cache_size": len(_detector._cache),
        "method": "semantic" if _detector._sdk_available else "fallback",
    }


# Maintain compatibility with existing interface
__all__ = [
    "DuplicateDetectionResult",
    "check_duplicate_issue",
    "get_performance_stats",
    "store_new_issue",
]
