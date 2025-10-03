"""Simple tests for TUI testing functionality"""

import pytest

from amplihack.testing import (
    TUITestCase,
    create_amplihack_test,
    create_tui_tester,
    test_amplihack_basics,
)


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
