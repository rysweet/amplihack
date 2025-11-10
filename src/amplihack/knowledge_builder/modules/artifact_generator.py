"""Artifact generator - creates 5 output files."""

from datetime import datetime
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from amplihack.knowledge_builder.kb_types import KnowledgeGraph, KnowledgeTriplet, Question


class ArtifactGenerator:
    """Generates 5 knowledge artifacts as markdown files."""

    def __init__(self, output_dir: Path):
        """Initialize artifact generator.

        Args:
            output_dir: Directory to write artifacts to
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _write_markdown(self, filename: str, content: str) -> Path:
        """Write markdown content to file.

        Args:
            filename: Name of file to write (e.g., "Knowledge.md")
            content: Markdown content to write

        Returns:
            Path to written file
        """
        output_file = self.output_dir / filename
        output_file.write_text(content, encoding="utf-8")
        return output_file

    def extract_triplets(self, questions: List[Question]) -> List[KnowledgeTriplet]:
        """Extract knowledge triplets from Q&A pairs.

        Args:
            questions: List of answered questions

        Returns:
            List of knowledge triplets
        """
        triplets = []

        for q in questions:
            if not q.answer or q.answer.startswith("Unable"):
                continue

            # Simple heuristic: extract subject-predicate-object from answer
            # For now, create a triplet using the question as subject
            # This is a simplified approach - could be enhanced with NLP

            # Extract first sentence of answer
            first_sentence = q.answer.split(". ")[0]

            triplets.append(
                KnowledgeTriplet(
                    subject=q.text.split("?")[0].strip(),
                    predicate="has answer",
                    object=first_sentence,
                    source="web_search",
                )
            )

        return triplets

    def generate_knowledge_md(self, kg: KnowledgeGraph) -> Path:
        """Generate Knowledge.md with mermaid diagram.

        Args:
            kg: Knowledge graph

        Returns:
            Path to generated file
        """
        content = f"""# Knowledge Graph: {kg.topic}

Generated: {kg.timestamp}

## Overview

This knowledge graph contains {len(kg.questions)} questions organized in a Socratic hierarchy:
- {len([q for q in kg.questions if q.depth == 0])} initial questions (depth 0)
- {len([q for q in kg.questions if q.depth == 1])} follow-up questions (depth 1)
- {len([q for q in kg.questions if q.depth == 2])} deeper questions (depth 2)
- {len([q for q in kg.questions if q.depth == 3])} deepest questions (depth 3)

## Visual Representation

```mermaid
graph TD
    ROOT["{kg.topic}"]
"""

        # Add initial questions
        initial_questions = [q for q in kg.questions if q.depth == 0]
        for i, q in enumerate(initial_questions[:5]):  # Limit to 5 for readability
            q_id = f"Q{i}"
            q_text = q.text[:40] + "..." if len(q.text) > 40 else q.text
            content += f'    {q_id}["{q_text}"]\n'
            content += f"    ROOT --> {q_id}\n"

            # Add first child for each
            children = [
                child for child in kg.questions if child.parent_index == kg.questions.index(q)
            ]
            if children:
                child = children[0]
                child_id = f"Q{i}_0"
                child_text = child.text[:30] + "..." if len(child.text) > 30 else child.text
                content += f'    {child_id}["{child_text}"]\n'
                content += f"    {q_id} --> {child_id}\n"

        content += "```\n\n"
        content += "*Note: Diagram shows simplified view (first 5 initial questions with first child each)*\n\n"

        # Add question hierarchy
        content += "## Question Hierarchy\n\n"
        for q in initial_questions:
            content += f"### {q.text}\n\n"
            content += f"**Answer:** {q.answer}\n\n"

            # Find direct children
            children = [
                child for child in kg.questions if child.parent_index == kg.questions.index(q)
            ]
            if children:
                content += "**Follow-up questions:**\n\n"
                for child in children[:3]:  # Limit to 3
                    content += f"- {child.text}\n"
                content += "\n"

        return self._write_markdown("Knowledge.md", content)

    def generate_triplets_md(self, kg: KnowledgeGraph) -> Path:
        """Generate Triplets.md with fact triplets.

        Args:
            kg: Knowledge graph

        Returns:
            Path to generated file
        """
        content = f"""# Knowledge Triplets: {kg.topic}

Generated: {kg.timestamp}

## Overview

This file contains {len(kg.triplets)} knowledge triplets extracted from the question-answer pairs.

Each triplet follows the format: (Subject, Predicate, Object)

## Triplets

| Subject | Predicate | Object | Source |
|---------|-----------|--------|--------|
"""

        for t in kg.triplets:
            # Truncate long values for table readability
            subject = t.subject[:50] + "..." if len(t.subject) > 50 else t.subject
            predicate = t.predicate[:30] + "..." if len(t.predicate) > 30 else t.predicate
            obj = t.object[:60] + "..." if len(t.object) > 60 else t.object

            content += f"| {subject} | {predicate} | {obj} | {t.source} |\n"

        return self._write_markdown("Triplets.md", content)

    def generate_keyinfo_md(self, kg: KnowledgeGraph) -> Path:
        """Generate KeyInfo.md with executive summary.

        Args:
            kg: Knowledge graph

        Returns:
            Path to generated file
        """
        # Collect key insights from initial questions
        key_insights = []
        initial_questions = [q for q in kg.questions if q.depth == 0]

        for q in initial_questions:
            if q.answer and not q.answer.startswith("Unable"):
                key_insights.append((q.text, q.answer))

        content = f"""# Key Information: {kg.topic}

Generated: {kg.timestamp}

## Executive Summary

This knowledge base explores **{kg.topic}** through {len(kg.questions)} questions across 4 depth levels using the Socratic method.

**Key Statistics:**
- Total Questions: {len(kg.questions)}
- Initial Questions: {len([q for q in kg.questions if q.depth == 0])}
- Depth 1 Questions: {len([q for q in kg.questions if q.depth == 1])}
- Depth 2 Questions: {len([q for q in kg.questions if q.depth == 2])}
- Depth 3 Questions: {len([q for q in kg.questions if q.depth == 3])}
- Unique Sources: {len(kg.sources)}
- Knowledge Triplets: {len(kg.triplets)}

## Core Concepts

"""

        for i, (question, answer) in enumerate(key_insights, 1):
            content += f"### {i}. {question}\n\n"
            content += f"{answer}\n\n"

        content += "## Knowledge Depth\n\n"
        content += "This knowledge base uses the Socratic method to progressively deepen understanding:\n\n"
        content += "- **Depth 0**: Fundamental questions establishing core concepts\n"
        content += "- **Depth 1**: Challenging assumptions and exploring implications\n"
        content += "- **Depth 2**: Testing logical consistency and edge cases\n"
        content += "- **Depth 3**: Deep philosophical and practical considerations\n\n"

        return self._write_markdown("KeyInfo.md", content)

    def generate_sources_md(self, kg: KnowledgeGraph) -> Path:
        """Generate Sources.md with all web sources.

        Args:
            kg: Knowledge graph

        Returns:
            Path to generated file
        """
        content = f"""# Sources: {kg.topic}

Generated: {kg.timestamp}

## Overview

This knowledge base is built from {len(kg.sources)} unique web sources.

## All Sources

"""

        # Group sources by domain
        sources_by_domain = {}
        for source in sorted(kg.sources):
            try:
                domain = urlparse(source).netloc
            except Exception:
                domain = "unknown"

            if domain not in sources_by_domain:
                sources_by_domain[domain] = []
            sources_by_domain[domain].append(source)

        # Output grouped by domain
        for domain in sorted(sources_by_domain.keys()):
            content += f"### {domain}\n\n"
            for source in sources_by_domain[domain]:
                content += f"- {source}\n"
            content += "\n"

        return self._write_markdown("Sources.md", content)

    def generate_howto_md(self, kg: KnowledgeGraph) -> Path:
        """Generate HowToUseTheseFiles.md with usage guide.

        Args:
            kg: Knowledge graph

        Returns:
            Path to generated file
        """
        content = f"""# How To Use These Files

Generated: {kg.timestamp}

## Overview

This directory contains a comprehensive knowledge base about **{kg.topic}** organized into 5 files:

1. **Knowledge.md** - Visual knowledge graph with mermaid diagram and question hierarchy
2. **Triplets.md** - Structured fact triplets in (Subject, Predicate, Object) format
3. **KeyInfo.md** - Executive summary with key concepts and statistics
4. **Sources.md** - All web sources used, organized by domain
5. **HowToUseTheseFiles.md** - This file

## Quick Start

### For Quick Overview
Start with **KeyInfo.md** to get the executive summary and core concepts.

### For Deep Understanding
Read **Knowledge.md** to explore the full question hierarchy and see how concepts build on each other.

### For Fact Extraction
Use **Triplets.md** to extract structured facts in a machine-readable format.

### For Research
Check **Sources.md** to find all original web sources, organized by domain.

### For Visual Learners
The mermaid diagram in **Knowledge.md** shows the conceptual structure at a glance.

## Structure

The knowledge is organized using the Socratic method:

- **Depth 0**: 10 fundamental questions establishing core understanding
- **Depth 1**: 30 follow-up questions (3 per initial question) challenging assumptions
- **Depth 2**: 90 deeper questions (3 per depth-1) exploring implications
- **Depth 3**: ~140 deepest questions testing logical consistency

Total: ~270 questions with answers backed by web research.

## Integration

### Using with Claude Code

```bash
# Search for specific concepts
grep -r "your concept" .

# Count questions by depth
grep "depth" Knowledge.md | sort | uniq -c

# Extract all URLs
grep -h "http" Sources.md | sort | uniq
```

### Using with Python

```python
# Parse triplets for knowledge graph
import re

with open("Triplets.md") as f:
    content = f.read()
    # Extract triplets from markdown table
    # Process with your knowledge graph library
```

## Regeneration

This knowledge base was generated by the Knowledge Builder agent. To regenerate or update:

```bash
/amplihack:knowledge-builder "{kg.topic}"
```

## Notes

- All answers are backed by web search results
- Sources are cited and can be verified
- The Socratic structure helps identify gaps in understanding
- This is a snapshot from {kg.timestamp}
"""

        return self._write_markdown("HowToUseTheseFiles.md", content)

    def generate_all(self, kg: KnowledgeGraph) -> List[Path]:
        """Generate all 5 artifact files.

        Args:
            kg: Knowledge graph

        Returns:
            List of paths to generated files
        """
        print(f"Generating artifacts in: {self.output_dir}")

        # Add timestamp
        kg.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Extract triplets
        print("Extracting knowledge triplets...")
        kg.triplets = self.extract_triplets(kg.questions)
        print(f"  Extracted {len(kg.triplets)} triplets")

        # Generate all files
        files = []
        print("Generating Knowledge.md...")
        files.append(self.generate_knowledge_md(kg))
        print("Generating Triplets.md...")
        files.append(self.generate_triplets_md(kg))
        print("Generating KeyInfo.md...")
        files.append(self.generate_keyinfo_md(kg))
        print("Generating Sources.md...")
        files.append(self.generate_sources_md(kg))
        print("Generating HowToUseTheseFiles.md...")
        files.append(self.generate_howto_md(kg))

        print(f"Generated {len(files)} artifact files")
        return files
