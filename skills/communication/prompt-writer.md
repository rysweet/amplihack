---
skill:
  name: prompt-writer
  description: Effective AI prompt engineering
---

# Prompt Engineering

## Prompt Patterns

### Role + Task + Format
```
You are an expert [role].
[Task description]
Format your response as [format].
```

### Few-Shot
```
Example 1: [input] → [output]
Example 2: [input] → [output]
Now do: [new input]
```

### Chain of Thought
```
Think through this step by step:
1. First, consider...
2. Then, analyze...
3. Finally, conclude...
```

## Anti-Patterns
- Vague instructions ("make it better")
- Conflicting constraints
- Missing context
- Overly complex single prompts
