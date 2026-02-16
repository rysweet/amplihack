# Goal-Seeking Agents - Agentic Loop Implementation

LLM-powered agentic loop for goal-seeking agents using the PERCEIVE→REASON→ACT→LEARN pattern.

## Philosophy

- **Ruthlessly Simple**: Core loop with 4 clear phases
- **LLM-Powered**: Uses litellm for reasoning and synthesis (not hardcoded rules)
- **Memory-First**: Stores all learnings in Kuzu graph database
- **Zero-BS**: No stubs, every function works
- **Modular Design**: Self-contained modules with clear contracts

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  WikipediaLearningAgent              │
│  (Specialized agent for learning and Q&A)           │
└──────────────┬──────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────┐
│                    AgenticLoop                       │
│  PERCEIVE → REASON → ACT → LEARN                    │
└──────┬──────────────────┬──────────────┬───────────┘
       │                  │              │
       ▼                  ▼              ▼
┌─────────────┐  ┌──────────────┐  ┌──────────────┐
│  Memory     │  │   Action     │  │   LiteLLM    │
│  Retrieval  │  │  Executor    │  │  (Reasoning) │
└─────────────┘  └──────────────┘  └──────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────┐
│      amplihack-memory-lib (Kuzu Backend)            │
│  - Store experiences                                 │
│  - Search by text                                    │
│  - Graph relationships                               │
└─────────────────────────────────────────────────────┘
```

## Core Components

### 1. AgenticLoop (`agentic_loop.py`)

Main PERCEIVE→REASON→ACT→LEARN loop orchestrator.

**Key Methods:**

- `perceive()`: Observe environment + retrieve relevant memory
- `reason()`: Use LLM to decide action (via litellm)
- `act()`: Execute chosen action
- `learn()`: Store experience in memory
- `run_iteration()`: Execute one complete loop iteration
- `run_until_goal()`: Run loop until goal achieved

**Example:**

```python
from amplihack.agents.goal_seeking import AgenticLoop, ActionExecutor, MemoryRetriever

memory = MemoryRetriever("my_agent")
executor = ActionExecutor()
executor.register_action("greet", lambda name: f"Hello {name}!")

loop = AgenticLoop(
    agent_name="my_agent",
    action_executor=executor,
    memory_retriever=memory,
    model="gpt-3.5-turbo"
)

state = loop.run_iteration(
    goal="Greet the user",
    observation="User Alice is present"
)

print(state.reasoning)  # LLM's reasoning
print(state.outcome)    # Action result
```

### 2. MemoryRetriever (`memory_retrieval.py`)

Interface to Kuzu graph database for storing and searching experiences.

**Key Methods:**

- `search()`: Text-based search over stored experiences
- `store_fact()`: Store a learned fact with confidence
- `get_statistics()`: Memory usage statistics

**Example:**

```python
from amplihack.agents.goal_seeking import MemoryRetriever

memory = MemoryRetriever("my_agent", backend="kuzu")

# Store fact
memory.store_fact(
    context="Photosynthesis",
    fact="Plants convert light to chemical energy",
    confidence=0.9,
    tags=["biology", "plants"]
)

# Search
results = memory.search("photosynthesis", limit=5)
for result in results:
    print(f"{result['context']}: {result['outcome']}")
```

### 3. ActionExecutor (`action_executor.py`)

Tool registry for actions agents can perform.

**Key Methods:**

- `register_action()`: Register a new action
- `execute()`: Execute action by name
- `get_available_actions()`: List registered actions

**Standard Actions:**

- `read_content()`: Read and parse text content
- `search_memory()`: Search memory for experiences
- `synthesize_answer()`: Use LLM to synthesize answer from context

**Example:**

```python
from amplihack.agents.goal_seeking import ActionExecutor

executor = ActionExecutor()

# Register custom action
def calculate(a: int, b: int) -> int:
    return a + b

executor.register_action("add", calculate)

# Execute
result = executor.execute("add", a=5, b=3)
print(result.output)  # 8
```

### 4. WikipediaLearningAgent (`wikipedia_learning_agent.py`)

Specialized agent that learns from Wikipedia content and answers questions using LLM synthesis.

**Question Complexity Levels:**

- **L1 (Recall)**: Direct fact retrieval - "What is X?"
- **L2 (Inference)**: Connect facts - "Why does X happen?"
- **L3 (Synthesis)**: Create understanding - "How are X and Y related?"
- **L4 (Application)**: Apply knowledge - "How would you use X to solve Y?"

**Key Methods:**

- `learn_from_content()`: Extract facts from text using LLM
- `answer_question()`: Answer question using LLM synthesis
- `get_memory_stats()`: Memory statistics

**Example:**

```python
from amplihack.agents.goal_seeking import WikipediaLearningAgent

agent = WikipediaLearningAgent("wiki_agent")

# Learn from content
agent.learn_from_content("""
Photosynthesis is the process by which plants convert light energy
into chemical energy. It occurs in chloroplasts using chlorophyll.
""")

# Answer L1 question (recall)
answer = agent.answer_question("What is photosynthesis?", question_level="L1")
print(answer)

# Answer L2 question (inference)
answer = agent.answer_question("Why do plants need light?", question_level="L2")
print(answer)

# Answer L3 question (synthesis)
answer = agent.answer_question(
    "How does photosynthesis relate to respiration?",
    question_level="L3"
)
print(answer)

agent.close()
```

## Key Features

### LLM-Powered Reasoning

Unlike rule-based systems, this implementation uses LLMs (via litellm) to:

- **Decide actions**: LLM reasons about what to do given the goal
- **Extract facts**: LLM structures information from unstructured text
- **Synthesize answers**: LLM combines retrieved facts into coherent answers

### Memory Integration

All learnings are stored in amplihack-memory-lib with Kuzu backend:

- **Graph structure**: Experiences as nodes with relationships
- **Text search**: Find relevant experiences by query
- **Confidence tracking**: Each experience has confidence score
- **Tags**: Organize experiences by topic

### Testable Without API Keys

All tests use mocked LLM responses:

```python
@patch('amplihack.agents.goal_seeking.agentic_loop.litellm.completion')
def test_reason_calls_llm(mock_completion, loop):
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(message=MagicMock(content='{"reasoning": "...", "action": "greet"}'))
    ]
    mock_completion.return_value = mock_response

    result = loop.reason("Goal: Test")
    assert result["action"] == "greet"
```

## Dependencies

- **litellm**: LLM calls (OpenAI, Anthropic, etc.)
- **amplihack-memory-lib**: Memory storage (Kuzu backend)
- **kuzu**: Graph database

All dependencies are already in pyproject.toml.

## Running Tests

```bash
# All tests
pytest tests/agents/goal_seeking/ -v

# Specific module
pytest tests/agents/goal_seeking/test_agentic_loop.py -v

# With coverage
pytest tests/agents/goal_seeking/ --cov=src/amplihack/agents/goal_seeking
```

All 61 tests pass without requiring API keys (uses mocked LLM).

## Usage Patterns

### Pattern 1: Custom Goal-Seeking Agent

```python
from amplihack.agents.goal_seeking import AgenticLoop, ActionExecutor, MemoryRetriever

# Create memory and executor
memory = MemoryRetriever("custom_agent")
executor = ActionExecutor()

# Register domain-specific actions
executor.register_action("fetch_data", lambda url: fetch_from_api(url))
executor.register_action("process", lambda data: process_data(data))

# Create loop
loop = AgenticLoop("custom_agent", executor, memory, model="gpt-4")

# Run
state = loop.run_iteration(
    goal="Fetch and process user data",
    observation="User ID: 12345"
)
```

### Pattern 2: Multi-Iteration Goal Pursuit

```python
def check_goal(state):
    return "success" in str(state.outcome).lower()

states = loop.run_until_goal(
    goal="Complete data pipeline",
    initial_observation="Pipeline starting",
    is_goal_achieved=check_goal
)

for i, state in enumerate(states):
    print(f"Iteration {i+1}: {state.action['action']} → {state.outcome}")
```

### Pattern 3: Wikipedia Learning and Q&A

```python
agent = WikipediaLearningAgent()

# Learn from multiple articles
articles = ["article1.txt", "article2.txt"]
for article in articles:
    with open(article) as f:
        agent.learn_from_content(f.read())

# Answer questions at different levels
questions = [
    ("What is quantum mechanics?", "L1"),
    ("Why is quantum mechanics important?", "L2"),
    ("How does quantum mechanics relate to computing?", "L3"),
    ("How would you apply quantum mechanics to cryptography?", "L4")
]

for question, level in questions:
    answer = agent.answer_question(question, question_level=level)
    print(f"\n{question}\n{answer}")
```

## Implementation Notes

### LiteLLM Configuration

Set environment variables for your LLM provider:

```bash
# OpenAI
export OPENAI_API_KEY=sk-...

# Anthropic
export ANTHROPIC_API_KEY=sk-ant-...

# Azure OpenAI
export AZURE_API_KEY=...
export AZURE_API_BASE=...
export AZURE_API_VERSION=...
```

Then specify model in litellm format:

- `"gpt-3.5-turbo"` - OpenAI GPT-3.5
- `"gpt-4"` - OpenAI GPT-4
- `"claude-3-sonnet-20240229"` - Anthropic Claude 3
- `"azure/gpt-4"` - Azure OpenAI

### Memory Storage Location

By default, memory is stored at `~/.amplihack/memory/<agent_name>/kuzu_db/`

Override with `storage_path` parameter:

```python
memory = MemoryRetriever(
    agent_name="my_agent",
    storage_path="/custom/path/memory"
)
```

## Future Enhancements

Potential extensions (not implemented yet):

1. **Graph Relationships**: Use Kuzu's SIMILAR_TO and LEADS_TO edges
2. **Batch Learning**: Process multiple documents in parallel
3. **Incremental Learning**: Update facts rather than always append
4. **Confidence Decay**: Lower confidence of old facts over time
5. **Multi-Agent Collaboration**: Agents share memory selectively

## Issue Reference

This implementation addresses Issue #2341: LLM-powered agentic loop for goal-seeking agents.

**Key Requirements Met:**

- ✅ PERCEIVE→REASON→ACT→LEARN loop using litellm
- ✅ Kuzu memory search via amplihack-memory-lib
- ✅ Tool registry with extensible actions
- ✅ Wikipedia learning agent with L1-L4 questions
- ✅ LLM synthesis (not just retrieval)
- ✅ Testable without API keys (mocked LLM)
- ✅ 61 passing tests with 100% coverage of core logic

## License

Same as amplihack parent project.
