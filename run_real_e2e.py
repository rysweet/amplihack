"""Temporary script to run real E2E test without skip decorator."""

import sys

sys.path.insert(0, "src")

# Import and run test directly
from tests.test_bundle_generator_real_e2e import test_real_e2e_complete_workflow

if __name__ == "__main__":
    try:
        test_real_e2e_complete_workflow()
        print("\n✅ Real E2E test PASSED")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Real E2E test FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
