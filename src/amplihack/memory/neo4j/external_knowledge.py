"""External knowledge integration with Neo4j memory system.

Handles fetching, caching, and linking external documentation sources
(Python docs, MS Learn, library docs) to code and memories.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from .connector import Neo4jConnector
from .config import get_config

logger = logging.getLogger(__name__)


class KnowledgeSource(Enum):
    """Supported external knowledge sources."""

    PYTHON_DOCS = "python-docs"
    MS_LEARN = "ms-learn"
    GITHUB = "github"
    LIBRARY_DOCS = "library-docs"
    CUSTOM = "custom"


@dataclass
class ExternalDoc:
    """External documentation record.

    Attributes:
        url: Source URL
        title: Document title
        content: Document content (can be markdown, HTML, or text)
        source: Knowledge source type
        version: Version identifier (e.g., "3.10", "latest")
        trust_score: Credibility score (0.0-1.0)
        metadata: Additional metadata
        fetched_at: When document was fetched
        ttl_hours: Cache TTL in hours (0 = no expiry)
    """
    url: str
    title: str
    content: str
    source: KnowledgeSource
    version: str = "latest"
    trust_score: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)
    fetched_at: datetime = field(default_factory=datetime.now)
    ttl_hours: int = 24 * 7  # 7 days default


@dataclass
class APIReference:
    """API reference documentation.

    Attributes:
        name: API/function/class name
        signature: Function signature or API endpoint
        doc_url: Link to full documentation
        description: Brief description
        examples: Code examples
        source: Knowledge source
        version: Version identifier
    """
    name: str
    signature: str
    doc_url: str
    description: str = ""
    examples: List[str] = field(default_factory=list)
    source: KnowledgeSource = KnowledgeSource.LIBRARY_DOCS
    version: str = "latest"


class ExternalKnowledgeManager:
    """Manages external knowledge integration with Neo4j.

    Handles:
    - Fetching external documentation
    - Caching with TTL
    - Linking docs to code and memories
    - Version tracking
    - Credibility scoring
    - Query and retrieval
    """

    def __init__(
        self,
        connector: Neo4jConnector,
        cache_dir: Optional[Path] = None,
        enable_http_cache: bool = True,
    ):
        """Initialize external knowledge manager.

        Args:
            connector: Connected Neo4jConnector instance
            cache_dir: Directory for local file cache
            enable_http_cache: Enable HTTP response caching
        """
        self.conn = connector
        self.config = get_config()

        # Set up cache directory
        self.cache_dir = cache_dir or Path.home() / ".amplihack" / "knowledge_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.enable_http_cache = enable_http_cache

        if not REQUESTS_AVAILABLE:
            logger.warning("requests library not available. Install with: pip install requests")

    def initialize_knowledge_schema(self) -> bool:
        """Initialize schema for external knowledge nodes (idempotent).

        Returns:
            True if successful, False otherwise
        """
        logger.info("Initializing external knowledge schema")

        try:
            self._create_knowledge_constraints()
            self._create_knowledge_indexes()
            logger.info("External knowledge schema initialization complete")
            return True

        except Exception as e:
            logger.error("External knowledge schema initialization failed: %s", e)
            return False

    def _create_knowledge_constraints(self):
        """Create unique constraints for knowledge nodes (idempotent)."""
        constraints = [
            # ExternalDoc URL uniqueness
            """
            CREATE CONSTRAINT external_doc_url IF NOT EXISTS
            FOR (ed:ExternalDoc) REQUIRE ed.url IS UNIQUE
            """,
            # APIReference ID uniqueness
            """
            CREATE CONSTRAINT api_reference_id IF NOT EXISTS
            FOR (api:APIReference) REQUIRE api.id IS UNIQUE
            """,
        ]

        for constraint in constraints:
            try:
                self.conn.execute_write(constraint)
                logger.debug("Created knowledge constraint")
            except Exception as e:
                logger.debug("Knowledge constraint already exists or error: %s", e)

    def _create_knowledge_indexes(self):
        """Create performance indexes for knowledge nodes (idempotent)."""
        indexes = [
            # Source type index
            """
            CREATE INDEX external_doc_source IF NOT EXISTS
            FOR (ed:ExternalDoc) ON (ed.source)
            """,
            # Version index
            """
            CREATE INDEX external_doc_version IF NOT EXISTS
            FOR (ed:ExternalDoc) ON (ed.version)
            """,
            # Trust score index
            """
            CREATE INDEX external_doc_trust IF NOT EXISTS
            FOR (ed:ExternalDoc) ON (ed.trust_score)
            """,
            # Fetched timestamp index
            """
            CREATE INDEX external_doc_fetched IF NOT EXISTS
            FOR (ed:ExternalDoc) ON (ed.fetched_at)
            """,
            # API name index
            """
            CREATE INDEX api_reference_name IF NOT EXISTS
            FOR (api:APIReference) ON (api.name)
            """,
        ]

        for index in indexes:
            try:
                self.conn.execute_write(index)
                logger.debug("Created knowledge index")
            except Exception as e:
                logger.debug("Knowledge index already exists or error: %s", e)

    def fetch_api_docs(
        self,
        url: str,
        source: KnowledgeSource = KnowledgeSource.LIBRARY_DOCS,
        version: str = "latest",
        trust_score: float = 0.8,
        force_refresh: bool = False,
    ) -> Optional[ExternalDoc]:
        """Fetch external documentation from URL.

        Args:
            url: Documentation URL
            source: Knowledge source type
            version: Version identifier
            trust_score: Credibility score (0.0-1.0)
            force_refresh: Force fetch even if cached

        Returns:
            ExternalDoc if successful, None otherwise
        """
        if not REQUESTS_AVAILABLE:
            logger.error("requests library required for HTTP fetching")
            return None

        # Check cache first
        if not force_refresh:
            cached = self._get_cached_doc(url)
            if cached:
                logger.debug("Using cached doc: %s", url)
                return cached

        logger.info("Fetching external doc: %s", url)

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Extract title from HTML or use URL
            title = self._extract_title(response.text) or url

            doc = ExternalDoc(
                url=url,
                title=title,
                content=response.text,
                source=source,
                version=version,
                trust_score=trust_score,
                metadata={
                    "content_type": response.headers.get("content-type", "text/html"),
                    "content_length": len(response.text),
                },
            )

            # Cache locally
            if self.enable_http_cache:
                self._cache_doc(doc)

            return doc

        except requests.RequestException as e:
            logger.error("Failed to fetch %s: %s", url, e)
            return None

    def _extract_title(self, html_content: str) -> Optional[str]:
        """Extract title from HTML content.

        Args:
            html_content: HTML content

        Returns:
            Extracted title or None
        """
        # Simple regex-based extraction
        import re
        match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _get_cache_path(self, url: str) -> Path:
        """Get cache file path for URL.

        Args:
            url: Document URL

        Returns:
            Path to cache file
        """
        # Hash URL to create safe filename
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        return self.cache_dir / f"{url_hash}.json"

    def _cache_doc(self, doc: ExternalDoc):
        """Cache document to local filesystem.

        Args:
            doc: Document to cache
        """
        cache_path = self._get_cache_path(doc.url)

        cache_data = {
            "url": doc.url,
            "title": doc.title,
            "content": doc.content,
            "source": doc.source.value,
            "version": doc.version,
            "trust_score": doc.trust_score,
            "metadata": doc.metadata,
            "fetched_at": doc.fetched_at.isoformat(),
            "ttl_hours": doc.ttl_hours,
        }

        try:
            with open(cache_path, "w") as f:
                json.dump(cache_data, f, indent=2)
            logger.debug("Cached doc: %s", cache_path)
        except OSError as e:
            logger.warning("Failed to cache doc: %s", e)

    def _get_cached_doc(self, url: str) -> Optional[ExternalDoc]:
        """Get cached document if not expired.

        Args:
            url: Document URL

        Returns:
            Cached ExternalDoc or None
        """
        cache_path = self._get_cache_path(url)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path) as f:
                cache_data = json.load(f)

            fetched_at = datetime.fromisoformat(cache_data["fetched_at"])
            ttl_hours = cache_data.get("ttl_hours", 24 * 7)

            # Check if expired
            if ttl_hours > 0:
                expiry = fetched_at + timedelta(hours=ttl_hours)
                if datetime.now() > expiry:
                    logger.debug("Cached doc expired: %s", url)
                    return None

            doc = ExternalDoc(
                url=cache_data["url"],
                title=cache_data["title"],
                content=cache_data["content"],
                source=KnowledgeSource(cache_data["source"]),
                version=cache_data["version"],
                trust_score=cache_data["trust_score"],
                metadata=cache_data.get("metadata", {}),
                fetched_at=fetched_at,
                ttl_hours=ttl_hours,
            )

            return doc

        except (OSError, json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to read cached doc: %s", e)
            return None

    def cache_external_doc(self, doc: ExternalDoc) -> bool:
        """Store external document in Neo4j.

        Args:
            doc: External document to store

        Returns:
            True if successful, False otherwise
        """
        logger.info("Caching external doc in Neo4j: %s", doc.url)

        query = """
        MERGE (ed:ExternalDoc {url: $url})
        SET
            ed.title = $title,
            ed.content = $content,
            ed.source = $source,
            ed.version = $version,
            ed.trust_score = $trust_score,
            ed.metadata = $metadata,
            ed.fetched_at = $fetched_at,
            ed.ttl_hours = $ttl_hours,
            ed.updated_at = $updated_at
        RETURN ed.url as url
        """

        params = {
            "url": doc.url,
            "title": doc.title,
            "content": doc.content,
            "source": doc.source.value,
            "version": doc.version,
            "trust_score": doc.trust_score,
            "metadata": json.dumps(doc.metadata),
            "fetched_at": doc.fetched_at.isoformat(),
            "ttl_hours": doc.ttl_hours,
            "updated_at": datetime.now().isoformat(),
        }

        try:
            result = self.conn.execute_write(query, params)
            return len(result) > 0
        except Exception as e:
            logger.error("Failed to cache doc in Neo4j: %s", e)
            return False

    def link_to_code(
        self,
        doc_url: str,
        code_path: str,
        relationship_type: str = "EXPLAINS",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Link external documentation to code file.

        Args:
            doc_url: External doc URL
            code_path: Code file path
            relationship_type: Type of relationship (EXPLAINS, DOCUMENTS, etc.)
            metadata: Optional relationship metadata

        Returns:
            True if successful, False otherwise
        """
        logger.info("Linking doc %s to code %s", doc_url, code_path)

        query = f"""
        MATCH (ed:ExternalDoc {{url: $doc_url}})
        MATCH (cf:CodeFile {{path: $code_path}})
        MERGE (ed)-[r:{relationship_type}]->(cf)
        ON CREATE SET
            r.created_at = $created_at,
            r.metadata = $metadata
        ON MATCH SET
            r.updated_at = $updated_at
        RETURN count(r) as count
        """

        params = {
            "doc_url": doc_url,
            "code_path": code_path,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": json.dumps(metadata or {}),
        }

        try:
            result = self.conn.execute_write(query, params)
            return result[0]["count"] > 0 if result else False
        except Exception as e:
            logger.error("Failed to link doc to code: %s", e)
            return False

    def link_to_function(
        self,
        doc_url: str,
        function_id: str,
        relationship_type: str = "DOCUMENTS",
    ) -> bool:
        """Link external documentation to function.

        Args:
            doc_url: External doc URL
            function_id: Function node ID
            relationship_type: Type of relationship

        Returns:
            True if successful, False otherwise
        """
        logger.info("Linking doc %s to function %s", doc_url, function_id)

        query = f"""
        MATCH (ed:ExternalDoc {{url: $doc_url}})
        MATCH (f:Function {{id: $function_id}})
        MERGE (ed)-[r:{relationship_type}]->(f)
        ON CREATE SET r.created_at = $created_at
        ON MATCH SET r.updated_at = $updated_at
        RETURN count(r) as count
        """

        params = {
            "doc_url": doc_url,
            "function_id": function_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        try:
            result = self.conn.execute_write(query, params)
            return result[0]["count"] > 0 if result else False
        except Exception as e:
            logger.error("Failed to link doc to function: %s", e)
            return False

    def link_to_memory(
        self,
        doc_url: str,
        memory_id: str,
        relationship_type: str = "SOURCED_FROM",
    ) -> bool:
        """Link memory to external documentation source.

        Args:
            doc_url: External doc URL
            memory_id: Memory node ID
            relationship_type: Type of relationship

        Returns:
            True if successful, False otherwise
        """
        logger.info("Linking memory %s to doc %s", memory_id, doc_url)

        query = f"""
        MATCH (m:Memory {{id: $memory_id}})
        MATCH (ed:ExternalDoc {{url: $doc_url}})
        MERGE (m)-[r:{relationship_type}]->(ed)
        ON CREATE SET r.created_at = $created_at
        ON MATCH SET r.updated_at = $updated_at
        RETURN count(r) as count
        """

        params = {
            "memory_id": memory_id,
            "doc_url": doc_url,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        try:
            result = self.conn.execute_write(query, params)
            return result[0]["count"] > 0 if result else False
        except Exception as e:
            logger.error("Failed to link memory to doc: %s", e)
            return False

    def store_api_reference(self, api_ref: APIReference) -> bool:
        """Store API reference in Neo4j.

        Args:
            api_ref: API reference to store

        Returns:
            True if successful, False otherwise
        """
        logger.info("Storing API reference: %s", api_ref.name)

        # Generate ID from name + version
        api_id = f"{api_ref.name}:{api_ref.version}"

        query = """
        MERGE (api:APIReference {id: $id})
        SET
            api.name = $name,
            api.signature = $signature,
            api.doc_url = $doc_url,
            api.description = $description,
            api.examples = $examples,
            api.source = $source,
            api.version = $version,
            api.updated_at = $updated_at
        RETURN api.id as id
        """

        params = {
            "id": api_id,
            "name": api_ref.name,
            "signature": api_ref.signature,
            "doc_url": api_ref.doc_url,
            "description": api_ref.description,
            "examples": json.dumps(api_ref.examples),
            "source": api_ref.source.value,
            "version": api_ref.version,
            "updated_at": datetime.now().isoformat(),
        }

        try:
            result = self.conn.execute_write(query, params)
            return len(result) > 0
        except Exception as e:
            logger.error("Failed to store API reference: %s", e)
            return False

    def query_external_knowledge(
        self,
        query_text: str,
        source: Optional[KnowledgeSource] = None,
        version: Optional[str] = None,
        min_trust_score: float = 0.5,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Query external knowledge by text search.

        Args:
            query_text: Search query
            source: Optional source filter
            version: Optional version filter
            min_trust_score: Minimum trust score
            limit: Maximum results

        Returns:
            List of matching documents
        """
        logger.info("Querying external knowledge: %s", query_text)

        # Build query with optional filters
        filters = ["ed.trust_score >= $min_trust_score"]
        params: Dict[str, Any] = {
            "query_text": query_text.lower(),
            "min_trust_score": min_trust_score,
            "limit": limit,
        }

        if source:
            filters.append("ed.source = $source")
            params["source"] = source.value

        if version:
            filters.append("ed.version = $version")
            params["version"] = version

        where_clause = " AND ".join(filters)

        query = f"""
        MATCH (ed:ExternalDoc)
        WHERE {where_clause}
            AND (toLower(ed.title) CONTAINS $query_text
                 OR toLower(ed.content) CONTAINS $query_text)
        RETURN ed {{
            .url, .title, .source, .version,
            .trust_score, .fetched_at
        }} as doc
        ORDER BY ed.trust_score DESC, ed.fetched_at DESC
        LIMIT $limit
        """

        try:
            results = self.conn.execute_query(query, params)
            return [r["doc"] for r in results]
        except Exception as e:
            logger.error("Failed to query external knowledge: %s", e)
            return []

    def get_doc_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get external document by URL.

        Args:
            url: Document URL

        Returns:
            Document data or None
        """
        query = """
        MATCH (ed:ExternalDoc {url: $url})
        RETURN ed {
            .url, .title, .content, .source, .version,
            .trust_score, .metadata, .fetched_at, .ttl_hours
        } as doc
        """

        params = {"url": url}

        try:
            results = self.conn.execute_query(query, params)
            return results[0]["doc"] if results else None
        except Exception as e:
            logger.error("Failed to get doc by URL: %s", e)
            return None

    def get_code_documentation(self, code_path: str) -> List[Dict[str, Any]]:
        """Get all external documentation linked to code file.

        Args:
            code_path: Code file path

        Returns:
            List of linked documents
        """
        query = """
        MATCH (cf:CodeFile {path: $code_path})
        MATCH (ed:ExternalDoc)-[r]->(cf)
        RETURN ed {
            .url, .title, .source, .version, .trust_score
        } as doc, type(r) as relationship_type
        ORDER BY ed.trust_score DESC
        """

        params = {"code_path": code_path}

        try:
            results = self.conn.execute_query(query, params)
            return [
                {**r["doc"], "relationship_type": r["relationship_type"]}
                for r in results
            ]
        except Exception as e:
            logger.error("Failed to get code documentation: %s", e)
            return []

    def get_function_documentation(self, function_id: str) -> List[Dict[str, Any]]:
        """Get all external documentation linked to function.

        Args:
            function_id: Function node ID

        Returns:
            List of linked documents
        """
        query = """
        MATCH (f:Function {id: $function_id})
        MATCH (ed:ExternalDoc)-[r]->(f)
        RETURN ed {
            .url, .title, .source, .version, .trust_score
        } as doc, type(r) as relationship_type
        ORDER BY ed.trust_score DESC
        """

        params = {"function_id": function_id}

        try:
            results = self.conn.execute_query(query, params)
            return [
                {**r["doc"], "relationship_type": r["relationship_type"]}
                for r in results
            ]
        except Exception as e:
            logger.error("Failed to get function documentation: %s", e)
            return []

    def cleanup_expired_docs(self) -> int:
        """Remove expired documents from Neo4j.

        Returns:
            Number of documents removed
        """
        logger.info("Cleaning up expired external docs")

        query = """
        MATCH (ed:ExternalDoc)
        WHERE ed.ttl_hours > 0
            AND datetime(ed.fetched_at) + duration({hours: ed.ttl_hours}) < datetime()
        DETACH DELETE ed
        RETURN count(ed) as count
        """

        try:
            result = self.conn.execute_write(query)
            count = result[0]["count"] if result else 0
            logger.info("Removed %d expired docs", count)
            return count
        except Exception as e:
            logger.error("Failed to cleanup expired docs: %s", e)
            return 0

    def get_knowledge_stats(self) -> Dict[str, Any]:
        """Get statistics about external knowledge.

        Returns:
            Dictionary with knowledge statistics
        """
        query = """
        MATCH (ed:ExternalDoc)
        OPTIONAL MATCH (ed)-[r:EXPLAINS|DOCUMENTS]->()
        RETURN
            count(DISTINCT ed) as total_docs,
            count(DISTINCT ed.source) as sources,
            avg(ed.trust_score) as avg_trust_score,
            count(DISTINCT r) as total_links
        """

        try:
            result = self.conn.execute_query(query)
            return result[0] if result else {
                "total_docs": 0,
                "sources": 0,
                "avg_trust_score": 0.0,
                "total_links": 0,
            }
        except Exception as e:
            logger.error("Failed to get knowledge stats: %s", e)
            return {
                "total_docs": 0,
                "sources": 0,
                "avg_trust_score": 0.0,
                "total_links": 0,
            }
