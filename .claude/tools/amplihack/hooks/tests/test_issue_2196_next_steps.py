#!/usr/bin/env python3
"""
Tests for Issue #2196 Phase 2B: Next Steps Structural Detection.

Verifies that:
- Structured next steps (bulleted lists) are detected
- Negation statements ("no next steps") pass the check
- Status observations don't trigger false positives
- Completion statements are handled correctly
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from power_steering_checker import PowerSteeringChecker


def test_structured_next_steps_fails():
    """Structured next steps (bulleted list) should FAIL the check."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Implementation complete. Next steps:\n- Run integration tests\n- Update documentation\n- Deploy to staging",
                    }
                ]
            },
        },
    ]

    result = checker._check_next_steps(transcript, "test_session")
    assert result is False, "Structured next steps should FAIL the check (work incomplete)"


def test_no_next_steps_passes():
    """'No next steps' negation should PASS the check."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "All work complete. No next steps remaining.",
                    }
                ]
            },
        },
    ]

    result = checker._check_next_steps(transcript, "test_session")
    assert result is True, "'No next steps' should PASS the check (work complete)"


def test_next_steps_none_passes():
    """'Next steps are none' should PASS the check."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Implementation finished. Next steps are none.",
                    }
                ]
            },
        },
    ]

    result = checker._check_next_steps(transcript, "test_session")
    assert result is True, "'Next steps are none' should PASS the check"


def test_all_done_passes():
    """'All done' completion statement should PASS the check."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "All done! Tests passing and PR ready.",
                    }
                ]
            },
        },
    ]

    result = checker._check_next_steps(transcript, "test_session")
    assert result is True, "'All done' should PASS the check"


def test_ci_pending_status_passes():
    """Status observations like 'CI pending' should NOT fail the check."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Implementation complete. CI checks are pending, waiting for results.",
                    }
                ]
            },
        },
    ]

    result = checker._check_next_steps(transcript, "test_session")
    assert result is True, "Status observation 'pending' should PASS (not concrete next steps)"


def test_waiting_for_ci_passes():
    """'Waiting for CI' should PASS (external wait, not agent work)."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "PR created. Waiting for CI to complete before merging.",
                    }
                ]
            },
        },
    ]

    result = checker._check_next_steps(transcript, "test_session")
    assert result is True, "'Waiting for CI' should PASS (not agent work)"


def test_numbered_list_next_steps_fails():
    """Numbered list of next steps should FAIL the check."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Current work done. Next steps:\n1. Add integration tests\n2. Update README\n3. Create PR",
                    }
                ]
            },
        },
    ]

    result = checker._check_next_steps(transcript, "test_session")
    assert result is False, "Numbered list next steps should FAIL (work incomplete)"


def test_remaining_with_bullets_fails():
    """'Remaining:' with bullets should FAIL the check."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Most features complete. Remaining:\n• Fix edge cases\n• Add error handling",
                    }
                ]
            },
        },
    ]

    result = checker._check_next_steps(transcript, "test_session")
    assert result is False, "Structured 'Remaining' list should FAIL"


def test_todo_with_bullets_fails():
    """'TODO:' with bullets should FAIL the check."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Core implementation done. TODO:\n* Add validation\n* Write tests",
                    }
                ]
            },
        },
    ]

    result = checker._check_next_steps(transcript, "test_session")
    assert result is False, "Structured TODO list should FAIL"


def test_no_outstanding_work_passes():
    """'No outstanding work' should PASS the check."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "All complete. No outstanding work remaining.",
                    }
                ]
            },
        },
    ]

    result = checker._check_next_steps(transcript, "test_session")
    assert result is True, "'No outstanding work' should PASS"


def test_nothing_left_passes():
    """'Nothing left to do' should PASS the check."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Implementation finished. Nothing left to do.",
                    }
                ]
            },
        },
    ]

    result = checker._check_next_steps(transcript, "test_session")
    assert result is True, "'Nothing left' should PASS"


def test_bare_next_steps_keyword_without_structure_passes():
    """Bare 'next steps' keyword WITHOUT structure should PASS (no concrete work)."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Implementation complete. Discussed possible next steps with user but none planned.",
                    }
                ]
            },
        },
    ]

    result = checker._check_next_steps(transcript, "test_session")
    assert result is True, "Bare 'next steps' without structure should PASS"


def test_outstanding_with_bullets_fails():
    """'Outstanding:' with bullets should FAIL."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Main work done. Outstanding:\n- Fix linting issues\n- Update tests",
                    }
                ]
            },
        },
    ]

    result = checker._check_next_steps(transcript, "test_session")
    assert result is False, "Structured 'Outstanding' list should FAIL"


def test_still_need_to_with_bullets_fails():
    """'Still need to:' with bullets should FAIL."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Most complete. Still need to:\n- Add documentation\n- Run benchmarks",
                    }
                ]
            },
        },
    ]

    result = checker._check_next_steps(transcript, "test_session")
    assert result is False, "'Still need to' with bullets should FAIL"


def test_everything_complete_passes():
    """'Everything complete' should PASS."""
    checker = PowerSteeringChecker()

    transcript = [
        {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "text",
                        "text": "Everything complete. All tests passing, PR ready to merge.",
                    }
                ]
            },
        },
    ]

    result = checker._check_next_steps(transcript, "test_session")
    assert result is True, "'Everything complete' should PASS"


if __name__ == "__main__":
    print("Running Issue #2196 Phase 2B tests (Next Steps)...")

    test_structured_next_steps_fails()
    print("✓ test_structured_next_steps_fails")

    test_no_next_steps_passes()
    print("✓ test_no_next_steps_passes")

    test_next_steps_none_passes()
    print("✓ test_next_steps_none_passes")

    test_all_done_passes()
    print("✓ test_all_done_passes")

    test_ci_pending_status_passes()
    print("✓ test_ci_pending_status_passes")

    test_waiting_for_ci_passes()
    print("✓ test_waiting_for_ci_passes")

    test_numbered_list_next_steps_fails()
    print("✓ test_numbered_list_next_steps_fails")

    test_remaining_with_bullets_fails()
    print("✓ test_remaining_with_bullets_fails")

    test_todo_with_bullets_fails()
    print("✓ test_todo_with_bullets_fails")

    test_no_outstanding_work_passes()
    print("✓ test_no_outstanding_work_passes")

    test_nothing_left_passes()
    print("✓ test_nothing_left_passes")

    test_bare_next_steps_keyword_without_structure_passes()
    print("✓ test_bare_next_steps_keyword_without_structure_passes")

    test_outstanding_with_bullets_fails()
    print("✓ test_outstanding_with_bullets_fails")

    test_still_need_to_with_bullets_fails()
    print("✓ test_still_need_to_with_bullets_fails")

    test_everything_complete_passes()
    print("✓ test_everything_complete_passes")

    print("\n✅ All Phase 2B tests passed!")
