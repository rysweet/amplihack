"""Smoke test for prepare_amplihack_env and recipe import staging."""

import os
import sys

sys.path.insert(0, "src")


def test_prepare_amplihack_env_sets_vars() -> None:
    from amplihack.launcher import prepare_amplihack_env

    env: dict[str, str] = {}
    prepare_amplihack_env(env, "test")
    assert env["AMPLIHACK_AGENT_BINARY"] == "test", f"got {env.get('AMPLIHACK_AGENT_BINARY')}"
    assert "AMPLIHACK_HOME" in env, "AMPLIHACK_HOME not set"
    assert env["PYTHONPATH"].endswith("/src") or "/src:" in env["PYTHONPATH"], (
        f"PYTHONPATH wrong: {env['PYTHONPATH']}"
    )
    print("PREPARE_ENV_OK")


def test_no_duplicate_pythonpath() -> None:
    from amplihack.launcher import prepare_amplihack_env

    env: dict[str, str] = {"AMPLIHACK_HOME": "/tmp/test-ah"}
    prepare_amplihack_env(env, "test")
    prepare_amplihack_env(env, "test")
    parts = env["PYTHONPATH"].split(os.pathsep)
    count = sum(1 for p in parts if p == "/tmp/test-ah/src")
    assert count == 1, f"PYTHONPATH duplicated: {env['PYTHONPATH']}"
    print("NO_DUPLICATE_OK")


def test_recipes_importable() -> None:
    from amplihack.recipes import run_recipe_by_name

    assert callable(run_recipe_by_name)
    print("RECIPES_IMPORT_OK")


def test_prepare_in_all() -> None:
    import amplihack.launcher

    assert "prepare_amplihack_env" in amplihack.launcher.__all__
    print("IN_ALL_OK")


if __name__ == "__main__":
    test_prepare_amplihack_env_sets_vars()
    test_no_duplicate_pythonpath()
    test_recipes_importable()
    test_prepare_in_all()
    print("ALL_STAGING_TESTS_PASSED")
