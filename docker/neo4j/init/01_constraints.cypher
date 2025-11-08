// Unique constraints for IDs
// These ensure data integrity at database level

CREATE CONSTRAINT agent_type_id IF NOT EXISTS
FOR (at:AgentType) REQUIRE at.id IS UNIQUE;

CREATE CONSTRAINT project_id IF NOT EXISTS
FOR (p:Project) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT memory_id IF NOT EXISTS
FOR (m:Memory) REQUIRE m.id IS UNIQUE;
