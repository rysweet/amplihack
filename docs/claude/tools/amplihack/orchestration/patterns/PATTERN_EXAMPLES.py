"""Example usage of fault-tolerance pattern orchestrators.

This file demonstrates how to use the three pattern orchestrators:
- N-Version Programming (n_version.py)
- Multi-Agent Debate (debate.py)
- Fallback Cascade (cascade.py)

These examples can be run directly or used as templates.
"""

from .cascade import create_custom_cascade, run_cascade
from .debate import run_debate
from .n_version import run_n_version


def example_n_version():
    """Example: N-Version Programming for critical implementation."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: N-Version Programming")
    print("=" * 80 + "\n")

    result = run_n_version(
        task_prompt="""Implement a secure password hashing function.

Requirements:
- Use industry-standard hashing algorithm (bcrypt, argon2, or pbkdf2)
- Include proper salt generation
- Configurable work factor/iterations
- Return both hash and salt
- Include tests verifying security properties
""",
        n=3,
        selection_criteria=["security", "correctness", "simplicity"],
        timeout=300,  # 5 minutes per version
    )

    print(f"\nSession ID: {result['session_id']}")
    print(f"Success: {result['success']}")
    print(f"Versions generated: {len(result['versions'])}")
    print(f"Successful versions: {sum(1 for v in result['versions'] if v.exit_code == 0)}")
    print(f"\nSelected: {result['selected']}")
    print(f"\nRationale:\n{result['rationale'][:500]}...")

    # Access specific version outputs
    for i, version in enumerate(result["versions"]):
        status = "SUCCESS" if version.exit_code == 0 else "FAILED"
        print(f"\nVersion {i + 1}: {status} (duration: {version.duration:.1f}s)")
        if version.exit_code != 0:
            print(f"  Error: {version.stderr[:200]}...")

    return result


def example_debate():
    """Example: Multi-Agent Debate for architectural decision."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Multi-Agent Debate")
    print("=" * 80 + "\n")

    result = run_debate(
        decision_question="""
Should we use PostgreSQL or MongoDB for storing user analytics events?

Context:
- Expected 10M events/day at launch
- Projected 100M events/day within 2 years
- Need complex aggregation queries for dashboards
- Real-time and historical reporting required
- Team experienced with PostgreSQL, not MongoDB
- Budget: $5K/month infrastructure

Decide which database to use and why.
""",
        perspectives=["performance", "simplicity", "cost", "maintainability"],
        rounds=3,
        timeout=180,  # 3 minutes per perspective per round
    )

    print(f"\nSession ID: {result['session_id']}")
    print(f"Success: {result['success']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Total rounds: {len(result['rounds'])}")

    # Show debate progression
    for round_data in result["rounds"]:
        round_num = round_data["round"]
        round_type = round_data["type"]
        successful = sum(1 for r in round_data["results"].values() if r.exit_code == 0)
        total = len(round_data["results"])
        print(f"\nRound {round_num} ({round_type}): {successful}/{total} perspectives succeeded")

    # Show synthesis
    if result["synthesis"]:
        print("\n--- CONSENSUS ---")
        print(result["synthesis"].output[:800])
        print("...(see full output in session logs)")

    return result


def example_cascade_quality():
    """Example: Fallback Cascade with quality degradation."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Fallback Cascade (Quality)")
    print("=" * 80 + "\n")

    result = run_cascade(
        task_prompt="""Analyze this codebase and provide recommendations:

Analyze the orchestration infrastructure in .claude/tools/amplihack/orchestration/
and suggest improvements for:
1. Error handling
2. Performance optimization
3. Code organization
4. Documentation
5. Testing coverage
""",
        fallback_strategy="quality",
        timeout_strategy="balanced",  # 30s / 10s / 5s
        notification_level="explicit",
    )

    print(f"\nSession ID: {result['session_id']}")
    print(f"Success: {result['success']}")
    print(f"Cascade level reached: {result['cascade_level']}")
    print(f"Total attempts: {len(result['attempts'])}")

    if result["degradation"]:
        print(f"\nDegradation: {result['degradation']}")

    # Show cascade path
    print("\n--- CASCADE PATH ---")
    levels = ["primary", "secondary", "tertiary"]
    for i, attempt in enumerate(result["attempts"]):
        level = levels[i] if i < len(levels) else f"level_{i + 1}"
        status = (
            "SUCCESS"
            if attempt.exit_code == 0
            else ("TIMEOUT" if attempt.exit_code == -1 else "FAILED")
        )
        print(f"{level.upper()}: {status} (duration: {attempt.duration:.1f}s)")

    # Show final result
    if result["success"]:
        print(f"\n--- RESULT ({result['cascade_level'].upper()} LEVEL) ---")
        print(result["result"].output[:500])
        print("...(see full output in session logs)")

    return result


def example_cascade_custom():
    """Example: Custom cascade with specific levels."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: Custom Fallback Cascade")
    print("=" * 80 + "\n")

    result = create_custom_cascade(
        task_prompt="""Generate API documentation for the orchestration patterns.

Include:
- Purpose and use cases
- Parameters and return values
- Example usage
- Common pitfalls
""",
        levels=[
            {
                "name": "comprehensive",
                "timeout": 120,
                "constraint": "Full documentation with examples, tutorials, and API reference",
                "model": None,  # Use default
            },
            {
                "name": "standard",
                "timeout": 30,
                "constraint": "API reference with basic examples",
                "model": None,
            },
            {
                "name": "minimal",
                "timeout": 10,
                "constraint": "Function signatures and brief descriptions only",
                "model": None,
            },
        ],
        notification_level="warning",
    )

    print(f"\nSession ID: {result['session_id']}")
    print(f"Success: {result['success']}")
    print(f"Final level: {result['cascade_level']}")

    if result["degradation"]:
        print(f"Degradation: {result['degradation']}")

    return result


def main():
    """Run all examples."""
    print("\n" + "#" * 80)
    print("# FAULT-TOLERANCE PATTERN ORCHESTRATORS - EXAMPLES")
    print("#" * 80)

    # Uncomment to run specific examples:

    # Example 1: N-Version Programming
    # example_n_version()

    # Example 2: Multi-Agent Debate
    # example_debate()

    # Example 3: Quality-based Cascade
    # example_cascade_quality()

    # Example 4: Custom Cascade
    # example_cascade_custom()

    print("\n" + "#" * 80)
    print("# Uncomment specific examples in main() to run them")
    print("#" * 80 + "\n")


if __name__ == "__main__":
    main()
