# Example 4: Pattern Comparison

## Scenario

User is deciding between multiple design patterns and needs a structured comparison.

## User Query

```
User: "I need to create different types of database connections (MySQL, PostgreSQL, MongoDB). Should I use Factory Method or Abstract Factory?"
```

## Skill Response

## Pattern Comparison for Database Connections

You're trying to: **Create different types of database connections based on database type**

**Relevant Patterns**: Factory Method, Abstract Factory, Simple Factory Function

---

### Option 1: Factory Method

**Best when**: Each database type requires a different connection creation process, and you want subclasses to specify which connection to create.

**Pros**:

- Clean separation of connection creation logic per database type
- Easy to add new database types (Open/Closed Principle)
- Each creator class can have database-specific initialization logic

**Cons**:

- Requires creating a class for each database type
- More verbose than simple approaches
- Inheritance-based (less flexible than composition)

**Complexity**: Medium

**Code overhead**:

- 1 Creator base class (abstract)
- 1 ConcreteCreator per database type (3 classes)
- 1 Product interface
- 1 ConcreteProduct per database type (3 classes)
- **Total: ~8 classes**

**Example**:

```python
class ConnectionCreator(ABC):
    @abstractmethod
    def create_connection(self) -> Connection:
        pass

    def connect_and_query(self, query):
        conn = self.create_connection()
        return conn.execute(query)

class MySQLCreator(ConnectionCreator):
    def create_connection(self) -> Connection:
        return MySQLConnection()

class PostgreSQLCreator(ConnectionCreator):
    def create_connection(self) -> Connection:
        return PostgreSQLConnection()
```

---

### Option 2: Abstract Factory

**Best when**: You need to create **families** of related objects (e.g., Connection + QueryBuilder + Transaction for each database).

**Pros**:

- Ensures related objects are used together
- Good for products with multiple related components
- Complete abstraction of database-specific implementation

**Cons**:

- **OVERKILL if you only need connections** (not families)
- High complexity (more classes than Factory Method)
- Harder to add new product types (need to update all factories)

**Complexity**: High

**Code overhead**:

- 1 AbstractFactory interface
- 1 ConcreteFactory per database type (3 classes)
- 1 interface per product type (Connection, QueryBuilder, Transaction = 3 interfaces)
- 1 concrete product per database per type (3 databases × 3 products = 9 classes)
- **Total: ~16 classes**

**Example**:

```python
class DatabaseFactory(ABC):
    @abstractmethod
    def create_connection(self) -> Connection:
        pass

    @abstractmethod
    def create_query_builder(self) -> QueryBuilder:
        pass

    @abstractmethod
    def create_transaction(self) -> Transaction:
        pass

class MySQLFactory(DatabaseFactory):
    def create_connection(self):
        return MySQLConnection()

    def create_query_builder(self):
        return MySQLQueryBuilder()

    def create_transaction(self):
        return MySQLTransaction()
```

---

### Option 3: Simple Factory Function (Recommended)

**Best when**: You just need to create connections based on type, without needing subclassing flexibility.

**Pros**:

- **Simplest solution** (YAGNI principle)
- Easy to understand and maintain
- No inheritance hierarchy
- One place to add new database types

**Cons**:

- Less extensible (adding new types requires modifying function)
- No subclass customization points
- Violates Open/Closed if you add types frequently

**Complexity**: Low

**Code overhead**:

- 1 factory function
- 1 ConcreteProduct per database type (3 classes)
- **Total: ~4 classes**

**Example**:

```python
def create_connection(db_type: str, config: dict) -> Connection:
    """Simple factory function for database connections."""
    if db_type == "mysql":
        return MySQLConnection(config)
    elif db_type == "postgresql":
        return PostgreSQLConnection(config)
    elif db_type == "mongodb":
        return MongoDBConnection(config)
    else:
        raise ValueError(f"Unknown database type: {db_type}")

# Usage
conn = create_connection("mysql", {"host": "localhost", "port": 3306})
```

---

## Philosophy Check: Do You Need a Pattern?

### Questions to Ask:

1. **Do you need families of related objects?**
   - If YES (Connection + QueryBuilder + Transaction) → Consider Abstract Factory
   - If NO (just Connection) → Don't use Abstract Factory

2. **Do you need subclass customization of creation logic?**
   - If YES → Consider Factory Method
   - If NO → Use Simple Factory Function

3. **How often will you add new database types?**
   - Rarely (1-2 times per year) → Simple Factory Function
   - Frequently (plugin system) → Factory Method

4. **Is this for a library/framework or application code?**
   - Library/framework → Factory Method (extensibility matters)
   - Application code → Simple Factory Function (simplicity matters)

### Simpler Alternative

**For your specific use case** (creating database connections):

```python
class ConnectionFactory:
    """Simple factory class with registry pattern."""
    _creators = {}

    @classmethod
    def register(cls, db_type: str, creator: Callable):
        cls._creators[db_type] = creator

    @classmethod
    def create(cls, db_type: str, config: dict) -> Connection:
        creator = cls._creators.get(db_type)
        if not creator:
            raise ValueError(f"Unknown database type: {db_type}")
        return creator(config)

# Register creators
ConnectionFactory.register("mysql", MySQLConnection)
ConnectionFactory.register("postgresql", PostgreSQLConnection)
ConnectionFactory.register("mongodb", MongoDBConnection)

# Usage
conn = ConnectionFactory.create("mysql", config)
```

**Benefits**:

- Simple (1 class + registration)
- Extensible (register new types without modifying code)
- No inheritance needed
- Open/Closed compliant

---

## Recommendation

Based on your description **"create different types of database connections"**:

### Use Simple Factory Function or Registry Pattern

**Reasoning**:

1. You only mentioned creating connections (not families of related objects)
2. You have 3 concrete types (manageable without pattern complexity)
3. Connection creation is likely straightforward (no complex logic per type)
4. Application code benefits from simplicity over extensibility

### DON'T use Abstract Factory

- **Why**: You don't need families of related objects
- **Complexity**: 16 classes vs 4 classes
- **YAGNI**: You aren't gonna need the extra abstraction

### Consider Factory Method IF:

- You're building a database abstraction library (not application)
- Each database needs significantly different connection logic
- You expect users to add custom database types via subclassing

### Upgrade Path

**Start simple**:

1. Begin with factory function or registry pattern
2. Measure complexity and extensibility needs
3. Refactor to Factory Method IF you encounter pain points

**Don't prematurely use Factory Method "for future flexibility"**. Refactor to it when you actually need it.

---

## Next Steps

1. Implement Simple Factory Function or Registry Pattern
2. Test with your 3 database types
3. Monitor for pain points:
   - Hard to add new types? → Consider Factory Method
   - Need related object families? → Consider Abstract Factory
   - Neither? → Keep it simple!

**Would you like**:

- Code example of Registry Pattern for your use case?
- Implementation guide for Factory Method?
- Deep dive into when Abstract Factory is actually needed?
