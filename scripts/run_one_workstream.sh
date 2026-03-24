#!/bin/bash
set -e

echo "========================================================================"
echo "WORKSTREAM 1: LLM Agentic Loop - Following DEFAULT WORKFLOW Recipe"
echo "========================================================================"
echo ""
echo "Task: Implement LLM-powered agentic loop for goal-seeking agents"
echo "Recipe: default-workflow.yaml (52 steps)"
echo ""

# Create context file for recipe
cat > recipe_context.json << 'CTX'
{
  "task_description": "Implement LLM-powered agentic loop for goal-seeking agents",
  "requirements": "Add PERCEIVE→REASON→ACT→LEARN cycle with Kuzu memory, action framework. Must pass Wikipedia test L1≥80%, L2≥60%, L3≥40%",
  "repo_path": ".",
  "branch_prefix": "feat"
}
CTX

echo "✓ Created recipe context"
echo ""
echo "Executing default-workflow recipe with Recipe Runner..."
echo "This will execute ALL 52 steps systematically."
echo ""

# Run the recipe
python3 -m amplihack.cli recipe run \
  amplifier-bundle/recipes/default-workflow.yaml \
  -c task_description="Implement LLM-powered agentic loop" \
  -c requirements="PERCEIVE→REASON→ACT→LEARN with Kuzu" \
  -c repo_path="." \
  --verbose
