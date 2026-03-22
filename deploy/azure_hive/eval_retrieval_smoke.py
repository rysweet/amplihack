#!/usr/bin/env python3
"""Compatibility wrapper for retrieval smoke now living in amplihack-agent-eval."""

from amplihack_eval.azure.eval_retrieval_smoke import main

if __name__ == "__main__":
    raise SystemExit(main())
