"""Contextual error analyzer using Claude Code SDK for intelligent error analysis.

Replaces simple regex-based pattern matching with LLM-powered contextual understanding
that can identify root causes, dynamic error categories, and specific actionable suggestions.
"""

import asyncio

# Check SDK availability using importlib
import importlib.util
import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional

SDK_AVAILABLE = importlib.util.find_spec("claude_code_sdk") is not None

try:
    from .security import filter_pattern_suggestion, sanitize_content
except ImportError:
    # Fallback for testing or missing security module
    def sanitize_content(content: str, max_length: int = 5000) -> str:
        return content[:max_length] + "..." if len(content) > max_length else content

    def filter_pattern_suggestion(suggestion: str) -> str:
        return suggestion[:200] + "..." if len(suggestion) > 200 else suggestion


@dataclass
class ErrorAnalysis:
    """Comprehensive error analysis result from LLM processing."""

    root_cause: str
    category: str  # Dynamically determined by LLM
    severity: str  # critical/warning/info
    suggestions: List[str]  # Specific, actionable suggestions
    patterns: List[str]  # Identified error patterns
    confidence: float  # 0.0 to 1.0


class ContextualErrorAnalyzer:
    """Intelligent error analyzer using Claude Code SDK for contextual understanding."""

    def __init__(self):
        self.sdk_available = SDK_AVAILABLE
        # LRU cache for efficiency (maxsize=64 for reasonable memory usage)
        self._lru_cache = {}
        self._cache_size_limit = 64

    @lru_cache(maxsize=64)
    def analyze_error_context(self, error_content: str, context: str = "") -> ErrorAnalysis:
        """Analyze error content with contextual understanding.

        Args:
            error_content: Error messages, logs, or failure content
            context: Additional context (session info, environment, etc.)

        Returns:
            ErrorAnalysis with intelligent categorization and suggestions
        """
        # Early validation
        if not error_content or len(error_content.strip()) < 10:
            return self._create_empty_analysis()

        # Sanitize input for security
        safe_content = sanitize_content(error_content, max_length=5000)
        safe_context = sanitize_content(context, max_length=1000) if context else ""

        # Try LLM analysis first, fallback to keyword extraction
        if self.sdk_available:
            try:
                analysis = asyncio.run(self._analyze_with_llm(safe_content, safe_context))
                if analysis:
                    return analysis
            except Exception as e:
                # Log but don't fail - graceful degradation
                print(f"LLM analysis failed, using fallback: {e}")

        # Fallback to keyword-based analysis
        return self._analyze_with_keywords(safe_content, safe_context)

    async def _analyze_with_llm(self, error_content: str, context: str) -> Optional[ErrorAnalysis]:
        """Analyze errors using Claude Code SDK with proper timeout handling."""

        prompt = self._create_analysis_prompt(error_content, context)

        try:
            # Import SDK within function to avoid issues
            from claude_code_sdk import ClaudeCodeOptions, ClaudeSDKClient  # type: ignore

            # Use asyncio.wait_for for timeout handling
            async def _sdk_analysis():
                async with ClaudeSDKClient(
                    options=ClaudeCodeOptions(
                        system_prompt="""You are an expert software debugging assistant. Analyze error content and provide structured analysis in JSON format.

Focus on:
1. Root cause identification (not just symptoms)
2. Appropriate error category
3. Severity assessment
4. Specific, actionable suggestions
5. Pattern recognition

Return ONLY valid JSON with the specified structure.""",
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

                    return self._parse_llm_response(response)

            # Call with timeout
            return await asyncio.wait_for(_sdk_analysis(), timeout=120)

        except asyncio.TimeoutError:
            print("Claude Code SDK timed out after 120 seconds")
            return None
        except Exception as e:
            print(f"Claude Code SDK error: {e}")
            return None

    def _create_analysis_prompt(self, error_content: str, context: str) -> str:
        """Create structured prompt for LLM analysis."""

        return f"""Analyze the following error content and provide structured error analysis.

ERROR CONTENT:
{error_content}

CONTEXT:
{context or "No additional context provided"}

Please provide analysis in this exact JSON format:
{{
    "root_cause": "Clear explanation of the underlying issue",
    "category": "specific_error_category",
    "severity": "critical|warning|info",
    "suggestions": [
        "Specific actionable suggestion 1",
        "Specific actionable suggestion 2",
        "Specific actionable suggestion 3"
    ],
    "patterns": [
        "Error pattern 1",
        "Error pattern 2"
    ],
    "confidence": 0.95
}}

Guidelines:
- root_cause should identify the underlying problem, not just symptoms
- category should be specific (e.g., "dependency_missing", "file_permissions", "api_timeout")
- severity: critical=breaks functionality, warning=degrades performance, info=minor issue
- suggestions must be specific and actionable (not generic advice)
- patterns should identify recurring error signatures
- confidence should reflect certainty in the analysis (0.0-1.0)

Return ONLY the JSON response, no additional text."""

    def _parse_llm_response(self, response: str) -> Optional[ErrorAnalysis]:
        """Parse LLM response and create ErrorAnalysis object."""

        # Handle markdown code blocks
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.endswith("```"):
            response = response[:-3]
        response = response.strip()

        try:
            data = json.loads(response)

            # Validate required fields
            required_fields = [
                "root_cause",
                "category",
                "severity",
                "suggestions",
                "patterns",
                "confidence",
            ]
            if not all(field in data for field in required_fields):
                return None

            # Sanitize suggestions for security
            sanitized_suggestions = [
                filter_pattern_suggestion(suggestion)
                for suggestion in data["suggestions"][:5]  # Limit to 5 suggestions
            ]

            return ErrorAnalysis(
                root_cause=sanitize_content(data["root_cause"], max_length=500),
                category=data["category"][:50],  # Limit category length
                severity=data["severity"]
                if data["severity"] in ["critical", "warning", "info"]
                else "warning",
                suggestions=sanitized_suggestions,
                patterns=[pattern[:200] for pattern in data["patterns"][:3]],  # Limit patterns
                confidence=max(0.0, min(1.0, float(data["confidence"]))),  # Clamp to 0-1
            )

        except (json.JSONDecodeError, KeyError, ValueError, TypeError) as e:
            print(f"Failed to parse LLM response: {e}")
            return None

    def _analyze_with_keywords(self, error_content: str, context: str) -> ErrorAnalysis:
        """Fallback keyword-based analysis when LLM is unavailable."""

        content_lower = error_content.lower()

        # Enhanced keyword patterns for better categorization
        error_patterns = [
            # File system errors
            (
                ["filenotfounderror", "no such file", "file not found"],
                "file_missing",
                "critical",
                "Check file paths and ensure files exist before operations",
            ),
            (
                ["permissionerror", "permission denied", "access denied"],
                "file_permissions",
                "critical",
                "Fix file/directory permissions or run with appropriate access rights",
            ),
            # Network/API errors
            (
                ["connectionerror", "connection refused", "network error"],
                "network_failure",
                "critical",
                "Check network connectivity and service availability",
            ),
            (
                ["timeout", "timed out", "connection timeout"],
                "timeout_error",
                "warning",
                "Increase timeout values or implement retry with exponential backoff",
            ),
            (
                ["http error", "api error", "status code"],
                "api_failure",
                "warning",
                "Add error handling for API responses and implement retry logic",
            ),
            # Python specific
            (
                ["modulenotfounderror", "no module named"],
                "missing_dependency",
                "critical",
                "Install missing Python package or fix import paths",
            ),
            (
                ["syntaxerror", "invalid syntax"],
                "syntax_error",
                "critical",
                "Fix syntax errors using IDE or linter tools",
            ),
            (["typeerror"], "type_error", "warning", "Add type checking and input validation"),
            (
                ["indexerror", "list index out of range"],
                "index_error",
                "warning",
                "Add bounds checking before accessing list/array elements",
            ),
            (
                ["keyerror"],
                "key_error",
                "warning",
                "Use safe dictionary access methods like .get() with defaults",
            ),
            (
                ["valueerror"],
                "value_error",
                "warning",
                "Add input validation and handle edge cases",
            ),
            # Process/execution errors
            (
                ["command not found", "executable not found"],
                "command_missing",
                "critical",
                "Install required command or check PATH environment variable",
            ),
            (
                ["memory error", "out of memory"],
                "memory_error",
                "critical",
                "Optimize memory usage or increase available system memory",
            ),
            (["broken pipe"], "process_error", "warning", "Handle process termination gracefully"),
        ]

        # Find best matching pattern
        best_match = None
        best_score = 0

        for keywords, category, severity, suggestion in error_patterns:
            score = sum(1 for keyword in keywords if keyword in content_lower)
            if score > best_score:
                best_score = score
                best_match = (category, severity, suggestion, keywords[:score])

        if best_match:
            category, severity, suggestion, matched_patterns = best_match
            confidence = min(0.8, 0.4 + (best_score * 0.1))  # Scale confidence with matches

            return ErrorAnalysis(
                root_cause=f"Detected {category.replace('_', ' ')} based on error patterns",
                category=category,
                severity=severity,
                suggestions=[suggestion, "Add comprehensive error logging for better diagnosis"],
                patterns=[f"Pattern: {' OR '.join(matched_patterns)}"],
                confidence=confidence,
            )
        # Generic fallback analysis
        return ErrorAnalysis(
            root_cause="Generic error detected - requires manual investigation",
            category="general_error",
            severity="warning",
            suggestions=[
                "Add detailed error logging to identify specific issue",
                "Review error context and stack traces",
                "Implement proper exception handling",
            ],
            patterns=["Generic error pattern"],
            confidence=0.3,
        )

    def _create_empty_analysis(self) -> ErrorAnalysis:
        """Create empty analysis for invalid input."""
        return ErrorAnalysis(
            root_cause="No error content provided",
            category="no_error",
            severity="info",
            suggestions=["Provide error content for analysis"],
            patterns=[],
            confidence=0.0,
        )

    def get_top_suggestion(self, error_content: str, context: str = "") -> Optional[Dict[str, Any]]:
        """Get the top error suggestion for integration with reflection system.

        Args:
            error_content: Error messages or failure content
            context: Additional context information

        Returns:
            Dictionary with suggestion details or None
        """
        analysis = self.analyze_error_context(error_content, context)

        if not analysis.suggestions:
            return None

        return {
            "type": f"error_{analysis.category}",
            "priority": "high"
            if analysis.severity == "critical"
            else "medium"
            if analysis.severity == "warning"
            else "low",
            "suggestion": analysis.suggestions[0],  # Top suggestion
            "confidence": analysis.confidence,
            "root_cause": analysis.root_cause,
            "all_suggestions": analysis.suggestions,
            "patterns": analysis.patterns,
            "implementation_steps": self._get_implementation_steps(analysis.category),
        }

    def _get_implementation_steps(self, category: str) -> List[str]:
        """Get implementation steps for specific error categories."""

        steps_map = {
            "file_missing": [
                "Use pathlib.Path.exists() or os.path.exists() before file operations",
                "Add try-catch blocks around file I/O operations",
            ],
            "file_permissions": [
                "Check file permissions with os.access() before operations",
                "Use appropriate file modes when opening files",
                "Run with proper user permissions",
            ],
            "network_failure": [
                "Add network connectivity checks before API calls",
                "Implement retry logic with exponential backoff",
                "Add timeout handling for network operations",
            ],
            "timeout_error": [
                "Increase timeout parameters in network calls",
                "Add connection pooling for better reliability",
                "Implement async operations for long-running tasks",
            ],
            "api_failure": [
                "Add HTTP status code checking",
                "Implement proper error response handling",
                "Add request/response logging for debugging",
            ],
            "missing_dependency": [
                "Add missing package to requirements.txt or pyproject.toml",
                "Install package with pip install <package>",
                "Verify virtual environment activation",
            ],
            "syntax_error": [
                "Run code through linter (flake8, pylint, black)",
                "Use IDE with syntax highlighting and error detection",
                "Review recent code changes for syntax issues",
            ],
            "type_error": [
                "Add type hints to function parameters and returns",
                "Validate input types before processing",
                "Use isinstance() checks for runtime type validation",
            ],
            "index_error": [
                "Check list/array length before accessing elements",
                "Use try-catch or conditional checks for safe access",
                "Consider using enumerate() for safer iteration",
            ],
            "key_error": [
                "Use dict.get() with default values instead of direct access",
                "Check key existence with 'key in dict' before access",
                "Consider using defaultdict for automatic defaults",
            ],
            "value_error": [
                "Add input validation before processing",
                "Handle edge cases and invalid input gracefully",
                "Use try-catch for conversion operations",
            ],
            "command_missing": [
                "Install required system package or tool",
                "Check PATH environment variable",
                "Use full path to executable if needed",
            ],
            "memory_error": [
                "Optimize data structures and algorithms",
                "Process data in smaller chunks",
                "Use generators for large datasets",
            ],
            "process_error": [
                "Add proper process cleanup and signal handling",
                "Use context managers for resource management",
                "Handle subprocess termination gracefully",
            ],
        }

        return steps_map.get(
            category,
            [
                "Add comprehensive error handling and logging",
                "Review error context and implement specific fixes",
                "Consider adding retry logic where appropriate",
            ],
        )


# Integration point for reflection.py
def analyze_session_patterns(
    session_content: str, context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Integration point for reflection system to analyze session patterns.

    Args:
        session_content: Full session content to analyze
        context: Additional context (metadata, environment info, etc.)

    Returns:
        Analysis results compatible with reflection system
    """
    analyzer = ContextualErrorAnalyzer()

    # Convert context dict to string for analysis
    context_str = ""
    if context:
        context_str = json.dumps(context, indent=2)

    analysis = analyzer.analyze_error_context(session_content, context_str)

    # Return format compatible with existing reflection system
    return {
        "error_analysis": {
            "root_cause": analysis.root_cause,
            "category": analysis.category,
            "severity": analysis.severity,
            "confidence": analysis.confidence,
            "suggestions": analysis.suggestions,
            "patterns": analysis.patterns,
        },
        "top_suggestion": analyzer.get_top_suggestion(session_content, context_str),
        "sdk_used": analyzer.sdk_available,
        "analysis_method": "llm" if analyzer.sdk_available else "keyword_fallback",
    }
