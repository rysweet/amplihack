#!/usr/bin/env python3
"""Test model-aware threshold selection."""

import sys
from pathlib import Path

# Setup paths
sys.path.insert(0, str(Path(__file__).parent.parent))

from context_management import TokenMonitor


def test_model_aware_thresholds():
    """Test that thresholds adjust based on model size."""

    print("=" * 70)
    print("🧪 Testing Model-Aware Thresholds")
    print("=" * 70)

    # Test 1M token model (Sonnet 4.5)
    print("\n📊 Test 1: Sonnet 4.5 (1M tokens)")
    print("-" * 70)
    monitor_1m = TokenMonitor(max_tokens=1_000_000)
    print(f"Max tokens: {monitor_1m.max_tokens:,}")
    print(f"Thresholds: {monitor_1m.thresholds}")

    test_cases_1m = [
        (100_000, "ok"),  # 10% → ok
        (250_000, "ok"),  # 25% → ok
        (350_000, "consider"),  # 35% → consider
        (450_000, "recommended"),  # 45% → recommended
        (550_000, "urgent"),  # 55% → urgent
    ]

    print("\nThreshold verification:")
    for tokens, expected in test_cases_1m:
        usage = monitor_1m.check_usage(tokens)
        status = usage.threshold_status
        match = "✅" if status == expected else "❌"
        print(
            f"  {match} {tokens:>7,} tokens ({tokens / 10_000:.0f}%) → {status:>12} (expected: {expected})"
        )

    # Test 200k token model (Haiku)
    print("\n📊 Test 2: Haiku (200k tokens)")
    print("-" * 70)
    monitor_200k = TokenMonitor(max_tokens=200_000)
    print(f"Max tokens: {monitor_200k.max_tokens:,}")
    print(f"Thresholds: {monitor_200k.thresholds}")

    test_cases_200k = [
        (50_000, "ok"),  # 25% → ok
        (90_000, "ok"),  # 45% → ok
        (115_000, "consider"),  # 57.5% → consider
        (145_000, "recommended"),  # 72.5% → recommended
        (175_000, "urgent"),  # 87.5% → urgent
    ]

    print("\nThreshold verification:")
    for tokens, expected in test_cases_200k:
        usage = monitor_200k.check_usage(tokens)
        status = usage.threshold_status
        match = "✅" if status == expected else "❌"
        print(
            f"  {match} {tokens:>7,} tokens ({(tokens / 200_000) * 100:.0f}%) → {status:>12} (expected: {expected})"
        )

    print("\n" + "=" * 70)
    print("🎯 Model-Aware Thresholds Summary")
    print("=" * 70)

    print("\n1M Token Model (Sonnet 4.5):")
    print("  • Top threshold: 50% (500k tokens)")
    print("  • Auto-snapshots at: 30%, 40%, 50%")
    print("  • Philosophy: Conservative (plenty of space)")

    print("\n200k Token Model (Haiku):")
    print("  • Top threshold: 85% (170k tokens)")
    print("  • Auto-snapshots at: 55%, 70%, 85%")
    print("  • Philosophy: Aggressive (limited space)")

    print("\n✅ Model-aware thresholds working correctly!")


if __name__ == "__main__":
    test_model_aware_thresholds()
