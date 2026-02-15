# Code Pattern Recognizer Agent

Learning agent that recognizes design patterns in Python code and improves recognition accuracy through experience.

## Overview

The Code Pattern Recognizer analyzes Python codebases to identify common design patterns:

- **Singleton Pattern**: Single instance classes
- **Factory Pattern**: Object creation abstractions
- **Observer Pattern**: Event-driven subscriptions
- **Strategy Pattern**: Interchangeable algorithms
- **Decorator Pattern**: Behavior enhancement

## Features

- **AST-based Analysis**: Uses Python's Abstract Syntax Tree for accurate pattern detection
- **Learning from Experience**: Stores pattern instances in memory for improved accuracy
- **Confidence Scoring**: Each pattern match has confidence score (0.0 to 1.0)
- **Refactoring Suggestions**: Provides actionable recommendations
- **Performance Tracking**: Demonstrates measurable learning (speed and accuracy improvements)

## Usage

### Basic Usage

```python
from pattern_recognizer import CodePatternRecognizer
from pathlib import Path

# Create agent with memory enabled
agent = CodePatternRecognizer(enable_memory=True)

# Analyze codebase
result = agent.execute(target=Path("./src"))

print(f"Patterns found: {result.patterns_found}")
print(f"Runtime: {result.runtime_seconds:.2f}s")
print(f"Suggestions: {result.refactoring_suggestions}")
```

### Without Memory (Baseline)

```python
# Disable memory for comparison
agent = CodePatternRecognizer(enable_memory=False)
result = agent.execute(target=Path("./src"))
```

### Tracking Learning Progress

```python
from pattern_recognizer.metrics import PatternRecognitionMetrics

metrics = PatternRecognitionMetrics(agent.memory)

# Get accuracy stats
accuracy = metrics.get_accuracy_stats()
print(f"Accuracy: {accuracy['accuracy']:.2%}")

# Get runtime improvement
improvement = metrics.get_runtime_improvement()
print(f"Speed improvement: {improvement['improvement_percentage']:.1f}%")

# Get confidence progression
confidence = metrics.get_confidence_progression()
print(f"Average confidence: {confidence['average_confidence']:.2f}")
```

## How Learning Works

1. **First Run**: Agent analyzes code using AST parsing and pattern signatures
   - Detects patterns based on code structure and naming
   - Stores pattern experiences in memory

2. **Second Run**: Agent loads previous patterns from memory
   - Applies cached pattern knowledge (0.1 confidence boost)
   - Faster analysis due to pattern recognition shortcuts
   - Stores updated experiences with higher confidence

3. **Subsequent Runs**: Continuous improvement
   - Pattern confidence increases with validation
   - Recognition speed improves (10-30% faster)
   - Suggestions become more specific

## Success Criteria

The agent demonstrates measurable learning:

- **Speed Improvement**: >10% faster on second run
- **Accuracy Improvement**: >5% better pattern detection
- **Confidence Growth**: Pattern confidence increases over time

## Testing

Run the test suite to validate learning behavior:

```bash
cd generated-agents/pattern-recognizer
pytest tests/test_pattern_recognizer_learning.py -v
```

Tests validate:

- Pattern recognition accuracy
- Learning behavior over multiple runs
- Memory retrieval and storage
- Runtime improvement metrics

## Architecture

```
pattern-recognizer/
├── agent.py              # Main agent implementation
├── metrics.py            # Learning metrics tracking
├── tests/
│   └── test_pattern_recognizer_learning.py
├── requirements.txt
└── README.md
```

### Key Components

**CodePatternRecognizer**

- Main agent class
- Executes pattern analysis
- Manages memory integration

**PatternMatch**

- Data class for single pattern match
- Includes confidence score and context

**PatternAnalysis**

- Result object with analysis details
- Contains matches, suggestions, metrics

**PatternRecognitionMetrics**

- Tracks learning progress
- Calculates accuracy and improvement

## Memory Storage

Patterns are stored as `Experience` objects:

```python
Experience(
    experience_type=ExperienceType.PATTERN,
    context="singleton pattern in config.py",
    outcome="Detected with 0.85 confidence",
    confidence=0.85,
    metadata={"pattern_name": "singleton", "file": "config.py"},
    tags=["pattern", "singleton"]
)
```

## Dependencies

- Python 3.10+
- `amplihack-memory-lib`: Memory system
- Standard library: `ast`, `pathlib`, `dataclasses`

No external dependencies beyond memory-lib.

## Example Output

```
Analysis Complete
-----------------
Patterns found: 8
Runtime: 1.23s
Files analyzed: 15

Patterns detected:
- singleton (2 instances, avg confidence: 0.87)
- factory (3 instances, avg confidence: 0.82)
- decorator (3 instances, avg confidence: 0.79)

Refactoring suggestions:
1. Multiple singleton patterns detected (2). Consider consolidating or using dependency injection.
2. Multiple factory patterns (3) found. Consider abstract factory or factory method pattern.
3. Multiple decorators (3). Consider decorator composition patterns.

Memory status:
- Patterns loaded: 12
- Experiences stored: 8
- Runtime improvement: 15.3%
```

## Limitations

- Python code only (not language-agnostic)
- AST-based detection (may miss dynamic patterns)
- Pattern signatures are simplified (not exhaustive)
- Confidence scores are heuristic-based

## Future Enhancements

- Support for additional patterns (Builder, Prototype, Adapter, etc.)
- Cross-file pattern detection (patterns spanning multiple modules)
- Integration with code quality tools (pylint, mypy)
- Visual pattern diagrams
- Pattern anti-pattern detection
