#!/usr/bin/env python3
"""Test documentation parsing WITHOUT Neo4j dependency.

This tests the core markdown parsing functionality using real documentation files.
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from amplihack.memory.neo4j.doc_graph import DocGraphIntegration
from amplihack.memory.neo4j import Neo4jConnector


def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s',
    )


def main():
    """Test documentation parsing with real files."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("DOCUMENTATION PARSING TEST (No Neo4j Required)")
    logger.info("=" * 60)

    # Create a dummy connector (won't be used for parsing)
    connector = Neo4jConnector(uri="bolt://localhost:7687", user="neo4j", password="test")
    doc_integration = DocGraphIntegration(connector)

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
    logger.info("TESTING MARKDOWN PARSING")
    logger.info("=" * 60)

    total_sections = 0
    total_concepts = 0
    total_code_refs = 0
    total_links = 0
    errors = 0

    for file_path in test_files:
        logger.info("\n--- Parsing: %s ---", file_path.name)

        try:
            doc_data = doc_integration.parse_markdown_doc(file_path)

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
            logger.info("Code references: %d", len(doc_data['code_references']))
            logger.info("Links: %d", len(doc_data['links']))
            logger.info("Words: %d", doc_data['metadata']['word_count'])

            # Show sample sections
            if doc_data['sections']:
                logger.info("\nSample sections:")
                for section in doc_data['sections'][:3]:
                    logger.info("  [H%d] %s", section['level'], section['heading'])

            # Show sample concepts
            if doc_data['concepts']:
                logger.info("\nSample concepts:")
                for concept in doc_data['concepts'][:5]:
                    logger.info("  - %s (%s)", concept['name'], concept['category'])

            # Show sample code references
            if doc_data['code_references']:
                logger.info("\nSample code references:")
                for ref in doc_data['code_references'][:3]:
                    line_str = f":{ref['line']}" if ref['line'] else ""
                    logger.info("  - %s%s", ref['file'], line_str)

            # Update totals
            total_sections += len(doc_data['sections'])
            total_concepts += len(doc_data['concepts'])
            total_code_refs += len(doc_data['code_references'])
            total_links += len(doc_data['links'])

            logger.info("\n✓ Parsed successfully")

        except Exception as e:
            logger.error("✗ Failed to parse: %s", e)
            errors += 1

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    logger.info("Files processed: %d", len(test_files))
    logger.info("Errors: %d", errors)
    logger.info("\nTotal extracted:")
    logger.info("  Sections: %d", total_sections)
    logger.info("  Concepts: %d", total_concepts)
    logger.info("  Code references: %d", total_code_refs)
    logger.info("  Links: %d", total_links)

    if errors == 0:
        logger.info("\n✓ ALL TESTS PASSED")
        logger.info("=" * 60)
        return 0
    logger.error("\n✗ TESTS FAILED (%d errors)", errors)
    logger.info("=" * 60)
    return 1


if __name__ == '__main__':
    sys.exit(main())
