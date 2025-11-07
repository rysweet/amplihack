# External Knowledge Integration for Neo4j Memory Graph

**Design Document - November 2025**

## Executive Summary

This document outlines strategies for integrating external knowledge sources (API docs, developer guides, library references) into the Neo4j memory graph for coding agents. The design follows the project's ruthless simplicity philosophy: **start simple, measure, optimize based on need**.

## Core Philosophy

### Start Simple, Scale Smart

```
Phase 1: File-based cache (TODAY)
    ↓
Phase 2: Hybrid (cache + Neo4j references) (MEASURE FIRST)
    ↓
Phase 3: Full graph integration (ONLY IF NEEDED)
```

**Golden Rule**: External knowledge is ADVISORY. Project-specific memory always takes precedence.

---

## 1. Graph Schema Design

### Node Types

#### ExternalDoc Node
```cypher
CREATE (doc:ExternalDoc {
    id: string,                  // Unique identifier
    source: string,              // "ms_learn" | "python_docs" | "mdn" | "stackoverflow"
    source_url: string,          // Original URL
    title: string,               // Document title
    content_hash: string,        // SHA256 of content (for change detection)
    summary: string,             // AI-generated summary (200-500 chars)
    content_snippet: string,     // First 1000 chars or key excerpt
    last_updated: datetime,      // When we fetched it
    last_accessed: datetime,     // When agent used it
    access_count: integer,       // Usage tracking
    relevance_score: float,      // 0.0-1.0 based on usage patterns
    version: string,             // e.g., "Python 3.12", "Node 20"
    language: string,            // Programming language
    category: string,            // "api" | "tutorial" | "reference" | "guide"
    fetch_method: string         // "cache" | "api" | "web_scrape"
})
```

#### APIReference Node
```cypher
CREATE (api:APIReference {
    id: string,
    namespace: string,           // e.g., "azure.storage.blob"
    function_name: string,       // e.g., "BlobServiceClient.create_container"
    signature: string,           // Full function signature
    parameters: string,          // JSON array of parameters
    return_type: string,
    description: string,
    example_code: string,        // Working code example
    common_patterns: string,     // JSON array of usage patterns
    gotchas: string,             // Common pitfalls (JSON array)
    version_introduced: string,
    deprecated_in: string,       // null if not deprecated
    source_doc_id: string        // Link to full documentation
})
```

#### BestPractice Node
```cypher
CREATE (bp:BestPractice {
    id: string,
    title: string,
    domain: string,              // "authentication" | "async" | "security"
    description: string,
    when_to_use: string,
    when_not_to_use: string,
    example_code: string,
    anti_patterns: string,       // JSON array of what NOT to do
    related_apis: string,        // JSON array of API references
    confidence_score: float,     // 0.0-1.0 based on source credibility
    source_count: integer,       // How many sources agree
    last_validated: datetime
})
```

#### CodeExample Node
```cypher
CREATE (ex:CodeExample {
    id: string,
    title: string,
    language: string,
    framework: string,           // Optional: "Flask" | "FastAPI" | "Django"
    code: string,                // Full working example
    explanation: string,
    use_case: string,
    difficulty: string,          // "beginner" | "intermediate" | "advanced"
    execution_time_ms: integer,  // Performance metric if available
    dependencies: string,        // JSON array of required packages
    works_with_version: string,  // Version compatibility
    upvotes: integer,            // If from StackOverflow/GitHub
    source_url: string
})
```

### Relationships

#### Between External Knowledge and Code

```cypher
// Link to project code
(doc:ExternalDoc)-[:EXPLAINS]->(file:CodeFile)
(api:APIReference)-[:USED_IN]->(func:Function)
(bp:BestPractice)-[:APPLIED_IN]->(file:CodeFile)
(ex:CodeExample)-[:SIMILAR_TO]->(func:Function)

// Knowledge hierarchy
(api:APIReference)-[:DOCUMENTED_IN]->(doc:ExternalDoc)
(bp:BestPractice)-[:REFERENCES]->(api:APIReference)
(ex:CodeExample)-[:DEMONSTRATES]->(api:APIReference)
(ex:CodeExample)-[:IMPLEMENTS]->(bp:BestPractice)

// Cross-references
(doc:ExternalDoc)-[:RELATED_TO]->(doc2:ExternalDoc)
(api:APIReference)-[:ALTERNATIVE_TO]->(api2:APIReference)
(bp:BestPractice)-[:CONFLICTS_WITH]->(bp2:BestPractice)
```

#### Version Tracking

```cypher
// Version relationships
(api:APIReference)-[:VERSION_OF]->(api_v2:APIReference)
(doc:ExternalDoc)-[:SUPERSEDES]->(doc_old:ExternalDoc)

// Compatibility tracking
(api:APIReference)-[:COMPATIBLE_WITH {version: "3.12"}]->(lang:Language)
(bp:BestPractice)-[:DEPRECATED_IN {version: "4.0"}]->(framework:Framework)
```

#### Source Credibility

```cypher
// Source credibility metadata
(doc:ExternalDoc)-[:SOURCED_FROM]->(source:Source {
    name: "Microsoft Learn",
    trust_score: 0.95,         // Official docs = high trust
    last_verified: datetime
})

(ex:CodeExample)-[:SOURCED_FROM]->(source:Source {
    name: "StackOverflow",
    trust_score: 0.75,         // Community = medium trust
    answer_accepted: true,
    upvotes: 150
})
```

---

## 2. External Knowledge Sources

### Tier 1: Official Documentation (Highest Priority)

**Sources:**
- Microsoft Learn (Azure, .NET, TypeScript)
- Python.org official docs
- MDN Web Docs (JavaScript, Web APIs)
- Library-specific official docs

**Characteristics:**
- High credibility (trust_score: 0.9-1.0)
- Version-specific
- Regularly updated
- Comprehensive

**Fetch Strategy:**
```python
def fetch_official_docs(package_name: str, version: str) -> ExternalDoc:
    """
    Fetch official documentation with caching.

    Priority:
    1. Check local cache (< 7 days old)
    2. Fetch from official API if available
    3. Web scrape documentation site
    4. Fallback to cached version (even if stale)
    """
    cache_path = f"~/.amplihack/external_knowledge/{package_name}/{version}"

    # Check cache first
    if cache_exists(cache_path) and cache_age_days(cache_path) < 7:
        return load_from_cache(cache_path)

    # Fetch from source
    try:
        doc = fetch_from_official_source(package_name, version)
        save_to_cache(cache_path, doc)
        return doc
    except FetchError:
        # Graceful degradation: use stale cache
        return load_from_cache(cache_path) if cache_exists(cache_path) else None
```

### Tier 2: Curated Tutorials (Medium Priority)

**Sources:**
- Real Python
- FreeCodeCamp
- Official framework tutorials
- Microsoft sample code repositories

**Characteristics:**
- High quality (trust_score: 0.7-0.9)
- Practical, working examples
- Often more accessible than official docs
- May lag behind latest versions

**Fetch Strategy:**
```python
def fetch_tutorial_knowledge(topic: str, language: str) -> List[ExternalDoc]:
    """
    Fetch curated tutorials with quality filtering.

    Filter criteria:
    - Published within last 2 years
    - Author has track record (check source credibility)
    - Code examples compile/run
    - Clear explanations
    """
    candidates = search_tutorial_sources(topic, language)
    return [t for t in candidates if quality_score(t) > 0.7]
```

### Tier 3: Community Knowledge (Advisory Only)

**Sources:**
- StackOverflow (accepted answers with high upvotes)
- GitHub issues (maintainer responses)
- Reddit r/programming (highly upvoted)

**Characteristics:**
- Variable quality (trust_score: 0.4-0.8)
- Often practical, real-world solutions
- Version compatibility may vary
- Require validation

**Fetch Strategy:**
```python
def fetch_community_knowledge(error_pattern: str) -> List[CodeExample]:
    """
    Fetch community solutions with strict filtering.

    Only include:
    - StackOverflow: Accepted answer + 10+ upvotes
    - GitHub: Maintainer comment or closed issue
    - Must have code example
    - Must be <2 years old or version-agnostic
    """
    results = []

    # StackOverflow
    so_results = search_stackoverflow(error_pattern)
    results.extend([
        r for r in so_results
        if r.accepted and r.upvotes >= 10
    ])

    # GitHub issues
    gh_results = search_github_issues(error_pattern)
    results.extend([
        r for r in gh_results
        if r.author_is_maintainer or r.state == "closed"
    ])

    return results
```

### Tier 4: Library-Specific Knowledge

**Sources:**
- PyPI package documentation
- NPM package README
- Library changelog and migration guides

**Fetch Strategy:**
```python
def fetch_library_knowledge(package: str, version: str) -> Dict:
    """
    Fetch library-specific knowledge from package registries.

    Data extracted:
    - README (installation, quick start)
    - API reference (if available)
    - CHANGELOG (breaking changes, new features)
    - Common usage patterns from examples/
    """
    registry_data = fetch_from_registry(package, version)

    return {
        "readme": extract_readme(registry_data),
        "api_reference": extract_api_docs(registry_data),
        "changelog": extract_changelog(registry_data),
        "examples": extract_examples(registry_data)
    }
```

---

## 3. Caching vs. On-Demand Strategy

### Decision Matrix

| Knowledge Type | Cache Strategy | Reason |
|----------------|----------------|--------|
| Official API docs | **Cache + Refresh** | Stable, frequently used, version-specific |
| Tutorials | **Cache Long-term** | Don't change often, high value |
| StackOverflow | **On-demand + Short cache** | Dynamic, context-dependent |
| Library READMEs | **Cache + Version-aware** | Stable per version |
| Best practices | **Cache + Periodic refresh** | Evolve slowly |

### Caching Implementation

```python
class ExternalKnowledgeCache:
    """
    Simple file-based cache with TTL and version awareness.

    Philosophy: Files are simple, versionable, inspectable.
    Don't use a database until you measure the need.
    """

    def __init__(self, cache_dir: Path = Path.home() / ".amplihack" / "external_knowledge"):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True, mode=0o700)

    def cache_key(self, source: str, identifier: str, version: str = None) -> Path:
        """Generate cache file path."""
        key = f"{source}/{identifier}"
        if version:
            key += f"/{version}"
        return self.cache_dir / f"{key}.json"

    def get(self, source: str, identifier: str, version: str = None, max_age_days: int = 7) -> Optional[Dict]:
        """Get from cache if fresh enough."""
        cache_file = self.cache_key(source, identifier, version)

        if not cache_file.exists():
            return None

        # Check age
        age_days = (datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)).days
        if age_days > max_age_days:
            return None

        with cache_file.open() as f:
            return json.load(f)

    def set(self, source: str, identifier: str, data: Dict, version: str = None):
        """Save to cache."""
        cache_file = self.cache_key(source, identifier, version)
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        with cache_file.open('w') as f:
            json.dump(data, f, indent=2)

        # Secure permissions
        cache_file.chmod(0o600)
```

### When to Fetch On-Demand

**Fetch on-demand for:**
- Error-specific solutions (context-dependent)
- Rare API usage (< 5% of queries)
- Rapidly changing content (beta features)
- User-initiated searches

**Pre-cache for:**
- Common APIs (used in > 10% of projects)
- Core language features
- Framework essentials
- Known problem areas

---

## 4. Linking External Knowledge to Code

### Automatic Linking (Simple Heuristics)

```python
def link_external_knowledge_to_code(file: CodeFile, external_docs: List[ExternalDoc]):
    """
    Link external knowledge to code files using simple heuristics.

    Match criteria:
    1. Import statements → Library documentation
    2. API calls → API reference docs
    3. Error patterns → Solution examples
    4. Code patterns → Best practices
    """

    # Extract imports
    imports = extract_imports(file.content)
    for imp in imports:
        matching_docs = find_docs_for_package(imp.package_name)
        for doc in matching_docs:
            create_relationship(doc, "EXPLAINS", file)

    # Extract API calls
    api_calls = extract_api_calls(file.content)
    for call in api_calls:
        matching_api_refs = find_api_reference(call.namespace, call.function)
        for api_ref in matching_api_refs:
            create_relationship(api_ref, "USED_IN", file)

    # Pattern matching
    patterns = detect_code_patterns(file.content)
    for pattern in patterns:
        best_practices = find_best_practices(pattern.type)
        for bp in best_practices:
            create_relationship(bp, "APPLIED_IN", file)
```

### Manual Linking (Agent-Driven)

```python
def agent_link_external_knowledge(agent_id: str, code_context: str, decision: str):
    """
    Let agents explicitly link external knowledge they used.

    When an agent says:
    "I followed the Azure Blob Storage documentation for container creation"

    We extract:
    - Source: "Azure Blob Storage documentation"
    - Topic: "container creation"
    - Decision: <agent's decision>

    Then create explicit link in graph.
    """

    knowledge_references = extract_knowledge_references(decision)

    for ref in knowledge_references:
        external_doc = find_or_fetch_external_doc(ref.source, ref.topic)
        if external_doc:
            create_relationship(
                external_doc,
                "INFORMED_DECISION",
                decision_node,
                properties={"agent_id": agent_id, "confidence": ref.confidence}
            )
```

---

## 5. Version Tracking Strategy

### Version-Aware Querying

```cypher
// Query: Find API reference for Python 3.12
MATCH (api:APIReference)-[:COMPATIBLE_WITH]->(lang:Language {name: "Python"})
WHERE lang.version = "3.12" OR api.version_introduced <= "3.12"
  AND (api.deprecated_in IS NULL OR api.deprecated_in > "3.12")
RETURN api

// Query: Find best practices valid for current framework version
MATCH (bp:BestPractice)-[:APPLIES_TO]->(framework:Framework)
WHERE framework.name = "FastAPI"
  AND framework.version >= bp.min_version
  AND (bp.deprecated_in IS NULL OR framework.version < bp.deprecated_in)
RETURN bp
ORDER BY bp.confidence_score DESC
LIMIT 5
```

### Version Metadata Storage

```python
class VersionedKnowledge:
    """Track version-specific knowledge with deprecation."""

    def store_api_reference(self, api_data: Dict):
        """Store API with version metadata."""
        cypher = """
        MERGE (api:APIReference {id: $id})
        SET api.function_name = $function_name,
            api.signature = $signature,
            api.version_introduced = $version_introduced,
            api.deprecated_in = $deprecated_in,
            api.last_updated = datetime()

        // Link to language version
        MERGE (lang:Language {name: $language, version: $language_version})
        MERGE (api)-[:COMPATIBLE_WITH]->(lang)
        """

        self.neo4j.run(cypher, **api_data)

    def mark_deprecated(self, api_id: str, deprecated_in_version: str, replacement: str):
        """Mark API as deprecated and link to replacement."""
        cypher = """
        MATCH (old:APIReference {id: $api_id})
        SET old.deprecated_in = $deprecated_in

        MERGE (new:APIReference {id: $replacement_id})
        MERGE (old)-[:REPLACED_BY {in_version: $deprecated_in}]->(new)
        """

        self.neo4j.run(cypher,
                      api_id=api_id,
                      deprecated_in=deprecated_in_version,
                      replacement_id=replacement)
```

---

## 6. Ranking & Relevance

### Source Credibility Scoring

```python
SOURCE_CREDIBILITY = {
    # Official sources
    "microsoft_learn": 0.95,
    "python_docs": 0.95,
    "mdn": 0.95,

    # Curated content
    "real_python": 0.85,
    "official_tutorials": 0.85,

    # Community (filtered)
    "stackoverflow_accepted": 0.75,
    "github_maintainer": 0.80,
    "reddit_highvote": 0.60,

    # Unknown/unverified
    "blog_unknown": 0.40,
    "forum_post": 0.35
}

def calculate_relevance_score(doc: ExternalDoc, context: str) -> float:
    """
    Calculate relevance score based on multiple factors.

    Factors (weighted):
    - Source credibility (40%)
    - Content freshness (20%)
    - Usage frequency (20%)
    - Text similarity to context (20%)
    """

    # Base credibility
    credibility = SOURCE_CREDIBILITY.get(doc.source, 0.5)

    # Freshness score (decay over time)
    age_days = (datetime.now() - doc.last_updated).days
    freshness = max(0.0, 1.0 - (age_days / 730.0))  # 2-year decay

    # Usage score (more used = more relevant)
    usage = min(1.0, doc.access_count / 100.0)

    # Semantic similarity (simple keyword matching for now)
    similarity = calculate_text_similarity(doc.summary, context)

    # Weighted average
    score = (
        credibility * 0.40 +
        freshness * 0.20 +
        usage * 0.20 +
        similarity * 0.20
    )

    return score
```

### Learning Which Sources Work

```python
class ExternalKnowledgeFeedback:
    """Track which external knowledge actually helped."""

    def record_usage(self, doc_id: str, agent_id: str, task_outcome: str):
        """Record when external knowledge was used and outcome."""
        cypher = """
        MATCH (doc:ExternalDoc {id: $doc_id})
        SET doc.access_count = doc.access_count + 1,
            doc.last_accessed = datetime()

        // Record outcome
        CREATE (usage:KnowledgeUsage {
            doc_id: $doc_id,
            agent_id: $agent_id,
            outcome: $outcome,
            timestamp: datetime()
        })
        """

        self.neo4j.run(cypher, doc_id=doc_id, agent_id=agent_id, outcome=task_outcome)

    def get_effective_sources(self, domain: str) -> List[ExternalDoc]:
        """Find external knowledge that led to successful outcomes."""
        cypher = """
        MATCH (doc:ExternalDoc {category: $domain})
        OPTIONAL MATCH (doc)<-[:USED]-(usage:KnowledgeUsage {outcome: "success"})
        WITH doc, count(usage) as success_count
        WHERE success_count > 5
        RETURN doc
        ORDER BY success_count DESC, doc.relevance_score DESC
        LIMIT 10
        """

        return self.neo4j.run(cypher, domain=domain)
```

---

## 7. Retrieval Strategies

### When to Query External Knowledge

```python
class ExternalKnowledgeRetriever:
    """Decide when and what external knowledge to retrieve."""

    def should_query_external(self, context: AgentContext) -> bool:
        """
        Decide if external knowledge would help.

        Query external knowledge if:
        1. Agent is encountering new library/API
        2. Error pattern not in project memory
        3. Best practice request for unfamiliar domain
        4. User explicitly asks for documentation

        Don't query if:
        1. Project memory has sufficient context
        2. Agent has handled this pattern before
        3. Pure refactoring (no new APIs)
        """

        # Check project memory first
        project_memories = self.memory_manager.retrieve(
            agent_id=context.agent_id,
            memory_type=MemoryType.PATTERN,
            search=context.current_task
        )

        if len(project_memories) >= 3:
            # We have sufficient project-specific knowledge
            return False

        # Check if task involves new APIs
        new_apis = self.detect_new_apis(context.code_context)
        if new_apis:
            return True

        # Check for error patterns
        if context.error_pattern and not self.has_solution_in_project_memory(context.error_pattern):
            return True

        return False

    def retrieve_relevant_knowledge(self, context: AgentContext, max_items: int = 5) -> List[ExternalDoc]:
        """
        Retrieve most relevant external knowledge.

        Strategy:
        1. Identify knowledge gaps in project memory
        2. Query external knowledge to fill gaps
        3. Rank by relevance
        4. Return top N items
        5. Cache for future use
        """

        knowledge_gaps = self.identify_knowledge_gaps(context)

        external_docs = []
        for gap in knowledge_gaps:
            docs = self.query_external_sources(
                topic=gap.topic,
                language=gap.language,
                version=gap.version
            )
            external_docs.extend(docs)

        # Rank by relevance
        ranked_docs = sorted(
            external_docs,
            key=lambda d: calculate_relevance_score(d, context.current_task),
            reverse=True
        )

        return ranked_docs[:max_items]
```

### Combining Project Memory + External Knowledge

```python
def build_agent_context(agent_id: str, task: str) -> str:
    """
    Build comprehensive context from project memory + external knowledge.

    Priority:
    1. Project-specific memories (HIGHEST)
    2. Previously successful external knowledge
    3. Fresh external knowledge (if gaps exist)
    """

    context_parts = []

    # Project memory (always first)
    project_memories = memory_manager.retrieve(
        agent_id=agent_id,
        search=task,
        min_importance=5
    )

    if project_memories:
        context_parts.append("## Project-Specific Knowledge")
        for mem in project_memories[:3]:  # Top 3
            context_parts.append(f"- {mem.title}: {mem.content}")

    # External knowledge (if needed)
    context = AgentContext(agent_id=agent_id, current_task=task)
    if external_retriever.should_query_external(context):
        external_docs = external_retriever.retrieve_relevant_knowledge(context, max_items=2)

        if external_docs:
            context_parts.append("\n## External Reference (Advisory)")
            for doc in external_docs:
                context_parts.append(f"- [{doc.source}] {doc.title}: {doc.summary}")
                if doc.example_code:
                    context_parts.append(f"  Example:\n  ```\n  {doc.example_code}\n  ```")

    return "\n".join(context_parts)
```

---

## 8. Keeping Knowledge Up-to-Date

### Refresh Strategy

```python
class ExternalKnowledgeRefresher:
    """Keep external knowledge fresh without over-fetching."""

    # Refresh frequencies by source type
    REFRESH_INTERVALS = {
        "official_docs": timedelta(days=30),      # Stable
        "tutorials": timedelta(days=90),           # Slow-changing
        "community": timedelta(days=7),            # Dynamic
        "library_specific": timedelta(days=14)     # Version-dependent
    }

    def needs_refresh(self, doc: ExternalDoc) -> bool:
        """Check if document needs refreshing."""
        age = datetime.now() - doc.last_updated
        interval = self.REFRESH_INTERVALS.get(doc.category, timedelta(days=30))

        # Refresh if:
        # 1. Older than refresh interval
        # 2. Has been accessed recently (indicates value)
        # 3. Is in top 20% by access count (high-value docs)

        is_stale = age > interval
        is_valuable = doc.access_count > self.get_access_count_percentile(0.8)
        recently_used = (datetime.now() - doc.last_accessed).days < 7

        return is_stale and (is_valuable or recently_used)

    def refresh_knowledge(self, doc: ExternalDoc):
        """Refresh external knowledge document."""
        try:
            # Fetch fresh content
            fresh_content = fetch_from_source(doc.source_url)

            # Check if content changed
            new_hash = hashlib.sha256(fresh_content.encode()).hexdigest()

            if new_hash != doc.content_hash:
                # Content changed - update
                doc.content_hash = new_hash
                doc.summary = generate_summary(fresh_content)
                doc.last_updated = datetime.now()

                # Log change for version tracking
                self.log_knowledge_change(doc.id, "content_updated")

        except FetchError:
            # Graceful degradation: keep using cached version
            self.log_knowledge_change(doc.id, "fetch_failed")
```

### Deprecation Detection

```python
def detect_deprecations(api_ref: APIReference) -> Optional[Dict]:
    """
    Detect if API has been deprecated.

    Methods:
    1. Check official deprecation notices in docs
    2. Monitor library changelogs
    3. Track community warnings
    """

    # Check official docs for deprecation markers
    doc_content = fetch_current_docs(api_ref.namespace)
    if "deprecated" in doc_content.lower():
        deprecation_info = extract_deprecation_info(doc_content)
        return {
            "deprecated": True,
            "deprecated_in": deprecation_info.version,
            "replacement": deprecation_info.replacement_api,
            "reason": deprecation_info.reason
        }

    # Check changelog
    changelog = fetch_changelog(api_ref.namespace)
    deprecation = find_deprecation_in_changelog(changelog, api_ref.function_name)
    if deprecation:
        return deprecation

    return None
```

---

## 9. Handling Large External Knowledge Bases

### Problem: 100k+ Documents

**Challenge**: Can't load all external knowledge into agent context (token limits)

**Solution**: Tiered retrieval + aggressive filtering

```python
class LargeKnowledgeBaseHandler:
    """Handle large external knowledge bases efficiently."""

    def __init__(self):
        self.index = ExternalKnowledgeIndex()  # Fast lookup structure
        self.cache = LRUCache(maxsize=1000)     # In-memory cache of frequently used docs

    def query(self, context: str, language: str, max_results: int = 5) -> List[ExternalDoc]:
        """
        Query large knowledge base efficiently.

        Strategy:
        1. Fast keyword filtering (reduce 100k → 1k)
        2. Semantic ranking (reduce 1k → 100)
        3. Relevance scoring (reduce 100 → 5)
        """

        # Stage 1: Fast keyword filter
        candidates = self.index.keyword_search(
            context=context,
            language=language,
            max_candidates=1000
        )

        # Stage 2: Semantic ranking
        if len(candidates) > 100:
            candidates = self.semantic_rank(candidates, context, top_k=100)

        # Stage 3: Detailed relevance scoring
        ranked_results = []
        for doc in candidates:
            score = calculate_relevance_score(doc, context)
            ranked_results.append((score, doc))

        ranked_results.sort(reverse=True, key=lambda x: x[0])

        return [doc for score, doc in ranked_results[:max_results]]

    def build_index(self):
        """Build efficient search index for large knowledge base."""
        # Use inverted index for fast keyword lookup
        index = {}

        for doc in self.load_all_docs():
            # Extract keywords
            keywords = extract_keywords(doc.title + " " + doc.summary)

            for keyword in keywords:
                if keyword not in index:
                    index[keyword] = []
                index[keyword].append(doc.id)

        return index
```

### Metadata-Only Storage

```python
def store_metadata_only(doc: ExternalDoc):
    """
    Store only metadata in Neo4j, full content in file cache.

    Neo4j storage (lightweight):
    - id, title, source, source_url
    - summary (500 chars max)
    - version, language, category
    - relevance_score, access_count

    File cache (full content):
    - Complete documentation
    - Code examples
    - Full API reference
    """

    # Store metadata in Neo4j
    cypher = """
    MERGE (doc:ExternalDoc {id: $id})
    SET doc.title = $title,
        doc.source = $source,
        doc.source_url = $source_url,
        doc.summary = $summary,
        doc.version = $version,
        doc.relevance_score = $relevance_score
    """

    neo4j.run(cypher, **doc.metadata)

    # Store full content in file cache
    cache_path = get_cache_path(doc.id)
    save_full_content(cache_path, doc.full_content)
```

---

## 10. Performance Considerations

### Query Performance Targets

```
Target: <100ms for external knowledge queries
Breakdown:
- Relevance check: <10ms (decide if external knowledge needed)
- Cache lookup: <20ms (check if already cached)
- Neo4j query: <50ms (fetch metadata)
- Full content fetch: <20ms (from file cache)
```

### Optimization Strategies

```python
# 1. Pre-compute relevance scores
def precompute_relevance_scores():
    """Run nightly to update relevance scores."""
    cypher = """
    MATCH (doc:ExternalDoc)
    SET doc.relevance_score =
        (doc.access_count * 0.4) +
        ((1.0 - (duration.between(doc.last_updated, datetime()).days / 730.0)) * 0.3) +
        (size([(doc)<-[:USED]-(usage:KnowledgeUsage {outcome: "success"}) | usage]) * 0.3)
    """
    neo4j.run(cypher)

# 2. Index frequently queried paths
neo4j.run("""
    CREATE INDEX external_doc_category IF NOT EXISTS
    FOR (d:ExternalDoc) ON (d.category, d.language, d.relevance_score)
""")

# 3. Materialize common queries
def materialize_top_docs():
    """Cache top documents for each category."""
    cypher = """
    MATCH (doc:ExternalDoc)
    WHERE doc.category = $category AND doc.language = $language
    WITH doc
    ORDER BY doc.relevance_score DESC
    LIMIT 20
    RETURN doc
    """

    for category in CATEGORIES:
        for language in LANGUAGES:
            results = neo4j.run(cypher, category=category, language=language)
            cache_results(f"top_{category}_{language}", results)
```

---

## 11. Integration Code Examples

### Example 1: Agent Queries External Knowledge

```python
class AgentWithExternalKnowledge:
    """Agent that uses both project memory and external knowledge."""

    def __init__(self, agent_id: str, session_id: str):
        self.agent_id = agent_id
        self.memory_manager = MemoryManager(session_id=session_id)
        self.external_knowledge = ExternalKnowledgeRetriever()

    def execute_task(self, task: str) -> str:
        """Execute task with comprehensive knowledge context."""

        # Build context from multiple sources
        context = self.build_comprehensive_context(task)

        # Execute with context
        result = self.execute_with_context(context, task)

        # Record what knowledge was useful
        self.record_knowledge_usage(context, result)

        return result

    def build_comprehensive_context(self, task: str) -> str:
        """Build context from project memory + external knowledge."""

        context_parts = []

        # 1. Project-specific memories (highest priority)
        project_memories = self.memory_manager.retrieve(
            agent_id=self.agent_id,
            search=task,
            min_importance=5,
            limit=3
        )

        if project_memories:
            context_parts.append("## Project Memory (Proven Patterns)")
            for mem in project_memories:
                context_parts.append(f"- {mem.title}: {mem.content}")

        # 2. External knowledge (if needed)
        agent_context = AgentContext(
            agent_id=self.agent_id,
            current_task=task,
            code_context=self.get_current_code_context()
        )

        if self.external_knowledge.should_query_external(agent_context):
            external_docs = self.external_knowledge.retrieve_relevant_knowledge(
                agent_context,
                max_items=2
            )

            if external_docs:
                context_parts.append("\n## External Reference (Advisory)")
                for doc in external_docs:
                    context_parts.append(
                        f"- [{doc.source}] {doc.title}\n"
                        f"  {doc.summary}\n"
                        f"  URL: {doc.source_url}"
                    )

        return "\n".join(context_parts)
```

### Example 2: Automatic API Documentation Linking

```python
def link_api_usage_to_docs(code_file: Path):
    """
    Automatically link API usage in code to external documentation.

    Process:
    1. Parse code to find API calls
    2. Query external knowledge for matching API docs
    3. Create relationships in Neo4j
    4. Cache for fast retrieval
    """

    # Parse code
    tree = ast.parse(code_file.read_text())
    api_calls = extract_api_calls(tree)

    for call in api_calls:
        # Find or fetch API documentation
        api_doc = find_or_fetch_api_doc(
            namespace=call.module,
            function=call.function_name,
            version=detect_package_version(call.module)
        )

        if api_doc:
            # Create relationship in Neo4j
            cypher = """
            MATCH (file:CodeFile {path: $file_path})
            MATCH (api:APIReference {id: $api_id})
            MERGE (api)-[:USED_IN {
                line_number: $line_number,
                context: $context
            }]->(file)
            """

            neo4j.run(cypher,
                     file_path=str(code_file),
                     api_id=api_doc.id,
                     line_number=call.line_number,
                     context=call.context_code)
```

### Example 3: Error-Driven Knowledge Fetching

```python
class ErrorDrivenKnowledgeFetcher:
    """Fetch external knowledge based on error patterns."""

    def handle_error(self, error: Exception, code_context: str) -> Optional[str]:
        """
        Fetch relevant external knowledge for error resolution.

        Priority:
        1. Check project memory for previous solutions
        2. Query external knowledge for error pattern
        3. Return most relevant solution
        """

        error_pattern = classify_error(error)

        # Check project memory first
        project_solutions = self.memory_manager.retrieve(
            memory_type=MemoryType.PATTERN,
            search=str(error),
            tags=["error_solution"]
        )

        if project_solutions:
            # We've solved this before
            return project_solutions[0].content

        # Query external knowledge
        external_solutions = self.query_external_error_solutions(
            error_pattern=error_pattern,
            code_context=code_context
        )

        if external_solutions:
            best_solution = external_solutions[0]

            # Store in project memory for future
            self.memory_manager.store(
                agent_id="error_handler",
                title=f"Solution: {error_pattern}",
                content=best_solution.solution,
                memory_type=MemoryType.PATTERN,
                tags=["error_solution", error_pattern],
                importance=8,
                metadata={
                    "external_source": best_solution.source,
                    "source_url": best_solution.url
                }
            )

            return best_solution.solution

        return None
```

---

## 12. Progressive Implementation Plan

### Phase 1: Foundation (Week 1)

**Goal**: File-based cache + basic Neo4j metadata

**Tasks**:
1. Implement `ExternalKnowledgeCache` (file-based)
2. Create Neo4j schema (ExternalDoc, APIReference nodes)
3. Build basic fetch functions for official docs
4. Test with single source (e.g., Python docs)

**Deliverable**: Can fetch and cache Python official docs

### Phase 2: Integration (Week 2)

**Goal**: Integrate with existing memory system

**Tasks**:
1. Implement `should_query_external()` logic
2. Add external knowledge to agent context builder
3. Create Neo4j relationships to code files
4. Test with architect agent

**Deliverable**: Agents can query external knowledge when needed

### Phase 3: Multiple Sources (Week 3)

**Goal**: Support multiple knowledge sources

**Tasks**:
1. Add MS Learn fetcher
2. Add MDN fetcher
3. Add StackOverflow fetcher (with filtering)
4. Implement source credibility scoring

**Deliverable**: Multi-source knowledge retrieval

### Phase 4: Optimization (Week 4)

**Goal**: Performance and ranking

**Tasks**:
1. Implement relevance scoring
2. Add usage tracking
3. Build recommendation engine
4. Performance testing

**Deliverable**: <100ms query performance

### Phase 5: Learning (Week 5)

**Goal**: Adaptive knowledge retrieval

**Tasks**:
1. Track which knowledge helps
2. Implement feedback loop
3. Auto-refresh stale content
4. Deprecation detection

**Deliverable**: Self-improving knowledge system

---

## 13. Success Metrics

### Performance Metrics
- External knowledge query time: <100ms (p95)
- Cache hit rate: >80%
- Neo4j query time: <50ms (p95)

### Quality Metrics
- Source credibility score: >0.7 average
- Knowledge freshness: <30 days average age for high-use docs
- Agent satisfaction: Track when external knowledge was useful

### Usage Metrics
- External knowledge query rate: 20-40% of agent tasks
- Cache efficiency: >80% hit rate
- Storage efficiency: <100MB for 10k documents (metadata only)

---

## 14. Monitoring & Maintenance

### Daily Operations

```python
def daily_maintenance():
    """Daily maintenance tasks."""
    # 1. Update relevance scores
    precompute_relevance_scores()

    # 2. Refresh high-value docs
    refresh_high_value_docs()

    # 3. Clean up unused cache
    cleanup_cache(older_than_days=90)
```

### Weekly Analysis

```python
def weekly_analysis():
    """Analyze external knowledge usage patterns."""
    # 1. Top 20 most used docs
    top_docs = get_top_documents(limit=20)

    # 2. Unused docs (consider removing)
    unused_docs = get_documents_never_accessed(age_days=90)

    # 3. Source effectiveness
    source_stats = analyze_source_effectiveness()

    # 4. Knowledge gaps
    gaps = identify_knowledge_gaps()

    return {
        "top_docs": top_docs,
        "unused_docs": unused_docs,
        "source_stats": source_stats,
        "gaps": gaps
    }
```

---

## 15. Key Principles (Summary)

1. **Project Memory First**: External knowledge is advisory, never replaces project-specific memory
2. **Cache Aggressively**: File-based cache with smart refresh
3. **Measure Before Optimizing**: Start simple, measure, optimize based on data
4. **Version Awareness**: Always track version compatibility
5. **Source Credibility**: Rank sources by trust score
6. **Graceful Degradation**: System works even if external knowledge unavailable
7. **Lightweight Metadata**: Store metadata in Neo4j, full content in files
8. **Learning Loop**: Track what works, improve recommendations
9. **Performance First**: <100ms query target
10. **User Control**: Never override explicit user requirements

---

## File Locations

```
Implementation:
- src/amplihack/external_knowledge/cache.py
- src/amplihack/external_knowledge/retriever.py
- src/amplihack/external_knowledge/neo4j_schema.py
- src/amplihack/external_knowledge/sources/

Data Storage:
- ~/.amplihack/external_knowledge/cache/    (file cache)
- Neo4j database (metadata + relationships)

Integration:
- src/amplihack/memory/manager.py           (add external knowledge queries)
- .claude/agents/*/                         (no changes - agents remain stateless)
```

---

**END OF DESIGN DOCUMENT**

This design follows the project's ruthless simplicity philosophy: start with file-based caching, measure what's needed, and only add Neo4j complexity where it provides clear value (relationships, fast metadata queries, version tracking). External knowledge is always advisory and never overrides project-specific memory.
