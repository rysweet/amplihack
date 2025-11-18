# Module: Microsoft Agent Framework Skill

## Purpose

Provide Claude Code with comprehensive Microsoft Agent Framework knowledge through progressive disclosure, enabling efficient agent development in .NET/Python while maintaining token efficiency and integration with amplihack workflows.

## Contract

### Inputs

- **User Request**: Questions about Agent Framework, code generation needs, integration decisions
- **Context Level**: Implicit based on question complexity (auto-selects tier)
- **Language Preference**: Python or C# (inferred from project context)

### Outputs

- **Framework Guidance**: Architecture patterns, best practices, API usage
- **Code Generation**: Agent definitions, workflows, integrations
- **Decision Support**: When to use Agent Framework vs amplihack agents
- **Documentation**: Progressive disclosure from metadata to deep technical content

### Side Effects

- **Token Usage**: Minimal by default (<100 tokens tier 1), scaling to needs
- **File System**: No writes (read-only documentation skill)
- **External Calls**: Optional version check for documentation freshness

## Dependencies

### External

- Microsoft Agent Framework documentation (embedded, versioned)
- GitHub repository (reference URLs)
- OpenTelemetry (mentioned in context)

### Internal

- Claude Code Read tool (documentation access)
- amplihack philosophy (integration decisions)
- Module-spec-generator pattern (doc-heavy skill design)

## Progressive Disclosure Strategy

### Tier 1: Metadata (<100 tokens)

**Purpose**: Auto-discovery and routing
**Content**: Skill identity, capabilities summary, common use cases
**Load Time**: Always (included in skill.md header)

### Tier 2: Core Instructions (<5,000 tokens)

**Purpose**: Framework overview and quick reference
**Content**:

- Architecture components (agents, workflows, tools)
- Quick start patterns (Python + C#)
- Decision framework (when to use)
- Integration with amplihack
  **Load Time**: Default when skill is invoked

### Tier 3: Detailed Documentation (5,000-15,000 tokens)

**Purpose**: Deep technical content
**Content**:

- Component deep dives (agents, workflows, tools, middleware)
- Tutorial walkthroughs from Microsoft Learn
- Sample code patterns from GitHub
- Workflow orchestration patterns
  **Load Time**: On-demand when user needs detailed guidance

### Tier 4: Advanced Topics (15,000+ tokens)

**Purpose**: Specialized scenarios
**Content**:

- RAG integration patterns
- Async multi-agent patterns
- Function interception and middleware
- DevUI integration
- Production deployment patterns
  **Load Time**: Explicit user request or complex scenario

## Content Organization

### Source Material (10 URLs)

1. **Microsoft Learn - Overview**: Architecture fundamentals
2. **Microsoft Learn - Tutorials**: Step-by-step guides
3. **Microsoft Learn - Workflows**: Graph-based orchestration
4. **GitHub Repo**: API reference and structure
5. **GitHub Samples**: Real-world examples
6. **Medium Article**: Practical implementation guide
7. **LinkedIn - Workflows**: Visual workflow patterns
8. **LinkedIn - Function Calls**: Tool integration
9. **LinkedIn - Async**: Multi-agent coordination
10. **DevBlog**: Announcement and vision

### Distillation Strategy

- **Tier 2**: Extract core concepts, API signatures, minimal examples (20% of content)
- **Tier 3**: Full tutorials, detailed examples, best practices (60% of content)
- **Tier 4**: Advanced scenarios, edge cases, production patterns (20% of content)

## Directory Structure

```
.claude/skills/microsoft-agent-framework/
├── skill.md                          # Tier 1+2: Metadata + Core (4,800 tokens)
├── reference/
│   ├── agents.md                     # Tier 3: Agent component details (3,000 tokens)
│   ├── workflows.md                  # Tier 3: Workflow orchestration (3,500 tokens)
│   ├── tools.md                      # Tier 3: Tool integration (2,500 tokens)
│   ├── middleware.md                 # Tier 3: Context and middleware (2,000 tokens)
│   ├── rag.md                        # Tier 4: RAG patterns (2,500 tokens)
│   ├── async.md                      # Tier 4: Async multi-agent (2,500 tokens)
│   └── production.md                 # Tier 4: Deployment patterns (2,000 tokens)
├── examples/
│   ├── quickstart-python.md          # Tier 2: Minimal Python example
│   ├── quickstart-csharp.md          # Tier 2: Minimal C# example
│   ├── workflow-simple.md            # Tier 3: Basic workflow
│   ├── workflow-conditional.md       # Tier 3: Conditional workflow
│   ├── rag-integration.md            # Tier 4: RAG example
│   └── async-coordination.md         # Tier 4: Async example
├── integration/
│   ├── decision-framework.md         # When to use Agent Framework vs amplihack
│   ├── amplihack-integration.md      # How to integrate with amplihack workflows
│   └── migration-guide.md            # Moving from amplihack to Agent Framework
├── metadata/
│   ├── version.json                  # Documentation version and freshness
│   └── sources.json                  # Original URL mappings
└── scripts/
    └── check-freshness.py            # Version checking script (optional)
```

## File Breakdown

### skill.md (4,800 tokens)

**Tier 1 Metadata (100 tokens)**:

```markdown
# Microsoft Agent Framework Skill

**Purpose**: Build AI agents using Microsoft Agent Framework (.NET/Python)
**Capabilities**: Architecture guidance, code generation, workflow orchestration
**Use Cases**: Multi-agent systems, tool integration, enterprise AI agents
**Languages**: Python 3.11+, C# .NET 8+
**Version**: v0.1.0 (Docs: 2024-01-15)
```

**Tier 2 Core Instructions (4,700 tokens)**:

- Framework architecture (agents, workflows, tools, middleware)
- Quick start patterns (Python + C# minimal examples)
- Decision framework (Agent Framework vs amplihack)
- Integration patterns with amplihack workflows
- Common operations (create agent, define workflow, add tools)
- API reference (key classes and methods)

### reference/ (18,000 tokens total)

**agents.md (3,000 tokens - Tier 3)**:

- Agent lifecycle and state management
- Tool registration and execution
- Agent threads and conversation management
- Context providers
- Agent composition patterns

**workflows.md (3,500 tokens - Tier 3)**:

- Graph-based workflow design
- Conditional branching and loops
- State management and checkpointing
- Error handling and recovery
- Workflow testing patterns

**tools.md (2,500 tokens - Tier 3)**:

- Tool definition patterns
- Function calling conventions
- Parameter validation
- Tool error handling
- MCP client integration

**middleware.md (2,000 tokens - Tier 3)**:

- Context enrichment
- Logging and observability
- Request/response transformation
- Authentication and authorization
- Custom middleware patterns

**rag.md (2,500 tokens - Tier 4)**:

- RAG architecture with Agent Framework
- Vector store integration
- Context retrieval patterns
- Hybrid search strategies
- Production RAG deployment

**async.md (2,500 tokens - Tier 4)**:

- Multi-agent coordination
- Async workflow patterns
- Event-driven architecture
- Message passing between agents
- Deadlock prevention

**production.md (2,000 tokens - Tier 4)**:

- Deployment architecture
- Monitoring and observability
- Performance optimization
- Security best practices
- Scaling strategies

### examples/ (8,000 tokens total)

**quickstart-python.md (800 tokens - Tier 2)**:

```python
# Minimal working agent
from microsoft.agents import Agent, ToolCall

agent = Agent(
    name="assistant",
    model="gpt-4o",
    tools=[search_tool]
)

response = agent.chat("Find recent AI news")
```

**quickstart-csharp.md (800 tokens - Tier 2)**:

```csharp
// Minimal working agent
var agent = new Agent(
    name: "assistant",
    model: "gpt-4o",
    tools: [searchTool]
);

var response = await agent.ChatAsync("Find recent AI news");
```

**workflow-simple.md (1,500 tokens - Tier 3)**:

- Linear workflow example
- State passing between agents
- Error handling

**workflow-conditional.md (2,000 tokens - Tier 3)**:

- Conditional branching
- Loop patterns
- Dynamic agent selection

**rag-integration.md (1,500 tokens - Tier 4)**:

- Full RAG workflow
- Vector store setup
- Context injection

**async-coordination.md (1,400 tokens - Tier 4)**:

- Multi-agent async pattern
- Event handling
- Coordination strategies

### integration/ (4,000 tokens total)

**decision-framework.md (1,500 tokens)**:

```markdown
# When to Use Microsoft Agent Framework

## Use Agent Framework When:

- Building .NET/Python enterprise agents
- Need graph-based workflow orchestration
- Require OpenTelemetry integration
- Multi-language team (C#/Python)
- Production deployment with DevUI

## Use amplihack Agents When:

- Claude Code workflow orchestration
- Rapid prototyping and experimentation
- Markdown-based agent definitions
- Session-specific coordination
- Meta-programming and self-improvement

## Hybrid Approach:

- amplihack orchestrates high-level workflow
- Agent Framework implements production agents
- Use UltraThink with Agent Framework tools
```

**amplihack-integration.md (1,500 tokens)**:

- Calling Agent Framework from amplihack agents
- Workflow integration patterns
- State management between systems
- Decision point identification

**migration-guide.md (1,000 tokens)**:

- Converting amplihack agents to Agent Framework
- Preserving agent contracts
- Testing migration strategy

### metadata/ (200 tokens total)

**version.json (100 tokens)**:

```json
{
  "skill_version": "0.1.0",
  "docs_version": "2024-01-15",
  "framework_version": "0.1.0",
  "last_updated": "2024-01-15T00:00:00Z",
  "sources": {
    "microsoft_learn": "2024-01-15",
    "github_repo": "commit:abc123",
    "medium": "2024-01-10"
  }
}
```

**sources.json (100 tokens)**:

- URL mappings
- Source priorities
- Update frequencies

## Token Budget Allocation

| Tier | Content           | Token Limit | Auto-Load |
| ---- | ----------------- | ----------- | --------- |
| 1    | Metadata          | 100         | Always    |
| 2    | Core Instructions | 4,700       | Default   |
| 3    | Detailed Docs     | 18,000      | On-demand |
| 4    | Advanced Topics   | 12,000      | Explicit  |

**Total Skill**: ~35,000 tokens (full content)
**Typical Load**: ~5,000 tokens (Tier 1+2)
**Deep Dive**: ~15,000 tokens (Tier 1+2+3 subset)

## Usage Patterns

### Pattern 1: Quick Reference (Tier 1+2)

```
User: "How do I create a basic agent with tools?"
Load: skill.md (metadata + core) = 4,800 tokens
Response: Quick start example from Tier 2
```

### Pattern 2: Detailed Tutorial (Tier 2+3)

```
User: "Show me how to build a workflow with conditional branching"
Load: skill.md + reference/workflows.md + examples/workflow-conditional.md
      = 4,800 + 3,500 + 2,000 = 10,300 tokens
Response: Full workflow tutorial with example
```

### Pattern 3: Advanced Scenario (Tier 2+3+4)

```
User: "Build a RAG agent with async multi-agent coordination"
Load: skill.md + reference/rag.md + reference/async.md + examples/
      = 4,800 + 2,500 + 2,500 + 3,000 = 12,800 tokens
Response: Complete RAG + async implementation
```

### Pattern 4: Decision Support (Tier 2 + Integration)

```
User: "Should I use Agent Framework or amplihack for this feature?"
Load: skill.md + integration/decision-framework.md
      = 4,800 + 1,500 = 6,300 tokens
Response: Decision framework with recommendation
```

## Version Checking Mechanism

### Freshness Strategy

1. **Embedded Version**: `metadata/version.json` records doc generation date
2. **Optional Check**: `scripts/check-freshness.py` validates against live sources
3. **Warning Threshold**: Warn if docs >30 days old
4. **Manual Update**: User or maintainer runs update script

### Check Process

```python
# scripts/check-freshness.py
import requests
from datetime import datetime, timedelta

def check_freshness():
    version = read_version_json()
    docs_date = datetime.fromisoformat(version['docs_version'])
    age = datetime.now() - docs_date

    if age > timedelta(days=30):
        print(f"⚠️  Documentation is {age.days} days old")
        print("Consider updating skill content")
        return False

    print(f"✓ Documentation is current ({age.days} days old)")
    return True
```

### Update Workflow

1. User notices outdated content
2. Run `check-freshness.py` to confirm
3. Fetch latest content from 10 URLs
4. Regenerate skill.md and reference/ files
5. Update metadata/version.json
6. Test with sample queries

## Integration with amplihack

### Integration Point 1: Workflow Orchestration

```markdown
# UltraThink Step 3: Design

- Use architect.md for high-level design
- If implementation requires .NET/Python agents:
  → Invoke microsoft-agent-framework skill
  → Generate Agent Framework code
  → Integrate with amplihack workflow
```

### Integration Point 2: Decision Framework

```markdown
# When planning feature implementation:

1. Does feature need production-grade multi-agent system? → Agent Framework
2. Is feature Claude Code workflow orchestration? → amplihack agents
3. Hybrid: amplihack orchestrates, Agent Framework implements agents
```

### Integration Point 3: Code Generation

```markdown
# builder.md extension:

- For .NET/Python agent code generation
- Use microsoft-agent-framework skill as reference
- Generate agent definitions, workflows, tool integrations
- Maintain amplihack philosophy in generated code
```

## Philosophy Alignment

### Ruthless Simplicity

- **Progressive Disclosure**: Load only what's needed (100 tokens → 35K tokens)
- **Clear Contracts**: Tier structure explicit and predictable
- **Minimal Abstraction**: Direct documentation access, no complex loaders

### Modular Brick Design

- **Single Responsibility**: One skill = Microsoft Agent Framework knowledge
- **Clear Studs**: Tier-based API for content access
- **Regeneratable**: All content from 10 source URLs + distillation rules
- **Self-Contained**: No external runtime dependencies

### Token Efficiency

- **Default Load**: 4,800 tokens (Tier 1+2)
- **Lazy Loading**: Tier 3+4 on-demand only
- **Content Distillation**: 10 URLs → 35K tokens (not 100K+ raw)

## Test Requirements

### Unit Tests

1. **Metadata Parsing**: version.json and sources.json load correctly
2. **Tier Selection**: Auto-select appropriate tier based on query
3. **Content Access**: Read reference/ files without errors
4. **Token Counting**: Verify tier token budgets

### Integration Tests

1. **Quick Reference**: Query answers from Tier 2 only
2. **Deep Dive**: Query loads Tier 3 content correctly
3. **Decision Framework**: Integration guidance works
4. **Code Generation**: Python and C# examples generate valid code

### Validation Tests

1. **Freshness Check**: Version checking script runs
2. **URL Validity**: Source URLs still accessible
3. **Content Accuracy**: Generated code matches framework docs
4. **Philosophy Compliance**: Skill follows amplihack patterns

## Implementation Notes

### Content Extraction Strategy

1. **Automated Scraping**: Use WebFetch tool to retrieve 10 URLs
2. **Manual Distillation**: Human review to extract key concepts
3. **Token Optimization**: Remove redundancy, preserve essential patterns
4. **Example Prioritization**: Working code examples over prose

### Maintenance Strategy

1. **Monthly Review**: Check framework release notes
2. **Quarterly Update**: Refresh content from sources
3. **Version Tracking**: Update metadata/version.json
4. **Breaking Changes**: Flag in skill.md header

### Documentation Workflow

1. Fetch latest content from 10 URLs
2. Distill content by tier (1→2→3→4)
3. Generate markdown files with token counts
4. Validate examples compile/run
5. Update version metadata
6. Test with sample queries

## Success Metrics

### Efficiency Metrics

- **Token Usage**: Average query <10,000 tokens (vs 35K full load)
- **Response Time**: <2s for Tier 1+2 queries
- **Cache Hit Rate**: >80% queries answered by Tier 2

### Quality Metrics

- **Code Validity**: 100% generated examples compile
- **Framework Accuracy**: Matches official docs
- **Decision Quality**: Correct framework selection >90%

### Adoption Metrics

- **Usage Frequency**: Skill invoked 10+ times/month
- **User Satisfaction**: Positive feedback on guidance quality
- **Integration Success**: amplihack + Agent Framework projects launched

## Future Enhancements

### Phase 2: Interactive Features

- RAG-based semantic search across docs
- Live documentation updates
- Interactive tutorials with validation

### Phase 3: Advanced Integration

- Auto-generate amplihack agents from Agent Framework specs
- Bidirectional workflow translation
- Unified observability (amplihack + Agent Framework)

---

**Specification Version**: 1.0.0
**Author**: architect.md
**Created**: 2024-01-15
**Status**: Ready for Implementation
