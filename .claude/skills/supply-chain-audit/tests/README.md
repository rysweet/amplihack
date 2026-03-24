# Supply Chain Audit — Test Suite

TDD test suite for the `supply-chain-audit` skill. Tests are written **before** implementation — they define the contract and **fail until the implementation exists**.

## Structure

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── pytest.ini               # Pytest settings
├── unit/
│   ├── test_finding_schema.py      # Finding object validation (11 fields, constraints)
│   ├── test_scope_detection.py     # Ecosystem detection from file signals
│   ├── test_pattern_detection.py   # Per-dimension checker logic (Dims 1-12)
│   ├── test_security_invariants.py # 7 unconditional security invariants
│   ├── test_error_conditions.py    # 5 named error conditions
│   └── test_report_schema.py       # Report format compliance
├── integration/
│   ├── test_audit_workflow.py      # 5-step audit workflow integration
│   └── test_eval_scenarios.py      # 3 graded eval scenarios (18 findings total)
├── e2e/
│   └── test_full_audit.py          # Full audit pipeline E2E tests
└── fixtures/
    ├── scenario_a/                  # GHA + Python + Node (7 findings)
    ├── scenario_b/                  # Containers + Go + Credentials (5 findings)
    └── scenario_c/                  # .NET + Rust + SLSA (6 findings)
```

## Running Tests

```bash
# All tests (expected: ALL FAIL — no implementation yet)
cd skills/supply-chain-audit && pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Specific invariant tests
pytest tests/unit/test_security_invariants.py -v

# Scenario A only
pytest tests/integration/test_eval_scenarios.py -k "ScenarioA" -v

# With coverage (once implementation exists)
pytest tests/ --cov=supply_chain_audit --cov-report=term-missing
```

## Test Count Summary

| Module                        | Tests    | Category      |
| ----------------------------- | -------- | ------------- |
| `test_finding_schema.py`      | 23       | Unit          |
| `test_scope_detection.py`     | 22       | Unit          |
| `test_pattern_detection.py`   | 35       | Unit          |
| `test_security_invariants.py` | 24       | Unit/Security |
| `test_error_conditions.py`    | 24       | Unit          |
| `test_report_schema.py`       | 20       | Unit          |
| `test_audit_workflow.py`      | 24       | Integration   |
| `test_eval_scenarios.py`      | 32       | Integration   |
| `test_full_audit.py`          | 26       | E2E           |
| **Total**                     | **~230** | Mixed         |

## Contract Coverage

Tests cover every contract element from `reference/contracts.md`:

- ✅ Finding schema — all 11 fields, all constraints
- ✅ Finding ID format — `{SEVERITY}-{NNN}`, uniqueness
- ✅ Severity enum — exactly `Critical|High|Medium|Info`
- ✅ Report schema — all 5 sections, empty-report variant
- ✅ All 4 inter-skill handoff templates
- ✅ All 5 named error conditions
- ✅ All 7 security invariants
- ✅ All 3 eval scenarios with 18 planted findings
- ✅ Accepted-risks 4 hard constraints
- ✅ Tool timeout values (gh=15s, crane=20s, syft=120s, grype=60s)
- ✅ Scope enum validation with injection rejection
- ✅ Path traversal rejection
- ✅ XPIA escalation
- ✅ Secret redaction
- ✅ SBOM write advisory

## Implementation Entrypoint

Tests import from a `supply_chain_audit` package that does not yet exist:

```python
from supply_chain_audit.audit import run_audit
from supply_chain_audit.schema import Finding, validate_finding, FindingId
from supply_chain_audit.detector import detect_ecosystems, EcosystemScope
from supply_chain_audit.checkers import check_action_sha_pinning, ...
from supply_chain_audit.report import AuditReport, SlsaAssessment, build_report
from supply_chain_audit.errors import (
    PathTraversalError, InvalidScopeError,
    ToolTimeoutError, AcceptedRisksOverflowError, XpiaEscalationError,
)
```

The expected module structure for implementation:

```
supply_chain_audit/
├── __init__.py
├── audit.py          # run_audit() — orchestrates the 5-step workflow
├── schema.py         # Finding, FindingId, validate_finding
├── detector.py       # detect_ecosystems, EcosystemScope
├── report.py         # AuditReport, SlsaAssessment, build_report
├── errors.py         # All named error classes
└── checkers/
    ├── __init__.py
    ├── actions.py    # Dims 1-4
    ├── containers.py # Dims 5, 12
    ├── credentials.py # Dim 6
    ├── dotnet.py     # Dim 7
    ├── python.py     # Dim 8
    ├── rust.py       # Dim 9
    ├── node.py       # Dim 10
    └── go.py         # Dim 11
```
