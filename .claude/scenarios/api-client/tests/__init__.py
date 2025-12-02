"""API Client test suite.

Testing pyramid distribution:
- 60% Unit tests (test_models.py, test_exceptions.py, test_resilience.py)
- 30% Integration tests (test_client.py with mock server)
- 10% E2E tests (test_client.py::TestAPIClientE2E - marked with @pytest.mark.e2e)
"""
