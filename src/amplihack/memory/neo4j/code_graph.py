"""Blarify code graph integration with Neo4j memory system.

Integrates blarify-generated code graphs into the same Neo4j database
as the memory system, creating relationships between code and memories.
"""

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .connector import Neo4jConnector
from .config import get_config

logger = logging.getLogger(__name__)


class BlarifyIntegration:
    """Integrates blarify code graphs with Neo4j memory system.

    Handles:
    - Importing blarify-generated code graphs
    - Creating code node types (File, Class, Function, Import)
    - Linking code to memories
    - Querying code context for memories
    - Incremental updates
    """

    def __init__(self, connector: Neo4jConnector):
        """Initialize blarify integration.

        Args:
            connector: Connected Neo4jConnector instance
        """
        self.conn = connector
        self.config = get_config()

    def initialize_code_schema(self) -> bool:
        """Initialize schema for code graph nodes (idempotent).

        Returns:
            True if successful, False otherwise
        """
        logger.info("Initializing code graph schema")

        try:
            self._create_code_constraints()
            self._create_code_indexes()
            logger.info("Code graph schema initialization complete")
            return True

        except Exception as e:
            logger.error("Code graph schema initialization failed: %s", e)
            return False

    def _create_code_constraints(self):
        """Create unique constraints for code nodes (idempotent)."""
        constraints = [
            # CodeFile path uniqueness
            """
            CREATE CONSTRAINT code_file_path IF NOT EXISTS
            FOR (cf:CodeFile) REQUIRE cf.path IS UNIQUE
            """,
            # Class name + file uniqueness
            """
            CREATE CONSTRAINT class_id IF NOT EXISTS
            FOR (c:Class) REQUIRE c.id IS UNIQUE
            """,
            # Function name + file uniqueness
            """
            CREATE CONSTRAINT function_id IF NOT EXISTS
            FOR (f:Function) REQUIRE f.id IS UNIQUE
            """,
        ]

        for constraint in constraints:
            try:
                self.conn.execute_write(constraint)
                logger.debug("Created code constraint")
            except Exception as e:
                logger.debug("Code constraint already exists or error: %s", e)

    def _create_code_indexes(self):
        """Create performance indexes for code nodes (idempotent)."""
        indexes = [
            # File language index
            """
            CREATE INDEX code_file_language IF NOT EXISTS
            FOR (cf:CodeFile) ON (cf.language)
            """,
            # Class name index
            """
            CREATE INDEX class_name IF NOT EXISTS
            FOR (c:Class) ON (c.name)
            """,
            # Function name index
            """
            CREATE INDEX function_name IF NOT EXISTS
            FOR (f:Function) ON (f.name)
            """,
        ]

        for index in indexes:
            try:
                self.conn.execute_write(index)
                logger.debug("Created code index")
            except Exception as e:
                logger.debug("Code index already exists or error: %s", e)

    def import_blarify_output(
        self,
        blarify_json_path: Path,
        project_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """Import blarify JSON output into Neo4j.

        Args:
            blarify_json_path: Path to blarify output JSON file
            project_id: Optional project ID to link code to

        Returns:
            Dictionary with counts of imported nodes

        Raises:
            FileNotFoundError: If JSON file doesn't exist
            ValueError: If JSON is invalid
        """
        if not blarify_json_path.exists():
            raise FileNotFoundError(f"Blarify output not found: {blarify_json_path}")

        logger.info("Importing blarify output from %s", blarify_json_path)

        with open(blarify_json_path) as f:
            blarify_data = json.load(f)

        counts = {
            "files": 0,
            "classes": 0,
            "functions": 0,
            "imports": 0,
            "relationships": 0,
        }

        # Import in order: files -> classes -> functions -> imports -> relationships
        counts["files"] = self._import_files(blarify_data.get("files", []), project_id)
        counts["classes"] = self._import_classes(blarify_data.get("classes", []))
        counts["functions"] = self._import_functions(blarify_data.get("functions", []))
        counts["imports"] = self._import_imports(blarify_data.get("imports", []))
        counts["relationships"] = self._import_relationships(blarify_data.get("relationships", []))

        logger.info("Blarify import complete: %s", counts)
        return counts

    def _import_files(self, files: List[Dict[str, Any]], project_id: Optional[str] = None) -> int:
        """Import code file nodes.

        Args:
            files: List of file dictionaries from blarify
            project_id: Optional project ID

        Returns:
            Number of files imported
        """
        if not files:
            return 0

        query = """
        UNWIND $files as file
        MERGE (cf:CodeFile {path: file.path})
        ON CREATE SET
            cf.language = file.language,
            cf.lines_of_code = file.lines_of_code,
            cf.last_modified = file.last_modified,
            cf.created_at = $created_at,
            cf.imported_at = $imported_at
        ON MATCH SET
            cf.lines_of_code = file.lines_of_code,
            cf.last_modified = file.last_modified,
            cf.imported_at = $imported_at

        WITH cf, file
        WHERE $project_id IS NOT NULL
        OPTIONAL MATCH (p:Project {id: $project_id})
        FOREACH (proj IN CASE WHEN p IS NOT NULL THEN [p] ELSE [] END |
            MERGE (cf)-[:BELONGS_TO_PROJECT]->(proj)
        )

        RETURN count(cf) as count
        """

        params = {
            "files": files,
            "project_id": project_id,
            "created_at": datetime.now().isoformat(),
            "imported_at": datetime.now().isoformat(),
        }

        result = self.conn.execute_write(query, params)
        return result[0]["count"] if result else 0

    def _import_classes(self, classes: List[Dict[str, Any]]) -> int:
        """Import class nodes.

        Args:
            classes: List of class dictionaries from blarify

        Returns:
            Number of classes imported
        """
        if not classes:
            return 0

        query = """
        UNWIND $classes as cls
        MERGE (c:Class {id: cls.id})
        ON CREATE SET
            c.name = cls.name,
            c.file_path = cls.file_path,
            c.line_number = cls.line_number,
            c.docstring = cls.docstring,
            c.is_abstract = cls.is_abstract,
            c.created_at = $created_at
        ON MATCH SET
            c.line_number = cls.line_number,
            c.docstring = cls.docstring

        WITH c, cls
        MATCH (cf:CodeFile {path: cls.file_path})
        MERGE (c)-[:DEFINED_IN]->(cf)

        RETURN count(c) as count
        """

        params = {
            "classes": classes,
            "created_at": datetime.now().isoformat(),
        }

        result = self.conn.execute_write(query, params)
        return result[0]["count"] if result else 0

    def _import_functions(self, functions: List[Dict[str, Any]]) -> int:
        """Import function nodes.

        Args:
            functions: List of function dictionaries from blarify

        Returns:
            Number of functions imported
        """
        if not functions:
            return 0

        query = """
        UNWIND $functions as func
        MERGE (f:Function {id: func.id})
        ON CREATE SET
            f.name = func.name,
            f.file_path = func.file_path,
            f.line_number = func.line_number,
            f.docstring = func.docstring,
            f.parameters = func.parameters,
            f.return_type = func.return_type,
            f.is_async = func.is_async,
            f.complexity = func.complexity,
            f.created_at = $created_at
        ON MATCH SET
            f.line_number = func.line_number,
            f.docstring = func.docstring,
            f.complexity = func.complexity

        WITH f, func
        MATCH (cf:CodeFile {path: func.file_path})
        MERGE (f)-[:DEFINED_IN]->(cf)

        // Link to class if class_id provided
        WITH f, func
        WHERE func.class_id IS NOT NULL
        OPTIONAL MATCH (c:Class {id: func.class_id})
        FOREACH (cls IN CASE WHEN c IS NOT NULL THEN [c] ELSE [] END |
            MERGE (f)-[:METHOD_OF]->(cls)
        )

        RETURN count(f) as count
        """

        params = {
            "functions": functions,
            "created_at": datetime.now().isoformat(),
        }

        result = self.conn.execute_write(query, params)
        return result[0]["count"] if result else 0

    def _import_imports(self, imports: List[Dict[str, Any]]) -> int:
        """Import import relationships.

        Args:
            imports: List of import dictionaries from blarify

        Returns:
            Number of imports created
        """
        if not imports:
            return 0

        query = """
        UNWIND $imports as imp
        MATCH (source:CodeFile {path: imp.source_file})
        MATCH (target:CodeFile {path: imp.target_file})
        MERGE (source)-[r:IMPORTS {
            symbol: imp.symbol
        }]->(target)
        ON CREATE SET
            r.alias = imp.alias,
            r.created_at = $created_at
        RETURN count(r) as count
        """

        params = {
            "imports": imports,
            "created_at": datetime.now().isoformat(),
        }

        result = self.conn.execute_write(query, params)
        return result[0]["count"] if result else 0

    def _import_relationships(self, relationships: List[Dict[str, Any]]) -> int:
        """Import code relationships (calls, inherits, references).

        Args:
            relationships: List of relationship dictionaries from blarify

        Returns:
            Number of relationships created
        """
        if not relationships:
            return 0

        count = 0

        for rel in relationships:
            rel_type = rel.get("type")
            source_id = rel.get("source_id")
            target_id = rel.get("target_id")

            if rel_type == "CALLS":
                count += self._create_call_relationship(source_id, target_id)
            elif rel_type == "INHERITS":
                count += self._create_inheritance_relationship(source_id, target_id)
            elif rel_type == "REFERENCES":
                count += self._create_reference_relationship(source_id, target_id)

        return count

    def _create_call_relationship(self, source_id: str, target_id: str) -> int:
        """Create CALLS relationship between functions."""
        query = """
        MATCH (source:Function {id: $source_id})
        MATCH (target:Function {id: $target_id})
        MERGE (source)-[r:CALLS]->(target)
        ON CREATE SET r.created_at = $created_at
        RETURN count(r) as count
        """

        params = {
            "source_id": source_id,
            "target_id": target_id,
            "created_at": datetime.now().isoformat(),
        }

        result = self.conn.execute_write(query, params)
        return result[0]["count"] if result else 0

    def _create_inheritance_relationship(self, source_id: str, target_id: str) -> int:
        """Create INHERITS relationship between classes."""
        query = """
        MATCH (source:Class {id: $source_id})
        MATCH (target:Class {id: $target_id})
        MERGE (source)-[r:INHERITS]->(target)
        ON CREATE SET r.created_at = $created_at
        RETURN count(r) as count
        """

        params = {
            "source_id": source_id,
            "target_id": target_id,
            "created_at": datetime.now().isoformat(),
        }

        result = self.conn.execute_write(query, params)
        return result[0]["count"] if result else 0

    def _create_reference_relationship(self, source_id: str, target_id: str) -> int:
        """Create REFERENCES relationship."""
        query = """
        MATCH (source {id: $source_id})
        MATCH (target {id: $target_id})
        MERGE (source)-[r:REFERENCES]->(target)
        ON CREATE SET r.created_at = $created_at
        RETURN count(r) as count
        """

        params = {
            "source_id": source_id,
            "target_id": target_id,
            "created_at": datetime.now().isoformat(),
        }

        result = self.conn.execute_write(query, params)
        return result[0]["count"] if result else 0

    def link_code_to_memories(self, project_id: Optional[str] = None) -> int:
        """Create relationships between code and memories.

        Links memories to relevant code files and functions based on:
        - File path in memory metadata
        - Function name in memory content
        - Tags matching code elements

        Args:
            project_id: Optional project scope

        Returns:
            Number of relationships created
        """
        logger.info("Linking code to memories")

        count = 0

        # Link memories to files based on metadata
        count += self._link_memories_to_files(project_id)

        # Link memories to functions based on content
        count += self._link_memories_to_functions(project_id)

        logger.info("Created %d code-memory relationships", count)
        return count

    def _link_memories_to_files(self, project_id: Optional[str] = None) -> int:
        """Link memories to code files based on metadata."""
        query = """
        MATCH (m:Memory)
        WHERE m.metadata CONTAINS 'file'

        WITH m,
             apoc.convert.fromJsonMap(m.metadata) AS meta
        WHERE meta.file IS NOT NULL

        MATCH (cf:CodeFile)
        WHERE cf.path CONTAINS meta.file OR meta.file CONTAINS cf.path

        MERGE (m)-[r:RELATES_TO_FILE]->(cf)
        ON CREATE SET r.created_at = $created_at

        RETURN count(r) as count
        """

        # Fallback query without APOC
        fallback_query = """
        MATCH (m:Memory), (cf:CodeFile)
        WHERE m.metadata CONTAINS cf.path

        MERGE (m)-[r:RELATES_TO_FILE]->(cf)
        ON CREATE SET r.created_at = $created_at

        RETURN count(r) as count
        """

        params = {"created_at": datetime.now().isoformat()}

        try:
            result = self.conn.execute_write(query, params)
            return result[0]["count"] if result else 0
        except Exception as e:
            logger.debug("APOC not available, using fallback: %s", e)
            result = self.conn.execute_write(fallback_query, params)
            return result[0]["count"] if result else 0

    def _link_memories_to_functions(self, project_id: Optional[str] = None) -> int:
        """Link memories to functions based on content matching."""
        query = """
        MATCH (m:Memory), (f:Function)
        WHERE m.content CONTAINS f.name

        MERGE (m)-[r:RELATES_TO_FUNCTION]->(f)
        ON CREATE SET r.created_at = $created_at

        RETURN count(r) as count
        """

        params = {"created_at": datetime.now().isoformat()}

        result = self.conn.execute_write(query, params)
        return result[0]["count"] if result else 0

    def query_code_context(
        self,
        memory_id: str,
        max_depth: int = 2,
    ) -> Dict[str, Any]:
        """Get code context for a memory.

        Args:
            memory_id: Memory ID to get context for
            max_depth: Maximum relationship depth to traverse

        Returns:
            Dictionary with related code files, functions, and classes
        """
        query = """
        MATCH (m:Memory {id: $memory_id})

        // Get related files
        OPTIONAL MATCH (m)-[:RELATES_TO_FILE]->(cf:CodeFile)
        WITH m, collect(DISTINCT {
            type: 'file',
            path: cf.path,
            language: cf.language,
            lines_of_code: cf.lines_of_code
        }) as files

        // Get related functions
        OPTIONAL MATCH (m)-[:RELATES_TO_FUNCTION]->(f:Function)
        WITH m, files, collect(DISTINCT {
            type: 'function',
            name: f.name,
            file_path: f.file_path,
            line_number: f.line_number,
            docstring: f.docstring,
            complexity: f.complexity
        }) as functions

        // Get related classes
        OPTIONAL MATCH (m)-[:RELATES_TO_FUNCTION]->(f:Function)-[:METHOD_OF]->(c:Class)
        WITH m, files, functions, collect(DISTINCT {
            type: 'class',
            name: c.name,
            file_path: c.file_path,
            line_number: c.line_number
        }) as classes

        RETURN {
            memory_id: m.id,
            files: files,
            functions: functions,
            classes: classes
        } as context
        """

        params = {
            "memory_id": memory_id,
            "max_depth": max_depth,
        }

        result = self.conn.execute_query(query, params)

        if result:
            return result[0]["context"]

        return {
            "memory_id": memory_id,
            "files": [],
            "functions": [],
            "classes": [],
        }

    def get_code_stats(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Get code graph statistics.

        Args:
            project_id: Optional project filter

        Returns:
            Dictionary with code statistics
        """
        query = """
        MATCH (cf:CodeFile)
        OPTIONAL MATCH (c:Class)-[:DEFINED_IN]->(cf)
        OPTIONAL MATCH (f:Function)-[:DEFINED_IN]->(cf)

        RETURN
            count(DISTINCT cf) as file_count,
            count(DISTINCT c) as class_count,
            count(DISTINCT f) as function_count,
            sum(cf.lines_of_code) as total_lines
        """

        result = self.conn.execute_query(query)

        if result:
            return result[0]

        return {
            "file_count": 0,
            "class_count": 0,
            "function_count": 0,
            "total_lines": 0,
        }

    def incremental_update(
        self,
        blarify_json_path: Path,
        project_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """Incrementally update code graph with changes.

        Uses MERGE to avoid duplicates and only update changed nodes.

        Args:
            blarify_json_path: Path to blarify output JSON
            project_id: Optional project ID

        Returns:
            Dictionary with update counts
        """
        logger.info("Performing incremental code graph update")
        return self.import_blarify_output(blarify_json_path, project_id)


def run_blarify(
    codebase_path: Path,
    output_path: Path,
    languages: Optional[List[str]] = None,
) -> bool:
    """Run blarify on a codebase to generate code graph.

    Args:
        codebase_path: Path to codebase to analyze
        output_path: Path to save blarify JSON output
        languages: Optional list of languages to analyze

    Returns:
        True if successful, False otherwise
    """
    logger.info("Running blarify on %s", codebase_path)

    try:
        # Check if blarify is installed
        subprocess.run(
            ["blarify", "--version"],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error(
            "blarify not found. Install with: pip install blarify\n"
            "See: https://github.com/blarApp/blarify"
        )
        return False

    # Build blarify command
    cmd = [
        "blarify",
        "analyze",
        str(codebase_path),
        "--output", str(output_path),
        "--format", "json",
    ]

    if languages:
        cmd.extend(["--languages", ",".join(languages)])

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        logger.info("Blarify completed successfully")
        logger.debug("Blarify output: %s", result.stdout)
        return True

    except subprocess.CalledProcessError as e:
        logger.error("Blarify failed: %s", e.stderr)
        return False
