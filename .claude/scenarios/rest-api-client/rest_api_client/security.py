"""Security features for REST API Client including SSRF protection.

This module provides security features to protect against common
vulnerabilities like Server-Side Request Forgery (SSRF).
"""

import ipaddress
import socket
from urllib.parse import urlparse

from .exceptions import SecurityError


class SSRFProtector:
    """Protects against Server-Side Request Forgery attacks.

    Validates URLs to prevent requests to internal/private networks
    and provides allowlist/blocklist functionality.
    """

    # Private IP networks that should be blocked by default
    BLOCKED_NETWORKS = [
        ipaddress.ip_network("127.0.0.0/8"),  # Loopback
        ipaddress.ip_network("10.0.0.0/8"),  # Private Class A
        ipaddress.ip_network("172.16.0.0/12"),  # Private Class B
        ipaddress.ip_network("192.168.0.0/16"),  # Private Class C
        ipaddress.ip_network("169.254.0.0/16"),  # Link-local
        ipaddress.ip_network("0.0.0.0/8"),  # This network
        ipaddress.ip_network("100.64.0.0/10"),  # Shared address space
        ipaddress.ip_network("224.0.0.0/4"),  # Multicast
        ipaddress.ip_network("255.255.255.255/32"),  # Broadcast
    ]

    # IPv6 networks to block
    BLOCKED_NETWORKS_IPV6 = [
        ipaddress.ip_network("::1/128"),  # Loopback
        ipaddress.ip_network("fc00::/7"),  # Unique local
        ipaddress.ip_network("fe80::/10"),  # Link-local
        ipaddress.ip_network("ff00::/8"),  # Multicast
        ipaddress.ip_network("::/128"),  # Unspecified
    ]

    # Hostnames that are always blocked
    BLOCKED_HOSTNAMES = {
        "localhost",
        "localhost.localdomain",
        "localhost4",
        "localhost6",
        "localhost.localhost",
        "local",
    }

    def __init__(
        self,
        allowed_hosts: list[str] | None = None,
        additional_blocked_hosts: list[str] | None = None,
        allow_private_networks: bool = False,
    ):
        """Initialize SSRF protector.

        Args:
            allowed_hosts: Explicit allowlist of hosts/IPs (overrides blocks)
            additional_blocked_hosts: Additional hosts to block
            allow_private_networks: Whether to allow private network access
        """
        self.allowed_hosts = set(allowed_hosts or [])
        self.additional_blocked_hosts = set(additional_blocked_hosts or [])
        self.allow_private_networks = allow_private_networks

        # Combine all blocked networks
        self.blocked_networks = []
        if not allow_private_networks:
            self.blocked_networks.extend(self.BLOCKED_NETWORKS)
            self.blocked_networks.extend(self.BLOCKED_NETWORKS_IPV6)

    def is_safe_url(self, url: str) -> bool:
        """Check if a URL is safe from SSRF attacks.

        Args:
            url: URL to validate

        Returns:
            True if URL is safe, False otherwise
        """
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname

            if not hostname:
                return False

            # Check explicit allowlist first
            if hostname in self.allowed_hosts:
                return True

            # Check blocked hostnames
            if hostname.lower() in self.BLOCKED_HOSTNAMES:
                return False

            # Check additional blocked hosts
            if hostname.lower() in self.additional_blocked_hosts:
                return False

            # Check if hostname is already an IP
            try:
                ip_obj = ipaddress.ip_address(hostname)
                return self._is_safe_ip(ip_obj)
            except ValueError:
                # Not an IP, need to resolve
                pass

            # Resolve hostname to IP
            try:
                # Get all IPs for the hostname
                addr_info = socket.getaddrinfo(hostname, None)
                ips = set()

                for info in addr_info:
                    ip_str = info[4][0]
                    ips.add(ip_str)

                # Check if any resolved IP is unsafe
                for ip_str in ips:
                    try:
                        ip_obj = ipaddress.ip_address(ip_str)
                        if not self._is_safe_ip(ip_obj):
                            return False
                    except ValueError:
                        # Invalid IP format, block to be safe
                        return False

                return True

            except socket.gaierror:
                # Cannot resolve hostname, block to be safe
                return False

        except Exception:
            # Any error in validation means we block the request
            return False

    def _is_safe_ip(self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """Check if an IP address is safe.

        Args:
            ip: IP address object

        Returns:
            True if IP is safe, False otherwise
        """
        # Check if IP is in allowed hosts
        if str(ip) in self.allowed_hosts:
            return True

        # Check against blocked networks
        for network in self.blocked_networks:
            if ip in network:
                return False

        return True

    def validate_url(self, url: str) -> None:
        """Validate a URL and raise exception if unsafe.

        Args:
            url: URL to validate

        Raises:
            SecurityError: If URL is not safe
        """
        if not self.is_safe_url(url):
            raise SecurityError(
                f"URL blocked for security reasons: {url}. "
                "This may be an attempt to access internal resources (SSRF)."
            )
