# Example 5: Philosophy Check (Over-Engineering Detection)

## Scenario

User is considering using a design pattern, and the skill needs to warn against potential over-engineering.

## User Query

```
User: "I'm building a small web app and thinking of using Singleton pattern for my database connection. Good idea?"
```

## Skill Response

## ⚠️ WARNING: Singleton Is Often a Code Smell

For database connections, **Singleton is almost always the wrong choice**. Let me explain why and suggest better alternatives.

---

### Why Singleton Is Problematic Here

**1. Global State Issues**

```python
# With Singleton - implicit global state
db = DatabaseConnection.get_instance()  # Where does this come from?
db.query(...)  # Hidden dependency!
```

- Hidden dependencies make code hard to understand
- Testing becomes difficult (can't easily mock)
- Violates Dependency Inversion Principle

**2. Testing Nightmares**

```python
def test_user_service():
    # How do you test this without hitting real database?
    service = UserService()
    service.create_user(...)  # Uses singleton DB - can't mock!
```

- Can't inject test double
- Tests hit real database (slow, fragile)
- Tests interfere with each other (shared state)

**3. Concurrency Problems**

```python
class DatabaseConnection:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance  # NOT thread-safe!
```

- Requires thread synchronization (complex)
- Performance bottleneck (single connection)
- Can't scale with connection pooling

**4. Violates Single Responsibility**

- Class manages both business logic AND instance lifecycle
- Harder to reason about and maintain

---

### Better Alternatives

#### Option 1: Dependency Injection (Recommended)

**Code**:

```python
class UserService:
    def __init__(self, db_connection):
        self.db = db_connection  # Explicit dependency!

    def create_user(self, name):
        self.db.query("INSERT INTO users ...")

# Application setup
db = DatabaseConnection(config)
user_service = UserService(db)
```

**Benefits**:

- ✅ Explicit dependencies (easy to understand)
- ✅ Easy to test (inject mock)
- ✅ Flexible (can inject different connections)
- ✅ No global state

**Testing**:

```python
def test_user_service():
    mock_db = MockDatabaseConnection()
    service = UserService(mock_db)
    service.create_user("John")
    assert mock_db.query_called
```

---

#### Option 2: Connection Pool (For Production)

**Code**:

```python
from contextlib import contextmanager

class ConnectionPool:
    def __init__(self, config, max_connections=10):
        self.pool = [DatabaseConnection(config)
                     for _ in range(max_connections)]

    @contextmanager
    def get_connection(self):
        conn = self.pool.pop()
        try:
            yield conn
        finally:
            self.pool.append(conn)  # Return to pool

# Usage
pool = ConnectionPool(config)

def create_user(pool, name):
    with pool.get_connection() as db:
        db.query("INSERT INTO users ...")
```

**Benefits**:

- ✅ Multiple connections (better concurrency)
- ✅ Resource management (connection reuse)
- ✅ Scalable (adjust pool size)
- ✅ Still testable (inject pool)

---

#### Option 3: Simple Module-Level Variable (For Small Apps)

**Code**:

```python
# db.py
_connection = None

def get_connection(config=None):
    global _connection
    if _connection is None:
        _connection = DatabaseConnection(config)
    return _connection

# Usage in application
from db import get_connection

db = get_connection(config)
db.query(...)
```

**Benefits**:

- ✅ Simple (no classes needed)
- ✅ Easy to understand
- ✅ Can be replaced in tests

**When to use**: Very small apps (< 500 lines), single-threaded, no testing needs

---

### When Singleton MIGHT Be OK

Singleton is appropriate only for:

**1. True Hardware Resources**

```python
class PrinterPort:  # Only one physical printer port
    ...
```

**2. Application-Wide Configuration (Read-Only)**

```python
class AppConfig:  # Immutable config loaded once at startup
    ...
```

**3. Logging Infrastructure**

```python
class Logger:  # Application-wide logging (but use logging library instead!)
    ...
```

**Note**: Even in these cases, modern alternatives (DI, service locator) are often better.

---

### For Your Web App Context

**Small web app characteristics**:

- Solo developer or small team
- Likely to evolve and grow
- Needs testing
- May need multiple environments (dev, test, prod)

**Recommendation: Use Dependency Injection**

**Why**:

1. **Now**: Simple to implement, clear dependencies
2. **Testing**: Easy to mock database
3. **Future**: Easy to add connection pooling later
4. **Growth**: Scales as app grows

**Example for Flask/FastAPI**:

```python
# app.py
from flask import Flask, g

app = Flask(__name__)

def get_db():
    if 'db' not in g:
        g.db = DatabaseConnection(app.config['DB_CONFIG'])
    return g.db

@app.route('/users', methods=['POST'])
def create_user():
    db = get_db()  # Request-scoped connection
    db.query(...)
```

Or with dependency injection framework:

```python
# Using dependency-injector library
from dependency_injector import containers, providers

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    db = providers.Singleton(DatabaseConnection, config.db)

container = Container()
db = container.db()
```

---

### Migration Path

**If you already have Singleton**:

```python
# Before (Singleton)
class Database:
    _instance = None
    @staticmethod
    def get_instance():
        if Database._instance is None:
            Database._instance = Database()
        return Database._instance

db = Database.get_instance()

# After (Dependency Injection)
class Database:
    def __init__(self, config):
        self.config = config

# Application setup
db = Database(config)
user_service = UserService(db)
```

---

## Summary

**DON'T use Singleton for database connection because**:

- Creates global state (hard to test, understand)
- Doesn't support connection pooling
- Violates Single Responsibility
- Over-engineering for no benefit

**DO use Dependency Injection instead**:

- Explicit dependencies
- Easy testing
- Flexible
- Simple to implement

**Alternative if you must have single connection**:

- Module-level variable (simpler than Singleton)
- Connection pool (better for production)

**Singleton is appropriate for**:

- True hardware resources (printer port)
- Immutable configuration
- Application-wide logging (though library is better)

---

**Would you like**:

- Code example of dependency injection for your framework (Flask/FastAPI/Django)?
- Deep dive into connection pooling?
- Comparison of Singleton vs dependency injection patterns?
