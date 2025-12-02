"""Tests for response module."""

import json

import pytest

from amplihack.api_client.response import ApiResponse


def test_response_ok_status():
    """Test response.ok for 2xx status codes."""
    assert ApiResponse(200, b"", {}).ok is True
    assert ApiResponse(201, b"", {}).ok is True
    assert ApiResponse(299, b"", {}).ok is True


def test_response_not_ok_status():
    """Test response.ok for non-2xx status codes."""
    assert ApiResponse(199, b"", {}).ok is False
    assert ApiResponse(300, b"", {}).ok is False
    assert ApiResponse(404, b"", {}).ok is False
    assert ApiResponse(500, b"", {}).ok is False


def test_response_text():
    """Test response.text property."""
    body = b"Hello, World!"
    response = ApiResponse(200, body, {})

    assert response.text == "Hello, World!"


def test_response_json():
    """Test response.json() method."""
    data = {"status": "ok", "count": 42, "items": ["a", "b", "c"]}
    body = json.dumps(data).encode("utf-8")
    response = ApiResponse(200, body, {})

    parsed = response.json()
    assert parsed == data
    assert parsed["count"] == 42


def test_response_json_invalid():
    """Test response.json() with invalid JSON."""
    response = ApiResponse(200, b"not json", {})

    with pytest.raises(json.JSONDecodeError):
        response.json()


def test_response_headers():
    """Test response headers are accessible."""
    headers = {"Content-Type": "application/json", "X-Custom": "value"}
    response = ApiResponse(200, b"{}", headers)

    assert response.headers["Content-Type"] == "application/json"
    assert response.headers["X-Custom"] == "value"
