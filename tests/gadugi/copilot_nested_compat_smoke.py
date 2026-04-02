#!/usr/bin/env python3
"""Outside-in smoke harness for nested Copilot compatibility."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def _load_rust_runner_module(repo_root: Path):
    sys.path.insert(0, str(repo_root / "src"))
    from amplihack.recipes import rust_runner

    return rust_runner


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    rust_runner = _load_rust_runner_module(repo_root)

    fake_binary_dir = Path(tempfile.mkdtemp(prefix="copilot-real-"))
    fake_binary = fake_binary_dir / "copilot-real"
    fake_binary.write_text(
        "#!/usr/bin/env python3\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\n",
        encoding="utf-8",
    )
    fake_binary.chmod(0o755)

    wrapper_dir = Path(rust_runner._create_copilot_compat_wrapper_dir(str(fake_binary)))
    wrapper = wrapper_dir / "copilot"

    command = [
        str(wrapper),
        "--system-prompt",
        "architect instructions",
        "--append-system-prompt=extra instructions",
        "--allow-tool=shell(git)",
        "--allow-path=/repo",
        "-p",
        "user prompt",
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    argv = json.loads(result.stdout)

    expected_prompt = "architect instructions\n\nextra instructions\n\nuser prompt"
    if argv != ["--allow-tool=shell(git)", "--allow-path=/repo", "-p", expected_prompt]:
        raise RuntimeError(f"Unexpected normalized argv: {argv}")

    blocked_command = [
        str(wrapper),
        "--dangerously-skip-permissions",
        "--disallowed-tools=Bash,Write",
        "-p",
        "classify only",
    ]
    blocked_result = subprocess.run(blocked_command, check=True, capture_output=True, text=True)
    blocked_argv = json.loads(blocked_result.stdout)
    blocked_prompt = (
        "Tool use is forbidden for this invocation. "
        "Do not call any tools. Original disallowed tool list: Bash, Write."
        "\n\nclassify only"
    )
    if blocked_argv != ["--allow-all-paths", "-p", blocked_prompt]:
        raise RuntimeError(f"Unexpected blocked normalized argv: {blocked_argv}")

    print("PROMPT_COMPAT_OK")
    print("PERMISSION_COMPAT_OK")
    print("CLAUDE_FLAG_COMPAT_OK")
    print(f"ARGS_JSON={json.dumps(argv)}")
    print("SMOKE_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
