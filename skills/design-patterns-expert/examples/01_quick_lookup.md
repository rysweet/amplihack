# Example 1: Quick Pattern Lookup

## Scenario

User wants a fast overview of a design pattern to understand its basic concept.

## User Query

```
User: "What is the Observer pattern?"
```

## Skill Response

**Observer (Behavioral)**

**Intent**: Define a one-to-many dependency between objects so that when one object changes state, all its dependents are notified and updated automatically.

**When to Use**:

- An abstraction has two aspects, one dependent on the other
- Change to one object requires changing others (number unknown)
- Object should notify other objects without knowing who they are

**Quick Example**:

```python
class Subject:
    def __init__(self):
        self.observers = []

    def attach(self, observer):
        self.observers.append(observer)

    def notify(self):
        for observer in self.observers:
            observer.update()
```

**Complexity Warning**: If you only have 1-2 observers or relationships are static, callbacks/direct calls are simpler. Observer excels with dynamic sets of dependents.

**Related Patterns**: Mediator (complex interactions), Singleton (subject often singleton)

**Deeper**: Request "Practical guide for Observer" (Tier 2) or "Deep dive into Observer" (Tier 3)
