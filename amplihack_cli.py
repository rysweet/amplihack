import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HOME = str(Path.home())
CLAUDE_DIR = os.path.join(HOME, ".claude")
CLI_NAME = "amplihack_cli.py"
CLI_SRC = os.path.abspath(__file__)
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))


def ensure_dirs():
    os.makedirs(CLAUDE_DIR, exist_ok=True)


MANIFEST_JSON = os.path.join(CLAUDE_DIR, "install", "amplihack-manifest.json")


def copytree_manifest(src, dst, rel_top=".claude"):
    search_dirs = ["agents", "commands", "tools"]
    base = os.path.join(src, rel_top)
    copied = []
    for dname in search_dirs:
        absdir = os.path.join(base, dname)
        if not os.path.exists(absdir):
            continue
        target_dir = os.path.join(dst, dname)
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        shutil.copytree(absdir, target_dir)
        copied.append(dname)
    return copied


def write_manifest(files, dirs):
    os.makedirs(os.path.dirname(MANIFEST_JSON), exist_ok=True)
    with open(MANIFEST_JSON, "w", encoding="utf-8") as f:
        json.dump({"files": files, "dirs": dirs}, f, indent=2)


def read_manifest():
    try:
        with open(MANIFEST_JSON, encoding="utf-8") as f:
            mf = json.load(f)
            return mf.get("files", []), mf.get("dirs", [])
    except Exception:
        return [], []


def get_all_files_and_dirs(root_dirs):
    all_files = []
    all_dirs = set()
    for d in root_dirs:
        if not os.path.exists(d):
            continue
        for r, dirs, files in os.walk(d):
            rel_dir = os.path.relpath(r, CLAUDE_DIR)
            all_dirs.add(rel_dir)
            for f in files:
                rel_path = os.path.relpath(os.path.join(r, f), CLAUDE_DIR)
                all_files.append(rel_path)
    return sorted(all_files), sorted(all_dirs)


def all_rel_dirs(base):
    # Returns all directories under base as relative paths (including base='.')
    result = set()
    for r, dirs, _files in os.walk(base):
        rel = os.path.relpath(r, CLAUDE_DIR)
        result.add(rel)
    return result


def install():
    ensure_dirs()
    # Compute dirs pre-copy
    pre_dirs = all_rel_dirs(CLAUDE_DIR)
    copytree_manifest(REPO_ROOT, CLAUDE_DIR)
    root_dirs = [os.path.join(CLAUDE_DIR, d) for d in ["agents", "commands", "tools"]]
    files, post_dirs = get_all_files_and_dirs(root_dirs)
    # Only keep created dirs
    new_dirs = sorted(set(post_dirs) - pre_dirs)
    write_manifest(files, new_dirs)
    print(
        f"Installed .claude/agents, .claude/commands, .claude/tools to {CLAUDE_DIR}. Manifest with files and newly created dirs written to {MANIFEST_JSON}."
    )


def uninstall():
    removed_any = False
    files, dirs = read_manifest()
    # Remove files first
    for f in files:
        target = os.path.join(CLAUDE_DIR, f)
        if os.path.isfile(target):
            os.remove(target)
            removed_any = True
    # Remove directories (deepest first)
    for d in sorted(dirs, key=lambda x: -x.count(os.sep)):
        target = os.path.join(CLAUDE_DIR, d)
        if os.path.isdir(target):
            shutil.rmtree(target, ignore_errors=True)
            removed_any = True
    try:
        os.remove(MANIFEST_JSON)
    except Exception:
        pass
    if removed_any:
        print(f"Removed all amplihack files/directories per manifest from {CLAUDE_DIR}")
    else:
        print("Nothing to uninstall.")


def filecmp(f1, f2):
    try:
        if os.path.getsize(f1) != os.path.getsize(f2):
            return False
        with open(f1, "rb") as file1, open(f2, "rb") as file2:
            return file1.read() == file2.read()
    except Exception:
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: amplihack install | uninstall")
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == "install":
        # Clone repo to tempdir, run amplihack_cli.py install in clone
        with tempfile.TemporaryDirectory() as tmp:
            repo_url = "https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding"
            subprocess.check_call(["git", "clone", "--depth", "1", repo_url, tmp])
            # When debugging locally, if the repo does not contain the latest version of this file, uncomment the line below
            # subprocess.check_call(["cp", "amplihack_cli.py", tmp])
            subprocess.check_call(
                [sys.executable, os.path.join(tmp, "amplihack_cli.py"), "_local_install"]
            )
    elif cmd == "uninstall":
        uninstall()
    elif cmd == "_local_install":
        install()
    else:
        print("Invalid command. Use install or uninstall.")
        sys.exit(1)


if __name__ == "__main__":
    main()
