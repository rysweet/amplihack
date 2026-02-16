# Agent Learning Evaluation Harness

Production-ready evaluation framework that proves goal-seeking agents can learn across execution boundaries using persistent memory.

## Quick Start

```bash
# Run end-to-end evaluation
python -m amplihack.eval.harness_runner --news-file news_data.json

# Generate quiz only
python -m amplihack.eval.quiz_generator --news-file news_data.json --output quiz.json

# Grade answers manually
python -m amplihack.eval.grader --quiz quiz.json --answers answers.json
```

## Architecture

### Components

1. **multi_source_collector.py**: Transforms WebSearch results into structured news data
2. **quiz_generator.py**: Generates L1-L4 cognitive level questions
3. **harness_runner.py**: Orchestrates learning → testing phases in subprocesses
4. **grader.py**: Semantically evaluates agent answers using LLM
5. **agent_subprocess.py**: Agent implementation for learning and testing phases

### Cognitive Levels

- **L1 (Recall)**: Direct facts from single source
- **L2 (Inference)**: Reasoning from facts within one source
- **L3 (Synthesis)**: Combining information across multiple sources
- **L4 (Application)**: Applying knowledge to hypothetical scenarios

## Usage

### Step 1: Collect News Data

Provide WebSearch results as JSON:

```json
{
  "sources": [
    {
      "url": "https://example.com/article1",
      "title": "Breaking News",
      "content": "Full article text...",
      "published": "2026-02-16T10:00:00Z"
    }
  ]
}
```

### Step 2: Run Harness

```bash
python -m amplihack.eval.harness_runner \
  --news-file news.json \
  --output-dir results/ \
  --agent-name test-agent \
  --memory-backend amplihack-memory-lib
```

### Step 3: Review Results

Results stored in `results/`:

- `quiz.json`: Generated questions
- `learning_phase.log`: Learning phase execution
- `testing_phase.log`: Testing phase execution
- `scores.json`: Grading results with semantic analysis

## Memory Integration

The harness uses `amplihack-memory-lib` (SQLite-based) for persistent storage:

```python
from amplihack_memory import MemoryConnector, Experience

# Learning phase
connector = MemoryConnector(agent_name="test-agent")
experience = Experience(
    experience_type=ExperienceType.LEARNING,
    context="News article about AI",
    outcome="Key facts stored",
    confidence=0.95
)
connector.store_experience(experience)

# Testing phase
experiences = connector.retrieve_experiences(
    query="AI developments",
    limit=10
)
```

## Subprocess Isolation

Each phase runs in a separate subprocess with clean environment:

```python
import subprocess
import json

# Learning phase
result = subprocess.run(
    ["python", "-m", "amplihack.eval.agent_subprocess", "--phase", "learning"],
    input=json.dumps(news_data),
    capture_output=True,
    text=True
)

# Testing phase
result = subprocess.run(
    ["python", "-m", "amplihack.eval.agent_subprocess", "--phase", "testing"],
    input=json.dumps(quiz_questions),
    capture_output=True,
    text=True
)
```

## Grading

Semantic evaluation uses LLM to compare agent answers with expected answers:

```python
from amplihack.eval.grader import grade_answer

score = grade_answer(
    question="What was announced?",
    expected="New AI model released",
    actual="Company launched AI system",
    level="L1"
)

# Returns: {"score": 0.9, "reasoning": "Semantically equivalent..."}
```

## Example Run

```bash
$ python -m amplihack.eval.harness_runner --news-file tech_news.json

[1/4] Collecting news data...
  Sources: 5
  Articles: 12

[2/4] Generating quiz questions...
  L1 (Recall): 3 questions
  L2 (Inference): 3 questions
  L3 (Synthesis): 2 questions
  L4 (Application): 2 questions

[3/4] Running learning phase...
  Agent stored 47 experiences
  Duration: 8.2s

[4/4] Running testing phase...
  Agent answered 10/10 questions
  Average confidence: 0.87
  Duration: 12.5s

[RESULTS]
  L1 Score: 95% (2.85/3.0)
  L2 Score: 88% (2.64/3.0)
  L3 Score: 75% (1.50/2.0)
  L4 Score: 70% (1.40/2.0)

  Overall: 84% (8.39/10.0)
  Memory Hit Rate: 92%
```

## Success Criteria

The harness validates:

1. Agent can store structured knowledge from news
2. Agent can retrieve relevant memories when answering
3. Answers show cross-execution learning (not in prompt)
4. Scores increase with memory vs. without memory baseline

## Philosophy Compliance

- **Ruthless Simplicity**: Each component has ONE job
- **Zero-BS Implementation**: No stubs, everything works
- **Regeneratable**: Complete specification in this doc
- **Testable**: Each component independently testable

## See Also

- [Memory System Architecture](../memory/ARCHITECTURE.md)
- [amplihack-memory-lib Documentation](../../amplihack-memory-lib/README.md)
- [Cognitive Level Definitions](./cognitive-levels.md)
