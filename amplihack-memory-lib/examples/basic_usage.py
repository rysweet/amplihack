"""Basic usage example for amplihack-memory-lib."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


from amplihack_memory import (
    Experience,
    ExperienceStore,
    ExperienceType,
    MemoryConnector,
)


def main():
    print("=" * 60)
    print("amplihack-memory-lib - Basic Usage Example")
    print("=" * 60)

    # 1. Initialize memory connector
    print("\n1. Creating MemoryConnector...")
    connector = MemoryConnector(
        agent_name="demo-agent",
        storage_path=Path("/tmp/demo-memory"),
    )
    print(f"   Storage: {connector.storage_path}")
    print(f"   Database: {connector.db_path}")

    # 2. Create and store experiences
    print("\n2. Storing experiences...")
    experiences = [
        Experience(
            experience_type=ExperienceType.SUCCESS,
            context="Analyzed Python codebase structure",
            outcome="Found 47 Python files with clear organization",
            confidence=0.95,
        ),
        Experience(
            experience_type=ExperienceType.PATTERN,
            context="Missing test coverage in utility modules",
            outcome="Detected pattern across 5 files",
            confidence=0.88,
        ),
        Experience(
            experience_type=ExperienceType.INSIGHT,
            context="Modular design improves maintainability",
            outcome="High cohesion, low coupling principle validated",
            confidence=0.92,
        ),
    ]

    for exp in experiences:
        exp_id = connector.store_experience(exp)
        print(f"   Stored: {exp.experience_type.value} - {exp_id}")

    # 3. Retrieve experiences
    print("\n3. Retrieving experiences...")
    all_exps = connector.retrieve_experiences(limit=10)
    print(f"   Retrieved {len(all_exps)} experiences")

    # 4. Filter by type
    print("\n4. Filtering by type (PATTERN)...")
    patterns = connector.retrieve_experiences(experience_type=ExperienceType.PATTERN)
    for exp in patterns:
        print(f"   - {exp.context}")

    # 5. Use ExperienceStore for advanced features
    print("\n5. Using ExperienceStore...")
    store = ExperienceStore(
        agent_name="demo-agent-2",
        storage_path=Path("/tmp/demo-memory-2"),
        max_experiences=100,
        auto_compress=True,
    )

    # Add experiences
    for i in range(5):
        exp = Experience(
            experience_type=ExperienceType.SUCCESS,
            context=f"Task {i}: Documentation quality check",
            outcome=f"Completed with {i + 1} issues found",
            confidence=0.8 + i * 0.02,
        )
        store.add(exp)

    # Get statistics
    stats = store.get_statistics()
    print(f"   Total experiences: {stats['total_experiences']}")
    print(f"   Storage size: {stats['storage_size_kb']:.1f} KB")
    print(f"   By type: {dict(stats['by_type'])}")

    # 6. Search experiences
    print("\n6. Searching experiences...")
    results = store.search("documentation quality", limit=3)
    print(f"   Found {len(results)} matching experiences")
    for exp in results:
        print(f"   - {exp.context[:50]}...")

    # 7. Cleanup
    print("\n7. Closing connections...")
    connector.close()
    store.connector.close()

    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
