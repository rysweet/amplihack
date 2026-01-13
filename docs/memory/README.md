# Memory System Documentation

> [Home](../index.md) > Memory System

Ahoy, matey! Welcome to the memory system documentation - where agents remember what they learned and share knowledge across sessions.

## Quick Navigation

**New to memory systems?** Start here:

- [5-Type Memory Guide](5-TYPE-MEMORY-GUIDE.md) - **NEW!** Understand the 5 psychological memory types
- [Quick Reference](5-TYPE-MEMORY-QUICKREF.md) - **NEW!** One-page cheat sheet for memory system
- [Agent Memory Integration](../AGENT_MEMORY_INTEGRATION.md) - How agents share and persist knowledge
- [Agent Memory Quickstart](../AGENT_MEMORY_QUICKSTART.md) - Get started in 5 minutes

**Looking for something specific?**

- [5-Type Memory System](#5-type-memory-system) - **NEW!** Episodic, Semantic, Procedural, Prospective, Working
- [Terminal Visualization](#terminal-visualization) - **NEW!** View memory graph in terminal
- [Kùzu Backend](#kùzu-backend) - **NEW!** Graph database schema
- [Neo4j Memory System](#neo4j-memory-system) - Graph-based memory
- [Testing & Validation](#testing--validation) - Memory system tests
- [External Knowledge](#external-knowledge) - Import external data

---

## 5-Type Memory System

**NEW!** Psychological memory model with 5 types, pluggable backends, and automatic hooks.

### Core Documentation

- [5-Type Memory Guide](5-TYPE-MEMORY-GUIDE.md) - Complete user guide for all 5 memory types
- [Developer Reference](5-TYPE-MEMORY-DEVELOPER.md) - Architecture, API reference, integration patterns
- [Quick Reference](5-TYPE-MEMORY-QUICKREF.md) - One-page cheat sheet and decision tree

### Architecture & Schema

- [Kùzu Memory Schema](KUZU_MEMORY_SCHEMA.md) - Graph database schema with 5 node types
- [Backend Architecture](../backend-architecture.md) - Pluggable backend design (SQLite, Kùzu, Neo4j)
- [Evaluation Framework](../evaluation-framework.md) - Compare backend quality and performance

### Features

**Memory Types**:

- **Episodic**: Session-specific events and conversations
- **Semantic**: Cross-session knowledge and patterns
- **Prospective**: Future intentions and reminders
- **Procedural**: How-to workflows and procedures
- **Working**: Active task state (auto-cleared on completion)

**Backends**:

- **Kùzu** (default): Embedded graph database, zero infrastructure
- **SQLite**: Relational storage, fast and simple
- **Neo4j**: External graph database (optional)

**Quality Gates**:

- Multi-agent review (3 agents: analyzer, patterns, knowledge-archaeologist)
- Trivial content filtering
- Selective retrieval with token budgets

---

## Terminal Visualization

**NEW!** View memory graph directly in your terminal with beautiful Rich-powered trees.

- [Memory Tree Visualization Guide](MEMORY_TREE_VISUALIZATION.md) - How to use `amplihack memory tree`
- Command: `amplihack memory tree [--session SESSION] [--type TYPE]`
- Color-coded by memory type with emoji indicators
- Star ratings for importance scores
- Filter by session, type, or agent

---

## Kùzu Backend

**NEW!** Embedded graph database as default memory backend.

- [Kùzu Memory Schema](KUZU_MEMORY_SCHEMA.md) - Complete schema documentation
- 5 separate node types (EpisodicMemory, SemanticMemory, etc.)
- 11 semantic relationships (CONTAINS_EPISODIC, CONTRIBUTES_TO_SEMANTIC, etc.)
- Sessions as first-class entities
- Zero Docker overhead (embedded database)

---

## Neo4j Memory System

Advanced graph-based memory for complex knowledge representation:

- [Neo4j Implementation Summary](NEO4J_IMPLEMENTATION_SUMMARY.md) - Current status
- [Neo4j Phases 1-6 Complete](NEO4J_PHASES_1_6_COMPLETE.md) - Implementation milestones
- [Neo4j Validation Checklist](NEO4J_VALIDATION_CHECKLIST.md) - Ensure proper setup
- [Neo4j Quick Reference](../neo4j_memory/quick_reference.md) - Fast answers

### Research & Deep Dives

For comprehensive research on the Neo4j memory system:

- [Neo4j Memory Research](../research/neo4j_memory_system/README.md) - Complete research archive
- [Executive Summary](../research/neo4j_memory_system/00-executive-summary/README.md)
- [Technical Research](../research/neo4j_memory_system/01-technical-research/README.md)
- [Design Patterns](../research/neo4j_memory_system/02-design-patterns/README.md)
- [Integration Guides](../research/neo4j_memory_system/03-integration-guides/README.md)
- [External Knowledge](../research/neo4j_memory_system/04-external-knowledge/README.md)

---

## Testing & Validation

Memory system performance and validation:

- [A/B Test Summary](AB_TEST_SUMMARY.md) - Performance comparisons
- [A/B Test Quick Reference](AB_TEST_QUICK_REFERENCE.md) - Test results at a glance
- [Effectiveness Test Design](EFFECTIVENESS_TEST_DESIGN.md) - How we measure success
- [Final Cleanup Report](FINAL_CLEANUP_REPORT.md) - Memory system cleanup

### Code Quality

- [Code Review PR 1077](CODE_REVIEW_PR_1077.md) - Example: Memory system review
- [Zero-BS Audit](ZERO_BS_AUDIT.md) - Quality audit results

---

## External Knowledge

Import and integrate external data sources:

- [External Knowledge Integration](../external_knowledge_integration.md) - Import external data sources
- [Blarify Integration](../blarify_integration.md) - Connect with Blarify knowledge base
- [Blarify Quickstart](../blarify_quickstart.md) - Get started with Blarify
- [Blarify Architecture](../blarify_architecture.md) - Understanding the Blarify integration

---

## Memory Patterns

Advanced patterns for memory collaboration:

- [Agent Type Memory Sharing Patterns](../agent_type_memory_sharing_patterns.md) - Patterns for memory collaboration
- [Neo4j Phase 4 Implementation](../neo4j_memory_phase4_implementation.md) - Latest features

---

## Related Documentation

- [Agents Overview](../../.claude/agents/amplihack/README.md) - How agents use memory
- [Document-Driven Development](../document_driven_development/README.md) - Memory in DDD workflow
- [Goal Agent Generator](../GOAL_AGENT_GENERATOR_GUIDE.md) - Create custom goal-seeking agents with memory

---

Need help? Check the [Troubleshooting Guide](../troubleshooting/README.md) or [Discoveries](../DISCOVERIES.md) for common issues.
