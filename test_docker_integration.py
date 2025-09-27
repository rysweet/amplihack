#!/usr/bin/env python
"""Test script for Docker integration in amplihack."""

import os
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from amplihack.docker import DockerDetector, DockerManager


def test_docker_detection():
    """Test Docker detection functionality."""
    print("Testing Docker Detection...")
    detector = DockerDetector()

    print(f"  Docker Available: {detector.is_available()}")
    print(f"  Docker Running: {detector.is_running()}")
    print(f"  Running in Docker: {detector.is_in_docker()}")
    print(f"  Should Use Docker: {detector.should_use_docker()}")

    return detector.is_available()


def test_docker_manager():
    """Test Docker manager functionality."""
    print("\nTesting Docker Manager...")
    manager = DockerManager()

    # Check if image exists
    print(f"  Image Name: {manager.IMAGE_NAME}")
    print(f"  Image Exists: {manager.detector.check_image_exists(manager.IMAGE_NAME)}")

    # Test environment variable collection
    env_vars = manager._get_env_vars()
    print(f"  Environment variables to forward: {len(env_vars)} found")

    return True


def test_docker_with_env():
    """Test Docker detection with environment variable set."""
    print("\nTesting with AMPLIHACK_USE_DOCKER=1...")

    # Set environment variable
    os.environ["AMPLIHACK_USE_DOCKER"] = "1"

    detector = DockerDetector()
    should_use = detector.should_use_docker()
    print(f"  Should Use Docker: {should_use}")

    # Clean up
    os.environ.pop("AMPLIHACK_USE_DOCKER", None)

    return True


def main():
    """Run all tests."""
    print("=" * 50)
    print("Docker Integration Test Suite")
    print("=" * 50)

    tests = [
        ("Docker Detection", test_docker_detection),
        ("Docker Manager", test_docker_manager),
        ("Environment Variable", test_docker_with_env),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, "PASS" if success else "FAIL"))
        except Exception as e:
            print(f"  Error: {e}")
            results.append((name, "ERROR"))

    print("\n" + "=" * 50)
    print("Test Results:")
    print("=" * 50)
    for name, result in results:
        print(f"  {name}: {result}")

    # Overall result
    all_passed = all(r == "PASS" for _, r in results)
    print("\n" + ("All tests passed!" if all_passed else "Some tests failed!"))

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
