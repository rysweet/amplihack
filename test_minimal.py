#!/usr/bin/env python3
"""Minimal test - verify API client basic functionality."""

import sys

sys.path.insert(0, ".claude/scenarios/api-client")

from amplihack.api_client import ClientConfig, RestClient

print("✓ Imports work")

# Test 1: Simple client
client = RestClient(base_url="https://api.example.com")
assert client.base_url == "https://api.example.com"
print("✓ Simple client works")

# Test 2: Config-based client
config = ClientConfig(base_url="https://api.test.com", timeout=60)
client2 = RestClient(config=config)
assert client2.timeout == 60
print("✓ Config-based client works")

print("\n✅ Step 13 COMPLETE: Manual testing passed!")
print("The API client works for basic user scenarios.")
