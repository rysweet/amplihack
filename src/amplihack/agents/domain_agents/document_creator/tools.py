"""Document creator domain tools. Pure functions for structuring, formatting, and evaluating documents."""

from __future__ import annotations

import re
from typing import Any


def analyze_structure(content: str, doc_type: str = "report") -> dict[str, Any]:
    """Analyze content and produce a document structure.

    Identifies headings, sections, and logical organization from raw content.

    Args:
        content: Raw content to structure
        doc_type: Type of document (report, memo, proposal, guide)

    Returns:
        Dict with sections, heading_count, word_count, structure_score
    """
    if not content or not content.strip():
        return {
            "sections": [],
            "heading_count": 0,
            "word_count": 0,
            "structure_score": 0.0,
        }

    lines = content.strip().split("\n")
    words = content.split()
    word_count = len(words)

    # Detect headings (markdown-style or ALL CAPS lines)
    sections: list[dict[str, Any]] = []
    current_section: dict[str, Any] | None = None

    for i, line in enumerate(lines):
        stripped = line.strip()
        is_heading = False

        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            title = stripped.lstrip("#").strip()
            is_heading = True
        elif stripped.isupper() and len(stripped) > 3 and len(stripped) < 80:
            level = 1
            title = stripped.title()
            is_heading = True
        elif stripped.endswith(":") and len(stripped) < 60:
            level = 2
            title = stripped.rstrip(":")
            is_heading = True

        if is_heading:
            if current_section:
                sections.append(current_section)
            current_section = {
                "title": title,
                "level": level,
                "line_start": i + 1,
                "content_lines": 0,
            }
        elif current_section:
            if stripped:
                current_section["content_lines"] += 1

    if current_section:
        sections.append(current_section)

    # If no sections detected, create one from the whole content
    if not sections and word_count > 0:
        sections = [{"title": "Main Content", "level": 1, "line_start": 1, "content_lines": len(lines)}]

    # Structure score based on doc type expectations
    expected_sections = {"report": 4, "memo": 3, "proposal": 5, "guide": 4}.get(doc_type, 3)
    section_ratio = min(1.0, len(sections) / expected_sections)
    has_intro = any("intro" in s["title"].lower() or "overview" in s["title"].lower() for s in sections)
    has_conclusion = any(
        "conclusion" in s["title"].lower() or "summary" in s["title"].lower() for s in sections
    )
    structure_score = 0.4 * section_ratio + 0.3 * (1.0 if has_intro else 0.0) + 0.3 * (1.0 if has_conclusion else 0.0)

    return {
        "sections": sections,
        "heading_count": len(sections),
        "word_count": word_count,
        "structure_score": round(structure_score, 3),
        "doc_type": doc_type,
    }


def evaluate_content(content: str, audience: str = "general") -> dict[str, Any]:
    """Evaluate content quality for a target audience.

    Checks readability, completeness, and audience appropriateness.

    Args:
        content: Document content to evaluate
        audience: Target audience (technical, executive, general, beginner)

    Returns:
        Dict with readability_score, completeness, audience_match, issues
    """
    if not content or not content.strip():
        return {
            "readability_score": 0.0,
            "completeness": 0.0,
            "audience_match": 0.0,
            "issues": [{"type": "empty", "message": "No content provided"}],
        }

    words = content.split()
    sentences = re.split(r"[.!?]+", content)
    sentences = [s.strip() for s in sentences if s.strip()]

    word_count = len(words)
    sentence_count = max(1, len(sentences))
    avg_sentence_len = word_count / sentence_count

    # Long words (3+ syllables approximation: 7+ characters)
    long_words = sum(1 for w in words if len(w) > 7)
    long_word_ratio = long_words / max(1, word_count)

    issues: list[dict[str, str]] = []

    # Readability scoring (simplified Flesch-Kincaid approximation)
    if avg_sentence_len > 25:
        issues.append({"type": "readability", "message": f"Average sentence length is {avg_sentence_len:.0f} words (target: <25)"})
    if long_word_ratio > 0.3:
        issues.append({"type": "readability", "message": f"High ratio of complex words: {long_word_ratio:.0%}"})

    readability = max(0.0, 1.0 - 0.02 * max(0, avg_sentence_len - 15) - 0.5 * max(0, long_word_ratio - 0.15))

    # Completeness checks
    has_intro = bool(re.search(r"\b(introduction|overview|purpose|objective)\b", content, re.IGNORECASE))
    has_conclusion = bool(re.search(r"\b(conclusion|summary|next steps|recommendation)\b", content, re.IGNORECASE))
    has_body = word_count > 100
    completeness = (0.3 * has_intro + 0.4 * has_body + 0.3 * has_conclusion)

    # Audience match
    technical_indicators = len(re.findall(r"\b(API|SDK|implementation|algorithm|infrastructure|deploy|config)\b", content, re.IGNORECASE))
    executive_indicators = len(re.findall(r"\b(ROI|strategy|revenue|budget|timeline|stakeholder|KPI)\b", content, re.IGNORECASE))

    audience_scores = {
        "technical": min(1.0, technical_indicators / 3),
        "executive": min(1.0, executive_indicators / 3),
        "general": 1.0 - 0.3 * min(1.0, (technical_indicators + executive_indicators) / 5),
        "beginner": max(0.0, 1.0 - long_word_ratio * 2 - 0.05 * max(0, avg_sentence_len - 15)),
    }
    audience_match = audience_scores.get(audience, 0.5)

    if not has_intro:
        issues.append({"type": "completeness", "message": "Missing introduction or overview section"})
    if not has_conclusion:
        issues.append({"type": "completeness", "message": "Missing conclusion or summary section"})

    return {
        "readability_score": round(readability, 3),
        "completeness": round(completeness, 3),
        "audience_match": round(audience_match, 3),
        "issues": issues,
        "word_count": word_count,
        "sentence_count": sentence_count,
        "avg_sentence_length": round(avg_sentence_len, 1),
    }


def format_document(content: str, format_type: str = "markdown") -> dict[str, Any]:
    """Apply formatting to document content.

    Normalizes headings, adds structure markers, and validates formatting.

    Args:
        content: Raw document content
        format_type: Target format (markdown, plain, html)

    Returns:
        Dict with formatted_content, format_issues, formatting_score
    """
    if not content or not content.strip():
        return {
            "formatted_content": "",
            "format_issues": [],
            "formatting_score": 0.0,
        }

    lines = content.strip().split("\n")
    format_issues: list[dict[str, str]] = []
    formatted_lines: list[str] = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        if format_type == "markdown":
            # Check heading formatting
            if stripped.startswith("#"):
                heading_match = re.match(r"^(#+)\s*(.*)", stripped)
                if heading_match:
                    hashes = heading_match.group(1)
                    title = heading_match.group(2)
                    if not title:
                        format_issues.append({"type": "empty_heading", "message": f"Line {i+1}: Empty heading"})
                    formatted_lines.append(f"{hashes} {title}")
                    continue

            # Check for consistent list formatting
            if re.match(r"^\s*[-*+]\s", stripped):
                # Normalize to consistent list marker
                normalized = re.sub(r"^(\s*)[-*+]\s", r"\1- ", stripped)
                formatted_lines.append(normalized)
                continue

        formatted_lines.append(line)

    # Check for blank lines between sections
    prev_was_heading = False
    for line in formatted_lines:
        if line.strip().startswith("#"):
            if prev_was_heading:
                format_issues.append({"type": "consecutive_headings", "message": "Consecutive headings without content"})
            prev_was_heading = True
        elif line.strip():
            prev_was_heading = False

    formatting_score = max(0.0, 1.0 - 0.1 * len(format_issues))

    return {
        "formatted_content": "\n".join(formatted_lines),
        "format_issues": format_issues,
        "formatting_score": round(formatting_score, 3),
    }


def assess_audience(content: str, target_audience: str = "general") -> dict[str, Any]:
    """Assess how well content matches its target audience.

    Analyzes vocabulary, complexity, and tone for audience fit.

    Args:
        content: Document content
        target_audience: Intended audience (technical, executive, general, beginner)

    Returns:
        Dict with audience_score, vocabulary_level, tone, recommendations
    """
    if not content or not content.strip():
        return {
            "audience_score": 0.0,
            "vocabulary_level": "unknown",
            "tone": "unknown",
            "recommendations": ["Provide content to analyze"],
        }

    words = content.lower().split()
    word_count = len(words)
    unique_words = len(set(words))
    vocabulary_diversity = unique_words / max(1, word_count)

    # Vocabulary complexity
    complex_words = sum(1 for w in words if len(w) > 8)
    complex_ratio = complex_words / max(1, word_count)

    if complex_ratio > 0.2:
        vocabulary_level = "advanced"
    elif complex_ratio > 0.1:
        vocabulary_level = "intermediate"
    else:
        vocabulary_level = "basic"

    # Tone detection
    formal_indicators = len(re.findall(r"\b(furthermore|consequently|therefore|henceforth|pursuant)\b", content, re.IGNORECASE))
    casual_indicators = len(re.findall(r"\b(you|your|we|let's|here's|isn't|don't|can't)\b", content, re.IGNORECASE))

    if formal_indicators > casual_indicators:
        tone = "formal"
    elif casual_indicators > formal_indicators * 2:
        tone = "casual"
    else:
        tone = "neutral"

    # Audience scoring
    recommendations: list[str] = []
    audience_score = 0.5  # baseline

    if target_audience == "technical":
        tech_terms = len(re.findall(r"\b(API|SDK|config|deploy|instance|server|database|query)\b", content, re.IGNORECASE))
        audience_score = min(1.0, 0.3 + tech_terms * 0.1 + 0.2 * (1 if vocabulary_level != "basic" else 0))
        if tech_terms < 2:
            recommendations.append("Include more technical terminology")
        if tone == "casual":
            recommendations.append("Consider a more formal tone for technical audience")

    elif target_audience == "executive":
        exec_terms = len(re.findall(r"\b(ROI|revenue|strategy|budget|impact|risk|timeline)\b", content, re.IGNORECASE))
        audience_score = min(1.0, 0.3 + exec_terms * 0.1 + 0.2 * (1 if vocabulary_level != "advanced" else 0.5))
        if exec_terms < 2:
            recommendations.append("Include business metrics and strategic language")
        if vocabulary_level == "advanced":
            recommendations.append("Simplify technical jargon for executive audience")

    elif target_audience == "beginner":
        audience_score = max(0.0, 1.0 - complex_ratio * 3)
        if vocabulary_level == "advanced":
            recommendations.append("Simplify vocabulary for beginner audience")
            audience_score = max(0.0, audience_score - 0.2)
        if tone == "formal":
            recommendations.append("Use a more approachable tone")

    else:  # general
        audience_score = min(1.0, 0.5 + 0.2 * (1 if vocabulary_level == "intermediate" else 0) + 0.3 * (1 if tone == "neutral" else 0))

    if not recommendations:
        recommendations.append("Content appears well-suited for target audience")

    return {
        "audience_score": round(audience_score, 3),
        "vocabulary_level": vocabulary_level,
        "vocabulary_diversity": round(vocabulary_diversity, 3),
        "tone": tone,
        "recommendations": recommendations,
        "word_count": word_count,
    }
