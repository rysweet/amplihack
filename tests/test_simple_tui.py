"""Simple tests for TUI testing functionality"""

import os

import pytest

from amplihack.testing import (
    TUITestCase,
    create_amplihack_test,
    create_tui_tester,
    test_amplihack_basics,
)


@pytest.fixture(scope="session", autouse=True)
def ci_environment_setup():
    """Set up CI-friendly environment for all TUI tests"""
    # Ensure CI-friendly environment variables are set
    original_env = {}
    ci_vars = {
        "CI": "true",
        "DEBIAN_FRONTEND": "noninteractive",
        "NPX_NO_INSTALL": "1",
        "AMPLIHACK_DEBUG": "false",
    }

    for key, value in ci_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    yield

    # Restore original environment
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.mark.asyncio
async def test_simple_tui_tester():
    """Test basic SimpleTUITester functionality"""
    tester = create_tui_tester()

    # Add a simple test
    test_case = TUITestCase("test1", "Test 1", ["echo hello"])
    tester.add_test(test_case)

    # Run the test
    result = await tester.run_test("test1")

    assert result.test_id == "test1"
    assert result.status == "passed"
    assert result.duration >= 0


@pytest.mark.asyncio
async def test_failing_test():
    """Test that failing tests are detected"""
    tester = create_tui_tester()

    # Add a test that should fail
    test_case = TUITestCase("fail_test", "Fail Test", ["fail_command"])
    tester.add_test(test_case)

    result = await tester.run_test("fail_test")

    assert result.test_id == "fail_test"
    assert result.status == "failed"


@pytest.mark.asyncio
async def test_amplihack_cli_tests():
    """Test AmplIHack CLI test creation"""
    test_case = create_amplihack_test("help", "--help")

    assert test_case.test_id == "help"
    assert test_case.name == "AmplIHack --help"
    assert test_case.commands == ["amplihack --help"]


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="Skipping amplihack CLI tests in CI - command not installed",
)
async def test_basic_amplihack_suite():
    """Test the basic AmplIHack test suite"""
    results = await test_amplihack_basics()

    assert "help" in results
    assert "install_help" in results
    assert results["help"].status == "passed"
    assert results["install_help"].status == "passed"


@pytest.mark.asyncio
async def test_run_all_tests():
    """Test running multiple tests"""
    tester = create_tui_tester()

    # Add multiple tests
    tester.add_test(TUITestCase("test1", "Test 1", ["echo hello"]))
    tester.add_test(TUITestCase("test2", "Test 2", ["echo world"]))

    results = await tester.run_all()

    assert len(results) == 2
    assert all(r.status == "passed" for r in results.values())
