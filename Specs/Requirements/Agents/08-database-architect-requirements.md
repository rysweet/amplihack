# Database Architect Agent Requirements

## Purpose and Value Proposition
Designs efficient database schemas, optimizes queries, and ensures data integrity and performance.

## Core Functional Requirements
- FR8.1: MUST design normalized database schemas
- FR8.2: MUST create and optimize indexes
- FR8.3: MUST write efficient queries with explain plans
- FR8.4: MUST implement data integrity constraints
- FR8.5: MUST design migration strategies
- FR8.6: MUST optimize for specific database engines

## Input Requirements
- IR8.1: Data requirements and relationships
- IR8.2: Query patterns and access frequencies
- IR8.3: Performance requirements
- IR8.4: Existing schema (for migrations)

## Output Requirements
- OR8.1: Database schema with DDL scripts
- OR8.2: Index definitions with rationale
- OR8.3: Optimized queries with explain plans
- OR8.4: Migration scripts with rollback plans
- OR8.5: Data integrity rules and constraints

## Quality Requirements
- QR8.1: Schemas must be properly normalized (3NF minimum)
- QR8.2: Queries must meet performance SLAs
- QR8.3: Migrations must be reversible
- QR8.4: Data integrity must be guaranteed