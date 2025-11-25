"""
Audit Logger - logs authentication events for security monitoring.
Simple implementation that writes to structured logs.
"""

import logging
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum


class AuditEventType(Enum):
    """Types of audit events."""
    USER_REGISTERED = "user_registered"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    TOKEN_REFRESHED = "token_refreshed"
    TOKEN_REVOKED = "token_revoked"
    PASSWORD_CHANGED = "password_changed"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"


class AuditLogger:
    """Logger for authentication audit events."""

    def __init__(self, logger_name: str = "auth.audit"):
        """
        Initialize audit logger.

        Args:
            logger_name: Name for the logger instance
        """
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)

        # Ensure we have a handler
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def _log_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None
    ):
        """
        Log an audit event.

        Args:
            event_type: Type of event
            user_id: User ID if applicable
            email: User email if applicable
            ip_address: Request IP address
            user_agent: Request user agent
            additional_data: Additional event data
        """
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type.value,
            "user_id": user_id,
            "email": email,
            "ip_address": ip_address,
            "user_agent": user_agent,
        }

        if additional_data:
            event.update(additional_data)

        # Log as structured JSON
        self.logger.info(json.dumps(event))

    def log_user_registration(
        self,
        user_id: str,
        email: str,
        username: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Log user registration event.

        Args:
            user_id: New user ID
            email: User email
            username: User username
            ip_address: Request IP address
            user_agent: Request user agent
        """
        self._log_event(
            AuditEventType.USER_REGISTERED,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            additional_data={"username": username}
        )

    def log_successful_login(
        self,
        user_id: str,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Log successful login event.

        Args:
            user_id: User ID
            email: User email
            ip_address: Request IP address
            user_agent: Request user agent
        """
        self._log_event(
            AuditEventType.LOGIN_SUCCESS,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent
        )

    def log_failed_login(
        self,
        email: str,
        reason: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Log failed login event.

        Args:
            email: Attempted email
            reason: Reason for failure
            ip_address: Request IP address
            user_agent: Request user agent
        """
        self._log_event(
            AuditEventType.LOGIN_FAILED,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent,
            additional_data={"reason": reason}
        )

    def log_logout(
        self,
        user_id: str,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Log logout event.

        Args:
            user_id: User ID
            email: User email
            ip_address: Request IP address
            user_agent: Request user agent
        """
        self._log_event(
            AuditEventType.LOGOUT,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent
        )

    def log_token_refreshed(
        self,
        user_id: str,
        email: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Log token refresh event.

        Args:
            user_id: User ID
            email: User email
            ip_address: Request IP address
            user_agent: Request user agent
        """
        self._log_event(
            AuditEventType.TOKEN_REFRESHED,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            user_agent=user_agent
        )

    def log_token_revoked(
        self,
        token_id: str,
        user_id: Optional[str] = None,
        revoked_by: Optional[str] = None,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """
        Log token revocation event.

        Args:
            token_id: Token JTI
            user_id: User ID of token owner
            revoked_by: User ID of admin who revoked
            reason: Revocation reason
            ip_address: Request IP address
        """
        self._log_event(
            AuditEventType.TOKEN_REVOKED,
            user_id=user_id,
            ip_address=ip_address,
            additional_data={
                "token_id": token_id,
                "revoked_by": revoked_by,
                "reason": reason
            }
        )

    def log_account_locked(
        self,
        user_id: str,
        email: str,
        reason: str,
        ip_address: Optional[str] = None
    ):
        """
        Log account lock event.

        Args:
            user_id: User ID
            email: User email
            reason: Lock reason
            ip_address: Request IP address
        """
        self._log_event(
            AuditEventType.ACCOUNT_LOCKED,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            additional_data={"reason": reason}
        )

    def log_account_unlocked(
        self,
        user_id: str,
        email: str,
        unlocked_by: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """
        Log account unlock event.

        Args:
            user_id: User ID
            email: User email
            unlocked_by: User ID of admin who unlocked
            ip_address: Request IP address
        """
        self._log_event(
            AuditEventType.ACCOUNT_UNLOCKED,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            additional_data={"unlocked_by": unlocked_by}
        )
