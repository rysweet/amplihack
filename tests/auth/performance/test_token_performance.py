"""
Performance tests for JWT token validation.
These tests ensure token operations meet performance requirements (<50ms).
"""

import pytest
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
import jwt
from typing import List, Dict, Any

# Import the modules to be tested (these don't exist yet - TDD approach)
from src.amplihack.auth.services import TokenService, TokenCache
from src.amplihack.auth.models import User
from src.amplihack.auth.config import JWTConfig


class TestTokenPerformance:
    """Performance tests for token operations."""

    @pytest.fixture
    def jwt_config(self):
        """Create JWT configuration optimized for performance testing."""
        return JWTConfig(
            secret_key="test_secret_key_for_testing_only_123456789",
            algorithm="HS256",
            access_token_expire_minutes=60,
            refresh_token_expire_days=30,
            issuer="amplihack-auth",
            audience="amplihack-api",
            enable_caching=True,
            cache_ttl_seconds=300,
        )

    @pytest.fixture
    def token_service(self, jwt_config):
        """Create a TokenService instance."""
        return TokenService(config=jwt_config)

    @pytest.fixture
    def sample_user(self):
        """Create a sample user."""
        return User(
            id="user_123",
            email="user@example.com",
            username="johndoe",
            roles=["user"],
            permissions=["read:profile", "update:profile"],
        )

    @pytest.fixture
    def sample_tokens(self, token_service, sample_user):
        """Generate sample tokens for testing."""
        return [token_service.generate_access_token(sample_user) for _ in range(100)]

    def measure_operation_time(self, operation, *args, **kwargs):
        """Measure the execution time of an operation."""
        start = time.perf_counter()
        result = operation(*args, **kwargs)
        end = time.perf_counter()
        return (end - start) * 1000, result  # Return time in milliseconds

    def test_token_generation_performance(self, token_service, sample_user):
        """Test that token generation completes within 50ms."""
        times = []

        for _ in range(100):
            duration, _ = self.measure_operation_time(
                token_service.generate_access_token,
                sample_user
            )
            times.append(duration)

        avg_time = statistics.mean(times)
        max_time = max(times)
        p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile

        assert avg_time < 50, f"Average generation time {avg_time:.2f}ms exceeds 50ms"
        assert p95_time < 50, f"95th percentile time {p95_time:.2f}ms exceeds 50ms"
        assert max_time < 100, f"Maximum generation time {max_time:.2f}ms exceeds 100ms"

        print(f"\nToken Generation Performance:")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  95th percentile: {p95_time:.2f}ms")
        print(f"  Maximum: {max_time:.2f}ms")

    def test_token_validation_performance(self, token_service, sample_tokens):
        """Test that token validation completes within 50ms."""
        times = []

        for token in sample_tokens:
            duration, _ = self.measure_operation_time(
                token_service.validate_token,
                token
            )
            times.append(duration)

        avg_time = statistics.mean(times)
        max_time = max(times)
        p95_time = statistics.quantiles(times, n=20)[18]

        assert avg_time < 50, f"Average validation time {avg_time:.2f}ms exceeds 50ms"
        assert p95_time < 50, f"95th percentile time {p95_time:.2f}ms exceeds 50ms"
        assert max_time < 100, f"Maximum validation time {max_time:.2f}ms exceeds 100ms"

        print(f"\nToken Validation Performance:")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  95th percentile: {p95_time:.2f}ms")
        print(f"  Maximum: {max_time:.2f}ms")

    def test_token_validation_with_cache(self, token_service, sample_user):
        """Test that cached token validation is significantly faster."""
        token = token_service.generate_access_token(sample_user)

        # First validation (cache miss)
        first_times = []
        for _ in range(10):
            token_service.clear_cache()  # Ensure cache miss
            duration, _ = self.measure_operation_time(
                token_service.validate_token,
                token
            )
            first_times.append(duration)

        # Second validation (cache hit)
        cached_times = []
        for _ in range(10):
            duration, _ = self.measure_operation_time(
                token_service.validate_token,
                token
            )
            cached_times.append(duration)

        avg_first = statistics.mean(first_times)
        avg_cached = statistics.mean(cached_times)

        # Cached validation should be at least 50% faster
        assert avg_cached < avg_first * 0.5, (
            f"Cached validation ({avg_cached:.2f}ms) not significantly "
            f"faster than uncached ({avg_first:.2f}ms)"
        )

        # Cached validation should be under 10ms
        assert avg_cached < 10, f"Cached validation {avg_cached:.2f}ms exceeds 10ms"

        print(f"\nCache Performance:")
        print(f"  Uncached average: {avg_first:.2f}ms")
        print(f"  Cached average: {avg_cached:.2f}ms")
        print(f"  Speedup: {avg_first / avg_cached:.2f}x")

    def test_concurrent_token_validation(self, token_service, sample_tokens):
        """Test token validation performance under concurrent load."""
        def validate_token(token):
            start = time.perf_counter()
            try:
                token_service.validate_token(token)
                success = True
            except:
                success = False
            end = time.perf_counter()
            return (end - start) * 1000, success

        # Test with different concurrency levels
        for num_workers in [10, 50, 100]:
            times = []
            successes = 0

            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [
                    executor.submit(validate_token, token)
                    for token in sample_tokens[:num_workers]
                ]

                for future in as_completed(futures):
                    duration, success = future.result()
                    times.append(duration)
                    if success:
                        successes += 1

            avg_time = statistics.mean(times)
            max_time = max(times)
            success_rate = (successes / num_workers) * 100

            assert avg_time < 100, (
                f"Average time {avg_time:.2f}ms exceeds 100ms "
                f"with {num_workers} concurrent workers"
            )
            assert success_rate == 100, (
                f"Success rate {success_rate:.1f}% is below 100% "
                f"with {num_workers} concurrent workers"
            )

            print(f"\nConcurrent Validation ({num_workers} workers):")
            print(f"  Average: {avg_time:.2f}ms")
            print(f"  Maximum: {max_time:.2f}ms")
            print(f"  Success rate: {success_rate:.1f}%")

    def test_token_refresh_performance(self, token_service, sample_user):
        """Test that token refresh completes within performance requirements."""
        # Generate initial tokens
        token_pair = token_service.generate_token_pair(sample_user)

        times = []
        for _ in range(50):
            duration, new_pair = self.measure_operation_time(
                token_service.refresh_tokens,
                token_pair.refresh_token
            )
            times.append(duration)
            token_pair = new_pair  # Use new refresh token for next iteration

        avg_time = statistics.mean(times)
        max_time = max(times)
        p95_time = statistics.quantiles(times, n=20)[18]

        assert avg_time < 100, f"Average refresh time {avg_time:.2f}ms exceeds 100ms"
        assert p95_time < 150, f"95th percentile time {p95_time:.2f}ms exceeds 150ms"

        print(f"\nToken Refresh Performance:")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  95th percentile: {p95_time:.2f}ms")
        print(f"  Maximum: {max_time:.2f}ms")

    def test_blacklist_check_performance(self, token_service):
        """Test that blacklist checking doesn't significantly impact performance."""
        # Populate blacklist with many tokens
        blacklist_size = 10000
        for i in range(blacklist_size):
            token_service.blacklist_token(f"jti_{i}", f"user_{i % 100}")

        # Generate test token
        user = User(id="test_user", email="test@example.com")
        token = token_service.generate_access_token(user)

        times = []
        for _ in range(100):
            duration, _ = self.measure_operation_time(
                token_service.validate_token_with_blacklist,
                token
            )
            times.append(duration)

        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]

        assert avg_time < 50, (
            f"Average validation with blacklist {avg_time:.2f}ms exceeds 50ms "
            f"(blacklist size: {blacklist_size})"
        )
        assert p95_time < 75, (
            f"95th percentile with blacklist {p95_time:.2f}ms exceeds 75ms"
        )

        print(f"\nBlacklist Check Performance (size={blacklist_size}):")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  95th percentile: {p95_time:.2f}ms")

    def test_bulk_token_generation(self, token_service):
        """Test performance of bulk token generation."""
        users = [
            User(id=f"user_{i}", email=f"user{i}@example.com")
            for i in range(1000)
        ]

        start = time.perf_counter()
        tokens = token_service.generate_bulk_tokens(users)
        end = time.perf_counter()

        total_time = (end - start) * 1000
        avg_time = total_time / len(users)

        assert len(tokens) == len(users)
        assert avg_time < 10, (
            f"Average time per token {avg_time:.2f}ms exceeds 10ms in bulk generation"
        )
        assert total_time < 30000, (
            f"Total time {total_time:.2f}ms exceeds 30s for 1000 tokens"
        )

        print(f"\nBulk Generation Performance (1000 tokens):")
        print(f"  Total time: {total_time:.2f}ms")
        print(f"  Average per token: {avg_time:.2f}ms")
        print(f"  Tokens per second: {1000 / (total_time / 1000):.0f}")

    def test_memory_usage(self, token_service):
        """Test that token operations don't cause excessive memory usage."""
        import tracemalloc
        import gc

        # Start memory tracking
        gc.collect()
        tracemalloc.start()
        snapshot_start = tracemalloc.take_snapshot()

        # Generate and validate many tokens
        for i in range(1000):
            user = User(id=f"user_{i}", email=f"user{i}@example.com")
            token = token_service.generate_access_token(user)
            token_service.validate_token(token)

        # Take ending snapshot
        snapshot_end = tracemalloc.take_snapshot()
        tracemalloc.stop()

        # Calculate memory difference
        stats = snapshot_end.compare_to(snapshot_start, 'lineno')
        total_memory = sum(stat.size_diff for stat in stats) / 1024 / 1024  # Convert to MB

        assert total_memory < 50, (
            f"Memory usage {total_memory:.2f}MB exceeds 50MB for 1000 token operations"
        )

        print(f"\nMemory Usage (1000 operations):")
        print(f"  Total increase: {total_memory:.2f}MB")
        print(f"  Average per operation: {total_memory * 1024:.2f}KB")

    def test_token_size_optimization(self, token_service):
        """Test that tokens are optimally sized."""
        users_with_different_claims = [
            User(id="user_1", email="a@b.c"),  # Minimal claims
            User(
                id="user_2",
                email="user@example.com",
                roles=["user"],
                permissions=["read", "write"],
            ),  # Moderate claims
            User(
                id="user_3",
                email="admin@organization.example.com",
                roles=["admin", "user", "moderator"],
                permissions=[f"permission_{i}" for i in range(20)],
                metadata={"org_id": "org_123", "dept": "engineering"},
            ),  # Many claims
        ]

        for user in users_with_different_claims:
            token = token_service.generate_access_token(user)
            token_size = len(token)

            # Token should be reasonably sized
            assert token_size < 2048, (
                f"Token size {token_size} bytes exceeds 2KB for user {user.id}"
            )

            # For minimal claims, token should be compact
            if user.id == "user_1":
                assert token_size < 500, (
                    f"Minimal token size {token_size} bytes exceeds 500 bytes"
                )

            print(f"\nToken size for {user.id}: {token_size} bytes")

    @pytest.mark.benchmark
    def test_performance_regression(self, token_service, benchmark):
        """Benchmark test to detect performance regressions."""
        user = User(id="bench_user", email="bench@example.com")

        # Benchmark token generation
        def generate():
            return token_service.generate_access_token(user)

        token = benchmark(generate)

        # Benchmark token validation
        def validate():
            return token_service.validate_token(token)

        benchmark(validate)

        # Performance assertions are configured in pytest-benchmark
        # Results are automatically compared against previous runs