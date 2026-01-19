# Engineer Analyst - Quick Reference

## TL;DR

Analyzes technical systems through engineering frameworks using first principles, systems thinking, optimization theory, and failure analysis. Provides quantitative assessment of feasibility, performance, reliability, and trade-offs.

## When to Use

- System design and architecture decisions
- Performance optimization and bottleneck analysis
- Failure analysis and root cause investigation
- Scalability assessment and capacity planning
- Technical feasibility evaluation
- Trade-off analysis between design alternatives

## Core Frameworks

1. **First Principles Analysis** - Break to fundamentals, question assumptions
2. **Systems Engineering (V-Model)** - Requirements → Design → Implementation → Testing
3. **Design Optimization** - Pareto frontiers, multi-objective trade-offs
4. **FMEA** - Failure Mode and Effects Analysis
5. **Scalability Analysis** - Amdahl's Law, bottleneck identification

## Theoretical Foundations

- **First Principles**: Reason from fundamental truths, not analogy
- **Systems Engineering**: Structured decomposition and integration
- **Optimization Theory**: Constraints, trade-offs, Pareto optimality
- **Failure Analysis**: FMEA, fault trees, root cause analysis
- **Performance Engineering**: Profiling, benchmarking, capacity planning

## Quick Analysis Process

1. **Clarify Requirements** - Objectives, constraints, priorities (quantified)
2. **Gather Context** - Current system, usage patterns, measurements
3. **First Principles** - Break to fundamentals, identify true constraints
4. **Enumerate Alternatives** - 3+ options including status quo
5. **Model and Estimate** - Quantify performance, cost, reliability
6. **Trade-off Analysis** - Score against multiple objectives
7. **Failure Analysis** - FMEA, single points of failure
8. **Prototype** - Validate key assumptions empirically
9. **Document** - Recommendation with justification and trade-offs

## Key Questions

**Requirements**:

- What is the technical objective? (Performance? Reliability? Cost?)
- What are hard constraints? (Physics, budget, timeline, compatibility)
- What are priorities when trade-offs inevitable?

**System Analysis**:

- How does current system work? (Architecture, bottlenecks)
- What are usage patterns and load profiles?
- What are theoretical limits? (Physics, algorithms, network)

**Design Evaluation**:

- What alternatives exist? (Include status quo)
- How do alternatives score on multiple objectives?
- Which designs are Pareto-optimal?
- What are sensitivities to assumptions?

**Failure Modes**:

- How can each component fail?
- What are consequences? (Severity)
- How likely? (Occurrence)
- Can we detect quickly? (Detectability)
- What mitigations exist?

**Scalability**:

- Will design work at 10x scale?
- Where will bottlenecks shift?
- Is this vertical or horizontal scaling problem?

## Applied Frameworks

**Requirements Engineering**:

- **MoSCoW**: Must have, Should have, Could have, Won't have
- **Types**: Functional, Performance, Interface, Operational, Constraint

**Root Cause Analysis**:

- **5 Whys**: Ask "Why?" repeatedly until reaching root cause
- **Fishbone**: Organize causes by category (People, Process, Technology, Environment)

**FMEA Process**:

1. Identify failure modes
2. Assess Severity (1-10)
3. Assess Occurrence (1-10)
4. Assess Detectability (1-10)
5. Calculate RPN = S × O × D
6. Prioritize highest RPN
7. Implement mitigations

**Load Testing**:

- **Load Test**: Performance at expected load
- **Stress Test**: Performance at/beyond max capacity
- **Spike Test**: Sudden load increases
- **Soak Test**: Sustained operation (memory leaks, degradation)

## Common Mistakes to Avoid

- **Premature optimization**: Optimize before measuring
- **Over-engineering**: Designing for scale you'll never reach
- **Under-engineering**: Ignoring known future requirements
- **Analysis paralysis**: Endless analysis without building
- **Not invented here**: Rejecting proven solutions for custom builds
- **Resume-driven development**: Choosing tech for career, not project
- **Ignoring ops costs**: Focusing on dev cost, ignoring infrastructure/maintenance
- **Cargo culting**: Copying Google/Facebook without understanding context
- **Assuming zero failures**: All systems fail; design for degradation
- **Ignoring human factors**: Operators use systems; design for usability

## Essential Resources

**Systems Engineering**:

- **NASA SE Handbook**: https://www.nasa.gov/seh/
- **INCOSE**: https://www.incose.org/

**Software Architecture**:

- **System Design Primer**: https://github.com/donnemartin/system-design-primer
- **AOSA**: https://aosabook.org/

**Performance**:

- **Brendan Gregg**: https://www.brendangregg.com/
- **High Scalability**: http://highscalability.com/

**Reliability**:

- **Google SRE**: https://sre.google/books/

## Key Principles

**First Principles (Musk)**:
"Boil things down to fundamental truths and reason up from there"

**Conway's Law**:
"Organizations design systems that mirror their communication structure"

**Amdahl's Law**:
Speedup limited by serial fraction: Speedup ≤ 1 / (1 - P + P/N)

**Little's Law**:
L = λW (queue length = arrival rate × wait time)

**CAP Theorem**:
Can't have Consistency, Availability, Partition-tolerance simultaneously

**Pareto Principle**:
80% of effects from 20% of causes (focus optimization efforts)

## Design Trade-offs

| Objective 1      | vs. | Objective 2        |
| ---------------- | --- | ------------------ |
| Performance      | ← → | Cost               |
| Reliability      | ← → | Simplicity         |
| Flexibility      | ← → | Performance        |
| Consistency      | ← → | Availability       |
| Latency          | ← → | Throughput         |
| Vertical Scaling | ← → | Horizontal Scaling |

## Scalability Patterns

**Stateless Services**: Enable horizontal scaling without coordination
**Database Sharding**: Partition data across databases
**Caching**: Reduce backend load (CDN, Redis, memcached)
**Async Processing**: Decouple request from heavy work (message queues)
**Read Replicas**: Scale read-heavy workloads
**Microservices**: Independently scalable components

## Performance Metrics

**Throughput**: Requests/transactions per second
**Latency**: Response time (mean, p50, p95, p99, max)
**Error Rate**: Failed requests as % of total
**Utilization**: CPU, memory, disk, network usage
**Saturation**: Load level where performance degrades

## Success Criteria

✓ Requirements quantified (not vague goals)
✓ Baseline measurements documented
✓ 3+ alternatives evaluated
✓ Numerical estimates (performance, cost, reliability)
✓ Trade-offs explicit with scoring
✓ Failure modes identified (FMEA)
✓ Assumptions and sensitivities noted
✓ Validation plan defined
✓ Scalability assessed (10x growth)
✓ Maintainability considered

## Decision Matrix Template

| Criterion          | Weight | Alt 1 Score | Alt 2 Score | Alt 3 Score |
| ------------------ | ------ | ----------- | ----------- | ----------- |
| Performance        | 0.3    |             |             |             |
| Reliability        | 0.25   |             |             |             |
| Cost               | 0.2    |             |             |             |
| Maintainability    | 0.15   |             |             |             |
| Scalability        | 0.1    |             |             |             |
| **Weighted Total** |        |             |             |             |

## Capacity Planning Rules

- **Never run at 100% utilization** (queuing explodes)
- **Safe range: 60-70% utilization** under normal load
- **Headroom for spikes**: 2-3x normal load capacity
- **Monitor p95/p99**, not just averages
- **Load test before launch**: Realistic traffic patterns

---

**For full details, see SKILL.md**
