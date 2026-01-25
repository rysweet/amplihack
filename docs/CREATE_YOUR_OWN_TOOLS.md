# Creating Your Own Tools with Amplihack

Amplihack is designed so **you can create new AI-powered tools** just by describing how they should think. This guide will walk you through the process of turning an idea into a working tool using **metacognitive recipes** – structured thought processes that the AI will follow. You don't need to write code; you'll describe the **problem**, outline the **approach**, and let amplihack build the solution.

**Workflow Overview:**

1.  **Identify a Problem or Need** – Pick a task or workflow you want to automate or improve
2.  **Outline a Metacognitive Recipe** – Describe the step-by-step thinking process an expert would use
3.  **Use Amplihack to Build the Tool** – Launch the creation process with your description (via `/amplihack:ultrathink`)
4.  **Refine and Integrate** – Test the generated tool, give feedback, and iterate until it works well
5.  **Leverage and Evolve** – Use your new tool, combine it with others for bigger tasks, and contribute improvements

## 1. Identify a Problem or Need

Every great tool begins with a **clear need**. Start by pinpointing a task that is repetitive, complex, or time-consuming – something you wish an AI agent could handle reliably. This could be anything from _codebase analysis_ (finding patterns across many files) to _documentation generation_ (creating comprehensive docs from code). The key is that you can describe **what the goal is** and **what a successful outcome looks like**.

If you're unsure what to build, try **brainstorming with amplihack**. For example, you can ask:

```
/amplihack:ultrathink I'm new to creating custom agents. What are some useful tools I could create with amplihack that show how agents can self-evaluate and improve via feedback loops? Just brainstorm ideas, don't build them yet.
```

This will prompt the AI to suggest possible tools. You might get inspired by suggestions like a _"Code Quality Analyzer"_ or a _"Test Coverage Enhancer"_ tool. Use your own experience and needs to choose an idea that would be genuinely useful to you. Remember, amplihack works best when the problem is something **concrete** that you can break down into parts.

## 2. Formulate a Metacognitive Recipe

Once you have a problem in mind, **outline the approach** an expert (or you, on your best day) would take to solve it. This outline is your **metacognitive recipe** – essentially the game plan for the tool. Focus on **how the AI should think**, not just what it should do. Think in terms of stages, decision points, and loops:

### Break the Task into Steps

Divide the problem into logical phases or sub-tasks. Each step should be something the AI can tackle in a single go. For example, a documentation generator might have steps for:

1. _Analyzing code structure_
2. _Extracting function signatures and docstrings_
3. _Generating API reference_
4. _Creating usage examples_
5. _Reviewing for completeness_

If a task feels too big or complex, it's a sign to decompose it into smaller steps or agents. Amplihack excels at this incremental approach. As a rule of thumb, **avoid making one agent handle "everything at once"** – smaller focused steps improve reliability.

_For more strategies on breaking down problems, see **THIS_IS_THE_WAY.md**, which covers best practices like task decomposition._

### Provide Context and Checkpoints

Consider what information each step needs and when to pause for review. For instance, should the AI summarize its findings before moving on? Should it ask the user to confirm something if ambiguity arises? By building in checkpoints or reviews (even if just self-reviews), you make the process more robust.

A tool recipe might include a loop where the AI evaluates its own output or seeks user feedback before proceeding to the next stage.

### Plan for Errors or Ambiguity

Metacognitive recipes often include fallback plans. Think about what the AI should do if a step produces incomplete or low-quality results. For example:

- "If the code analysis is incomplete, have the AI refine it again"
- "If no usage examples can be generated, the tool should explain the issue rather than proceeding blindly"

Designing these recovery or iteration steps helps the tool adapt when things don't go perfectly on the first try.

Write down your recipe in plain language. It can be a numbered list of steps or a few short paragraphs describing the flow. The goal is to **describe the thinking process** clearly enough that amplihack (and you) understand the intended logic.

> **Tip:** Aim for the level of detail you'd give if delegating the task to a smart colleague. Include important details (criteria for decisions, what outputs to generate, etc.), but don't micromanage every tiny action. Amplihack's AI will fill in routine parts – you just define the high-level game plan.

## 3. Use Amplihack to Build the Tool

With your idea and recipe in hand, it's time to **turn it into a tool**. In amplihack, you use the `/amplihack:ultrathink` command to kick off the tool generation:

```
/amplihack:ultrathink <Your tool description and recipe>
```

### Example Tool Creation

```
/amplihack:ultrathink I want to create a tool called "API Documentation Generator".

Goal: Analyze Python API code and generate comprehensive documentation with usage examples.

Steps:
1. Scan the specified directory for Python files containing API endpoints
2. Extract function signatures, docstrings, and type hints
3. Identify request/response models and data structures
4. Generate markdown documentation with:
   - Endpoint descriptions
   - Parameter documentation
   - Response format examples
   - Code usage examples
5. Validate that all public endpoints are documented
6. Offer the draft for review and incorporate feedback
```

When you submit this prompt, amplihack will spring into action:

### Planning and Generation

Amplihack's AI will interpret your description and begin creating the tool. It will:

- Outline the plan using the architect agent
- Create necessary code modules
- Implement each step with the builder agent
- Generate tests with the tester agent

Remember, _you_ are not writing the code – amplihack is, based on your instructions.

### Interactive Clarification

Depending on the complexity, amplihack may ask clarifying questions:

- "Should the documentation include authentication examples?"
- "Do you want to generate OpenAPI/Swagger specs?"
- "Should deprecated endpoints be included or excluded?"

Answer these questions to guide the build. This is amplihack making sure it correctly understands your intent before finalizing the tool.

### Automatic Documentation

Amplihack automatically creates documentation for your new tool as part of the build process. This includes:

- Usage instructions
- Example invocations
- Configuration options
- Integration guidance

## 4. Tool Types and Patterns

Amplihack supports several patterns for tool creation, each suited to different needs.

### Pattern 1: Specialized Agent

Create a new agent that can be invoked for specific tasks.

**When to use:** For tasks that need to be repeated with different inputs

**Location:** `~/.amplihack/.claude/agents/your-agent-name.md`

**Example:**

```markdown
# Your Agent Name

You are a specialized agent for [purpose].

## Capabilities

- [What the agent can do]
- [Specific skills or knowledge]

## Approach

1. [Step 1 of the agent's process]
2. [Step 2]
3. [Step 3]

## Output Format

[What the agent produces]
```

**Invocation:**

```
Can you have the your-agent-name agent analyze @src/api/endpoints.py?
```

### Pattern 2: Slash Command

Create a reusable slash command for common workflows.

**When to use:** For multi-step workflows that you run frequently

**Location:** `~/.amplihack/.claude/commands/your-command.md`

**Example command structure:**

```markdown
# Your Command

Description of what this command does.

## Steps

1. [Action 1]
2. [Action 2]
3. [Action 3]

## Usage

/your-command [arguments]
```

**Invocation:**

```
/your-command [arguments]
```

### Pattern 3: Python Script/Module

Create executable code for complex processing.

**When to use:** For tasks requiring significant computation or external API calls

**Location:** `src/amplihack/tools/your_tool.py`

**Structure:**

```python
"""
Your tool description.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def main(input_path: Path, output_path: Path) -> None:
    """
    Main entry point for your tool.

    Args:
        input_path: Path to input data
        output_path: Where to write results
    """
    logger.info(f"Processing {input_path}")
    # Implementation
    logger.info(f"Results written to {output_path}")

if __name__ == "__main__":
    import sys
    main(Path(sys.argv[1]), Path(sys.argv[2]))
```

**Integration with agent:**
Create an agent in `~/.amplihack/.claude/agents/` that invokes your Python tool.

## 5. Refine the Tool (Iterate and Improve)

Newly generated tools might work on the first try, but often you'll need a round of tweaking to get them just right. Treat this as an iterative **conversation with amplihack**:

### Test the Tool

Run your tool on a sample task or input. For example, if you created an API documentation generator:

```
Use the API Documentation Generator to document @src/api/
```

The tool should execute its steps and produce an output (like generated markdown docs).

### Observe and Note Issues

As it runs, watch for any steps that seem off. Does it skip a step? Is the output of a phase not what you expected? For instance:

- Maybe it didn't include usage examples
- The generated docs are too verbose
- Some endpoints weren't discovered

These observations will guide your refinements.

### Provide Feedback in Context

You can improve the tool by continuing the conversation with amplihack:

```
The generated documentation was missing usage examples.
Please update the tool to include practical code examples for each endpoint.
```

Because amplihack keeps track of the tool it just built, it can modify the implementation accordingly.

### Iterate Until Satisfied

Repeat testing and providing adjustments. Don't hesitate to iterate; this is a normal part of crafting a reliable tool. Even complex multi-step tools can usually be perfected with a few rounds of feedback.

Throughout this refinement, keep the **metacognitive principles** in mind: if a particular step is failing, maybe it needs to be broken into two steps, or given more context. You can instruct amplihack to make such changes:

```
Break the endpoint discovery into a separate step before documentation generation,
so it can handle nested route definitions correctly.
```

## 6. Best Practices for Tool Creation

### Follow the Philosophy

All tools should adhere to amplihack's philosophy (see `~/.amplihack/.claude/context/PHILOSOPHY.md`):

✅ **Ruthless Simplicity**

- Start with minimal implementation
- Add features only when needed
- Avoid premature abstractions

✅ **Zero-BS Implementation**

- No placeholder functions or TODOs
- Complete, working code only
- Explicit error handling

✅ **Modular Design**

- Clear separation of concerns
- Self-contained modules
- Well-defined interfaces

### Error Handling

❌ **Don't do this:**

```python
try:
    result = process()
except:
    pass  # Silent failure
```

✅ **Do this:**

```python
try:
    result = process()
except ProcessingError as e:
    logger.error(f"Processing failed: {e}")
    raise ToolError(f"Failed to process input: {e}") from e
```

### Logging and Visibility

✅ **Always provide feedback:**

```python
logger.info(f"Found {len(files)} files to process")
for file in files[:5]:  # Show first 5
    logger.info(f"  • {file.name}")
if len(files) > 5:
    logger.info(f"  ... and {len(files) - 5} more")
```

### Input Validation

✅ **Validate early:**

```python
def generate_docs(source_dir: Path, output_dir: Path) -> None:
    if not source_dir.exists():
        raise ValueError(f"Source directory does not exist: {source_dir}")
    if not output_dir.parent.exists():
        raise ValueError(f"Output parent directory does not exist: {output_dir.parent}")
    # Proceed with generation
```

## 7. Use Your Tool and Enrich Amplihack

Congratulations – you've built a new tool! Now it's time to put it to work and integrate it into your broader workflows:

### Direct Usage

You can call your tool whenever you need it. For example, once the _API Documentation Generator_ is ready, you can invoke it in any future session:

```
Use the API Documentation Generator to document the new endpoints in @src/api/v2/
```

### Combination and Composition

One of the most powerful aspects of amplihack is that **tools can be combined**. Your new tool can be used alongside others to handle bigger tasks:

```
/amplihack:ultrathink
1. Use the API Documentation Generator on @src/api/
2. Use the code-reviewer agent to review the generated docs
3. Use the knowledge-builder to create a searchable knowledge base from the docs
```

Over time, you'll build up a suite of specialized tools, and you'll find you can chain them together – the output of one becoming the input to another – to accomplish complex workflows.

### Reusable Recipes

The recipe you encoded in your tool is now part of amplihack's knowledge. Future tasks could potentially learn from what you've built. Even if you tackle a different project, you might reuse the same pattern.

For example, the approach used in your documentation tool (e.g. _"scan → extract → generate → validate"_) could be repurposed in a totally different domain by creating a new tool with a similar structure.

### Continuous Improvement

The amplihack system evolves constantly. As you add tools, you're extending the overall capability of the environment. Every tool you create and refine contributes to a richer ecosystem of AI agents.

Your tools might even surface insights for future development. By building and using custom tools, you're helping amplihack get smarter and more useful for everyone.

## 8. Sharing and Next Steps

Part of amplihack's vision is to build a community-driven library of tools. If your new tool is broadly useful, consider contributing it back to the project.

### Contributing Your Tool

1. **Document thoroughly** - Include usage examples and edge cases
2. **Test comprehensively** - Ensure it works across different scenarios
3. **Follow philosophy** - Verify it adheres to ruthless simplicity
4. **Submit a PR** - Include the tool and documentation

### Learning Resources

To deepen your understanding and improve your tool-creation skills, make sure to read:

- **THIS_IS_THE_WAY.md** - Effective strategies and patterns for AI-agent development
- **DISCOVERIES.md** - Non-obvious problems and solutions from real development
- **PHILOSOPHY.md** - Core principles including the Brick Philosophy and zero-BS implementation
- **DEFAULT_WORKFLOW.md** - The multi-step workflow for development tasks
- **Existing Agents** - Browse `~/.amplihack/.claude/agents/` for examples of specialized agents

### Tool Creation Checklist

Before considering your tool complete, verify:

- [ ] Clear purpose and use cases documented
- [ ] Metacognitive recipe is well-defined
- [ ] Input validation implemented
- [ ] Error handling is explicit and informative
- [ ] Logging provides visibility into progress
- [ ] Testing covers common and edge cases
- [ ] No TODOs, placeholders, or stub functions
- [ ] Philosophy compliance verified
- [ ] Usage examples provided
- [ ] Integration with existing agents considered

## Conclusion

By following this guide, you should be able to turn your own ideas into reliable, reusable amplihack tools. **Find a need, describe the approach, and let the AI build it.** You'll be expanding amplihack's capabilities with each tool you create.

The process is iterative and collaborative – you provide the vision and guidance, amplihack provides the implementation. Together, you build tools that make development faster, more reliable, and more enjoyable.

**Have fun experimenting, and happy building!**
