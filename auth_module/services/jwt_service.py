"""
JWT service for token generation and validation.
Uses RSA-256 algorithm for signing.
"""

import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import uuid
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


class JWTService:
    """JWT token management service."""

    ALGORITHM = "RS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 15
    REFRESH_TOKEN_EXPIRE_DAYS = 7

    def __init__(self, private_key_path: str, public_key_path: str):
        """
        Initialize JWT service with RSA keys.

        Args:
            private_key_path: Path to RSA private key (PEM format)
            public_key_path: Path to RSA public key (PEM format)
        """
        self.private_key = self._load_private_key(private_key_path)
        self.public_key = self._load_public_key(public_key_path)

    @staticmethod
    def _load_private_key(path: str) -> str:
        """Load RSA private key from file."""
        with open(path, 'rb') as key_file:
            return key_file.read()

    @staticmethod
    def _load_public_key(path: str) -> str:
        """Load RSA public key from file."""
        with open(path, 'rb') as key_file:
            return key_file.read()

    def create_access_token(
        self,
        user_id: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> tuple[str, datetime, str]:
        """
        Create JWT access token.

        Args:
            user_id: User identifier
            additional_claims: Extra claims to include

        Returns:
            Tuple of (token, expires_at, token_id)
        """
        token_id = str(uuid.uuid4())
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)

        payload = {
            "sub": user_id,
            "iat": now,
            "exp": expires_at,
            "jti": token_id,
            "type": "access"
        }

        if additional_claims:
            payload.update(additional_claims)

        token = jwt.encode(
            payload,
            self.private_key,
            algorithm=self.ALGORITHM
        )

        return token, expires_at, token_id

    def create_refresh_token(
        self,
        user_id: str
    ) -> tuple[str, datetime, str]:
        """
        Create JWT refresh token.

        Args:
            user_id: User identifier

        Returns:
            Tuple of (token, expires_at, token_id)
        """
        token_id = str(uuid.uuid4())
        now = datetime.utcnow()
        expires_at = now + timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)

        payload = {
            "sub": user_id,
            "iat": now,
            "exp": expires_at,
            "jti": token_id,
            "type": "refresh"
        }

        token = jwt.encode(
            payload,
            self.private_key,
            algorithm=self.ALGORITHM
        )

        return token, expires_at, token_id

    def verify_token(
        self,
        token: str,
        token_type: str = "access"
    ) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token string
            token_type: Expected token type

        Returns:
            Decoded payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.ALGORITHM]
            )

            # Verify token type
            if payload.get("type") != token_type:
                return None

            return payload

        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def get_token_info(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Get token information without full validation.

        Args:
            token: JWT token string

        Returns:
            Token info or None if invalid
        """
        try:
            # Decode without verification for info extraction
            payload = jwt.decode(
                token,
                options={"verify_signature": False}
            )

            return {
                "user_id": payload.get("sub"),
                "token_id": payload.get("jti"),
                "issued_at": datetime.fromtimestamp(payload.get("iat", 0)),
                "expires_at": datetime.fromtimestamp(payload.get("exp", 0)),
                "type": payload.get("type")
            }

        except jwt.DecodeError:
            return None

    @staticmethod
    def generate_rsa_keypair() -> tuple[str, str]:
        """
        Generate new RSA key pair for JWT signing.

        Returns:
            Tuple of (private_key_pem, public_key_pem)
        """
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
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

        return private_pem.decode('utf-8'), public_pem.decode('utf-8')