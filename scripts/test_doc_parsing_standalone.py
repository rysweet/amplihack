#!/usr/bin/env python3
"""Test documentation parsing STANDALONE (no dependencies).

Tests markdown parsing logic directly without Neo4j or connector dependencies.
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s',
    )


# Import only the parsing methods we need - inline the class to avoid deps
import re
from datetime import datetime
from typing import Any, Dict, List


class DocParser:
    """Standalone documentation parser (no Neo4j dependencies)."""

    def parse_markdown_doc(self, file_path: Path) -> Dict[str, Any]:
        """Parse markdown documentation file into structured data."""
        if not file_path.exists():
            raise FileNotFoundError(f"Documentation file not found: {file_path}")

        if file_path.suffix.lower() not in ['.md', '.markdown']:
            raise ValueError(f"Not a markdown file: {file_path}")

        with open(file_path, encoding='utf-8') as f:
            content = f.read()

        # Extract title (first heading)
        title = self._extract_title(content)

        # Parse sections
        sections = self._parse_sections(content)

        # Extract concepts
        concepts = self._extract_concepts(content, sections)

        # Extract code references
        code_references = self._extract_code_references(content)

        # Extract links
        links = self._extract_links(content)

        # Build metadata
        metadata = self._extract_metadata(file_path, content)

        return {
            'path': str(file_path.absolute()),
            'title': title,
            'content': content,
            'sections': sections,
            'concepts': concepts,
            'code_references': code_references,
            'links': links,
            'metadata': metadata,
        }

    def _extract_title(self, content: str) -> str:
        """Extract title from markdown content (first # heading)."""
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return "Untitled"

    def _parse_sections(self, content: str) -> List[Dict[str, Any]]:
        """Parse markdown into sections based on headings."""
        sections = []
        lines = content.split('\n')

        current_section = None
        current_content = []

        for line in lines:
            # Check for heading
            heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)

            if heading_match:
                # Save previous section
                if current_section:
                    current_section['content'] = '\n'.join(current_content).strip()
                    sections.append(current_section)

                # Start new section
                level = len(heading_match.group(1))
                heading = heading_match.group(2).strip()

                current_section = {
                    'heading': heading,
                    'level': level,
                    'content': '',
                }
                current_content = []
            else:
                # Add to current section content
                if current_section:
                    current_content.append(line)

        # Save last section
        if current_section:
            current_section['content'] = '\n'.join(current_content).strip()
            sections.append(current_section)

        return sections

    def _extract_concepts(self, content: str, sections: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Extract key concepts from documentation."""
        concepts = []
        seen = set()

        # Extract from section headings
        for section in sections:
            heading = section['heading']
            # Skip generic headings
            if heading.lower() not in ['overview', 'introduction', 'summary', 'conclusion']:
                if heading not in seen:
                    concepts.append({
                        'name': heading,
                        'category': 'section',
                    })
                    seen.add(heading)

        # Extract bold text (likely important concepts)
        bold_pattern = re.compile(r'\*\*([^*]+)\*\*')
        for match in bold_pattern.finditer(content):
            concept = match.group(1).strip()
            # Filter out short or generic terms
            if len(concept) > 3 and concept not in seen:
                concepts.append({
                    'name': concept,
                    'category': 'emphasized',
                })
                seen.add(concept)

        # Extract code block languages as concepts
        code_block_pattern = re.compile(r'```(\w+)')
        for match in code_block_pattern.finditer(content):
            language = match.group(1).strip()
            if language and language not in seen:
                concepts.append({
                    'name': language,
                    'category': 'language',
                })
                seen.add(language)

        return concepts

    def _extract_code_references(self, content: str) -> List[Dict[str, Any]]:
        """Extract code references from documentation."""
        references = []

        # Pattern 1: @file.py or @path/to/file.py
        at_pattern = re.compile(r'@([\w/._-]+\.py)')
        for match in at_pattern.finditer(content):
            file_path = match.group(1)
            references.append({
                'file': file_path,
                'line': None,
            })

        # Pattern 2: file:line references (e.g., example.py:42)
        file_line_pattern = re.compile(r'([\w/._-]+\.py):(\d+)')
        for match in file_line_pattern.finditer(content):
            file_path = match.group(1)
            line_num = int(match.group(2))
            references.append({
                'file': file_path,
                'line': line_num,
            })

        # Pattern 3: Inline code with .py extension (`file.py`)
        inline_code_pattern = re.compile(r'`([\w/._-]+\.py)`')
        for match in inline_code_pattern.finditer(content):
            file_path = match.group(1)
            references.append({
                'file': file_path,
                'line': None,
            })

        return references

    def _extract_links(self, content: str) -> List[Dict[str, str]]:
        """Extract markdown links from content."""
        links = []

        # Markdown link pattern: [text](url)
        link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        for match in link_pattern.finditer(content):
            text = match.group(1).strip()
            url = match.group(2).strip()
            links.append({
                'text': text,
                'url': url,
            })

        return links

    def _extract_metadata(self, file_path: Path, content: str) -> Dict[str, Any]:
        """Extract metadata from file and content."""
        stat = file_path.stat()

        return {
            'size_bytes': stat.st_size,
            'line_count': content.count('\n') + 1,
            'word_count': len(content.split()),
            'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'file_type': file_path.suffix.lower(),
        }


def main():
    """Test documentation parsing with real files."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("STANDALONE DOCUMENTATION PARSING TEST")
    logger.info("=" * 60)

    parser = DocParser()

    # Find test files
    project_root = Path(__file__).parent.parent

    test_files = []

    # Get files from docs/
    docs_dir = project_root / 'docs'
    if docs_dir.exists():
        docs_files = list(docs_dir.glob('**/*.md'))
        test_files.extend(docs_files[:3])

    # Get files from .claude/context/
    context_dir = project_root / '.claude' / 'context'
    if context_dir.exists():
        context_files = list(context_dir.glob('*.md'))
        test_files.extend(context_files[:2])

    if not test_files:
        logger.error("No markdown files found for testing")
        return 1

    logger.info("\nFound %d test files:", len(test_files))
    for file in test_files:
        logger.info("  - %s", file.relative_to(project_root))

    # Test parsing each file
    logger.info("\n" + "=" * 60)
    logger.info("PARSING TEST RESULTS")
    logger.info("=" * 60)

    total_sections = 0
    total_concepts = 0
    total_code_refs = 0
    total_links = 0
    errors = 0

    for file_path in test_files:
        logger.info("\n--- %s ---", file_path.name)

        try:
            doc_data = parser.parse_markdown_doc(file_path)

            # Verify structure
            assert 'path' in doc_data
            assert 'title' in doc_data
            assert 'content' in doc_data
            assert 'sections' in doc_data
            assert 'concepts' in doc_data
            assert 'code_references' in doc_data
            assert 'links' in doc_data
            assert 'metadata' in doc_data

            # Print results
            logger.info("Title: %s", doc_data['title'])
            logger.info("Sections: %d", len(doc_data['sections']))
            logger.info("Concepts: %d", len(doc_data['concepts']))
            logger.info("Code refs: %d", len(doc_data['code_references']))
            logger.info("Links: %d", len(doc_data['links']))
            logger.info("Words: %d", doc_data['metadata']['word_count'])

            # Show sample sections
            if doc_data['sections']:
                logger.info("\nSections (first 3):")
                for section in doc_data['sections'][:3]:
                    logger.info("  [H%d] %s", section['level'], section['heading'])

            # Show sample concepts
            if doc_data['concepts']:
                logger.info("\nConcepts (first 5):")
                for concept in doc_data['concepts'][:5]:
                    logger.info("  - %s (%s)", concept['name'], concept['category'])

            # Show sample code references
            if doc_data['code_references']:
                logger.info("\nCode references (first 3):")
                for ref in doc_data['code_references'][:3]:
                    line_str = f":{ref['line']}" if ref['line'] else ""
                    logger.info("  - %s%s", ref['file'], line_str)

            # Update totals
            total_sections += len(doc_data['sections'])
            total_concepts += len(doc_data['concepts'])
            total_code_refs += len(doc_data['code_references'])
            total_links += len(doc_data['links'])

            logger.info("\n✓ SUCCESS")

        except Exception as e:
            logger.error("✗ FAILED: %s", e, exc_info=True)
            errors += 1

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("FINAL SUMMARY")
    logger.info("=" * 60)
    logger.info("Files processed: %d", len(test_files))
    logger.info("Errors: %d", errors)
    logger.info("\nTotal extracted:")
    logger.info("  Sections: %d", total_sections)
    logger.info("  Concepts: %d", total_concepts)
    logger.info("  Code references: %d", total_code_refs)
    logger.info("  Links: %d", total_links)

    if errors == 0 and total_sections > 0:
        logger.info("\n✓ ALL TESTS PASSED - Documentation parsing works!")
        logger.info("=" * 60)
        return 0
    logger.error("\n✗ TESTS FAILED")
    logger.info("=" * 60)
    return 1


if __name__ == '__main__':
    sys.exit(main())
