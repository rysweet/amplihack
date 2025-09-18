# Development Philosophy

This document outlines the core development philosophy that guides our approach to building software with AI assistance. It combines principles of ruthless simplicity with modular design for AI-powered development.

## Core Philosophy

### The Zen of Simple Code

Our development philosophy embodies a Zen-like minimalism that values simplicity and clarity above all:

- **Wabi-sabi philosophy**: Embracing simplicity and the essential. Each line serves a clear purpose without unnecessary embellishment.
- **Occam's Razor thinking**: The solution should be as simple as possible, but no simpler.
- **Trust in emergence**: Complex systems work best when built from simple, well-defined components that do one thing well.
- **Present-moment focus**: The code handles what's needed now rather than anticipating every possible future scenario.
- **Pragmatic trust**: We trust external systems enough to interact with them directly, handling failures as they occur rather than assuming they'll happen.

### The Brick Philosophy for AI Development

_"We provide the blueprint, and AI builds the product, one modular piece at a time."_

Like a brick model, our software is built from small, clear modules. Each module is a self-contained "brick" of functionality with defined connectors (interfaces) to the rest of the system. Because these connection points are standard and stable, we can generate or regenerate any single module independently without breaking the whole.

**Key concepts:**

- **A brick** = Self-contained module with ONE clear responsibility
- **A stud** = Public contract (functions, API, data model) others connect to
- **Regeneratable** = Can be rebuilt from spec without breaking connections
- **Isolated** = All code, tests, fixtures inside the module's folder

## Core Design Principles

### 1. Ruthless Simplicity

- **KISS principle taken to heart**: Keep everything as simple as possible, but no simpler
- **Minimize abstractions**: Every layer of abstraction must justify its existence
- **Start minimal, grow as needed**: Begin with the simplest implementation that meets current needs
- **Avoid future-proofing**: Don't build for hypothetical future requirements
- **Question everything**: Regularly challenge complexity in the codebase

### 2. Modular Architecture for AI

- **Preserve key architectural patterns**: Clear module boundaries with defined contracts
- **Simplify implementations**: Maintain pattern benefits with dramatically simpler code
- **Scrappy but structured**: Lightweight implementations of solid architectural foundations
- **End-to-end thinking**: Focus on complete flows rather than perfect components
- **Regeneration-ready**: Every module can be rebuilt from its specification

### 3. Library vs Custom Code

Choosing between custom code and external libraries is a judgment call that evolves with requirements:

#### When Custom Code Makes Sense

- The need is simple and well-understood
- You want code perfectly tuned to your exact requirements
- Libraries would require significant "hacking" or workarounds
- The problem is unique to your domain
- You need full control over the implementation

#### When Libraries Make Sense

- They solve complex problems you'd rather not tackle (auth, crypto, video encoding)
- They align well with your needs without major modifications
- The problem is well-solved with mature, battle-tested solutions
- Configuration alone can adapt them to your requirements
- The complexity they handle far exceeds the integration cost

#### Stay Flexible

Keep library integration points minimal and isolated so you can switch approaches when needed. There's no shame in moving from custom to library or library to custom. Requirements change, understanding deepens, and the right answer today might not be the right answer tomorrow.

## The Human-AI Partnership

### Humans as Architects, AI as Builders

In this approach, humans step back from being code mechanics and instead take on the role of architects and quality inspectors:

- **Humans define**: Vision, specifications, contracts, and quality standards
- **AI builds**: Code implementation according to specifications
- **Humans validate**: Testing behavior, not reviewing every line of code
- **AI regenerates**: Modules can be rebuilt when requirements change

### Building in Parallel

Our AI builders can spawn multiple versions of software in parallel:

- Generate and test multiple variants of a feature simultaneously
- Try different algorithms or approaches side by side
- Build for multiple platforms from the same specifications
- Learn from parallel experiments to refine specifications

## Development Approach

### Vertical Slices

- Implement complete end-to-end functionality slices
- Start with core user journeys
- Get data flowing through all layers early
- Add features horizontally only after core flows work

### Iterative Implementation

- 80/20 principle: Focus on high-value, low-effort features first
- One working feature > multiple partial features
- Validate with real usage before enhancing
- Be willing to refactor early work as patterns emerge

### Testing Strategy

- Emphasis on behavior testing at module boundaries
- Manual testability as a design goal
- Focus on critical path testing initially
- Add unit tests for complex logic and edge cases
- Testing pyramid: 60% unit, 30% integration, 10% end-to-end

### Error Handling

- Handle common errors robustly
- Log detailed information for debugging
- Provide clear error messages to users
- Fail fast and visibly during development

## Decision-Making Framework

When faced with implementation decisions, ask:

1. **Necessity**: "Do we actually need this right now?"
2. **Simplicity**: "What's the simplest way to solve this problem?"
3. **Modularity**: "Can this be a self-contained brick?"
4. **Regenerability**: "Can AI rebuild this from a specification?"
5. **Value**: "Does the complexity add proportional value?"
6. **Maintenance**: "How easy will this be to understand and change later?"

## Areas to Embrace Complexity

Some areas justify additional complexity:

- **Security**: Never compromise on security fundamentals
- **Data integrity**: Ensure data consistency and reliability
- **Core user experience**: Make the primary user flows smooth and reliable
- **Error visibility**: Make problems obvious and diagnosable

## Areas to Aggressively Simplify

Push for extreme simplicity in:

- **Internal abstractions**: Minimize layers between components
- **Generic "future-proof" code**: Resist solving non-existent problems
- **Edge case handling**: Handle the common cases well first
- **Framework usage**: Use only what you need from frameworks
- **State management**: Keep state simple and explicit

## Remember

- **It's easier to add complexity later than to remove it**
- **Code you don't write has no bugs**
- **Favor clarity over cleverness**
- **The best code is often the simplest**
- **Trust AI to handle the details while you guide the vision**
- **Modules should be bricks: self-contained and regeneratable**

This philosophy serves as the foundational guide for all development decisions in the project.
