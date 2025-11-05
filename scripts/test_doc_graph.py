#!/usr/bin/env python3
"""Test documentation knowledge graph with REAL markdown files.

This script tests the documentation graph system end-to-end:
1. Parse real markdown files from docs/ and .claude/
2. Import them into Neo4j
3. Verify nodes and relationships created
4. Test queries and linking functionality
5. Validate graph integrity
"""

import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from amplihack.memory.neo4j import (
    Neo4jConnector,
    ensure_neo4j_running,
    get_config,
)
from amplihack.memory.neo4j.doc_graph import DocGraphIntegration


def setup_logging():
    """Configure logging for tests."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(levelname)s - %(message)s',
    )


class DocGraphTester:
    """Test documentation graph functionality with real files."""

    def __init__(self):
        """Initialize tester."""
        self.logger = logging.getLogger(__name__)
        self.connector = None
        self.doc_integration = None
        self.test_files = []

    def setup(self) -> bool:
        """Setup test environment.

        Returns:
            True if setup successful, False otherwise
        """
        self.logger.info("=" * 60)
        self.logger.info("DOCUMENTATION GRAPH TESTING")
        self.logger.info("=" * 60)

        # Ensure Neo4j is running
        self.logger.info("\n1. Starting Neo4j...")
        if not ensure_neo4j_running(blocking=True):
            self.logger.error("Failed to start Neo4j")
            return False
        self.logger.info("✓ Neo4j is running")

        # Connect to Neo4j
        self.logger.info("\n2. Connecting to Neo4j...")
        config = get_config()
        self.connector = Neo4jConnector(
            uri=config.uri,
            auth=(config.username, config.password),
        )

        if not self.connector.connect():
            self.logger.error("Failed to connect to Neo4j")
            return False
        self.logger.info("✓ Connected to Neo4j")

        # Initialize documentation integration
        self.logger.info("\n3. Initializing documentation schema...")
        self.doc_integration = DocGraphIntegration(self.connector)

        if not self.doc_integration.initialize_doc_schema():
            self.logger.error("Failed to initialize schema")
            return False
        self.logger.info("✓ Schema initialized")

        return True

    def find_test_files(self) -> bool:
        """Find real markdown files to test with.

        Returns:
            True if files found, False otherwise
        """
        self.logger.info("\n4. Finding test markdown files...")

        project_root = Path(__file__).parent.parent

        # Find files in docs/
        docs_dir = project_root / 'docs'
        if docs_dir.exists():
            docs_files = list(docs_dir.glob('**/*.md'))
            self.test_files.extend(docs_files[:3])  # Take first 3

        # Find files in .claude/context/
        context_dir = project_root / '.claude' / 'context'
        if context_dir.exists():
            context_files = list(context_dir.glob('*.md'))
            self.test_files.extend(context_files[:2])  # Take first 2

        if not self.test_files:
            self.logger.error("No markdown files found for testing")
            return False

        self.logger.info("✓ Found %d test files:", len(self.test_files))
        for file in self.test_files:
            self.logger.info("  - %s", file.relative_to(project_root))

        return True

    def test_markdown_parsing(self) -> bool:
        """Test markdown parsing functionality.

        Returns:
            True if all tests pass, False otherwise
        """
        self.logger.info("\n5. Testing markdown parsing...")

        for file_path in self.test_files:
            try:
                doc_data = self.doc_integration.parse_markdown_doc(file_path)

                # Verify parsed data structure
                assert 'path' in doc_data
                assert 'title' in doc_data
                assert 'content' in doc_data
                assert 'sections' in doc_data
                assert 'concepts' in doc_data
                assert 'code_references' in doc_data
                assert 'links' in doc_data
                assert 'metadata' in doc_data

                self.logger.info("  ✓ Parsed: %s", file_path.name)
                self.logger.info("    - Title: %s", doc_data['title'])
                self.logger.info("    - Sections: %d", len(doc_data['sections']))
                self.logger.info("    - Concepts: %d", len(doc_data['concepts']))
                self.logger.info("    - Code refs: %d", len(doc_data['code_references']))
                self.logger.info("    - Links: %d", len(doc_data['links']))

            except Exception as e:
                self.logger.error("Failed to parse %s: %s", file_path, e)
                return False

        self.logger.info("✓ All files parsed successfully")
        return True

    def test_concept_extraction(self) -> bool:
        """Test concept extraction from real files.

        Returns:
            True if concepts extracted, False otherwise
        """
        self.logger.info("\n6. Testing concept extraction...")

        total_concepts = 0

        for file_path in self.test_files:
            doc_data = self.doc_integration.parse_markdown_doc(file_path)
            concepts = doc_data['concepts']

            if concepts:
                self.logger.info("  ✓ %s: %d concepts", file_path.name, len(concepts))
                # Show first few concepts
                for concept in concepts[:3]:
                    self.logger.info("    - %s (%s)", concept['name'], concept['category'])
                total_concepts += len(concepts)

        if total_concepts == 0:
            self.logger.warning("! No concepts extracted from any file")
            return False

        self.logger.info("✓ Extracted %d total concepts", total_concepts)
        return True

    def test_code_reference_extraction(self) -> bool:
        """Test code reference extraction.

        Returns:
            True if test passes, False otherwise
        """
        self.logger.info("\n7. Testing code reference extraction...")

        total_refs = 0

        for file_path in self.test_files:
            doc_data = self.doc_integration.parse_markdown_doc(file_path)
            refs = doc_data['code_references']

            if refs:
                self.logger.info("  ✓ %s: %d code references", file_path.name, len(refs))
                # Show first few references
                for ref in refs[:3]:
                    self.logger.info("    - %s:%s", ref['file'], ref.get('line', '?'))
                total_refs += len(refs)

        self.logger.info("✓ Extracted %d total code references", total_refs)
        return True

    def test_import_to_neo4j(self) -> bool:
        """Test importing documentation into Neo4j.

        Returns:
            True if import successful, False otherwise
        """
        self.logger.info("\n8. Testing Neo4j import...")

        total_stats = {
            'doc_files': 0,
            'sections': 0,
            'concepts': 0,
            'code_refs': 0,
        }

        for file_path in self.test_files:
            try:
                stats = self.doc_integration.import_documentation(
                    file_path=file_path,
                    project_id='test-project',
                )

                total_stats['doc_files'] += stats.get('doc_files', 0)
                total_stats['sections'] += stats.get('sections', 0)
                total_stats['concepts'] += stats.get('concepts', 0)
                total_stats['code_refs'] += stats.get('code_refs', 0)

                self.logger.info("  ✓ Imported: %s", file_path.name)

            except Exception as e:
                self.logger.error("Failed to import %s: %s", file_path, e)
                return False

        self.logger.info("✓ Import complete:")
        self.logger.info("  - DocFiles: %d", total_stats['doc_files'])
        self.logger.info("  - Sections: %d", total_stats['sections'])
        self.logger.info("  - Concepts: %d", total_stats['concepts'])
        self.logger.info("  - Code refs: %d", total_stats['code_refs'])

        return True

    def test_graph_queries(self) -> bool:
        """Test querying the documentation graph.

        Returns:
            True if queries work, False otherwise
        """
        self.logger.info("\n9. Testing graph queries...")

        # Query 1: Get documentation stats
        try:
            stats = self.doc_integration.get_doc_stats()
            self.logger.info("  ✓ Doc stats query successful:")
            self.logger.info("    - Total docs: %d", stats['doc_count'])
            self.logger.info("    - Total concepts: %d", stats['concept_count'])
            self.logger.info("    - Total sections: %d", stats['section_count'])
        except Exception as e:
            self.logger.error("Failed to query doc stats: %s", e)
            return False

        # Query 2: Search for relevant docs
        try:
            search_terms = ['neo4j', 'memory', 'agent', 'test']
            for term in search_terms:
                results = self.doc_integration.query_relevant_docs(term, limit=3)
                self.logger.info("  ✓ Search '%s': %d results", term, len(results))
                if results:
                    for result in results[:2]:
                        self.logger.info("    - %s", Path(result['path']).name)
        except Exception as e:
            self.logger.error("Failed to search docs: %s", e)
            return False

        self.logger.info("✓ All queries successful")
        return True

    def test_doc_code_linking(self) -> bool:
        """Test linking documentation to code.

        Returns:
            True if linking works, False otherwise
        """
        self.logger.info("\n10. Testing doc-code linking...")

        try:
            link_count = self.doc_integration.link_docs_to_code(project_id='test-project')
            self.logger.info("✓ Created %d doc-code links", link_count)
            return True
        except Exception as e:
            self.logger.error("Failed to link docs to code: %s", e)
            return False

    def test_graph_integrity(self) -> bool:
        """Test graph integrity and relationships.

        Returns:
            True if graph is valid, False otherwise
        """
        self.logger.info("\n11. Testing graph integrity...")

        # Query to check all relationship types exist
        query = """
        MATCH (df:DocFile)-[r]->(target)
        RETURN type(r) as rel_type, count(r) as count
        ORDER BY count DESC
        """

        try:
            results = self.connector.execute_query(query)

            if results:
                self.logger.info("  ✓ Relationship types found:")
                for result in results:
                    self.logger.info("    - %s: %d", result['rel_type'], result['count'])
            else:
                self.logger.warning("  ! No relationships found")

        except Exception as e:
            self.logger.error("Failed to check graph integrity: %s", e)
            return False

        # Check for orphaned nodes
        query = """
        MATCH (df:DocFile)
        WHERE NOT (df)-[]-()
        RETURN count(df) as orphan_count
        """

        try:
            results = self.connector.execute_query(query)
            orphan_count = results[0]['orphan_count'] if results else 0

            if orphan_count > 0:
                self.logger.warning("  ! Found %d orphaned DocFiles", orphan_count)
            else:
                self.logger.info("  ✓ No orphaned nodes")

        except Exception as e:
            self.logger.error("Failed to check for orphans: %s", e)
            return False

        self.logger.info("✓ Graph integrity check passed")
        return True

    def teardown(self):
        """Cleanup test environment."""
        self.logger.info("\n12. Cleaning up...")

        if self.connector:
            self.connector.close()
            self.logger.info("✓ Closed Neo4j connection")

    def run_all_tests(self) -> bool:
        """Run all tests.

        Returns:
            True if all tests pass, False otherwise
        """
        try:
            # Setup
            if not self.setup():
                return False

            # Find test files
            if not self.find_test_files():
                return False

            # Run tests
            tests = [
                self.test_markdown_parsing,
                self.test_concept_extraction,
                self.test_code_reference_extraction,
                self.test_import_to_neo4j,
                self.test_graph_queries,
                self.test_doc_code_linking,
                self.test_graph_integrity,
            ]

            for test in tests:
                if not test():
                    self.logger.error("\n✗ Test failed: %s", test.__name__)
                    return False

            # Success
            self.logger.info("\n" + "=" * 60)
            self.logger.info("✓ ALL TESTS PASSED")
            self.logger.info("=" * 60)
            return True

        except Exception as e:
            self.logger.error("\n✗ Unexpected error: %s", e, exc_info=True)
            return False

        finally:
            self.teardown()


def main():
    """Main entry point."""
    setup_logging()

    tester = DocGraphTester()
    success = tester.run_all_tests()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
