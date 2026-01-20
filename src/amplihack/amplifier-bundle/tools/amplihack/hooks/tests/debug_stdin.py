#!/usr/bin/env python3
"""Debug stdin state during test execution"""

import os
import sys

sys.path.insert(0, "..")

from shutdown_context import _is_in_atexit_context, _is_stdin_closed, is_shutdown_in_progress

print(
    f"ENV: AMPLIHACK_SHUTDOWN_IN_PROGRESS = {os.environ.get('AMPLIHACK_SHUTDOWN_IN_PROGRESS', 'NOT SET')}"
)
print(f"is_shutdown_in_progress() = {is_shutdown_in_progress()}")
print(f"_is_stdin_closed() = {_is_stdin_closed()}")
print(f"_is_in_atexit_context() = {_is_in_atexit_context()}")
print(f"sys.stdin = {sys.stdin}")
print(f"hasattr(sys.stdin, 'closed') = {hasattr(sys.stdin, 'closed')}")
if hasattr(sys.stdin, "closed"):
    print(f"sys.stdin.closed = {sys.stdin.closed}")
try:
    fileno = sys.stdin.fileno()
    print(f"sys.stdin.fileno() = {fileno}")
except Exception as e:
    print(f"sys.stdin.fileno() raised: {type(e).__name__}: {e}")
