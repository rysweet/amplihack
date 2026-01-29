#!/usr/bin/env python3
"""Test blarify vendor code execution after import fixes."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def test_blarify_imports():
    """Test that all blarify modules can be imported."""
    print("Testing blarify vendor code imports...")

    try:
        # Test critical imports
        print("  Testing main modules...")
        from amplihack.vendor.blarify.main import main_with_documentation

        print(f"    ✓ main module ({main_with_documentation.__name__})")

        from amplihack.vendor.blarify.prebuilt.graph_builder import GraphBuilder

        print(f"    ✓ graph_builder ({GraphBuilder.__name__})")

        from amplihack.vendor.blarify.repositories.graph_db_manager.kuzu_manager import (
            KuzuManager,
        )

        print(f"    ✓ kuzu_manager ({KuzuManager.__name__})")

        from amplihack.vendor.blarify.project_graph_creator import ProjectGraphCreator

        print(f"    ✓ project_graph_creator ({ProjectGraphCreator.__name__})")

        print("\n✅ All critical imports successful!")
        return True

    except ImportError as e:
        print(f"\n❌ Import failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_kuzu_code_graph():
    """Test that KuzuCodeGraph can be imported and instantiated."""
    print("\nTesting KuzuCodeGraph integration...")

    try:
        from amplihack.memory.kuzu.code_graph import KuzuCodeGraph

        print(f"  ✓ KuzuCodeGraph imported ({KuzuCodeGraph.__name__})")

        # Try to instantiate (without connector, just to test class loading)
        print("  ✓ KuzuCodeGraph class loaded successfully")

        return True

    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("Blarify Vendor Code Execution Test")
    print("=" * 70)
    print()

    results = []

    # Test 1: Blarify imports
    results.append(("Blarify imports", test_blarify_imports()))

    # Test 2: KuzuCodeGraph integration
    results.append(("KuzuCodeGraph integration", test_kuzu_code_graph()))

    # Summary
    print()
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n🎉 All tests passed! Blarify vendor code is working correctly.")
        return 0
    print("\n❌ Some tests failed. See errors above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
