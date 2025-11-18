# Gang of Four Design Patterns - Anti-Patterns and Common Mistakes

This file documents 10 common mistakes and anti-patterns when using design patterns.

---

## Anti-Pattern 1: Singleton Abuse (Global State Hell)

**Symptom**: Everything is a Singleton because "we only need one instance".

**Bad Example**:

```python
class DatabaseConnection(Singleton):
    """DON'T DO THIS"""
    pass

class Logger(Singleton):
    """DON'T DO THIS"""
    pass

class Config(Singleton):
    """DON'T DO THIS"""
    pass

class CacheManager(Singleton):
    """DON'T DO THIS"""
    pass

# Testing nightmare - can't mock, can't isolate
def test_user_service():
    service = UserService()  # Implicitly uses DatabaseConnection singleton
    # Can't inject mock database!
```

**Why It's Wrong**:

- Creates hidden dependencies (implicit coupling)
- Makes testing nearly impossible (can't mock/inject)
- Violates Single Responsibility (manages both creation and behavior)
- Global state causes race conditions in concurrent code
- Memory leaks (singletons never garbage collected)

**Correct Approach - Dependency Injection**:

```python
class UserService:
    """GOOD: Dependencies explicit and injectable"""

    def __init__(self, db: DatabaseConnection, logger: Logger, config: Config):
        self.db = db
        self.logger = logger
        self.config = config

    def create_user(self, username: str) -> User:
        self.logger.info(f"Creating user: {username}")
        # Use injected dependencies
        return self.db.insert(User(username))


# Easy to test - inject mocks
def test_user_service():
    mock_db = MockDatabase()
    mock_logger = MockLogger()
    mock_config = MockConfig()

    service = UserService(mock_db, mock_logger, mock_config)
    # Full control over dependencies!
```

**When Singleton IS Acceptable**:

- True hardware resources (printer spooler, device driver)
- Read-only configuration loaded once at startup
- Application-wide logging infrastructure (with careful design)
- **Criteria**: Must be genuinely global, immutable after init, and benefit from shared instance

---

## Anti-Pattern 2: Factory Overuse ("Just In Case" Factories)

**Symptom**: Every class has a factory "for future flexibility" even with only one implementation.

**Bad Example**:

```python
# DON'T DO THIS - Over-engineered for single use case

class UserFactory:
    """Factory for User... but we only have one User type"""

    def create_user(self, name: str, email: str) -> User:
        return User(name, email)  # Could just call User() directly!


class EmailFactory:
    """Factory for Email... but we only send one email type"""

    def create_email(self, to: str, subject: str, body: str) -> Email:
        return Email(to, subject, body)  # Just call Email()!


# Usage - pointless indirection
factory = UserFactory()
user = factory.create_user("Alice", "alice@example.com")

# VS direct (simpler, clearer)
user = User("Alice", "alice@example.com")
```

**Why It's Wrong**:

- YAGNI violation ("You Aren't Gonna Need It")
- Adds complexity with zero benefit
- Harder to understand (extra layer of indirection)
- More classes to maintain

**Correct Approach - Wait Until You Need It**:

```python
# Start simple
user = User("Alice", "alice@example.com")

# Add Factory ONLY when you have ≥2 implementations
# Example: NOW we have multiple user types

class UserFactory:
    """GOOD: Factory justified by multiple concrete types"""

    def create_user(self, user_type: str, **kwargs) -> User:
        if user_type == "admin":
            return AdminUser(**kwargs)
        elif user_type == "guest":
            return GuestUser(**kwargs)
        elif user_type == "premium":
            return PremiumUser(**kwargs)
        else:
            return RegularUser(**kwargs)
```

**When Factory IS Appropriate**:

- ≥2 concrete product types exist NOW (not "might exist")
- Object creation involves complex logic/configuration
- Need to decouple client from concrete classes
- Runtime type determination required

---

## Anti-Pattern 3: Pattern Stuffing (Using All Patterns)

**Symptom**: Project uses 10+ patterns in 1000 lines of code because "patterns are best practices".

**Bad Example**:

```python
# DON'T DO THIS - Pattern stuffing for simple to-do app

# Singleton + Factory + Builder + Observer + Strategy + Command
# ...for a simple CRUD app!

class TodoListSingleton(Singleton):
    """Unnecessary Singleton"""
    pass

class TodoFactory(AbstractFactory):
    """Unnecessary Factory"""
    def create_todo(self): pass
    def create_list(self): pass

class TodoBuilder:
    """Unnecessary Builder for simple object"""
    def __init__(self):
        self.todo = None

    def set_title(self, title): pass
    def set_due_date(self, date): pass
    def build(self): return self.todo

class TodoObserver(Observer):
    """Unnecessary Observer"""
    pass

# Just to create a single to-do item!
singleton = TodoListSingleton()
factory = TodoFactory()
builder = factory.create_builder()
todo = builder.set_title("Buy milk").set_due_date("2024-01-01").build()
```

**Why It's Wrong**:

- Over-engineering simple problems
- Code becomes unreadable (too many abstractions)
- Maintenance nightmare
- Poor onboarding (new devs overwhelmed)

**Correct Approach - Ruthless Simplicity**:

```python
# GOOD: Simple, direct, readable

@dataclass
class Todo:
    """Simple data class"""
    title: str
    due_date: Optional[datetime] = None
    completed: bool = False


class TodoList:
    """Simple class with clear responsibilities"""

    def __init__(self):
        self.todos: List[Todo] = []

    def add(self, todo: Todo) -> None:
        self.todos.append(todo)

    def complete(self, index: int) -> None:
        self.todos[index].completed = True

    def get_incomplete(self) -> List[Todo]:
        return [t for t in self.todos if not t.completed]


# Usage - clear and simple
todo_list = TodoList()
todo_list.add(Todo("Buy milk", datetime(2024, 1, 1)))
```

**Guideline**: Start with simplest solution. Add patterns ONLY when:

- Complexity justifies them
- ≥2 concrete use cases exist NOW
- Pattern reduces overall system complexity

---

## Anti-Pattern 4: Abstract Factory for Small Families

**Symptom**: Using Abstract Factory when you have only 1-2 products or 1-2 families.

**Bad Example**:

```python
# DON'T DO THIS - Abstract Factory for tiny product family

class GUIFactory(ABC):
    """Abstract Factory for... 1 product type?"""

    @abstractmethod
    def create_button(self) -> Button:
        pass


class WindowsFactory(GUIFactory):
    def create_button(self) -> Button:
        return WindowsButton()


class MacFactory(GUIFactory):
    def create_button(self) -> Button:
        return MacButton()


# Usage - overcomplicated for one product type
factory = WindowsFactory()
button = factory.create_button()  # Just call WindowsButton()!
```

**Why It's Wrong**:

- Abstract Factory justified only for ≥3 products AND ≥2 families
- Single product = use Factory Method instead
- Adds unnecessary abstraction layers

**Correct Approach - Use Simpler Pattern**:

```python
# GOOD: Factory Method for single product type

class ButtonFactory:
    """Factory Method sufficient for single product"""

    @staticmethod
    def create_button(platform: str) -> Button:
        if platform == "windows":
            return WindowsButton()
        elif platform == "mac":
            return MacButton()
        else:
            raise ValueError(f"Unknown platform: {platform}")


# Or even simpler - direct instantiation with parameter
class Button:
    def __init__(self, platform: str):
        self.platform = platform

    @classmethod
    def for_platform(cls, platform: str) -> 'Button':
        # Factory method built into class
        return cls(platform)
```

**Use Abstract Factory When**:

- ≥3 product types (Button, Checkbox, TextBox)
- ≥2 product families (Windows, Mac, Linux)
- Products must be used together (consistency enforced)

---

## Anti-Pattern 5: Observer With No Unsubscribe (Memory Leaks)

**Symptom**: Observers are attached but never detached, causing memory leaks.

**Bad Example**:

```python
# DON'T DO THIS - No detach mechanism

class EventPublisher:
    def __init__(self):
        self.subscribers = []

    def subscribe(self, observer):
        self.subscribers.append(observer)
        # Missing: unsubscribe method!

    def notify(self, event):
        for observer in self.subscribers:
            observer.update(event)


# Problem: Observers never garbage collected
class UIComponent:
    def __init__(self, publisher):
        publisher.subscribe(self)  # Component registered
        # When component destroyed, subscriber reference remains!

    def update(self, event):
        print(f"Got event: {event}")


# Memory leak: 1000 dead components still in subscribers list!
publisher = EventPublisher()
for i in range(1000):
    component = UIComponent(publisher)
    del component  # Destroyed, but subscriber reference remains!
```

**Why It's Wrong**:

- Memory leaks (observers never garbage collected)
- Performance degradation (notify iterates over dead observers)
- Unexpected behavior (dead observers may still receive notifications)

**Correct Approach - Proper Lifecycle Management**:

```python
# GOOD: Proper subscribe/unsubscribe with context manager

class EventPublisher:
    def __init__(self):
        self._subscribers: List[Observer] = []

    def subscribe(self, observer: Observer) -> None:
        if observer not in self._subscribers:
            self._subscribers.append(observer)

    def unsubscribe(self, observer: Observer) -> None:
        """IMPORTANT: Allow observers to unsubscribe"""
        if observer in self._subscribers:
            self._subscribers.remove(observer)

    def notify(self, event: Any) -> None:
        # Iterate over copy (allows unsubscribe during iteration)
        for observer in list(self._subscribers):
            observer.update(event)


class UIComponent:
    def __init__(self, publisher: EventPublisher):
        self.publisher = publisher
        self.publisher.subscribe(self)

    def update(self, event: Any) -> None:
        print(f"Got event: {event}")

    def cleanup(self) -> None:
        """IMPORTANT: Unsubscribe when component destroyed"""
        self.publisher.unsubscribe(self)

    def __del__(self):
        """Automatic cleanup on garbage collection"""
        self.cleanup()


# Even better: Context manager
from contextlib import contextmanager

@contextmanager
def subscribe_to(publisher: EventPublisher, observer: Observer):
    """Auto-unsubscribe when exiting context"""
    publisher.subscribe(observer)
    try:
        yield
    finally:
        publisher.unsubscribe(observer)


# Usage
with subscribe_to(publisher, component):
    # Component receives events
    pass
# Automatically unsubscribed
```

---

## Anti-Pattern 6: Visitor for Simple Operations

**Symptom**: Using complex Visitor pattern when simple polymorphism suffices.

**Bad Example**:

```python
# DON'T DO THIS - Visitor for simple operation

class Shape(ABC):
    @abstractmethod
    def accept(self, visitor):
        pass


class Circle(Shape):
    def accept(self, visitor):
        visitor.visit_circle(self)


class Square(Shape):
    def accept(self, visitor):
        visitor.visit_square(self)


class AreaVisitor:
    """Complex visitor for simple calculation!"""

    def visit_circle(self, circle):
        return 3.14 * circle.radius ** 2

    def visit_square(self, square):
        return square.side ** 2


# Usage - overcomplicated
circle = Circle()
visitor = AreaVisitor()
area = circle.accept(visitor)  # Why not circle.area()?
```

**Why It's Wrong**:

- Visitor is heavyweight (double dispatch complexity)
- Simple polymorphism is clearer
- Harder to understand and maintain
- Adds many classes for simple operations

**Correct Approach - Simple Polymorphism**:

```python
# GOOD: Simple polymorphism for simple operations

class Shape(ABC):
    @abstractmethod
    def area(self) -> float:
        """Simple polymorphic method"""
        pass


class Circle(Shape):
    def __init__(self, radius: float):
        self.radius = radius

    def area(self) -> float:
        return 3.14 * self.radius ** 2


class Square(Shape):
    def __init__(self, side: float):
        self.side = side

    def area(self) -> float:
        return self.side ** 2


# Usage - clear and simple
circle = Circle(5)
square = Square(4)

print(f"Circle area: {circle.area()}")
print(f"Square area: {square.area()}")
```

**Use Visitor When**:

- ≥5 different operations on stable structure
- Structure rarely changes, but operations change frequently
- Operations don't belong in element classes (violate SRP)

---

## Anti-Pattern 7: Deep Decorator Chains (Debugging Nightmare)

**Symptom**: Stacking 5+ decorators creating unreadable, unmaintainable code.

**Bad Example**:

```python
# DON'T DO THIS - Decorator chain hell

connection = LoggingDecorator(
    RetryDecorator(
        TimeoutDecorator(
            CacheDecorator(
                CompressionDecorator(
                    EncryptionDecorator(
                        AuthenticationDecorator(
                            RateLimitDecorator(
                                BaseConnection()
                            )
                        )
                    )
                )
            )
        )
    )
)

# What order do decorators execute?
# Which decorator is causing the bug?
# How to test individual decorators?
# Debugging nightmare!
```

**Why It's Wrong**:

- Hard to read (nested structure unclear)
- Difficult to debug (which decorator failed?)
- Inflexible (hard to reorder or remove decorators)
- Testing nightmare (can't test decorators in isolation)

**Correct Approach - Pipeline or Builder Pattern**:

```python
# GOOD: Pipeline pattern with explicit builder

class ConnectionBuilder:
    """Builder for creating decorated connections"""

    def __init__(self, connection: Connection):
        self._connection = connection
        self._decorators: List[str] = []

    def with_logging(self) -> 'ConnectionBuilder':
        self._connection = LoggingDecorator(self._connection)
        self._decorators.append("logging")
        return self

    def with_retry(self, max_attempts: int = 3) -> 'ConnectionBuilder':
        self._connection = RetryDecorator(self._connection, max_attempts)
        self._decorators.append("retry")
        return self

    def with_encryption(self) -> 'ConnectionBuilder':
        self._connection = EncryptionDecorator(self._connection)
        self._decorators.append("encryption")
        return self

    def build(self) -> Connection:
        print(f"Built connection with: {', '.join(self._decorators)}")
        return self._connection


# Usage - readable, testable, debuggable
connection = (
    ConnectionBuilder(BaseConnection())
    .with_logging()
    .with_retry(max_attempts=3)
    .with_encryption()
    .build()
)
```

**Guideline**:

- Limit decorator chains to 2-3 decorators
- Use builder pattern for complex configurations
- Consider alternatives (Strategy, middleware pipeline)

---

## Anti-Pattern 8: Command Without Undo (Missing Core Benefit)

**Symptom**: Implementing Command pattern but not supporting undo/redo.

**Bad Example**:

```python
# DON'T DO THIS - Command without undo = just callbacks!

class Command(ABC):
    @abstractmethod
    def execute(self):
        pass
    # Missing: undo() method!


class PrintCommand(Command):
    def __init__(self, message):
        self.message = message

    def execute(self):
        print(self.message)  # Can't undo print!


# This is just a callback - use functions instead!
def print_message(message):
    print(message)
```

**Why It's Wrong**:

- Command pattern's main benefit is undo/redo support
- Without undo, it's just callbacks with extra complexity
- Simple functions/lambdas are clearer

**Correct Approach - Either Support Undo or Use Callbacks**:

```python
# Option 1: GOOD - Command WITH undo support

class Command(ABC):
    @abstractmethod
    def execute(self):
        pass

    @abstractmethod
    def undo(self):
        """IMPORTANT: Support undo for Command pattern"""
        pass


class AddTextCommand(Command):
    def __init__(self, document, text, position):
        self.document = document
        self.text = text
        self.position = position

    def execute(self):
        self.document.insert(self.position, self.text)

    def undo(self):
        self.document.delete(self.position, len(self.text))


# Option 2: GOOD - Use simple callbacks when no undo needed

from typing import Callable

class Button:
    def __init__(self, on_click: Callable[[], None]):
        self.on_click = on_click

    def click(self):
        self.on_click()


# Usage - simpler than Command without undo
button = Button(lambda: print("Clicked!"))
button.click()
```

**Use Command When**:

- Need undo/redo functionality
- Need to queue/log/schedule operations
- Need macro commands (composite)
- **Don't Use**: For simple callbacks (use functions/lambdas)

---

## Anti-Pattern 9: State Machine for Simple Booleans

**Symptom**: Using State pattern when simple boolean flags suffice.

**Bad Example**:

```python
# DON'T DO THIS - State pattern for on/off

class State(ABC):
    @abstractmethod
    def toggle(self, light):
        pass


class OnState(State):
    def toggle(self, light):
        light.state = OffState()
        print("Light OFF")


class OffState(State):
    def toggle(self, light):
        light.state = OnState()
        print("Light ON")


class Light:
    def __init__(self):
        self.state = OffState()

    def toggle(self):
        self.state.toggle(self)


# Usage - overcomplicated for boolean!
light = Light()
light.toggle()  # Just use: light.is_on = not light.is_on
```

**Why It's Wrong**:

- State pattern overkill for 2-3 simple states
- Boolean/enum is clearer and simpler
- More classes to maintain for no benefit

**Correct Approach - Use Simple State Variables**:

```python
# GOOD: Simple boolean for simple cases

class Light:
    def __init__(self):
        self.is_on = False

    def toggle(self):
        self.is_on = not self.is_on
        print("Light ON" if self.is_on else "Light OFF")


# Usage - clear and simple
light = Light()
light.toggle()


# GOOD: Use State pattern for complex state machines (≥5 states)

from enum import Enum

class DocumentState(Enum):
    DRAFT = "draft"
    REVIEW = "review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class Document:
    """Complex state machine - State pattern justified"""

    def __init__(self):
        self.state = DocumentState.DRAFT

    def submit_for_review(self):
        if self.state == DocumentState.DRAFT:
            self.state = DocumentState.REVIEW
        else:
            raise ValueError(f"Can't review from {self.state}")

    def approve(self):
        if self.state == DocumentState.REVIEW:
            self.state = DocumentState.APPROVED
        else:
            raise ValueError(f"Can't approve from {self.state}")

    # Complex transitions justify State pattern
```

**Use State Pattern When**:

- ≥5 states with complex transitions
- State-specific behavior is substantial
- Need to enforce state transition rules
- **Don't Use**: For simple on/off or 2-3 state systems

---

## Anti-Pattern 10: Template Method With No Variance

**Symptom**: Template Method where all subclasses implement steps identically.

**Bad Example**:

```python
# DON'T DO THIS - Template Method with no variance

class DataProcessor(ABC):
    def process(self):
        self.load()
        self.transform()
        self.save()

    @abstractmethod
    def load(self): pass

    @abstractmethod
    def transform(self): pass

    @abstractmethod
    def save(self): pass


class JSONProcessor(DataProcessor):
    def load(self):
        return json.load()  # Same as others

    def transform(self):
        return data.upper()  # Same as others

    def save(self):
        return json.dump()  # Same as others


class XMLProcessor(DataProcessor):
    """Only difference is load/save format!"""
    def load(self):
        return xml.parse()  # Different

    def transform(self):
        return data.upper()  # SAME - shouldn't be overridden!

    def save(self):
        return xml.write()  # Different
```

**Why It's Wrong**:

- Template Method requires both invariant AND variant parts
- If everything varies: use Strategy instead
- If nothing varies: don't use pattern at all
- Forces override of methods that shouldn't vary

**Correct Approach - Strategy for Variable Algorithms**:

```python
# GOOD: Strategy pattern when algorithm varies

class DataProcessor:
    """Single class with strategy for variable parts"""

    def __init__(self, loader, saver):
        self.loader = loader
        self.saver = saver

    def process(self, input_path, output_path):
        # Load (variable)
        data = self.loader.load(input_path)

        # Transform (invariant - shared by all)
        transformed = data.upper()

        # Save (variable)
        self.saver.save(transformed, output_path)


# Strategies only for variable parts
class JSONLoader:
    def load(self, path):
        return json.load(open(path))


class XMLLoader:
    def load(self, path):
        return xml.parse(path)


# Usage - clearer separation of concerns
json_processor = DataProcessor(JSONLoader(), JSONSaver())
xml_processor = DataProcessor(XMLLoader(), XMLSaver())
```

**Use Template Method When**:

- Algorithm has BOTH invariant and variant parts
- Invariant parts substantial (≥3 fixed steps)
- Variant parts are minority (1-2 customization points)
- **Don't Use**: When everything varies (Strategy) or nothing varies (simple function)

---

## Summary of Guidelines

**Before using a pattern, ask:**

1. **Do I have ≥2 concrete use cases RIGHT NOW?** (not "might need later")
2. **Is there a simpler solution?** (functions, simple classes, composition)
3. **Does the pattern reduce overall complexity?** (or just add abstraction?)
4. **Will future me understand this?** (or be confused by overengineering?)

**Pattern Selection Checklist:**

- **Singleton**: Only for truly global, immutable resources (prefer DI)
- **Factory**: Only when ≥2 product types exist now
- **Abstract Factory**: Only when ≥3 products AND ≥2 families
- **Observer**: Only with dynamic observer set (≥2 observers)
- **Strategy**: Only with ≥3 swappable algorithms
- **Command**: Only when undo/redo/queuing needed
- **Visitor**: Only with ≥5 operations on stable structure
- **Decorator**: Limit to 2-3 decorators (use builder for more)
- **State**: Only with ≥5 states and complex transitions
- **Template Method**: Only with substantial invariant parts

**Remember**: Patterns are tools, not goals. The best code is often the simplest code that works.
