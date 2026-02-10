# Guide Agent Test Suite

Complete test infrastructure for the guide agent using gadugi-agentic-test framework.

## Overview

This test suite validates the guide agent's ability to adapt teaching approach based on learner persona (beginner, intermediate, advanced).

**Key Features:**

- Persona-based scenario testing
- Automatic metric collection
- Jargon validation
- Pacing analysis ([WAIT] patterns)
- Resource quality assessment
- Iterative re-testing support

## Directory Structure

```
.claude/tests/agentic/guide-agent/
├── config/                          # Configuration files
│   ├── metrics-schema.json          # Defines all collectable metrics
│   ├── validation-patterns.json     # Regex patterns for validation
│   └── test-config.yaml            # gadugi-agentic-test config
├── scenarios/                       # Test scenarios by persona
│   ├── beginner/                   # Beginner-level scenarios
│   ├── intermediate/               # Intermediate-level scenarios
│   ├── advanced/                   # Advanced-level scenarios
│   └── README.md
├── personas/                        # Persona definitions
│   └── README.md
└── README.md                       # This file

../../../test-automation/            # Automation scripts
├── collect-metrics.py              # Metric collection script
└── README.md

../../../evidence/                   # Test evidence
├── conversations/                  # Conversation logs
├── screenshots/                    # Visual evidence
├── metrics/                       # Metric JSON files
├── annotations/                   # Manual notes
└── README.md

../../../reports/                    # Generated reports
├── latest/                        # Latest test run
├── baselines/                     # Baseline comparisons
└── README.md
```

## Quick Start

### 1. Install Dependencies

```bash
# Install gadugi-agentic-test (if available)
npm install -g gadugi-agentic-test

# Verify Python (for metric collection)
python3 --version  # Should be 3.7+
```

### 2. Run a Test Scenario

```bash
# Run single scenario
gadugi-agentic-test run scenarios/beginner/getting-started-first-project.yaml

# Run all beginner scenarios
gadugi-agentic-test run scenarios/beginner/*.yaml --capture
```

### 3. Collect Metrics

```bash
# Metrics are auto-collected via hooks, or manually:
python test-automation/collect-metrics.py \
  --conversation evidence/conversations/beginner-test.log \
  --persona beginner \
  --scenario first-project
```

### 4. View Results

```bash
# View latest report
cat reports/latest/summary.md

# View specific metrics
cat evidence/metrics/beginner-first-project-*.json | jq '.metrics.overallSuccess'
```

## Configuration

### Metrics Schema (`config/metrics-schema.json`)

Defines the complete structure of collected metrics:

- Pedagogical quality (clarity, scaffolding, checkpoints)
- Jargon control (violations, warnings, score)
- Resource guidance (links, quality)
- Interactive engagement (questions, encouragement)
- Error handling (confusion detection, recovery)
- Overall success (composite score, verdict)

### Validation Patterns (`config/validation-patterns.json`)

Contains regex patterns for:

- **Jargon Detection**: Persona-specific forbidden/warning terms
- **[WAIT] Patterns**: Pacing control validation
- **Links**: Documentation, tutorials, interactive resources
- **Checkpoints**: Comprehension check patterns
- **Scaffolding**: Step indicators, building blocks
- **Encouragement**: Supportive language patterns
- **Anti-patterns**: Things to avoid

### Test Configuration (`config/test-config.yaml`)

Main configuration for gadugi-agentic-test:

- Persona definitions and expectations
- Scenario organization
- Metrics collection settings
- Success criteria by persona
- Evidence collection rules
- Report generation settings
- Iterative testing support

## Persona Testing

### Beginner

**Success Criteria:**

- Zero jargon violations
- 2+ [WAIT] patterns for pacing
- 3+ comprehension checkpoints
- 2+ encouragement instances
- No overwhelming anti-patterns

**Example Scenario:**

```yaml
name: "beginner-variables-introduction"
persona: "beginner"
validation:
  metrics:
    - jargonScore >= 8
    - waitUsage >= 2
    - checkpoints >= 3
```

### Intermediate

**Success Criteria:**

- Zero critical jargon violations (some warnings OK)
- 1+ [WAIT] patterns
- 2+ checkpoints
- Moderate scaffolding

### Advanced

**Success Criteria:**

- Strong scaffolding progression
- High-quality resource links
- Technical depth

## Metric Collection

The `collect-metrics.py` script analyzes conversations and generates metrics:

**Collected Automatically:**

- Jargon violation count and type
- [WAIT] pattern frequency
- Checkpoint frequency and distribution
- Link count and context
- Question/engagement count
- Encouragement instances

**Requires Implementation:**

- Concept clarity scoring (currently manual)
- Response adaptation quality (requires conversation analysis)
- Link relevance scoring (requires validation)
- Composite scoring formulas

## Iterative Testing

The framework supports re-testing scenarios:

1. **Version Tracking**: Link metrics to agent versions
2. **Baseline Comparison**: Compare against v3.0.0 baseline
3. **Regression Detection**: Highlight metrics that decreased
4. **Evidence Preservation**: Keep all historical evidence

```bash
# Run with comparison
gadugi-agentic-test run scenarios/beginner/*.yaml \
  --compare-baseline reports/baselines/v3.0.0/ \
  --highlight-regressions
```

## Creating New Scenarios

1. Choose persona directory: `scenarios/{persona}/`
2. Create YAML file: `{category}-{topic}-{variant}.yaml`
3. Define interaction flow
4. Specify validation criteria
5. Reference validation patterns
6. Add to test suite

Example:

```yaml
name: "beginner-loops-introduction"
description: "Teaching loop concepts to beginners"
persona: "beginner"
category: "core-concepts"

interaction:
  - role: user
    message: "I need to do something 10 times. How do I do that?"

  - role: agent
    expectedBehaviors:
      - "uses-analogy"
      - "includes-wait-pattern"
      - "checks-comprehension"
    mustNotContain:
      - "iteration"
      - "iterator"
      - "for...in"
      - "for...of"

validation:
  metrics:
    - jargonScore >= 8
    - waitUsage >= 2
```

## Integration with gadugi-agentic-test

This test suite is designed to integrate with gadugi-agentic-test framework:

- Scenarios follow gadugi YAML format
- Hooks trigger metric collection
- Reports use standard formats
- Evidence structure aligns with gadugi conventions

**Note**: As of this setup, gadugi-agentic-test is not installed. The infrastructure is ready for when it becomes available, or scenarios can be run manually.

## Manual Testing Workflow

Without gadugi-agentic-test installed:

1. **Conduct Conversation**: Run guide agent with test persona
2. **Save Log**: Save conversation to `evidence/conversations/`
3. **Collect Metrics**: Run `collect-metrics.py` on log
4. **Review Results**: Check metrics JSON for pass/fail
5. **Document**: Add annotations to `evidence/annotations/`

## Future Enhancements

- [ ] Complete metric collection implementation (scoring formulas)
- [ ] Add report generation script
- [ ] Add comparison script for historical analysis
- [ ] Create visualization dashboard
- [ ] Implement NLP-based quality assessment
- [ ] Add CI/CD integration
- [ ] Create interactive scenario builder
- [ ] Add A/B testing support

## Support

For issues or questions:

- Review configuration files in `config/`
- Check READMEs in subdirectories
- Examine existing scenarios for examples
- Review metric collection script for patterns
