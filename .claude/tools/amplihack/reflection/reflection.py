"""Simple AI-powered reflection system with user visibility.

Analyzes session logs and creates GitHub issues for improvements.
Shows the user what's happening during reflection analysis.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

try:
    from .display import (
        show_analysis_complete,
        show_analysis_start,
        show_automation_status,
        show_error,
        show_issue_created,
        show_pattern_found,
    )
except ImportError:
    # Fallback to absolute import for direct execution
    from display import (
        show_analysis_complete,
        show_analysis_start,
        show_automation_status,
        show_error,
        show_issue_created,
        show_pattern_found,
    )


# Define fallback types and functions
class FakeResult:
    def __init__(self):
        self.is_duplicate = False
        self.similar_issues = []
        self.confidence = 0.0
        self.reason = "Duplicate detection not available"


def fallback_check_duplicate_issue(title, body, pattern_type=None, repository="current"):
    """Fallback - no duplicate detection."""
    return FakeResult()


def fallback_store_new_issue(
    issue_id, title, body, pattern_type=None, priority="medium", repository="current"
):
    """Fallback - no storage."""


# Import semantic duplicate detection system
try:
    # Try relative import first
    from .semantic_duplicate_detector import (
        DuplicateDetectionResult,
        check_duplicate_issue,
        store_new_issue,
    )

    DUPLICATE_DETECTION_AVAILABLE = True
except ImportError:
    try:
        # Try absolute import as fallback
        import semantic_duplicate_detector

        DuplicateDetectionResult = semantic_duplicate_detector.DuplicateDetectionResult
        check_duplicate_issue = semantic_duplicate_detector.check_duplicate_issue
        store_new_issue = semantic_duplicate_detector.store_new_issue
        DUPLICATE_DETECTION_AVAILABLE = True
    except ImportError:
        # Fallback if semantic duplicate detection is not available
        DUPLICATE_DETECTION_AVAILABLE = False
        check_duplicate_issue = fallback_check_duplicate_issue
        store_new_issue = fallback_store_new_issue
        DuplicateDetectionResult = FakeResult


# Import security utilities
try:
    from .security import (
        create_safe_preview,
        filter_pattern_suggestion,
        sanitize_content,
        sanitize_messages,
    )
except ImportError:
    # Fallback security functions if security module not available
    def sanitize_messages(messages: List[Dict]) -> List[Dict]:
        """Fallback sanitizer."""
        return [
            {
                "content": str(msg.get("content", ""))[:100] + "..."
                if len(str(msg.get("content", ""))) > 100
                else str(msg.get("content", ""))
            }
            for msg in messages[:10]
        ]

    def sanitize_content(content: str, max_length: int = 200) -> str:
        """Fallback content sanitizer."""
        return content[:max_length] + "..." if len(content) > max_length else content

    def filter_pattern_suggestion(suggestion: str) -> str:
        """Fallback suggestion filter."""
        return suggestion[:100] + "..." if len(suggestion) > 100 else suggestion

    def create_safe_preview(content: str, context: str = "") -> str:
        """Fallback preview creator."""
        safe_content = content[:50] + "..." if len(content) > 50 else content
        return f"{context}: {safe_content}" if context else safe_content


def is_reflection_enabled() -> bool:
    """Check if reflection is enabled via environment variable."""
    return os.environ.get("REFLECTION_ENABLED", "true").lower() not in ["false", "0", "no", "off"]


def analyze_session_patterns(messages: List[Dict]) -> List[Dict]:
    """Analyze session for improvement patterns with specific error analysis."""
    import time

    # Initialize variables
    CONTEXTUAL_ANALYSIS_AVAILABLE = False
    ContextualErrorAnalyzer = None

    try:
        from .contextual_error_analyzer import ContextualErrorAnalyzer

        CONTEXTUAL_ANALYSIS_AVAILABLE = True
    except ImportError:
        # Try alternative import paths
        try:
            from contextual_error_analyzer import ContextualErrorAnalyzer

            CONTEXTUAL_ANALYSIS_AVAILABLE = True
        except ImportError:
            # Contextual analysis not available, fall back to basic detection
            CONTEXTUAL_ANALYSIS_AVAILABLE = False
            ContextualErrorAnalyzer = None

    start_time = time.time()
    patterns = []

    # SECURITY: Sanitize messages before processing
    safe_messages = sanitize_messages(messages)

    # Build sanitized content for pattern analysis (memory-efficient)
    # Use generator to avoid creating intermediate list
    content_parts = (
        str(msg["content"])
        for msg in safe_messages
        if isinstance(msg, dict) and "content" in msg and msg["content"]
    )

    # Join efficiently with size limit for performance
    content = " ".join(content_parts)[:10000]  # Limit content size for performance

    # Contextual Error Pattern Detection
    if CONTEXTUAL_ANALYSIS_AVAILABLE and ContextualErrorAnalyzer is not None:
        try:
            # Create analyzer instance (no caching to avoid function attribute issues)
            analyzer = ContextualErrorAnalyzer()
            top_suggestion = analyzer.get_top_suggestion(content)

            if top_suggestion:
                patterns.append(top_suggestion)

        except Exception as e:
            # Fallback to basic error detection if contextual analysis fails
            print(f"Contextual error analysis failed: {e}, falling back to basic detection")
            CONTEXTUAL_ANALYSIS_AVAILABLE = False

    # Fallback for basic error detection
    if not CONTEXTUAL_ANALYSIS_AVAILABLE:
        content_lower = content.lower()
        if "error" in content_lower or "failed" in content_lower:
            patterns.append(
                {
                    "type": "error_handling",
                    "priority": "high",
                    "suggestion": "Improve error handling based on session failures",
                }
            )

    # Look for workflow issues (using sanitized content)
    content_lower = content.lower()
    if "try again" in content_lower or "repeat" in content_lower:
        patterns.append(
            {
                "type": "workflow",
                "priority": "medium",
                "suggestion": "Streamline workflow to reduce repetitive actions",
            }
        )

    # Look for automation opportunities (safe count)
    tool_count = content.count("tool_use")
    if tool_count > 10:
        patterns.append(
            {
                "type": "automation",
                "priority": "medium",
                "suggestion": f"Consider automating frequent tool combinations ({tool_count} uses detected)",
            }
        )

    # SECURITY: Filter all suggestions before returning
    for pattern in patterns:
        pattern["suggestion"] = filter_pattern_suggestion(pattern["suggestion"])

    # Performance check - ensure under 5 seconds
    elapsed_time = time.time() - start_time
    if elapsed_time > 5.0:
        print(f"Warning: Enhanced error analysis took {elapsed_time:.2f}s (target: <5s)")

    return patterns


def create_github_issue(pattern: Dict) -> Optional[str]:
    """Create GitHub issue for improvement pattern with duplicate detection.

    Returns issue URL on success, None on failure or skip.
    Gracefully handles missing gh CLI, label errors, and timeouts.
    """
    try:
        # Check if gh CLI is available
        try:
            check_result = subprocess.run(
                ["gh", "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if check_result.returncode != 0:
                print("ℹ️  GitHub CLI (gh) not available - skipping issue creation")
                return None
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"ℹ️  GitHub CLI (gh) not available: {e} - skipping issue creation")
            return None

        # SECURITY: Sanitize all content before creating GitHub issue
        safe_type = sanitize_content(pattern.get("type", "unknown"), max_length=50)
        safe_suggestion = filter_pattern_suggestion(pattern.get("suggestion", ""))
        safe_priority = sanitize_content(pattern.get("priority", "medium"), max_length=20)

        # Truncate title to prevent information disclosure
        title = f"AI-detected {safe_type}: {safe_suggestion[:60]}"

        body = f"""# AI-Detected Improvement Opportunity

**Type**: {safe_type}
**Priority**: {safe_priority}

## Suggestion
{safe_suggestion}

## Next Steps
This improvement was identified by AI analysis. Please review and implement as appropriate.

**Labels**: ai-improvement, {safe_type}, {safe_priority}-priority
"""

        # DUPLICATE DETECTION: Check for similar issues before creating
        if DUPLICATE_DETECTION_AVAILABLE:
            duplicate_result = check_duplicate_issue(title, body, safe_type)

            if duplicate_result.is_duplicate:
                # Handle duplicate case
                similar_count = len(duplicate_result.similar_issues)
                print(f"🔍 Duplicate detected: {duplicate_result.confidence:.1%} similarity")
                print(f"   Found {similar_count} similar issue(s). Skipping creation.")
                print(f"   Reason: {duplicate_result.reason}")

                # Return the most similar existing issue ID if available
                if duplicate_result.similar_issues:
                    existing_issue = duplicate_result.similar_issues[0]
                    existing_id = existing_issue.get("issue_id")
                    if existing_id:
                        print(f"   📋 Existing issue: #{existing_id}")
                        return existing_id

                return None

            if duplicate_result.similar_issues:
                # Found similar but not duplicate - inform user
                similar_count = len(duplicate_result.similar_issues)
                print(
                    f"ℹ️  Found {similar_count} similar issue(s) ({duplicate_result.confidence:.1%} similarity)"
                )
                print("   Creating new issue as similarity is below threshold")

        # Try to create the GitHub issue with labels
        try:
            result = subprocess.run(
                [
                    "gh",
                    "issue",
                    "create",
                    "--title",
                    title,
                    "--body",
                    body,
                    "--label",
                    f"ai-improvement,{safe_type},{safe_priority}-priority",
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,  # Reduced timeout to 10 seconds
            )
        except subprocess.TimeoutExpired:
            print("⚠️  GitHub issue creation timed out (>10s) - skipping")
            return None

        if result.returncode == 0:
            issue_url = result.stdout.strip()
            issue_id = issue_url.split("/")[-1] if issue_url else None

            # Store the new issue in duplicate detection cache
            if DUPLICATE_DETECTION_AVAILABLE and issue_id:
                store_new_issue(issue_id, title, body, safe_type, safe_priority)
                print(f"💾 Cached issue #{issue_id} for future duplicate detection")

            show_issue_created(issue_url, pattern["type"])
            return issue_url  # Return URL instead of just ID for better visibility
        # Check if error is due to labels - try without labels
        error_msg = result.stderr.lower()
        if "label" in error_msg or "not found" in error_msg:
            print("⚠️  Label issue detected - retrying without labels...")
            try:
                result_no_labels = subprocess.run(
                    [
                        "gh",
                        "issue",
                        "create",
                        "--title",
                        title,
                        "--body",
                        body,
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result_no_labels.returncode == 0:
                    issue_url = result_no_labels.stdout.strip()
                    show_issue_created(issue_url, pattern["type"])
                    return issue_url
            except subprocess.TimeoutExpired:
                print("⚠️  GitHub issue creation timed out on retry - skipping")
                return None

        # Generic failure
        print(f"⚠️  Failed to create GitHub issue: {result.stderr[:100]}")
        return None

    except Exception as e:
        # Log but don't crash - reflection should continue even if GitHub fails
        print(f"⚠️  Exception creating GitHub issue: {str(e)[:100]}")
        return None


def delegate_to_ultrathink(issue_number: str, pattern: Dict) -> bool:
    """Delegate issue to UltraThink for automated fix."""
    try:
        task = f"Fix GitHub issue #{issue_number}: {pattern['suggestion']}"

        result = subprocess.run(
            ["claude", "ultrathink", task], check=False, capture_output=True, text=True, timeout=300
        )

        success = result.returncode == 0
        show_automation_status(issue_number, success)
        return success

    except Exception as e:
        show_error(f"Failed to delegate to UltraThink: {e}")
        return False


def process_reflection_analysis(messages: List[Dict]) -> Optional[str]:
    """Main reflection analysis entry point with user visibility."""

    if not is_reflection_enabled():
        print("ℹ️  Reflection analysis disabled (set REFLECTION_ENABLED=true to enable)")
        return None

    try:
        # Validate messages input
        if not messages:
            show_error("No session messages provided for analysis")
            return None

        # Start analysis with user visibility
        show_analysis_start(len(messages))

        # Analyze patterns
        patterns = analyze_session_patterns(messages)

        # Show discovered patterns
        for i, pattern in enumerate(patterns, 1):
            show_pattern_found(pattern["type"], pattern["suggestion"], pattern["priority"])

        # Create issue for highest priority pattern
        issue_number = None
        if patterns:
            top_pattern = max(
                patterns, key=lambda p: {"high": 3, "medium": 2, "low": 1}[p["priority"]]
            )
            issue_number = create_github_issue(top_pattern)

            if issue_number:
                # Try automated fix
                delegate_to_ultrathink(issue_number, top_pattern)

        # Show completion
        show_analysis_complete(len(patterns), 1 if patterns else 0)

        return issue_number if patterns else None

    except Exception as e:
        show_error(f"Reflection analysis failed: {e}")
        return None


def main():
    """CLI interface for testing."""
    if len(sys.argv) != 2:
        print("Usage: python simple_reflection.py <analysis_file.json>")
        sys.exit(1)

    analysis_path = Path(sys.argv[1])

    # Load session data from file
    try:
        if not analysis_path.exists():
            print(f"Error: Analysis file not found: {analysis_path}")
            sys.exit(1)

        with open(analysis_path) as f:
            data = json.load(f)

        # Get messages from data
        messages = data.get("messages", [])
        if not messages and "learnings" in data:
            # Use learnings as fallback
            messages = [{"content": str(data["learnings"])}]

        if not messages:
            print("Error: No session messages found for analysis")
            sys.exit(1)

        result = process_reflection_analysis(messages)

        if result:
            print(f"Issue created: #{result}")
        else:
            print("No issues created")

    except Exception as e:
        print(f"Error processing analysis file: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
