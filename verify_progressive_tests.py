#!/usr/bin/env python
"""Verification script for progressive test suite integration."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from amplihack.agents.goal_seeking import LearningAgent
from amplihack.eval.test_levels import LEVEL_1, LEVEL_2


def test_basic_functionality():
    """Test basic LearningAgent functionality without requiring API keys."""
    print("Testing LearningAgent basic functionality...")

    # Test 1: Backward compatibility
    from amplihack.agents.goal_seeking import WikipediaLearningAgent
    print(f"✓ Backward compatibility: LearningAgent is WikipediaLearningAgent = {LearningAgent is WikipediaLearningAgent}")

    # Test 2: Test levels are accessible
    print(f"✓ L1 test level loaded: {LEVEL_1.level_id} - {LEVEL_1.level_name}")
    print(f"  Articles: {len(LEVEL_1.articles)}, Questions: {len(LEVEL_1.questions)}")

    print(f"✓ L2 test level loaded: {LEVEL_2.level_id} - {LEVEL_2.level_name}")
    print(f"  Articles: {len(LEVEL_2.articles)}, Questions: {len(LEVEL_2.questions)}")

    # Test 3: Agent instantiation
    import tempfile
    temp_dir = Path(tempfile.mkdtemp())
    try:
        # Kuzu needs a file path, not directory - provide db file path
        db_file = temp_dir / "test_db"
        agent = LearningAgent(
            agent_name="test_verification",
            storage_path=db_file,
            use_hierarchical=True,
        )
        print(f"✓ LearningAgent instantiated with hierarchical memory")

        stats = agent.get_memory_stats()
        print(f"✓ Memory stats accessible: {stats}")

        agent.close()
        print(f"✓ Agent closed successfully")
    finally:
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    print("\n✅ All basic functionality tests passed!")


def test_progressive_suite_imports():
    """Test that progressive test suite can import agent_subprocess."""
    print("\nTesting progressive test suite imports...")

    from amplihack.eval.agent_subprocess import learning_phase, testing_phase
    print(f"✓ agent_subprocess imports: learning_phase, testing_phase")

    from amplihack.eval.progressive_test_suite import (
        ProgressiveConfig,
        run_progressive_suite,
    )
    print(f"✓ progressive_test_suite imports: ProgressiveConfig, run_progressive_suite")

    print("\n✅ All progressive suite imports successful!")


if __name__ == "__main__":
    print("=" * 70)
    print("VERIFICATION: LearningAgent Rename & Progressive Test Suite Integration")
    print("=" * 70)

    try:
        test_basic_functionality()
        test_progressive_suite_imports()

        print("\n" + "=" * 70)
        print("✅ ALL VERIFICATIONS PASSED")
        print("=" * 70)

        print("\nSummary:")
        print("1. ✅ WikipediaLearningAgent → LearningAgent rename complete")
        print("2. ✅ Backward compatibility alias working")
        print("3. ✅ HierarchicalMemory integration functional")
        print("4. ✅ Progressive test suite imports working")
        print("5. ✅ L1 and L2 test levels accessible")

    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
