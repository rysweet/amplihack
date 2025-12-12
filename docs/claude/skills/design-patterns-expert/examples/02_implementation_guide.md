# Example 2: Implementation Guide

## Scenario

User needs practical guidance on how to implement a specific pattern with working code.

## User Query

```
User: "How to implement the Strategy pattern in Python?"
```

## Skill Response

**Strategy Pattern - Practical Guide**

### Structure

```
Context
  - strategy: Strategy
  + set_strategy(Strategy)
  + execute_strategy()

Strategy (interface)
  + execute(data)

ConcreteStrategyA : Strategy
  + execute(data)

ConcreteStrategyB : Strategy
  + execute(data)
```

### Implementation Steps

1. **Define Strategy interface**:

   ```python
   class Strategy:
       def execute(self, data):
           pass
   ```

2. **Create Concrete Strategies**:

   ```python
   class ConcreteStrategyA(Strategy):
       def execute(self, data):
           # Algorithm A implementation
           return sorted(data)

   class ConcreteStrategyB(Strategy):
       def execute(self, data):
           # Algorithm B implementation
           return reversed(data)
   ```

3. **Create Context that uses Strategy**:

   ```python
   class Context:
       def __init__(self, strategy: Strategy):
           self.strategy = strategy

       def set_strategy(self, strategy: Strategy):
           self.strategy = strategy

       def do_work(self, data):
           return self.strategy.execute(data)
   ```

### Code Example: Python

```python
from abc import ABC, abstractmethod

# Strategy interface
class SortStrategy(ABC):
    @abstractmethod
    def sort(self, data: list) -> list:
        pass

# Concrete strategies
class QuickSort(SortStrategy):
    def sort(self, data: list) -> list:
        if len(data) <= 1:
            return data
        pivot = data[len(data) // 2]
        left = [x for x in data if x < pivot]
        middle = [x for x in data if x == pivot]
        right = [x for x in data if x > pivot]
        return self.sort(left) + middle + self.sort(right)

class BubbleSort(SortStrategy):
    def sort(self, data: list) -> list:
        data = data.copy()
        n = len(data)
        for i in range(n):
            for j in range(0, n - i - 1):
                if data[j] > data[j + 1]:
                    data[j], data[j + 1] = data[j + 1], data[j]
        return data

# Context
class Sorter:
    def __init__(self, strategy: SortStrategy):
        self.strategy = strategy

    def set_strategy(self, strategy: SortStrategy):
        self.strategy = strategy

    def sort_data(self, data: list) -> list:
        print(f"Using {self.strategy.__class__.__name__}")
        return self.strategy.sort(data)

# Usage
if __name__ == "__main__":
    data = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3]

    # Use QuickSort strategy
    sorter = Sorter(QuickSort())
    print(sorter.sort_data(data))  # [1, 1, 2, 3, 3, 4, 5, 5, 6, 9]

    # Switch to BubbleSort strategy at runtime
    sorter.set_strategy(BubbleSort())
    print(sorter.sort_data(data))  # [1, 1, 2, 3, 3, 4, 5, 5, 6, 9]
```

### Real-World Use Cases

- **Payment Processing**: Different payment methods (CreditCard, PayPal, Crypto)
- **Data Validation**: Different validation rules (Email, Phone, SSN)
- **Compression**: Different algorithms (ZIP, RAR, GZIP)
- **Navigation**: Different route-finding algorithms (shortest, fastest, scenic)

### Common Pitfalls

- **Too few strategies**: If you have only 1-2 simple algorithms, Strategy over-engineers. Use function parameters instead.
  - ❌ Bad: Creating Strategy classes for trivial logic
  - ✅ Good: Use simple function parameters or lambda functions

- **Confusing with State**: Strategy changes algorithm; State changes behavior based on internal state.

- **Over-abstraction**: Don't create strategy hierarchies unless necessary. Keep it simple.

### When NOT to Use

- **Simple algorithms**: If algorithms are 1-2 lines, use function parameters
- **Fixed algorithms**: If algorithm never changes at runtime, Strategy over-engineers
- **Prototype context**: If requirements are unstable, Strategy adds premature structure

### Trade-offs

| Benefit                                  | Cost                                         |
| ---------------------------------------- | -------------------------------------------- |
| Easy to add new algorithms (Open/Closed) | Extra classes to maintain                    |
| Swap algorithms at runtime               | More objects in memory                       |
| Isolate algorithm implementation details | Indirection makes code less obvious          |
| Eliminate conditional statements         | Clients must understand different strategies |

**Philosophy Check**: ✅ Good fit when you have ≥3 complex algorithms that vary at runtime. ⚠️ Over-engineering if used for simple function logic.

**Go Deeper**: Request "Deep dive into Strategy" for TypeScript/Java implementations, variations, and advanced topics.
