# Test Personas

This directory contains persona definitions for guide agent testing.

## Overview

Each persona represents a different learner profile with specific needs, expectations, and success criteria.

## Persona Definitions

### Beginner
- **Display Name**: Complete Beginner
- **Background**: New to programming
- **Needs**: Extensive scaffolding, analogies, encouragement
- **Jargon Tolerance**: Minimal - technical terms must be explained
- **Pacing**: Slow with frequent checkpoints
- **Success Criteria**: Zero jargon violations, 2+ [WAIT] patterns, 3+ checkpoints

### Intermediate
- **Display Name**: Intermediate Learner
- **Background**: Some programming experience
- **Needs**: Context, moderate scaffolding
- **Jargon Tolerance**: Moderate - common terms OK with context
- **Pacing**: Moderate with regular checkpoints
- **Success Criteria**: Zero critical violations, 1+ [WAIT] patterns, 2+ checkpoints

### Advanced
- **Display Name**: Advanced Developer
- **Background**: Experienced programmer
- **Needs**: Concise explanations, technical depth
- **Jargon Tolerance**: High - technical communication preferred
- **Pacing**: Fast, minimal hand-holding
- **Success Criteria**: Strong scaffolding progression, high-quality resources

## Persona Files

Create individual persona YAML files for detailed configuration:

```yaml
# beginner.yaml
name: "beginner"
displayName: "Complete Beginner"

characteristics:
  priorKnowledge: "none"
  learningStyle: "visual-and-analogical"
  motivationLevel: "high-but-fragile"
  frustrationTolerance: "low"
  
expectations:
  maxJargonViolations: 0
  minWaitUsage: 2
  minCheckpoints: 3
  requiresEncouragement: true
  
responses:
  confusion:
    - "I don't understand what that means"
    - "Can you explain that differently?"
    - "I'm lost"
  
  understanding:
    - "Oh, I think I get it!"
    - "So it's like..."
    - "That makes sense"
```

## Usage

Persona files are referenced in test scenarios to determine appropriate validation criteria and expected agent behaviors.
