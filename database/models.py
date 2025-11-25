"""
SQLAlchemy ORM Models for JWT Authentication System
Following ruthless simplicity: declarative models with sensible defaults
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy import (
    Column, String, Boolean, Integer, DateTime, Text,
    ForeignKey, CheckConstraint, Index, text
)
from sqlalchemy.dialects.postgresql import UUID, INET, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    """
    Core user model with authentication fields.
    Uses JSONB for flexible evolution without schema changes.
    """
    __tablename__ = 'users'

    # Primary Key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4,
                server_default=text("uuid_generate_v4()"))

    # Authentication
    email = Column(Text, nullable=False, unique=True, index=True)
    username = Column(Text, unique=True, index=True)
    password_hash = Column(Text, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, server_default="true", nullable=False)
    is_verified = Column(Boolean, default=False, server_default="false", nullable=False)
    email_verified_at = Column(DateTime(timezone=True))

    # RBAC - Start simple with role, expand with permissions
    role = Column(Text, default="user", server_default="user", nullable=False)
    permissions = Column(JSONB, default=list, server_default="[]", nullable=False)

    # Profile - Flexible storage
    profile = Column(JSONB, default=dict, server_default="{}", nullable=False)

    # Security tracking
    last_login_at = Column(DateTime(timezone=True))
    last_login_ip = Column(INET)
    failed_login_attempts = Column(Integer, default=0, server_default="0", nullable=False)
    locked_until = Column(DateTime(timezone=True))

    # Audit
    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now(),
                        onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True))  # Soft delete

    # Relationships
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")

    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('user', 'admin', 'moderator')", name="check_user_role"),
        Index("idx_users_email", "email", postgresql_where=text("deleted_at IS NULL")),
        Index("idx_users_username", "username",
              postgresql_where=text("username IS NOT NULL AND deleted_at IS NULL")),
        Index("idx_users_created_at", text("created_at DESC")),
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"

    # Helper methods
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        return permission in (self.permissions or [])

    def add_permission(self, permission: str):
        """Add a permission to user"""
        if not self.permissions:
            self.permissions = []
        if permission not in self.permissions:
            self.permissions = self.permissions + [permission]  # Trigger JSONB update

    def remove_permission(self, permission: str):
        """Remove a permission from user"""
        if self.permissions and permission in self.permissions:
            self.permissions = [p for p in self.permissions if p != permission]

    def is_locked(self) -> bool:
        """Check if account is locked"""
        if self.locked_until:
            return datetime.utcnow() < self.locked_until
        return False

    def update_profile(self, **kwargs):
        """Update profile data"""
        if not self.profile:
            self.profile = {}
        self.profile = {**self.profile, **kwargs}  # Trigger JSONB update


class RefreshToken(Base):
    """
    Refresh tokens for JWT authentication.
    Access tokens are stateless, refresh tokens are tracked.
    """
    __tablename__ = 'refresh_tokens'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4,
                server_default=text("uuid_generate_v4()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash = Column(Text, nullable=False, unique=True, index=True)

    # Metadata for security
    device_id = Column(Text)
    user_agent = Column(Text)
    ip_address = Column(INET)

    # Lifecycle
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    revoked_at = Column(DateTime(timezone=True))
    revoked_reason = Column(Text)
    last_used_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    # Indexes
    __table_args__ = (
        Index("idx_refresh_tokens_user_id", "user_id"),
        Index("idx_refresh_tokens_expires_at", "expires_at",
              postgresql_where=text("revoked_at IS NULL")),
    )

    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"

    def is_valid(self) -> bool:
        """Check if token is still valid"""
        return (
            self.revoked_at is None and
            self.expires_at > datetime.utcnow()
        )

    def revoke(self, reason: str = None):
        """Revoke this refresh token"""
        self.revoked_at = datetime.utcnow()
        self.revoked_reason = reason


class PasswordResetToken(Base):
    """
    One-time tokens for password reset flow.
    """
    __tablename__ = 'password_reset_tokens'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4,
                server_default=text("uuid_generate_v4()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash = Column(Text, nullable=False, unique=True, index=True)

    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True))

    # Security context
    ip_address = Column(INET)
    user_agent = Column(Text)

    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="password_reset_tokens")

    # Indexes
    __table_args__ = (
        Index("idx_password_reset_tokens_user_id", "user_id"),
        Index("idx_password_reset_tokens_expires_at", "expires_at",
              postgresql_where=text("used_at IS NULL")),
    )

    def __repr__(self):
        return f"<PasswordResetToken(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"

    def is_valid(self) -> bool:
        """Check if token is still valid"""
        return (
            self.used_at is None and
            self.expires_at > datetime.utcnow()
        )

    def mark_used(self):
        """Mark token as used"""
        self.used_at = datetime.utcnow()


class AuditLog(Base):
    """
    Security audit trail for important events.
    """
    __tablename__ = 'audit_logs'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4,
                server_default=text("uuid_generate_v4()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='SET NULL'))

    event_type = Column(Text, nullable=False, index=True)
    event_data = Column(JSONB, default=dict, server_default="{}", nullable=False)

    ip_address = Column(INET)
    user_agent = Column(Text)

    created_at = Column(DateTime(timezone=True), default=func.now(), server_default=func.now(),
                        nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    # Indexes
    __table_args__ = (
        Index("idx_audit_logs_user_id", "user_id"),
        Index("idx_audit_logs_event_type", "event_type"),
        Index("idx_audit_logs_created_at", text("created_at DESC")),
    )

    def __repr__(self):
        return f"<AuditLog(id={self.id}, event_type={self.event_type}, user_id={self.user_id})>"

    @classmethod
    def log(cls, db: Session, event_type: str, user_id: Optional[str] = None,
            event_data: Optional[Dict[str, Any]] = None, ip_address: Optional[str] = None,
            user_agent: Optional[str] = None):
        """
        Convenience method to create audit log entries.

        Example:
            AuditLog.log(db, "login_success", user_id=user.id,
                        event_data={"method": "password"},
                        ip_address=request.client.host)
        """
        log_entry = cls(
            event_type=event_type,
            user_id=user_id,
            event_data=event_data or {},
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.add(log_entry)
        db.commit()
        return log_entry


# Common event types for audit logging
class AuditEventType:
    """Constants for audit event types"""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_COMPLETE = "password_reset_complete"
    EMAIL_VERIFICATION = "email_verification"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    PERMISSION_CHANGE = "permission_change"
    ROLE_CHANGE = "role_change"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_REVOKED = "token_revoked"
    ACCOUNT_DELETED = "account_deleted"