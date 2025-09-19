#!/usr/bin/env python3
"""Example demonstrating context manager usage with ProxyManager."""

from pathlib import Path

from amplihack.proxy.config import ProxyConfig
from amplihack.proxy.manager import ProxyManager


def demo_context_manager():
    """Demonstrate using ProxyManager as a context manager."""

    # Load proxy configuration
    config_path = Path("azure.env")
    proxy_config = ProxyConfig(config_path)

    # Use context manager for automatic cleanup
    with ProxyManager(proxy_config) as proxy:
        print(f"Proxy running at: {proxy.get_proxy_url()}")

        # Your code here - proxy is automatically started
        # and will be stopped when exiting the context

        # Check if proxy is running
        if proxy.is_running():
            print("Proxy is active and ready")

        # Do work with the proxy...
        # The proxy will automatically stop when we exit this block

    print("Proxy has been automatically stopped")


def demo_traditional_usage():
    """Demonstrate traditional start/stop usage."""

    config_path = Path("azure.env")
    proxy_config = ProxyConfig(config_path)
    proxy_manager = ProxyManager(proxy_config)

    try:
        # Start proxy
        if proxy_manager.start_proxy():
            print(f"Proxy started at: {proxy_manager.get_proxy_url()}")

            # Do work with proxy...

        else:
            print("Failed to start proxy")
    finally:
        # Always clean up
        proxy_manager.stop_proxy()
        print("Proxy stopped")


if __name__ == "__main__":
    print("Context Manager Usage:")
    print("-" * 40)
    demo_context_manager()

    print("\n\nTraditional Usage:")
    print("-" * 40)
    demo_traditional_usage()
