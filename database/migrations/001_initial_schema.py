"""
Initial database schema for JWT authentication system
Migration: 001_initial_schema.py
Date: 2024

This migration creates the core tables for user authentication with JWT tokens.
Follows the principle of starting simple and evolving based on measured needs.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """
    Create initial schema for JWT authentication
    """

    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),

        # Authentication fields
        sa.Column('email', sa.Text(), nullable=False),
        sa.Column('username', sa.Text(), nullable=True),
        sa.Column('password_hash', sa.Text(), nullable=False),

        # Status fields
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_verified', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('email_verified_at', sa.TIMESTAMP(timezone=True), nullable=True),

        # RBAC
        sa.Column('role', sa.Text(), server_default='user', nullable=False),
        sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),

        # Profile
        sa.Column('profile', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),

        # Security
        sa.Column('last_login_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('last_login_ip', postgresql.INET(), nullable=True),
        sa.Column('failed_login_attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('locked_until', sa.TIMESTAMP(timezone=True), nullable=True),

        # Audit
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username'),
        sa.CheckConstraint("role IN ('user', 'admin', 'moderator')", name='check_user_role')
    )

    # Create refresh_tokens table
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.Text(), nullable=False),

        # Metadata
        sa.Column('device_id', sa.Text(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),

        # Lifecycle
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('revoked_reason', sa.Text(), nullable=True),
        sa.Column('last_used_at', sa.TIMESTAMP(timezone=True), nullable=True),

        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    # Create password_reset_tokens table
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.Text(), nullable=False),

        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('used_at', sa.TIMESTAMP(timezone=True), nullable=True),

        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),

        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('uuid_generate_v4()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),

        sa.Column('event_type', sa.Text(), nullable=False),
        sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),

        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),

        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()'), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL')
    )

    # Create indexes
    op.create_index('idx_users_email', 'users', ['email'], postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_index('idx_users_username', 'users', ['username'],
                    postgresql_where=sa.text('username IS NOT NULL AND deleted_at IS NULL'))
    op.create_index('idx_users_created_at', 'users', [sa.text('created_at DESC')])

    op.create_index('idx_refresh_tokens_user_id', 'refresh_tokens', ['user_id'])
    op.create_index('idx_refresh_tokens_expires_at', 'refresh_tokens', ['expires_at'],
                    postgresql_where=sa.text('revoked_at IS NULL'))

    op.create_index('idx_password_reset_tokens_user_id', 'password_reset_tokens', ['user_id'])
    op.create_index('idx_password_reset_tokens_expires_at', 'password_reset_tokens', ['expires_at'],
                    postgresql_where=sa.text('used_at IS NULL'))

    op.create_index('idx_audit_logs_user_id', 'audit_logs', ['user_id'])
    op.create_index('idx_audit_logs_event_type', 'audit_logs', ['event_type'])
    op.create_index('idx_audit_logs_created_at', 'audit_logs', [sa.text('created_at DESC')])

    # Create update trigger
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)

    # Create views
    op.execute("""
        CREATE VIEW active_users AS
        SELECT * FROM users WHERE deleted_at IS NULL AND is_active = true;
    """)

    op.execute("""
        CREATE VIEW valid_refresh_tokens AS
        SELECT * FROM refresh_tokens
        WHERE revoked_at IS NULL AND expires_at > NOW();
    """)


def downgrade() -> None:
    """
    Drop all tables and clean up
    """

    # Drop views
    op.execute('DROP VIEW IF EXISTS valid_refresh_tokens')
    op.execute('DROP VIEW IF EXISTS active_users')

    # Drop trigger and function
    op.execute('DROP TRIGGER IF EXISTS update_users_updated_at ON users')
    op.execute('DROP FUNCTION IF EXISTS update_updated_at_column()')

    # Drop tables in reverse order (respect foreign keys)
    op.drop_table('audit_logs')
    op.drop_table('password_reset_tokens')
    op.drop_table('refresh_tokens')
    op.drop_table('users')