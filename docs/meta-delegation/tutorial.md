# Meta-Delegation Tutorial

**Learn meta-delegation through hands-on examples in 30 minutes.**

---

## Prerequisites

Before starting this tutorial, you should have:

- amplihack installed and working
- Familiarity with Python
- Basic understanding of AI agents
- 30 minutes of focused time

## What You'll Learn

By the end of this tutorial, you'll be able to:

1. Run basic meta-delegation tasks
2. Choose the right persona for your task
3. Write effective success criteria
4. Interpret results and evidence
5. Handle failures and partial successes

---

## Step 1: Your First Meta-Delegation (5 minutes)

Let's start with a simple task: creating a Python function with tests.

### Create a Python Script

```python
# first_meta_delegation.py
from amplihack.meta_delegation import run_meta_delegation

# Define what we want
goal = "Create a Python function that calculates factorial of a number"
success_criteria = "Function exists, handles edge cases, has tests, all tests pass"

# Run meta-delegation
result = run_meta_delegation(
    goal=goal,
    success_criteria=success_criteria,
    persona_type="junior_dev",
    platform="claude-code"
)

# Check results
print(f"Status: {result.status}")
print(f"Success Score: {result.success_score}/100")
print(f"\nEvidence collected:")
for item in result.evidence:
    print(f"  - {item.type}: {item.path}")
```

### Run It

```bash
python first_meta_delegation.py
```

### Expected Output

```
[Meta-Delegator] Starting subprocess with junior_dev persona
[Meta-Delegator] Subprocess running (PID: 12345)
[Meta-Delegator] Task in progress...
[Meta-Delegator] Task completed in 45 seconds
[Meta-Delegator] Collecting evidence...
[Meta-Delegator] Evaluating success criteria...

Status: SUCCESS
Success Score: 95/100

Evidence collected:
  - code_file: factorial.py
  - test_file: test_factorial.py
  - execution_log: subprocess_output.log
```

### What Happened?

1. **Subprocess Created**: A new isolated environment was created
2. **Agent Executed**: The junior_dev agent ran Claude Code/Copilot/Amplifier
3. **Code Generated**: The agent created `factorial.py` and `test_factorial.py`
4. **Tests Run**: The agent executed tests to validate the implementation
5. **Evidence Collected**: All artifacts were captured
6. **Success Evaluated**: The evaluator scored the results

---

## Step 2: Understanding Personas (10 minutes)

Personas change how the agent approaches your task. Let's compare.

### Experiment: Same Task, Different Personas

```python
# persona_comparison.py
from amplihack.meta_delegation import run_meta_delegation

goal = "Analyze the security of a user authentication system"
success_criteria = "Identify vulnerabilities, suggest fixes, provide examples"

# Try each persona
personas = ["guide", "qa_engineer", "architect", "junior_dev"]
results = {}

for persona in personas:
    print(f"\n{'='*60}")
    print(f"Running with {persona} persona...")
    print('='*60)

    result = run_meta_delegation(
        goal=goal,
        success_criteria=success_criteria,
        persona_type=persona,
        platform="claude-code"
    )

    results[persona] = result
    print(f"Status: {result.status}")
    print(f"Score: {result.success_score}/100")
    print(f"Evidence: {len(result.evidence)} items")

# Compare results
print("\n" + "="*60)
print("COMPARISON")
print("="*60)
for persona, result in results.items():
    print(f"{persona:12} | Score: {result.success_score:3}/100 | Evidence: {len(result.evidence):2} items")
```

### Expected Output

```
============================================================
Running with guide persona...
============================================================
[Meta-Delegator] Guide persona: Using Socratic approach...
Status: SUCCESS
Score: 88/100
Evidence: 8 items

============================================================
Running with qa_engineer persona...
============================================================
[Meta-Delegator] QA Engineer persona: Using rigorous testing approach...
Status: SUCCESS
Score: 95/100
Evidence: 15 items

============================================================
Running with architect persona...
============================================================
[Meta-Delegator] Architect persona: Using strategic design approach...
Status: SUCCESS
Score: 90/100
Evidence: 10 items

============================================================
Running with junior_dev persona...
============================================================
[Meta-Delegator] Junior Dev persona: Using task-focused approach...
Status: SUCCESS
Score: 78/100
Evidence: 6 items

============================================================
COMPARISON
============================================================
guide        | Score:  88/100 | Evidence:  8 items
qa_engineer  | Score:  95/100 | Evidence: 15 items
architect    | Score:  90/100 | Evidence: 10 items
junior_dev   | Score:  78/100 | Evidence:  6 items
```

### Analysis

- **QA Engineer**: Most thorough, highest score, most evidence (perfect for security analysis)
- **Architect**: Strategic overview, good documentation, solid score
- **Guide**: Explanatory, educational approach, balanced evidence
- **Junior Dev**: Task-focused, less comprehensive but fast

**Lesson**: Choose persona based on what you need:
- Need teaching? → `guide`
- Need thoroughness? → `qa_engineer`
- Need design? → `architect`
- Need quick implementation? → `junior_dev`

---

## Step 3: Writing Effective Success Criteria (5 minutes)

Success criteria determine how well the agent succeeded. Let's practice writing good ones.

### Bad Success Criteria ❌

```python
# Too vague
success_criteria = "Make it good"

# Not measurable
success_criteria = "Code should be clean"

# Too strict
success_criteria = "Must achieve 100% code coverage"
```

### Good Success Criteria ✅

```python
# Specific and measurable
success_criteria = """
- Function accepts integer input
- Returns correct factorial value
- Handles n=0 (returns 1)
- Handles negative numbers (raises ValueError)
- Has at least 5 test cases
- All tests pass
"""

# Clear deliverables
success_criteria = """
Deliverables:
1. Working implementation in calculator.py
2. Test suite in test_calculator.py with >80% coverage
3. README.md with usage examples
4. All tests pass
"""
```

### Exercise: Write Your Own

Try improving these criteria:

**Original:**
```python
goal = "Create a REST API"
success_criteria = "API works"
```

**Improved:**
```python
goal = "Create a REST API for user management"
success_criteria = """
- API has GET /users endpoint (returns user list)
- API has POST /users endpoint (creates user)
- API validates required fields (name, email)
- Returns proper HTTP status codes (200, 201, 400)
- Has tests for each endpoint
- All tests pass
"""
```

---

## Step 4: Interpreting Evidence (5 minutes)

Evidence is proof of what the agent accomplished. Let's analyze it.

### Example: Examining Evidence

```python
# examine_evidence.py
from amplihack.meta_delegation import run_meta_delegation

result = run_meta_delegation(
    goal="Create a module for parsing CSV files",
    success_criteria="Module can read CSV, handle errors, has tests",
    persona_type="junior_dev"
)

print(f"Status: {result.status}\n")

# Group evidence by type
evidence_by_type = {}
for item in result.evidence:
    if item.type not in evidence_by_type:
        evidence_by_type[item.type] = []
    evidence_by_type[item.type].append(item)

# Display organized evidence
for evidence_type, items in evidence_by_type.items():
    print(f"{evidence_type.upper()}:")
    for item in items:
        print(f"  - {item.path}")
        if item.excerpt:
            print(f"    Preview: {item.excerpt[:100]}...")
    print()

# Read specific evidence
code_files = result.get_evidence_by_type("code_file")
if code_files:
    main_code = code_files[0]
    print(f"\nGenerated Code ({main_code.path}):")
    print("=" * 60)
    print(main_code.content)
```

### Expected Output

```
Status: SUCCESS

CODE_FILE:
  - csv_parser.py
    Preview: import csv\nfrom typing import List, Dict\n\nclass CSVParser:\n    def __init__(self, file_p...
  - __init__.py
    Preview: from .csv_parser import CSVParser\n\n__all__ = ['CSVParser']\n...

TEST_FILE:
  - test_csv_parser.py
    Preview: import pytest\nfrom csv_parser import CSVParser\n\nclass TestCSVParser:\n    def test_ba...

DOCUMENTATION:
  - README.md
    Preview: # CSV Parser Module\n\nA simple CSV parsing module with error handling.\n\n## Usage\...

EXECUTION_LOG:
  - subprocess_output.log
    Preview: [2026-01-20 10:30:15] Starting task: Create a module for parsing CSV files\n[202...

Generated Code (csv_parser.py):
============================================================
import csv
from typing import List, Dict

class CSVParser:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def parse(self) -> List[Dict[str, str]]:
        """Parse CSV file and return list of dictionaries."""
        try:
            with open(self.file_path, 'r') as f:
                reader = csv.DictReader(f)
                return list(reader)
        except FileNotFoundError:
            raise ValueError(f"File not found: {self.file_path}")
        except csv.Error as e:
            raise ValueError(f"CSV parsing error: {e}")
```

### Evidence Types

Common evidence types you'll see:

- **code_file**: Source code files generated
- **test_file**: Test files created
- **documentation**: README, guides, specs
- **execution_log**: Full subprocess output
- **test_results**: Test run output
- **validation_report**: Success criteria evaluation details

---

## Step 5: Handling Failures (5 minutes)

Not all delegations succeed. Let's learn to handle failures gracefully.

### Example: Dealing with Failure

```python
# handle_failures.py
from amplihack.meta_delegation import run_meta_delegation

# Intentionally difficult task
goal = "Implement a quantum computer simulator in Python"
success_criteria = """
- Simulates quantum gates (Hadamard, CNOT, Pauli)
- Handles multi-qubit systems
- Has comprehensive tests
- All tests pass
"""

result = run_meta_delegation(
    goal=goal,
    success_criteria=success_criteria,
    persona_type="junior_dev",
    platform="claude-code"
)

# Handle different outcomes
if result.status == "SUCCESS":
    print("✓ Task completed successfully!")
    print(f"Score: {result.success_score}/100")

elif result.status == "PARTIAL":
    print("⚠ Task partially completed")
    print(f"Score: {result.success_score}/100")
    print(f"\nWhat was achieved:")
    for item in result.evidence:
        print(f"  - {item.type}: {item.path}")

    print(f"\nWhat's missing:")
    print(result.partial_completion_notes)

else:  # FAILURE
    print("✗ Task failed")
    print(f"Score: {result.success_score}/100")
    print(f"Reason: {result.failure_reason}")

    print(f"\nDiagnostic information:")
    print(f"Execution time: {result.duration_seconds}s")

    # Check logs for clues
    log_evidence = result.get_evidence_by_type("execution_log")
    if log_evidence:
        log = log_evidence[0]
        print(f"\nLast 20 lines of execution log:")
        lines = log.content.split('\n')
        print('\n'.join(lines[-20:]))
```

### Expected Output (Partial Success)

```
⚠ Task partially completed
Score: 65/100

What was achieved:
  - code_file: quantum_simulator.py
  - test_file: test_quantum_simulator.py
  - documentation: README.md
  - execution_log: subprocess_output.log

What's missing:
- Multi-qubit CNOT gate not fully implemented
- Only 8 of 12 tests passing
- Performance tests missing

Recommendations:
1. Review the partial implementation in quantum_simulator.py
2. Complete the CNOT gate implementation
3. Fix the 4 failing tests
4. Consider splitting into multiple delegations
```

### Recovery Strategies

When delegation fails or partially succeeds:

1. **Review Evidence**: Check what was produced
2. **Analyze Logs**: Look for error messages
3. **Adjust Task Scope**: Break into smaller pieces
4. **Try Different Persona**: QA engineer might find issues guide missed
5. **Refine Success Criteria**: Make them more specific or achievable

---

## Putting It All Together

### Final Exercise: Complete Workflow

Create a meta-delegation for a real task:

```python
# complete_workflow.py
from amplihack.meta_delegation import run_meta_delegation

# Step 1: Design phase
print("Phase 1: Architecture Design")
design_result = run_meta_delegation(
    goal="Design a Python package for sending email notifications",
    success_criteria="""
    - Architecture document with module structure
    - API specification with function signatures
    - Error handling strategy
    - Documentation plan
    """,
    persona_type="architect"
)

if design_result.status != "SUCCESS":
    print(f"Design failed: {design_result.failure_reason}")
    exit(1)

print(f"✓ Design complete (score: {design_result.success_score}/100)\n")

# Step 2: Implementation phase
print("Phase 2: Implementation")
impl_result = run_meta_delegation(
    goal="Implement the email notification package following the architecture",
    success_criteria="""
    - email_notifier.py with send_email() function
    - Support for SMTP and SendGrid backends
    - Configuration via environment variables
    - Has comprehensive tests
    - All tests pass
    """,
    persona_type="junior_dev",
    # Pass context from design phase
    context=design_result.get_evidence_by_type("architecture_doc")[0].content
)

if impl_result.status != "SUCCESS":
    print(f"Implementation failed: {impl_result.failure_reason}")
    exit(1)

print(f"✓ Implementation complete (score: {impl_result.success_score}/100)\n")

# Step 3: QA phase
print("Phase 3: Quality Assurance")
qa_result = run_meta_delegation(
    goal="Perform thorough QA on the email notification package",
    success_criteria="""
    - Identify any bugs or issues
    - Verify test coverage >85%
    - Check error handling
    - Validate documentation
    - Generate QA report
    """,
    persona_type="qa_engineer"
)

print(f"✓ QA complete (score: {qa_result.success_score}/100)\n")

# Summary
print("="*60)
print("PROJECT COMPLETE")
print("="*60)
print(f"Design score: {design_result.success_score}/100")
print(f"Implementation score: {impl_result.success_score}/100")
print(f"QA score: {qa_result.success_score}/100")
print(f"Overall: {(design_result.success_score + impl_result.success_score + qa_result.success_score) / 3:.1f}/100")
```

---

## What's Next?

You've completed the tutorial! You now know how to:

- ✓ Run basic meta-delegations
- ✓ Choose appropriate personas
- ✓ Write effective success criteria
- ✓ Interpret evidence and results
- ✓ Handle failures and partial successes

### Continue Learning

- **[How-To Guide](./howto.md)**: Common recipes and patterns
- **[Concepts](./concepts.md)**: Deep dive into architecture
- **[Reference](./reference.md)**: Complete API documentation
- **[Troubleshooting](./troubleshooting.md)**: Fix common problems

### Try These Advanced Topics

1. **Custom Scenarios**: Use Gadugi to generate test scenarios
2. **Evidence Filtering**: Find specific artifacts in results
3. **Multi-Platform**: Run same task on different platforms
4. **Chained Delegations**: Pipeline multiple agents together

---

**Status**: [PLANNED - Implementation Pending]

This tutorial describes the intended usage of the meta-delegation system once implemented.
