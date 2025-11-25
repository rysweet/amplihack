"""
JWT Token Service - handles token generation, validation, and management.
Uses RSA-256 for signing with support for key rotation.
"""

import jwt
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from ..config import JWTConfig
from ..exceptions import TokenExpiredError, TokenInvalidError, TokenBlacklistedError
from ..models import TokenPayload


class TokenService:
    """Service for JWT token operations."""

    def __init__(self, config: JWTConfig, blacklist_service=None):
        """
        Initialize token service.

        Args:
            config: JWT configuration
            blacklist_service: Optional blacklist service for revocation
        """
        self.config = config
        self.blacklist_service = blacklist_service
        self._private_key = None
        self._public_key = None

        # Load keys if paths provided
        if config.private_key_path:
            self._private_key = self._load_key(config.private_key_path)
        if config.public_key_path:
            self._public_key = self._load_key(config.public_key_path)

    @staticmethod
    def _load_key(path: str) -> bytes:
        """Load key from file."""
        with open(path, "rb") as f:
            return f.read()

    @staticmethod
    def generate_rsa_keypair(key_size: int = 2048) -> Tuple[str, str]:
        """
        Generate RSA key pair for JWT signing.

        Args:
            key_size: RSA key size in bits (2048 or 4096)

        Returns:
            Tuple of (private_key_pem, public_key_pem)
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
            backend=default_backend()
        )

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        public_key = private_key.public_key()
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        return private_pem.decode("utf-8"), public_pem.decode("utf-8")

    def generate_access_token(
        self,
        user_id: str,
        email: str,
        username: Optional[str] = None,
        roles: Optional[list] = None,
        permissions: Optional[list] = None,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate access token.

        Args:
            user_id: User identifier
            email: User email
            username: Optional username
            roles: User roles
            permissions: User permissions
            additional_claims: Extra claims to include

        Returns:
            JWT access token
        """
        now = datetime.now(timezone.utc)
        exp = now + timedelta(minutes=self.config.access_token_expire_minutes)

        payload = {
            "sub": user_id,
            "email": email,
            "username": username,
            "roles": roles or ["user"],
            "permissions": permissions or [],
            "type": "access",
            "exp": int(exp.timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(uuid.uuid4()),
            "iss": self.config.issuer,
            "aud": self.config.audience,
        }

        if additional_claims:
            payload.update(additional_claims)

        signing_key = self._private_key or self.config.secret_key
        return jwt.encode(payload, signing_key, algorithm=self.config.algorithm)

    def generate_refresh_token(self, user_id: str) -> str:
        """
        Generate refresh token.

        Args:
            user_id: User identifier

        Returns:
            JWT refresh token
        """
        now = datetime.now(timezone.utc)
        exp = now + timedelta(days=self.config.refresh_token_expire_days)

        payload = {
            "sub": user_id,
            "type": "refresh",
            "exp": int(exp.timestamp()),
            "iat": int(now.timestamp()),
            "jti": str(uuid.uuid4()),
            "iss": self.config.issuer,
            "aud": self.config.audience,
        }

        signing_key = self._private_key or self.config.secret_key
        return jwt.encode(payload, signing_key, algorithm=self.config.algorithm)

    def validate_token(
        self,
        token: str,
        token_type: str = "access",
        check_blacklist: bool = True
    ) -> TokenPayload:
        """
        Validate and decode JWT token.

        Args:
            token: JWT token string
            token_type: Expected token type (access/refresh)
            check_blacklist: Whether to check blacklist

        Returns:
            Token payload

        Raises:
            TokenExpiredError: Token has expired
            TokenInvalidError: Token is invalid
            TokenBlacklistedError: Token is blacklisted
        """
        try:
            # Decode token
            verification_key = self._public_key or self.config.secret_key
            payload = jwt.decode(
                token,
                verification_key,
                algorithms=[self.config.algorithm],
                audience=self.config.audience,
                issuer=self.config.issuer,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "require": ["exp", "iat", "jti", "sub"]
                }
            )

            # Verify token type
            if payload.get("type") != token_type:
                raise TokenInvalidError(f"Expected {token_type} token")

            # Check blacklist if service available
            if check_blacklist and self.blacklist_service:
                token_id = payload.get("jti")
                if token_id and self.blacklist_service.is_blacklisted(token_id):
                    raise TokenBlacklistedError()

            # Return payload
            return TokenPayload(
                user_id=payload["sub"],
                email=payload.get("email", ""),
                username=payload.get("username"),
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                token_type=payload.get("type"),
                jti=payload.get("jti"),
                exp=payload.get("exp"),
                iat=payload.get("iat"),
            )

        except jwt.ExpiredSignatureError:
            raise TokenExpiredError()
        except jwt.InvalidTokenError as e:
            raise TokenInvalidError(str(e))
        except Exception as e:
            raise TokenInvalidError(f"Token validation failed: {str(e)}")

    def decode_token_unsafe(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode token without validation (for inspection).

        Args:
            token: JWT token string

        Returns:
            Token payload dict or None
        """
        try:
            return jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False}
            )
        except Exception:
            return None

    def revoke_token(self, token: str):
        """
        Revoke a token by adding to blacklist.

        Args:
            token: JWT token to revoke
        """
        if not self.blacklist_service:
            raise RuntimeError("Blacklist service not configured")

        payload = self.decode_token_unsafe(token)
        if payload:
            token_id = payload.get("jti")
            exp = payload.get("exp")
            if token_id and exp:
                ttl = int(exp - datetime.now(timezone.utc).timestamp())
                if ttl > 0:
                    self.blacklist_service.blacklist_token(token_id, ttl)
