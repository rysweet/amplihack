# Performance Optimizer Agent Requirements

## Purpose and Value Proposition
Analyzes performance bottlenecks and optimizes code for speed, memory usage, and scalability.

## Core Functional Requirements
- FR7.1: MUST profile code for performance bottlenecks
- FR7.2: MUST analyze algorithm complexity (Big O)
- FR7.3: MUST identify memory leaks and inefficiencies
- FR7.4: MUST optimize database queries and indexes
- FR7.5: MUST suggest caching strategies
- FR7.6: MUST provide before/after performance metrics

## Input Requirements
- IR7.1: Code to optimize
- IR7.2: Performance requirements/SLAs
- IR7.3: Current performance metrics
- IR7.4: Usage patterns and load characteristics

## Output Requirements
- OR7.1: Performance analysis report with bottlenecks
- OR7.2: Optimization recommendations with impact estimates
- OR7.3: Optimized code implementations
- OR7.4: Performance comparison metrics
- OR7.5: Scalability analysis

## Quality Requirements
- QR7.1: Optimizations must maintain correctness
- QR7.2: Performance gains must be measurable
- QR7.3: Code readability must be preserved
- QR7.4: Optimizations must consider trade-offs