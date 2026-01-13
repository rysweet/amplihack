-- Database Schema for 5-Type Memory System
-- Extends existing SQLite schema with psychological memory types

-- ============================================================================
-- Core Tables
-- ============================================================================

-- Memory entries with 5 psychological types
CREATE TABLE IF NOT EXISTS memory_entries (
    -- Identity
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,

    -- Memory type (5 psychological types)
    memory_type TEXT NOT NULL CHECK (
        memory_type IN ('episodic', 'semantic', 'prospective', 'procedural', 'working')
    ),

    -- Content
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata TEXT,  -- JSON

    -- Scoring
    importance INTEGER CHECK (importance >= 1 AND importance <= 10),
    relevance_score REAL,  -- Cached relevance for recent queries

    -- Tags (JSON array)
    tags TEXT,

    -- Timestamps
    created_at TEXT NOT NULL,
    accessed_at TEXT NOT NULL,
    expires_at TEXT,

    -- Hierarchy
    parent_id TEXT,

    FOREIGN KEY (parent_id) REFERENCES memory_entries(id) ON DELETE CASCADE
);

-- Sessions
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    last_accessed TEXT NOT NULL,
    metadata TEXT  -- JSON
);

-- Agent activity tracking
CREATE TABLE IF NOT EXISTS session_agents (
    session_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    first_activity TEXT NOT NULL,
    last_activity TEXT NOT NULL,
    memory_count INTEGER DEFAULT 0,

    PRIMARY KEY (session_id, agent_id),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

-- Review history (for transparency and debugging)
CREATE TABLE IF NOT EXISTS review_history (
    id TEXT PRIMARY KEY,
    memory_id TEXT,  -- NULL if rejected
    content_hash TEXT NOT NULL,  -- For deduplication
    memory_type TEXT NOT NULL,

    -- Review results
    average_score REAL NOT NULL,
    should_store BOOLEAN NOT NULL,

    -- Individual agent scores (JSON array)
    agent_scores TEXT NOT NULL,

    -- Metadata
    reviewed_at TEXT NOT NULL,
    review_duration_ms INTEGER,

    FOREIGN KEY (memory_id) REFERENCES memory_entries(id) ON DELETE SET NULL
);

-- ============================================================================
-- Indexes for Performance (<50ms retrieval)
-- ============================================================================

-- Primary retrieval patterns
CREATE INDEX IF NOT EXISTS idx_memory_type
    ON memory_entries(memory_type);

CREATE INDEX IF NOT EXISTS idx_agent_id
    ON memory_entries(agent_id);

CREATE INDEX IF NOT EXISTS idx_session_id
    ON memory_entries(session_id);

CREATE INDEX IF NOT EXISTS idx_importance
    ON memory_entries(importance);

CREATE INDEX IF NOT EXISTS idx_created_at
    ON memory_entries(created_at);

-- Compound indexes for common queries
CREATE INDEX IF NOT EXISTS idx_type_importance
    ON memory_entries(memory_type, importance);

CREATE INDEX IF NOT EXISTS idx_type_agent
    ON memory_entries(memory_type, agent_id);

CREATE INDEX IF NOT EXISTS idx_agent_importance
    ON memory_entries(agent_id, importance);

-- Full-text search
CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
    title,
    content,
    content=memory_entries,
    content_rowid=rowid
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS memory_fts_insert AFTER INSERT ON memory_entries BEGIN
    INSERT INTO memory_fts(rowid, title, content)
    VALUES (new.rowid, new.title, new.content);
END;

CREATE TRIGGER IF NOT EXISTS memory_fts_delete AFTER DELETE ON memory_entries BEGIN
    DELETE FROM memory_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS memory_fts_update AFTER UPDATE ON memory_entries BEGIN
    UPDATE memory_fts SET title = new.title, content = new.content
    WHERE rowid = new.rowid;
END;

-- ============================================================================
-- Views for Common Queries
-- ============================================================================

-- Active memories (not expired, not working)
CREATE VIEW IF NOT EXISTS active_memories AS
SELECT * FROM memory_entries
WHERE (expires_at IS NULL OR expires_at > datetime('now'))
  AND memory_type != 'working'
ORDER BY importance DESC, created_at DESC;

-- High-value semantic memories (learnings)
CREATE VIEW IF NOT EXISTS learnings AS
SELECT * FROM memory_entries
WHERE memory_type = 'semantic'
  AND importance >= 7
  AND (expires_at IS NULL OR expires_at > datetime('now'))
ORDER BY importance DESC, created_at DESC;

-- Pending prospective memories (TODOs)
CREATE VIEW IF NOT EXISTS pending_todos AS
SELECT * FROM memory_entries
WHERE memory_type = 'prospective'
  AND (expires_at IS NULL OR expires_at > datetime('now'))
ORDER BY importance DESC, created_at ASC;

-- Recent episodic memories (conversations)
CREATE VIEW IF NOT EXISTS recent_conversations AS
SELECT * FROM memory_entries
WHERE memory_type = 'episodic'
  AND (expires_at IS NULL OR expires_at > datetime('now'))
ORDER BY created_at DESC
LIMIT 100;

-- Procedural memories (workflows)
CREATE VIEW IF NOT EXISTS procedures AS
SELECT * FROM memory_entries
WHERE memory_type = 'procedural'
  AND importance >= 7
  AND (expires_at IS NULL OR expires_at > datetime('now'))
ORDER BY importance DESC, accessed_at DESC;

-- ============================================================================
-- Migration from Current Schema
-- ============================================================================

-- Map old memory types to new psychological types
-- Run this after schema update to migrate existing data

-- Old → New mapping:
-- conversation → episodic
-- decision → semantic
-- pattern → semantic
-- context → working
-- learning → semantic
-- artifact → semantic

-- Migration query (run once):
/*
UPDATE memory_entries
SET memory_type = CASE memory_type
    WHEN 'conversation' THEN 'episodic'
    WHEN 'decision' THEN 'semantic'
    WHEN 'pattern' THEN 'semantic'
    WHEN 'context' THEN 'working'
    WHEN 'learning' THEN 'semantic'
    WHEN 'artifact' THEN 'semantic'
    ELSE memory_type
END
WHERE memory_type IN ('conversation', 'decision', 'pattern', 'context', 'learning', 'artifact');
*/

-- ============================================================================
-- Example Queries
-- ============================================================================

-- Store episodic memory (conversation event)
/*
INSERT INTO memory_entries (
    id, session_id, agent_id, memory_type,
    title, content, metadata, importance,
    created_at, accessed_at
) VALUES (
    'mem_' || hex(randomblob(16)),
    'session_123',
    'orchestrator',
    'episodic',
    'User discussed authentication',
    'User asked about JWT implementation',
    json_object('participants', json_array('user', 'architect')),
    6,
    datetime('now'),
    datetime('now')
);
*/

-- Retrieve semantic memories (learnings) about API design
/*
SELECT * FROM memory_entries
WHERE memory_type = 'semantic'
  AND importance >= 7
  AND (content LIKE '%API%' OR tags LIKE '%"api"%')
  AND (expires_at IS NULL OR expires_at > datetime('now'))
ORDER BY importance DESC, created_at DESC
LIMIT 10;
*/

-- Retrieve pending TODOs (prospective memories)
/*
SELECT * FROM pending_todos
WHERE agent_id = 'architect'
LIMIT 20;
*/

-- Clear working memory after task completion
/*
DELETE FROM memory_entries
WHERE memory_type = 'working'
  AND session_id = 'session_123'
  AND agent_id = 'builder';
*/

-- Full-text search across all memories
/*
SELECT m.* FROM memory_entries m
JOIN memory_fts fts ON m.rowid = fts.rowid
WHERE memory_fts MATCH 'authentication JWT'
ORDER BY rank, m.importance DESC
LIMIT 10;
*/

-- Get review history for transparency
/*
SELECT
    rh.reviewed_at,
    rh.memory_type,
    rh.average_score,
    rh.should_store,
    rh.agent_scores,
    me.title
FROM review_history rh
LEFT JOIN memory_entries me ON rh.memory_id = me.id
WHERE rh.reviewed_at > datetime('now', '-1 day')
ORDER BY rh.reviewed_at DESC;
*/

-- ============================================================================
-- Maintenance Queries
-- ============================================================================

-- Clean up expired memories
/*
DELETE FROM memory_entries
WHERE expires_at IS NOT NULL
  AND expires_at < datetime('now');
*/

-- Clean up old working memories (>7 days)
/*
DELETE FROM memory_entries
WHERE memory_type = 'working'
  AND created_at < datetime('now', '-7 days');
*/

-- Vacuum and optimize
/*
VACUUM;
ANALYZE;
*/

-- Get database statistics
/*
SELECT
    memory_type,
    COUNT(*) as count,
    AVG(importance) as avg_importance,
    COUNT(DISTINCT agent_id) as agents
FROM memory_entries
WHERE expires_at IS NULL OR expires_at > datetime('now')
GROUP BY memory_type
ORDER BY count DESC;
*/

-- ============================================================================
-- Performance Validation
-- ============================================================================

-- Verify query performance (<50ms)
/*
EXPLAIN QUERY PLAN
SELECT * FROM memory_entries
WHERE memory_type = 'semantic'
  AND importance >= 7
  AND agent_id = 'architect'
ORDER BY created_at DESC
LIMIT 10;

-- Should use indexes:
-- SEARCH memory_entries USING INDEX idx_type_importance
*/

-- Check index usage
/*
SELECT * FROM sqlite_stat1
WHERE tbl = 'memory_entries';
*/
