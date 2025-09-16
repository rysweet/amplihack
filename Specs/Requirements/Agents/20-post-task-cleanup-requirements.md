# Post Task Cleanup Agent Requirements

## Purpose and Value Proposition
Ensures codebase hygiene after task completion by removing artifacts and validating philosophy compliance.

## Core Functional Requirements
- FR20.1: MUST analyze version control status for all changes
- FR20.2: MUST identify and remove temporary artifacts
- FR20.3: MUST check philosophy compliance
- FR20.4: MUST detect unnecessary complexity
- FR20.5: MUST validate modular design principles
- FR20.6: MUST delegate fixes to appropriate agents

## Input Requirements
- IR20.1: The agent must receive completed task context and descriptions
- IR20.2: The agent must access version control repository state
- IR20.3: The agent must reference philosophy documents for compliance checking
- IR20.4: The agent must process the list of changed files

## Output Requirements
- OR20.1: The agent must report all cleanup actions taken
- OR20.2: The agent must identify philosophy violations found
- OR20.3: The agent must provide delegation recommendations for fixes
- OR20.4: The agent must generate a final cleanliness report
- OR20.5: The agent must suggest preventions for future issues

## Quality Requirements
- QR20.1: Must not break working functionality
- QR20.2: All temporary files must be identified
- QR20.3: Philosophy checks must be comprehensive
- QR20.4: Reports must be actionable