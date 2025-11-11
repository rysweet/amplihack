"""
Natural language prompt parser for Agent Bundle Generator.

Uses simplified NLP techniques to parse and understand agent requirements from
natural language descriptions. Can be enhanced with spaCy or other NLP libraries later.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from .exceptions import ParsingError
from .models import ParsedPrompt

logger = logging.getLogger(__name__)


class PromptParser:
    """
    Parse natural language prompts to extract agent requirements.

    Uses rule-based NLP with pattern matching for initial implementation.
    Can be enhanced with spaCy, transformers, or other NLP libraries.
    """

    # Common action verbs for agent creation
    ACTION_VERBS = {
        "create",
        "build",
        "generate",
        "make",
        "develop",
        "design",
        "implement",
        "construct",
        "produce",
        "establish",
        "set up",
    }

    # Agent type indicators
    AGENT_KEYWORDS = {
        "agent",
        "assistant",
        "bot",
        "system",
        "service",
        "handler",
        "processor",
        "analyzer",
        "monitor",
        "validator",
        "scanner",
    }

    # Capability indicators
    CAPABILITY_VERBS = {
        "analyze",
        "process",
        "validate",
        "scan",
        "monitor",
        "track",
        "transform",
        "convert",
        "check",
        "verify",
        "audit",
        "review",
        "generate",
        "create",
        "produce",
        "detect",
        "identify",
        "extract",
    }

    # Complexity indicators
    COMPLEXITY_INDICATORS = {
        "simple": ["simple", "basic", "minimal", "straightforward", "quick"],
        "standard": ["standard", "normal", "typical", "regular", "moderate"],
        "advanced": ["advanced", "complex", "comprehensive", "sophisticated", "detailed"],
    }

    def __init__(self, enable_advanced_nlp: bool = False):
        """
        Initialize the prompt parser.

        Args:
            enable_advanced_nlp: Whether to use advanced NLP libraries (future enhancement)
        """
        self.enable_advanced_nlp = enable_advanced_nlp
        self._nlp = None

        if enable_advanced_nlp:
            try:
                import spacy

                self._nlp = spacy.load("en_core_web_sm")
            except (ImportError, OSError) as e:
                logger.warning(f"spaCy not available ({e}), falling back to rule-based parsing")
                self.enable_advanced_nlp = False

    def parse(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> ParsedPrompt:
        """
        Parse a natural language prompt.

        Args:
            prompt: Natural language description of agents
            context: Optional context (existing agents, project type, etc.)

        Returns:
            ParsedPrompt with extracted information

        Raises:
            ParsingError: If prompt cannot be parsed
        """
        if not prompt or not prompt.strip():
            raise ParsingError("Empty prompt provided")

        # Clean and normalize prompt
        cleaned_prompt = self._clean_prompt(prompt)

        # Extract components
        sentences = self._extract_sentences(cleaned_prompt)
        tokens = self._tokenize(cleaned_prompt)
        key_phrases = self._extract_key_phrases(cleaned_prompt, tokens)
        entities = self._extract_entities(cleaned_prompt, tokens)

        # Calculate confidence based on how well we understood the prompt
        confidence = self._calculate_confidence(tokens, key_phrases, entities)

        # Add context metadata
        metadata = {
            "original_length": len(prompt),
            "sentence_count": len(sentences),
            "token_count": len(tokens),
            "has_agent_keywords": any(kw in tokens for kw in self.AGENT_KEYWORDS),
            "has_action_verbs": any(verb in tokens for verb in self.ACTION_VERBS),
        }

        if context:
            metadata["context"] = context

        return ParsedPrompt(
            raw_prompt=prompt,
            tokens=tokens,
            sentences=sentences,
            key_phrases=key_phrases,
            entities=entities,
            confidence=confidence,
            metadata=metadata,
        )

    def extract_requirements(
        self, text: str, hints: Optional[List[str]] = None
    ) -> Dict[str, List[str]]:
        """
        Extract functional, technical, and constraint requirements.

        Args:
            text: Text to extract requirements from
            hints: Optional hints for extraction

        Returns:
            Dictionary with functional, technical, and constraints lists
        """
        requirements = {"functional": [], "technical": [], "constraints": []}

        # Split into lines/sentences
        lines = text.replace(". ", ".\n").split("\n")

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Functional requirements (what the agent should do)
            if any(verb in line.lower() for verb in self.CAPABILITY_VERBS):
                requirements["functional"].append(line)

            # Technical requirements (how it should work)
            elif any(
                keyword in line.lower()
                for keyword in ["performance", "speed", "memory", "api", "format", "protocol"]
            ):
                requirements["technical"].append(line)

            # Constraints (limitations and boundaries)
            elif any(
                keyword in line.lower()
                for keyword in ["must", "should", "cannot", "limit", "maximum", "minimum"]
            ):
                requirements["constraints"].append(line)

            # Use hints if provided
            elif hints:
                for hint in hints:
                    if hint.lower() in line.lower():
                        requirements["functional"].append(line)
                        break

        return requirements

    def _clean_prompt(self, prompt: str) -> str:
        """Clean and normalize the prompt text."""
        # Remove extra whitespace
        cleaned = re.sub(r"\s+", " ", prompt)

        # Standardize punctuation
        cleaned = re.sub(r"([.!?])\s*", r"\1 ", cleaned)

        # Remove special characters but keep meaningful punctuation
        cleaned = re.sub(r"[^\w\s.!?,;:\-]", "", cleaned)

        return cleaned.strip()

    def _extract_sentences(self, text: str) -> List[str]:
        """Extract sentences from text."""
        # Simple sentence splitting (can be improved with NLTK or spaCy)
        sentences = re.split(r"[.!?]+", text)
        return [s.strip() for s in sentences if s.strip()]

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        # Convert to lowercase and split
        tokens = text.lower().split()

        # Remove punctuation from tokens
        tokens = [re.sub(r"[^\w\-]", "", token) for token in tokens]

        # Remove empty tokens
        return [token for token in tokens if token]

    def _extract_key_phrases(self, text: str, tokens: List[str]) -> List[str]:
        """Extract key phrases from text."""
        key_phrases = []

        # Look for agent-related phrases
        for i, token in enumerate(tokens):
            # Agent type phrases
            if token in self.AGENT_KEYWORDS:
                # Get surrounding context
                start = max(0, i - 2)
                end = min(len(tokens), i + 3)
                phrase = " ".join(tokens[start:end])
                key_phrases.append(phrase)

            # Action phrases
            elif token in self.ACTION_VERBS:
                # Get object of the action
                if i + 1 < len(tokens):
                    phrase = f"{token} {tokens[i + 1]}"
                    if i + 2 < len(tokens) and tokens[i + 2] in self.AGENT_KEYWORDS:
                        phrase += f" {tokens[i + 2]}"
                    key_phrases.append(phrase)

        # Look for numbered lists (1. 2. 3. or - bullet points)
        list_pattern = r"(?:(?:\d+\.)|(?:-)|(?:\*)) (.+?)(?=(?:\d+\.)|(?:-)|(?:\*)|$)"
        list_items = re.findall(list_pattern, text)
        key_phrases.extend(list_items)

        return list(set(key_phrases))  # Remove duplicates

    def _extract_entities(self, text: str, tokens: List[str]) -> Dict[str, List[str]]:
        """Extract named entities from text."""
        entities = {"agents": [], "capabilities": [], "technologies": [], "requirements": []}

        # Extract agent names
        agent_pattern = r"(\w+)\s+(?:agent|assistant|bot|system|service)"
        agent_matches = re.findall(agent_pattern, text, re.IGNORECASE)
        entities["agents"] = list(set(agent_matches))

        # Extract capabilities
        for verb in self.CAPABILITY_VERBS:
            if verb in tokens:
                entities["capabilities"].append(verb)

        # Extract technology mentions
        tech_keywords = [
            "json",
            "xml",
            "api",
            "database",
            "file",
            "stream",
            "http",
            "rest",
            "graphql",
        ]
        for tech in tech_keywords:
            if tech in tokens:
                entities["technologies"].append(tech)

        # Extract requirement keywords
        req_pattern = r"(?:must|should|need to|requires?)\s+(\w+(?:\s+\w+){0,2})"
        req_matches = re.findall(req_pattern, text, re.IGNORECASE)
        entities["requirements"] = list(set(req_matches))

        return entities

    def _calculate_confidence(
        self, tokens: List[str], key_phrases: List[str], entities: Dict[str, List[str]]
    ) -> float:
        """Calculate parsing confidence score."""
        confidence = 0.0

        # Check for action verbs (20%)
        if any(verb in tokens for verb in self.ACTION_VERBS):
            confidence += 0.2

        # Check for agent keywords (20%)
        if any(kw in tokens for kw in self.AGENT_KEYWORDS):
            confidence += 0.2

        # Check for extracted agent names (20%)
        if entities.get("agents"):
            confidence += 0.2

        # Check for capabilities (20%)
        if entities.get("capabilities"):
            confidence += 0.2

        # Check for meaningful key phrases (20%)
        if len(key_phrases) >= 2:
            confidence += 0.2

        return min(confidence, 1.0)

    def identify_agent_count(self, parsed: ParsedPrompt) -> int:
        """
        Identify the number of agents requested.

        Args:
            parsed: ParsedPrompt object

        Returns:
            Estimated number of agents (1-10)
        """
        count = 0

        # Check for explicit numbers
        number_pattern = r"(\d+)\s+agents?"
        matches = re.findall(number_pattern, parsed.raw_prompt, re.IGNORECASE)
        if matches:
            count = int(matches[0])

        # Check for numbered lists
        numbered_pattern = r"^\d+\."
        for sentence in parsed.sentences:
            if re.match(numbered_pattern, sentence.strip()):
                count += 1

        # Check for bullet points
        bullet_pattern = r"^[-*]"
        for sentence in parsed.sentences:
            if re.match(bullet_pattern, sentence.strip()):
                count += 1

        # Check entity count
        if not count and parsed.entities.get("agents"):
            count = len(parsed.entities["agents"])

        # Default to 1 if no count found
        if count == 0:
            count = 1

        # Cap at 10 agents
        return min(count, 10)

    def identify_complexity(self, parsed: ParsedPrompt) -> str:
        """
        Identify requested complexity level.

        Args:
            parsed: ParsedPrompt object

        Returns:
            Complexity level: "simple", "standard", or "advanced"
        """
        tokens = set(parsed.tokens)

        # Check for explicit complexity indicators
        for level, indicators in self.COMPLEXITY_INDICATORS.items():
            if any(indicator in tokens for indicator in indicators):
                return level

        # Estimate based on requirements count
        total_requirements = len(parsed.entities.get("capabilities", [])) + len(
            parsed.entities.get("requirements", [])
        )

        if total_requirements <= 2:
            return "simple"
        if total_requirements <= 5:
            return "standard"
        return "advanced"
