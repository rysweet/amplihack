#!/usr/bin/env python3
"""5-Agent Hive Mind Evaluation: Real performance test of UnifiedHiveMind.

Tests the full pipeline: fact storage, promotion, gossip, event propagation,
and cross-domain retrieval across 5 specialized agents.

5 Agents, 5 Domains:
    1. networking_agent   -- TCP/IP, DNS, load balancing, CDNs, HTTP/2, WebSocket
    2. storage_agent      -- SQL/NoSQL databases, caching, object storage, replication
    3. compute_agent      -- Containers, Kubernetes, serverless, VMs, auto-scaling
    4. security_agent     -- TLS, auth (OAuth, JWT), WAF, vulnerability scanning
    5. observability_agent -- Logging (ELK), metrics (Prometheus), tracing (Jaeger)

Each agent learns 25 unique facts (125 total). Evaluation asks 30 questions
in three categories (single-domain, cross-domain, synthesis) and compares
isolated (local-only) performance against hive-enabled (local+hive+gossip).

Usage:
    uv run python experiments/hive_mind/run_5agent_real_eval.py
"""

from __future__ import annotations

import os
import sys
import time
from typing import Any

# Allow running from repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from amplihack.agents.goal_seeking.hive_mind.unified import (  # type: ignore[import-not-found]
    HiveMindAgent,
    HiveMindConfig,
    UnifiedHiveMind,
)

# ---------------------------------------------------------------------------
# Domain knowledge: 25 facts per agent (125 total)
# Each fact: (content, confidence, tags)
# ---------------------------------------------------------------------------

NETWORKING_FACTS: list[tuple[str, float, list[str]]] = [
    (
        "TCP provides reliable ordered delivery of data packets using acknowledgments",
        0.96,
        ["networking", "tcp"],
    ),
    (
        "UDP is connectionless and faster than TCP but does not guarantee delivery",
        0.93,
        ["networking", "udp"],
    ),
    (
        "DNS translates human-readable domain names to IP addresses using recursive resolvers",
        0.97,
        ["networking", "dns"],
    ),
    (
        "Load balancers distribute incoming traffic across multiple backend servers",
        0.95,
        ["networking", "load-balancing"],
    ),
    (
        "CDNs cache static content at edge locations closer to end users",
        0.94,
        ["networking", "cdn"],
    ),
    (
        "HTTP/2 multiplexes multiple streams over a single TCP connection",
        0.92,
        ["networking", "http2"],
    ),
    (
        "WebSocket enables full-duplex bidirectional communication over a single TCP connection",
        0.91,
        ["networking", "websocket"],
    ),
    (
        "BGP is the routing protocol that exchanges routes between autonomous systems on the internet",
        0.89,
        ["networking", "bgp"],
    ),
    (
        "NAT translates private IP addresses to public addresses for internet access",
        0.90,
        ["networking", "nat"],
    ),
    (
        "CIDR notation specifies IP address ranges using prefix length like /24",
        0.88,
        ["networking", "cidr"],
    ),
    (
        "Reverse proxies terminate client connections and forward requests to backend servers",
        0.91,
        ["networking", "reverse-proxy"],
    ),
    (
        "gRPC uses HTTP/2 and protocol buffers for efficient remote procedure calls",
        0.90,
        ["networking", "grpc"],
    ),
    (
        "QUIC protocol provides encrypted transport with reduced connection latency",
        0.87,
        ["networking", "quic"],
    ),
    (
        "ARP resolves IP addresses to MAC addresses on local network segments",
        0.86,
        ["networking", "arp"],
    ),
    (
        "VLANs segment a physical network into isolated broadcast domains",
        0.85,
        ["networking", "vlan"],
    ),
    (
        "DHCP automatically assigns IP addresses to devices on a network",
        0.93,
        ["networking", "dhcp"],
    ),
    (
        "TLS handshake establishes encrypted connections using certificate exchange",
        0.94,
        ["networking", "tls"],
    ),
    (
        "ICMP is used by ping and traceroute to diagnose network connectivity issues",
        0.88,
        ["networking", "icmp"],
    ),
    (
        "Anycast routing directs traffic to the nearest server using the same IP address",
        0.84,
        ["networking", "anycast"],
    ),
    ("SNI allows multiple TLS certificates on a single IP address", 0.83, ["networking", "sni"]),
    (
        "MTU determines the maximum packet size that can traverse a network link",
        0.82,
        ["networking", "mtu"],
    ),
    (
        "Service mesh provides observability and traffic management between microservices",
        0.90,
        ["networking", "service-mesh"],
    ),
    (
        "DNS round-robin distributes requests across multiple servers using multiple A records",
        0.86,
        ["networking", "dns"],
    ),
    (
        "TCP congestion control algorithms like CUBIC prevent network overload",
        0.85,
        ["networking", "tcp"],
    ),
    (
        "Layer 7 load balancing inspects HTTP headers to make routing decisions",
        0.91,
        ["networking", "load-balancing"],
    ),
]

STORAGE_FACTS: list[tuple[str, float, list[str]]] = [
    (
        "PostgreSQL is an advanced relational database with ACID compliance and JSON support",
        0.96,
        ["storage", "postgresql", "sql"],
    ),
    (
        "Redis provides sub-millisecond in-memory caching with data structures",
        0.95,
        ["storage", "redis", "caching"],
    ),
    (
        "MongoDB stores documents in flexible BSON format for schema-less data",
        0.93,
        ["storage", "mongodb", "nosql"],
    ),
    (
        "Memcached is a distributed memory caching system for reducing database load",
        0.91,
        ["storage", "memcached", "caching"],
    ),
    (
        "S3 object storage provides virtually unlimited scalable storage via HTTP API",
        0.94,
        ["storage", "s3", "object-storage"],
    ),
    (
        "Database sharding distributes rows across multiple nodes for horizontal scaling",
        0.92,
        ["storage", "sharding"],
    ),
    (
        "Read replicas offload SELECT queries from the primary database to improve throughput",
        0.91,
        ["storage", "replication"],
    ),
    (
        "Write-ahead logging ensures database durability by recording changes before applying them",
        0.90,
        ["storage", "wal"],
    ),
    (
        "Cassandra provides high-availability distributed storage with tunable consistency",
        0.89,
        ["storage", "cassandra", "nosql"],
    ),
    (
        "Database indexing creates B-tree structures that speed up query lookups dramatically",
        0.95,
        ["storage", "indexing"],
    ),
    (
        "Connection pooling reuses database connections to reduce overhead from repeated handshakes",
        0.90,
        ["storage", "connection-pooling"],
    ),
    (
        "Denormalization trades storage space for faster read performance by duplicating data",
        0.87,
        ["storage", "denormalization"],
    ),
    (
        "MVCC allows multiple transactions to read data without blocking writers",
        0.88,
        ["storage", "mvcc"],
    ),
    (
        "Elasticsearch provides full-text search with inverted index data structures",
        0.92,
        ["storage", "elasticsearch", "search"],
    ),
    (
        "Data replication across regions provides disaster recovery and low-latency reads",
        0.91,
        ["storage", "replication"],
    ),
    (
        "LSM trees optimize write-heavy workloads by batching writes to disk",
        0.85,
        ["storage", "lsm"],
    ),
    (
        "Bloom filters provide probabilistic set membership checks with minimal memory",
        0.84,
        ["storage", "bloom-filter"],
    ),
    (
        "Cache invalidation strategies include TTL, write-through, and write-behind patterns",
        0.89,
        ["storage", "caching"],
    ),
    (
        "CockroachDB provides distributed SQL with serializable isolation across regions",
        0.86,
        ["storage", "cockroachdb", "sql"],
    ),
    (
        "Redis Cluster partitions data across multiple nodes using hash slots",
        0.88,
        ["storage", "redis", "clustering"],
    ),
    (
        "Columnar storage like Parquet optimizes analytical queries by storing data by column",
        0.87,
        ["storage", "columnar"],
    ),
    (
        "Event sourcing stores every state change as an immutable event log",
        0.86,
        ["storage", "event-sourcing"],
    ),
    (
        "GraphQL queries let clients request exactly the data fields they need",
        0.85,
        ["storage", "graphql"],
    ),
    (
        "Database vacuum reclaims storage from deleted or updated rows in PostgreSQL",
        0.83,
        ["storage", "postgresql"],
    ),
    (
        "Consistent hashing distributes keys across nodes with minimal remapping during scaling",
        0.90,
        ["storage", "consistent-hashing"],
    ),
]

COMPUTE_FACTS: list[tuple[str, float, list[str]]] = [
    (
        "Docker containers package applications with dependencies in isolated filesystem layers",
        0.96,
        ["compute", "docker", "containers"],
    ),
    (
        "Kubernetes orchestrates container deployment scaling and self-healing across clusters",
        0.97,
        ["compute", "kubernetes", "k8s"],
    ),
    (
        "Serverless functions execute code on demand without managing server infrastructure",
        0.94,
        ["compute", "serverless"],
    ),
    (
        "Virtual machines provide hardware-level isolation using hypervisor technology",
        0.93,
        ["compute", "vm", "virtualization"],
    ),
    (
        "Auto-scaling adjusts compute capacity based on CPU utilization and request metrics",
        0.92,
        ["compute", "auto-scaling"],
    ),
    (
        "GPU computing accelerates parallel workloads like machine learning and rendering",
        0.91,
        ["compute", "gpu"],
    ),
    (
        "Kubernetes pods are the smallest deployable units containing one or more containers",
        0.95,
        ["compute", "kubernetes", "pods"],
    ),
    (
        "Horizontal pod autoscaler adjusts replica count based on CPU and custom metrics",
        0.90,
        ["compute", "kubernetes", "hpa"],
    ),
    (
        "Container registries like ECR store and distribute Docker images to clusters",
        0.89,
        ["compute", "registry"],
    ),
    (
        "Kubernetes namespaces provide logical isolation of resources within a cluster",
        0.88,
        ["compute", "kubernetes", "namespaces"],
    ),
    (
        "Spot instances provide unused cloud capacity at steep discounts but can be reclaimed",
        0.87,
        ["compute", "spot-instances"],
    ),
    (
        "Init containers run before application containers to perform setup tasks",
        0.86,
        ["compute", "kubernetes", "init-containers"],
    ),
    (
        "CronJobs in Kubernetes schedule recurring batch processing tasks",
        0.85,
        ["compute", "kubernetes", "cronjobs"],
    ),
    (
        "DaemonSets ensure one pod runs on every node for system-level services",
        0.84,
        ["compute", "kubernetes", "daemonsets"],
    ),
    (
        "StatefulSets manage stateful applications with stable network identities",
        0.83,
        ["compute", "kubernetes", "statefulsets"],
    ),
    (
        "WASM provides a portable compilation target for running code in sandboxed environments",
        0.82,
        ["compute", "wasm"],
    ),
    (
        "Container resource limits prevent individual pods from consuming excessive CPU or memory",
        0.91,
        ["compute", "kubernetes", "resource-limits"],
    ),
    (
        "Blue-green deployments run two identical environments to enable zero-downtime releases",
        0.90,
        ["compute", "deployment"],
    ),
    (
        "Canary deployments gradually roll out changes to a small subset of users first",
        0.89,
        ["compute", "deployment"],
    ),
    (
        "Infrastructure as Code tools like Terraform define compute resources declaratively",
        0.92,
        ["compute", "iac", "terraform"],
    ),
    (
        "Kubernetes ingress controllers manage external HTTP traffic routing to services",
        0.88,
        ["compute", "kubernetes", "ingress"],
    ),
    (
        "etcd stores Kubernetes cluster state as a distributed key-value store",
        0.87,
        ["compute", "kubernetes", "etcd"],
    ),
    (
        "Sidecar containers run alongside application containers for logging or proxying",
        0.86,
        ["compute", "kubernetes", "sidecar"],
    ),
    (
        "Node affinity rules control which cluster nodes pods are scheduled onto",
        0.84,
        ["compute", "kubernetes", "scheduling"],
    ),
    (
        "Kubernetes RBAC controls who can access cluster resources through role bindings",
        0.90,
        ["compute", "kubernetes", "rbac"],
    ),
]

SECURITY_FACTS: list[tuple[str, float, list[str]]] = [
    (
        "TLS encrypts data in transit between client and server using symmetric keys",
        0.97,
        ["security", "tls", "encryption"],
    ),
    (
        "OAuth2 delegates authorization without sharing user credentials between services",
        0.95,
        ["security", "oauth2", "authorization"],
    ),
    (
        "JWT tokens carry digitally signed claims for stateless authentication",
        0.94,
        ["security", "jwt", "authentication"],
    ),
    (
        "SQL injection inserts malicious SQL code through unsanitized user input fields",
        0.96,
        ["security", "sql-injection", "vulnerability"],
    ),
    (
        "XSS attacks inject malicious JavaScript into web pages viewed by other users",
        0.95,
        ["security", "xss", "vulnerability"],
    ),
    (
        "WAF filters and monitors HTTP traffic to block common web application attacks",
        0.92,
        ["security", "waf", "defense"],
    ),
    (
        "Zero trust architecture requires verification for every request regardless of network location",
        0.91,
        ["security", "zero-trust"],
    ),
    (
        "Container scanning detects known vulnerabilities in Docker image layers",
        0.90,
        ["security", "container-scanning"],
    ),
    (
        "CORS headers control which origins are permitted to access API resources",
        0.89,
        ["security", "cors"],
    ),
    (
        "CSRF attacks trick authenticated users into executing unwanted actions",
        0.88,
        ["security", "csrf", "vulnerability"],
    ),
    (
        "Rate limiting prevents brute force and denial-of-service attacks by capping requests",
        0.93,
        ["security", "rate-limiting"],
    ),
    (
        "Secrets management tools like Vault store API keys and passwords encrypted at rest",
        0.91,
        ["security", "secrets-management"],
    ),
    (
        "Bcrypt hashing protects stored passwords against rainbow table attacks",
        0.92,
        ["security", "bcrypt", "hashing"],
    ),
    (
        "Two-factor authentication requires both password and a second verification factor",
        0.90,
        ["security", "2fa", "authentication"],
    ),
    (
        "Penetration testing simulates real attacks to discover exploitable vulnerabilities",
        0.88,
        ["security", "pentesting"],
    ),
    (
        "Certificate pinning prevents man-in-the-middle attacks by binding certificates to hosts",
        0.86,
        ["security", "certificate-pinning"],
    ),
    (
        "Input validation rejects malformed data at API boundaries before processing",
        0.93,
        ["security", "input-validation"],
    ),
    (
        "RBAC assigns permissions to roles rather than individual users for scalable access control",
        0.90,
        ["security", "rbac"],
    ),
    (
        "Audit logging records all security-relevant events with timestamps for forensic review",
        0.89,
        ["security", "audit-logging"],
    ),
    (
        "DDoS mitigation absorbs volumetric attacks using distributed scrubbing centers",
        0.87,
        ["security", "ddos"],
    ),
    (
        "Network segmentation limits lateral movement after a breach using firewall rules",
        0.88,
        ["security", "segmentation"],
    ),
    (
        "Content Security Policy headers restrict which resources a browser can load",
        0.85,
        ["security", "csp"],
    ),
    (
        "SSRF attacks trick servers into making requests to internal resources on behalf of attackers",
        0.84,
        ["security", "ssrf", "vulnerability"],
    ),
    (
        "Dependency scanning identifies known CVEs in third-party libraries before deployment",
        0.86,
        ["security", "dependency-scanning"],
    ),
    (
        "mTLS requires both client and server to present certificates for mutual authentication",
        0.90,
        ["security", "mtls", "tls"],
    ),
]

OBSERVABILITY_FACTS: list[tuple[str, float, list[str]]] = [
    (
        "ELK stack combines Elasticsearch Logstash and Kibana for centralized log management",
        0.95,
        ["observability", "elk", "logging"],
    ),
    (
        "Prometheus scrapes time-series metrics from instrumented service endpoints",
        0.96,
        ["observability", "prometheus", "metrics"],
    ),
    (
        "Jaeger provides distributed tracing to track requests across microservice boundaries",
        0.94,
        ["observability", "jaeger", "tracing"],
    ),
    (
        "Grafana dashboards visualize metrics from Prometheus and other data sources",
        0.93,
        ["observability", "grafana", "dashboards"],
    ),
    (
        "SLOs define target reliability levels as a percentage of successful requests",
        0.91,
        ["observability", "slo"],
    ),
    (
        "Alerting rules fire notifications when metrics exceed defined thresholds",
        0.92,
        ["observability", "alerting"],
    ),
    (
        "Structured logging uses JSON format for machine-parseable log entries",
        0.90,
        ["observability", "structured-logging"],
    ),
    (
        "OpenTelemetry provides vendor-neutral instrumentation for traces metrics and logs",
        0.93,
        ["observability", "opentelemetry"],
    ),
    (
        "P99 latency measures the worst-case response time experienced by the top 1 percent",
        0.89,
        ["observability", "latency", "p99"],
    ),
    (
        "Span context propagation carries trace IDs across service boundaries via HTTP headers",
        0.88,
        ["observability", "tracing", "context-propagation"],
    ),
    (
        "Log aggregation collects logs from distributed services into a central searchable store",
        0.91,
        ["observability", "log-aggregation"],
    ),
    (
        "Error rate tracking measures the percentage of failed requests over time windows",
        0.90,
        ["observability", "error-rate"],
    ),
    (
        "Synthetic monitoring probes endpoints from external locations to detect outages",
        0.87,
        ["observability", "synthetic-monitoring"],
    ),
    (
        "Cardinality explosion from high-dimension labels can overwhelm metrics storage",
        0.85,
        ["observability", "cardinality"],
    ),
    (
        "Flame graphs visualize CPU profiling data to identify performance bottlenecks",
        0.86,
        ["observability", "flame-graph", "profiling"],
    ),
    (
        "Health check endpoints expose service liveness and readiness status",
        0.92,
        ["observability", "health-checks"],
    ),
    (
        "Correlation IDs link related log entries across multiple services for a single request",
        0.89,
        ["observability", "correlation-id"],
    ),
    (
        "SLI metrics quantify service behavior such as latency throughput and error rate",
        0.88,
        ["observability", "sli"],
    ),
    (
        "Error budgets define how much unreliability a service can tolerate before freezing changes",
        0.87,
        ["observability", "error-budget"],
    ),
    (
        "Log sampling reduces storage costs by keeping a representative subset of log entries",
        0.84,
        ["observability", "log-sampling"],
    ),
    (
        "RED method tracks Rate Errors and Duration for every microservice",
        0.90,
        ["observability", "red-method"],
    ),
    (
        "USE method monitors Utilization Saturation and Errors for infrastructure resources",
        0.89,
        ["observability", "use-method"],
    ),
    (
        "Distributed tracing shows the full call graph of a request across service boundaries",
        0.93,
        ["observability", "distributed-tracing"],
    ),
    (
        "Anomaly detection uses statistical baselines to identify unusual metric patterns",
        0.86,
        ["observability", "anomaly-detection"],
    ),
    (
        "Service level indicators measure the ratio of good events to total events",
        0.88,
        ["observability", "sli"],
    ),
]

# ---------------------------------------------------------------------------
# Domain registry: maps agent_id -> facts list
# ---------------------------------------------------------------------------

AGENT_DOMAINS: dict[str, list[tuple[str, float, list[str]]]] = {
    "networking_agent": NETWORKING_FACTS,
    "storage_agent": STORAGE_FACTS,
    "compute_agent": COMPUTE_FACTS,
    "security_agent": SECURITY_FACTS,
    "observability_agent": OBSERVABILITY_FACTS,
}

# ---------------------------------------------------------------------------
# Evaluation questions: 30 total
# (asking_agent, question, answer_keywords, category)
#
# Keywords are chosen so they appear in the fact text (after tokenization)
# but NOT in the question text itself, forcing the system to retrieve the
# relevant fact to score well.
# ---------------------------------------------------------------------------

EVAL_QUESTIONS: list[tuple[str, str, list[str], str]] = [
    # ===== 10 SINGLE-DOMAIN questions (agent queries its own knowledge) =====
    (
        "networking_agent",
        "How does TCP ensure reliable data delivery?",
        ["reliable", "ordered", "delivery", "packets", "acknowledgments"],
        "single-domain",
    ),
    (
        "networking_agent",
        "What is the purpose of DNS in networking?",
        ["dns", "translates", "domain", "names", "addresses"],
        "single-domain",
    ),
    (
        "storage_agent",
        "How does Redis provide fast caching?",
        ["redis", "sub-millisecond", "memory", "caching"],
        "single-domain",
    ),
    (
        "storage_agent",
        "What is database sharding and why is it used?",
        ["sharding", "distributes", "nodes", "horizontal", "scaling"],
        "single-domain",
    ),
    (
        "compute_agent",
        "How does Kubernetes manage container deployments?",
        ["kubernetes", "orchestrates", "container", "deployment", "scaling"],
        "single-domain",
    ),
    (
        "compute_agent",
        "What are serverless functions and how do they work?",
        ["serverless", "functions", "execute", "demand", "infrastructure"],
        "single-domain",
    ),
    (
        "security_agent",
        "How does TLS protect data in transit?",
        ["tls", "encrypts", "transit", "client", "server"],
        "single-domain",
    ),
    (
        "security_agent",
        "What is SQL injection and how does it exploit applications?",
        ["sql", "injection", "malicious", "input"],
        "single-domain",
    ),
    (
        "observability_agent",
        "How does Prometheus collect metrics?",
        ["prometheus", "scrapes", "time-series", "metrics", "endpoints"],
        "single-domain",
    ),
    (
        "observability_agent",
        "What is distributed tracing and why is it useful?",
        ["distributed", "tracing", "requests", "microservice", "boundaries"],
        "single-domain",
    ),
    # ===== 10 CROSS-DOMAIN questions (agent must use 1 other domain) =====
    (
        "networking_agent",
        "How does Redis caching reduce database load?",
        # networking agent asking about storage domain knowledge
        ["redis", "memory", "caching", "database"],
        "cross-domain",
    ),
    (
        "storage_agent",
        "How do load balancers distribute traffic across servers?",
        # storage agent asking about networking domain
        ["load", "balancers", "distribute", "traffic", "servers"],
        "cross-domain",
    ),
    (
        "compute_agent",
        "How does TLS encryption protect data between services?",
        # compute agent asking about security domain
        ["tls", "encrypts", "transit", "client", "server"],
        "cross-domain",
    ),
    (
        "security_agent",
        "How does Kubernetes orchestrate container deployments?",
        # security agent asking about compute domain
        ["kubernetes", "orchestrates", "container", "deployment"],
        "cross-domain",
    ),
    (
        "observability_agent",
        "How does database indexing speed up queries?",
        # observability agent asking about storage domain
        ["indexing", "b-tree", "query", "lookups"],
        "cross-domain",
    ),
    (
        "networking_agent",
        "What does Jaeger provide for distributed tracing?",
        # networking agent asking about observability domain
        ["jaeger", "distributed", "tracing", "requests", "microservice"],
        "cross-domain",
    ),
    (
        "storage_agent",
        "How does auto-scaling adjust compute capacity?",
        # storage agent asking about compute domain
        ["auto-scaling", "adjusts", "capacity", "cpu", "metrics"],
        "cross-domain",
    ),
    (
        "compute_agent",
        "How does Prometheus scrape metrics from services?",
        # compute agent asking about observability domain
        ["prometheus", "scrapes", "time-series", "metrics"],
        "cross-domain",
    ),
    (
        "security_agent",
        "How does a CDN cache content at edge locations?",
        # security agent asking about networking domain
        ["cdn", "cache", "content", "edge", "users"],
        "cross-domain",
    ),
    (
        "observability_agent",
        "How does WAF filter malicious HTTP traffic?",
        # observability agent asking about security domain
        ["waf", "filters", "monitors", "http", "attacks"],
        "cross-domain",
    ),
    # ===== 10 SYNTHESIS questions (require 2-3 domains combined) =====
    (
        "networking_agent",
        "How do load balancing, auto-scaling, and Prometheus metrics work together?",
        # networking + compute + observability
        ["load", "balancers", "auto-scaling", "prometheus", "metrics"],
        "synthesis",
    ),
    (
        "storage_agent",
        "How do database replication, TLS encryption, and distributed tracing interact?",
        # storage + security + observability
        ["replication", "tls", "encrypts", "tracing"],
        "synthesis",
    ),
    (
        "compute_agent",
        "How do container scanning, Kubernetes RBAC, and audit logging secure deployments?",
        # compute + security + observability
        ["container", "scanning", "rbac", "audit", "logging"],
        "synthesis",
    ),
    (
        "security_agent",
        "How do WAF protection, CDN caching, and rate limiting defend web applications?",
        # security + networking
        ["waf", "cdn", "rate", "limiting", "traffic"],
        "synthesis",
    ),
    (
        "observability_agent",
        "How do SLOs, error budgets, and canary deployments manage release risk?",
        # observability + compute
        ["slo", "error", "budgets", "canary", "deployments"],
        "synthesis",
    ),
    (
        "networking_agent",
        "How do service mesh, mTLS, and correlation IDs secure microservice communication?",
        # networking + security + observability
        ["service", "mesh", "mtls", "correlation"],
        "synthesis",
    ),
    (
        "storage_agent",
        "How do Redis caching, connection pooling, and P99 latency monitoring optimize throughput?",
        # storage + observability
        ["redis", "caching", "connection", "pooling", "p99", "latency"],
        "synthesis",
    ),
    (
        "compute_agent",
        "How do Kubernetes pod autoscaling, Redis caching, and Grafana dashboards work together?",
        # compute + storage + observability
        ["autoscaler", "redis", "grafana", "dashboards", "metrics"],
        "synthesis",
    ),
    (
        "security_agent",
        "How do OAuth2 authorization, structured logging, and input validation protect APIs?",
        # security + observability
        ["oauth2", "authorization", "structured", "logging", "input", "validation"],
        "synthesis",
    ),
    (
        "observability_agent",
        "How do health checks, DNS resolution, and container readiness work together?",
        # observability + networking + compute
        ["health", "check", "dns", "readiness"],
        "synthesis",
    ),
]


def _score_answer(retrieved_contents: list[str], answer_keywords: list[str]) -> float:
    """Score how well retrieved facts cover the answer keywords.

    Computes the fraction of expected keywords found anywhere in the
    concatenated retrieved text. This tests whether the hive mind's
    retrieval pipeline actually surfaces relevant knowledge.

    Args:
        retrieved_contents: List of fact content strings from retrieval.
        answer_keywords: Keywords that should appear in good results.

    Returns:
        Coverage score in [0.0, 1.0].
    """
    if not answer_keywords:
        return 1.0
    if not retrieved_contents:
        return 0.0

    combined_text = " ".join(retrieved_contents).lower()
    matches = sum(1 for kw in answer_keywords if kw.lower() in combined_text)
    return matches / len(answer_keywords)


def _timer() -> tuple[Any, Any]:
    """Create a start/stop timer pair that returns elapsed milliseconds."""
    state = {"start": 0.0}

    def start():
        state["start"] = time.perf_counter()

    def stop() -> float:
        return (time.perf_counter() - state["start"]) * 1000.0

    return start, stop


def _evaluate_questions(
    agents: dict[str, HiveMindAgent],
    isolated_agents: dict[str, HiveMindAgent],
    _hive: UnifiedHiveMind,
    _isolated_hive: UnifiedHiveMind,
) -> tuple[dict[str, list[float]], dict[str, list[float]], float]:
    """Run Phase 5: evaluate 30 questions and return per-category scores.

    Args:
        agents: Hive-connected agents keyed by agent_id.
        isolated_agents: Isolated baseline agents keyed by agent_id.
        _hive: The unified hive mind (unused, kept for call-site symmetry).
        _isolated_hive: The isolated hive (unused, kept for call-site symmetry).

    Returns:
        (category_isolated, category_hive, evaluation_ms) where each category
        dict maps category name to a list of per-question scores.
    """
    print("\n--- Phase 5: Evaluation (30 questions) ---")
    print("-" * 70)

    start, stop = _timer()
    start()

    category_isolated: dict[str, list[float]] = {
        "single-domain": [],
        "cross-domain": [],
        "synthesis": [],
    }
    category_hive: dict[str, list[float]] = {
        "single-domain": [],
        "cross-domain": [],
        "synthesis": [],
    }

    for i, (agent_id, question, keywords, category) in enumerate(EVAL_QUESTIONS, 1):
        # Isolated: query only local facts (no hive, no gossip)
        iso_results = isolated_agents[agent_id].ask_local(question, limit=15)
        iso_contents = [r["content"] for r in iso_results]
        iso_score = _score_answer(iso_contents, keywords)
        category_isolated[category].append(iso_score)

        # Hive: query all layers (local + hive + gossip)
        hive_results = agents[agent_id].ask(question, limit=15)
        hive_contents = [r["content"] for r in hive_results]
        hive_score = _score_answer(hive_contents, keywords)
        category_hive[category].append(hive_score)

        delta = hive_score - iso_score
        tag = category.upper()[:6]
        delta_str = f"+{delta:+.0%}"[1:] if delta >= 0 else f"{delta:.0%}"

        # Show per-question detail
        print(f"  {i:2d}. [{tag:6s}] ({agent_id[:10]:10s}) {question[:48]:48s}")
        print(f"      Isolated={iso_score:.0%}  Hive={hive_score:.0%}  Delta={delta_str}")

    evaluation_ms = stop()
    return category_isolated, category_hive, evaluation_ms


def _print_results(
    category_isolated: dict[str, list[float]],
    category_hive: dict[str, list[float]],
    timings: dict[str, float],
    hive: UnifiedHiveMind,
) -> dict:
    """Print results, timing, agent knowledge, hypothesis and return summary.

    Args:
        category_isolated: Per-category isolated scores.
        category_hive: Per-category hive scores.
        timings: Dict of phase_name -> elapsed milliseconds.
        hive: The unified hive mind (for agent knowledge summaries).

    Returns:
        Full evaluation results dict.
    """

    def _avg(scores: list[float]) -> float:
        return sum(scores) / len(scores) if scores else 0.0

    iso_single = _avg(category_isolated["single-domain"])
    iso_cross = _avg(category_isolated["cross-domain"])
    iso_synth = _avg(category_isolated["synthesis"])
    iso_overall = _avg(
        category_isolated["single-domain"]
        + category_isolated["cross-domain"]
        + category_isolated["synthesis"]
    )

    hive_single = _avg(category_hive["single-domain"])
    hive_cross = _avg(category_hive["cross-domain"])
    hive_synth = _avg(category_hive["synthesis"])
    hive_overall = _avg(
        category_hive["single-domain"] + category_hive["cross-domain"] + category_hive["synthesis"]
    )

    print("\n" + "=" * 70)
    print("                          RESULTS")
    print("=" * 70)
    print(f"{'':26s} {'Isolated':>10s} {'Hive':>10s} {'Delta':>10s}")
    print("-" * 58)
    print(
        f"{'Single-domain (10q)':26s} {iso_single:>9.1%} {hive_single:>9.1%} "
        f"{hive_single - iso_single:>+9.1%}pp"
    )
    print(
        f"{'Cross-domain (10q)':26s} {iso_cross:>9.1%} {hive_cross:>9.1%} "
        f"{hive_cross - iso_cross:>+9.1%}pp"
    )
    print(
        f"{'Synthesis (10q)':26s} {iso_synth:>9.1%} {hive_synth:>9.1%} "
        f"{hive_synth - iso_synth:>+9.1%}pp"
    )
    print("-" * 58)
    print(
        f"{'OVERALL (30q)':26s} {iso_overall:>9.1%} {hive_overall:>9.1%} "
        f"{hive_overall - iso_overall:>+9.1%}pp"
    )

    # Timing
    print(f"\n{'':26s} TIMING")
    print("-" * 58)
    print(f"{'Learning:':26s} {timings['learning_ms']:>8.1f}ms")
    print(f"{'Promotion:':26s} {timings['promotion_ms']:>8.1f}ms")
    print(f"{'Gossip:':26s} {timings['gossip_ms']:>8.1f}ms")
    print(f"{'Event Processing:':26s} {timings['event_ms']:>8.1f}ms")
    print(f"{'Evaluation (30q):':26s} {timings['evaluation_ms']:>8.1f}ms")

    # Agent knowledge distribution
    print(f"\n{'':26s} AGENT KNOWLEDGE")
    print("-" * 70)
    print(f"{'Agent':24s} {'Local':>6s} {'Hive':>6s} {'Gossip':>8s} {'Total':>6s}")
    print("-" * 70)
    for agent_id in AGENT_DOMAINS:
        summary = hive.get_agent_knowledge_summary(agent_id)
        local = summary["local_facts"]
        hive_avail = summary["hive_facts_available"]
        gossip_recv = summary["gossip_facts_received"]
        total = local + gossip_recv  # hive is shared, not per-agent owned
        print(f"{agent_id:24s} {local:>6d} {hive_avail:>6d} {gossip_recv:>8d} {total:>6d}")

    # Hypothesis check
    cross_improvement = hive_cross - iso_cross
    print(f"\n{'':26s} HYPOTHESIS")
    print("-" * 58)
    print("Cross-domain improvement target: >40%")
    print(f"Actual cross-domain improvement:  {cross_improvement:+.1%}pp")
    if cross_improvement > 0.40:
        print("Result: CONFIRMED -- hive mind delivers >40% cross-domain gain")
    elif cross_improvement > 0.20:
        print("Result: PARTIAL -- significant gain but below 40% target")
    else:
        print("Result: FAILED -- insufficient cross-domain improvement")

    overall_improvement = hive_overall - iso_overall
    print(f"\nOverall improvement: {overall_improvement:+.1%}pp")

    print("\n" + "=" * 70)

    return {
        "isolated": {
            "single_domain": iso_single,
            "cross_domain": iso_cross,
            "synthesis": iso_synth,
            "overall": iso_overall,
        },
        "hive": {
            "single_domain": hive_single,
            "cross_domain": hive_cross,
            "synthesis": hive_synth,
            "overall": hive_overall,
        },
        "delta": {
            "single_domain": hive_single - iso_single,
            "cross_domain": cross_improvement,
            "synthesis": hive_synth - iso_synth,
            "overall": overall_improvement,
        },
        "timings": timings,
        "hypothesis_confirmed": cross_improvement > 0.40,
    }


def _setup_and_train() -> tuple[
    dict[str, HiveMindAgent],
    dict[str, HiveMindAgent],
    UnifiedHiveMind,
    UnifiedHiveMind,
    dict[str, float],
]:
    """Create hives, register agents, and run phases 1-4.

    Returns:
        (agents, isolated_agents, hive, isolated_hive, timings) where timings
        contains learning_ms, promotion_ms, gossip_ms, and event_ms.
    """
    timings: dict[str, float] = {}

    # --------------- Setup ---------------
    config = HiveMindConfig(
        promotion_confidence_threshold=0.5,
        promotion_consensus_required=1,
        gossip_interval_rounds=5,
        gossip_top_k=10,
        gossip_fanout=3,  # each agent talks to 3 of 4 peers
        enable_gossip=True,
        enable_events=True,
    )
    hive = UnifiedHiveMind(config=config)

    # Also create a second isolated hive (no gossip, no events, no promotion)
    # to serve as the isolated baseline. Each agent only sees its own facts.
    isolated_config = HiveMindConfig(
        promotion_confidence_threshold=1.0,  # never promote
        promotion_consensus_required=99,
        enable_gossip=False,
        enable_events=False,
    )
    isolated_hive = UnifiedHiveMind(config=isolated_config)

    agents: dict[str, HiveMindAgent] = {}
    isolated_agents: dict[str, HiveMindAgent] = {}

    for agent_id in AGENT_DOMAINS:
        hive.register_agent(agent_id)
        agents[agent_id] = HiveMindAgent(agent_id, hive)
        isolated_hive.register_agent(agent_id)
        isolated_agents[agent_id] = HiveMindAgent(agent_id, isolated_hive)

    # --------------- Phase 1: Learning ---------------
    print("\n--- Phase 1: Learning (25 facts per agent) ---")
    start, stop = _timer()
    start()

    for agent_id, facts in AGENT_DOMAINS.items():
        for content, conf, tags in facts:
            agents[agent_id].learn(content, conf, tags)
            isolated_agents[agent_id].learn(content, conf, tags)
        summary = hive.get_agent_knowledge_summary(agent_id)
        print(
            f"  {agent_id:24s}: {summary['local_facts']:3d} local, "
            f"round={summary['learning_round']}"
        )

    timings["learning_ms"] = stop()

    # --------------- Phase 2: Promotion ---------------
    print("\n--- Phase 2: Promotion (top-10 per agent) ---")
    start, stop = _timer()
    start()

    total_promoted = 0
    for agent_id, facts in AGENT_DOMAINS.items():
        sorted_facts = sorted(facts, key=lambda f: -f[1])[:10]
        for content, conf, tags in sorted_facts:
            agents[agent_id].promote(content, conf, tags)
            total_promoted += 1
        print(f"  {agent_id:24s}: promoted 10 facts")

    stats_after_promotion = hive.get_stats()
    print(f"  Total hive facts: {stats_after_promotion['graph']['hive_facts']}")
    timings["promotion_ms"] = stop()

    # --------------- Phase 3: Gossip ---------------
    print("\n--- Phase 3: Gossip (5 rounds) ---")
    start, stop = _timer()
    start()

    for i in range(5):
        gossip_stats = hive.run_gossip_round()
        print(
            f"  Round {gossip_stats['round_number']}: "
            f"{gossip_stats['messages_sent']} msgs, "
            f"{gossip_stats['new_facts_learned']} new facts"
        )

    timings["gossip_ms"] = stop()

    # --------------- Phase 4: Event processing ---------------
    print("\n--- Phase 4: Event Processing ---")
    start, stop = _timer()
    start()

    event_results = hive.process_events()
    for agent_id in AGENT_DOMAINS:
        count = event_results.get(agent_id, 0)
        print(f"  {agent_id:24s}: incorporated {count} events")

    timings["event_ms"] = stop()

    return agents, isolated_agents, hive, isolated_hive, timings


def run_evaluation() -> dict:
    """Run the full 5-agent hive mind evaluation.

    Returns:
        Dict with detailed evaluation results including scores, timing,
        and knowledge distribution metrics.
    """
    print("=" * 70)
    print("          5-AGENT HIVE MIND EVALUATION")
    print("=" * 70)
    print("Agents: 5 | Facts/agent: 25 | Total: 125")
    print("Gossip rounds: 5 | Promoted: 50 (top-10 per agent)")
    print("=" * 70)

    agents, isolated_agents, hive, isolated_hive, timings = _setup_and_train()

    # --------------- Phase 5: Evaluation (30 questions) ---------------
    category_isolated, category_hive, timings["evaluation_ms"] = _evaluate_questions(
        agents, isolated_agents, hive, isolated_hive
    )

    # --------------- Results ---------------
    return _print_results(category_isolated, category_hive, timings, hive)


if __name__ == "__main__":
    results = run_evaluation()
    sys.exit(0)
