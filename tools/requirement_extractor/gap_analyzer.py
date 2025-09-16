"""
Gap analyzer for comparing extracted requirements against existing documentation
"""
import re
from pathlib import Path
from typing import List, Set, Dict, Any, Optional
from .models import Requirement, GapAnalysis


class GapAnalyzer:
    """Analyzes gaps between extracted requirements and existing documentation"""

    def __init__(self):
        self.existing_requirements: List[Requirement] = []

    def load_existing_requirements(self, doc_path: str) -> bool:
        """Load existing requirements from a documentation file"""
        if not doc_path or not Path(doc_path).exists():
            return False

        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse markdown or text file for requirements
            self.existing_requirements = self._parse_requirements_from_text(content)
            return True

        except Exception as e:
            print(f"Failed to load existing requirements: {e}")
            return False

    def _parse_requirements_from_text(self, content: str) -> List[Requirement]:
        """Parse requirements from text/markdown content"""
        requirements = []

        # Look for common requirement patterns
        # Pattern 1: Numbered requirements (1. Requirement text)
        # Pattern 2: Bullet points with keywords (- Must/Should/Shall...)
        # Pattern 3: Headers with requirement keywords (## REQ-001: Title)

        lines = content.split('\n')
        req_id = 0

        for i, line in enumerate(lines):
            line = line.strip()

            # Check for requirement patterns
            is_requirement = False
            title = ""
            description = ""

            # Pattern 1: Numbered list
            if re.match(r'^\d+\.\s+', line):
                is_requirement = True
                title = re.sub(r'^\d+\.\s+', '', line)[:50]
                description = line

            # Pattern 2: Keywords in bullets
            elif re.match(r'^[-*]\s+(Must|Should|Shall|Will|Can)', line, re.IGNORECASE):
                is_requirement = True
                title = line[2:52]  # Remove bullet, take first 50 chars
                description = line[2:]  # Remove bullet

            # Pattern 3: Requirement IDs
            elif re.match(r'^#+\s*REQ[-_]\d+', line, re.IGNORECASE):
                is_requirement = True
                parts = line.split(':', 1)
                title = parts[1].strip() if len(parts) > 1 else line
                description = line

                # Try to get more context from following lines
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and not next_line.startswith('#'):
                        description += " " + next_line

            if is_requirement:
                req_id += 1
                req = Requirement(
                    id=f"DOC_{req_id}",
                    title=title[:100],  # Limit title length
                    description=description,
                    category="Documentation",
                    priority="medium",
                    source_modules=["documentation"],
                    evidence=[],
                    confidence=0.9
                )
                requirements.append(req)

        return requirements

    def analyze_gaps(self, extracted_requirements: List[Requirement]) -> GapAnalysis:
        """Analyze gaps between extracted and documented requirements"""
        # Create normalized sets for comparison
        doc_titles = {self._normalize_text(r.title) for r in self.existing_requirements}
        extracted_titles = {self._normalize_text(r.title) for r in extracted_requirements}

        # Find missing requirements
        missing_in_docs = []
        missing_in_code = []
        inconsistencies = []

        # Check what's in code but not in docs
        for req in extracted_requirements:
            normalized_title = self._normalize_text(req.title)
            if not self._find_similar_requirement(req, self.existing_requirements):
                missing_in_docs.append(req)

        # Check what's in docs but not in code
        for req in self.existing_requirements:
            if not self._find_similar_requirement(req, extracted_requirements):
                missing_in_code.append(req)

        # Check for inconsistencies (requirements that exist in both but differ)
        for ext_req in extracted_requirements:
            similar = self._find_similar_requirement(ext_req, self.existing_requirements)
            if similar:
                # Check if descriptions differ significantly
                if self._descriptions_differ(ext_req.description, similar.description):
                    inconsistencies.append({
                        "extracted": ext_req,
                        "documented": similar,
                        "difference": "Descriptions differ significantly"
                    })

        return GapAnalysis(
            documented_requirements=self.existing_requirements,
            extracted_requirements=extracted_requirements,
            missing_in_docs=missing_in_docs,
            missing_in_code=missing_in_code,
            inconsistencies=inconsistencies
        )

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        # Remove special characters, convert to lowercase
        text = re.sub(r'[^a-zA-Z0-9\s]', '', text.lower())
        # Remove extra whitespace
        text = ' '.join(text.split())
        return text

    def _find_similar_requirement(self, req: Requirement, requirements: List[Requirement]) -> Optional[Requirement]:
        """Find a similar requirement in a list"""
        normalized_target = self._normalize_text(req.title)

        for candidate in requirements:
            normalized_candidate = self._normalize_text(candidate.title)

            # Check for exact match
            if normalized_target == normalized_candidate:
                return candidate

            # Check for significant overlap (>70% word overlap)
            target_words = set(normalized_target.split())
            candidate_words = set(normalized_candidate.split())

            if target_words and candidate_words:
                overlap = len(target_words & candidate_words)
                total = len(target_words | candidate_words)
                if total > 0 and overlap / total > 0.7:
                    return candidate

        return None

    def _descriptions_differ(self, desc1: str, desc2: str) -> bool:
        """Check if two descriptions differ significantly"""
        norm1 = self._normalize_text(desc1)
        norm2 = self._normalize_text(desc2)

        # If one is much longer than the other
        if abs(len(norm1) - len(norm2)) > max(len(norm1), len(norm2)) * 0.5:
            return True

        # Check word overlap
        words1 = set(norm1.split())
        words2 = set(norm2.split())

        if not words1 or not words2:
            return False

        overlap = len(words1 & words2)
        total = len(words1 | words2)

        # If less than 50% overlap, they differ
        return total > 0 and overlap / total < 0.5