"""
Conversation Analysis Engine for Auto-Mode

Real-time analysis of Claude Code session output using Claude Agent SDK.
Evaluates progress against user objectives and formulates next prompts.
"""

import asyncio
import json
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# Import Claude Agent SDK
try:
    from claude_agent_sdk import query as claude_query  # type: ignore

    CLAUDE_SDK_AVAILABLE = True
except ImportError:
    CLAUDE_SDK_AVAILABLE = False
    claude_query = None  # type: ignore

logger = logging.getLogger(__name__)


class AnalysisType(Enum):
    """Types of analysis to perform"""

    PROGRESS_EVALUATION = "progress_evaluation"
    QUALITY_ASSESSMENT = "quality_assessment"
    NEXT_PROMPT_GENERATION = "next_prompt_generation"
    NEXT_ACTION_PLANNING = "next_action_planning"
    ERROR_DIAGNOSIS = "error_diagnosis"
    OBJECTIVE_ALIGNMENT = "objective_alignment"


@dataclass
class AnalysisRequest:
    """Request for analysis from the engine"""

    id: str
    session_id: str
    analysis_type: AnalysisType
    claude_output: str
    user_objective: str
    context: Dict[str, Any]
    timestamp: datetime


@dataclass
class AnalysisResult:
    """Result from analysis"""

    request_id: str
    session_id: str
    analysis_type: AnalysisType
    confidence: float  # 0.0 to 1.0
    findings: List[str]
    recommendations: List[str]
    next_prompt: Optional[str]
    quality_score: float  # 0.0 to 1.0
    progress_indicators: Dict[str, Any]
    ai_reasoning: str
    metadata: Dict[str, Any]
    timestamp: datetime


@dataclass
class AnalysisConfig:
    """Configuration for analysis engine"""

    batch_size: int = 10
    max_analysis_length: int = 8000  # Max chars of Claude output to analyze
    confidence_threshold: float = 0.6
    enable_caching: bool = True
    cache_ttl_minutes: int = 30
    analysis_timeout_seconds: int = 60


class SDKConnectionError(Exception):
    """Raised when SDK connection fails"""


class AnalysisError(Exception):
    """Raised when analysis fails"""


class PromptInjectionError(Exception):
    """Raised when prompt injection is detected"""


class ConversationAnalysisEngine:
    """
    Real-time analysis engine using Claude Agent SDK.

    Analyzes Claude Code session output to evaluate progress,
    assess quality, and generate next prompts for auto-mode.
    """

    def __init__(self, config: Optional[AnalysisConfig] = None):
        self.config = config or AnalysisConfig()
        self.analysis_cache: Dict[str, AnalysisResult] = {}
        self.analysis_history: List[AnalysisResult] = []

        # Validate SDK is available
        if not CLAUDE_SDK_AVAILABLE:
            raise SDKConnectionError(
                "Claude Agent SDK not available. Install with: pip install claude-agent-sdk"
            )

        logger.info("Claude Agent SDK initialized successfully")

        # Security validation patterns
        self._dangerous_patterns = [
            r"exec\s*\(",
            r"eval\s*\(",
            r"__import__",
            r"subprocess",
            r"os\.system",
            r"file\s*=\s*open",
            r"rm\s+-rf",
            r"DELETE\s+FROM",
            r"DROP\s+TABLE",
            r"<script.*?>",
            r"javascript:",
            r"data:.*base64",
        ]

    async def analyze_conversation(
        self,
        session_id: str,
        claude_output: str,
        user_objective: str,
        analysis_type: AnalysisType,
        context: Optional[Dict[str, Any]] = None,
    ) -> AnalysisResult:
        """
        Analyze Claude Code output for insights and next steps using REAL Claude AI.

        Args:
            session_id: Session identifier
            claude_output: Output from Claude Code to analyze
            user_objective: User's stated objective
            analysis_type: Type of analysis to perform
            context: Additional context for analysis

        Returns:
            Analysis result with findings and recommendations

        Raises:
            SDKConnectionError: If SDK is unavailable
            AnalysisError: If analysis fails
        """
        # Validate inputs for security
        self._validate_prompt_content(claude_output)
        self._validate_prompt_content(user_objective)

        request = AnalysisRequest(
            id=str(uuid.uuid4()),
            session_id=session_id,
            analysis_type=analysis_type,
            claude_output=self._truncate_output(claude_output),
            user_objective=self._sanitize_input(user_objective),
            context=context or {},
            timestamp=datetime.now(),
        )

        try:
            # Check cache first
            cache_key = self._generate_cache_key(request)
            if self.config.enable_caching and cache_key in self.analysis_cache:
                cached_result = self.analysis_cache[cache_key]
                if self._is_cache_valid(cached_result):
                    logger.info(f"Returning cached analysis for {request.id}")
                    return cached_result

            # Perform REAL analysis using Claude Agent SDK
            result = await self._perform_real_sdk_analysis(request)

            # Cache result
            if self.config.enable_caching:
                self.analysis_cache[cache_key] = result

            # Store in history
            self.analysis_history.append(result)

            logger.info(f"Completed analysis {request.id} with confidence {result.confidence}")
            return result

        except Exception as e:
            logger.error(f"Analysis failed for request {request.id}: {e}")
            raise AnalysisError(f"Analysis failed: {e}")

    async def _perform_real_sdk_analysis(self, request: AnalysisRequest) -> AnalysisResult:
        """
        Perform analysis using REAL Claude Agent SDK.

        This sends the analysis prompt to Claude and gets back AI-generated insights.
        NO HEURISTICS. NO TEMPLATES. REAL AI ANALYSIS.
        """
        # Build analysis prompt based on type
        analysis_prompt = self._build_analysis_prompt(request)

        try:
            # Call REAL Claude Agent SDK
            response_text = await self._call_claude_sdk(analysis_prompt)

            # Parse AI response
            result = self._parse_ai_response(request, response_text)

            return result

        except Exception as e:
            raise AnalysisError(f"SDK analysis failed: {e}")

    async def _call_claude_sdk(self, prompt: str) -> str:
        """
        Call REAL Claude Agent SDK to analyze content.

        Uses claude_agent_sdk.query() to send prompt and get AI response.

        Note: Requires Claude Code CLI version 2.0.0 or higher.
        """
        try:
            # Collect all response chunks from Claude
            response_texts = []

            async for message in claude_query(prompt=prompt):  # type: ignore
                # Extract text from Message objects
                # Messages can be SystemMessage, AssistantMessage, ResultMessage, etc.
                # We want the content from AssistantMessage objects
                if (
                    hasattr(message, "__class__")
                    and "AssistantMessage" in message.__class__.__name__
                ):
                    # AssistantMessage has content attribute with TextBlock objects
                    if hasattr(message, "content") and isinstance(message.content, list):
                        for content_block in message.content:
                            if hasattr(content_block, "text"):
                                response_texts.append(content_block.text)
                elif hasattr(message, "result"):
                    # ResultMessage may contain the final result
                    response_texts.append(str(message.result))

            # Combine all text chunks into full response
            full_response = "".join(response_texts)

            if not full_response:
                # Fallback: if no text was extracted, log warning
                logger.warning("No text content extracted from Claude SDK response")
                raise SDKConnectionError("No text content in Claude SDK response")

            logger.info(f"Received Claude SDK response: {len(full_response)} chars")
            return full_response

        except Exception as e:
            logger.error(f"Claude SDK call failed: {e}")

            # Check if error is due to version incompatibility
            error_str = str(e)
            if "unsupported" in error_str.lower() or "version" in error_str.lower():
                raise SDKConnectionError(
                    f"Claude Agent SDK failed due to version incompatibility. "
                    f"Claude Code CLI version 2.0.0+ is required. "
                    f"Error: {e}"
                )
            if "unknown option" in error_str.lower():
                raise SDKConnectionError(
                    f"Claude Agent SDK failed due to CLI incompatibility. "
                    f"Please upgrade Claude Code CLI to version 2.0.0+. "
                    f"Error: {e}"
                )

            raise SDKConnectionError(f"Failed to call Claude Agent SDK: {e}")

    def _build_analysis_prompt(self, request: AnalysisRequest) -> str:
        """Build analysis prompt for Claude AI"""

        # Sanitize inputs
        safe_objective = self._sanitize_input(request.user_objective)
        safe_output = self._sanitize_input(request.claude_output)
        safe_session_id = re.sub(r"[^a-zA-Z0-9\-_]", "", request.session_id)

        base_context = f"""You are analyzing Claude Code session output to evaluate progress toward a user's objective.

User Objective: {safe_objective}

Claude Code Output to Analyze:
{safe_output}

Session ID: {safe_session_id}
Analysis Type: {request.analysis_type.value}

"""

        if request.analysis_type == AnalysisType.PROGRESS_EVALUATION:
            return (
                base_context
                + """Evaluate the progress toward the user's objective. Analyze:
1. What has been accomplished so far?
2. What remains to be done?
3. Are we on the right track?
4. What obstacles or blockers exist?

Provide your analysis in the following JSON format:
{
  "confidence": <float 0.0-1.0>,
  "findings": [<list of key findings>],
  "recommendations": [<list of recommendations>],
  "next_prompt": "<specific next prompt to continue progress>",
  "quality_score": <float 0.0-1.0>,
  "progress_indicators": {
    "completion_percentage": <int 0-100>,
    "blockers_identified": <int>,
    "objectives_met": <int>
  },
  "ai_reasoning": "<your detailed reasoning about the analysis>"
}
"""
            )

        if request.analysis_type == AnalysisType.QUALITY_ASSESSMENT:
            return (
                base_context
                + """Assess the quality of the work done. Consider:
1. Code quality and best practices
2. Completeness of implementation
3. Potential issues or bugs
4. Alignment with objectives

Provide your analysis in JSON format with fields: confidence, findings, recommendations, next_prompt, quality_score, progress_indicators, ai_reasoning.
"""
            )

        if request.analysis_type == AnalysisType.NEXT_ACTION_PLANNING:
            return (
                base_context
                + """Plan the next action to take toward the objective. Consider:
1. What is the most important next step?
2. What blockers need to be addressed?
3. How to maintain momentum?
4. What would provide the most value?

Provide a specific, actionable next prompt for Claude in JSON format with all required fields.
"""
            )

        if request.analysis_type == AnalysisType.ERROR_DIAGNOSIS:
            return (
                base_context
                + """Diagnose any errors or issues in the output. Consider:
1. What went wrong?
2. Root cause analysis
3. How to fix the problem?
4. Prevention strategies

Provide your diagnosis in JSON format with all required fields.
"""
            )

        if request.analysis_type == AnalysisType.OBJECTIVE_ALIGNMENT:
            return (
                base_context
                + """Evaluate alignment with the user's objective. Consider:
1. Is the work moving toward the goal?
2. Are we solving the right problem?
3. Should we adjust course?
4. Are there better approaches?

Provide your evaluation in JSON format with all required fields.
"""
            )

        return (
            base_context
            + """Perform general analysis of the Claude Code output and provide insights in JSON format with all required fields.
"""
        )

    def _parse_ai_response(self, request: AnalysisRequest, response: str) -> AnalysisResult:
        """Parse Claude AI response into structured AnalysisResult"""
        try:
            # Try to extract JSON from response
            # Claude might wrap JSON in markdown code blocks
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON object directly
                json_match = re.search(r"\{.*\}", response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise AnalysisError("No JSON found in Claude response")

            data = json.loads(json_str)

            # Helper to convert qualitative values to floats
            def to_float(value, default=0.5):
                if isinstance(value, (int, float)):
                    return float(value)
                if isinstance(value, str):
                    value_lower = value.lower()
                    # Map qualitative terms to numeric values
                    qualitative_map = {
                        "very high": 0.9,
                        "high": 0.75,
                        "medium": 0.5,
                        "moderate": 0.5,
                        "low": 0.25,
                        "very low": 0.1,
                        "excellent": 0.95,
                        "good": 0.75,
                        "fair": 0.5,
                        "poor": 0.25,
                    }
                    return qualitative_map.get(value_lower, default)
                return default

            return AnalysisResult(
                request_id=request.id,
                session_id=request.session_id,
                analysis_type=request.analysis_type,
                confidence=to_float(data.get("confidence"), 0.5),
                findings=data.get("findings", []),
                recommendations=data.get("recommendations", []),
                next_prompt=data.get("next_prompt"),
                quality_score=to_float(data.get("quality_score"), 0.5),
                progress_indicators=data.get("progress_indicators", {}),
                ai_reasoning=data.get("ai_reasoning", ""),
                metadata=data.get("metadata", {}),
                timestamp=datetime.now(),
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from Claude response: {e}")
            logger.error(f"Response was: {response}")
            raise AnalysisError(f"Failed to parse AI response as JSON: {e}")
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            raise AnalysisError(f"Failed to parse AI response: {e}")

    async def synthesize_response(
        self,
        session_id: str,
        prompt: str,
        user_objective: str,
        context: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Generate Claude's response to a prompt using REAL Claude Agent SDK.

        This sends the prompt to Claude and gets back the AI-generated response.
        NO TEMPLATES. REAL AI RESPONSE.

        Args:
            session_id: Session identifier
            prompt: The prompt to send to Claude
            user_objective: User's stated objective
            context: Additional context

        Returns:
            Dictionary with 'response' key containing Claude's actual response
        """
        try:
            # Validate inputs
            self._validate_prompt_content(prompt)
            self._validate_prompt_content(user_objective)

            # Build full prompt with context
            full_prompt = f"""User Objective: {user_objective}

Context: {json.dumps(context, indent=2)}

{prompt}"""

            # Call REAL Claude Agent SDK
            response_text = await self._call_claude_sdk(full_prompt)

            return {
                "response": response_text,
                "session_id": session_id,
                "prompt_length": len(prompt),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to synthesize response: {e}")
            return None

    def _truncate_output(self, output: str) -> str:
        """Truncate output to maximum analysis length"""
        if len(output) <= self.config.max_analysis_length:
            return output

        # Truncate but try to preserve structure
        truncated = output[: self.config.max_analysis_length]
        last_newline = truncated.rfind("\n")
        if last_newline > self.config.max_analysis_length * 0.8:
            truncated = truncated[:last_newline]

        truncated += "\n[...output truncated for analysis...]"
        return truncated

    def _validate_prompt_content(self, content: str) -> None:
        """Validate content for prompt injection attempts"""
        if not content:
            return

        content_lower = content.lower()

        # Check for dangerous patterns
        for pattern in self._dangerous_patterns:
            if re.search(pattern, content_lower, re.IGNORECASE):
                logger.warning(f"Dangerous pattern detected in prompt content: {pattern}")
                raise PromptInjectionError(f"Potentially dangerous content detected: {pattern}")

        # Check for excessive length (potential DoS)
        if len(content) > 50000:
            raise PromptInjectionError("Content exceeds maximum length")

    def _sanitize_input(self, text: str) -> str:
        """Sanitize user input to prevent injection"""
        if not text:
            return ""

        # Remove or escape potentially dangerous characters
        # Replace control characters
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]", "", text)

        # Escape potential script injection
        text = text.replace("<", "&lt;").replace(">", "&gt;")
        text = text.replace("${", "\\${")
        text = text.replace("#{", "\\#{")

        # Limit length
        if len(text) > 10000:
            text = text[:10000] + "...[truncated for security]"

        return text

    def _generate_cache_key(self, request: AnalysisRequest) -> str:
        """Generate cache key for request"""
        # Create hash of relevant request data
        key_data = {
            "analysis_type": request.analysis_type.value,
            "output_hash": hash(request.claude_output[:1000]),  # Hash first 1000 chars
            "objective_hash": hash(request.user_objective),
        }
        return f"{request.session_id}_{hash(str(key_data))}"

    def _is_cache_valid(self, result: AnalysisResult) -> bool:
        """Check if cached result is still valid"""
        age_minutes = (datetime.now() - result.timestamp).total_seconds() / 60
        return age_minutes < self.config.cache_ttl_minutes

    async def batch_analyze(self, requests: List[AnalysisRequest]) -> List[AnalysisResult]:
        """Analyze multiple requests in batch for efficiency"""
        results = []

        # Process in batches
        for i in range(0, len(requests), self.config.batch_size):
            batch = requests[i : i + self.config.batch_size]
            batch_results = await asyncio.gather(
                *[
                    self.analyze_conversation(
                        req.session_id,
                        req.claude_output,
                        req.user_objective,
                        req.analysis_type,
                        req.context,
                    )
                    for req in batch
                ],
                return_exceptions=True,
            )

            # Filter out exceptions and add successful results
            for result in batch_results:
                if isinstance(result, AnalysisResult):
                    results.append(result)
                else:
                    logger.error(f"Batch analysis error: {result}")

        return results

    def get_analysis_history(
        self,
        session_id: Optional[str] = None,
        analysis_type: Optional[AnalysisType] = None,
        limit: Optional[int] = None,
    ) -> List[AnalysisResult]:
        """Get analysis history with optional filtering"""
        filtered = self.analysis_history

        if session_id:
            filtered = [r for r in filtered if r.session_id == session_id]

        if analysis_type:
            filtered = [r for r in filtered if r.analysis_type == analysis_type]

        # Sort by timestamp, most recent first
        filtered.sort(key=lambda r: r.timestamp, reverse=True)

        if limit:
            filtered = filtered[:limit]

        return filtered

    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get statistics about analysis performance"""
        if not self.analysis_history:
            return {"total_analyses": 0}

        total = len(self.analysis_history)
        avg_confidence = sum(r.confidence for r in self.analysis_history) / total
        avg_quality = sum(r.quality_score for r in self.analysis_history) / total

        type_counts = {}
        for result in self.analysis_history:
            type_name = result.analysis_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        return {
            "total_analyses": total,
            "average_confidence": avg_confidence,
            "average_quality_score": avg_quality,
            "analysis_types": type_counts,
            "cache_hit_rate": len(self.analysis_cache) / total if total > 0 else 0,
        }
