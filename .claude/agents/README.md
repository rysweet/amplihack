# Amplihack Agents

This directory contains specialized agents that extend Claude Code's capabilities for the amplihack framework.

## Recently Added Agents (2025-10-27)

### Knowledge Work Agents

These agents were ported from amplifier to enhance amplihack's knowledge processing and complexity management capabilities:

#### 1. ambiguity-guardian

**Value: HIGHEST** - Preserves productive contradictions and navigates uncertainty

- Use when: Fundamental disagreements between sources, paradoxes, multiple valid interpretations
- Key capability: Makes ambiguity productive rather than problematic
- Output: Tension maps, uncertainty cartography, paradox preservation, ambiguity indices

#### 2. knowledge-archaeologist

**Value: HIGH** - Traces evolution of knowledge and identifies valuable abandoned approaches

- Use when: Understanding concept evolution, paradigm shifts, discovering old solutions for new problems
- Key capability: Temporal analysis of knowledge - how ideas evolve, decay, and resurrect
- Output: Temporal layers, lineage trees, paradigm shifts, decay patterns, revival candidates

#### 3. post-task-cleanup

**Value: MEDIUM** - Ensures codebase hygiene after task completion

- Use when: After completing major tasks or todo lists
- Key capability: Reviews changes, removes temporary artifacts, enforces philosophy compliance
- Output: Cleanup report with specific actions and philosophy adherence score

#### 4. concept-extractor

**Value: MEDIUM** - Extracts structured knowledge from documents

- Use when: Processing articles, papers, or documents for knowledge synthesis
- Key capability: Identifies atomic concepts, relationships, tensions, and uncertainties
- Output: Structured JSON with concepts, relationships, tensions, uncertainties

#### 5. insight-synthesizer

**Value: MEDIUM** - Discovers revolutionary connections and breakthrough insights

- Use when: Stuck on complex problems, seeking innovative solutions, need unexpected connections
- Key capability: Collision-zone thinking, pattern-pattern recognition, simplification cascades
- Output: Collision experiments, cross-domain patterns, simplifications, revolutionary insights

## Integration with Amplihack Philosophy

These agents complement amplihack's existing capabilities:

- **ambiguity-guardian** + **architect**: Handle complex requirements with multiple valid interpretations
- **knowledge-archaeologist** + **analyzer**: Understand code evolution and why patterns were chosen
- **post-task-cleanup** + **reviewer**: Ensure code quality and philosophy compliance post-implementation
- **concept-extractor** + **knowledge-builder**: Enhance documentation and knowledge base creation
- **insight-synthesizer** + **optimizer**: Find breakthrough simplifications and novel solutions

## Usage Examples

### Using ambiguity-guardian for complex requirements:

```
User: "Our authentication system needs to support both OAuth and SAML, but the requirements conflict"
Claude: "I'll use the ambiguity-guardian agent to map these tensions and create a solution that preserves both approaches"
```

### Using knowledge-archaeologist for code understanding:

```
User: "Why did we choose this specific architecture pattern?"
Claude: "Let me invoke the knowledge-archaeologist agent to trace the evolution of this pattern and document the reasoning"
```

### Using post-task-cleanup after major work:

```
User: "Feature implementation complete"
Claude: "I'll run the post-task-cleanup agent to ensure no temporary files or unnecessary complexity remains"
```

### Using concept-extractor for documentation:

```
User: "Process these design documents and extract the key concepts"
Claude: "I'll use the concept-extractor agent to build a structured knowledge base from these documents"
```

### Using insight-synthesizer for innovation:

```
User: "We need a breakthrough approach to this performance bottleneck"
Claude: "Let me deploy the insight-synthesizer agent to explore revolutionary connections and find simplification cascades"
```

## Agent Interaction Patterns

### Sequential Pattern (Common)

1. **concept-extractor** → Extract knowledge from documents
2. **insight-synthesizer** → Find revolutionary connections
3. **architect** → Design implementation
4. **builder** → Implement solution
5. **post-task-cleanup** → Ensure quality

### Parallel Pattern (When Appropriate)

- **ambiguity-guardian** + **architect** → Handle complex requirements simultaneously
- **knowledge-archaeologist** + **analyzer** → Understand code and history in parallel

### Iterative Pattern (For Exploration)

1. **insight-synthesizer** → Generate multiple approaches
2. **ambiguity-guardian** → Preserve tensions between approaches
3. **architect** → Design solution that accommodates multiple paths
4. **builder** → Implement flexible architecture

## Philosophy Alignment

All agents strictly follow amplihack's core principles:

- **Simplicity**: Start simple, add only justified complexity
- **Modular**: Self-contained modules with clear interfaces
- **Working code**: No stubs or dead code
- **Test-driven**: Tests before implementation

The new agents enhance these principles by:

- Preserving valuable complexity (ambiguity-guardian)
- Learning from past simplifications (knowledge-archaeologist)
- Enforcing simplicity post-implementation (post-task-cleanup)
- Structuring knowledge clearly (concept-extractor)
- Finding breakthrough simplifications (insight-synthesizer)

## Contributing New Agents

When adding new agents:

1. Follow the agent template format (see existing agents)
2. Define clear use cases with examples
3. Specify tool requirements
4. Document output format
5. Align with amplihack philosophy
6. Add to this README with value assessment
7. Update main README agent count

## Testing Agents

Test new agents with:

```bash
# Test agent loads correctly
claude --agent ambiguity-guardian

# Test agent with sample task
claude --agent knowledge-archaeologist "Trace the evolution of microservices architecture"
```

## See Also

- [Main README](../../README.md) - Project overview and quick start
- [Philosophy](.claude/context/PHILOSOPHY.md) - Core principles
- [Patterns](.claude/context/PATTERNS.md) - Common patterns
