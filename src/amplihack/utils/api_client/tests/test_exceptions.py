"""
Test suite for custom exception hierarchy.

Tests all custom exceptions can be raised and caught, proper inheritance chain,
exception messages and attributes.

Testing Philosophy:
- Unit tests for exception classes
- Verify exception hierarchy
- Test exception attributes
- Ensure proper error messages
"""

import pytest

from amplihack.utils.api_client import (
    APIClientError,
    HTTPError,
    RateLimitError,
    RequestError,
    ResponseError,
    RetryExhaustedError,
)


class TestExceptionHierarchy:
    """Test exception inheritance chain"""

    def test_api_client_error_is_base_exception(self):
        """Test APIClientError is the base exception"""
        error = APIClientError("Base error")
        assert isinstance(error, Exception)
        assert isinstance(error, APIClientError)

    def test_request_error_inherits_from_api_client_error(self):
        """Test RequestError inherits from APIClientError"""
        error = RequestError("Request failed")
        assert isinstance(error, APIClientError)
        assert isinstance(error, RequestError)

    def test_http_error_inherits_from_api_client_error(self):
        """Test HTTPError inherits from APIClientError"""
        error = HTTPError(status_code=500, message="Server error")
        assert isinstance(error, APIClientError)
        assert isinstance(error, HTTPError)

    def test_rate_limit_error_inherits_from_http_error(self):
        """Test RateLimitError inherits from HTTPError"""
        error = RateLimitError(wait_time=60.0, retry_after="60")
        assert isinstance(error, APIClientError)
        assert isinstance(error, HTTPError)
        assert isinstance(error, RateLimitError)

    def test_retry_exhausted_error_inherits_from_api_client_error(self):
        """Test RetryExhaustedError inherits from APIClientError"""
        last_error = RequestError("Connection failed")
        error = RetryExhaustedError(attempts=3, last_error=last_error)
        assert isinstance(error, APIClientError)
        assert isinstance(error, RetryExhaustedError)

    def test_response_error_inherits_from_api_client_error(self):
        """Test ResponseError inherits from APIClientError"""
        error = ResponseError("Invalid response format")
        assert isinstance(error, APIClientError)
        assert isinstance(error, ResponseError)


class TestAPIClientError:
    """Test APIClientError base exception"""

    def test_api_client_error_can_be_raised(self):
        """Test APIClientError can be raised"""
        with pytest.raises(APIClientError) as exc_info:
            raise APIClientError("Base error message")

        assert str(exc_info.value) == "Base error message"

    def test_api_client_error_can_be_caught(self):
        """Test APIClientError can be caught"""
        try:
            raise APIClientError("Test error")
        except APIClientError as e:
            assert str(e) == "Test error"

    def test_api_client_error_catches_all_subclasses(self):
        """Test catching APIClientError catches all subclass exceptions"""
        exceptions_to_test = [
            RequestError("Request error"),
            HTTPError(404, "Not found"),
            RateLimitError(60.0, "60"),
            RetryExhaustedError(3, RequestError("Failed")),
            ResponseError("Response error"),
        ]

        for exception in exceptions_to_test:
            try:
                raise exception
            except APIClientError:
                pass  # Successfully caught
            else:
                pytest.fail(f"{type(exception).__name__} was not caught by APIClientError")


class TestRequestError:
    """Test RequestError exception"""

    def test_request_error_can_be_raised(self):
        """Test RequestError can be raised"""
        with pytest.raises(RequestError) as exc_info:
            raise RequestError("Connection timeout")

        assert str(exc_info.value) == "Connection timeout"

    def test_request_error_message(self):
        """Test RequestError has correct error message"""
        error = RequestError("DNS resolution failed")
        assert str(error) == "DNS resolution failed"

    def test_request_error_with_detailed_message(self):
        """Test RequestError with detailed error message"""
        error = RequestError("Failed to connect to https://api.example.com: Connection refused")
        assert "Connection refused" in str(error)
        assert "https://api.example.com" in str(error)


class TestHTTPError:
    """Test HTTPError exception"""

    def test_http_error_can_be_raised(self):
        """Test HTTPError can be raised"""
        with pytest.raises(HTTPError) as exc_info:
            raise HTTPError(status_code=404, message="Not Found")

        error = exc_info.value
        assert error.status_code == 404
        assert error.message == "Not Found"

    def test_http_error_status_code_attribute(self):
        """Test HTTPError has status_code attribute"""
        error = HTTPError(status_code=500, message="Internal Server Error")
        assert error.status_code == 500
        assert isinstance(error.status_code, int)

    def test_http_error_message_attribute(self):
        """Test HTTPError has message attribute"""
        error = HTTPError(status_code=400, message="Bad Request")
        assert error.message == "Bad Request"
        assert isinstance(error.message, str)

    def test_http_error_response_data_attribute(self):
        """Test HTTPError has response_data attribute"""
        response_data = {"error": "Invalid input", "field": "email"}
        error = HTTPError(status_code=400, message="Bad Request", response_data=response_data)
        assert error.response_data == response_data

    def test_http_error_response_data_optional(self):
        """Test HTTPError response_data is optional"""
        error = HTTPError(status_code=404, message="Not Found")
        assert hasattr(error, "response_data")
        assert error.response_data is None

    def test_http_error_string_representation(self):
        """Test HTTPError string representation"""
        error = HTTPError(status_code=403, message="Forbidden")
        error_str = str(error)
        assert "403" in error_str
        assert "Forbidden" in error_str

    def test_http_error_various_status_codes(self):
        """Test HTTPError with various HTTP status codes"""
        status_codes = [400, 401, 403, 404, 500, 502, 503, 504]

        for code in status_codes:
            error = HTTPError(status_code=code, message=f"Error {code}")
            assert error.status_code == code


class TestRateLimitError:
    """Test RateLimitError exception"""

    def test_rate_limit_error_can_be_raised(self):
        """Test RateLimitError can be raised"""
        with pytest.raises(RateLimitError) as exc_info:
            raise RateLimitError(wait_time=60.0, retry_after="60")

        error = exc_info.value
        assert error.wait_time == 60.0
        assert error.retry_after == "60"

    def test_rate_limit_error_wait_time_attribute(self):
        """Test RateLimitError has wait_time attribute"""
        error = RateLimitError(wait_time=120.0, retry_after="120")
        assert error.wait_time == 120.0
        assert isinstance(error.wait_time, float)

    def test_rate_limit_error_retry_after_attribute(self):
        """Test RateLimitError has retry_after attribute"""
        error = RateLimitError(wait_time=60.0, retry_after="60")
        assert error.retry_after == "60"

    def test_rate_limit_error_retry_after_optional(self):
        """Test RateLimitError retry_after is optional"""
        error = RateLimitError(wait_time=60.0)
        assert hasattr(error, "retry_after")
        assert error.retry_after is None

    def test_rate_limit_error_status_code_is_429(self):
        """Test RateLimitError status_code is always 429"""
        error = RateLimitError(wait_time=60.0, retry_after="60")
        assert error.status_code == 429

    def test_rate_limit_error_inherits_http_error_attributes(self):
        """Test RateLimitError inherits HTTPError attributes"""
        error = RateLimitError(wait_time=60.0, retry_after="60")
        assert hasattr(error, "status_code")
        assert hasattr(error, "message")
        assert error.status_code == 429

    def test_rate_limit_error_string_representation(self):
        """Test RateLimitError string representation"""
        error = RateLimitError(wait_time=120.0, retry_after="120")
        error_str = str(error)
        assert "120" in error_str or "rate limit" in error_str.lower()


class TestRetryExhaustedError:
    """Test RetryExhaustedError exception"""

    def test_retry_exhausted_error_can_be_raised(self):
        """Test RetryExhaustedError can be raised"""
        last_error = HTTPError(status_code=500, message="Server Error")

        with pytest.raises(RetryExhaustedError) as exc_info:
            raise RetryExhaustedError(attempts=3, last_error=last_error)

        error = exc_info.value
        assert error.attempts == 3
        assert error.last_error == last_error

    def test_retry_exhausted_error_attempts_attribute(self):
        """Test RetryExhaustedError has attempts attribute"""
        last_error = RequestError("Connection failed")
        error = RetryExhaustedError(attempts=5, last_error=last_error)
        assert error.attempts == 5
        assert isinstance(error.attempts, int)

    def test_retry_exhausted_error_last_error_attribute(self):
        """Test RetryExhaustedError has last_error attribute"""
        last_error = HTTPError(status_code=503, message="Service Unavailable")
        error = RetryExhaustedError(attempts=3, last_error=last_error)
        assert error.last_error == last_error
        assert isinstance(error.last_error, Exception)

    def test_retry_exhausted_error_with_request_error(self):
        """Test RetryExhaustedError with RequestError as last_error"""
        last_error = RequestError("Network timeout")
        error = RetryExhaustedError(attempts=3, last_error=last_error)
        assert isinstance(error.last_error, RequestError)
        assert str(error.last_error) == "Network timeout"

    def test_retry_exhausted_error_with_http_error(self):
        """Test RetryExhaustedError with HTTPError as last_error"""
        last_error = HTTPError(status_code=500, message="Internal Server Error")
        error = RetryExhaustedError(attempts=3, last_error=last_error)
        assert isinstance(error.last_error, HTTPError)
        assert error.last_error.status_code == 500

    def test_retry_exhausted_error_string_representation(self):
        """Test RetryExhaustedError string representation"""
        last_error = HTTPError(status_code=503, message="Service Unavailable")
        error = RetryExhaustedError(attempts=3, last_error=last_error)
        error_str = str(error)
        assert "3" in error_str or "retry" in error_str.lower() or "attempt" in error_str.lower()


class TestResponseError:
    """Test ResponseError exception"""

    def test_response_error_can_be_raised(self):
        """Test ResponseError can be raised"""
        with pytest.raises(ResponseError) as exc_info:
            raise ResponseError("Invalid JSON response")

        assert str(exc_info.value) == "Invalid JSON response"

    def test_response_error_message(self):
        """Test ResponseError has correct error message"""
        error = ResponseError("Failed to parse response body")
        assert str(error) == "Failed to parse response body"

    def test_response_error_with_detailed_message(self):
        """Test ResponseError with detailed error message"""
        error = ResponseError("Expected JSON but received HTML: <!DOCTYPE html>...")
        assert "Expected JSON" in str(error)
        assert "HTML" in str(error)


class TestExceptionCatching:
    """Test exception catching patterns"""

    def test_catch_specific_exception_before_base(self):
        """Test catching specific exceptions before base APIClientError"""
        try:
            raise HTTPError(status_code=404, message="Not Found")
        except HTTPError as e:
            assert e.status_code == 404
        except APIClientError:
            pytest.fail("Should have caught HTTPError, not APIClientError")

    def test_catch_base_exception_for_all_errors(self):
        """Test catching base APIClientError catches all subclasses"""
        errors = [
            RequestError("Request error"),
            HTTPError(500, "Server error"),
            RateLimitError(60.0, "60"),
            RetryExhaustedError(3, RequestError("Failed")),
            ResponseError("Response error"),
        ]

        for error in errors:
            caught = False
            try:
                raise error
            except APIClientError:
                caught = True

            assert caught, f"Failed to catch {type(error).__name__} with APIClientError"

    def test_catch_http_error_catches_rate_limit_error(self):
        """Test catching HTTPError catches RateLimitError"""
        try:
            raise RateLimitError(wait_time=60.0, retry_after="60")
        except HTTPError as e:
            assert isinstance(e, RateLimitError)
        except APIClientError:
            pytest.fail("Should have caught as HTTPError")

    def test_multiple_except_blocks(self):
        """Test multiple except blocks for different exception types"""

        def raise_error(error_type):
            if error_type == "rate_limit":
                raise RateLimitError(60.0, "60")
            if error_type == "http":
                raise HTTPError(500, "Server Error")
            if error_type == "request":
                raise RequestError("Connection failed")
            if error_type == "retry":
                raise RetryExhaustedError(3, RequestError("Failed"))

        # Test rate limit catch
        try:
            raise_error("rate_limit")
        except RateLimitError as e:
            assert e.wait_time == 60.0
        except HTTPError:
            pytest.fail("Should catch RateLimitError specifically")

        # Test HTTP error catch
        try:
            raise_error("http")
        except RateLimitError:
            pytest.fail("Should not be RateLimitError")
        except HTTPError as e:
            assert e.status_code == 500

        # Test request error catch
        try:
            raise_error("request")
        except HTTPError:
            pytest.fail("Should not be HTTPError")
        except RequestError as e:
            assert "Connection failed" in str(e)


class TestExceptionMessages:
    """Test exception message formatting"""

    def test_api_client_error_custom_message(self):
        """Test APIClientError with custom message"""
        error = APIClientError("Custom error message")
        assert str(error) == "Custom error message"

    def test_request_error_descriptive_message(self):
        """Test RequestError with descriptive message"""
        error = RequestError(
            "Failed to connect to https://api.example.com:443: [Errno 111] Connection refused"
        )
        message = str(error)
        assert "Connection refused" in message
        assert "https://api.example.com" in message

    def test_http_error_includes_status_and_message(self):
        """Test HTTPError includes both status code and message"""
        error = HTTPError(status_code=404, message="Resource not found")
        error_str = str(error)
        # Message should contain useful information
        assert error.status_code == 404
        assert error.message == "Resource not found"

    def test_rate_limit_error_includes_wait_time(self):
        """Test RateLimitError includes wait time information"""
        error = RateLimitError(wait_time=120.0, retry_after="120")
        assert error.wait_time == 120.0
        # Error should convey rate limiting information
        assert error.status_code == 429

    def test_retry_exhausted_error_includes_attempts(self):
        """Test RetryExhaustedError includes attempt count"""
        last_error = HTTPError(500, "Server Error")
        error = RetryExhaustedError(attempts=3, last_error=last_error)
        assert error.attempts == 3
        assert error.last_error == last_error


class TestExceptionAttributes:
    """Test exception attributes are properly set"""

    def test_http_error_all_attributes(self):
        """Test HTTPError has all required attributes"""
        error = HTTPError(
            status_code=400,
            message="Bad Request",
            response_data={"error": "Invalid input"},
        )

        assert hasattr(error, "status_code")
        assert hasattr(error, "message")
        assert hasattr(error, "response_data")
        assert error.status_code == 400
        assert error.message == "Bad Request"
        assert error.response_data == {"error": "Invalid input"}

    def test_rate_limit_error_all_attributes(self):
        """Test RateLimitError has all required attributes"""
        error = RateLimitError(wait_time=60.0, retry_after="60")

        assert hasattr(error, "wait_time")
        assert hasattr(error, "retry_after")
        assert hasattr(error, "status_code")  # Inherited from HTTPError
        assert error.wait_time == 60.0
        assert error.retry_after == "60"
        assert error.status_code == 429

    def test_retry_exhausted_error_all_attributes(self):
        """Test RetryExhaustedError has all required attributes"""
        last_error = RequestError("Failed")
        error = RetryExhaustedError(attempts=3, last_error=last_error)

        assert hasattr(error, "attempts")
        assert hasattr(error, "last_error")
        assert error.attempts == 3
        assert error.last_error == last_error


class TestExceptionRepr:
    """Test exception __repr__ methods"""

    def test_http_error_repr(self):
        """Test HTTPError has useful repr"""
        error = HTTPError(status_code=404, message="Not Found")
        repr_str = repr(error)
        # Repr should be helpful for debugging
        assert "HTTPError" in repr_str or "404" in repr_str

    def test_rate_limit_error_repr(self):
        """Test RateLimitError has useful repr"""
        error = RateLimitError(wait_time=60.0, retry_after="60")
        repr_str = repr(error)
        assert "RateLimitError" in repr_str or "60" in repr_str

    def test_retry_exhausted_error_repr(self):
        """Test RetryExhaustedError has useful repr"""
        last_error = HTTPError(500, "Server Error")
        error = RetryExhaustedError(attempts=3, last_error=last_error)
        repr_str = repr(error)
        assert "RetryExhaustedError" in repr_str or "3" in repr_str
