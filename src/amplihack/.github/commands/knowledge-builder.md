# GitHub Copilot Command Reference: knowledge-builder

**Source**: `.claude/commands/amplihack/knowledge-builder.md`

---

## Command Metadata

- **name**: /socratic
- **version**: 1.0.0
- **description**: Build comprehensive knowledge base using Socratic method and web search
- **triggers**: 
- **invokes**: 
- **- type**: command
- **philosophy**: 
- **- principle**: Modular Design
- **application**: Structured output in 5 self-contained markdown files
- **dependencies**: 
- **required**: 
- **optional**: 
- **examples**: 
- **- "/amplihack**: knowledge-builder Rust memory safety model"

---

## Usage with GitHub Copilot CLI

This command is designed for Claude Code but the patterns and approaches
can be referenced when using GitHub Copilot CLI.

**Example**:
```bash
# Reference this command's approach
gh copilot explain .github/commands/knowledge-builder.md

# Use patterns from this command
gh copilot suggest --context .github/commands/knowledge-builder.md "your task"
```

---

## Original Command Documentation


# Knowledge Builder

Build a comprehensive knowledge base about any topic using the Socratic method (3 levels deep) combined with web search.

## How it Works

1. **Input**: Provide a topic (1-2 sentences)
2. **Question Generation**: Generate 10 initial questions, then recursively apply Socratic method to create ~270 total questions across 4 depth levels
3. **Knowledge Acquisition**: Answer all questions using web search
4. **Artifact Generation**: Create 5 markdown files with structured knowledge

## Output Files

All files are created in `.claude/data/<topic_name>/`:

1. **Knowledge.md** - Visual knowledge graph with mermaid diagram and full question hierarchy
2. **Triplets.md** - Structured fact triplets in (Subject, Predicate, Object) format
3. **KeyInfo.md** - Executive summary with key statistics and core concepts
4. **Sources.md** - All web sources used, organized by domain
5. **HowToUseTheseFiles.md** - Usage guide for the knowledge base

## Question Structure

- **Depth 0**: 10 fundamental questions establishing core understanding
- **Depth 1**: 30 follow-up questions (3 per initial) challenging assumptions
- **Depth 2**: 90 deeper questions (3 per depth-1) exploring implications
- **Depth 3**: ~140 deepest questions (3 per depth-2) testing logical consistency

Total: ~270 questions with web-researched answers

## Example Usage

```bash
/amplihack:knowledge-builder "Quantum computing and its implications for cryptography"
```

## Implementation

```python
import sys

from amplihack.knowledge_builder import KnowledgeBuilder

# Get topic from user prompt (everything after the command)
topic = """{{PROMPT}}"""

if not topic or topic == "{{PROMPT}}":
    print("Usage: /amplihack:knowledge-builder '<topic (1-2 sentences)>'")
    print()
    print("Example:")
    print('  /amplihack:knowledge-builder "Quantum computing and its implications"')
    sys.exit(1)

# Build knowledge base
builder = KnowledgeBuilder(topic)
output_dir = builder.build()

print()
print(f"Knowledge base created at: {output_dir}")
print()
print("Open Knowledge.md to start exploring!")
```

## Notes

- Process takes 10-30 minutes depending on topic complexity
- Requires internet connection for web search
- All answers are backed by cited sources
- Knowledge base is regeneratable at any time
