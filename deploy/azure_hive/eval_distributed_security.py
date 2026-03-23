#!/usr/bin/env python3
"""Compatibility wrapper for distributed security eval now living in amplihack-agent-eval."""

from amplihack_eval.azure.eval_distributed_security import main

if __name__ == "__main__":
    raise SystemExit(main())
