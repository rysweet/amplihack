"""Blarify code graph integration with Kuzu memory system.

Integrates blarify-generated code graphs into the same Kuzu database
as the memory system, creating relationships between code and memories.

This is a port from the removed graph database.
Key differences:
- Uses Kuzu connector instead of the removed connector
- No MERGE - uses explicit INSERT pattern with checks
- Schema matches kuzu_backend.py (CodeFile, Class, Function nodes)
- Query syntax is 90% compatible with Cypher

Public API:
    KuzuCodeGraph: Blarify integration for Kuzu (replaces BlarifyIntegration)
    run_blarify: Standalone function to run blarify CLI
"""

import json
import logging
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .connector import KuzuConnector

logger = logging.getLogger(__name__)

# Try to import rich for progress indication
try:
    from rich.console import Console
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.text import Text

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    logger.debug("rich library not available, progress indicators will be disabled")


class KuzuCodeGraph:
    """Integrates blarify code graphs with Kuzu memory system.

    Handles:
    - Importing blarify-generated code graphs
    - Creating code node types (CodeFile, Class, Function)
    - Linking code to memories
    - Querying code context for memories
    - Incremental updates

    Schema:
        Uses node tables from kuzu_backend.py:
        - CodeFile (file_id, file_path, language, size_bytes, ...)
        - Class (class_id, class_name, docstring, is_abstract, ...)
        - Function (function_id, function_name, signature, is_async, ...)

        Relationship tables:
        - DEFINED_IN (Class → CodeFile)
        - DEFINED_IN (Function → CodeFile)
        - METHOD_OF (Function → Class)
        - CALLS (Function → Function)
        - INHERITS (Class → Class)
        - IMPORTS (CodeFile → CodeFile)
        - RELATES_TO_FILE_* (Memory → CodeFile)
        - RELATES_TO_FUNCTION_* (Memory → Function)
    """

    def __init__(self, connector: KuzuConnector):
        """Initialize blarify integration.

        Args:
            connector: Connected KuzuConnector instance
        """
        self.conn = connector
        self._ensure_code_graph_schema()

    def _ensure_code_graph_schema(self):
        """Ensure code graph schema tables exist in Kuzu database.

        Creates CodeFile, CodeClass, CodeFunction tables if they don't exist.
        Safe to call multiple times.
        """
        schema_queries = [
            """
            CREATE NODE TABLE IF NOT EXISTS CodeFile (
                file_id STRING,
                file_path STRING,
                language STRING,
                size_bytes INT64,
                last_modified TIMESTAMP,
                created_at TIMESTAMP,
                metadata STRING,
                PRIMARY KEY (file_id)
            )
            """,
            """
            CREATE NODE TABLE IF NOT EXISTS CodeClass (
                class_id STRING,
                class_name STRING,
                fully_qualified_name STRING,
                file_path STRING,
                line_number INT64,
                docstring STRING,
                is_abstract BOOLEAN,
                created_at TIMESTAMP,
                metadata STRING,
                PRIMARY KEY (class_id)
            )
            """,
            """
            CREATE NODE TABLE IF NOT EXISTS CodeFunction (
                function_id STRING,
                function_name STRING,
                fully_qualified_name STRING,
                signature STRING,
                file_path STRING,
                line_number INT64,
                parameters STRING,
                return_type STRING,
                docstring STRING,
                is_async BOOLEAN,
                cyclomatic_complexity INT64,
                created_at TIMESTAMP,
                metadata STRING,
                PRIMARY KEY (function_id)
            )
            """,
            """
            CREATE REL TABLE IF NOT EXISTS DEFINED_IN (
                FROM CodeFunction TO CodeFile,
                line_number INT64,
                end_line INT64
            )
            """,
            """
            CREATE REL TABLE IF NOT EXISTS CLASS_DEFINED_IN (
                FROM CodeClass TO CodeFile
            )
            """,
            """
            CREATE REL TABLE IF NOT EXISTS METHOD_OF (
                FROM CodeFunction TO CodeClass
            )
            """,
            """
            CREATE REL TABLE IF NOT EXISTS CALLS (
                FROM CodeFunction TO CodeFunction
            )
            """,
            """
            CREATE REL TABLE IF NOT EXISTS IMPORTS (
                FROM CodeFile TO CodeFile,
                symbol STRING,
                alias STRING
            )
            """,
        ]

        for query in schema_queries:
            try:
                self.conn.execute_write(query)
            except Exception as e:
                # Table might already exist
                logger.debug("Schema creation: %s", e)

    def run_blarify(
        self,
        codebase_path: str,
        languages: list[str] | None = None,
    ) -> dict[str, int]:
        """Run blarify and import results in one operation.

        Convenience method that:
        1. Runs blarify CLI to generate JSON
        2. Imports results into Kuzu
        3. Returns import counts

        Args:
            codebase_path: Path to codebase to analyze
            languages: Optional list of languages to analyze

        Returns:
            Dictionary with counts: {"files": N, "classes": N, "functions": N, ...}

        Raises:
            RuntimeError: If blarify execution fails
        """
        import os
        from tempfile import NamedTemporaryFile

        # Create temp file for blarify output
        with NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            # Run blarify using standalone function
            logger.info("Running blarify on %s", codebase_path)
            success = run_blarify(Path(codebase_path), tmp_path, languages)

            if not success:
                raise RuntimeError("Blarify execution failed")

            # Import results into Kuzu
            logger.info("Importing blarify results into Kuzu")
            counts = self.import_blarify_output(tmp_path, project_id=None)

            logger.info("Blarify import complete: %s", counts)
            return counts

        finally:
            # Cleanup temp file
            if tmp_path.exists():
                os.unlink(tmp_path)
                logger.debug("Cleaned up temporary file: %s", tmp_path)

    def import_blarify_output(
        self,
        blarify_json_path: Path,
        project_id: str | None = None,
    ) -> dict[str, int]:
        """Import blarify JSON output into Kuzu.

        Args:
            blarify_json_path: Path to blarify output JSON file
            project_id: Optional project ID to link code to (not yet implemented)

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

    def _import_files(self, files: list[dict[str, Any]], project_id: str | None = None) -> int:
        """Import code file nodes.

        Args:
            files: List of file dictionaries from blarify
            project_id: Optional project ID (not yet used)

        Returns:
            Number of files imported
        """
        if not files:
            return 0

        now = datetime.now()
        count = 0

        for file in files:
            try:
                # Generate file_id from path
                file_id = file.get("path", "")

                # Parse last_modified timestamp
                last_modified_str = file.get("last_modified")
                if last_modified_str and isinstance(last_modified_str, str):
                    # Parse ISO format timestamp
                    last_modified = datetime.fromisoformat(last_modified_str.replace("Z", "+00:00"))
                else:
                    last_modified = now

                # Check if file already exists
                existing = self.conn.execute_query(
                    """
                    MATCH (cf:CodeFile {file_id: $file_id})
                    RETURN cf.file_id
                    """,
                    {"file_id": file_id},
                )

                if existing:
                    # Update existing file
                    self.conn.execute_write(
                        """
                        MATCH (cf:CodeFile {file_id: $file_id})
                        SET
                            cf.size_bytes = $size_bytes,
                            cf.last_modified = $last_modified
                        """,
                        {
                            "file_id": file_id,
                            "size_bytes": file.get("lines_of_code", 0),
                            "last_modified": last_modified,
                        },
                    )
                else:
                    # Create new file
                    self.conn.execute_write(
                        """
                        CREATE (cf:CodeFile {
                            file_id: $file_id,
                            file_path: $file_path,
                            language: $language,
                            size_bytes: $size_bytes,
                            last_modified: $last_modified,
                            created_at: $created_at,
                            metadata: $metadata
                        })
                        """,
                        {
                            "file_id": file_id,
                            "file_path": file.get("path", ""),
                            "language": file.get("language", ""),
                            "size_bytes": file.get("lines_of_code", 0),
                            "last_modified": last_modified,
                            "created_at": now,
                            "metadata": json.dumps({}),
                        },
                    )

                count += 1

            except Exception as e:
                logger.warning("Failed to import file %s: %s", file.get("path"), e)

        return count

    def _import_classes(self, classes: list[dict[str, Any]]) -> int:
        """Import class nodes.

        Args:
            classes: List of class dictionaries from blarify

        Returns:
            Number of classes imported
        """
        if not classes:
            return 0

        now = datetime.now()
        count = 0

        for cls in classes:
            try:
                class_id = cls.get("id", "")
                file_path = cls.get("file_path", "")

                # Check if class exists
                existing = self.conn.execute_query(
                    """
                    MATCH (c:CodeClass {class_id: $class_id})
                    RETURN c.class_id
                    """,
                    {"class_id": class_id},
                )

                if existing:
                    # Update existing class
                    self.conn.execute_write(
                        """
                        MATCH (c:CodeClass {class_id: $class_id})
                        SET
                            c.docstring = $docstring,
                            c.metadata = $metadata
                        """,
                        {
                            "class_id": class_id,
                            "docstring": cls.get("docstring", ""),
                            "metadata": json.dumps({"line_number": cls.get("line_number", 0)}),
                        },
                    )
                else:
                    # Create new class
                    self.conn.execute_write(
                        """
                        CREATE (c:CodeClass {
                            class_id: $class_id,
                            class_name: $class_name,
                            fully_qualified_name: $fully_qualified_name,
                            docstring: $docstring,
                            is_abstract: $is_abstract,
                            created_at: $created_at,
                            metadata: $metadata
                        })
                        """,
                        {
                            "class_id": class_id,
                            "class_name": cls.get("name", ""),
                            "fully_qualified_name": cls.get("id", ""),
                            "docstring": cls.get("docstring", ""),
                            "is_abstract": cls.get("is_abstract", False),
                            "created_at": now,
                            "metadata": json.dumps({"line_number": cls.get("line_number", 0)}),
                        },
                    )

                # Create CLASS_DEFINED_IN relationship to file
                if file_path:
                    # Check if relationship exists
                    rel_exists = self.conn.execute_query(
                        """
                        MATCH (c:CodeClass {class_id: $class_id})-[r:CLASS_DEFINED_IN]->(cf:CodeFile {file_id: $file_id})
                        RETURN count(r) as cnt
                        """,
                        {"class_id": class_id, "file_id": file_path},
                    )

                    if not rel_exists or rel_exists[0]["cnt"] == 0:
                        self.conn.execute_write(
                            """
                            MATCH (c:CodeClass {class_id: $class_id})
                            MATCH (cf:CodeFile {file_id: $file_id})
                            CREATE (c)-[:CLASS_DEFINED_IN]->(cf)
                            """,
                            {
                                "class_id": class_id,
                                "file_id": file_path,
                            },
                        )

                count += 1

            except Exception as e:
                logger.warning("Failed to import class %s: %s", cls.get("name"), e)

        return count

    def _import_functions(self, functions: list[dict[str, Any]]) -> int:
        """Import function nodes.

        Args:
            functions: List of function dictionaries from blarify

        Returns:
            Number of functions imported
        """
        if not functions:
            return 0

        now = datetime.now()
        count = 0

        for func in functions:
            try:
                function_id = func.get("id", "")
                file_path = func.get("file_path", "")
                class_id = func.get("class_id")

                # Check if function exists
                existing = self.conn.execute_query(
                    """
                    MATCH (f:CodeFunction {function_id: $function_id})
                    RETURN f.function_id
                    """,
                    {"function_id": function_id},
                )

                if existing:
                    # Update existing function
                    self.conn.execute_write(
                        """
                        MATCH (f:CodeFunction {function_id: $function_id})
                        SET
                            f.docstring = $docstring,
                            f.cyclomatic_complexity = $cyclomatic_complexity,
                            f.metadata = $metadata
                        """,
                        {
                            "function_id": function_id,
                            "docstring": func.get("docstring", ""),
                            "cyclomatic_complexity": func.get("complexity", 0),
                            "metadata": json.dumps(
                                {
                                    "line_number": func.get("line_number", 0),
                                    "parameters": func.get("parameters", []),
                                    "return_type": func.get("return_type", ""),
                                }
                            ),
                        },
                    )
                else:
                    # Create new function
                    self.conn.execute_write(
                        """
                        CREATE (f:CodeFunction {
                            function_id: $function_id,
                            function_name: $function_name,
                            fully_qualified_name: $fully_qualified_name,
                            signature: $signature,
                            docstring: $docstring,
                            is_async: $is_async,
                            cyclomatic_complexity: $cyclomatic_complexity,
                            created_at: $created_at,
                            metadata: $metadata
                        })
                        """,
                        {
                            "function_id": function_id,
                            "function_name": func.get("name", ""),
                            "fully_qualified_name": func.get("id", ""),
                            "signature": f"{func.get('name', '')}({', '.join(func.get('parameters', []))})",
                            "docstring": func.get("docstring", ""),
                            "is_async": func.get("is_async", False),
                            "cyclomatic_complexity": func.get("complexity", 0),
                            "created_at": now,
                            "metadata": json.dumps(
                                {
                                    "line_number": func.get("line_number", 0),
                                    "parameters": func.get("parameters", []),
                                    "return_type": func.get("return_type", ""),
                                }
                            ),
                        },
                    )

                # Create DEFINED_IN relationship to file
                if file_path:
                    rel_exists = self.conn.execute_query(
                        """
                        MATCH (f:CodeFunction {function_id: $function_id})-[r:DEFINED_IN]->(cf:CodeFile {file_id: $file_id})
                        RETURN count(r) as cnt
                        """,
                        {"function_id": function_id, "file_id": file_path},
                    )

                    if not rel_exists or rel_exists[0]["cnt"] == 0:
                        self.conn.execute_write(
                            """
                            MATCH (f:CodeFunction {function_id: $function_id})
                            MATCH (cf:CodeFile {file_id: $file_id})
                            CREATE (f)-[:DEFINED_IN {
                                line_number: $line_number,
                                end_line: $end_line
                            }]->(cf)
                            """,
                            {
                                "function_id": function_id,
                                "file_id": file_path,
                                "line_number": func.get("line_number", 0),
                                "end_line": func.get("line_number", 0),
                            },
                        )

                # Create METHOD_OF relationship if function belongs to a class
                if class_id:
                    rel_exists = self.conn.execute_query(
                        """
                        MATCH (f:CodeFunction {function_id: $function_id})-[r:METHOD_OF]->(c:Class {class_id: $class_id})
                        RETURN count(r) as cnt
                        """,
                        {"function_id": function_id, "class_id": class_id},
                    )

                    if not rel_exists or rel_exists[0]["cnt"] == 0:
                        self.conn.execute_write(
                            """
                            MATCH (f:CodeFunction {function_id: $function_id})
                            MATCH (c:CodeClass {class_id: $class_id})
                            CREATE (f)-[:METHOD_OF {
                                method_type: $method_type,
                                visibility: $visibility
                            }]->(c)
                            """,
                            {
                                "function_id": function_id,
                                "class_id": class_id,
                                "method_type": "instance",
                                "visibility": "public",
                            },
                        )

                count += 1

            except Exception as e:
                logger.warning("Failed to import function %s: %s", func.get("name"), e)

        return count

    def _import_imports(self, imports: list[dict[str, Any]]) -> int:
        """Import import relationships.

        Args:
            imports: List of import dictionaries from blarify

        Returns:
            Number of imports created
        """
        if not imports:
            return 0

        count = 0

        for imp in imports:
            try:
                source_file = imp.get("source_file", "")
                target_file = imp.get("target_file", "")
                symbol = imp.get("symbol", "")

                if not source_file or not target_file:
                    continue

                # Check if relationship exists
                rel_exists = self.conn.execute_query(
                    """
                    MATCH (source:CodeFile {file_id: $source_file})-[r:IMPORTS]->(target:CodeFile {file_id: $target_file})
                    WHERE r.import_type = $symbol
                    RETURN count(r) as cnt
                    """,
                    {"source_file": source_file, "target_file": target_file, "symbol": symbol},
                )

                if not rel_exists or rel_exists[0]["cnt"] == 0:
                    self.conn.execute_write(
                        """
                        MATCH (source:CodeFile {file_id: $source_file})
                        MATCH (target:CodeFile {file_id: $target_file})
                        CREATE (source)-[:IMPORTS {
                            import_type: $import_type,
                            alias: $alias
                        }]->(target)
                        """,
                        {
                            "source_file": source_file,
                            "target_file": target_file,
                            "import_type": symbol,
                            "alias": imp.get("alias", ""),
                        },
                    )
                    count += 1

            except Exception as e:
                logger.warning("Failed to import relationship: %s", e)

        return count

    def _import_relationships(self, relationships: list[dict[str, Any]]) -> int:
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

            # Skip relationships with missing IDs
            if not source_id or not target_id:
                continue

            if rel_type == "CALLS":
                count += self._create_call_relationship(source_id, target_id)
            elif rel_type == "INHERITS":
                count += self._create_inheritance_relationship(source_id, target_id)
            elif rel_type == "REFERENCES":
                count += self._create_reference_relationship(source_id, target_id)

        return count

    def _create_call_relationship(self, source_id: str, target_id: str) -> int:
        """Create CALLS relationship between functions."""
        try:
            # Check if relationship exists
            rel_exists = self.conn.execute_query(
                """
                MATCH (source:Function {function_id: $source_id})-[r:CALLS]->(target:Function {function_id: $target_id})
                RETURN count(r) as cnt
                """,
                {"source_id": source_id, "target_id": target_id},
            )

            if rel_exists and rel_exists[0]["cnt"] > 0:
                return 0

            self.conn.execute_write(
                """
                MATCH (source:Function {function_id: $source_id})
                MATCH (target:Function {function_id: $target_id})
                CREATE (source)-[:CALLS {
                    call_count: $call_count,
                    context: $context
                }]->(target)
                """,
                {
                    "source_id": source_id,
                    "target_id": target_id,
                    "call_count": 1,
                    "context": "",
                },
            )
            return 1

        except Exception as e:
            logger.warning("Failed to create CALLS relationship: %s", e)
            return 0

    def _create_inheritance_relationship(self, source_id: str, target_id: str) -> int:
        """Create INHERITS relationship between classes."""
        try:
            # Check if relationship exists
            rel_exists = self.conn.execute_query(
                """
                MATCH (source:Class {class_id: $source_id})-[r:INHERITS]->(target:Class {class_id: $target_id})
                RETURN count(r) as cnt
                """,
                {"source_id": source_id, "target_id": target_id},
            )

            if rel_exists and rel_exists[0]["cnt"] > 0:
                return 0

            self.conn.execute_write(
                """
                MATCH (source:Class {class_id: $source_id})
                MATCH (target:Class {class_id: $target_id})
                CREATE (source)-[:INHERITS {
                    inheritance_order: $inheritance_order,
                    inheritance_type: $inheritance_type
                }]->(target)
                """,
                {
                    "source_id": source_id,
                    "target_id": target_id,
                    "inheritance_order": 0,
                    "inheritance_type": "single",
                },
            )
            return 1

        except Exception as e:
            logger.warning("Failed to create INHERITS relationship: %s", e)
            return 0

    def _create_reference_relationship(self, source_id: str, target_id: str) -> int:
        """Create REFERENCES_CLASS relationship."""
        try:
            # Check if relationship exists
            rel_exists = self.conn.execute_query(
                """
                MATCH (source:Function {function_id: $source_id})-[r:REFERENCES_CLASS]->(target:Class {class_id: $target_id})
                RETURN count(r) as cnt
                """,
                {"source_id": source_id, "target_id": target_id},
            )

            if rel_exists and rel_exists[0]["cnt"] > 0:
                return 0

            self.conn.execute_write(
                """
                MATCH (source:Function {function_id: $source_id})
                MATCH (target:Class {class_id: $target_id})
                CREATE (source)-[:REFERENCES_CLASS {
                    reference_type: $reference_type,
                    context: $context
                }]->(target)
                """,
                {
                    "source_id": source_id,
                    "target_id": target_id,
                    "reference_type": "usage",
                    "context": "",
                },
            )
            return 1

        except Exception as e:
            logger.warning("Failed to create REFERENCES relationship: %s", e)
            return 0

    def link_code_to_memories(self, project_id: str | None = None) -> int:
        """Create relationships between code and memories.

        Links memories to relevant code files and functions based on:
        - File path in memory metadata
        - Function name in memory content
        - Tags matching code elements

        Args:
            project_id: Optional project scope (not yet implemented)

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

    def _link_memories_to_files(self, project_id: str | None = None) -> int:
        """Link memories to code files based on metadata."""
        count = 0
        now = datetime.now()

        try:
            # Query all memory types that could link to files
            for memory_type in [
                "EpisodicMemory",
                "SemanticMemory",
                "ProceduralMemory",
                "ProspectiveMemory",
                "WorkingMemory",
            ]:
                rel_table = f"RELATES_TO_FILE_{memory_type.replace('Memory', '').upper()}"

                # Get memories with metadata containing file paths
                memories = self.conn.execute_query(
                    f"""
                    MATCH (m:{memory_type})
                    WHERE m.metadata IS NOT NULL
                    RETURN m.memory_id, m.metadata
                    """
                )

                for mem in memories:
                    try:
                        memory_id = mem["m.memory_id"]
                        metadata_str = mem["m.metadata"]

                        if not metadata_str:
                            continue

                        metadata = json.loads(metadata_str)
                        file_path = metadata.get("file")

                        if not file_path:
                            continue

                        # Find matching code files
                        files = self.conn.execute_query(
                            """
                            MATCH (cf:CodeFile)
                            WHERE cf.file_path CONTAINS $file_path OR $file_path CONTAINS cf.file_path
                            RETURN cf.file_id
                            """,
                            {"file_path": file_path},
                        )

                        for file in files:
                            file_id = file["cf.file_id"]

                            # Check if relationship exists
                            rel_exists = self.conn.execute_query(
                                f"""
                                MATCH (m:{memory_type} {{memory_id: $memory_id}})-[r:{rel_table}]->(cf:CodeFile {{file_id: $file_id}})
                                RETURN count(r) as cnt
                                """,
                                {"memory_id": memory_id, "file_id": file_id},
                            )

                            if not rel_exists or rel_exists[0]["cnt"] == 0:
                                self.conn.execute_write(
                                    f"""
                                    MATCH (m:{memory_type} {{memory_id: $memory_id}})
                                    MATCH (cf:CodeFile {{file_id: $file_id}})
                                    CREATE (m)-[:{rel_table} {{
                                        relevance_score: $relevance_score,
                                        context: $context,
                                        timestamp: $timestamp
                                    }}]->(cf)
                                    """,
                                    {
                                        "memory_id": memory_id,
                                        "file_id": file_id,
                                        "relevance_score": 1.0,
                                        "context": "metadata_file_match",
                                        "timestamp": now,
                                    },
                                )
                                count += 1

                    except Exception as e:
                        logger.debug("Error linking memory to file: %s", e)

        except Exception as e:
            logger.warning("Error in _link_memories_to_files: %s", e)

        return count

    def _link_memories_to_functions(self, project_id: str | None = None) -> int:
        """Link memories to functions based on content matching."""
        count = 0
        now = datetime.now()

        try:
            # Query all memory types
            for memory_type in [
                "EpisodicMemory",
                "SemanticMemory",
                "ProceduralMemory",
                "ProspectiveMemory",
                "WorkingMemory",
            ]:
                rel_table = f"RELATES_TO_FUNCTION_{memory_type.replace('Memory', '').upper()}"

                # Get memories with content
                memories = self.conn.execute_query(
                    f"""
                    MATCH (m:{memory_type})
                    WHERE m.content IS NOT NULL
                    RETURN m.memory_id, m.content
                    """
                )

                for mem in memories:
                    try:
                        memory_id = mem["m.memory_id"]
                        content = mem["m.content"]

                        if not content:
                            continue

                        # Find functions mentioned in content
                        functions = self.conn.execute_query(
                            """
                            MATCH (f:Function)
                            WHERE $content CONTAINS f.function_name
                            RETURN f.function_id, f.function_name
                            """,
                            {"content": content},
                        )

                        for func in functions:
                            function_id = func["f.function_id"]

                            # Check if relationship exists
                            rel_exists = self.conn.execute_query(
                                f"""
                                MATCH (m:{memory_type} {{memory_id: $memory_id}})-[r:{rel_table}]->(f:Function {{function_id: $function_id}})
                                RETURN count(r) as cnt
                                """,
                                {"memory_id": memory_id, "function_id": function_id},
                            )

                            if not rel_exists or rel_exists[0]["cnt"] == 0:
                                self.conn.execute_write(
                                    f"""
                                    MATCH (m:{memory_type} {{memory_id: $memory_id}})
                                    MATCH (f:Function {{function_id: $function_id}})
                                    CREATE (m)-[:{rel_table} {{
                                        relevance_score: $relevance_score,
                                        context: $context,
                                        timestamp: $timestamp
                                    }}]->(f)
                                    """,
                                    {
                                        "memory_id": memory_id,
                                        "function_id": function_id,
                                        "relevance_score": 0.8,
                                        "context": "content_name_match",
                                        "timestamp": now,
                                    },
                                )
                                count += 1

                    except Exception as e:
                        logger.debug("Error linking memory to function: %s", e)

        except Exception as e:
            logger.warning("Error in _link_memories_to_functions: %s", e)

        return count

    def query_code_context(
        self,
        memory_id: str,
        max_depth: int = 2,
    ) -> dict[str, Any]:
        """Get code context for a memory.

        Args:
            memory_id: Memory ID to get context for
            max_depth: Maximum relationship depth to traverse (not yet used)

        Returns:
            Dictionary with related code files, functions, and classes
        """
        # Try to find memory in each memory type
        memory_type = None
        for mtype in [
            "EpisodicMemory",
            "SemanticMemory",
            "ProceduralMemory",
            "ProspectiveMemory",
            "WorkingMemory",
        ]:
            result = self.conn.execute_query(
                f"""
                MATCH (m:{mtype} {{memory_id: $memory_id}})
                RETURN m.memory_id
                """,
                {"memory_id": memory_id},
            )
            if result:
                memory_type = mtype
                break

        if not memory_type:
            return {
                "memory_id": memory_id,
                "files": [],
                "functions": [],
                "classes": [],
            }

        files = []
        functions = []
        classes = []

        # Get related files
        rel_table = f"RELATES_TO_FILE_{memory_type.replace('Memory', '').upper()}"
        try:
            file_results = self.conn.execute_query(
                f"""
                MATCH (m:{memory_type} {{memory_id: $memory_id}})-[:{rel_table}]->(cf:CodeFile)
                RETURN cf.file_path, cf.language, cf.size_bytes
                """,
                {"memory_id": memory_id},
            )

            for row in file_results:
                files.append(
                    {
                        "type": "file",
                        "path": row["cf.file_path"],
                        "language": row["cf.language"],
                        "size_bytes": row["cf.size_bytes"],
                    }
                )
        except Exception as e:
            logger.debug("Error querying related files: %s", e)

        # Get related functions
        rel_table = f"RELATES_TO_FUNCTION_{memory_type.replace('Memory', '').upper()}"
        try:
            func_results = self.conn.execute_query(
                f"""
                MATCH (m:{memory_type} {{memory_id: $memory_id}})-[:{rel_table}]->(f:Function)
                RETURN f.function_name, f.signature, f.docstring, f.cyclomatic_complexity
                """,
                {"memory_id": memory_id},
            )

            for row in func_results:
                functions.append(
                    {
                        "type": "function",
                        "name": row["f.function_name"],
                        "signature": row["f.signature"],
                        "docstring": row["f.docstring"],
                        "complexity": row["f.cyclomatic_complexity"],
                    }
                )
        except Exception as e:
            logger.debug("Error querying related functions: %s", e)

        # Get related classes (via functions)
        try:
            class_results = self.conn.execute_query(
                f"""
                MATCH (m:{memory_type} {{memory_id: $memory_id}})-[:{rel_table}]->(f:Function)-[:METHOD_OF]->(c:Class)
                RETURN DISTINCT c.class_name, c.fully_qualified_name, c.docstring
                """,
                {"memory_id": memory_id},
            )

            for row in class_results:
                classes.append(
                    {
                        "type": "class",
                        "name": row["c.class_name"],
                        "fully_qualified_name": row["c.fully_qualified_name"],
                        "docstring": row["c.docstring"],
                    }
                )
        except Exception as e:
            logger.debug("Error querying related classes: %s", e)

        return {
            "memory_id": memory_id,
            "files": files,
            "functions": functions,
            "classes": classes,
        }

    def get_code_stats(self, project_id: str | None = None) -> dict[str, Any]:
        """Get code graph statistics.

        Args:
            project_id: Optional project filter (not yet implemented)

        Returns:
            Dictionary with code statistics
        """
        try:
            stats = {}

            # Count files
            result = self.conn.execute_query("MATCH (cf:CodeFile) RETURN count(cf) as cnt")
            stats["file_count"] = result[0]["cnt"] if result else 0

            # Count classes
            result = self.conn.execute_query("MATCH (c:Class) RETURN count(c) as cnt")
            stats["class_count"] = result[0]["cnt"] if result else 0

            # Count functions
            result = self.conn.execute_query("MATCH (f:Function) RETURN count(f) as cnt")
            stats["function_count"] = result[0]["cnt"] if result else 0

            # Total lines of code (size_bytes as proxy)
            result = self.conn.execute_query(
                "MATCH (cf:CodeFile) RETURN sum(cf.size_bytes) as total"
            )
            stats["total_lines"] = result[0]["total"] if result else 0

            return stats

        except Exception as e:
            logger.error("Error getting code stats: %s", e)
            return {
                "file_count": 0,
                "class_count": 0,
                "function_count": 0,
                "total_lines": 0,
            }

    def incremental_update(
        self,
        blarify_json_path: Path,
        project_id: str | None = None,
    ) -> dict[str, int]:
        """Incrementally update code graph with changes.

        Uses upsert pattern to avoid duplicates and only update changed nodes.

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
    languages: list[str] | None = None,
) -> bool:
    """Run blarify on a codebase using vendored blarify with Kuzu backend.

    Uses the vendored blarify package with KuzuManager to analyze the codebase
    and store results directly in a Kuzu database, then exports to JSON.

    Args:
        codebase_path: Path to codebase to analyze
        output_path: Path to save blarify JSON output
        languages: Optional list of languages to analyze

    Returns:
        True if successful, False otherwise
    """
    logger.info("Running vendored blarify on %s with Kuzu backend", codebase_path)

    try:
        # Add vendored blarify to path for imports
        import sys

        vendor_path = Path(__file__).parent.parent.parent / "vendor"
        if str(vendor_path) not in sys.path:
            sys.path.insert(0, str(vendor_path))

        # Import vendored blarify components
        # Create temporary Kuzu database path (don't create directory - Kuzu will do it)
        import tempfile

        from blarify.prebuilt.graph_builder import GraphBuilder
        from blarify.repositories.graph_db_manager.kuzu_manager import KuzuManager

        temp_kuzu_dir = (
            Path(tempfile.gettempdir())
            / f"blarify_kuzu_{tempfile._get_candidate_names().__next__()}"
        )

        # Initialize Kuzu manager
        repo_id = codebase_path.name or "amplihack"
        entity_id = "amplihack"

        db_manager = KuzuManager(
            repo_id=repo_id,
            entity_id=entity_id,
            db_path=str(temp_kuzu_dir),
        )

        # Build the graph using vendored blarify (it manages LSP and file iteration internally)
        logger.info("Building code graph with vendored blarify...")
        graph_builder = GraphBuilder(
            root_path=str(codebase_path),
            db_manager=db_manager,
            only_hierarchy=False,
            extensions_to_skip=[".json", ".xml", ".md", ".txt"] if not languages else [],
            names_to_skip=[
                "__pycache__",
                "node_modules",
                ".git",
                ".github",
                "venv",
                ".venv",
                "vendor",
            ],
        )

        # Build and save graph directly to Kuzu
        graph_builder.build()

        logger.info("Blarify analysis complete, data saved to Kuzu")

        # Export from Kuzu to JSON format expected by amplihack
        output_data = {
            "files": [],
            "classes": [],
            "functions": [],
            "relationships": [],
        }

        # Query Kuzu database to extract data with all properties needed by import
        # Files
        file_results = db_manager.query("""
            MATCH (n:NODE)
            WHERE n.node_type = 'FILE'
            RETURN n.path as path, n.name as name
        """)
        output_data["files"] = [{"path": r["path"], "name": r["name"]} for r in file_results]

        # Classes - query all properties from NODE table
        class_results = db_manager.conn.execute("""
            MATCH (n:NODE)
            WHERE n.node_type = 'CLASS'
            RETURN n
        """)
        classes = []
        while class_results.has_next():
            row = class_results.get_next()
            node = row[0]  # First column is the node
            # Extract properties from the node dict
            classes.append(
                {
                    "id": node.get("node_id", ""),
                    "name": node.get("name", ""),
                    "file_path": node.get("path", ""),
                    "line_number": node.get("start_line", 0),
                    "docstring": node.get("text", "")[:200] if node.get("text") else "",
                }
            )
        output_data["classes"] = classes

        # Functions - query all properties
        func_results = db_manager.conn.execute("""
            MATCH (n:NODE)
            WHERE n.node_type = 'FUNCTION'
            RETURN n
        """)
        functions = []
        while func_results.has_next():
            row = func_results.get_next()
            node = row[0]
            functions.append(
                {
                    "id": node.get("node_id", ""),
                    "name": node.get("name", ""),
                    "file_path": node.get("path", ""),
                    "line_number": node.get("start_line", 0),
                    "docstring": node.get("text", "")[:200] if node.get("text") else "",
                    "parameters": [],  # Would need parsing from text
                    "complexity": 0,  # Not available in basic parse
                }
            )
        output_data["functions"] = functions

        # Relationships - query each type separately (Kuzu doesn't have type() function)
        all_relationships = []

        # Query CONTAINS relationships
        try:
            contains_results = db_manager.query("""
                MATCH (source:NODE)-[:CONTAINS]->(target:NODE)
                RETURN source.node_id as source_id, target.node_id as target_id
            """)
            for r in contains_results:
                all_relationships.append(
                    {"type": "CONTAINS", "source_id": r["source_id"], "target_id": r["target_id"]}
                )
        except Exception:
            pass

        # Query CALLS relationships
        try:
            calls_results = db_manager.query("""
                MATCH (source:NODE)-[:CALLS]->(target:NODE)
                RETURN source.node_id as source_id, target.node_id as target_id
            """)
            for r in calls_results:
                all_relationships.append(
                    {"type": "CALLS", "source_id": r["source_id"], "target_id": r["target_id"]}
                )
        except Exception:
            pass

        # Query REFERENCES relationships
        try:
            ref_results = db_manager.query("""
                MATCH (source:NODE)-[:REFERENCES]->(target:NODE)
                RETURN source.node_id as source_id, target.node_id as target_id
            """)
            for r in ref_results:
                all_relationships.append(
                    {"type": "REFERENCES", "source_id": r["source_id"], "target_id": r["target_id"]}
                )
        except Exception:
            pass

        output_data["relationships"] = all_relationships

        # Write JSON output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)

        logger.info("Blarify output written to %s", output_path)

        # Cleanup
        db_manager.close()

        # CRITICAL: Clean up temp Kuzu database to prevent leaks
        import shutil
        import time

        # Give Kuzu time to fully close files before cleanup
        time.sleep(0.1)

        try:
            if temp_kuzu_dir.exists():
                if temp_kuzu_dir.is_dir():
                    # It's a directory - remove tree
                    shutil.rmtree(temp_kuzu_dir, ignore_errors=False)
                    logger.debug("Cleaned up temp Kuzu directory: %s", temp_kuzu_dir)
                else:
                    # It's a file - remove file
                    temp_kuzu_dir.unlink()
                    logger.debug("Cleaned up temp Kuzu file: %s", temp_kuzu_dir)
            else:
                logger.debug("Temp Kuzu path already cleaned: %s", temp_kuzu_dir)
        except Exception as e:
            logger.warning("Error during cleanup of %s: %s", temp_kuzu_dir, e)
            # Best effort cleanup
            try:
                if temp_kuzu_dir.exists() and temp_kuzu_dir.is_dir():
                    shutil.rmtree(temp_kuzu_dir, ignore_errors=True)
                elif temp_kuzu_dir.exists():
                    temp_kuzu_dir.unlink(missing_ok=True)
            except OSError:
                pass  # Ignore cleanup errors

        return True

    except ImportError as e:
        logger.error("Failed to import vendored blarify: %s", e)
        logger.error("Vendored blarify may not be properly installed")
        return False
    except Exception as e:
        logger.error("Blarify analysis failed: %s", e)
        import traceback

        logger.debug("Traceback: %s", traceback.format_exc())
        return False


def _run_with_progress_indicator(
    cmd: list[str], codebase_path: Path
) -> subprocess.CompletedProcess:
    """Run subprocess with a rich progress indicator.

    Args:
        cmd: Command to execute
        codebase_path: Path being analyzed (for display)

    Returns:
        CompletedProcess instance with results
    """
    console = Console()
    process_result = None
    process_error = None
    result_lock = threading.Lock()

    def run_subprocess():
        """Run the subprocess in a separate thread."""
        nonlocal process_result, process_error
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )
            with result_lock:
                process_result = result
        except Exception as e:
            with result_lock:
                process_error = e

    # Start subprocess in background thread (not daemon - we want proper cleanup)
    thread = threading.Thread(target=run_subprocess)
    thread.start()

    # Show progress indicator while subprocess runs
    spinner = Spinner(
        "dots", text=Text(f"Indexing codebase: {codebase_path.name}...", style="cyan")
    )

    try:
        with Live(spinner, console=console, refresh_per_second=10) as live:
            start_time = time.time()
            while thread.is_alive():
                elapsed = time.time() - start_time
                elapsed_str = f"{int(elapsed)}s"

                # Update spinner text with elapsed time
                spinner.update(
                    text=Text(
                        f"Indexing codebase: {codebase_path.name}... ({elapsed_str} elapsed)",
                        style="cyan",
                    )
                )
                live.update(spinner)

                # Check every 100ms
                thread.join(timeout=0.1)
    finally:
        # Ensure thread cleanup even if Live context fails
        thread.join(timeout=5.0)
        if thread.is_alive():
            logger.warning("Background thread did not complete cleanly within timeout")

    # Check if there was an error (with lock protection)
    with result_lock:
        if process_error:
            raise process_error

        if process_result is None:
            raise RuntimeError("Subprocess did not complete successfully")

        # Show completion message
        if process_result.returncode == 0:
            console.print(f"[green]✓[/green] Blarify indexing completed for {codebase_path.name}")

        return process_result


__all__ = [
    "KuzuCodeGraph",
    "run_blarify",
]
