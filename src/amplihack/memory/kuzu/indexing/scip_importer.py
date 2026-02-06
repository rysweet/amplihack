"""SCIP protobuf importer for Kuzu graph database.

Reads index.scip files created by scip-python/scip-typescript and imports
the code symbols into Kuzu graph database.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ..connector import KuzuConnector

logger = logging.getLogger(__name__)

# Import SCIP protobuf bindings with fallback
scip_available = False
scip = None

if TYPE_CHECKING:
    from amplihack.vendor.blarify import scip_pb2 as scip  # type: ignore

    scip_available = True
else:
    # Try multiple import paths for compatibility
    import_attempts = [
        (
            "from amplihack.vendor.blarify import scip_pb2 as scip",
            lambda: __import__("amplihack.vendor.blarify.scip_pb2", fromlist=[""]),
        ),
        (
            "from blarify import scip_pb2 as scip",
            lambda: __import__("blarify.scip_pb2", fromlist=[""]),
        ),
    ]

    for description, import_func in import_attempts:
        try:
            scip = import_func()
            scip_available = True
            logger.debug(f"Successfully imported SCIP using: {description}")
            break
        except (ImportError, ModuleNotFoundError, ValueError) as e:
            logger.debug(f"Import attempt failed ({description}): {e}")
            continue

if not scip_available:
    logger.error("SCIP protobuf bindings not found - cannot import SCIP indexes")


class ScipImporter:
    """Imports SCIP protobuf indexes into Kuzu graph database."""

    def __init__(self, connector: KuzuConnector):
        """Initialize importer with Kuzu connector.

        Args:
            connector: Connected KuzuConnector instance
        """
        self.conn = connector
        self._ensure_schema()

    def _ensure_schema(self):
        """Ensure Kuzu schema exists for code graph nodes."""
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
        ]

        for query in schema_queries:
            try:
                self.conn.execute_write(query)
            except Exception as e:
                logger.debug("Schema creation: %s", e)

    def import_from_file(
        self,
        scip_index_path: str,
        project_root: str,
        language: str,
    ) -> dict[str, Any]:
        """Import SCIP index file into Kuzu database.

        Args:
            scip_index_path: Path to index.scip file
            project_root: Root path of the project (for relative path resolution)
            language: Primary language being indexed

        Returns:
            Dictionary with import statistics:
            {
                "files": int,
                "functions": int,
                "classes": int,
                "symbols": int,
                "relationships": int
            }
        """
        logger.info("Importing SCIP index from %s", scip_index_path)

        # Read and parse SCIP protobuf file
        index_path = Path(scip_index_path)
        if not index_path.exists():
            raise FileNotFoundError(f"SCIP index not found: {scip_index_path}")

        with open(index_path, "rb") as f:
            index_data = f.read()

        if not scip_available or scip is None:
            raise RuntimeError("SCIP protobuf bindings not available")

        index = scip.Index()
        index.ParseFromString(index_data)

        logger.info(
            "Parsed SCIP index: %d documents, %d external symbols",
            len(index.documents),
            len(index.external_symbols),
        )

        stats = {
            "files": 0,
            "functions": 0,
            "classes": 0,
            "symbols": 0,
            "relationships": 0,
        }

        project_path = Path(project_root)

        # Batch collect all nodes before inserting
        files_to_insert = []
        functions_to_insert = []
        classes_to_insert = []

        logger.info("Extracting nodes from SCIP index...")

        for doc in index.documents:
            file_path = (project_path / doc.relative_path).as_posix()
            files_to_insert.append((file_path, doc.language or language))
            stats["files"] += 1

            # Process symbols in this document
            for symbol_info in doc.symbols:
                symbol_name = symbol_info.symbol
                kind = symbol_info.kind

                # Determine if this is a function or class based on symbol pattern
                # (scip-python sets kind=0 for everything, so we use naming patterns)
                if self._is_function_kind(kind, symbol_name):
                    line_number = self._find_definition_line(symbol_name, doc.occurrences)
                    functions_to_insert.append((symbol_info, file_path, line_number))
                    stats["functions"] += 1
                elif self._is_class_kind(kind, symbol_name):
                    line_number = self._find_definition_line(symbol_name, doc.occurrences)
                    classes_to_insert.append((symbol_info, file_path, line_number))
                    stats["classes"] += 1

                stats["symbols"] += 1

            # Count relationships
            for occurrence in doc.occurrences:
                if occurrence.symbol:
                    stats["relationships"] += 1

        # Batch insert all nodes
        logger.info(f"Inserting {len(files_to_insert)} files...")
        self._batch_insert_files(files_to_insert)

        logger.info(f"Inserting {len(functions_to_insert)} functions...")
        self._batch_insert_functions(functions_to_insert)

        logger.info(f"Inserting {len(classes_to_insert)} classes...")
        self._batch_insert_classes(classes_to_insert)

        logger.info(
            "Import complete: %d files, %d functions, %d classes, %d relationships",
            stats["files"],
            stats["functions"],
            stats["classes"],
            stats["relationships"],
        )

        return stats

    def _is_function_kind(self, kind: int, symbol: str) -> bool:
        """Check if SCIP symbol represents a function/method.

        scip-python sets kind=0 for everything, so we detect functions by symbol pattern.
        SCIP symbol format: scip-python python <package> <module>/<name>()./
        Functions have `()` in the symbol name.
        """
        # Check for function signature indicators
        return "()" in symbol or "(" in symbol

    def _is_class_kind(self, kind: int, symbol: str) -> bool:
        """Check if SCIP symbol represents a class/type.

        scip-python sets kind=0, so detect classes by naming conventions:
        - Classes are typically CamelCase
        - Classes don't have () in the name
        - Classes appear as descriptors in symbol path
        """
        # Extract name from symbol
        name = self._extract_name_from_symbol(symbol)

        # Skip if it's a function (has parentheses)
        if "()" in symbol or "(" in symbol:
            return False

        # Check if name looks like a class (CamelCase starting with uppercase)
        # and is not a module-level variable
        if name and len(name) > 0:
            # CamelCase pattern: starts with uppercase, has lowercase
            is_camel_case = name[0].isupper() and any(c.islower() for c in name)
            # Exclude common non-class patterns
            is_not_constant = not name.isupper()  # ALL_CAPS are constants
            return is_camel_case and is_not_constant

        return False

    def _create_file_node(self, file_path: str, language: str):
        """Create CodeFile node in Kuzu."""
        file_id = file_path  # Use path as ID for uniqueness

        # Check if file already exists
        check_query = """
        MATCH (f:CodeFile {file_id: $file_id})
        RETURN f
        """
        existing = self.conn.execute_query(check_query, {"file_id": file_id})

        if not existing:
            # Insert new file node
            insert_query = """
            CREATE (f:CodeFile {
                file_id: $file_id,
                file_path: $file_path,
                language: $language,
                size_bytes: 0,
                created_at: current_timestamp()
            })
            """
            self.conn.execute_write(
                insert_query,
                {
                    "file_id": file_id,
                    "file_path": file_path,
                    "language": language,
                },
            )
            logger.debug("Created CodeFile node: %s", file_path)

    def _create_function_node(self, symbol_info, file_path: str, doc):
        """Create CodeFunction node in Kuzu."""
        symbol_name = symbol_info.symbol
        function_name = self._extract_name_from_symbol(symbol_name)
        function_id = symbol_name  # Use full symbol as ID

        # Find line number from occurrences
        line_number = self._find_definition_line(symbol_name, doc.occurrences)

        # Check if function already exists
        check_query = """
        MATCH (f:CodeFunction {function_id: $function_id})
        RETURN f
        """
        existing = self.conn.execute_query(check_query, {"function_id": function_id})

        if not existing:
            # Extract documentation
            docstring = " ".join(symbol_info.documentation) if symbol_info.documentation else ""

            # Insert function node
            insert_query = """
            CREATE (f:CodeFunction {
                function_id: $function_id,
                function_name: $function_name,
                fully_qualified_name: $fqn,
                signature: $signature,
                file_path: $file_path,
                line_number: $line_number,
                docstring: $docstring,
                is_async: false,
                cyclomatic_complexity: 0,
                created_at: current_timestamp()
            })
            """
            self.conn.execute_write(
                insert_query,
                {
                    "function_id": function_id,
                    "function_name": function_name,
                    "fqn": symbol_name,
                    "signature": symbol_info.display_name or function_name,
                    "file_path": file_path,
                    "line_number": line_number,
                    "docstring": docstring,
                },
            )

            # Create DEFINED_IN relationship to file
            self._create_defined_in_relationship(function_id, file_path, line_number)

            logger.debug("Created CodeFunction node: %s at line %d", function_name, line_number)

    def _create_class_node(self, symbol_info, file_path: str, doc):
        """Create CodeClass node in Kuzu."""
        symbol_name = symbol_info.symbol
        class_name = self._extract_name_from_symbol(symbol_name)
        class_id = symbol_name

        # Find line number
        line_number = self._find_definition_line(symbol_name, doc.occurrences)

        # Check if class already exists
        check_query = """
        MATCH (c:CodeClass {class_id: $class_id})
        RETURN c
        """
        existing = self.conn.execute_query(check_query, {"class_id": class_id})

        if not existing:
            # Extract documentation
            docstring = " ".join(symbol_info.documentation) if symbol_info.documentation else ""

            # Insert class node
            insert_query = """
            CREATE (c:CodeClass {
                class_id: $class_id,
                class_name: $class_name,
                fully_qualified_name: $fqn,
                file_path: $file_path,
                line_number: $line_number,
                docstring: $docstring,
                is_abstract: false,
                created_at: current_timestamp()
            })
            """
            self.conn.execute_write(
                insert_query,
                {
                    "class_id": class_id,
                    "class_name": class_name,
                    "fqn": symbol_name,
                    "file_path": file_path,
                    "line_number": line_number,
                    "docstring": docstring,
                },
            )

            # Create CLASS_DEFINED_IN relationship
            rel_query = """
            MATCH (c:CodeClass {class_id: $class_id})
            MATCH (f:CodeFile {file_id: $file_id})
            CREATE (c)-[:CLASS_DEFINED_IN]->(f)
            """
            self.conn.execute_write(
                rel_query,
                {"class_id": class_id, "file_id": file_path},
            )

            logger.debug("Created CodeClass node: %s at line %d", class_name, line_number)

    def _create_defined_in_relationship(self, function_id: str, file_path: str, line_number: int):
        """Create DEFINED_IN relationship between function and file."""
        rel_query = """
        MATCH (func:CodeFunction {function_id: $function_id})
        MATCH (file:CodeFile {file_id: $file_id})
        CREATE (func)-[:DEFINED_IN {line_number: $line_number, end_line: $line_number}]->(file)
        """
        self.conn.execute_write(
            rel_query,
            {
                "function_id": function_id,
                "file_id": file_path,
                "line_number": line_number,
            },
        )

    def _extract_name_from_symbol(self, symbol: str) -> str:
        """Extract human-readable name from SCIP symbol string.

        SCIP symbols are in format: scip-python python <package> <module>/<name>
        Extract just the final name component.
        """
        if "/" in symbol:
            parts = symbol.split("/")
            return parts[-1].rstrip(".")
        if " " in symbol:
            parts = symbol.split()
            return parts[-1].rstrip(".")
        return symbol.rstrip(".")

    def _find_definition_line(self, symbol: str, occurrences) -> int:
        """Find the definition line number for a symbol from occurrences.

        SCIP occurrences mark definitions with the Definition role.
        SymbolRole.Definition = 1 (from SCIP protobuf enum)
        """
        if not scip_available:
            return 0

        DEFINITION_ROLE = 1  # SymbolRole.Definition from SCIP protobuf

        for occ in occurrences:
            if occ.symbol == symbol:
                # Check if this is a definition (not just a reference)
                if occ.symbol_roles & DEFINITION_ROLE:
                    # Range is [start_line, start_char, end_line, end_char]
                    if len(occ.range) >= 4:
                        return occ.range[0]  # Return start line

        # If no definition found, return 0 as fallback
        return 0

    def _batch_insert_files(self, files: list[tuple[str, str]]):
        """Batch insert CodeFile nodes."""
        if not files:
            return

        # Use a single query with parameters for all files
        for file_path, language in files:
            try:
                # Try to insert, skip if already exists (PRIMARY KEY conflict)
                insert_query = """
                CREATE (f:CodeFile {
                    file_id: $file_id,
                    file_path: $file_path,
                    language: $language,
                    size_bytes: 0,
                    created_at: current_timestamp()
                })
                """
                self.conn.execute_write(
                    insert_query,
                    {
                        "file_id": file_path,
                        "file_path": file_path,
                        "language": language,
                    },
                )
            except Exception:
                # Skip if node already exists (duplicate key error)
                pass

    def _batch_insert_functions(self, functions: list[tuple[Any, str, int]]):
        """Batch insert CodeFunction nodes."""
        if not functions:
            return

        for symbol_info, file_path, line_number in functions:
            try:
                symbol_name = symbol_info.symbol
                function_name = self._extract_name_from_symbol(symbol_name)
                function_id = symbol_name
                docstring = " ".join(symbol_info.documentation) if symbol_info.documentation else ""

                insert_query = """
                CREATE (f:CodeFunction {
                    function_id: $function_id,
                    function_name: $function_name,
                    fully_qualified_name: $fqn,
                    signature: $signature,
                    file_path: $file_path,
                    line_number: $line_number,
                    docstring: $docstring,
                    is_async: false,
                    cyclomatic_complexity: 0,
                    created_at: current_timestamp()
                })
                """
                self.conn.execute_write(
                    insert_query,
                    {
                        "function_id": function_id,
                        "function_name": function_name,
                        "fqn": symbol_name,
                        "signature": symbol_info.display_name or function_name,
                        "file_path": file_path,
                        "line_number": line_number,
                        "docstring": docstring,
                    },
                )

                # Create DEFINED_IN relationship
                rel_query = """
                MATCH (func:CodeFunction {function_id: $function_id})
                MATCH (file:CodeFile {file_id: $file_id})
                CREATE (func)-[:DEFINED_IN {line_number: $line_number, end_line: $line_number}]->(file)
                """
                self.conn.execute_write(
                    rel_query,
                    {
                        "function_id": function_id,
                        "file_id": file_path,
                        "line_number": line_number,
                    },
                )
            except Exception:
                # Skip duplicates
                pass

    def _batch_insert_classes(self, classes: list[tuple[Any, str, int]]):
        """Batch insert CodeClass nodes."""
        if not classes:
            return

        for symbol_info, file_path, line_number in classes:
            try:
                symbol_name = symbol_info.symbol
                class_name = self._extract_name_from_symbol(symbol_name)
                class_id = symbol_name
                docstring = " ".join(symbol_info.documentation) if symbol_info.documentation else ""

                insert_query = """
                CREATE (c:CodeClass {
                    class_id: $class_id,
                    class_name: $class_name,
                    fully_qualified_name: $fqn,
                    file_path: $file_path,
                    line_number: $line_number,
                    docstring: $docstring,
                    is_abstract: false,
                    created_at: current_timestamp()
                })
                """
                self.conn.execute_write(
                    insert_query,
                    {
                        "class_id": class_id,
                        "class_name": class_name,
                        "fqn": symbol_name,
                        "file_path": file_path,
                        "line_number": line_number,
                        "docstring": docstring,
                    },
                )

                # Create CLASS_DEFINED_IN relationship
                rel_query = """
                MATCH (c:CodeClass {class_id: $class_id})
                MATCH (f:CodeFile {file_id: $file_id})
                CREATE (c)-[:CLASS_DEFINED_IN]->(f)
                """
                self.conn.execute_write(
                    rel_query,
                    {"class_id": class_id, "file_id": file_path},
                )
            except Exception:
                # Skip duplicates
                pass
