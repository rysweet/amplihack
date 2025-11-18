# Gang of Four Design Patterns - Complete Reference

This reference contains detailed specifications for all 23 Gang of Four design patterns.

## Sources

- **Design Patterns: Elements of Reusable Object-Oriented Software** (1994) - Gamma, Helm, Johnson, Vlissides (Gang of Four)
- **Refactoring Guru** - https://refactoring.guru/design-patterns
- **Source Making** - https://sourcemaking.com/design_patterns
- **Game Programming Patterns** - https://gameprogrammingpatterns.com
- **Python Patterns Guide** - https://python-patterns.guide
- **GitHub python-patterns** - https://github.com/faif/python-patterns

---

## Using This Skill

### Progressive Disclosure Protocol

**Three-Tier System**

**Tier 1: Quick Reference** (always inline, instant)

- One-sentence intent
- When to use (2-3 bullets)
- Quick pseudocode example (3-5 lines)
- Complexity warning
- Related patterns

**Tier 2: Practical Guide** (generated on request or from examples.md)

- Structure diagram
- Implementation steps
- Complete code example (Python, 20-40 lines)
- Real-world use cases
- Common pitfalls
- When NOT to use

**Tier 3: Deep Dive** (from reference-patterns.md)

- Full structure explanation
- Complete pattern specification
- Problem/Solution/Consequences
- Pattern variations
- Advanced topics
- Philosophy alignment check
- Authoritative references

**Tier Detection Algorithm**

I automatically detect desired depth from:

**Tier 3 Signals**:

- "detailed explanation", "deep dive", "comprehensive"
- "all details", "thorough", "trade-offs"
- "when not to use", "alternatives", "variations"
- "implementation details", "show me the full"

**Tier 2 Signals**:

- "code example", "how to implement", "show me how"
- "practical", "use case", "real-world"
- "step by step", "guide"

**Tier 1 Signals** (default):

- "what is", "quick summary", "briefly", "overview"
- "which pattern", "compare"

**Default**: Start with Tier 1, offer to go deeper.

### Philosophy Check Protocol

For EVERY pattern recommendation, I apply this filter:

1. **Is there a simpler solution?**
   - Could plain functions solve this?
   - Would a single class be sufficient?
   - Is this premature abstraction?

2. **Is complexity justified?**
   - Do you have ≥2 actual use cases NOW?
   - Are requirements likely to change?
   - Will this pattern reduce future complexity?

3. **Will this be regeneratable?**
   - Is the pattern well-understood?
   - Can it be rebuilt from spec?
   - Is it a "brick" (self-contained module)?

### Pattern Recognition Engine

**Query to Pattern Mapping**

When you describe a problem, I match against these triggers:

| User Says...                                     | Consider Pattern                 | Why                                                  |
| ------------------------------------------------ | -------------------------------- | ---------------------------------------------------- |
| "need different ways to create..."               | Factory Method, Abstract Factory | Object creation flexibility                          |
| "create complex object step by step"             | Builder                          | Separate construction from representation            |
| "expensive to create, want to clone"             | Prototype                        | Copy existing objects                                |
| "only one instance needed"                       | Singleton                        | Controlled single instance (often overused)          |
| "incompatible interfaces"                        | Adapter                          | Make incompatible interfaces work together           |
| "separate abstraction from implementation"       | Bridge                           | Vary abstraction and implementation independently    |
| "treat individual and groups uniformly"          | Composite                        | Tree structures, recursive composition               |
| "add responsibilities dynamically"               | Decorator                        | Flexible alternative to subclassing                  |
| "simplify complex subsystem"                     | Facade                           | Unified interface to subsystems                      |
| "many similar objects, memory concern"           | Flyweight                        | Share common state across many objects               |
| "control access to object"                       | Proxy                            | Add level of indirection (lazy init, access control) |
| "pass request along chain"                       | Chain of Responsibility          | Decouple sender from receiver                        |
| "encapsulate request as object"                  | Command                          | Parameterize, queue, log operations                  |
| "traverse collection without exposing structure" | Iterator                         | Sequential access without exposing internals         |
| "decouple objects that interact"                 | Mediator                         | Centralize complex communications                    |
| "capture/restore object state"                   | Memento                          | Undo mechanism, snapshots                            |
| "notify multiple objects of changes"             | Observer                         | One-to-many dependency, event handling               |
| "object behavior changes with state"             | State                            | State-specific behavior without conditionals         |
| "swap algorithms at runtime"                     | Strategy                         | Encapsulate algorithm families                       |
| "define algorithm skeleton, defer steps"         | Template Method                  | Invariant parts in superclass                        |
| "operations on object structure"                 | Visitor                          | Add operations without changing classes              |
| "parse/interpret language"                       | Interpreter                      | Grammar-based language processing                    |

**Automatic Philosophy Warnings**

I automatically warn when:

- **Singleton requested**: "Singleton is often a code smell. Consider dependency injection instead."
- **Abstract Factory with <3 product families**: "You might not need Abstract Factory yet. Start with Factory Method."
- **Visitor for <3 operations**: "Visitor adds significant complexity. Could you use simple polymorphism?"
- **Any pattern for prototype/MVP**: "Patterns add structure for change. If requirements are unstable, stay simple."
- **Pattern for one-time use**: "Patterns are for recurring problems. Is this actually recurring?"

### Decision Framework

**Creational Patterns Decision Tree**

```
Need to create objects?
├─ Single product type?
│  ├─ Simple creation? → Direct instantiation
│  └─ Complex creation? → Factory Method
├─ Multiple product types?
│  ├─ Products independent? → Factory Method
│  └─ Products must work together (families)? → Abstract Factory
├─ Many constructor parameters (≥5)?
│  └─ Step-by-step construction? → Builder
├─ Expensive to create?
│  └─ Want to clone? → Prototype
└─ Need exactly one instance?
   └─ Truly global resource? → Singleton (prefer DI)
```

**Structural Patterns Decision Tree**

```
Need to modify structure?
├─ Incompatible interfaces?
│  └─ Wrap external class? → Adapter
├─ Separate interface from implementation?
│  └─ Both vary independently? → Bridge
├─ Part-whole hierarchy?
│  └─ Treat leaves/composites uniformly? → Composite
├─ Add responsibilities dynamically?
│  ├─ Multiple combinable features? → Decorator
│  └─ Single added layer? → Simple subclass
├─ Simplify complex subsystem?
│  └─ Unified interface? → Facade
├─ Many similar objects?
│  └─ Memory pressure? → Flyweight
└─ Control access to object?
   └─ Lazy init, access control, remote? → Proxy
```

**Behavioral Patterns Decision Tree**

```
Need to manage behavior/algorithms?
├─ Multiple handlers for request?
│  └─ Don't know which handles? → Chain of Responsibility
├─ Encapsulate request as object?
│  └─ Undo/redo/queue needed? → Command
├─ Traverse collection?
│  └─ Hide internal structure? → Iterator (or use built-in)
├─ Complex object interactions?
│  └─ Centralize communication? → Mediator
├─ Save/restore object state?
│  └─ Undo mechanism? → Memento
├─ Notify multiple dependents?
│  └─ One-to-many broadcast? → Observer
├─ Behavior depends on state?
│  ├─ Complex state machine (≥5 states)? → State
│  └─ Simple (2-3 states)? → Boolean/enum
├─ Swap algorithms at runtime?
│  └─ Multiple strategies (≥3)? → Strategy
├─ Algorithm with invariant/variant parts?
│  └─ Substantial shared code? → Template Method
├─ Many operations on structure?
│  └─ Structure stable, operations change? → Visitor
└─ Interpret simple language?
   └─ Grammar simple? → Interpreter (or use parser library)
```

### Response Protocol

**For Pattern Lookups**

1. Detect desired tier from query
2. Provide requested tier content
3. Include philosophy warning if applicable
4. Offer to go deeper

**For Pattern Recognition**

1. Understand user's problem
2. Map to relevant patterns (1-3 patterns)
3. If multiple patterns apply, provide comparison
4. Always include "Do you need a pattern?" section
5. Give clear recommendation with justification

**For Philosophy Checks**

1. Acknowledge pattern choice
2. Evaluate against ruthless simplicity
3. Provide warnings if over-engineering detected
4. Suggest simpler alternatives
5. Give conditional approval if pattern is justified

### Integration with Amplihack Agents

**With Architect Agent**

When architect designs systems, I provide:

- Pattern suggestions based on requirements
- Trade-off analysis for pattern choices
- Warnings against over-engineering
- Philosophy-aligned recommendations

**With Builder Agent**

When builder implements code, I provide:

- Code templates and examples (from examples.md)
- Implementation guidance
- Language-specific best practices
- Testing strategies

**With Reviewer Agent**

When reviewer checks code, I provide:

- Pattern identification
- Appropriate usage validation
- Over-engineering detection (from antipatterns.md)
- Simplification suggestions

---

## Creational Patterns

Patterns that deal with object creation mechanisms, trying to create objects in a manner suitable to the situation.

### Factory Method

**Intent**: Define an interface for creating objects, but let subclasses decide which class to instantiate.

**Problem**: You need to create objects without specifying the exact class to instantiate, allowing flexibility in which concrete class is used.

**Solution**: Define a factory method in a base class that returns an object of a product interface. Subclasses override this method to return specific product implementations.

**Structure**:

- **Product**: Interface for objects the factory method creates
- **ConcreteProduct**: Implements the Product interface
- **Creator**: Declares the factory method returning Product
- **ConcreteCreator**: Overrides factory method to return ConcreteProduct

**Consequences**:

- **Pros**:
  - Eliminates need to bind application-specific classes into code
  - Provides hooks for subclasses to extend
  - Connects parallel class hierarchies
- **Cons**:
  - Requires subclassing just to create particular product
  - Can lead to large number of similar classes

**References**:

- GoF Book: Pages 107-116
- Refactoring Guru: https://refactoring.guru/design-patterns/factory-method
- Python Patterns: https://python-patterns.guide/gang-of-four/factory-method/

---

### Abstract Factory

**Intent**: Provide an interface for creating families of related or dependent objects without specifying their concrete classes.

**Problem**: You need to create multiple related objects that must be used together (a family), and you want to enforce this consistency.

**Solution**: Define an abstract factory interface with methods for creating each type of product. Concrete factories implement this interface to create product families.

**Structure**:

- **AbstractFactory**: Interface for creating abstract products
- **ConcreteFactory**: Implements operations to create concrete products
- **AbstractProduct**: Interface for a type of product
- **ConcreteProduct**: Product object created by corresponding concrete factory
- **Client**: Uses only AbstractFactory and AbstractProduct interfaces

**Consequences**:

- **Pros**:
  - Isolates concrete classes
  - Makes exchanging product families easy
  - Promotes consistency among products
- **Cons**:
  - Supporting new kinds of products is difficult
  - Increases number of classes

**References**:

- GoF Book: Pages 87-95
- Refactoring Guru: https://refactoring.guru/design-patterns/abstract-factory
- Source Making: https://sourcemaking.com/design_patterns/abstract_factory

---

### Builder

**Intent**: Separate the construction of a complex object from its representation, allowing the same construction process to create different representations.

**Problem**: You need to construct a complex object step by step, and the construction process must allow different representations.

**Solution**: Define a Builder interface with methods for creating parts of a product. Director class uses Builder to construct objects. ConcreteBuilders implement the Builder interface.

**Structure**:

- **Builder**: Interface for creating parts of Product
- **ConcreteBuilder**: Constructs and assembles parts, defines representation
- **Director**: Constructs object using Builder interface
- **Product**: Complex object being built

**Consequences**:

- **Pros**:
  - Lets you vary product's internal representation
  - Isolates code for construction and representation
  - Gives finer control over construction process
- **Cons**:
  - Requires creating separate ConcreteBuilder for each type of product
  - Builder classes must be mutable
  - May increase overall code complexity

**References**:

- GoF Book: Pages 97-106
- Refactoring Guru: https://refactoring.guru/design-patterns/builder
- Python Patterns: https://python-patterns.guide/gang-of-four/builder/

---

### Prototype

**Intent**: Specify the kinds of objects to create using a prototypical instance, and create new objects by copying this prototype.

**Problem**: Creating objects is expensive (database queries, complex initialization), or you want to avoid subclassing just to create objects.

**Solution**: Create new objects by cloning a prototypical instance. Prototype interface declares a cloning method.

**Structure**:

- **Prototype**: Interface declaring clone method
- **ConcretePrototype**: Implements clone method
- **Client**: Creates new objects by asking prototype to clone itself

**Consequences**:

- **Pros**:
  - Adds/removes products at runtime
  - Specifies new objects by varying values
  - Reduces subclassing
  - Configures application with classes dynamically
- **Cons**:
  - Cloning complex objects with circular references is difficult
  - Deep vs shallow copy decisions required

**References**:

- GoF Book: Pages 117-126
- Refactoring Guru: https://refactoring.guru/design-patterns/prototype
- GitHub python-patterns: https://github.com/faif/python-patterns/blob/master/patterns/creational/prototype.py

---

### Singleton

**Intent**: Ensure a class has only one instance and provide a global point of access to it.

**Problem**: You need exactly one instance of a class (single resource, coordination point), and that instance must be accessible globally.

**Solution**: Make the class responsible for keeping track of its sole instance. Class can ensure no other instance can be created (intercept requests for creating new objects).

**Structure**:

- **Singleton**: Defines Instance operation letting clients access unique instance; may be responsible for creating own unique instance

**Consequences**:

- **Pros**:
  - Controlled access to sole instance
  - Reduced namespace pollution
  - Permits refinement of operations and representation
  - Permits variable number of instances (if needed)
- **Cons**:
  - Violates Single Responsibility Principle (controls both creation and behavior)
  - Makes unit testing difficult (global state)
  - Requires special treatment in multithreaded environments
  - Can mask bad design (components know too much about each other)

**WARNING**: Singleton is often overused and considered an anti-pattern in modern development. Prefer dependency injection for most use cases.

**References**:

- GoF Book: Pages 127-134
- Refactoring Guru: https://refactoring.guru/design-patterns/singleton
- Source Making: https://sourcemaking.com/design_patterns/singleton (includes criticism)

---

## Structural Patterns

Patterns concerned with how classes and objects are composed to form larger structures.

### Adapter

**Intent**: Convert the interface of a class into another interface clients expect. Lets classes work together that couldn't otherwise because of incompatible interfaces.

**Problem**: You want to use an existing class, but its interface doesn't match what you need.

**Solution**: Define an adapter class that wraps the existing class and implements the interface clients expect.

**Structure**:

- **Target**: Interface that Client uses
- **Adapter**: Adapts interface of Adaptee to Target interface
- **Adaptee**: Existing interface that needs adapting
- **Client**: Collaborates with objects conforming to Target

**Consequences**:

- **Pros**:
  - Allows incompatible interfaces to work together
  - Increases class reusability
  - Introduces only one object (adapter)
- **Cons**:
  - Increases overall complexity
  - Sometimes requires many adaptations along adapter chain

**References**:

- GoF Book: Pages 139-150
- Refactoring Guru: https://refactoring.guru/design-patterns/adapter
- Python Patterns: https://python-patterns.guide/gang-of-four/adapter/

---

### Bridge

**Intent**: Decouple an abstraction from its implementation so that the two can vary independently.

**Problem**: You want to avoid a permanent binding between an abstraction and its implementation, especially when both should be extensible by subclassing.

**Solution**: Separate abstraction and implementation into separate class hierarchies. Abstraction contains a reference to implementation object.

**Structure**:

- **Abstraction**: Defines abstraction's interface; maintains reference to Implementor
- **RefinedAbstraction**: Extends interface defined by Abstraction
- **Implementor**: Interface for implementation classes
- **ConcreteImplementor**: Implements Implementor interface

**Consequences**:

- **Pros**:
  - Decouples interface and implementation
  - Improves extensibility
  - Hides implementation details from clients
- **Cons**:
  - Increases complexity
  - May impact performance (extra indirection)

**References**:

- GoF Book: Pages 151-161
- Refactoring Guru: https://refactoring.guru/design-patterns/bridge
- Source Making: https://sourcemaking.com/design_patterns/bridge

---

### Composite

**Intent**: Compose objects into tree structures to represent part-whole hierarchies. Lets clients treat individual objects and compositions uniformly.

**Problem**: You want to represent part-whole hierarchies of objects and treat individual objects and compositions uniformly.

**Solution**: Define a Component interface for both primitives and composites. Composite stores child components and implements operations by delegating to children.

**Structure**:

- **Component**: Interface for objects in composition
- **Leaf**: Represents leaf objects (no children)
- **Composite**: Defines behavior for components having children; stores child components
- **Client**: Manipulates objects through Component interface

**Consequences**:

- **Pros**:
  - Makes client simple (treats composites and leaves uniformly)
  - Makes it easy to add new kinds of components
  - Defines class hierarchies of primitive and composite objects
- **Cons**:
  - Can make design overly general
  - Hard to restrict composite components

**References**:

- GoF Book: Pages 163-173
- Refactoring Guru: https://refactoring.guru/design-patterns/composite
- Game Programming Patterns: https://gameprogrammingpatterns.com/component.html

---

### Decorator

**Intent**: Attach additional responsibilities to an object dynamically. Provides flexible alternative to subclassing for extending functionality.

**Problem**: You need to add responsibilities to individual objects dynamically and transparently, without affecting other objects.

**Solution**: Enclose the component in a decorator object. Decorator conforms to the interface of the component it decorates, forwarding requests and potentially performing additional actions.

**Structure**:

- **Component**: Interface for objects that can have responsibilities added
- **ConcreteComponent**: Object to which additional responsibilities can be attached
- **Decorator**: Maintains reference to Component and conforms to Component interface
- **ConcreteDecorator**: Adds responsibilities to component

**Consequences**:

- **Pros**:
  - More flexible than static inheritance
  - Avoids feature-laden classes high in hierarchy
  - Can add/remove responsibilities at runtime
- **Cons**:
  - Can result in many small objects
  - Decorator and component aren't identical (type checking issues)
  - Complex configurations can be hard to debug

**References**:

- GoF Book: Pages 175-184
- Refactoring Guru: https://refactoring.guru/design-patterns/decorator
- Python Patterns: https://python-patterns.guide/gang-of-four/decorator-pattern/

---

### Facade

**Intent**: Provide a unified interface to a set of interfaces in a subsystem. Defines higher-level interface that makes the subsystem easier to use.

**Problem**: You want to provide a simple interface to a complex subsystem with many interdependent classes.

**Solution**: Define a Facade class that provides simple methods required by client, delegating to appropriate subsystem objects.

**Structure**:

- **Facade**: Knows which subsystem classes are responsible for a request; delegates client requests to appropriate subsystem objects
- **Subsystem classes**: Implement subsystem functionality; handle work assigned by Facade; have no knowledge of Facade

**Consequences**:

- **Pros**:
  - Shields clients from subsystem components
  - Promotes weak coupling between subsystem and clients
  - Reduces compilation dependencies
- **Cons**:
  - Can become a god object coupled to all classes
  - May not provide all functionality clients need

**References**:

- GoF Book: Pages 185-193
- Refactoring Guru: https://refactoring.guru/design-patterns/facade
- Source Making: https://sourcemaking.com/design_patterns/facade

---

### Flyweight

**Intent**: Use sharing to support large numbers of fine-grained objects efficiently.

**Problem**: Your application uses a large number of objects that consume substantial memory, and many objects share common state.

**Solution**: Share common parts of state between multiple objects instead of keeping all data in each object. Separate intrinsic (shared) state from extrinsic (unique) state.

**Structure**:

- **Flyweight**: Interface through which flyweights can receive and act on extrinsic state
- **ConcreteFlyweight**: Implements Flyweight interface; stores intrinsic state
- **FlyweightFactory**: Creates and manages flyweight objects; ensures proper sharing
- **Client**: Maintains reference to flyweights; computes/stores extrinsic state

**Consequences**:

- **Pros**:
  - Reduces number of objects
  - Reduces memory consumption
  - Reduces overhead of managing objects
- **Cons**:
  - Introduces run-time costs (computing/transferring extrinsic state)
  - Makes code more complicated
  - Only beneficial when memory savings are significant

**References**:

- GoF Book: Pages 195-206
- Refactoring Guru: https://refactoring.guru/design-patterns/flyweight
- Game Programming Patterns: https://gameprogrammingpatterns.com/flyweight.html

---

### Proxy

**Intent**: Provide a surrogate or placeholder for another object to control access to it.

**Problem**: You need a more versatile or sophisticated reference to an object than a simple pointer (lazy initialization, access control, remote access).

**Solution**: Provide a proxy object that acts as substitute for the real object. Proxy has same interface as the real object.

**Structure**:

- **Subject**: Common interface for RealSubject and Proxy
- **RealSubject**: Real object that proxy represents
- **Proxy**: Maintains reference to RealSubject; controls access; may be responsible for creating/deleting RealSubject

**Proxy Types**:

- **Virtual Proxy**: Delays creation of expensive objects until needed
- **Protection Proxy**: Controls access based on access rights
- **Remote Proxy**: Provides local representative for remote object
- **Smart Proxy**: Performs additional actions (reference counting, locking, loading persistent object)

**Consequences**:

- **Pros**:
  - Controls access to real object
  - Can optimize performance (lazy initialization, caching)
  - Provides level of indirection for various purposes
- **Cons**:
  - May introduce additional latency
  - Increases code complexity

**References**:

- GoF Book: Pages 207-217
- Refactoring Guru: https://refactoring.guru/design-patterns/proxy
- Python Patterns: https://python-patterns.guide/gang-of-four/proxy/

---

## Behavioral Patterns

Patterns concerned with algorithms and the assignment of responsibilities between objects.

### Chain of Responsibility

**Intent**: Avoid coupling sender of request to receiver by giving more than one object a chance to handle request. Chain receiving objects and pass request along until object handles it.

**Problem**: You want to decouple sender and receiver, allowing multiple objects to handle a request without sender knowing which object will handle it.

**Solution**: Each handler in chain either handles the request or forwards it to next handler in chain.

**Structure**:

- **Handler**: Interface for handling requests; implements successor link
- **ConcreteHandler**: Handles requests it's responsible for; forwards others to successor
- **Client**: Initiates request to ConcreteHandler in chain

**Consequences**:

- **Pros**:
  - Reduces coupling
  - Adds flexibility in assigning responsibilities
  - Allows dynamic chain modification
- **Cons**:
  - Receipt isn't guaranteed
  - Can be hard to observe/debug runtime characteristics
  - May impact performance (chain traversal)

**References**:

- GoF Book: Pages 223-232
- Refactoring Guru: https://refactoring.guru/design-patterns/chain-of-responsibility
- Source Making: https://sourcemaking.com/design_patterns/chain_of_responsibility

---

### Command

**Intent**: Encapsulate a request as an object, letting you parameterize clients with different requests, queue or log requests, and support undoable operations.

**Problem**: You need to parameterize objects with actions to perform, specify/queue/execute requests at different times, or support undo.

**Solution**: Encapsulate request as object with all information needed to execute it. Command objects can be stored, passed as parameters, and invoked when needed.

**Structure**:

- **Command**: Interface for executing operations
- **ConcreteCommand**: Binds Receiver with action; implements execute by invoking operations on Receiver
- **Client**: Creates ConcreteCommand and sets its Receiver
- **Invoker**: Asks command to carry out request
- **Receiver**: Knows how to perform operations

**Consequences**:

- **Pros**:
  - Decouples object invoking operation from object performing it
  - Commands are first-class objects (manipulated and extended)
  - Can assemble commands into composite
  - Easy to add new commands
- **Cons**:
  - Can result in many small command classes
  - Indirection may reduce code readability

**References**:

- GoF Book: Pages 233-242
- Refactoring Guru: https://refactoring.guru/design-patterns/command
- Game Programming Patterns: https://gameprogrammingpatterns.com/command.html

---

### Interpreter

**Intent**: Given a language, define representation for its grammar along with an interpreter that uses the representation to interpret sentences in the language.

**Problem**: You need to interpret sentences in a simple language and the grammar is simple.

**Solution**: Define a class for each grammar rule. Syntax tree is instance of Composite pattern used to interpret sentences.

**Structure**:

- **AbstractExpression**: Interface for interpreting operations
- **TerminalExpression**: Implements interpret for terminal symbols
- **NonterminalExpression**: Implements interpret for grammar rules
- **Context**: Contains global information for interpreter
- **Client**: Builds abstract syntax tree; invokes interpret

**Consequences**:

- **Pros**:
  - Easy to change and extend grammar
  - Implementing grammar is straightforward
- **Cons**:
  - Complex grammars are hard to maintain
  - Not efficient for complex languages
  - Better alternatives exist (parser generators)

**WARNING**: Rarely used in modern development. Use parser libraries (pyparsing, ANTLR) for non-trivial grammars.

**References**:

- GoF Book: Pages 243-255
- Refactoring Guru: https://refactoring.guru/design-patterns/interpreter
- Source Making: https://sourcemaking.com/design_patterns/interpreter

---

### Iterator

**Intent**: Provide a way to access elements of an aggregate object sequentially without exposing its underlying representation.

**Problem**: You need to traverse a collection without exposing its internal structure or support multiple simultaneous traversals.

**Solution**: Define Iterator interface that provides methods for traversing collection. Aggregate creates iterator objects.

**Structure**:

- **Iterator**: Interface for accessing and traversing elements
- **ConcreteIterator**: Implements Iterator; keeps track of current position
- **Aggregate**: Interface for creating Iterator
- **ConcreteAggregate**: Implements Iterator creation; returns ConcreteIterator

**Consequences**:

- **Pros**:
  - Supports variations in traversal
  - Simplifies aggregate interface
  - Multiple simultaneous traversals
- **Cons**:
  - May be overkill for simple collections
  - Language-specific (most modern languages have built-in iteration)

**NOTE**: Most modern languages (Python, JavaScript, Java, C#) have built-in iterator support. Only implement manually for custom traversal logic.

**References**:

- GoF Book: Pages 257-271
- Refactoring Guru: https://refactoring.guru/design-patterns/iterator
- Python Patterns: https://python-patterns.guide/gang-of-four/iterator/

---

### Mediator

**Intent**: Define an object that encapsulates how a set of objects interact. Promotes loose coupling by keeping objects from referring to each other explicitly.

**Problem**: You have a set of objects that communicate in complex but well-defined ways, and the resulting interdependencies are unstructured and hard to understand.

**Solution**: Define Mediator object that handles interactions between colleague objects. Colleagues communicate through mediator rather than directly.

**Structure**:

- **Mediator**: Interface for communicating with Colleague objects
- **ConcreteMediator**: Implements cooperative behavior; coordinates Colleagues
- **Colleague**: Each Colleague knows its Mediator; communicates through it

**Consequences**:

- **Pros**:
  - Limits subclassing
  - Decouples colleagues
  - Simplifies object protocols
  - Abstracts object cooperation
  - Centralizes control
- **Cons**:
  - Mediator can become complex monolith
  - May become god object

**References**:

- GoF Book: Pages 273-282
- Refactoring Guru: https://refactoring.guru/design-patterns/mediator
- Source Making: https://sourcemaking.com/design_patterns/mediator

---

### Memento

**Intent**: Without violating encapsulation, capture and externalize object's internal state so object can be restored to this state later.

**Problem**: You need to save and restore object state (undo/redo, snapshots) without violating encapsulation.

**Solution**: Memento object stores snapshot of Originator's internal state. Only Originator can access Memento's contents.

**Structure**:

- **Memento**: Stores internal state of Originator; protects against access by objects other than Originator
- **Originator**: Creates memento containing snapshot; uses memento to restore state
- **Caretaker**: Responsible for memento's safekeeping; never operates on or examines memento contents

**Consequences**:

- **Pros**:
  - Preserves encapsulation boundaries
  - Simplifies Originator (no need to manage state history)
- **Cons**:
  - May be expensive (if Originator has large state)
  - Hidden costs in maintaining history
  - May require additional classes/interfaces

**References**:

- GoF Book: Pages 283-291
- Refactoring Guru: https://refactoring.guru/design-patterns/memento
- Source Making: https://sourcemaking.com/design_patterns/memento

---

### Observer

**Intent**: Define one-to-many dependency between objects so that when one object changes state, all dependents are notified and updated automatically.

**Problem**: You need to maintain consistency between related objects without making classes tightly coupled, or change to one object requires changing others.

**Solution**: Define Subject that maintains list of Observers. When Subject state changes, it notifies all Observers.

**Structure**:

- **Subject**: Knows its observers; provides interface for attaching/detaching observers
- **Observer**: Interface for objects that should be notified of changes
- **ConcreteSubject**: Stores state; sends notification when state changes
- **ConcreteObserver**: Maintains reference to ConcreteSubject; implements Observer update interface

**Consequences**:

- **Pros**:
  - Abstract coupling between Subject and Observer
  - Support for broadcast communication
  - Follows Open/Closed Principle
- **Cons**:
  - Unexpected updates
  - Update overhead
  - Memory leaks (observers not properly detached)

**References**:

- GoF Book: Pages 293-303
- Refactoring Guru: https://refactoring.guru/design-patterns/observer
- Game Programming Patterns: https://gameprogrammingpatterns.com/observer.html

---

### State

**Intent**: Allow an object to alter its behavior when its internal state changes. The object will appear to change its class.

**Problem**: Object behavior depends on its state, and it must change behavior at runtime depending on state.

**Solution**: Define separate State objects that encapsulate state-specific behavior. Context delegates state-specific behavior to current State object.

**Structure**:

- **Context**: Defines interface of interest to clients; maintains instance of ConcreteState that defines current state
- **State**: Interface for encapsulating behavior associated with particular state
- **ConcreteState**: Implements behavior associated with state of Context

**Consequences**:

- **Pros**:
  - Localizes state-specific behavior
  - Makes state transitions explicit
  - State objects can be shared
- **Cons**:
  - Increases number of classes
  - May be overkill for simple state machines

**References**:

- GoF Book: Pages 305-313
- Refactoring Guru: https://refactoring.guru/design-patterns/state
- Game Programming Patterns: https://gameprogrammingpatterns.com/state.html

---

### Strategy

**Intent**: Define a family of algorithms, encapsulate each one, and make them interchangeable. Lets algorithm vary independently from clients that use it.

**Problem**: You need different variants of an algorithm, or an algorithm uses data clients shouldn't know about, or a class defines many behaviors appearing as conditional statements.

**Solution**: Define family of Strategy classes that encapsulate different algorithms. Context uses Strategy interface, allowing algorithm to be selected at runtime.

**Structure**:

- **Strategy**: Common interface for all supported algorithms
- **ConcreteStrategy**: Implements algorithm using Strategy interface
- **Context**: Configured with ConcreteStrategy; maintains reference to Strategy; may define interface for Strategy to access its data

**Consequences**:

- **Pros**:
  - Families of related algorithms
  - Alternative to subclassing
  - Eliminates conditional statements
  - Provides choice of implementations
- **Cons**:
  - Clients must be aware of different strategies
  - Increases number of objects
  - Communication overhead between Strategy and Context

**References**:

- GoF Book: Pages 315-323
- Refactoring Guru: https://refactoring.guru/design-patterns/strategy
- Game Programming Patterns: https://gameprogrammingpatterns.com/strategy.html

---

### Template Method

**Intent**: Define skeleton of algorithm in operation, deferring some steps to subclasses. Lets subclasses redefine certain steps without changing algorithm's structure.

**Problem**: You have an algorithm with invariant parts and variant parts, and you want to avoid code duplication while allowing customization.

**Solution**: Define template method in base class that calls hook methods. Subclasses override hook methods to customize behavior.

**Structure**:

- **AbstractClass**: Defines abstract primitive operations; implements template method defining algorithm skeleton
- **ConcreteClass**: Implements primitive operations to carry out subclass-specific steps

**Consequences**:

- **Pros**:
  - Code reuse (common behavior in base class)
  - Inverted control ("Hollywood Principle")
  - Provides hooks for extension points
- **Cons**:
  - Clients may be limited by provided skeleton
  - Template method can become hard to maintain
  - Violates Liskov Substitution Principle if subclasses can't implement all steps

**References**:

- GoF Book: Pages 325-330
- Refactoring Guru: https://refactoring.guru/design-patterns/template-method
- Source Making: https://sourcemaking.com/design_patterns/template_method

---

### Visitor

**Intent**: Represent an operation to be performed on elements of an object structure. Lets you define new operation without changing classes of elements on which it operates.

**Problem**: You need to perform many distinct operations on objects in a structure, and you want to avoid polluting classes with these operations.

**Solution**: Define Visitor interface with visit method for each element type. Elements accept Visitors, calling appropriate visit method.

**Structure**:

- **Visitor**: Interface declaring visit operation for each ConcreteElement
- **ConcreteVisitor**: Implements operations defined by Visitor
- **Element**: Defines accept operation taking Visitor as argument
- **ConcreteElement**: Implements accept operation
- **ObjectStructure**: Can enumerate elements; may provide high-level interface for Visitor

**Consequences**:

- **Pros**:
  - Makes adding new operations easy
  - Gathers related operations
  - Can visit across class hierarchies
  - Can accumulate state
- **Cons**:
  - Adding new ConcreteElement classes is hard
  - Breaks encapsulation
  - May require public element interfaces

**WARNING**: Visitor is complex and often overused. Consider simpler alternatives (polymorphism, function dispatch) before using Visitor.

**References**:

- GoF Book: Pages 331-344
- Refactoring Guru: https://refactoring.guru/design-patterns/visitor
- Source Making: https://sourcemaking.com/design_patterns/visitor
