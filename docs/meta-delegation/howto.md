# Meta-Delegation How-To Guide

**Task-focused recipes for common meta-delegation scenarios.**

---

## Quick Reference

Jump to a specific task:

- [Run a Simple Delegation](#run-a-simple-delegation)
- [Choose the Right Persona](#choose-the-right-persona)
- [Pass Context Between Delegations](#pass-context-between-delegations)
- [Filter and Search Evidence](#filter-and-search-evidence)
- [Handle Timeouts](#handle-timeouts)
- [Retry Failed Delegations](#retry-failed-delegations)
- [Run on Different Platforms](#run-on-different-platforms)
- [Generate Test Scenarios](#generate-test-scenarios)
- [Export Evidence as Archive](#export-evidence-as-archive)
- [Chain Multiple Delegations](#chain-multiple-delegations)

---

## Run a Simple Delegation

**Problem**: You need to delegate a task to an AI agent.

**Solution**:

```python
from amplihack.meta_delegation import run_meta_delegation

result = run_meta_delegation(
    goal="Create a function to validate email addresses",
    success_criteria="Function exists, handles invalid emails, has tests"
)

print(f"Status: {result.status}")
# Output: Status: SUCCESS
```

**Default behavior**:
- Platform: `claude-code`
- Persona: `guide`
- Timeout: 30 minutes

---

## Choose the Right Persona

**Problem**: You need to pick the best persona for your task.

**Decision Tree**:

```
What is your primary goal?
│
├─ Teaching/Learning
│  └─> Use "guide"
│      • Socratic approach
│      • Explanatory
│      • Best for understanding
│
├─ Thorough Testing/Validation
│  └─> Use "qa_engineer"
│      • Rigorous verification
│      • Comprehensive evidence
│      • Best for quality assurance
│
├─ System Design/Architecture
│  └─> Use "architect"
│      • Strategic planning
│      • High-level overview
│      • Best for specifications
│
└─ Quick Implementation
   └─> Use "junior_dev"
       • Task-focused
       • Gets it done
       • Best for straightforward coding
```

**Examples**:

```python
# Teaching scenario
run_meta_delegation(
    goal="Explain how OAuth2 works and implement a simple example",
    success_criteria="Clear explanation, working code, step-by-step guide",
    persona_type="guide"  # Best for teaching
)

# Testing scenario
run_meta_delegation(
    goal="Analyze this API for security vulnerabilities",
    success_criteria="Identify issues, test exploits, provide fixes",
    persona_type="qa_engineer"  # Best for thorough testing
)

# Design scenario
run_meta_delegation(
    goal="Design a microservices architecture for an e-commerce platform",
    success_criteria="Architecture diagram, service boundaries, API specs",
    persona_type="architect"  # Best for design
)

# Implementation scenario
run_meta_delegation(
    goal="Implement the shopping cart service from this spec",
    success_criteria="Working code, follows spec, has basic tests",
    persona_type="junior_dev"  # Best for implementation
)
```

---

## Pass Context Between Delegations

**Problem**: You want the second delegation to use results from the first.

**Solution**:

```python
from amplihack.meta_delegation import run_meta_delegation

# Step 1: Design phase
design = run_meta_delegation(
    goal="Design a user authentication system",
    success_criteria="Architecture doc, API spec, security considerations",
    persona_type="architect"
)

# Step 2: Get design document from evidence
arch_doc = design.get_evidence_by_type("architecture_doc")[0]

# Step 3: Implementation phase with context
implementation = run_meta_delegation(
    goal="Implement the authentication system",
    success_criteria="Working code following the architecture, tests pass",
    persona_type="junior_dev",
    context=arch_doc.content  # Pass design as context
)

print(f"Design score: {design.success_score}/100")
print(f"Implementation score: {implementation.success_score}/100")
```

**Output**:

```
Design score: 92/100
Implementation score: 88/100
```

**Tip**: Always extract relevant evidence before passing as context to keep it focused.

---

## Filter and Search Evidence

**Problem**: You need to find specific artifacts in the evidence.

**Solution**:

```python
result = run_meta_delegation(
    goal="Create a web scraper for news articles",
    success_criteria="Scraper works, handles errors, has tests"
)

# Method 1: Get evidence by type
code_files = result.get_evidence_by_type("code_file")
for code in code_files:
    print(f"Code file: {code.path}")
    # Output: Code file: scraper.py

# Method 2: Filter evidence with custom logic
test_files = [e for e in result.evidence if e.path.startswith("test_")]
for test in test_files:
    print(f"Test file: {test.path}")
    # Output: Test file: test_scraper.py

# Method 3: Search evidence content
import re
documentation = [
    e for e in result.evidence
    if e.type == "documentation" and re.search(r"usage|example", e.content, re.I)
]
for doc in documentation:
    print(f"Documentation with examples: {doc.path}")
    # Output: Documentation with examples: README.md

# Method 4: Get evidence by filename pattern
import fnmatch
py_files = [
    e for e in result.evidence
    if fnmatch.fnmatch(e.path, "*.py") and e.type == "code_file"
]
print(f"Found {len(py_files)} Python files")
# Output: Found 2 Python files
```

---

## Handle Timeouts

**Problem**: Your delegation is taking too long and you want to control timeout behavior.

**Solution**:

```python
from amplihack.meta_delegation import run_meta_delegation, DelegationTimeout

# Set custom timeout
try:
    result = run_meta_delegation(
        goal="Perform comprehensive security audit",
        success_criteria="Check all OWASP Top 10, generate report",
        timeout_minutes=60  # Allow 1 hour
    )
except DelegationTimeout as e:
    print(f"Delegation timed out after {e.elapsed_minutes} minutes")
    print(f"Partial results: {e.partial_result}")

    # Access what was completed
    if e.partial_result:
        print(f"Evidence collected before timeout: {len(e.partial_result.evidence)}")
        for item in e.partial_result.evidence:
            print(f"  - {item.path}")
```

**Output**:

```
Delegation timed out after 60 minutes
Partial results: MetaDelegationResult(status='PARTIAL', success_score=55)
Evidence collected before timeout: 8
  - security_scan_partial.md
  - vulnerability_report_incomplete.md
  - test_results.log
  - [... 5 more items ...]
```

**Best Practices**:

- Default timeout (30 min) works for most tasks
- Use 60+ minutes for complex analyses
- Always catch `DelegationTimeout` for long-running tasks
- Partial results are still valuable

---

## Retry Failed Delegations

**Problem**: A delegation failed, and you want to retry with adjustments.

**Solution**:

```python
from amplihack.meta_delegation import run_meta_delegation

goal = "Implement a Redis cache wrapper"
success_criteria = "Wrapper works, handles connection errors, has tests"

# First attempt
result = run_meta_delegation(goal=goal, success_criteria=success_criteria)

if result.status == "FAILURE":
    print(f"Failed with score {result.success_score}/100")
    print(f"Reason: {result.failure_reason}")

    # Strategy 1: Simplify success criteria
    simpler_criteria = "Wrapper works for basic get/set, has minimal tests"
    result = run_meta_delegation(goal=goal, success_criteria=simpler_criteria)

if result.status == "PARTIAL":
    print(f"Partial success: {result.success_score}/100")

    # Strategy 2: Change persona (try qa_engineer for thoroughness)
    result = run_meta_delegation(
        goal=goal,
        success_criteria=success_criteria,
        persona_type="qa_engineer"
    )

if result.status == "SUCCESS":
    print(f"Success on retry: {result.success_score}/100")
```

**Retry Strategies**:

1. **Simplify criteria**: Remove optional requirements
2. **Change persona**: Try `qa_engineer` if `junior_dev` failed
3. **Break into steps**: Multiple smaller delegations
4. **Increase timeout**: Allow more time for complex tasks
5. **Add context**: Provide more background information

---

## Run on Different Platforms

**Problem**: You want to run the same task on multiple platforms to compare results.

**Solution**:

```python
from amplihack.meta_delegation import run_meta_delegation

goal = "Create a markdown to HTML converter"
success_criteria = "Converts basic markdown, handles headers/links/lists, has tests"

platforms = ["claude-code", "copilot", "amplifier"]
results = {}

for platform in platforms:
    print(f"\nRunning on {platform}...")
    result = run_meta_delegation(
        goal=goal,
        success_criteria=success_criteria,
        platform=platform
    )
    results[platform] = result

# Compare results
print("\n" + "="*70)
print("PLATFORM COMPARISON")
print("="*70)
print(f"{'Platform':<15} | {'Status':<10} | {'Score':>5} | {'Evidence':>8} | {'Time':>8}")
print("-"*70)

for platform, result in results.items():
    print(
        f"{platform:<15} | "
        f"{result.status:<10} | "
        f"{result.success_score:>5}/100 | "
        f"{len(result.evidence):>8} items | "
        f"{result.duration_seconds:>8.1f}s"
    )
```

**Output**:

```
======================================================================
PLATFORM COMPARISON
======================================================================
Platform        | Status     | Score | Evidence |     Time
----------------------------------------------------------------------
claude-code     | SUCCESS    |  92/100 |  10 items |     38.5s
copilot         | SUCCESS    |  88/100 |   8 items |     42.3s
amplifier       | SUCCESS    |  90/100 |   9 items |     35.7s
```

---

## Generate Test Scenarios

**Problem**: You want to use Gadugi to generate comprehensive test scenarios.

**Solution**:

```python
from amplihack.meta_delegation import run_meta_delegation

# Enable scenario generation
result = run_meta_delegation(
    goal="Create a payment processing module",
    success_criteria="""
    - Handles credit card, PayPal, and bank transfer
    - Validates payment data
    - Has comprehensive tests covering edge cases
    """,
    persona_type="qa_engineer",
    enable_scenarios=True  # Activates Gadugi
)

# Access generated scenarios
if hasattr(result, 'test_scenarios'):
    print(f"Generated {len(result.test_scenarios)} test scenarios:")
    for scenario in result.test_scenarios:
        print(f"\n{scenario.name}")
        print(f"  Category: {scenario.category}")
        print(f"  Description: {scenario.description}")
        print(f"  Expected: {scenario.expected_outcome}")
```

**Output**:

```
Generated 12 test scenarios:

Valid Credit Card Payment
  Category: happy_path
  Description: Process a valid credit card payment with correct CVV and expiry
  Expected: Payment succeeds, transaction ID returned

Expired Credit Card
  Category: error_handling
  Description: Attempt payment with expired credit card
  Expected: ValidationError raised with clear message

Invalid CVV Code
  Category: error_handling
  Description: Credit card with incorrect CVV length
  Expected: ValidationError with CVV validation message

[... 9 more scenarios ...]
```

**Gadugi Scenario Categories**:

- `happy_path`: Normal successful operations
- `error_handling`: Invalid inputs and edge cases
- `boundary_conditions`: Limits and extremes
- `security`: Potential vulnerabilities
- `performance`: Load and stress scenarios

---

## Export Evidence as Archive

**Problem**: You want to save all evidence to disk for review.

**Solution**:

```python
from amplihack.meta_delegation import run_meta_delegation
import os
import shutil

result = run_meta_delegation(
    goal="Create a REST API for todo items",
    success_criteria="CRUD endpoints, validation, tests"
)

# Create archive directory
archive_dir = "evidence_archive_20260120_103045"
os.makedirs(archive_dir, exist_ok=True)

# Export all evidence
for item in result.evidence:
    # Create subdirectories by type
    type_dir = os.path.join(archive_dir, item.type)
    os.makedirs(type_dir, exist_ok=True)

    # Write evidence file
    file_path = os.path.join(type_dir, os.path.basename(item.path))
    with open(file_path, 'w') as f:
        f.write(item.content)

    print(f"Exported: {file_path}")

# Create summary report
summary_path = os.path.join(archive_dir, "SUMMARY.md")
with open(summary_path, 'w') as f:
    f.write(f"# Meta-Delegation Evidence Archive\n\n")
    f.write(f"**Status**: {result.status}\n")
    f.write(f"**Success Score**: {result.success_score}/100\n")
    f.write(f"**Duration**: {result.duration_seconds}s\n\n")
    f.write(f"## Evidence Collected\n\n")

    # Group by type
    by_type = {}
    for item in result.evidence:
        by_type.setdefault(item.type, []).append(item)

    for evidence_type, items in sorted(by_type.items()):
        f.write(f"### {evidence_type.replace('_', ' ').title()}\n\n")
        for item in items:
            f.write(f"- [{item.path}](./{evidence_type}/{os.path.basename(item.path)})\n")
        f.write("\n")

print(f"\nArchive created: {archive_dir}/")
print(f"Summary: {summary_path}")
```

**Output**:

```
Exported: evidence_archive_20260120_103045/code_file/todo_api.py
Exported: evidence_archive_20260120_103045/code_file/models.py
Exported: evidence_archive_20260120_103045/test_file/test_todo_api.py
Exported: evidence_archive_20260120_103045/documentation/README.md
Exported: evidence_archive_20260120_103045/documentation/API_SPEC.md
Exported: evidence_archive_20260120_103045/execution_log/subprocess_output.log

Archive created: evidence_archive_20260120_103045/
Summary: evidence_archive_20260120_103045/SUMMARY.md
```

**Directory Structure**:

```
evidence_archive_20260120_103045/
├── SUMMARY.md
├── code_file/
│   ├── todo_api.py
│   └── models.py
├── test_file/
│   └── test_todo_api.py
├── documentation/
│   ├── README.md
│   └── API_SPEC.md
└── execution_log/
    └── subprocess_output.log
```

---

## Chain Multiple Delegations

**Problem**: You need to run a sequence of delegations where each builds on the previous.

**Solution**:

```python
from amplihack.meta_delegation import run_meta_delegation

# Pipeline configuration
pipeline = [
    {
        "name": "Architecture",
        "goal": "Design a blog platform backend",
        "success_criteria": "Architecture doc, API spec, data model",
        "persona": "architect"
    },
    {
        "name": "Implementation",
        "goal": "Implement the blog platform following the architecture",
        "success_criteria": "Working code, follows design, basic tests",
        "persona": "junior_dev",
        "use_context_from": "Architecture"  # Use previous result
    },
    {
        "name": "Testing",
        "goal": "Perform comprehensive testing of the blog platform",
        "success_criteria": "Test coverage >85%, edge cases covered, report generated",
        "persona": "qa_engineer",
        "use_context_from": "Implementation"
    }
]

# Execute pipeline
results = {}
context = None

for stage in pipeline:
    print(f"\n{'='*60}")
    print(f"Stage: {stage['name']}")
    print('='*60)

    # Build delegation parameters
    params = {
        "goal": stage["goal"],
        "success_criteria": stage["success_criteria"],
        "persona_type": stage["persona"]
    }

    # Add context from previous stage if specified
    if "use_context_from" in stage and stage["use_context_from"] in results:
        prev_result = results[stage["use_context_from"]]
        # Combine relevant evidence as context
        context_parts = []
        for evidence_type in ["architecture_doc", "code_file", "api_spec"]:
            items = prev_result.get_evidence_by_type(evidence_type)
            if items:
                context_parts.append(f"## {evidence_type}\n\n{items[0].content}")
        params["context"] = "\n\n".join(context_parts)

    # Run delegation
    result = run_meta_delegation(**params)
    results[stage["name"]] = result

    print(f"Status: {result.status}")
    print(f"Score: {result.success_score}/100")
    print(f"Evidence: {len(result.evidence)} items")

    # Stop pipeline if stage fails
    if result.status == "FAILURE":
        print(f"\n⚠ Pipeline halted at stage: {stage['name']}")
        break

# Pipeline summary
print("\n" + "="*60)
print("PIPELINE SUMMARY")
print("="*60)

total_score = sum(r.success_score for r in results.values())
avg_score = total_score / len(results) if results else 0

for stage_name, result in results.items():
    status_symbol = "✓" if result.status == "SUCCESS" else "✗"
    print(f"{status_symbol} {stage_name:<20} | Score: {result.success_score:3}/100")

print(f"\nOverall Pipeline Score: {avg_score:.1f}/100")
```

**Output**:

```
============================================================
Stage: Architecture
============================================================
Status: SUCCESS
Score: 95/100
Evidence: 8 items

============================================================
Stage: Implementation
============================================================
Status: SUCCESS
Score: 88/100
Evidence: 12 items

============================================================
Stage: Testing
============================================================
Status: SUCCESS
Score: 92/100
Evidence: 15 items

============================================================
PIPELINE SUMMARY
============================================================
✓ Architecture         | Score:  95/100
✓ Implementation       | Score:  88/100
✓ Testing              | Score:  92/100

Overall Pipeline Score: 91.7/100
```

---

## Advanced: Custom Success Evaluation

**Problem**: You want custom logic to evaluate success beyond the standard criteria.

**Solution**:

```python
from amplihack.meta_delegation import run_meta_delegation

# Standard delegation
result = run_meta_delegation(
    goal="Create a database migration tool",
    success_criteria="Tool can migrate up/down, handles errors, has tests"
)

# Custom evaluation logic
def custom_evaluate(result):
    """Apply custom success criteria."""
    score = result.success_score  # Start with standard score

    # Bonus: Check for specific files
    if result.get_evidence_by_type("architecture_doc"):
        score += 5
        print("  +5 points: Architecture document found")

    # Bonus: Check test coverage in logs
    test_results = result.get_evidence_by_type("test_results")
    if test_results and "100% coverage" in test_results[0].content:
        score += 10
        print("  +10 points: Perfect test coverage")

    # Penalty: Too much code (over-engineering)
    code_files = result.get_evidence_by_type("code_file")
    total_lines = sum(c.content.count('\n') for c in code_files)
    if total_lines > 500:
        score -= 5
        print(f"  -5 points: Too much code ({total_lines} lines)")

    return min(100, score)  # Cap at 100

# Apply custom evaluation
custom_score = custom_evaluate(result)
print(f"\nStandard score: {result.success_score}/100")
print(f"Custom score: {custom_score}/100")
```

**Output**:

```
  +5 points: Architecture document found
  +10 points: Perfect test coverage

Standard score: 85/100
Custom score: 100/100
```

---

## Related Documentation

- [Tutorial](./tutorial.md) - Learn the basics step-by-step
- [Reference](./reference.md) - Complete API documentation
- [Concepts](./concepts.md) - Architecture and design
- [Troubleshooting](./troubleshooting.md) - Fix common issues

---

**Status**: [PLANNED - Implementation Pending]

This how-to guide describes the intended usage patterns once the meta-delegation system is implemented.
