# AI Working Directory

This directory contains **experimental tools under development** - the innovation lab for amplihack's tool ecosystem.

## Purpose

The `ai_working/` directory serves as:

- **Innovation Space**: Rapid prototyping of new tool ideas
- **Testing Ground**: Validation of concepts before production
- **Learning Lab**: Experimentation with new patterns and approaches
- **Incubation**: Safe space for tools that may fail or evolve significantly

## Guidelines

### Experimentation Rules

1. **Fast Iteration**: Build quickly, test immediately, learn rapidly
2. **Document Learning**: Capture insights in `notes.md` files
3. **Real Usage**: Test with actual use cases, not just theory
4. **Simple Structure**: Keep it minimal until patterns emerge

### Directory Structure

```
ai_working/
├── README.md           # This file
├── experimental-tool/  # Each experiment gets its own directory
│   ├── README.md      # Basic description and current status
│   ├── prototype.py   # Working code (however minimal)
│   ├── notes.md       # Learning, issues, next steps
│   └── examples/      # Test cases and usage examples
└── archive/           # Deprecated or failed experiments
```

### Tool Lifecycle

1. **Initial Idea**: Create directory with basic README
2. **Rapid Prototype**: Build minimal working version
3. **User Testing**: Get feedback from real scenarios
4. **Iteration**: Refine based on learning
5. **Decision Point**: Graduate to scenarios/ or archive

## Quality Standards

Even experimental tools must:

- **Work**: No broken or non-functional code
- **Be Documented**: Clear README with current status
- **Follow Philosophy**: Respect amplihack's simplicity principles
- **Be Safe**: No security risks or destructive behavior

## Graduation Criteria

Move to `~/.amplihack/.claude/scenarios/` when:

- Used successfully by 2-3 real users
- Stable interface (no breaking changes for 1+ week)
- Clear value proposition validated
- Ready for full documentation and testing

## Archive Policy

Move to `archive/` when:

- Concept proven invalid or unnecessary
- Better solution found elsewhere
- No user interest after reasonable trial period
- Technical blockers make completion infeasible

## Common Experiment Types

### Tool Prototypes

- New automation concepts
- Workflow improvements
- Integration experiments

### Pattern Validation

- Testing new organizational approaches
- Validating user interface concepts
- Exploring integration possibilities

### Technology Evaluation

- New libraries or frameworks
- Alternative implementation approaches
- Performance optimization concepts

## Integration Testing

All experiments should test integration with:

- **Agent System**: Can agents be effectively utilized?
- **Workflow**: Does it fit with DEFAULT_WORKFLOW.md?
- **User Preferences**: Does it respect USER_PREFERENCES.md?
- **Philosophy**: Does it maintain ruthless simplicity?

## Naming Conventions

- **Descriptive**: Name clearly indicates what's being explored
- **Prefixes**: Use prefixes to indicate type:
  - `proto-`: Early prototype
  - `eval-`: Technology evaluation
  - `test-`: Pattern testing
  - `spike-`: Quick exploration

## Examples

```
ai_working/
├── proto-visual-debugger/
├── eval-typescript-integration/
├── test-parallel-agents/
└── spike-voice-commands/
```

## Success Metrics

- **Learning Rate**: Insights gained per experiment
- **Graduation Rate**: Successful moves to scenarios/
- **Time to Value**: Speed from idea to working prototype
- **Innovation Quality**: Uniqueness and value of concepts

---

_Remember: The goal is learning and validation, not perfection. Build fast, learn faster, graduate the best._
