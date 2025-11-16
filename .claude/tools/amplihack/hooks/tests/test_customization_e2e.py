#!/usr/bin/env python3
"""End-to-end test for user customization workflow."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker import PowerSteeringChecker


def test_user_customization_workflow():
    """Test the complete user customization workflow."""
    print("Testing user customization workflow...")

    # Create temp project
    temp_dir = tempfile.mkdtemp()
    project_root = Path(temp_dir)
    (project_root / ".claude" / "tools" / "amplihack").mkdir(parents=True)
    (project_root / ".claude" / "runtime" / "power-steering").mkdir(parents=True, exist_ok=True)

    config_path = project_root / ".claude" / "tools" / "amplihack" / ".power_steering_config"
    config_path.write_text(json.dumps({"enabled": True}))

    # Step 1: Create custom YAML with team consideration
    print("Step 1: Creating custom considerations.yaml...")
    yaml_path = project_root / ".claude" / "tools" / "amplihack" / "considerations.yaml"
    custom_yaml = """
- id: security_scan
  category: Security & Compliance
  question: Was security scanning performed?
  description: Ensures security tools ran on code changes
  severity: blocker
  checker: generic
  enabled: true

- id: code_review
  category: Team Process
  question: Was code reviewed by peer?
  description: Ensures peer review completed
  severity: warning
  checker: generic
  enabled: true
"""
    yaml_path.write_text(custom_yaml)
    print("  ✓ Custom YAML created")

    # Step 2: Load checker with custom config
    print("Step 2: Loading PowerSteeringChecker...")
    checker = PowerSteeringChecker(project_root)
    assert len(checker.considerations) == 2, f"Expected 2, got {len(checker.considerations)}"
    print(f"  ✓ Loaded {len(checker.considerations)} custom considerations")

    # Step 3: Verify considerations loaded correctly
    print("Step 3: Verifying consideration properties...")
    security_check = checker.considerations[0]
    assert security_check["id"] == "security_scan"
    assert security_check["severity"] == "blocker"
    assert security_check["checker"] == "generic"
    assert security_check["enabled"] is True
    print("  ✓ Security scan consideration valid")

    review_check = checker.considerations[1]
    assert review_check["id"] == "code_review"
    assert review_check["severity"] == "warning"
    print("  ✓ Code review consideration valid")

    # Step 4: Test with transcript
    print("Step 4: Testing with sample transcript...")
    transcript = [
        {"type": "user", "message": {"content": "Fix security vulnerability"}},
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "text", "text": "Ran security scans, all passed. Code reviewed by team."}
                ]
            },
        },
    ]

    analysis = checker._analyze_considerations(transcript, "test_session")
    print(f"  ✓ Analysis complete: {len(analysis.results)} results")

    # Step 5: Verify results
    print("Step 5: Verifying analysis results...")
    assert "security_scan" in analysis.results
    assert "code_review" in analysis.results
    assert analysis.results["security_scan"].satisfied is True
    assert analysis.results["code_review"].satisfied is True
    print("  ✓ Both custom considerations satisfied")

    # Step 6: Test disabling a consideration
    print("Step 6: Testing consideration disable...")
    disabled_yaml = """
- id: security_scan
  category: Security & Compliance
  question: Was security scanning performed?
  description: Ensures security tools ran on code changes
  severity: blocker
  checker: generic
  enabled: false  # Disabled

- id: code_review
  category: Team Process
  question: Was code reviewed by peer?
  description: Ensures peer review completed
  severity: warning
  checker: generic
  enabled: true
"""
    yaml_path.write_text(disabled_yaml)

    # Reload checker
    checker2 = PowerSteeringChecker(project_root)
    analysis2 = checker2._analyze_considerations(transcript, "test_session")

    # security_scan should not be in results (disabled)
    assert "security_scan" not in analysis2.results
    assert "code_review" in analysis2.results
    print("  ✓ Disabled consideration correctly skipped")

    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)

    print("\n✅ User customization workflow test PASSED!")
    return True


if __name__ == "__main__":
    try:
        test_user_customization_workflow()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
