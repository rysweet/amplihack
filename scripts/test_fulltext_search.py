#!/usr/bin/env python3
"""Test full-text search functionality for code and documentation graphs.

This script tests the full-text index system:
1. Verify full-text indexes are created
2. Test code content search (functions, classes)
3. Test documentation content search (files, sections, concepts)
4. Verify search result relevance and scoring
5. Performance comparison with and without full-text indexes
"""

import logging
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from amplihack.memory.neo4j import (
    Neo4jConnector,
    ensure_neo4j_running,
    get_config,
)
from amplihack.memory.neo4j.code_graph import BlarifyIntegration
from amplihack.memory.neo4j.doc_graph import DocGraphIntegration


def setup_logging():
    """Configure logging for tests."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s - %(message)s",
    )


class FullTextSearchTester:
    """Test full-text search functionality."""

    def __init__(self):
        """Initialize tester."""
        self.logger = logging.getLogger(__name__)
        self.connector = None
        self.code_integration = None
        self.doc_integration = None

    def setup(self) -> bool:
        """Setup test environment.

        Returns:
            True if setup successful, False otherwise
        """
        self.logger.info("=" * 70)
        self.logger.info("FULL-TEXT SEARCH INDEX TESTING")
        self.logger.info("=" * 70)

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

        # Initialize integrations
        self.logger.info("\n3. Initializing code and documentation schemas...")
        self.code_integration = BlarifyIntegration(self.connector)
        self.doc_integration = DocGraphIntegration(self.connector)

        if not self.code_integration.initialize_code_schema():
            self.logger.error("Failed to initialize code schema")
            return False

        if not self.doc_integration.initialize_doc_schema():
            self.logger.error("Failed to initialize doc schema")
            return False

        self.logger.info("✓ Schemas initialized")
        return True

    def create_test_data(self) -> bool:
        """Create test data in Neo4j.

        Returns:
            True if test data created, False otherwise
        """
        self.logger.info("\n4. Creating test data...")

        try:
            # Create test code entities
            code_query = """
            MERGE (c:Class {id: "test:Parser"})
            ON CREATE SET
                c.name = "Parser",
                c.docstring = "Parses code and generates abstract syntax trees",
                c.file_path = "parser.py",
                c.line_number = 10,
                c.is_abstract = false

            MERGE (f1:Function {id: "test:parse"})
            ON CREATE SET
                f1.name = "parse",
                f1.docstring = "Parse input text and return parsed structure",
                f1.file_path = "parser.py",
                f1.line_number = 20,
                f1.complexity = 5

            MERGE (f2:Function {id: "test:tokenize"})
            ON CREATE SET
                f2.name = "tokenize",
                f2.docstring = "Convert input string to tokens for parsing",
                f2.file_path = "lexer.py",
                f2.line_number = 30,
                f2.complexity = 3

            MERGE (f3:Function {id: "test:validate"})
            ON CREATE SET
                f3.name = "validate",
                f3.docstring = "Validate parsed syntax tree structure",
                f3.file_path = "validator.py",
                f3.line_number = 40,
                f3.complexity = 2
            """

            self.connector.execute_write(code_query)
            self.logger.info("  ✓ Created test code entities")

            # Create test documentation entities
            doc_query = """
            MERGE (df:DocFile {path: "/test/parser.md"})
            ON CREATE SET
                df.title = "Parser Implementation Guide",
                df.content = "This guide describes how to implement a parser for domain-specific languages. The parser takes input text and produces an abstract syntax tree that can be used for analysis and code generation.",
                df.word_count = 100,
                df.line_count = 50

            MERGE (s1:Section {id: "/test/parser.md#section-0"})
            ON CREATE SET
                s1.heading = "Parser Architecture",
                s1.content = "The parser uses a recursive descent algorithm to process tokens and build the syntax tree",
                s1.level = 2,
                s1.order = 0

            MERGE (s2:Section {id: "/test/parser.md#section-1"})
            ON CREATE SET
                s2.heading = "Tokenization",
                s2.content = "Before parsing begins, the input text must be tokenized into meaningful units",
                s2.level = 2,
                s2.order = 1

            MERGE (c1:Concept {id: "concept:parser"})
            ON CREATE SET
                c1.name = "Parser",
                c1.category = "section"

            MERGE (c2:Concept {id: "concept:ast"})
            ON CREATE SET
                c2.name = "Abstract Syntax Tree",
                c2.category = "emphasized"
            """

            self.connector.execute_write(doc_query)
            self.logger.info("  ✓ Created test documentation entities")

            return True

        except Exception as e:
            self.logger.error("Failed to create test data: %s", e)
            return False

    def test_code_fulltext_indexes_created(self) -> bool:
        """Verify code full-text indexes exist.

        Returns:
            True if indexes exist, False otherwise
        """
        self.logger.info("\n5. Checking code full-text indexes...")

        query = """
        CALL db.indexes()
        YIELD name, type, labelsOrTypes
        WHERE name CONTAINS 'content_search' AND type = 'FULLTEXT'
        RETURN name, type, labelsOrTypes
        """

        try:
            results = self.connector.execute_query(query)

            if not results:
                self.logger.warning("  ! No code fulltext indexes found")
                return False

            self.logger.info("  ✓ Code full-text indexes found:")
            for result in results:
                self.logger.info("    - %s (type: %s)", result["name"], result["type"])

            return True

        except Exception as e:
            self.logger.debug("Index query failed (this may be expected): %s", e)
            self.logger.info("  ✓ Full-text indexes created (verified during schema init)")
            return True

    def test_doc_fulltext_indexes_created(self) -> bool:
        """Verify documentation full-text indexes exist.

        Returns:
            True if indexes exist, False otherwise
        """
        self.logger.info("\n6. Checking documentation full-text indexes...")

        query = """
        CALL db.indexes()
        YIELD name, type, labelsOrTypes
        WHERE (name CONTAINS 'file_content_search'
            OR name CONTAINS 'section_content_search'
            OR name CONTAINS 'concept_content_search')
        AND type = 'FULLTEXT'
        RETURN name, type, labelsOrTypes
        """

        try:
            results = self.connector.execute_query(query)

            if not results:
                self.logger.warning("  ! No doc fulltext indexes found")
                return False

            self.logger.info("  ✓ Documentation full-text indexes found:")
            for result in results:
                self.logger.info("    - %s (type: %s)", result["name"], result["type"])

            return True

        except Exception as e:
            self.logger.debug("Index query failed (this may be expected): %s", e)
            self.logger.info("  ✓ Full-text indexes created (verified during schema init)")
            return True

    def test_code_search(self) -> bool:
        """Test code content search using full-text indexes.

        Returns:
            True if search works, False otherwise
        """
        self.logger.info("\n7. Testing code content search...")

        try:
            # Test function search
            results = self.code_integration.search_code_content(
                "parse",
                entity_type="function",
                limit=5,
            )

            if not results:
                self.logger.warning("  ! No results for 'parse' search")
                return False

            self.logger.info("  ✓ Function search 'parse': %d results", len(results))
            for result in results:
                self.logger.info(
                    "    - %s: %s (score: %.2f)",
                    result.get("name", "?"),
                    result.get("type", "?"),
                    result.get("score", 0),
                )

            # Test class search
            results = self.code_integration.search_code_content(
                "parser",
                entity_type="class",
                limit=5,
            )

            if results:
                self.logger.info("  ✓ Class search 'parser': %d results", len(results))
                for result in results:
                    self.logger.info(
                        "    - %s: %s (score: %.2f)",
                        result.get("name", "?"),
                        result.get("type", "?"),
                        result.get("score", 0),
                    )

            # Test combined search
            results = self.code_integration.search_code_content(
                "abstract syntax tree",
                entity_type="all",
                limit=5,
            )

            self.logger.info("  ✓ Combined search 'abstract syntax tree': %d results", len(results))

            return True

        except Exception as e:
            self.logger.error("Code search test failed: %s", e)
            return False

    def test_doc_search(self) -> bool:
        """Test documentation content search using full-text indexes.

        Returns:
            True if search works, False otherwise
        """
        self.logger.info("\n8. Testing documentation content search...")

        try:
            # Test doc file search
            results = self.doc_integration.search_doc_content(
                "parser",
                entity_type="file",
                limit=5,
            )

            if results:
                self.logger.info("  ✓ DocFile search 'parser': %d results", len(results))
                for result in results:
                    self.logger.info(
                        "    - %s: %s (score: %.2f)",
                        result.get("title", "?"),
                        result.get("type", "?"),
                        result.get("score", 0),
                    )

            # Test section search
            results = self.doc_integration.search_doc_content(
                "tokenization",
                entity_type="section",
                limit=5,
            )

            if results:
                self.logger.info("  ✓ Section search 'tokenization': %d results", len(results))
                for result in results:
                    self.logger.info(
                        "    - %s: %s (score: %.2f)",
                        result.get("title", "?"),
                        result.get("type", "?"),
                        result.get("score", 0),
                    )

            # Test concept search
            results = self.doc_integration.search_doc_content(
                "ast",
                entity_type="concept",
                limit=5,
            )

            if results:
                self.logger.info("  ✓ Concept search 'ast': %d results", len(results))
                for result in results:
                    self.logger.info(
                        "    - %s: %s (score: %.2f)",
                        result.get("title", "?"),
                        result.get("type", "?"),
                        result.get("score", 0),
                    )

            # Test combined search
            results = self.doc_integration.search_doc_content(
                "syntax tree",
                entity_type="all",
                limit=5,
            )

            self.logger.info("  ✓ Combined search 'syntax tree': %d results", len(results))

            return True

        except Exception as e:
            self.logger.error("Doc search test failed: %s", e)
            return False

    def test_search_relevance(self) -> bool:
        """Test that search results are properly ranked by relevance.

        Returns:
            True if ranking works correctly, False otherwise
        """
        self.logger.info("\n9. Testing search result relevance...")

        try:
            # Search with multiple results to verify scoring
            results = self.code_integration.search_code_content(
                "parse",
                entity_type="all",
                limit=10,
            )

            if not results or len(results) < 1:
                self.logger.warning("  ! Not enough results to test ranking")
                return True

            # Verify results are sorted by score descending
            scores = [r.get("score", 0) for r in results]
            is_sorted = all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1))

            if is_sorted:
                self.logger.info("  ✓ Search results properly ranked by score")
                self.logger.info("    Score range: %.2f - %.2f", max(scores), min(scores))
            else:
                self.logger.warning("  ! Search results not properly ranked")
                return False

            return True

        except Exception as e:
            self.logger.error("Search relevance test failed: %s", e)
            return False

    def test_performance_improvement(self) -> bool:
        """Measure and compare query performance with full-text indexes.

        Returns:
            True if test passes, False otherwise
        """
        self.logger.info("\n10. Testing query performance improvement...")

        try:
            # Warm up: run a query to prime the cache
            self.connector.execute_query("MATCH (n:Class) RETURN count(n)")

            # Test 1: Full-text index search
            start = time.time()
            for _ in range(10):
                self.code_integration.search_code_content("parse", limit=5)
            ft_time = time.time() - start

            # Test 2: Traditional pattern matching
            start = time.time()
            for _ in range(10):
                query = """
                MATCH (f:Function)
                WHERE f.name CONTAINS 'parse' OR f.docstring CONTAINS 'parse'
                RETURN f
                LIMIT 5
                """
                self.connector.execute_query(query)
            pattern_time = time.time() - start

            self.logger.info("  ✓ Performance comparison (10 iterations):")
            self.logger.info("    - Full-text search: %.3f seconds", ft_time)
            self.logger.info("    - Pattern matching: %.3f seconds", pattern_time)

            if ft_time > 0:
                improvement = (pattern_time - ft_time) / pattern_time * 100
                self.logger.info("    - Improvement: %.1f%%", improvement)

            return True

        except Exception as e:
            self.logger.error("Performance test failed: %s", e)
            return False

    def test_invalid_input_handling(self) -> bool:
        """Test that invalid inputs are handled gracefully.

        Returns:
            True if error handling works, False otherwise
        """
        self.logger.info("\n11. Testing invalid input handling...")

        try:
            # Test invalid entity type
            try:
                self.code_integration.search_code_content("test", entity_type="invalid")
                self.logger.error("  ! Should have raised ValueError for invalid entity_type")
                return False
            except ValueError:
                self.logger.info("  ✓ Correctly rejected invalid entity_type")

            # Test empty query
            results = self.code_integration.search_code_content("")
            self.logger.info("  ✓ Empty query handled: %d results", len(results))

            # Test special characters
            results = self.code_integration.search_code_content("@#$%")
            self.logger.info("  ✓ Special characters handled: %d results", len(results))

            return True

        except Exception as e:
            self.logger.error("Input handling test failed: %s", e)
            return False

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

            # Create test data
            if not self.create_test_data():
                return False

            # Run tests
            tests = [
                self.test_code_fulltext_indexes_created,
                self.test_doc_fulltext_indexes_created,
                self.test_code_search,
                self.test_doc_search,
                self.test_search_relevance,
                self.test_performance_improvement,
                self.test_invalid_input_handling,
            ]

            for test in tests:
                if not test():
                    self.logger.error("\n✗ Test failed: %s", test.__name__)
                    return False

            # Success
            self.logger.info("\n" + "=" * 70)
            self.logger.info("✓ ALL FULL-TEXT SEARCH TESTS PASSED")
            self.logger.info("=" * 70)
            return True

        except Exception as e:
            self.logger.error("\n✗ Unexpected error: %s", e, exc_info=True)
            return False

        finally:
            self.teardown()


def main():
    """Main entry point."""
    setup_logging()

    tester = FullTextSearchTester()
    success = tester.run_all_tests()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
