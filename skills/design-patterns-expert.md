# Design Patterns Expert

Domain knowledge for selecting and applying appropriate design patterns while maintaining simplicity.

## When to Use

- Architectural decisions
- Solving recurring design problems
- Code structure review
- Keywords: "pattern", "architecture", "structure", "design"

## Pattern Selection Philosophy

**WARNING**: Patterns are tools, not goals. Only apply when:
1. Problem is recurring and well-understood
2. Pattern simplifies (not complicates) the solution
3. Team recognizes the pattern
4. Benefits outweigh indirection cost

## Essential Patterns (Use Frequently)

### Strategy Pattern
**Problem**: Need interchangeable algorithms
**Solution**: Extract algorithm to interface, inject implementations
```python
# Before: Switch statement
def process(type, data):
    if type == "json": ...
    elif type == "xml": ...

# After: Strategy
class Processor(Protocol):
    def process(self, data): ...

def process(processor: Processor, data):
    return processor.process(data)
```
**When**: Multiple algorithms for same task

### Factory Pattern
**Problem**: Complex object creation logic
**Solution**: Encapsulate creation in factory function/class
```python
def create_connection(config: Config) -> Connection:
    if config.type == "postgres":
        return PostgresConnection(config.url)
    elif config.type == "sqlite":
        return SqliteConnection(config.path)
```
**When**: Creation logic is complex or varies

### Decorator Pattern
**Problem**: Add behavior without modifying original
**Solution**: Wrap object with enhanced version
```python
@retry(max_attempts=3)
@log_calls
def fetch_data(url: str) -> dict: ...
```
**When**: Cross-cutting concerns, optional features

### Observer Pattern
**Problem**: React to state changes without coupling
**Solution**: Publish events, subscribers react independently
```python
class EventEmitter:
    def emit(self, event: str, data: Any): ...
    def on(self, event: str, handler: Callable): ...
```
**When**: Decoupled notification needed

## Useful Patterns (Use When Needed)

### Repository Pattern
**Problem**: Data access logic scattered
**Solution**: Centralize data operations
**When**: Complex data access, testing important

### Adapter Pattern
**Problem**: Interface mismatch
**Solution**: Wrapper that translates interfaces
**When**: Integrating third-party libraries

### Command Pattern
**Problem**: Need undo/redo, queuing, or logging of operations
**Solution**: Encapsulate operations as objects
**When**: Operation history needed

### Template Method
**Problem**: Algorithm with varying steps
**Solution**: Define skeleton, subclasses fill steps
**When**: Shared structure, varying implementation

## Patterns to Avoid (Usually Overkill)

| Pattern | Problem | Simpler Alternative |
|---------|---------|---------------------|
| **Singleton** | Global state, testing nightmare | Dependency injection |
| **Abstract Factory** | Too much indirection | Simple factory function |
| **Visitor** | Complex, rarely needed | Pattern matching / if-else |
| **Bridge** | Over-engineering | Direct implementation |

## Pattern Detection Checklist

```markdown
## Pattern Review: [component]

### Current Patterns Used
- [ ] List identified patterns
- [ ] Justify each pattern's presence

### Potential Pattern Opportunities
- [ ] Repeated switch statements → Strategy?
- [ ] Complex object creation → Factory?
- [ ] Cross-cutting concerns → Decorator?
- [ ] State change reactions → Observer?

### Anti-Pattern Check
- [ ] No premature abstraction
- [ ] No pattern for pattern's sake
- [ ] Complexity justified by benefit
```

## Philosophy Alignment

Patterns should support amplihack philosophy:
- **Ruthless Simplicity**: Pattern must simplify, not complicate
- **Brick Philosophy**: Patterns define clear interfaces (studs)
- **Regeneratable**: Well-known patterns are easier to regenerate
