#!/bin/bash
# Run default model tests with proper environment
PYTHONPATH=src:$PYTHONPATH uv run pytest tests/launcher/test_default_model.py -v --tb=short "$@"
