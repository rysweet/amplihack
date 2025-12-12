"""
Azure Service Principal authentication for remote execution.

Provides secure authentication using Service Principal credentials from environment
variables or .env files. Supports debug mode for troubleshooting.

Example:
    from .claude.tools.amplihack.remote.auth import get_azure_auth

    credential, subscription_id, resource_group = get_azure_auth()
    # Use credential with Azure SDK clients
"""

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from azure.identity import ClientSecretCredential


@dataclass
class AzureCredentials:
    """Container for Azure Service Principal credentials.

    Attributes:
        tenant_id: Azure AD tenant ID
        client_id: Service Principal application (client) ID
        client_secret: Service Principal secret value
        subscription_id: Target Azure subscription ID
        resource_group: Optional resource group name for operations
    """

    tenant_id: str
    client_id: str
    client_secret: str
    subscription_id: str
    resource_group: str | None = None

    def __post_init__(self):
        """Validate that all required credentials are provided."""
        if not all([self.tenant_id, self.client_id, self.client_secret, self.subscription_id]):
            missing = [
                name
                for name, value in [
                    ("tenant_id", self.tenant_id),
                    ("client_id", self.client_id),
                    ("client_secret", self.client_secret),
                    ("subscription_id", self.subscription_id),
                ]
                if not value
            ]
            raise ValueError(f"Missing required credentials: {', '.join(missing)}")


class AzureAuthenticator:
    """Handles Azure authentication with Service Principal credentials.

    Searches for credentials in the following order:
    1. Environment variables (AZURE_TENANT_ID, etc.)
    2. .env file in current directory
    3. .env file in project root

    Example:
        auth = AzureAuthenticator(debug=True)
        credential = auth.get_credential()
        subscription_id = auth.get_subscription_id()
    """

    def __init__(self, env_file: Path | None = None, debug: bool = False):
        """Initialize authenticator.

        Args:
            env_file: Optional path to specific .env file
            debug: Enable debug logging to stderr
        """
        self.env_file = env_file
        self.debug = debug
        self._credentials: AzureCredentials | None = None

    def _log_debug(self, message: str):
        """Log debug message to stderr if debug mode is enabled."""
        if self.debug:
            print(f"[DEBUG] {message}", file=sys.stderr)

    def _find_env_file(self) -> Path | None:
        """Find .env file by searching current directory and project root.

        Returns:
            Path to .env file if found, None otherwise
        """
        search_paths = [
            Path.cwd() / ".env",
            Path(__file__).parent.parent.parent.parent.parent / ".env",  # Project root
        ]

        for path in search_paths:
            if path.exists():
                self._log_debug(f"Found .env file: {path}")
                return path

        self._log_debug("No .env file found")
        return None

    def _load_env_file(self, env_path: Path):
        """Load environment variables from .env file.

        Args:
            env_path: Path to .env file to load
        """
        self._log_debug(f"Loading environment from: {env_path}")

        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")

                    # Only set if not already in environment
                    if key not in os.environ:
                        os.environ[key] = value
                        self._log_debug(f"Loaded {key} from .env")

    def _load_credentials(self) -> AzureCredentials:
        """Load credentials from environment or .env file.

        Returns:
            AzureCredentials object with loaded credentials

        Raises:
            ValueError: If required credentials are missing
        """
        # Load .env file if specified or found
        if self.env_file:
            if not self.env_file.exists():
                raise FileNotFoundError(f".env file not found: {self.env_file}")
            self._load_env_file(self.env_file)
        else:
            env_path = self._find_env_file()
            if env_path:
                self._load_env_file(env_path)

        # Get credentials from environment
        tenant_id = os.getenv("AZURE_TENANT_ID", "")
        client_id = os.getenv("AZURE_CLIENT_ID", "")
        client_secret = os.getenv("AZURE_CLIENT_SECRET", "")
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID", "")
        resource_group = os.getenv("AZURE_RESOURCE_GROUP")

        self._log_debug(f"Tenant ID: {'✓' if tenant_id else '✗'}")
        self._log_debug(f"Client ID: {'✓' if client_id else '✗'}")
        self._log_debug(f"Client Secret: {'✓' if client_secret else '✗'}")
        self._log_debug(f"Subscription ID: {'✓' if subscription_id else '✗'}")
        self._log_debug(f"Resource Group: {resource_group or '(not set)'}")

        return AzureCredentials(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
            subscription_id=subscription_id,
            resource_group=resource_group,
        )

    def get_credentials(self) -> AzureCredentials:
        """Get Azure credentials, loading them if not already loaded.

        Returns:
            AzureCredentials object
        """
        if not self._credentials:
            self._credentials = self._load_credentials()
        return self._credentials

    def get_credential(self) -> ClientSecretCredential:
        """Create Azure SDK credential object.

        Returns:
            ClientSecretCredential for use with Azure SDK clients
        """
        creds = self.get_credentials()

        self._log_debug("Creating ClientSecretCredential")
        return ClientSecretCredential(
            tenant_id=creds.tenant_id,
            client_id=creds.client_id,
            client_secret=creds.client_secret,
        )

    def get_subscription_id(self) -> str:
        """Get Azure subscription ID.

        Returns:
            Subscription ID string
        """
        return self.get_credentials().subscription_id

    def get_resource_group(self) -> str | None:
        """Get configured resource group name.

        Returns:
            Resource group name if configured, None otherwise
        """
        return self.get_credentials().resource_group


def get_azure_auth(
    env_file: Path | None = None, debug: bool = False
) -> tuple[ClientSecretCredential, str, str | None]:
    """Convenience function to get Azure authentication in one call.

    Args:
        env_file: Optional path to specific .env file
        debug: Enable debug logging

    Returns:
        Tuple of (credential, subscription_id, resource_group)

    Example:
        credential, sub_id, rg = get_azure_auth(debug=True)

        # Use with Azure SDK
        from azure.mgmt.compute import ComputeManagementClient
        compute_client = ComputeManagementClient(credential, sub_id)
    """
    auth = AzureAuthenticator(env_file=env_file, debug=debug)
    credential = auth.get_credential()
    subscription_id = auth.get_subscription_id()
    resource_group = auth.get_resource_group()

    return credential, subscription_id, resource_group
