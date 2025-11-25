"""
Optimized query patterns for JWT authentication system.
Following the principle: measure first, optimize only proven bottlenecks.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy import and_, or_, func, text
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy.sql import exists

from .models import User, RefreshToken, PasswordResetToken, AuditLog, AuditEventType


class UserQueries:
    """Optimized queries for user operations"""

    @staticmethod
    def get_by_email(db: Session, email: str, include_deleted: bool = False) -> Optional[User]:
        """
        Get user by email with optimized index usage.
        Uses idx_users_email partial index.
        """
        query = db.query(User).filter(User.email == email)
        if not include_deleted:
            query = query.filter(User.deleted_at.is_(None))
        return query.first()

    @staticmethod
    def get_by_username(db: Session, username: str, include_deleted: bool = False) -> Optional[User]:
        """
        Get user by username with optimized index usage.
        Uses idx_users_username partial index.
        """
        if not username:
            return None
        query = db.query(User).filter(User.username == username)
        if not include_deleted:
            query = query.filter(User.deleted_at.is_(None))
        return query.first()

    @staticmethod
    def get_active_user(db: Session, user_id: UUID) -> Optional[User]:
        """
        Get active user by ID, checking all status flags.
        Most common query - optimized for speed.
        """
        return db.query(User).filter(
            and_(
                User.id == user_id,
                User.is_active == True,
                User.deleted_at.is_(None)
            )
        ).first()

    @staticmethod
    def get_with_tokens(db: Session, user_id: UUID) -> Optional[User]:
        """
        Get user with refresh tokens preloaded.
        Avoids N+1 query problem.
        """
        return db.query(User)\
            .options(selectinload(User.refresh_tokens))\
            .filter(User.id == user_id)\
            .first()

    @staticmethod
    def search_users(
        db: Session,
        search_term: Optional[str] = None,
        role: Optional[str] = None,
        is_verified: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[User]:
        """
        Search users with filters.
        Uses indexes efficiently.
        """
        query = db.query(User).filter(User.deleted_at.is_(None))

        if search_term:
            # Use OR for email/username search
            query = query.filter(
                or_(
                    User.email.ilike(f"%{search_term}%"),
                    User.username.ilike(f"%{search_term}%")
                )
            )

        if role:
            query = query.filter(User.role == role)

        if is_verified is not None:
            query = query.filter(User.is_verified == is_verified)

        # Use index on created_at for sorting
        return query.order_by(User.created_at.desc())\
            .limit(limit)\
            .offset(offset)\
            .all()

    @staticmethod
    def count_by_role(db: Session) -> Dict[str, int]:
        """
        Get user count by role.
        Single query with GROUP BY.
        """
        results = db.query(
            User.role,
            func.count(User.id).label('count')
        ).filter(
            User.deleted_at.is_(None)
        ).group_by(User.role).all()

        return {role: count for role, count in results}

    @staticmethod
    def bulk_update_inactive(db: Session, days: int = 90) -> int:
        """
        Mark users as inactive who haven't logged in for N days.
        Bulk update for efficiency.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        result = db.query(User).filter(
            and_(
                User.last_login_at < cutoff_date,
                User.is_active == True,
                User.deleted_at.is_(None)
            )
        ).update(
            {"is_active": False},
            synchronize_session=False
        )

        db.commit()
        return result


class TokenQueries:
    """Optimized queries for token operations"""

    @staticmethod
    def get_valid_refresh_token(db: Session, token_hash: str) -> Optional[RefreshToken]:
        """
        Get valid refresh token by hash.
        Uses indexes and checks validity inline.
        """
        return db.query(RefreshToken).filter(
            and_(
                RefreshToken.token_hash == token_hash,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.utcnow()
            )
        ).first()

    @staticmethod
    def get_user_refresh_tokens(
        db: Session,
        user_id: UUID,
        only_valid: bool = True
    ) -> List[RefreshToken]:
        """
        Get all refresh tokens for a user.
        Optionally filter to only valid tokens.
        """
        query = db.query(RefreshToken).filter(RefreshToken.user_id == user_id)

        if only_valid:
            query = query.filter(
                and_(
                    RefreshToken.revoked_at.is_(None),
                    RefreshToken.expires_at > datetime.utcnow()
                )
            )

        return query.order_by(RefreshToken.created_at.desc()).all()

    @staticmethod
    def revoke_all_user_tokens(db: Session, user_id: UUID, reason: str = "logout") -> int:
        """
        Revoke all refresh tokens for a user.
        Bulk update for efficiency.
        """
        result = db.query(RefreshToken).filter(
            and_(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None)
            )
        ).update(
            {
                "revoked_at": datetime.utcnow(),
                "revoked_reason": reason
            },
            synchronize_session=False
        )

        db.commit()
        return result

    @staticmethod
    def cleanup_expired_tokens(db: Session) -> int:
        """
        Delete expired tokens older than 30 days.
        Run as periodic maintenance task.
        """
        cutoff_date = datetime.utcnow() - timedelta(days=30)

        # Delete expired refresh tokens
        refresh_deleted = db.query(RefreshToken).filter(
            RefreshToken.expires_at < cutoff_date
        ).delete(synchronize_session=False)

        # Delete used password reset tokens
        reset_deleted = db.query(PasswordResetToken).filter(
            or_(
                PasswordResetToken.used_at.isnot(None),
                PasswordResetToken.expires_at < cutoff_date
            )
        ).delete(synchronize_session=False)

        db.commit()
        return refresh_deleted + reset_deleted


class AuditQueries:
    """Optimized queries for audit logs"""

    @staticmethod
    def get_user_events(
        db: Session,
        user_id: UUID,
        event_types: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """
        Get audit events for a user with filters.
        Uses indexes on user_id and event_type.
        """
        query = db.query(AuditLog).filter(AuditLog.user_id == user_id)

        if event_types:
            query = query.filter(AuditLog.event_type.in_(event_types))

        if start_date:
            query = query.filter(AuditLog.created_at >= start_date)

        if end_date:
            query = query.filter(AuditLog.created_at <= end_date)

        return query.order_by(AuditLog.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_failed_login_attempts(
        db: Session,
        email: str,
        window_minutes: int = 15
    ) -> int:
        """
        Count failed login attempts in time window.
        Used for rate limiting.
        """
        since = datetime.utcnow() - timedelta(minutes=window_minutes)

        # First get user_id from email
        user = UserQueries.get_by_email(db, email, include_deleted=True)
        if not user:
            return 0

        return db.query(func.count(AuditLog.id)).filter(
            and_(
                AuditLog.user_id == user.id,
                AuditLog.event_type == AuditEventType.LOGIN_FAILED,
                AuditLog.created_at >= since
            )
        ).scalar() or 0

    @staticmethod
    def get_security_events(
        db: Session,
        hours: int = 24,
        limit: int = 1000
    ) -> List[AuditLog]:
        """
        Get recent security-related events for monitoring.
        """
        since = datetime.utcnow() - timedelta(hours=hours)

        security_events = [
            AuditEventType.LOGIN_FAILED,
            AuditEventType.ACCOUNT_LOCKED,
            AuditEventType.PASSWORD_RESET_REQUEST,
            AuditEventType.PERMISSION_CHANGE,
            AuditEventType.ROLE_CHANGE,
            AuditEventType.TOKEN_REVOKED
        ]

        return db.query(AuditLog).filter(
            and_(
                AuditLog.event_type.in_(security_events),
                AuditLog.created_at >= since
            )
        ).order_by(AuditLog.created_at.desc()).limit(limit).all()


class PerformanceQueries:
    """
    Query patterns for performance monitoring.
    Use these to identify bottlenecks before optimization.
    """

    @staticmethod
    def explain_query(db: Session, query) -> str:
        """
        Get EXPLAIN ANALYZE output for a query.
        Use to identify slow queries.
        """
        compiled = query.statement.compile(
            compile_kwargs={"literal_binds": True}
        )
        explain_query = f"EXPLAIN ANALYZE {compiled}"
        result = db.execute(text(explain_query))
        return '\n'.join([row[0] for row in result])

    @staticmethod
    def get_index_usage(db: Session) -> List[Dict[str, Any]]:
        """
        Check index usage statistics.
        Identifies unused indexes and missing indexes.
        """
        query = text("""
            SELECT
                schemaname,
                tablename,
                indexname,
                idx_scan,
                idx_tup_read,
                idx_tup_fetch,
                pg_size_pretty(pg_relation_size(indexrelid)) as index_size
            FROM pg_stat_user_indexes
            WHERE schemaname = 'public'
            ORDER BY idx_scan ASC;
        """)

        result = db.execute(query)
        return [dict(row) for row in result]

    @staticmethod
    def get_slow_queries(db: Session, min_duration_ms: int = 100) -> List[Dict[str, Any]]:
        """
        Get currently running slow queries.
        Requires pg_stat_statements extension.
        """
        query = text("""
            SELECT
                query,
                calls,
                mean_exec_time,
                total_exec_time,
                min_exec_time,
                max_exec_time
            FROM pg_stat_statements
            WHERE mean_exec_time > :min_duration
            ORDER BY mean_exec_time DESC
            LIMIT 20;
        """)

        try:
            result = db.execute(query, {"min_duration": min_duration_ms})
            return [dict(row) for row in result]
        except Exception:
            # pg_stat_statements might not be enabled
            return []

    @staticmethod
    def get_table_sizes(db: Session) -> List[Dict[str, Any]]:
        """
        Get table sizes for capacity planning.
        """
        query = text("""
            SELECT
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                n_tup_ins as rows_inserted,
                n_tup_upd as rows_updated,
                n_tup_del as rows_deleted,
                n_live_tup as live_rows,
                n_dead_tup as dead_rows
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
        """)

        result = db.execute(query)
        return [dict(row) for row in result]


# Query optimization guidelines comment
"""
QUERY OPTIMIZATION GUIDELINES:

1. MEASURE FIRST
   - Use EXPLAIN ANALYZE before optimizing
   - Check actual execution time and row counts
   - Monitor pg_stat_statements for real usage patterns

2. INDEX STRATEGY
   - Already have indexes on foreign keys and WHERE columns
   - Add composite indexes only when queries use multiple columns
   - Use partial indexes for filtered queries (already implemented)
   - Consider BRIN indexes for time-series data if tables grow large

3. OPTIMIZATION PATTERNS
   - Use EXISTS instead of IN for subqueries
   - Batch updates with UPDATE ... FROM
   - Use COPY for bulk inserts
   - Consider materialized views for complex aggregations

4. MONITORING QUERIES TO ADD WHEN NEEDED
   - Connection pool statistics
   - Lock contention analysis
   - Cache hit ratios
   - Vacuum/analyze statistics

5. FUTURE OPTIMIZATIONS (WHEN DATA JUSTIFIES)
   - Partition audit_logs by month if > 10M rows
   - Add read replicas for analytics queries
   - Consider TimescaleDB for audit_logs if time-series heavy
   - Implement query result caching in Redis

Remember: The best optimization is the one you don't need to make.
"""