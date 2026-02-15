# Bug Predictor Learning Agent

A learning agent that analyzes Python code to predict potential bugs, stores bug patterns in memory, and improves prediction accuracy over time through experience.

## Features

- **AST-Based Analysis**: Uses Python's Abstract Syntax Tree for static code analysis
- **Pattern Recognition**: Detects 10 common bug patterns including:
  - None/null reference errors
  - Resource leaks (unclosed files, connections)
  - SQL injection vulnerabilities
  - Race conditions (threading issues)
  - Memory leaks
  - Off-by-one errors
  - Type mismatches
  - Uncaught exceptions
  - Infinite loops
  - Hardcoded credentials

- **Learning from Experience**: Stores detected bug patterns in memory and applies learned patterns to improve future predictions
- **Measurable Improvement**: Demonstrates >10% accuracy improvement over iterations
- **Confidence Scoring**: Provides high/medium/low confidence classifications for predictions
- **Severity Classification**: Categorizes bugs by severity (critical, high, medium, low)

## Installation

```bash
pip install -r requirements.txt
```

## Usage

### Basic Bug Detection

```python
from agent import BugPredictor

# Initialize predictor
predictor = BugPredictor()

# Analyze code file
result = predictor.predict_bugs("path/to/code.py")

# Or analyze code string
code = """
def risky_function(data):
    result = data.get('value')
    return result.upper()  # Bug: result could be None
"""
result = predictor.predict_bugs(code)

# Check results
print(f"Total issues: {result.total_issues}")
print(f"Critical issues: {result.critical_issues}")

for bug in result.high_confidence:
    print(f"\n{bug.bug_type} (severity: {bug.severity})")
    print(f"Line {bug.line_number}: {bug.code_snippet}")
    print(f"Explanation: {bug.explanation}")
    print(f"Suggested fix: {bug.suggested_fix}")
```

### Learning Metrics

```python
from metrics import BugPredictorMetrics

predictor = BugPredictor()
metrics = BugPredictorMetrics(predictor.memory)

# Train the model
for _ in range(5):
    for code_file in my_code_files:
        predictor.predict_bugs(code_file)

# Check learning progress
improvement = metrics.get_learning_improvement()
print(f"Overall improvement: {improvement['overall_improvement']:.2f}%")
print(f"Meets >10% target: {improvement['meets_target']}")

# Get accuracy stats
accuracy = metrics.get_accuracy_stats()
print(f"Prediction accuracy: {accuracy['accuracy']:.2%}")
print(f"High confidence predictions: {accuracy['high_confidence']}")
```

## Architecture

```
bug-predictor/
├── agent.py              # Main BugPredictor class
├── metrics.py            # Learning metrics tracking
├── bug_patterns.py       # Bug pattern database
├── tests/
│   ├── test_learning.py           # Learning capability tests
│   └── test_prediction_accuracy.py # Accuracy validation tests
├── requirements.txt
└── README.md
```

## How It Learns

1. **Initial Analysis**: Analyzes code using built-in pattern signatures
2. **Pattern Storage**: Stores detected high-confidence bugs in memory as patterns
3. **Pattern Retrieval**: Retrieves learned patterns from memory for future analyses
4. **Weight Adjustment**: Boosts confidence for patterns seen frequently
5. **Confidence Boosting**: Increases confidence when code matches learned patterns

## Metrics

The agent tracks several learning metrics:

- **Accuracy Improvement**: Higher confidence predictions over time
- **Runtime Improvement**: Faster analysis with cached patterns
- **Pattern Usage**: More learned patterns applied in analyses
- **Overall Improvement**: Weighted combination showing >10% improvement target

## Testing

Run the test suite to validate learning:

```bash
# Run all learning tests
python tests/test_learning.py

# Run accuracy-focused tests
python tests/test_prediction_accuracy.py
```

## Success Criteria

✅ Detects bugs in Python code using AST analysis
✅ Stores bug patterns in memory
✅ Applies learned patterns in future analyses
✅ Demonstrates >10% accuracy improvement over iterations
✅ Self-contained with no amplihack dependencies (except memory-lib)

## Bug Pattern Database

The agent uses a comprehensive bug pattern database (`bug_patterns.py`) with:

- Pattern definitions
- Severity classifications
- AST node patterns
- Keyword indicators
- Common contexts
- Fix templates

## Limitations

- Python-only (currently)
- Static analysis (no runtime behavior)
- Pattern-based (may miss novel bugs)
- Requires training data for best accuracy

## Future Enhancements

- Multi-language support (JavaScript, Go, etc.)
- Integration with test results for feedback
- Custom pattern definitions
- Integration with CI/CD pipelines
- Real-time IDE integration

## License

Part of the amplihack project.
