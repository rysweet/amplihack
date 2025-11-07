// Performance indexes for common queries
// These speed up filtering and sorting operations

CREATE INDEX memory_type IF NOT EXISTS
FOR (m:Memory) ON (m.memory_type);

CREATE INDEX memory_created_at IF NOT EXISTS
FOR (m:Memory) ON (m.created_at);

CREATE INDEX agent_type_name IF NOT EXISTS
FOR (at:AgentType) ON (at.name);

CREATE INDEX project_path IF NOT EXISTS
FOR (p:Project) ON (p.path);
