// Seed common agent types
// MERGE ensures idempotent operation (safe to run multiple times)

MERGE (at:AgentType {id: 'architect'})
ON CREATE SET
  at.name = 'Architect Agent',
  at.description = 'System design and architecture',
  at.created_at = timestamp();

MERGE (at:AgentType {id: 'builder'})
ON CREATE SET
  at.name = 'Builder Agent',
  at.description = 'Code implementation',
  at.created_at = timestamp();

MERGE (at:AgentType {id: 'reviewer'})
ON CREATE SET
  at.name = 'Reviewer Agent',
  at.description = 'Code review and quality assurance',
  at.created_at = timestamp();

MERGE (at:AgentType {id: 'tester'})
ON CREATE SET
  at.name = 'Tester Agent',
  at.description = 'Test generation and validation',
  at.created_at = timestamp();

MERGE (at:AgentType {id: 'optimizer'})
ON CREATE SET
  at.name = 'Optimizer Agent',
  at.description = 'Performance optimization',
  at.created_at = timestamp();
