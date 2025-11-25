-- JWT Authentication Database Schema
-- Following ruthless simplicity: Start simple, measure, then optimize
-- PostgreSQL schema for user authentication system

-- Enable UUID extension for better ID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- USERS TABLE
-- =====================================================
-- Core user table with flexible design
CREATE TABLE users (
    -- Primary key using UUID for better distribution
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Core authentication fields
    email TEXT NOT NULL UNIQUE,
    username TEXT UNIQUE,  -- Optional username support
    password_hash TEXT NOT NULL,  -- bcrypt hash storage

    -- User status and verification
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    email_verified_at TIMESTAMPTZ,

    -- Role-based access control (start simple)
    role TEXT DEFAULT 'user' CHECK (role IN ('user', 'admin', 'moderator')),

    -- Flexible permissions using JSONB
    -- Allows evolution without schema changes
    permissions JSONB DEFAULT '[]'::jsonb,

    -- Profile data (flexible schema)
    profile JSONB DEFAULT '{}'::jsonb,

    -- Security fields
    last_login_at TIMESTAMPTZ,
    last_login_ip INET,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ,  -- Account lockout after failed attempts

    -- Audit fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ  -- Soft delete support
);

-- =====================================================
-- REFRESH TOKENS TABLE
-- =====================================================
-- Store refresh tokens in database for persistence
-- Access tokens are stateless (JWT), refresh tokens need tracking
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,  -- Store hash of token, not token itself

    -- Token metadata
    device_id TEXT,  -- Track device/browser
    user_agent TEXT,
    ip_address INET,

    -- Token lifecycle
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,  -- Soft revoke
    revoked_reason TEXT,
    last_used_at TIMESTAMPTZ,

    -- Audit
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- PASSWORD RESET TOKENS TABLE
-- =====================================================
-- Separate table for password reset tokens
CREATE TABLE password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,

    -- Token validity
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,

    -- Security
    ip_address INET,
    user_agent TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- AUDIT LOG TABLE
-- =====================================================
-- Track important security events
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Event details
    event_type TEXT NOT NULL,  -- login, logout, password_change, etc.
    event_data JSONB DEFAULT '{}'::jsonb,

    -- Context
    ip_address INET,
    user_agent TEXT,

    -- Timestamp
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =====================================================
-- INDEXES FOR PERFORMANCE
-- =====================================================
-- Only add indexes based on actual query patterns
-- Start with these essential ones:

-- User lookups
CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_username ON users(username) WHERE username IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX idx_users_created_at ON users(created_at DESC);

-- Token lookups
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at) WHERE revoked_at IS NULL;
CREATE INDEX idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);
CREATE INDEX idx_password_reset_tokens_expires_at ON password_reset_tokens(expires_at) WHERE used_at IS NULL;

-- Audit log queries
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_event_type ON audit_logs(event_type);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- JSONB indexes for permissions (when patterns emerge)
-- CREATE INDEX idx_users_permissions ON users USING GIN (permissions);
-- CREATE INDEX idx_users_profile ON users USING GIN (profile);

-- =====================================================
-- TRIGGERS
-- =====================================================
-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- VIEWS FOR COMMON QUERIES
-- =====================================================
-- Active users view (excludes soft-deleted)
CREATE VIEW active_users AS
SELECT * FROM users WHERE deleted_at IS NULL AND is_active = true;

-- Valid refresh tokens view
CREATE VIEW valid_refresh_tokens AS
SELECT * FROM refresh_tokens
WHERE revoked_at IS NULL AND expires_at > NOW();

-- =====================================================
-- COMMENTS FOR DOCUMENTATION
-- =====================================================
COMMENT ON TABLE users IS 'Core user authentication table with flexible JSONB fields for evolution';
COMMENT ON COLUMN users.permissions IS 'Array of permission strings, e.g. ["read:posts", "write:posts"]';
COMMENT ON COLUMN users.profile IS 'Flexible user profile data: {"name": "...", "avatar": "...", ...}';
COMMENT ON COLUMN users.locked_until IS 'Account lockout after N failed login attempts';

COMMENT ON TABLE refresh_tokens IS 'Persistent refresh tokens for JWT authentication flow';
COMMENT ON TABLE password_reset_tokens IS 'One-time tokens for password reset flow';
COMMENT ON TABLE audit_logs IS 'Security audit trail for user actions';