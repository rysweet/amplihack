#!/usr/bin/env python3
"""Example usage of the pre-commit workflow tool."""

from precommit_workflow import PreCommitWorkflow


def main():
    """Demonstrate pre-commit workflow tool usage."""
    workflow = PreCommitWorkflow()

    print("=" * 60)
    print("Pre-commit Workflow Tool Example")
    print("=" * 60)

    # 1. Verify environment
    print("\n1. Checking pre-commit environment:")
    print("-" * 40)
    env_checks = workflow.verify_environment()
    print(f"Environment ready: {all(env_checks.values())}")

    # 2. Analyze any failures
    print("\n2. Analyzing current pre-commit status:")
    print("-" * 40)
    analysis = workflow.analyze_failures()
    if analysis["success"]:
        print("All checks passing!")
    else:
        print(f"Found {len(analysis['failed_hooks'])} issues")
        if analysis["fixable"]:
            print(f"  - {len(analysis['fixable'])} auto-fixable")
        if analysis["manual_fixes"]:
            print(f"  - {len(analysis['manual_fixes'])} need manual fixes")

    # 3. Auto-fix if needed
    if analysis["fixable"]:
        print("\n3. Attempting auto-fix:")
        print("-" * 40)
        # Extract tool names from hook IDs
        tools = set()
        for hook_id in analysis["fixable"]:
            if "ruff" in hook_id:
                tools.add("ruff")
            elif "prettier" in hook_id:
                tools.add("prettier")
            elif "black" in hook_id:
                tools.add("black")

        if tools:
            success = workflow.auto_fix(list(tools))
            print(f"Auto-fix {'succeeded' if success else 'failed'}")

    # 4. Final verification
    print("\n4. Final verification:")
    print("-" * 40)
    all_pass = workflow.verify_success()
    print(f"Final status: {'✅ PASS' if all_pass else '❌ FAIL'}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
