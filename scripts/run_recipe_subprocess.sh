#!/bin/bash

python3 -m amplihack.cli recipe run \
  amplifier-bundle/recipes/default-workflow.yaml \
  -c task_description="LLM agentic loop" \
  -c requirements="PERCEIVE→REASON→ACT→LEARN with litellm + Kuzu" \
  -c repo_path="." \
  --verbose
