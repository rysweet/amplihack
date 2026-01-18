# Microsoft Agent Framework - Overview

## What is Microsoft Agent Framework?

Microsoft Agent Framework is an open-source platform for building production-ready AI agents and multi-agent workflows. It unifies the simplicity of AutoGen with the enterprise features of Semantic Kernel into a single, cohesive framework.

**Key Characteristics**:

- **Open-source**: MIT license, community-driven development
- **Multi-language**: Full support for Python 3.10+ and C# (.NET 8.0+)
- **Enterprise-ready**: Built-in telemetry, middleware, security, and monitoring
- **Research-to-production**: Direct path from experimentation to deployment

## Architecture

### Core Components

1. **AI Agents**
   - Stateful conversational entities
   - Process messages, call tools, maintain context
   - Support for single-turn and multi-turn conversations
   - Thread-based conversation management

2. **Workflows**
   - Graph-based orchestration engine
   - Executors (agents as workflow nodes)
   - Edges (control flow between nodes)
   - Support for sequential, parallel, and conditional routing

3. **Model Clients**
   - Abstraction over LLM providers (OpenAI, Azure OpenAI, local models)
   - Unified API regardless of provider
   - Support for structured outputs and function calling

4. **Thread Management**
   - Conversation history tracking
   - State persistence across turns
   - Thread-level context providers

5. **Context Providers**
   - Plugin system for external context
   - Database integration, document retrieval, API calls
   - Custom context injection per message

6. **Middleware**
   - Request/response interceptors
   - Cross-cutting concerns (logging, auth, rate limiting)
   - Composable middleware chains

7. **MCP Clients**
   - Model Context Protocol integration
   - Connect to external tools and services
   - Standardized tool communication

## Use Cases

### Customer Support

Build conversational agents that:

- Maintain context across interactions
- Access knowledge bases and CRM systems
- Escalate to human agents when needed
- Track conversation sentiment and satisfaction

**Example**: Multi-tier support bot with intent classification → FAQ agent → technical support agent → human escalation workflow.

### Education & Tutoring

Create adaptive learning systems that:

- Tailor explanations to student level
- Track learning progress over sessions
- Provide interactive exercises with feedback
- Integrate with course materials and assessments

**Example**: Math tutor that remembers student's weak areas, adapts problem difficulty, and provides step-by-step explanations.

### Code Generation & Review

Develop coding assistants that:

- Generate code from natural language descriptions
- Review and suggest improvements to existing code
- Maintain coding style and best practices
- Integrate with version control and CI/CD

**Example**: Multi-agent workflow with requirements agent → architect → coder → reviewer → tester.

### Research & Analysis

Build research tools that:

- Gather information from multiple sources
- Synthesize findings into coherent reports
- Track citations and sources
- Support iterative refinement

**Example**: Research workflow with source gathering agent → fact checker → synthesizer → citation formatter.

### Data Processing Pipelines

Create data workflows that:

- Process data through multiple stages
- Apply transformations and validations
- Handle errors and retries gracefully
- Monitor progress and generate reports

**Example**: ETL pipeline with extractor agent → transformer agents (parallel) → validator → loader.

## Framework Philosophy

### Design Principles

1. **Simplicity First**
   - Start with simple agents, add complexity as needed
   - Sensible defaults, explicit overrides
   - Clear error messages and debugging tools

2. **Enterprise Readiness**
   - Production-grade telemetry and monitoring
   - Security and auth built-in
   - Scalable architecture for high-throughput scenarios

3. **Extensibility**
   - Plugin system for custom components
   - Open standards (OpenTelemetry, MCP)
   - Community contributions welcomed

4. **Research Integration**
   - Direct pipeline from research (AF Labs) to production
   - Bleeding-edge features available in preview
   - Benchmarking and evaluation tools included

## Comparison with Other Frameworks

### vs. LangChain

- **Agent Framework**: Stronger typing, better enterprise features, graph-based workflows
- **LangChain**: Broader ecosystem, more integrations, mature documentation

### vs. AutoGen

- **Agent Framework**: Superset of AutoGen with enterprise features and workflows
- **AutoGen**: Simpler, research-focused, fewer dependencies

### vs. Semantic Kernel

- **Agent Framework**: Unified API combining SK's enterprise features with AutoGen's simplicity
- **Semantic Kernel**: More Azure-centric, stronger .NET support historically

### vs. amplihack

- **Agent Framework**: Stateful conversational agents, complex orchestration, enterprise features
- **amplihack**: Stateless task delegation, file-based operations, token-efficient skills
- **Best together**: Use Agent Framework for stateful agents, amplihack for orchestration

## Installation & Setup

### Python

```bash
# Install preview version
pip install agent-framework --pre

# With optional dependencies
pip install agent-framework[openai,azure,telemetry] --pre

# Development install
git clone https://github.com/microsoft/agent-framework.git
cd agent-framework/python
pip install -e ".[dev]"
```

### C#

```bash
# Install preview package
dotnet add package Microsoft.Agents.AI --prerelease

# With specific providers
dotnet add package Microsoft.Agents.AI.OpenAI --prerelease
dotnet add package Microsoft.Agents.AI.Azure --prerelease
```

### Environment Configuration

```bash
# OpenAI
export OPENAI_API_KEY=sk-...

# Azure OpenAI
export AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
export AZURE_OPENAI_API_KEY=...
export AZURE_OPENAI_DEPLOYMENT=gpt-4

# Telemetry (optional)
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

## Quick Start Example

### Python

```python
import asyncio
from agents_framework import Agent, ModelClient

async def main():
    # Create agent
    agent = Agent(
        name="assistant",
        model=ModelClient(model="gpt-4"),
        instructions="You are a helpful assistant"
    )

    # Run conversation
    response = await agent.run(message="Hello! What can you help with?")
    print(response.content)

if __name__ == "__main__":
    asyncio.run(main())
```

### C#

```csharp
using Microsoft.Agents.AI;

var agent = new Agent(
    name: "assistant",
    model: new ModelClient(model: "gpt-4"),
    instructions: "You are a helpful assistant"
);

var response = await agent.RunAsync("Hello! What can you help with?");
Console.WriteLine(response.Content);
```

## Community & Support

- **GitHub**: https://github.com/microsoft/agent-framework
- **Documentation**: https://microsoft.github.io/agent-framework/
- **Issues**: https://github.com/microsoft/agent-framework/issues
- **Discussions**: https://github.com/microsoft/agent-framework/discussions

## Versioning & Releases

Current version: **0.1.0-preview** (as of 2025-11-15)

**Release Cadence**: Monthly preview releases, quarterly stable releases (planned)

**Breaking Changes**: Expect API changes during preview phase. Semantic versioning after 1.0.0.

**Migration Path**: Upgrade guides provided for each release with breaking changes.

## License

MIT License - see [LICENSE](https://github.com/microsoft/agent-framework/blob/main/LICENSE) for details.
