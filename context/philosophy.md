# Amplihack Development Philosophy

This document outlines the core development philosophy that guides our approach to building software with AI assistance.

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

Like a brick model, our software is built from small, clear modules. Each module is a self-contained "brick" of functionality with defined connectors (interfaces) to the rest of the system.

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

### 3. Zero-BS Implementations

- **Focus on quality**: Prioritize robust, well-tested implementations over quick fixes
- **Avoid technical debt**: Don't sacrifice long-term maintainability for short-term gains
- **No shortcuts**: Every function must work or not exist
- **No stubs or placeholders**: No dead code, unimplemented functions, or TODOs in code
- **No faked APIs or mock implementations**: Implement real functionality from the start (except in tests)
- **No swallowed exceptions**: Handle errors transparently

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
