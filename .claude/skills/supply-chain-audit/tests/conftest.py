"""
Shared fixtures and configuration for supply-chain-audit tests.
TDD: Defines the test infrastructure. Tests fail until implementation exists.
"""

from pathlib import Path

import pytest

# Root of the skill directory
SKILL_ROOT = Path(__file__).parent.parent
FIXTURES_ROOT = Path(__file__).parent / "fixtures"
REFERENCE_ROOT = SKILL_ROOT / "reference"


@pytest.fixture
def scenario_a_root():
    """Fixture directory for Scenario A: GHA + Python + Node."""
    return FIXTURES_ROOT / "scenario_a"


@pytest.fixture
def scenario_b_root():
    """Fixture directory for Scenario B: Containers + Go + Credentials."""
    return FIXTURES_ROOT / "scenario_b"


@pytest.fixture
def scenario_c_root():
    """Fixture directory for Scenario C: .NET + Rust + SLSA."""
    return FIXTURES_ROOT / "scenario_c"


@pytest.fixture
def clean_repo(tmp_path):
    """Empty repo with no ecosystem files — verifies empty-report path."""
    return tmp_path


@pytest.fixture
def gha_only_repo(tmp_path):
    """Repo with only GitHub Actions workflows."""
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)
    wf_file = wf_dir / "ci.yml"
    wf_file.write_text(
        "name: CI\n"
        "on: [push]\n"
        "permissions: read-all\n"
        "jobs:\n"
        "  build:\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        "      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2\n"
    )
    return tmp_path


@pytest.fixture
def accepted_risks_file(tmp_path):
    """Well-formed .supply-chain-accepted-risks.yml for suppression tests."""
    content = """\
- id: "HIGH-001"
  dimension: 1
  file: ".github/workflows/ci.yml"
  line: 8
  rationale: "Internal action; change-controlled release process."
  accepted_by: "security-team"
  review_date: "2099-12-31"
"""
    fixture_dir = tmp_path / "_fixtures"
    fixture_dir.mkdir(exist_ok=True)
    risk_file = fixture_dir / ".supply-chain-accepted-risks.yml"
    risk_file.write_text(content)
    return risk_file


@pytest.fixture
def expired_accepted_risks_file(tmp_path):
    """Accepted-risks file with a past review_date — should restore severity."""
    content = """\
- id: "HIGH-001"
  dimension: 1
  file: ".github/workflows/ci.yml"
  line: 8
  rationale: "Temporary exception during migration."
  accepted_by: "eng-lead"
  review_date: "2020-01-01"
"""
    fixture_dir = tmp_path / "_fixtures"
    fixture_dir.mkdir(exist_ok=True)
    risk_file = fixture_dir / ".supply-chain-accepted-risks.yml"
    risk_file.write_text(content)
    return risk_file
