"""Documentation knowledge graph integration with Neo4j memory system.

Integrates markdown documentation into the same Neo4j database as code and memories,
creating relationships between documentation, code, and concepts.

Public API:
    DocGraphIntegration - Main integration class
    parse_markdown_doc() - Parse markdown files into structured data
    extract_concepts() - Extract key concepts from documentation
    extract_code_references() - Find @file.py and code references
    import_documentation() - Import markdown files to Neo4j
    link_docs_to_code() - Create documentation-code relationships
    query_relevant_docs() - Find documentation for code/task
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .connector import Neo4jConnector
from .config import get_config

logger = logging.getLogger(__name__)


class DocGraphIntegration:
    """Integrates documentation knowledge graphs with Neo4j memory system.

    Handles:
    - Parsing markdown documentation files
    - Extracting concepts and relationships
    - Creating documentation nodes (DocFile, Concept, Section)
    - Linking documentation to code (CodeFile, Function, Class)
    - Linking documentation to memories
    - Querying relevant documentation
    """

    def __init__(self, connector: Neo4jConnector):
        """Initialize documentation graph integration.

        Args:
            connector: Connected Neo4jConnector instance
        """
        self.conn = connector
        self.config = get_config()

    def initialize_doc_schema(self) -> bool:
        """Initialize schema for documentation graph nodes (idempotent).

        Returns:
            True if successful, False otherwise
        """
        logger.info("Initializing documentation graph schema")

        try:
            self._create_doc_constraints()
            self._create_doc_indexes()
            logger.info("Documentation graph schema initialization complete")
            return True

        except Exception as e:
            logger.error("Documentation graph schema initialization failed: %s", e)
            return False

    def _create_doc_constraints(self):
        """Create unique constraints for documentation nodes (idempotent)."""
        constraints = [
            # DocFile path uniqueness
            """
            CREATE CONSTRAINT doc_file_path IF NOT EXISTS
            FOR (df:DocFile) REQUIRE df.path IS UNIQUE
            """,
            # Concept name uniqueness (within category)
            """
            CREATE CONSTRAINT concept_id IF NOT EXISTS
            FOR (c:Concept) REQUIRE c.id IS UNIQUE
            """,
            # Section ID uniqueness
            """
            CREATE CONSTRAINT section_id IF NOT EXISTS
            FOR (s:Section) REQUIRE s.id IS UNIQUE
            """,
        ]

        for constraint in constraints:
            try:
                self.conn.execute_write(constraint)
                logger.debug("Created documentation constraint")
            except Exception as e:
                logger.debug("Documentation constraint already exists or error: %s", e)

    def _create_doc_indexes(self):
        """Create performance indexes for documentation nodes (idempotent)."""
        indexes = [
            # DocFile title index
            """
            CREATE INDEX doc_file_title IF NOT EXISTS
            FOR (df:DocFile) ON (df.title)
            """,
            # Concept name index
            """
            CREATE INDEX concept_name IF NOT EXISTS
            FOR (c:Concept) ON (c.name)
            """,
            # Concept category index
            """
            CREATE INDEX concept_category IF NOT EXISTS
            FOR (c:Concept) ON (c.category)
            """,
            # Section heading index
            """
            CREATE INDEX section_heading IF NOT EXISTS
            FOR (s:Section) ON (s.heading)
            """,
        ]

        for index in indexes:
            try:
                self.conn.execute_write(index)
                logger.debug("Created documentation index")
            except Exception as e:
                logger.debug("Documentation index already exists or error: %s", e)

    def parse_markdown_doc(self, file_path: Path) -> Dict[str, Any]:
        """Parse markdown documentation file into structured data.

        Args:
            file_path: Path to markdown file

        Returns:
            Dictionary with parsed documentation structure:
            {
                'path': str,
                'title': str,
                'content': str,
                'sections': [{'heading': str, 'level': int, 'content': str}],
                'concepts': [str],
                'code_references': [{'file': str, 'line': int}],
                'links': [{'text': str, 'url': str}],
                'metadata': dict
            }

        Raises:
            FileNotFoundError: If markdown file doesn't exist
            ValueError: If file is not markdown
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Documentation file not found: {file_path}")

        if file_path.suffix.lower() not in [".md", ".markdown"]:
            raise ValueError(f"Not a markdown file: {file_path}")

        logger.info("Parsing markdown documentation: %s", file_path)

        with open(file_path, encoding="utf-8") as f:
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
            "path": str(file_path.absolute()),
            "title": title,
            "content": content,
            "sections": sections,
            "concepts": concepts,
            "code_references": code_references,
            "links": links,
            "metadata": metadata,
        }

    def _extract_title(self, content: str) -> str:
        """Extract title from markdown content (first # heading)."""
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return "Untitled"

    def _parse_sections(self, content: str) -> List[Dict[str, Any]]:
        """Parse markdown into sections based on headings.

        Returns:
            List of sections with heading, level, and content
        """
        sections = []
        lines = content.split("\n")

        current_section = None
        current_content = []

        for line in lines:
            # Check for heading
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)

            if heading_match:
                # Save previous section
                if current_section:
                    current_section["content"] = "\n".join(current_content).strip()
                    sections.append(current_section)

                # Start new section
                level = len(heading_match.group(1))
                heading = heading_match.group(2).strip()

                current_section = {
                    "heading": heading,
                    "level": level,
                    "content": "",
                }
                current_content = []
            else:
                # Add to current section content
                if current_section:
                    current_content.append(line)

        # Save last section
        if current_section:
            current_section["content"] = "\n".join(current_content).strip()
            sections.append(current_section)

        return sections

    def _extract_concepts(
        self, content: str, sections: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Extract key concepts from documentation.

        Concepts are identified from:
        - Section headings
        - Bold text (**concept**)
        - Code blocks with language identifiers
        - Lists with important terms

        Returns:
            List of concepts with name and category
        """
        concepts = []
        seen = set()

        # Extract from section headings
        for section in sections:
            heading = section["heading"]
            # Skip generic headings
            if heading.lower() not in ["overview", "introduction", "summary", "conclusion"]:
                if heading not in seen:
                    concepts.append(
                        {
                            "name": heading,
                            "category": "section",
                        }
                    )
                    seen.add(heading)

        # Extract bold text (likely important concepts)
        bold_pattern = re.compile(r"\*\*([^*]+)\*\*")
        for match in bold_pattern.finditer(content):
            concept = match.group(1).strip()
            # Filter out short or generic terms
            if len(concept) > 3 and concept not in seen:
                concepts.append(
                    {
                        "name": concept,
                        "category": "emphasized",
                    }
                )
                seen.add(concept)

        # Extract code block languages as concepts
        code_block_pattern = re.compile(r"```(\w+)")
        for match in code_block_pattern.finditer(content):
            language = match.group(1).strip()
            if language and language not in seen:
                concepts.append(
                    {
                        "name": language,
                        "category": "language",
                    }
                )
                seen.add(language)

        return concepts

    def _extract_code_references(self, content: str) -> List[Dict[str, Any]]:
        """Extract code references from documentation.

        Looks for:
        - @file.py references
        - @path/to/file.py references
        - file:line references
        - Code blocks with file indicators

        Returns:
            List of code references with file and optional line
        """
        references = []

        # Pattern 1: @file.py or @path/to/file.py
        at_pattern = re.compile(r"@([\w/._-]+\.py)")
        for match in at_pattern.finditer(content):
            file_path = match.group(1)
            references.append(
                {
                    "file": file_path,
                    "line": None,
                }
            )

        # Pattern 2: file:line references (e.g., example.py:42)
        file_line_pattern = re.compile(r"([\w/._-]+\.py):(\d+)")
        for match in file_line_pattern.finditer(content):
            file_path = match.group(1)
            line_num = int(match.group(2))
            references.append(
                {
                    "file": file_path,
                    "line": line_num,
                }
            )

        # Pattern 3: Inline code with .py extension (`file.py`)
        inline_code_pattern = re.compile(r"`([\w/._-]+\.py)`")
        for match in inline_code_pattern.finditer(content):
            file_path = match.group(1)
            references.append(
                {
                    "file": file_path,
                    "line": None,
                }
            )

        return references

    def _extract_links(self, content: str) -> List[Dict[str, str]]:
        """Extract markdown links from content.

        Returns:
            List of links with text and url
        """
        links = []

        # Markdown link pattern: [text](url)
        link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
        for match in link_pattern.finditer(content):
            text = match.group(1).strip()
            url = match.group(2).strip()
            links.append(
                {
                    "text": text,
                    "url": url,
                }
            )

        return links

    def _extract_metadata(self, file_path: Path, content: str) -> Dict[str, Any]:
        """Extract metadata from file and content.

        Returns:
            Dictionary with file metadata
        """
        stat = file_path.stat()

        return {
            "size_bytes": stat.st_size,
            "line_count": content.count("\n") + 1,
            "word_count": len(content.split()),
            "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "file_type": file_path.suffix.lower(),
        }

    def import_documentation(
        self,
        file_path: Path,
        project_id: Optional[str] = None,
    ) -> Dict[str, int]:
        """Import markdown documentation file into Neo4j.

        Args:
            file_path: Path to markdown file
            project_id: Optional project ID to link documentation to

        Returns:
            Dictionary with counts of imported nodes

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not markdown
        """
        logger.info("Importing documentation: %s", file_path)

        # Parse markdown
        doc_data = self.parse_markdown_doc(file_path)

        counts = {
            "doc_files": 0,
            "sections": 0,
            "concepts": 0,
            "code_refs": 0,
        }

        # Import DocFile node
        counts["doc_files"] = self._import_doc_file(doc_data, project_id)

        # Import sections
        counts["sections"] = self._import_sections(doc_data)

        # Import concepts
        counts["concepts"] = self._import_concepts(doc_data)

        # Import code references
        counts["code_refs"] = self._import_code_references(doc_data)

        logger.info("Documentation import complete: %s", counts)
        return counts

    def _import_doc_file(self, doc_data: Dict[str, Any], project_id: Optional[str] = None) -> int:
        """Import DocFile node."""
        query = """
        MERGE (df:DocFile {path: $path})
        ON CREATE SET
            df.title = $title,
            df.content = $content,
            df.line_count = $line_count,
            df.word_count = $word_count,
            df.last_modified = $last_modified,
            df.created_at = $created_at,
            df.imported_at = $imported_at
        ON MATCH SET
            df.title = $title,
            df.content = $content,
            df.line_count = $line_count,
            df.word_count = $word_count,
            df.last_modified = $last_modified,
            df.imported_at = $imported_at

        WITH df
        WHERE $project_id IS NOT NULL
        OPTIONAL MATCH (p:Project {id: $project_id})
        FOREACH (proj IN CASE WHEN p IS NOT NULL THEN [p] ELSE [] END |
            MERGE (df)-[:BELONGS_TO_PROJECT]->(proj)
        )

        RETURN count(df) as count
        """

        params = {
            "path": doc_data["path"],
            "title": doc_data["title"],
            "content": doc_data["content"],
            "line_count": doc_data["metadata"]["line_count"],
            "word_count": doc_data["metadata"]["word_count"],
            "last_modified": doc_data["metadata"]["last_modified"],
            "project_id": project_id,
            "created_at": datetime.now().isoformat(),
            "imported_at": datetime.now().isoformat(),
        }

        result = self.conn.execute_write(query, params)
        return result[0]["count"] if result else 0

    def _import_sections(self, doc_data: Dict[str, Any]) -> int:
        """Import section nodes and link to DocFile."""
        if not doc_data["sections"]:
            return 0

        # Generate unique section IDs
        sections_with_ids = []
        for idx, section in enumerate(doc_data["sections"]):
            section_id = f"{doc_data['path']}#section-{idx}"
            sections_with_ids.append(
                {
                    "id": section_id,
                    "heading": section["heading"],
                    "level": section["level"],
                    "content": section["content"],
                    "order": idx,
                }
            )

        query = """
        MATCH (df:DocFile {path: $doc_path})

        UNWIND $sections as sec
        MERGE (s:Section {id: sec.id})
        ON CREATE SET
            s.heading = sec.heading,
            s.level = sec.level,
            s.content = sec.content,
            s.order = sec.order,
            s.created_at = $created_at
        ON MATCH SET
            s.heading = sec.heading,
            s.level = sec.level,
            s.content = sec.content,
            s.order = sec.order

        MERGE (df)-[:HAS_SECTION]->(s)

        RETURN count(s) as count
        """

        params = {
            "doc_path": doc_data["path"],
            "sections": sections_with_ids,
            "created_at": datetime.now().isoformat(),
        }

        result = self.conn.execute_write(query, params)
        return result[0]["count"] if result else 0

    def _import_concepts(self, doc_data: Dict[str, Any]) -> int:
        """Import concept nodes and link to DocFile."""
        if not doc_data["concepts"]:
            return 0

        # Generate unique concept IDs
        concepts_with_ids = []
        for concept in doc_data["concepts"]:
            concept_id = f"{concept['category']}:{concept['name']}"
            concepts_with_ids.append(
                {
                    "id": concept_id,
                    "name": concept["name"],
                    "category": concept["category"],
                }
            )

        query = """
        MATCH (df:DocFile {path: $doc_path})

        UNWIND $concepts as con
        MERGE (c:Concept {id: con.id})
        ON CREATE SET
            c.name = con.name,
            c.category = con.category,
            c.created_at = $created_at
        ON MATCH SET
            c.name = con.name,
            c.category = con.category

        MERGE (df)-[:DEFINES]->(c)

        RETURN count(c) as count
        """

        params = {
            "doc_path": doc_data["path"],
            "concepts": concepts_with_ids,
            "created_at": datetime.now().isoformat(),
        }

        result = self.conn.execute_write(query, params)
        return result[0]["count"] if result else 0

    def _import_code_references(self, doc_data: Dict[str, Any]) -> int:
        """Import code references and link DocFile to CodeFile."""
        if not doc_data["code_references"]:
            return 0

        query = """
        MATCH (df:DocFile {path: $doc_path})

        UNWIND $refs as ref
        OPTIONAL MATCH (cf:CodeFile)
        WHERE cf.path CONTAINS ref.file OR ref.file CONTAINS cf.path

        FOREACH (code_file IN CASE WHEN cf IS NOT NULL THEN [cf] ELSE [] END |
            MERGE (df)-[r:REFERENCES {
                file: ref.file,
                line: ref.line
            }]->(code_file)
            ON CREATE SET r.created_at = $created_at
        )

        RETURN count(DISTINCT cf) as count
        """

        params = {
            "doc_path": doc_data["path"],
            "refs": doc_data["code_references"],
            "created_at": datetime.now().isoformat(),
        }

        result = self.conn.execute_write(query, params)
        return result[0]["count"] if result else 0

    def link_docs_to_code(self, project_id: Optional[str] = None) -> int:
        """Create relationships between documentation and code.

        Links DocFiles to CodeFiles, Functions, and Classes based on:
        - Explicit code references in documentation
        - Concept matches (function names, class names)
        - File path patterns

        Args:
            project_id: Optional project scope

        Returns:
            Number of relationships created
        """
        logger.info("Linking documentation to code")

        count = 0

        # Link concepts to functions
        count += self._link_concepts_to_functions()

        # Link concepts to classes
        count += self._link_concepts_to_classes()

        logger.info("Created %d doc-code relationships", count)
        return count

    def _link_concepts_to_functions(self) -> int:
        """Link concepts to functions by name matching."""
        query = """
        MATCH (c:Concept), (f:Function)
        WHERE toLower(c.name) = toLower(f.name)
           OR c.name CONTAINS f.name
           OR f.name CONTAINS c.name

        MERGE (c)-[r:IMPLEMENTED_IN]->(f)
        ON CREATE SET r.created_at = $created_at

        RETURN count(r) as count
        """

        params = {"created_at": datetime.now().isoformat()}

        result = self.conn.execute_write(query, params)
        return result[0]["count"] if result else 0

    def _link_concepts_to_classes(self) -> int:
        """Link concepts to classes by name matching."""
        query = """
        MATCH (c:Concept), (cls:Class)
        WHERE toLower(c.name) = toLower(cls.name)
           OR c.name CONTAINS cls.name
           OR cls.name CONTAINS c.name

        MERGE (c)-[r:IMPLEMENTED_IN]->(cls)
        ON CREATE SET r.created_at = $created_at

        RETURN count(r) as count
        """

        params = {"created_at": datetime.now().isoformat()}

        result = self.conn.execute_write(query, params)
        return result[0]["count"] if result else 0

    def link_docs_to_memories(self, project_id: Optional[str] = None) -> int:
        """Create relationships between documentation and memories.

        Links memories to relevant documentation based on:
        - Tags matching concepts
        - Content similarity
        - Code references in both

        Args:
            project_id: Optional project scope

        Returns:
            Number of relationships created
        """
        logger.info("Linking documentation to memories")

        count = 0

        # Link memories to docs via concepts
        count += self._link_memories_to_docs_via_concepts()

        logger.info("Created %d doc-memory relationships", count)
        return count

    def _link_memories_to_docs_via_concepts(self) -> int:
        """Link memories to documentation via shared concepts."""
        query = """
        MATCH (m:Memory)-[:TAGGED_WITH]->(tag)
        MATCH (c:Concept)
        WHERE toLower(tag.name) = toLower(c.name)

        MATCH (c)<-[:DEFINES]-(df:DocFile)

        MERGE (m)-[r:DOCUMENTED_IN]->(df)
        ON CREATE SET r.created_at = $created_at

        RETURN count(r) as count
        """

        params = {"created_at": datetime.now().isoformat()}

        try:
            result = self.conn.execute_write(query, params)
            return result[0]["count"] if result else 0
        except Exception as e:
            logger.debug("Could not link memories to docs: %s", e)
            return 0

    def query_relevant_docs(
        self,
        query_text: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find relevant documentation for a query or task.

        Args:
            query_text: Search query or task description
            limit: Maximum number of documents to return

        Returns:
            List of relevant documentation files with metadata
        """
        # Simple keyword-based search
        # TODO: Enhance with vector embeddings for semantic search

        query = """
        MATCH (df:DocFile)
        WHERE toLower(df.title) CONTAINS toLower($query)
           OR toLower(df.content) CONTAINS toLower($query)

        OPTIONAL MATCH (df)-[:DEFINES]->(c:Concept)
        WHERE toLower(c.name) CONTAINS toLower($query)

        WITH df, count(c) as concept_matches

        RETURN {
            path: df.path,
            title: df.title,
            line_count: df.line_count,
            word_count: df.word_count,
            concept_matches: concept_matches,
            last_modified: df.last_modified
        } as doc

        ORDER BY concept_matches DESC, df.title ASC
        LIMIT $limit
        """

        params = {
            "query": query_text,
            "limit": limit,
        }

        result = self.conn.execute_query(query, params)

        if result:
            return [record["doc"] for record in result]

        return []

    def get_doc_stats(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Get documentation graph statistics.

        Args:
            project_id: Optional project filter

        Returns:
            Dictionary with documentation statistics
        """
        query = """
        MATCH (df:DocFile)
        OPTIONAL MATCH (df)-[:HAS_SECTION]->(s:Section)
        OPTIONAL MATCH (df)-[:DEFINES]->(c:Concept)
        OPTIONAL MATCH (df)-[:REFERENCES]->(cf:CodeFile)

        RETURN
            count(DISTINCT df) as doc_count,
            count(DISTINCT s) as section_count,
            count(DISTINCT c) as concept_count,
            count(DISTINCT cf) as code_ref_count,
            sum(df.word_count) as total_words
        """

        result = self.conn.execute_query(query)

        if result:
            return result[0]

        return {
            "doc_count": 0,
            "section_count": 0,
            "concept_count": 0,
            "code_ref_count": 0,
            "total_words": 0,
        }
