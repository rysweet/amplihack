"""
Custom exceptions for authentication module.
Following ruthless simplicity - each exception has a clear purpose.
"""


class AuthenticationError(Exception):
    """Base exception for authentication errors."""
    pass


class InvalidCredentialsError(AuthenticationError):
    """Raised when login credentials are invalid."""
    def __init__(self, message="Invalid email or password"):
        super().__init__(message)


class AccountLockedError(AuthenticationError):
    """Raised when account is locked due to failed attempts."""
    def __init__(self, message="Account is locked due to too many failed attempts"):
        super().__init__(message)


class AccountNotActiveError(AuthenticationError):
    """Raised when account is not active."""
    def __init__(self, message="Account is not active"):
        super().__init__(message)


class TooManyFailedAttemptsError(AuthenticationError):
    """Raised when too many failed login attempts."""
    def __init__(self, message="Too many failed login attempts"):
        super().__init__(message)


class TokenError(Exception):
    """Base exception for token-related errors."""
    pass


class TokenExpiredError(TokenError):
    """Raised when token has expired."""
    def __init__(self, message="Token has expired"):
        super().__init__(message)


class TokenInvalidError(TokenError):
    """Raised when token is invalid or malformed."""
    def __init__(self, message="Invalid or malformed token"):
        super().__init__(message)


class TokenBlacklistedError(TokenError):
    """Raised when token has been blacklisted."""
    def __init__(self, message="Token has been revoked"):
        super().__init__(message)


class UserError(Exception):
    """Base exception for user-related errors."""
    pass


class UserAlreadyExistsError(UserError):
    """Raised when user already exists."""
    def __init__(self, message="User with this email already exists"):
        super().__init__(message)


class UserNotFoundError(UserError):
    """Raised when user is not found."""
    def __init__(self, message="User not found"):
        super().__init__(message)


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded."""
    def __init__(self, retry_after: int, message="Rate limit exceeded"):
        self.retry_after = retry_after
        super().__init__(message)


class InsufficientPermissionsError(Exception):
    """Raised when user lacks required permissions."""
    def __init__(self, message="Insufficient permissions"):
        super().__init__(message)
