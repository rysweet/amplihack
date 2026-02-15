#!/usr/bin/env python3
"""Example demonstrating secure memory usage with capability-based access control.

This example shows:
1. Creating agent capabilities
2. Setting up secure memory backend
3. Automatic credential scrubbing
4. Permission enforcement
5. Query validation
"""

from pathlib import Path

from amplihack_memory import (
    AgentCapabilities,
    CredentialScrubber,
    Experience,
    ExperienceStore,
    ExperienceType,
    QueryCostExceededError,
    QueryValidator,
    ScopeLevel,
    SecureMemoryBackend,
    SecurityViolationError,
)


def example_basic_secure_store():
    """Example 1: Basic secure store with capability enforcement."""
    print("=" * 60)
    print("Example 1: Basic Secure Store")
    print("=" * 60)

    # Define restricted capabilities for a worker agent
    worker_caps = AgentCapabilities(
        scope=ScopeLevel.SESSION_ONLY,
        allowed_experience_types=[ExperienceType.SUCCESS, ExperienceType.FAILURE],
        max_query_cost=50,
        can_access_patterns=False,
        memory_quota_mb=10,
    )

    # Create secure store
    store = ExperienceStore("worker_agent", storage_path=Path("/tmp/secure_memory"))
    secure_store = SecureMemoryBackend(store, worker_caps)

    # Store allowed experience
    try:
        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Completed task successfully",
            outcome="All validation checks passed",
            confidence=0.9,
        )
        exp_id = secure_store.add_experience(exp)
        print(f"✓ Stored SUCCESS experience: {exp_id}")
    except SecurityViolationError as e:
        print(f"✗ Security violation: {e}")

    # Try to store disallowed experience type
    try:
        pattern_exp = Experience(
            experience_type=ExperienceType.PATTERN,
            context="Observed recurring pattern",
            outcome="Pattern details here",
            confidence=0.8,
        )
        secure_store.add_experience(pattern_exp)
        print("✗ Should have blocked PATTERN experience!")
    except SecurityViolationError as e:
        print(f"✓ Correctly blocked PATTERN experience: {e}")

    print()


def example_credential_scrubbing():
    """Example 2: Automatic credential scrubbing."""
    print("=" * 60)
    print("Example 2: Automatic Credential Scrubbing")
    print("=" * 60)

    # Create scrubber
    scrubber = CredentialScrubber()

    # Example with credentials
    exp_with_creds = Experience(
        experience_type=ExperienceType.SUCCESS,
        context="Connected to API using key: sk-1234567890abcdefghijklmnopqrstuvwxyz",
        outcome="Successfully authenticated and retrieved data",
        confidence=0.95,
    )

    print("Original context:")
    print(f"  {exp_with_creds.context}")

    # Scrub credentials
    scrubbed_exp, was_modified = scrubber.scrub_experience(exp_with_creds)

    print("\nScrubbed context:")
    print(f"  {scrubbed_exp.context}")
    print(f"  Was modified: {was_modified}")
    print(f"  Tags: {scrubbed_exp.tags}")

    # Check if text contains credentials
    test_texts = [
        "Normal log message",
        "API key: sk-abc123def456ghi789",
        "password=secret123",
    ]

    print("\nCredential detection:")
    for text in test_texts:
        has_creds = scrubber.contains_credentials(text)
        status = "✗ HAS CREDENTIALS" if has_creds else "✓ CLEAN"
        print(f"  {status}: {text}")

    print()


def example_integrated_secure_flow():
    """Example 3: Full integrated secure flow."""
    print("=" * 60)
    print("Example 3: Integrated Secure Flow")
    print("=" * 60)

    # Define capabilities
    caps = AgentCapabilities(
        scope=ScopeLevel.SESSION_ONLY,
        allowed_experience_types=[ExperienceType.SUCCESS, ExperienceType.FAILURE],
        max_query_cost=50,
        can_access_patterns=False,
        memory_quota_mb=10,
    )

    # Create secure store
    store = ExperienceStore("integrated_agent", storage_path=Path("/tmp/secure_memory"))
    secure_store = SecureMemoryBackend(store, caps)

    # Store experience with credentials (will be auto-scrubbed)
    exp = Experience(
        experience_type=ExperienceType.SUCCESS,
        context="Deployed app using AWS key AKIAIOSFODNN7EXAMPLE",
        outcome="Deployment successful",
        confidence=0.9,
    )

    print("Storing experience with AWS key...")
    exp_id = secure_store.add_experience(exp)
    print(f"✓ Stored as: {exp_id}")

    # Retrieve and verify scrubbing
    results = secure_store.search(query="Deployed", limit=1)
    if results:
        retrieved = results[0]
        print(f"\nRetrieved context: {retrieved.context}")
        print(f"Credentials scrubbed: {'AKIAIOSFODNN7EXAMPLE' not in retrieved.context}")
        print(f"Tags: {retrieved.tags}")

    # Try searching for disallowed experience type
    print("\nTrying to search for PATTERN experiences...")
    try:
        secure_store.search(query="test", experience_type=ExperienceType.PATTERN)
        print("✗ Should have blocked PATTERN search!")
    except SecurityViolationError as e:
        print(f"✓ Correctly blocked: {e}")

    print()


def example_query_validation():
    """Example 4: Query cost validation."""
    print("=" * 60)
    print("Example 4: Query Validation")
    print("=" * 60)

    validator = QueryValidator()

    # Test queries with different costs
    queries = [
        ("SELECT * FROM experiences LIMIT 10", 50),
        ("SELECT * FROM experiences", 10),  # No LIMIT - expensive
        (
            "SELECT * FROM experiences e JOIN other o ON e.id = o.id LIMIT 10",
            100,
        ),
    ]

    for sql, max_cost in queries:
        cost = validator.estimate_cost(sql)
        print(f"\nQuery: {sql[:50]}...")
        print(f"  Estimated cost: {cost}")
        print(f"  Max allowed: {max_cost}")

        try:
            validator.validate_query(sql, max_cost)
            print(f"  ✓ ALLOWED (cost {cost} <= {max_cost})")
        except QueryCostExceededError as e:
            print(f"  ✗ BLOCKED: {e}")

    # Test safety validation
    print("\nSafety checks:")
    unsafe_queries = [
        "SELECT * FROM experiences LIMIT 10",
        "DELETE FROM experiences",
        "UPDATE experiences SET confidence = 1.0",
    ]

    for sql in unsafe_queries:
        is_safe = validator.is_safe_query(sql)
        status = "✓ SAFE" if is_safe else "✗ UNSAFE"
        print(f"  {status}: {sql}")

    print()


def example_capability_profiles():
    """Example 5: Different capability profiles for different agent roles."""
    print("=" * 60)
    print("Example 5: Capability Profiles")
    print("=" * 60)

    # Restricted worker agent
    worker_caps = AgentCapabilities(
        scope=ScopeLevel.SESSION_ONLY,
        allowed_experience_types=[ExperienceType.SUCCESS, ExperienceType.FAILURE],
        max_query_cost=30,
        can_access_patterns=False,
        memory_quota_mb=10,
    )

    # Standard agent with pattern access
    standard_caps = AgentCapabilities(
        scope=ScopeLevel.CROSS_SESSION_READ,
        allowed_experience_types=[
            ExperienceType.SUCCESS,
            ExperienceType.FAILURE,
            ExperienceType.INSIGHT,
        ],
        max_query_cost=100,
        can_access_patterns=True,
        memory_quota_mb=50,
    )

    # Privileged admin agent
    admin_caps = AgentCapabilities(
        scope=ScopeLevel.GLOBAL_WRITE,
        allowed_experience_types=[],  # All types allowed
        max_query_cost=1000,
        can_access_patterns=True,
        memory_quota_mb=500,
    )

    profiles = [
        ("Worker", worker_caps),
        ("Standard", standard_caps),
        ("Admin", admin_caps),
    ]

    print("Capability Profiles:")
    print()

    for name, caps in profiles:
        print(f"{name} Agent:")
        print(f"  Scope: {caps.scope.value}")
        print(f"  Experience types: {[t.value for t in caps.allowed_experience_types] or 'ALL'}")
        print(f"  Max query cost: {caps.max_query_cost}")
        print(f"  Pattern access: {caps.can_access_patterns}")
        print(f"  Memory quota: {caps.memory_quota_mb}MB")
        print()


def main():
    """Run all examples."""
    print("\n")
    print("*" * 60)
    print("SECURE MEMORY USAGE EXAMPLES")
    print("*" * 60)
    print()

    example_basic_secure_store()
    example_credential_scrubbing()
    example_integrated_secure_flow()
    example_query_validation()
    example_capability_profiles()

    print("*" * 60)
    print("All examples completed!")
    print("*" * 60)
    print()


if __name__ == "__main__":
    main()
