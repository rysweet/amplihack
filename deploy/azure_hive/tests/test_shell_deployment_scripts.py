from __future__ import annotations

import os
import subprocess
import textwrap
from pathlib import Path


_AZURE_HIVE_DIR = Path(__file__).resolve().parents[1]


def _write_fake_az(tmp_path: Path, script: str) -> Path:
    fake_az = tmp_path / "az"
    fake_az.write_text(textwrap.dedent(script), encoding="utf-8")
    fake_az.chmod(0o755)
    return fake_az


def _script_env(tmp_path: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["PATH"] = f"{tmp_path}:{env['PATH']}"
    env["ANTHROPIC_API_KEY"] = "test-key"
    return env


def test_deploy_script_fails_loudly_when_acr_create_fails(tmp_path: Path):
    _write_fake_az(
        tmp_path,
        """\
        #!/usr/bin/env python3
        import json
        import sys

        args = sys.argv[1:]
        if args[:2] == ["group", "create"]:
            sys.exit(0)
        if args[:2] == ["acr", "list"]:
            print("")
            sys.exit(0)
        if args[:2] == ["acr", "check-name"]:
            print(json.dumps({"nameAvailable": True}))
            sys.exit(0)
        if args[:2] == ["acr", "create"]:
            print("acr create boom", file=sys.stderr)
            sys.exit(1)
        raise SystemExit(f"unexpected az invocation: {args!r}")
        """,
    )

    result = subprocess.run(
        ["bash", str(_AZURE_HIVE_DIR / "deploy.sh"), "--infra-only"],
        capture_output=True,
        text=True,
        env=_script_env(tmp_path),
    )

    assert result.returncode == 1
    assert "Failed to create ACR" in result.stderr
    assert "acr create boom" in result.stderr


def test_deploy_status_fails_when_resource_group_is_missing(tmp_path: Path):
    _write_fake_az(
        tmp_path,
        """\
        #!/usr/bin/env python3
        import sys

        args = sys.argv[1:]
        if args[:2] == ["group", "show"]:
            print("resource group missing", file=sys.stderr)
            sys.exit(3)
        raise SystemExit(f"unexpected az invocation: {args!r}")
        """,
    )

    result = subprocess.run(
        ["bash", str(_AZURE_HIVE_DIR / "deploy.sh"), "--status"],
        capture_output=True,
        text=True,
        env=dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}"),
    )

    assert result.returncode == 1
    assert "Resource group hive-mind-rg not found." in result.stderr


def test_cleanup_volumes_fails_when_share_delete_fails(tmp_path: Path):
    _write_fake_az(
        tmp_path,
        """\
        #!/usr/bin/env python3
        import sys

        args = sys.argv[1:]
        if args[:3] == ["storage", "account", "list"]:
            print("hivesatest")
            sys.exit(0)
        if args[:4] == ["storage", "account", "keys", "list"]:
            print("fake-key")
            sys.exit(0)
        if args[:3] == ["storage", "file", "list"]:
            query = args[args.index("--query") + 1]
            if "type=='file'" in query:
                print("stale.db")
            else:
                print("")
            sys.exit(0)
        if args[:3] == ["storage", "file", "delete"]:
            print("delete failed", file=sys.stderr)
            sys.exit(1)
        raise SystemExit(f"unexpected az invocation: {args!r}")
        """,
    )

    result = subprocess.run(
        ["bash", str(_AZURE_HIVE_DIR / "cleanup_volumes.sh")],
        capture_output=True,
        text=True,
        env=dict(os.environ, PATH=f"{tmp_path}:{os.environ['PATH']}"),
    )

    assert result.returncode == 1
    assert "Failed to delete file 'stale.db'" in result.stderr
    assert "Cleanup incomplete" in result.stderr
