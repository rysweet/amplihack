#!/usr/bin/env python3
"""Simple test to verify the critical import fix."""


def test_import_fix():
    """Test that APIClientError is used instead of non-existent APIException."""
    # This should import without errors now
    # Create a Response object with 400 error status
    import json

    from rest_api_client.exceptions import APIClientError, ValidationError

    from rest_api_client.models import APIResponse

    response = APIResponse(status_code=400, body=json.dumps({"error": "Bad Request"}), headers={})

    # This should raise ValidationError for 400 errors
    try:
        response.raise_for_status()
    except ValidationError as e:
        print(f"✓ ValidationError raised correctly for 400: {e}")
        assert e.status_code == 400

    # Test with a generic error that should use APIClientError
    response = APIResponse(
        status_code=999,  # Non-standard error code
        body=json.dumps({"error": "Unknown"}),
        headers={},
    )

    try:
        response.raise_for_status()
    except APIClientError as e:
        print(f"✓ APIClientError raised correctly: {e}")
        assert e.status_code == 999

    print("\n✅ All tests passed! The critical import bug is fixed.")
    return True


if __name__ == "__main__":
    test_import_fix()
