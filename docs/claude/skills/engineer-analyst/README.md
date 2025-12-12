# Engineer Analyst Skill

> **Analyze technical systems through rigorous engineering frameworks to design reliable, efficient, and scalable solutions.**

## Overview

The Engineer Analyst skill enables Claude to perform sophisticated technical system analysis. Drawing on established engineering frameworks, design methodologies, and quantitative analysis, this skill provides insights into:

- **System Design**: Architecture, components, interfaces, and trade-offs
- **Performance Analysis**: Bottlenecks, scalability, optimization opportunities
- **Failure Analysis**: Root causes, failure modes, mitigation strategies
- **Trade-off Evaluation**: Multi-objective optimization with constraints
- **Feasibility Assessment**: Technical viability and risk identification
- **Requirements Engineering**: Clarification, decomposition, and validation

## What Makes This Different

Unlike general technical analysis, engineer analysis:

1. **Quantitative Rigor**: Numbers, measurements, and calculations drive decisions
2. **First Principles**: Breaks problems to fundamentals rather than relying on analogy
3. **Systems Thinking**: Considers interactions and emergent behaviors, not just components
4. **Trade-off Explicit**: Acknowledges competing objectives; no perfect solutions
5. **Failure-Aware**: Designs for resilience and graceful degradation
6. **Evidence-Based**: Prototypes and measurements validate assumptions

## Use Cases

### System Design

- Microservices vs. monolith architecture decisions
- Database selection and schema design
- API design and versioning strategies
- Caching architectures and content delivery
- Message queue and event-driven architectures

### Performance Optimization

- Database query optimization and indexing
- Application profiling and bottleneck identification
- Load balancing and auto-scaling strategies
- Caching strategies to reduce backend load
- Algorithm optimization and complexity analysis

### Reliability Engineering

- Failure mode and effects analysis (FMEA)
- High availability and disaster recovery design
- Circuit breakers and graceful degradation
- Monitoring, alerting, and observability
- Chaos engineering and resilience testing

### Capacity Planning

- Resource sizing for expected load
- Scalability analysis and growth projections
- Cost optimization for cloud infrastructure
- Performance testing and load simulation

## Engineering Frameworks Available

### Core Theoretical Approaches

- **First Principles Analysis**: Breaking problems to fundamental truths
- **Systems Engineering (V-Model)**: Requirements → Design → Implementation → Testing
- **Design Optimization**: Pareto frontiers, multi-objective trade-offs
- **FMEA**: Systematic failure mode identification and mitigation
- **Scalability Analysis**: Amdahl's Law, bottleneck shifting, horizontal/vertical scaling

### Applied Frameworks

- **Requirements Engineering**: MoSCoW prioritization, functional/non-functional requirements
- **Design Thinking**: Double diamond process, rapid prototyping, user-centered design
- **Root Cause Analysis**: 5 Whys, Fishbone diagrams, fault tree analysis
- **Load Testing**: Performance under expected and extreme loads
- **Cost-Benefit Analysis**: NPV, opportunity cost, trade-off quantification

### Methodologies

- **Prototyping**: POC, throwaway, evolutionary, horizontal/vertical
- **Design of Experiments**: Systematic parameter space exploration
- **Queueing Theory**: Capacity planning, response time modeling
- **Performance Profiling**: CPU, memory, I/O, lock contention analysis
- **Benchmarking**: Baseline measurements, A/B testing, regression detection

## Quick Start

### Basic Usage

```
Claude, use the engineer-analyst skill to analyze [TECHNICAL SYSTEM/PROBLEM].

Examples:
- "Use engineer-analyst to evaluate microservices vs. monolith for our application."
- "Analyze database performance issues using engineer-analyst skill."
- "Use engineer skill to conduct failure analysis of last week's outage."
```

### Advanced Usage

```
"Use engineer-analyst to optimize query performance with first principles analysis
and load testing validation."

"Apply engineer-analyst with FMEA methodology to assess reliability of proposed
architecture."

"Use engineer-analyst to conduct trade-off analysis between three database options
considering cost, performance, and operational complexity."
```

## Analysis Process

1. **Clarify Requirements** - Objectives, constraints, priorities
2. **Gather Context** - Current system, usage patterns, bottlenecks
3. **First Principles** - Break to fundamentals, question assumptions
4. **Enumerate Alternatives** - Multiple design options including status quo
5. **Model and Estimate** - Quantify expected performance
6. **Trade-off Analysis** - Multi-objective scoring, Pareto optimality
7. **Failure Analysis** - FMEA, single points of failure
8. **Prototype and Validate** - Test key assumptions empirically
9. **Document and Communicate** - Clear recommendations with justification

## Example Analyses

### Example 1: Microservices vs. Monolith

**Decision**: Stay monolith short-term, prepare for strategic extraction
**Reasoning**: Small team benefits from monolith simplicity; plan transition as team grows

### Example 2: Database Index Design

**Problem**: Slow product search queries
**Solution**: Add composite indexes on (category, price) and (brand, stock)
**Result**: 45x query performance improvement with minimal write overhead

### Example 3: Cloud Outage Root Cause

**Cause**: Coupled code deploy and database migration, no rollback plan
**Mitigations**: Decouple migrations, canary deployments, feature flags, improved monitoring

## Quality Standards

✓ **Quantified requirements** with measurable objectives
✓ **Baseline measurements** of current system
✓ **Multiple alternatives** evaluated (3+ options)
✓ **Numerical estimates** of performance, cost, reliability
✓ **Explicit trade-offs** with multi-objective scoring
✓ **Failure mode analysis** (FMEA or equivalent)
✓ **Validation plan** to verify design
✓ **Documented assumptions** and sensitivities
✓ **Scalability assessment** at 10x growth
✓ **Maintainability** considerations

## Resources

### Systems Engineering

- **NASA Systems Engineering Handbook**: https://www.nasa.gov/seh/
- **INCOSE**: https://www.incose.org/

### Software Architecture

- **System Design Primer**: https://github.com/donnemartin/system-design-primer
- **AOSA**: https://aosabook.org/ (Architecture of Open Source Applications)

### Performance

- **Brendan Gregg**: https://www.brendangregg.com/ (Performance engineering)
- **High Scalability**: http://highscalability.com/ (Case studies)

### Reliability

- **Google SRE Books**: https://sre.google/books/
- **Resilience Engineering**: https://www.resilience-engineering-association.org/

## Integration with Other Skills

- **Decision Logger**: Document technical decisions and rationale
- **Module Spec Generator**: Create engineering specifications for systems
- **Philosophy Guardian**: Ensure ruthless simplicity in designs
- **Test Gap Analyzer**: Identify testing gaps in engineered systems

## Version

**Current Version**: 1.0.0
**Status**: Production Ready
**Last Updated**: 2025-11-16
