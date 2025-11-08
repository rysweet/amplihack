# External Knowledge Integration - Implementation Guide

**Concrete code examples for integrating external knowledge into Neo4j memory graph**

## Quick Start: Minimal Integration (30 minutes)

### Step 1: File-Based Cache (Start Here)

```python
# src/amplihack/external_knowledge/cache.py

from pathlib import Path
from typing import Optional, Dict
import json
import hashlib
from datetime import datetime, timedelta

class ExternalKnowledgeCache:
    """
    Simple file-based cache for external knowledge.

    Philosophy: Start with files. They're simple, versionable, and inspectable.
    Move to database only when files become a bottleneck.
    """

    def __init__(self, cache_dir: Path = None):
        self.cache_dir = cache_dir or Path.home() / ".amplihack" / "external_knowledge"
        self.cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    def get(self,
            source: str,
            identifier: str,
            version: str = None,
            max_age_days: int = 7) -> Optional[Dict]:
        """
        Get cached knowledge if fresh enough.

        Args:
            source: "python_docs" | "ms_learn" | "stackoverflow"
            identifier: Unique ID within source (e.g., "asyncio.run")
            version: Version string (e.g., "3.12")
            max_age_days: Max age before considering stale

        Returns:
            Cached data dict or None if not found/stale
        """
        cache_file = self._get_cache_path(source, identifier, version)

        if not cache_file.exists():
            return None

        # Check freshness
        file_age = datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)
        if file_age > timedelta(days=max_age_days):
            return None

        try:
            with cache_file.open() as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            # Corrupted cache file
            cache_file.unlink()
            return None

    def set(self,
            source: str,
            identifier: str,
            data: Dict,
            version: str = None):
        """Save knowledge to cache."""
        cache_file = self._get_cache_path(source, identifier, version)
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        # Add metadata
        cache_data = {
            "cached_at": datetime.now().isoformat(),
            "source": source,
            "identifier": identifier,
            "version": version,
            "data": data
        }

        with cache_file.open('w') as f:
            json.dump(cache_data, f, indent=2)

        # Secure permissions
        cache_file.chmod(0o600)

    def _get_cache_path(self, source: str, identifier: str, version: str = None) -> Path:
        """Generate cache file path."""
        # Hash identifier to avoid filesystem issues
        id_hash = hashlib.md5(identifier.encode()).hexdigest()[:16]

        parts = [source, id_hash]
        if version:
            parts.append(version)

        return self.cache_dir / "/".join(parts) / "data.json"

    def invalidate(self, source: str = None, identifier: str = None):
        """Invalidate cache entries."""
        if source and identifier:
            cache_file = self._get_cache_path(source, identifier)
            if cache_file.exists():
                cache_file.unlink()
        elif source:
            # Invalidate entire source
            source_dir = self.cache_dir / source
            if source_dir.exists():
                import shutil
                shutil.rmtree(source_dir)

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total_files = 0
        total_size = 0
        sources = {}

        for source_dir in self.cache_dir.iterdir():
            if source_dir.is_dir():
                source_files = list(source_dir.rglob("*.json"))
                source_size = sum(f.stat().st_size for f in source_files)

                sources[source_dir.name] = {
                    "count": len(source_files),
                    "size_mb": source_size / 1024 / 1024
                }

                total_files += len(source_files)
                total_size += source_size

        return {
            "total_files": total_files,
            "total_size_mb": total_size / 1024 / 1024,
            "sources": sources
        }
```

### Step 2: Simple Fetcher (Python Docs Example)

```python
# src/amplihack/external_knowledge/sources/python_docs.py

import requests
from typing import Optional, Dict
from bs4 import BeautifulSoup

class PythonDocsFetcher:
    """Fetch Python official documentation."""

    BASE_URL = "https://docs.python.org/3"

    def fetch_function_doc(self, module: str, function: str, version: str = "3.12") -> Optional[Dict]:
        """
        Fetch documentation for a Python function.

        Example:
            fetch_function_doc("asyncio", "run", "3.12")
        """

        # Construct URL
        url = f"{self.BASE_URL}/library/{module}.html#{module}.{function}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract function signature
            signature = self._extract_signature(soup, function)

            # Extract description
            description = self._extract_description(soup, function)

            # Extract examples
            examples = self._extract_examples(soup)

            return {
                "source": "python_docs",
                "source_url": url,
                "module": module,
                "function": function,
                "version": version,
                "signature": signature,
                "description": description,
                "examples": examples,
                "fetched_at": datetime.now().isoformat()
            }

        except requests.RequestException as e:
            print(f"Failed to fetch {module}.{function}: {e}")
            return None

    def _extract_signature(self, soup: BeautifulSoup, function_name: str) -> str:
        """Extract function signature from parsed HTML."""
        # Find dt element with function name
        dt = soup.find('dt', id=lambda x: x and function_name in x)
        if dt:
            return dt.get_text(strip=True)
        return ""

    def _extract_description(self, soup: BeautifulSoup, function_name: str) -> str:
        """Extract function description."""
        dt = soup.find('dt', id=lambda x: x and function_name in x)
        if dt:
            dd = dt.find_next_sibling('dd')
            if dd:
                # Get first paragraph
                p = dd.find('p')
                if p:
                    return p.get_text(strip=True)
        return ""

    def _extract_examples(self, soup: BeautifulSoup) -> list:
        """Extract code examples."""
        examples = []
        for pre in soup.find_all('pre'):
            code = pre.get_text(strip=True)
            if code and len(code) < 500:  # Reasonable size
                examples.append(code)
        return examples[:2]  # Max 2 examples
```

### Step 3: Simple Integration with Memory System

```python
# src/amplihack/external_knowledge/retriever.py

from typing import Optional, List, Dict
from amplihack.memory import MemoryManager, MemoryType
from .cache import ExternalKnowledgeCache
from .sources.python_docs import PythonDocsFetcher

class ExternalKnowledgeRetriever:
    """
    Retrieve external knowledge with caching and project memory integration.

    Priority:
    1. Project memory (what we've learned in this project)
    2. Cached external knowledge (what we fetched recently)
    3. Fresh external knowledge (fetch from source)
    """

    def __init__(self, memory_manager: MemoryManager = None):
        self.cache = ExternalKnowledgeCache()
        self.memory_manager = memory_manager
        self.fetchers = {
            "python_docs": PythonDocsFetcher(),
            # Add more fetchers as needed
        }

    def get_function_doc(self,
                        language: str,
                        module: str,
                        function: str,
                        version: str = None) -> Optional[Dict]:
        """
        Get function documentation with smart fallback.

        Fallback chain:
        1. Check project memory (did we look this up before?)
        2. Check cache (do we have it cached?)
        3. Fetch from source (go get it)
        """

        # Step 1: Check project memory
        if self.memory_manager:
            memories = self.memory_manager.retrieve(
                memory_type=MemoryType.LEARNING,
                search=f"{module}.{function}",
                tags=["external_doc", language]
            )
            if memories:
                # We've used this before
                return memories[0].metadata.get("external_doc")

        # Step 2: Check cache
        cache_key = f"{language}_docs"
        identifier = f"{module}.{function}"
        cached = self.cache.get(cache_key, identifier, version, max_age_days=30)
        if cached:
            return cached["data"]

        # Step 3: Fetch from source
        fetcher = self.fetchers.get(f"{language}_docs")
        if not fetcher:
            return None

        doc = fetcher.fetch_function_doc(module, function, version)
        if doc:
            # Cache for future use
            self.cache.set(cache_key, identifier, doc, version)

            # Store in project memory
            if self.memory_manager:
                self.memory_manager.store(
                    agent_id="knowledge_retriever",
                    title=f"Documentation: {module}.{function}",
                    content=doc.get("description", ""),
                    memory_type=MemoryType.LEARNING,
                    metadata={"external_doc": doc},
                    tags=["external_doc", language, module],
                    importance=5
                )

        return doc

    def should_fetch_external(self, context: Dict) -> bool:
        """
        Decide if we should fetch external knowledge.

        Heuristics:
        - New API/library we haven't seen before
        - Error pattern not in project memory
        - Explicit user request for documentation
        """

        # Check if this is a new API
        if context.get("new_api"):
            return True

        # Check if we have project memory for this
        if self.memory_manager and context.get("search_term"):
            memories = self.memory_manager.retrieve(
                search=context["search_term"],
                limit=1
            )
            if not memories:
                return True

        # Check for error patterns
        if context.get("error_pattern"):
            return True

        return False
```

### Step 4: Integrate with Agent Context Builder

````python
# Modification to existing memory integration code

def build_agent_context(agent_id: str, task: str, memory_manager: MemoryManager) -> str:
    """
    Build agent context from project memory + external knowledge.

    Changes from original:
    - Add external knowledge if needed
    - Keep project memory as primary source
    """

    context_parts = []

    # 1. Project memory (ALWAYS FIRST - HIGHEST PRIORITY)
    project_memories = memory_manager.retrieve(
        agent_id=agent_id,
        search=task,
        min_importance=5,
        limit=3
    )

    if project_memories:
        context_parts.append("## Project-Specific Knowledge (Primary Source)")
        for mem in project_memories:
            context_parts.append(f"- {mem.title}: {mem.content}")

    # 2. External knowledge (ADVISORY ONLY)
    external_retriever = ExternalKnowledgeRetriever(memory_manager)

    context = {
        "agent_id": agent_id,
        "search_term": task,
        "new_api": detect_new_api(task)  # Simple heuristic
    }

    if external_retriever.should_fetch_external(context):
        # Detect what documentation might be needed
        api_info = extract_api_info(task)
        if api_info:
            doc = external_retriever.get_function_doc(
                language=api_info["language"],
                module=api_info["module"],
                function=api_info["function"]
            )

            if doc:
                context_parts.append("\n## External Reference (Advisory)")
                context_parts.append(f"[{doc['source']}] {doc['module']}.{doc['function']}")
                context_parts.append(f"Description: {doc['description']}")
                if doc.get("signature"):
                    context_parts.append(f"Signature: `{doc['signature']}`")
                if doc.get("examples"):
                    context_parts.append(f"Example:\n```python\n{doc['examples'][0]}\n```")
                context_parts.append(f"Full docs: {doc['source_url']}")

    return "\n".join(context_parts)


def detect_new_api(task: str) -> bool:
    """Simple heuristic to detect if task involves new APIs."""
    # Look for import statements or function calls we haven't seen
    import_keywords = ["import", "from", "require"]
    return any(keyword in task.lower() for keyword in import_keywords)


def extract_api_info(task: str) -> Optional[Dict]:
    """
    Extract API information from task description.

    Simple pattern matching for common cases:
    - "use asyncio.run"
    - "call BlobServiceClient.create_container"
    - "import azure.storage.blob"
    """
    patterns = [
        r"use\s+(\w+)\.(\w+)",
        r"call\s+(\w+)\.(\w+)",
        r"import\s+(\w+(?:\.\w+)*)",
    ]

    import re
    for pattern in patterns:
        match = re.search(pattern, task, re.IGNORECASE)
        if match:
            parts = match.group(1).split(".")
            return {
                "language": "python",  # Default, could be smarter
                "module": parts[0] if len(parts) > 0 else "",
                "function": parts[1] if len(parts) > 1 else match.group(2) if match.lastindex > 1 else ""
            }

    return None
````

---

## Neo4j Integration (Phase 2 - After File Cache Works)

### Neo4j Schema Setup

```python
# src/amplihack/external_knowledge/neo4j_schema.py

from neo4j import GraphDatabase
from typing import Dict

class ExternalKnowledgeNeo4j:
    """Neo4j integration for external knowledge metadata."""

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self._create_schema()

    def _create_schema(self):
        """Create indexes and constraints."""
        with self.driver.session() as session:
            # Unique constraint on ExternalDoc ID
            session.run("""
                CREATE CONSTRAINT external_doc_id IF NOT EXISTS
                FOR (d:ExternalDoc) REQUIRE d.id IS UNIQUE
            """)

            # Index for fast lookups
            session.run("""
                CREATE INDEX external_doc_search IF NOT EXISTS
                FOR (d:ExternalDoc) ON (d.source, d.category, d.language)
            """)

            # Index for relevance scoring
            session.run("""
                CREATE INDEX external_doc_relevance IF NOT EXISTS
                FOR (d:ExternalDoc) ON (d.relevance_score)
            """)

            # APIReference unique constraint
            session.run("""
                CREATE CONSTRAINT api_reference_id IF NOT EXISTS
                FOR (a:APIReference) REQUIRE a.id IS UNIQUE
            """)

    def store_external_doc(self, doc: Dict):
        """
        Store external doc metadata in Neo4j.

        Full content stays in file cache.
        Neo4j stores only metadata for fast querying.
        """
        with self.driver.session() as session:
            cypher = """
            MERGE (doc:ExternalDoc {id: $id})
            SET doc.source = $source,
                doc.source_url = $source_url,
                doc.title = $title,
                doc.summary = $summary,
                doc.content_hash = $content_hash,
                doc.version = $version,
                doc.language = $language,
                doc.category = $category,
                doc.last_updated = datetime($last_updated),
                doc.access_count = COALESCE(doc.access_count, 0),
                doc.relevance_score = 0.5
            """

            session.run(cypher,
                       id=doc["id"],
                       source=doc["source"],
                       source_url=doc["source_url"],
                       title=doc["title"],
                       summary=doc.get("summary", "")[:500],  # Limit size
                       content_hash=doc["content_hash"],
                       version=doc.get("version"),
                       language=doc["language"],
                       category=doc["category"],
                       last_updated=doc["last_updated"])

    def link_to_code_file(self, doc_id: str, file_path: str, relationship: str = "EXPLAINS"):
        """Link external doc to code file."""
        with self.driver.session() as session:
            cypher = """
            MATCH (doc:ExternalDoc {id: $doc_id})
            MATCH (file:CodeFile {path: $file_path})
            MERGE (doc)-[r:""" + relationship + """]->(file)
            SET r.created_at = datetime()
            """

            session.run(cypher, doc_id=doc_id, file_path=file_path)

    def increment_access_count(self, doc_id: str):
        """Track document usage."""
        with self.driver.session() as session:
            cypher = """
            MATCH (doc:ExternalDoc {id: $doc_id})
            SET doc.access_count = doc.access_count + 1,
                doc.last_accessed = datetime()
            """

            session.run(cypher, doc_id=doc_id)

    def get_relevant_docs(self,
                         language: str,
                         category: str,
                         limit: int = 5) -> list:
        """Get most relevant docs for a language/category."""
        with self.driver.session() as session:
            cypher = """
            MATCH (doc:ExternalDoc)
            WHERE doc.language = $language
              AND doc.category = $category
            RETURN doc
            ORDER BY doc.relevance_score DESC, doc.access_count DESC
            LIMIT $limit
            """

            result = session.run(cypher, language=language, category=category, limit=limit)
            return [record["doc"] for record in result]

    def find_docs_for_api(self, module: str, function: str) -> list:
        """Find documentation for specific API."""
        with self.driver.session() as session:
            cypher = """
            MATCH (api:APIReference)-[:DOCUMENTED_IN]->(doc:ExternalDoc)
            WHERE api.namespace = $module
              AND api.function_name = $function
            RETURN doc, api
            """

            result = session.run(cypher, module=module, function=function)
            return [record for record in result]

    def close(self):
        """Close database connection."""
        self.driver.close()
```

### Linking Code to External Docs

```python
# src/amplihack/external_knowledge/code_linker.py

import ast
from pathlib import Path
from typing import List, Dict

class CodeToExternalLinker:
    """Automatically link code to external documentation."""

    def __init__(self, neo4j_manager: ExternalKnowledgeNeo4j, cache: ExternalKnowledgeCache):
        self.neo4j = neo4j_manager
        self.cache = cache
        self.retriever = ExternalKnowledgeRetriever()

    def analyze_and_link(self, file_path: Path):
        """
        Analyze code file and link to relevant external docs.

        Process:
        1. Parse code to extract imports and API calls
        2. For each import/call, find or fetch documentation
        3. Create Neo4j relationships
        """

        code = file_path.read_text()
        tree = ast.parse(code)

        # Extract imports
        imports = self._extract_imports(tree)
        for imp in imports:
            self._link_import_to_docs(imp, str(file_path))

        # Extract function calls
        api_calls = self._extract_api_calls(tree)
        for call in api_calls:
            self._link_api_call_to_docs(call, str(file_path))

    def _extract_imports(self, tree: ast.AST) -> List[Dict]:
        """Extract import statements."""
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "type": "import",
                        "module": alias.name,
                        "alias": alias.asname
                    })
            elif isinstance(node, ast.ImportFrom):
                imports.append({
                    "type": "from_import",
                    "module": node.module,
                    "names": [alias.name for alias in node.names]
                })

        return imports

    def _extract_api_calls(self, tree: ast.AST) -> List[Dict]:
        """Extract function/method calls."""
        calls = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    # Method call: obj.method()
                    calls.append({
                        "type": "method_call",
                        "object": self._get_name(node.func.value),
                        "method": node.func.attr,
                        "line": node.lineno
                    })
                elif isinstance(node.func, ast.Name):
                    # Function call: function()
                    calls.append({
                        "type": "function_call",
                        "function": node.func.id,
                        "line": node.lineno
                    })

        return calls

    def _get_name(self, node):
        """Get name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return ""

    def _link_import_to_docs(self, imp: Dict, file_path: str):
        """Link import to external documentation."""
        module = imp["module"]

        # Fetch or retrieve documentation
        doc = self.retriever.get_function_doc(
            language="python",
            module=module,
            function=""  # Module-level docs
        )

        if doc:
            # Store in Neo4j
            doc_id = f"{doc['source']}:{module}"
            self.neo4j.store_external_doc({
                "id": doc_id,
                "source": doc["source"],
                "source_url": doc["source_url"],
                "title": f"{module} documentation",
                "summary": doc.get("description", "")[:500],
                "content_hash": hash(doc["description"]),
                "version": doc.get("version"),
                "language": "python",
                "category": "api",
                "last_updated": doc["fetched_at"]
            })

            # Link to code file
            self.neo4j.link_to_code_file(doc_id, file_path, relationship="IMPORTED_BY")

    def _link_api_call_to_docs(self, call: Dict, file_path: str):
        """Link API call to external documentation."""
        if call["type"] == "method_call":
            # Try to resolve object type and find documentation
            # This is simplified - real implementation would need type inference
            pass
```

---

## Usage Examples

### Example 1: Simple Integration

```python
# In agent execution code

from amplihack.memory import MemoryManager
from amplihack.external_knowledge import ExternalKnowledgeRetriever

def execute_agent_with_external_knowledge(agent_id: str, task: str, session_id: str):
    """Execute agent with both project memory and external knowledge."""

    # Initialize memory and knowledge retriever
    memory = MemoryManager(session_id=session_id)
    knowledge = ExternalKnowledgeRetriever(memory)

    # Build comprehensive context
    context = build_agent_context(agent_id, task, memory)

    # Agent executes with enhanced context
    result = agent.execute(context, task)

    return result
```

### Example 2: Error-Driven Knowledge Fetching

```python
def handle_error_with_external_knowledge(error: Exception, code_context: str):
    """Fetch external knowledge to resolve error."""

    error_pattern = classify_error(error)

    # Check project memory first
    memory = MemoryManager()
    solutions = memory.retrieve(
        memory_type=MemoryType.PATTERN,
        search=str(error),
        tags=["error_solution"]
    )

    if solutions:
        return solutions[0].content

    # No project memory - query external knowledge
    knowledge = ExternalKnowledgeRetriever(memory)

    # Search for error pattern in StackOverflow
    external_solution = knowledge.search_error_solution(
        error_pattern=error_pattern,
        language="python",
        code_context=code_context
    )

    if external_solution:
        # Store in project memory for next time
        memory.store(
            agent_id="error_handler",
            title=f"Solution: {error_pattern}",
            content=external_solution["solution"],
            memory_type=MemoryType.PATTERN,
            tags=["error_solution", error_pattern],
            importance=8,
            metadata={
                "source": external_solution["source"],
                "url": external_solution["url"]
            }
        )

        return external_solution["solution"]

    return None
```

### Example 3: Automatic API Documentation Linking

```python
# Run after code generation or modification

from amplihack.external_knowledge import CodeToExternalLinker

def link_generated_code_to_docs(file_path: Path):
    """Automatically link generated code to external documentation."""

    # Initialize Neo4j manager
    neo4j = ExternalKnowledgeNeo4j(
        uri="bolt://localhost:7687",
        user="neo4j",
        password="password"
    )

    # Initialize linker
    linker = CodeToExternalLinker(neo4j, ExternalKnowledgeCache())

    # Analyze and link
    linker.analyze_and_link(file_path)

    print(f"Linked {file_path} to external documentation")
```

---

## Testing

### Test Cache Operations

```python
# tests/test_external_knowledge_cache.py

import pytest
from pathlib import Path
from amplihack.external_knowledge import ExternalKnowledgeCache

def test_cache_get_set():
    """Test basic cache operations."""
    cache = ExternalKnowledgeCache()

    # Store data
    data = {
        "title": "asyncio.run documentation",
        "description": "Run an async function",
        "example": "asyncio.run(main())"
    }

    cache.set("python_docs", "asyncio.run", data, version="3.12")

    # Retrieve data
    cached = cache.get("python_docs", "asyncio.run", version="3.12", max_age_days=7)

    assert cached is not None
    assert cached["data"]["title"] == data["title"]


def test_cache_expiration():
    """Test that old cache entries are considered stale."""
    cache = ExternalKnowledgeCache()

    # Store with very short max age
    cache.set("test_source", "test_id", {"test": "data"})

    # Immediately check with 0 day max age
    cached = cache.get("test_source", "test_id", max_age_days=0)

    assert cached is None  # Should be considered stale


def test_cache_invalidation():
    """Test cache invalidation."""
    cache = ExternalKnowledgeCache()

    cache.set("test_source", "test_id", {"test": "data"})

    # Verify it exists
    assert cache.get("test_source", "test_id") is not None

    # Invalidate
    cache.invalidate("test_source", "test_id")

    # Verify it's gone
    assert cache.get("test_source", "test_id") is None
```

### Test Integration with Memory System

```python
# tests/test_external_knowledge_integration.py

import pytest
from amplihack.memory import MemoryManager, MemoryType
from amplihack.external_knowledge import ExternalKnowledgeRetriever

def test_external_knowledge_with_memory_fallback():
    """Test that project memory is checked before external fetch."""

    memory = MemoryManager()
    retriever = ExternalKnowledgeRetriever(memory)

    # Store in project memory
    memory.store(
        agent_id="test_agent",
        title="asyncio.run usage",
        content="Use asyncio.run() to run async functions",
        memory_type=MemoryType.LEARNING,
        tags=["external_doc", "python", "asyncio"]
    )

    # Retrieve - should come from project memory (not external fetch)
    doc = retriever.get_function_doc("python", "asyncio", "run")

    # Should return project memory, not fetch externally
    assert doc is not None
```

---

## Performance Monitoring

```python
# src/amplihack/external_knowledge/monitoring.py

from typing import Dict
import time
from functools import wraps

class ExternalKnowledgeMonitor:
    """Monitor external knowledge performance."""

    def __init__(self):
        self.stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "external_fetches": 0,
            "total_query_time_ms": 0,
            "query_count": 0
        }

    def record_cache_hit(self):
        """Record cache hit."""
        self.stats["cache_hits"] += 1

    def record_cache_miss(self):
        """Record cache miss."""
        self.stats["cache_misses"] += 1

    def record_external_fetch(self, duration_ms: float):
        """Record external fetch."""
        self.stats["external_fetches"] += 1
        self.stats["total_query_time_ms"] += duration_ms

    def record_query(self, duration_ms: float):
        """Record query performance."""
        self.stats["query_count"] += 1
        self.stats["total_query_time_ms"] += duration_ms

    def get_stats(self) -> Dict:
        """Get performance statistics."""
        total_queries = self.stats["cache_hits"] + self.stats["cache_misses"]
        cache_hit_rate = self.stats["cache_hits"] / max(1, total_queries)

        avg_query_time = self.stats["total_query_time_ms"] / max(1, self.stats["query_count"])

        return {
            "cache_hit_rate": f"{cache_hit_rate:.2%}",
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "external_fetches": self.stats["external_fetches"],
            "avg_query_time_ms": f"{avg_query_time:.2f}",
            "total_queries": self.stats["query_count"]
        }

    def timed_query(self, func):
        """Decorator to time queries."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            duration_ms = (time.time() - start) * 1000
            self.record_query(duration_ms)
            return result
        return wrapper


# Global monitor instance
monitor = ExternalKnowledgeMonitor()
```

---

## File Structure

```
src/amplihack/external_knowledge/
├── __init__.py
├── cache.py                      # File-based cache (START HERE)
├── retriever.py                  # Main retrieval logic
├── neo4j_schema.py              # Neo4j integration (Phase 2)
├── code_linker.py               # Automatic code linking
├── monitoring.py                # Performance monitoring
└── sources/
    ├── __init__.py
    ├── python_docs.py           # Python official docs fetcher
    ├── ms_learn.py              # Microsoft Learn fetcher (TODO)
    ├── stackoverflow.py         # StackOverflow fetcher (TODO)
    └── mdn.py                   # MDN Web Docs fetcher (TODO)

tests/test_external_knowledge/
├── test_cache.py
├── test_retriever.py
├── test_integration.py
└── test_neo4j.py
```

---

## Progressive Implementation Checklist

### Phase 1: File Cache (Week 1)

- [ ] Implement `ExternalKnowledgeCache` class
- [ ] Implement `PythonDocsFetcher` class
- [ ] Write tests for cache operations
- [ ] Test with real Python docs
- [ ] Measure cache hit rate and performance

### Phase 2: Memory Integration (Week 2)

- [ ] Implement `ExternalKnowledgeRetriever` class
- [ ] Integrate with existing `MemoryManager`
- [ ] Add external knowledge to agent context builder
- [ ] Test with architect agent
- [ ] Measure impact on agent performance

### Phase 3: Neo4j Metadata (Week 3)

- [ ] Implement Neo4j schema
- [ ] Store metadata in Neo4j
- [ ] Implement code-to-doc linking
- [ ] Create Cypher queries for retrieval
- [ ] Benchmark Neo4j vs file-based performance

### Phase 4: Multiple Sources (Week 4)

- [ ] Implement MS Learn fetcher
- [ ] Implement StackOverflow fetcher
- [ ] Add source credibility scoring
- [ ] Implement relevance ranking
- [ ] Test multi-source retrieval

### Phase 5: Optimization (Week 5)

- [ ] Add performance monitoring
- [ ] Implement smart refresh strategy
- [ ] Optimize cache hit rate
- [ ] Add deprecation detection
- [ ] Document performance characteristics

---

**END OF IMPLEMENTATION GUIDE**

Start with Phase 1 (file-based cache). Measure performance. Only move to Neo4j if file-based cache becomes a bottleneck. This follows the project's ruthless simplicity philosophy.
