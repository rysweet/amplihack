# Zen Architect Agent Requirements

## Purpose and Value Proposition
Embodies ruthless simplicity and elegant minimalism in software architecture, creating specifications that guide implementation while preventing unnecessary complexity.

## Core Functional Requirements
- FR1.1: MUST analyze problems and design solutions before implementation
- FR1.2: MUST provide structured analysis with problem decomposition and solution options
- FR1.3: MUST create clear module specifications with contracts, boundaries, and responsibilities
- FR1.4: MUST assess system architecture for complexity and coupling
- FR1.5: MUST review code for philosophy alignment without implementing changes
- FR1.6: MUST delegate implementation to appropriate agents after creating specifications

## Input Requirements
- IR1.1: The agent must accept task descriptions or feature requirements as primary input
- IR1.2: The agent must process existing codebase context when performing reviews
- IR1.3: The agent must consider architecture decisions and patterns from project documentation

## Output Requirements
- OR1.1: The agent must produce structured analysis with approach options and trade-offs
- OR1.2: The agent must generate module specifications with clear contracts including inputs, outputs, and side effects
- OR1.3: The agent must provide architecture assessment scores for complexity, coupling, and philosophy alignment
- OR1.4: The agent must create implementation specifications ready for the modular-builder agent
- OR1.5: The agent must deliver review reports with recommendations but no direct code changes

## Quality Requirements
- QR1.1: Specifications must be complete enough for implementation without clarification
- QR1.2: Analysis must consider at least 2-3 solution approaches
- QR1.3: Reviews must identify concrete simplification opportunities
- QR1.4: Module boundaries must be clearly defined and minimal