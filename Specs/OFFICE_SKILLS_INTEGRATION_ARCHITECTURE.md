# Office Skills Integration Architecture

## Executive Summary

This document defines the architecture for integrating Anthropic's four Office document skills (XLSX, DOCX, PPTX, PDF) into the amplihack project. The design follows the brick philosophy: each skill is a self-contained module with clear contracts, independently functional, and regeneratable from specification.

## 1. Problem Analysis

### 1.1 Core Requirements

**Explicit (Non-negotiable):**
- ONE PR per skill (4 PRs total)
- Each skill independently functional
- Source: https://github.com/anthropics/skills
- Must use `.claude/skills/` directory structure
- All dependencies documented

**Implicit:**
- Skills must work with existing Claude Code framework
- Follow amplihack philosophy (ruthless simplicity, modularity)
- Minimal changes to existing code
- Clear documentation for users
- Verification mechanism for each skill

### 1.2 Problem Decomposition

The integration breaks into 6 distinct concerns:

1. **Directory Structure**: Where skills live and how they organize
2. **Skill Integration Pattern**: What to copy and how to adapt
3. **Dependency Management**: How to track and install dependencies
4. **Testing Strategy**: How to verify each skill works
5. **Documentation**: How to communicate usage and status
6. **Common Components**: How to handle shared scripts/dependencies

## 2. Solution Design

### 2.1 Directory Structure

```
.claude/skills/
├── README.md                       # Skills overview and usage guide
├── INTEGRATION_STATUS.md           # Tracking integration progress (which skills work)
├── common/                         # Shared dependencies and scripts
│   ├── README.md                   # Common components documentation
│   ├── dependencies.txt            # Shared dependencies across skills
│   ├── ooxml/                      # Shared OOXML scripts (docx + pptx)
│   │   ├── README.md
│   │   ├── unpack.py
│   │   ├── pack.py
│   │   ├── rearrange.py           # PPTX specific
│   │   ├── inventory.py           # PPTX specific
│   │   └── replace.py             # PPTX specific
│   └── verification/               # Shared verification utilities
│       ├── README.md
│       └── verify_skill.py        # Generic skill verification script
│
├── xlsx/                           # Excel spreadsheet skill
│   ├── SKILL.md                    # Skill definition (from Anthropic)
│   ├── README.md                   # Integration notes and usage
│   ├── DEPENDENCIES.md             # Skill-specific dependencies
│   ├── scripts/
│   │   └── recalc.py              # Formula recalculation script
│   ├── tests/                      # Skill verification tests
│   │   ├── test_basic.py
│   │   └── fixtures/
│   └── examples/                   # Usage examples
│       └── basic_usage.md
│
├── docx/                           # Word document skill
│   ├── SKILL.md
│   ├── README.md
│   ├── DEPENDENCIES.md
│   ├── scripts/                    # Symlink to ../common/ooxml/
│   ├── tests/
│   │   ├── test_basic.py
│   │   └── fixtures/
│   └── examples/
│       └── basic_usage.md
│
├── pptx/                           # PowerPoint presentation skill
│   ├── SKILL.md
│   ├── README.md
│   ├── DEPENDENCIES.md
│   ├── scripts/                    # Symlink to ../common/ooxml/
│   ├── tests/
│   │   ├── test_basic.py
│   │   └── fixtures/
│   └── examples/
│       └── basic_usage.md
│
└── pdf/                            # PDF manipulation skill
    ├── SKILL.md
    ├── README.md
    ├── DEPENDENCIES.md
    ├── tests/
    │   ├── test_basic.py
    │   └── fixtures/
    └── examples/
        └── basic_usage.md
```

**Design Rationale:**

- **Brick Philosophy**: Each skill is self-contained with all its code in one directory
- **Common Components**: Shared scripts in `common/` to avoid duplication (DRY principle)
- **Symlinks for OOXML**: docx and pptx reference common OOXML scripts via symlinks (single source of truth)
- **Test Isolation**: Each skill has its own tests for independent verification
- **Documentation Levels**: README at root, integration status tracking, per-skill READMEs

### 2.2 Integration Pattern

#### 2.2.1 What to Copy

**For each skill:**

1. **SKILL.md** (Primary artifact)
   - Contains YAML frontmatter with skill metadata
   - Contains skill instructions for Claude Code
   - Copy verbatim from Anthropic repository

2. **Scripts** (Implementation artifacts)
   - XLSX: `recalc.py`
   - DOCX: OOXML scripts (unpack.py, pack.py)
   - PPTX: OOXML scripts (unpack.py, pack.py, rearrange.py, inventory.py, replace.py)
   - PDF: No scripts (uses Python libraries directly)

3. **Dependencies** (Extract from SKILL.md)
   - Python packages (pandas, openpyxl, etc.)
   - System packages (LibreOffice, poppler-utils, etc.)
   - Node packages (docx, pptxgenjs, etc.)

#### 2.2.2 What to Create (New Files)

**Per-skill:**

1. **README.md** - Integration-specific documentation
   - How this skill integrates with amplihack
   - Amplihack-specific usage patterns
   - Known limitations or considerations

2. **DEPENDENCIES.md** - Dependency specification
   ```markdown
   # Dependencies for [Skill Name]

   ## Python Packages
   - package==version  # Purpose

   ## System Packages
   - package  # Purpose

   ## Node Packages
   - package  # Purpose

   ## Installation
   ```bash
   # Python
   pip install package1 package2

   # System (Ubuntu/Debian)
   sudo apt-get install package1

   # System (macOS)
   brew install package1

   # Node
   npm install -g package1
   ```

   ## Verification
   ```bash
   python -c "import package; print(package.__version__)"
   ```
   ```

3. **tests/test_basic.py** - Verification test
   - Smoke test that skill loads correctly
   - Basic functionality test (create/read simple document)
   - Skip if dependencies not installed

4. **examples/basic_usage.md** - Usage documentation
   - Simple example of using the skill
   - Common patterns
   - Links to SKILL.md for full documentation

#### 2.2.3 What to Adapt

**OOXML Scripts (docx + pptx):**

- Extract from Anthropic repository
- Place in `.claude/skills/common/ooxml/`
- Create symlinks from skill directories:
  - `.claude/skills/docx/scripts -> ../common/ooxml`
  - `.claude/skills/pptx/scripts -> ../common/ooxml`

**Rationale:** OOXML scripts are identical across skills. Symlinks maintain single source of truth while allowing each skill to reference "their" scripts.

### 2.3 Dependency Management Approach

#### 2.3.1 Dependency Categorization

**Core Dependencies (Required for skill to function):**
- Python packages (pandas, openpyxl, pypdf, etc.)
- Critical system tools (LibreOffice for calculations)

**Optional Dependencies (Enhanced functionality):**
- OCR tools (pytesseract, pdf2image)
- Advanced processing (playwright, sharp)

#### 2.3.2 Dependency Documentation Strategy

**Three-level documentation:**

1. **Skill-level** (`.claude/skills/[skill]/DEPENDENCIES.md`)
   - Complete list of dependencies for this skill
   - Installation instructions per platform
   - Verification commands

2. **Common level** (`.claude/skills/common/dependencies.txt`)
   - Dependencies shared across multiple skills
   - Installation order (if dependencies exist)

3. **Root level** (`.claude/skills/README.md`)
   - Quick start: minimum dependencies to get started
   - Full install: all dependencies for all skills
   - Platform-specific guidance

#### 2.3.3 Dependency Installation Pattern

**No automatic installation.** Users choose what to install.

**Rationale:**
- Follows amplihack philosophy (no magic, explicit)
- System packages require sudo/admin access
- Users may not want all skills
- LibreOffice is 500MB+ download

**Instead:**
- Clear documentation on what's needed
- Verification scripts that check dependencies
- Tests that skip gracefully if dependencies missing
- Helpful error messages pointing to documentation

#### 2.3.4 Dependency Verification

Create `.claude/skills/common/verification/verify_skill.py`:

```python
#!/usr/bin/env python3
"""Verify skill dependencies are installed."""

import sys
import importlib
import subprocess
from typing import List, Tuple

def check_python_package(package: str) -> Tuple[bool, str]:
    """Check if Python package is installed."""
    try:
        importlib.import_module(package)
        return True, "Installed"
    except ImportError:
        return False, "Not installed"

def check_system_command(command: str) -> Tuple[bool, str]:
    """Check if system command is available."""
    try:
        subprocess.run([command, "--version"],
                      capture_output=True,
                      check=True)
        return True, "Available"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False, "Not available"

def verify_skill(skill_name: str,
                python_packages: List[str],
                system_commands: List[str]) -> bool:
    """Verify all dependencies for a skill."""
    print(f"Verifying {skill_name} skill dependencies...\n")

    all_ok = True

    if python_packages:
        print("Python packages:")
        for package in python_packages:
            ok, status = check_python_package(package)
            print(f"  {package}: {status}")
            all_ok = all_ok and ok

    if system_commands:
        print("\nSystem commands:")
        for command in system_commands:
            ok, status = check_system_command(command)
            print(f"  {command}: {status}")
            all_ok = all_ok and ok

    print(f"\n{'✓' if all_ok else '✗'} {skill_name} skill is {'ready' if all_ok else 'missing dependencies'}")
    return all_ok

if __name__ == "__main__":
    # Usage: python verify_skill.py xlsx
    skill = sys.argv[1] if len(sys.argv) > 1 else "all"

    # Define skill dependencies
    skills = {
        "xlsx": {
            "python": ["pandas", "openpyxl"],
            "system": ["soffice"]  # LibreOffice
        },
        "docx": {
            "python": ["defusedxml"],
            "system": ["pandoc", "soffice", "pdftoppm"]
        },
        "pptx": {
            "python": ["markitdown", "defusedxml"],
            "system": ["node", "soffice"]
        },
        "pdf": {
            "python": ["pypdf", "pdfplumber", "reportlab"],
            "system": ["qpdf", "pdftk"]
        }
    }

    if skill == "all":
        for skill_name, deps in skills.items():
            verify_skill(skill_name, deps["python"], deps["system"])
            print("\n" + "="*50 + "\n")
    else:
        deps = skills.get(skill)
        if deps:
            verify_skill(skill, deps["python"], deps["system"])
        else:
            print(f"Unknown skill: {skill}")
            sys.exit(1)
```

### 2.4 Testing Strategy

#### 2.4.1 Test Levels

**Level 1: Skill Load Test**
- Verify SKILL.md exists and is readable
- Verify YAML frontmatter is valid
- Check skill can be invoked in Claude Code

**Level 2: Dependency Test**
- Run verification script
- Report missing dependencies
- Skip gracefully if dependencies unavailable

**Level 3: Basic Functionality Test**
- Create a simple document (e.g., blank Excel file)
- Read it back
- Verify basic operations work
- Only runs if dependencies available

**Level 4: Integration Test** (Future)
- Test skill interaction with amplihack agents
- Test skill usage in real workflows

#### 2.4.2 Test Implementation Pattern

Each skill gets `tests/test_basic.py`:

```python
"""Basic verification tests for [skill] skill."""

import pytest
import sys
from pathlib import Path

# Import verification utility
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "common" / "verification"))
from verify_skill import verify_skill

# Define skill dependencies
PYTHON_PACKAGES = ["pandas", "openpyxl"]  # Example for xlsx
SYSTEM_COMMANDS = ["soffice"]

def test_skill_file_exists():
    """Verify SKILL.md exists."""
    skill_file = Path(__file__).parent.parent / "SKILL.md"
    assert skill_file.exists(), "SKILL.md not found"

def test_skill_yaml_valid():
    """Verify SKILL.md has valid YAML frontmatter."""
    skill_file = Path(__file__).parent.parent / "SKILL.md"
    content = skill_file.read_text()
    assert content.startswith("---"), "SKILL.md missing YAML frontmatter"

    # Basic YAML parsing
    import yaml
    parts = content.split("---")
    assert len(parts) >= 3, "Invalid YAML structure"
    metadata = yaml.safe_load(parts[1])
    assert "name" in metadata, "YAML missing 'name' field"

@pytest.mark.skipif(
    not verify_skill("[skill]", PYTHON_PACKAGES, SYSTEM_COMMANDS),
    reason="Dependencies not installed"
)
def test_basic_functionality():
    """Test basic skill functionality."""
    # Skill-specific test
    # Example for xlsx:
    import pandas as pd
    df = pd.DataFrame({"A": [1, 2, 3]})

    # Write and read back
    test_file = Path("/tmp/test_skill.xlsx")
    df.to_excel(test_file, index=False)
    df2 = pd.read_excel(test_file)

    assert df.equals(df2), "Data integrity check failed"
    test_file.unlink()

def test_readme_exists():
    """Verify README.md exists with integration notes."""
    readme = Path(__file__).parent.parent / "README.md"
    assert readme.exists(), "README.md not found"

    content = readme.read_text()
    assert "amplihack" in content.lower(), "README missing amplihack context"
```

#### 2.4.3 Running Tests

```bash
# Test individual skill
cd .claude/skills/xlsx
pytest tests/

# Test all skills
cd .claude/skills
pytest */tests/

# Verify dependencies before testing
python common/verification/verify_skill.py xlsx
```

### 2.5 Documentation Requirements

#### 2.5.1 Root Documentation (`.claude/skills/README.md`)

**Contents:**
1. Overview of office skills integration
2. Available skills (xlsx, docx, pptx, pdf)
3. Quick start guide
4. Common use cases
5. Dependency installation summary
6. Link to INTEGRATION_STATUS.md
7. Troubleshooting

**Template:**

```markdown
# Office Document Skills

Anthropic's office document skills integrated into amplihack.

## Available Skills

- **xlsx**: Create/edit Excel spreadsheets with formulas
- **docx**: Create/edit Word documents with tracked changes
- **pptx**: Create/edit PowerPoint presentations
- **pdf**: Comprehensive PDF manipulation and extraction

## Quick Start

1. Install dependencies for desired skill (see skill README)
2. Verify installation: `python common/verification/verify_skill.py [skill]`
3. Use skill in Claude Code conversation

## Integration Status

See [INTEGRATION_STATUS.md](INTEGRATION_STATUS.md) for current status.

## Usage Example

```
User: Create an Excel spreadsheet with sales data
Claude: [Uses xlsx skill to generate spreadsheet]
```

## Dependencies

Each skill requires different dependencies. See skill-specific DEPENDENCIES.md:
- [xlsx/DEPENDENCIES.md](xlsx/DEPENDENCIES.md)
- [docx/DEPENDENCIES.md](docx/DEPENDENCIES.md)
- [pptx/DEPENDENCIES.md](pptx/DEPENDENCIES.md)
- [pdf/DEPENDENCIES.md](pdf/DEPENDENCIES.md)

## Troubleshooting

### Skill not working
1. Verify dependencies: `python common/verification/verify_skill.py [skill]`
2. Check skill tests: `cd [skill] && pytest tests/`
3. Review skill README for known issues

### Missing dependencies
See skill-specific DEPENDENCIES.md for installation instructions.
```

#### 2.5.2 Integration Status Tracking (`.claude/skills/INTEGRATION_STATUS.md`)

**Purpose:** Track which skills are integrated and working.

**Template:**

```markdown
# Office Skills Integration Status

## Integration Progress

| Skill | Status | Dependencies | Tests | PR | Notes |
|-------|--------|--------------|-------|----|----|
| xlsx  | ✓ Integrated | ✓ Documented | ✓ Passing | #XXX | Ready |
| docx  | ✗ Not Started | - | - | - | Planned PR #2 |
| pptx  | ⚠ In Progress | ✓ Documented | ⚠ Partial | #XXX | Active work |
| pdf   | ✗ Not Started | - | - | - | Planned PR #4 |

## Status Legend

- ✓ Complete
- ⚠ In Progress
- ✗ Not Started
- ⨯ Blocked

## Integration Order

1. PDF (simplest, no external scripts, fewest dependencies)
2. XLSX (single script, moderate dependencies)
3. DOCX (OOXML scripts, moderate dependencies)
4. PPTX (most complex, most OOXML scripts, heaviest dependencies)

**Rationale:** Start simple, build confidence, increase complexity.

## Current Blockers

None.

## Next Steps

- [ ] Integrate PDF skill (PR #1)
- [ ] Integrate XLSX skill (PR #2)
- [ ] Set up common OOXML infrastructure (PR #3 prep)
- [ ] Integrate DOCX skill (PR #3)
- [ ] Integrate PPTX skill (PR #4)
```

#### 2.5.3 Per-Skill Documentation

Each skill needs:

1. **README.md** - Integration context
   ```markdown
   # [Skill Name] Skill Integration

   ## Overview
   [What this skill does]

   ## Integration with amplihack
   [How it fits into amplihack workflows]

   ## Dependencies
   See [DEPENDENCIES.md](DEPENDENCIES.md)

   ## Usage
   See [examples/basic_usage.md](examples/basic_usage.md)

   ## Testing
   ```bash
   pytest tests/
   ```

   ## Known Issues
   [Any amplihack-specific issues]
   ```

2. **DEPENDENCIES.md** - Complete dependency list (see 2.3.2)

3. **examples/basic_usage.md** - Simple usage examples
   ```markdown
   # Basic [Skill] Usage

   ## Example 1: [Common task]

   User: [Example prompt]

   Claude: [Expected response]

   Result: [What gets created]

   ## Example 2: [Another common task]
   ...
   ```

### 2.6 Common Components Strategy

#### 2.6.1 Shared OOXML Scripts

**Problem:** docx and pptx both use OOXML manipulation scripts.

**Solution:** Extract to `.claude/skills/common/ooxml/`

**Scripts:**
- `unpack.py` (both) - Extracts OOXML archive
- `pack.py` (both) - Repackages OOXML archive
- `rearrange.py` (pptx only) - Slide reordering
- `inventory.py` (pptx only) - Content inventory
- `replace.py` (pptx only) - Content replacement

**Implementation:**
```bash
# During integration
mkdir -p .claude/skills/common/ooxml
cp [anthropic-repo]/ooxml/unpack.py .claude/skills/common/ooxml/
cp [anthropic-repo]/ooxml/pack.py .claude/skills/common/ooxml/

# In skill directories
cd .claude/skills/docx
ln -s ../common/ooxml scripts

cd .claude/skills/pptx
ln -s ../common/ooxml scripts
```

#### 2.6.2 Shared Dependencies

**Common across multiple skills:**
- LibreOffice (xlsx, docx, pptx)
- defusedxml (docx, pptx)
- poppler-utils (docx, pdf)

**Documentation:** `.claude/skills/common/dependencies.txt`

```
# Shared Dependencies Across Skills

## Python Packages
defusedxml  # Used by: docx, pptx
            # Purpose: Safe XML parsing

## System Packages
LibreOffice  # Used by: xlsx, docx, pptx
            # Purpose: Document calculations and conversions
            # Command: soffice

poppler-utils  # Used by: docx, pdf
              # Purpose: PDF processing
              # Commands: pdftoppm, pdftotext
```

#### 2.6.3 Verification Utilities

**Shared verification script:** `.claude/skills/common/verification/verify_skill.py`

See section 2.3.4 for implementation.

## 3. Implementation Order Recommendation

### 3.1 Recommended Order

**PR #1: PDF Skill** (Simplest)
- No external scripts
- Pure Python libraries
- Fewest system dependencies
- Good learning opportunity

**PR #2: XLSX Skill** (Moderate)
- One script (recalc.py)
- Moderate dependencies
- Tests common OOXML pattern

**PR #3: DOCX Skill** (Moderate-Complex)
- Requires common OOXML infrastructure
- Sets up symlink pattern
- More dependencies

**PR #4: PPTX Skill** (Most Complex)
- Heaviest dependencies
- Most OOXML scripts
- Builds on docx patterns

### 3.2 Rationale

**Start Simple:** PDF has no external scripts, establishing basic integration pattern.

**Build Infrastructure:** XLSX introduces script handling. DOCX establishes OOXML common infrastructure.

**Increase Complexity:** PPTX leverages patterns from previous PRs.

**Risk Management:** Each PR is independently valuable. If PR #4 blocks, we still have 3 working skills.

### 3.3 Per-PR Checklist

**Each PR must include:**
- [ ] Skill directory with SKILL.md
- [ ] README.md with integration notes
- [ ] DEPENDENCIES.md with complete dependency list
- [ ] tests/test_basic.py with verification tests
- [ ] examples/basic_usage.md with usage examples
- [ ] Update to .claude/skills/INTEGRATION_STATUS.md
- [ ] Scripts (if applicable)
- [ ] All tests passing (or skipping gracefully)
- [ ] Documentation reviewed for clarity

**PR #1 (PDF) additionally includes:**
- [ ] .claude/skills/ directory creation
- [ ] .claude/skills/README.md
- [ ] .claude/skills/INTEGRATION_STATUS.md
- [ ] .claude/skills/common/ directory structure
- [ ] .claude/skills/common/verification/verify_skill.py

**PR #3 (DOCX) additionally includes:**
- [ ] .claude/skills/common/ooxml/ directory
- [ ] OOXML scripts (unpack.py, pack.py)
- [ ] Symlink setup for docx/scripts
- [ ] OOXML README

## 4. Risk Assessment

### 4.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Dependency installation fails on some platforms | High | Medium | Clear documentation, graceful test skipping |
| OOXML scripts require modifications | Medium | Medium | Test thoroughly, maintain upstream compatibility |
| Skills don't integrate with Claude Code | Low | High | Follow Anthropic patterns exactly, minimal modification |
| Symlinks break on Windows | Medium | Low | Document Windows setup, consider copies as fallback |
| LibreOffice unavailable in CI | High | Low | Make optional, skip tests if missing |

### 4.2 Process Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| PRs blocked by review delays | Medium | Medium | Each PR independent, can proceed in parallel |
| Integration order causes rework | Low | Medium | Start simple, establish patterns early |
| Documentation drift | Medium | Low | Update INTEGRATION_STATUS.md with each PR |
| Test coverage gaps | Medium | Medium | Require tests in each PR, verify before merge |

### 4.3 Philosophy Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Over-engineering the integration | Medium | Medium | Follow brick philosophy, keep it simple |
| Under-documenting for users | Medium | High | Three-level documentation strategy |
| Creating implicit dependencies | Low | High | Clear DEPENDENCIES.md, explicit installation |
| Violating regeneratability | Low | High | Each skill self-contained, minimal coupling |

### 4.4 Critical Success Factors

**Must Have:**
- Each skill works independently
- Clear dependency documentation
- Tests verify basic functionality
- Documentation explains integration

**Nice to Have:**
- All dependencies available in CI
- Complete test coverage
- Advanced usage examples
- Integration with amplihack agents

**Out of Scope (for initial integration):**
- Automatic dependency installation
- Skill orchestration between skills
- Advanced error recovery
- Skill versioning/updates

## 5. Verification Approach

### 5.1 Per-Skill Verification

**For each skill PR:**

1. **File Structure Check**
   ```bash
   # Verify all required files exist
   test -f .claude/skills/[skill]/SKILL.md
   test -f .claude/skills/[skill]/README.md
   test -f .claude/skills/[skill]/DEPENDENCIES.md
   test -d .claude/skills/[skill]/tests
   test -d .claude/skills/[skill]/examples
   ```

2. **Dependency Verification**
   ```bash
   python .claude/skills/common/verification/verify_skill.py [skill]
   ```

3. **Test Execution**
   ```bash
   cd .claude/skills/[skill]
   pytest tests/ -v
   ```

4. **Claude Code Integration**
   ```bash
   # Manual verification in Claude Code session
   # 1. Start Claude Code
   # 2. Try basic skill invocation
   # 3. Verify skill appears in available skills
   ```

5. **Documentation Review**
   - README is clear and complete
   - Examples are tested and work
   - DEPENDENCIES.md is accurate
   - Integration notes are helpful

### 5.2 Integration Verification

**After all PRs merged:**

1. **All Skills Loadable**
   ```bash
   # Verify all SKILL.md files valid
   find .claude/skills -name "SKILL.md" -type f
   ```

2. **All Dependencies Documented**
   ```bash
   # Verify each skill has DEPENDENCIES.md
   find .claude/skills -name "DEPENDENCIES.md" -type f
   ```

3. **Common Components Work**
   ```bash
   # Verify OOXML scripts exist and are symlinked
   test -d .claude/skills/common/ooxml
   test -L .claude/skills/docx/scripts
   test -L .claude/skills/pptx/scripts
   ```

4. **All Tests Pass**
   ```bash
   cd .claude/skills
   pytest */tests/ -v
   ```

5. **Status Document Accurate**
   - INTEGRATION_STATUS.md shows all skills integrated
   - All checkboxes for each skill completed

### 5.3 User Acceptance Criteria

**A skill is considered "integrated" when:**

1. SKILL.md from Anthropic repository is present
2. README.md explains amplihack-specific usage
3. DEPENDENCIES.md lists all requirements
4. Basic test passes (or skips gracefully)
5. Example usage documented
6. INTEGRATION_STATUS.md updated
7. PR merged to main branch

**The overall integration is "complete" when:**

1. All 4 skills meet acceptance criteria
2. Common infrastructure in place
3. Root README explains skill usage
4. Verification script works for all skills
5. Documentation reviewed and accurate

## 6. Pre-Commit Configuration

### 6.1 Analysis

**Current State:**
- Project has comprehensive pre-commit configuration
- Includes ruff, pyright, prettier, detect-secrets
- Custom quality gates for production code

**Skills Integration Impact:**
- Skills contain scripts that may need linting
- OOXML scripts may have different standards
- Test files should follow project standards
- SKILL.md files don't need linting (markdown)

### 6.2 Recommendation

**No changes required to pre-commit configuration.**

**Rationale:**
1. **Scripts are external code**: OOXML and recalc.py come from Anthropic, maintain upstream compatibility
2. **Tests follow standards**: Our test files will follow existing pytest patterns
3. **Documentation is markdown**: Already handled by prettier
4. **Isolation**: Skills are in `.claude/skills/` which can be excluded if needed

**If issues arise:**
- Add `.claude/skills/common/ooxml/` to ruff exclude
- Add `.claude/skills/*/scripts/` to pyright exclude
- These are upstream code, not our production code

### 6.3 Integration Testing with Pre-Commit

**Before each PR:**
```bash
# Run pre-commit on changed files
pre-commit run --files .claude/skills/[skill]/**/*

# Verify no issues with test files
pre-commit run --files .claude/skills/[skill]/tests/**/*.py
```

**Expected outcome:** Test files pass, scripts may be excluded.

## 7. Module Specifications

Following the brick philosophy, here are the module specifications for each component.

### 7.1 Module: PDF Skill

**Purpose:** Comprehensive PDF manipulation and extraction.

**Contract:**
- **Inputs**: PDF files, manipulation instructions via natural language
- **Outputs**: Modified PDFs, extracted text/data
- **Side Effects**: File I/O (reads/writes PDFs)

**Dependencies:**
- Python: pypdf, pdfplumber, reportlab, pytesseract (optional), pdf2image (optional), pandas
- System: poppler-utils, qpdf, pdftk

**Implementation Notes:**
- Uses pypdf for basic manipulation
- pdfplumber for text extraction
- reportlab for PDF generation
- OCR capabilities optional (graceful degradation)

**Test Requirements:**
- SKILL.md loads correctly
- Basic PDF creation works
- Text extraction works
- Dependency verification accurate

**Regeneratability:** Can rebuild from SKILL.md + dependency list.

---

### 7.2 Module: XLSX Skill

**Purpose:** Create and edit Excel spreadsheets with formula support.

**Contract:**
- **Inputs**: Spreadsheet data, formulas, formatting instructions
- **Outputs**: Excel files (.xlsx)
- **Side Effects**: File I/O, LibreOffice process invocation (for recalc)

**Dependencies:**
- Python: pandas, openpyxl
- System: LibreOffice
- Scripts: recalc.py (formula recalculation)

**Implementation Notes:**
- pandas for data manipulation
- openpyxl for Excel file format
- recalc.py uses LibreOffice for formula evaluation
- LibreOffice optional (formulas won't recalculate without it)

**Test Requirements:**
- SKILL.md loads correctly
- Basic spreadsheet creation works
- recalc.py script executable
- Dependency verification accurate

**Regeneratability:** Can rebuild from SKILL.md + recalc.py + dependency list.

---

### 7.3 Module: DOCX Skill

**Purpose:** Create and edit Word documents with tracked changes.

**Contract:**
- **Inputs**: Document content, formatting, change tracking instructions
- **Outputs**: Word files (.docx)
- **Side Effects**: File I/O, OOXML archive manipulation

**Dependencies:**
- Python: defusedxml
- System: pandoc, LibreOffice, poppler-utils
- Node: docx package
- Scripts: OOXML scripts (unpack.py, pack.py) from common/ooxml/

**Implementation Notes:**
- Uses OOXML format (Office Open XML)
- unpack.py extracts .docx to XML
- pack.py repackages XML to .docx
- Tracked changes via OOXML modification
- Depends on common OOXML infrastructure

**Test Requirements:**
- SKILL.md loads correctly
- OOXML scripts accessible (symlink works)
- Basic document creation works
- Dependency verification accurate

**Regeneratability:** Can rebuild from SKILL.md + OOXML common scripts + dependency list.

---

### 7.4 Module: PPTX Skill

**Purpose:** Create and edit PowerPoint presentations.

**Contract:**
- **Inputs**: Presentation content, layout, design instructions
- **Outputs**: PowerPoint files (.pptx)
- **Side Effects**: File I/O, OOXML archive manipulation, Node process invocation

**Dependencies:**
- Python: markitdown, defusedxml
- System: LibreOffice
- Node: pptxgenjs, playwright, sharp
- Scripts: OOXML scripts (unpack.py, pack.py, rearrange.py, inventory.py, replace.py) from common/ooxml/

**Implementation Notes:**
- Uses OOXML format
- pptxgenjs for presentation generation
- playwright for browser automation (advanced features)
- sharp for image processing
- Most complex skill (heaviest dependencies)
- Depends on common OOXML infrastructure

**Test Requirements:**
- SKILL.md loads correctly
- OOXML scripts accessible (symlink works)
- Basic presentation creation works
- Node dependencies installable
- Dependency verification accurate

**Regeneratability:** Can rebuild from SKILL.md + OOXML common scripts + dependency list.

---

### 7.5 Module: Common OOXML Scripts

**Purpose:** Shared OOXML manipulation utilities for docx and pptx skills.

**Contract:**
- **Inputs**: OOXML archive files (.docx/.pptx), manipulation commands
- **Outputs**: Modified OOXML archives
- **Side Effects**: File I/O (unpack/pack operations)

**Dependencies:**
- Python: defusedxml
- System: None (pure Python)

**Implementation Notes:**
- unpack.py: Extracts ZIP archive, parses XML
- pack.py: Rebuilds ZIP archive from XML
- rearrange.py (pptx): Reorders slides
- inventory.py (pptx): Lists presentation content
- replace.py (pptx): Text/content replacement
- Single source of truth for OOXML operations
- Symlinked from skill directories

**Test Requirements:**
- Scripts are executable
- unpack/pack round-trip preserves data
- XML parsing safe (defusedxml)

**Regeneratability:** Can rebuild from script source + documentation.

---

### 7.6 Module: Verification Utilities

**Purpose:** Verify skill dependencies are installed and working.

**Contract:**
- **Inputs**: Skill name, dependency lists
- **Outputs**: Status report (installed/missing)
- **Side Effects**: None (read-only checks)

**Dependencies:**
- Python: Standard library only
- System: None (checks for others)

**Implementation Notes:**
- Checks Python packages via importlib
- Checks system commands via subprocess
- Returns structured status
- Used by tests and manual verification

**Test Requirements:**
- Correctly detects installed packages
- Correctly detects missing packages
- Handles errors gracefully

**Regeneratability:** Simple utility, easily rebuilt from specification.

---

### 7.7 Module: Integration Status Tracking

**Purpose:** Track which skills are integrated and their status.

**Contract:**
- **Inputs**: Manual updates per PR
- **Outputs**: Markdown table showing status
- **Side Effects**: None (documentation only)

**Dependencies:** None (markdown file)

**Implementation Notes:**
- Simple markdown table
- Updated with each PR
- Links to PRs for traceability
- Shows integration order

**Test Requirements:**
- File exists and is valid markdown
- Contains all 4 skills
- Status accurately reflects reality

**Regeneratability:** Trivial (markdown document).

## 8. Decision Record

### 8.1 Key Decisions

**Decision: Use symlinks for OOXML scripts**
- **Why:** Single source of truth, avoid duplication
- **Alternatives Considered:** Copy scripts to each skill, git submodules
- **Trade-offs:** Symlinks may not work on Windows, but simpler than alternatives

**Decision: No automatic dependency installation**
- **Why:** Follows amplihack philosophy, respects user choice
- **Alternatives Considered:** Install script, Docker container, conda environment
- **Trade-offs:** More manual setup, but explicit and flexible

**Decision: Integration order (PDF → XLSX → DOCX → PPTX)**
- **Why:** Start simple, build infrastructure, increase complexity
- **Alternatives Considered:** Alphabetical, by complexity (reverse), by popularity
- **Trade-offs:** PDF might be less popular than XLSX, but better learning curve

**Decision: Three-level documentation**
- **Why:** Balance between detail and overview, serves different needs
- **Alternatives Considered:** Single README, per-skill only, auto-generated
- **Trade-offs:** More maintenance, but clearer for users

**Decision: Test skipping for missing dependencies**
- **Why:** CI may not have LibreOffice, users may not want all skills
- **Alternatives Considered:** Require all dependencies, mock dependencies
- **Trade-offs:** Incomplete test coverage, but pragmatic

**Decision: Common verification script**
- **Why:** DRY principle, consistent experience, easier maintenance
- **Alternatives Considered:** Per-skill verification, manual checks
- **Trade-offs:** One more file, but much better UX

**Decision: ONE PR per skill (not negotiable)**
- **Why:** Explicit requirement, allows independent review/merge
- **Alternatives Considered:** None (requirement)
- **Trade-offs:** More PRs to manage, but cleaner history

**Decision: No changes to pre-commit configuration**
- **Why:** External code doesn't need project linting, tests already covered
- **Alternatives Considered:** Exclude skills directory, custom rules
- **Trade-offs:** May lint upstream code, but can exclude if needed

### 8.2 Open Questions

**Q: Should verification script auto-install missing dependencies?**
- **A:** No. Respect user choice, avoid sudo/admin operations.

**Q: What if OOXML scripts need modification for amplihack?**
- **A:** Document modifications clearly, maintain upstream compatibility, consider contributing back.

**Q: Should skills be git submodules of Anthropic repository?**
- **A:** No. We copy files, not link repositories. Simplifies updates and allows customization.

**Q: Do we need CI tests for all skills?**
- **A:** Nice to have, not required. Tests should skip gracefully if dependencies missing.

**Q: Should we version skills separately from amplihack?**
- **A:** Not initially. Track Anthropic upstream version in SKILL.md comments.

## 9. Success Metrics

### 9.1 Quantitative Metrics

- **Integration Completeness**: 4/4 skills integrated (100%)
- **Test Coverage**: >80% of test files passing (or skipping appropriately)
- **Documentation Coverage**: 100% of required docs present
- **PR Velocity**: 4 PRs in reasonable timeframe (2-4 weeks)

### 9.2 Qualitative Metrics

- **User Experience**: Users can find and use skills without asking for help
- **Philosophy Compliance**: Integration follows brick philosophy
- **Maintainability**: Someone unfamiliar can understand structure in <30 minutes
- **Robustness**: Missing dependencies cause graceful degradation, not crashes

### 9.3 Definition of Done

**For the overall integration:**

- [ ] All 4 skills integrated (SKILL.md present)
- [ ] All skills documented (README, DEPENDENCIES, examples)
- [ ] All skills tested (basic functionality verified)
- [ ] Common infrastructure in place (ooxml/, verification/)
- [ ] Root documentation complete (README, INTEGRATION_STATUS)
- [ ] All PRs merged
- [ ] At least one skill verified working in real usage

## 10. Next Steps

### 10.1 Immediate Actions (PR #1 - PDF Skill)

1. Create `.claude/skills/` directory structure
2. Copy PDF SKILL.md from Anthropic repository
3. Create PDF README.md with integration notes
4. Create PDF DEPENDENCIES.md with complete dependency list
5. Create tests/test_basic.py for PDF
6. Create examples/basic_usage.md for PDF
7. Create common/verification/verify_skill.py
8. Create root README.md
9. Create INTEGRATION_STATUS.md
10. Submit PR #1

### 10.2 Subsequent PRs

**PR #2 (XLSX):** Follow same pattern, add recalc.py script

**PR #3 (DOCX):** Set up common/ooxml/, establish symlink pattern

**PR #4 (PPTX):** Leverage OOXML infrastructure from PR #3

### 10.3 Post-Integration

1. Verify all skills work in real usage
2. Collect user feedback
3. Update documentation based on feedback
4. Consider additional examples
5. Track upstream changes in Anthropic repository
6. Update INTEGRATION_STATUS.md with lessons learned

---

## Appendix A: File Checklist

**Per PR checklist** (adapt for each skill):

```
.claude/skills/[skill]/
├── SKILL.md                    (from Anthropic)
├── README.md                   (amplihack integration notes)
├── DEPENDENCIES.md             (complete dependency list)
├── tests/
│   ├── test_basic.py          (verification tests)
│   └── fixtures/              (test data)
├── examples/
│   └── basic_usage.md         (usage examples)
└── scripts/                    (if applicable)
    └── [skill-specific]
```

**PR #1 (PDF) additional files:**

```
.claude/skills/
├── README.md                           (root overview)
├── INTEGRATION_STATUS.md               (status tracking)
└── common/
    ├── README.md                       (common components overview)
    ├── dependencies.txt                (shared dependencies)
    └── verification/
        ├── README.md
        └── verify_skill.py            (verification utility)
```

**PR #3 (DOCX) additional files:**

```
.claude/skills/common/ooxml/
├── README.md                   (OOXML scripts documentation)
├── unpack.py
└── pack.py
```

**PR #4 (PPTX) additional files to common/ooxml/:**

```
.claude/skills/common/ooxml/
├── rearrange.py
├── inventory.py
└── replace.py
```

---

## Appendix B: Dependency Summary

### B.1 Python Packages

| Package | Skills | Purpose |
|---------|--------|---------|
| pandas | xlsx, pdf | Data manipulation |
| openpyxl | xlsx | Excel file format |
| pypdf | pdf | PDF manipulation |
| pdfplumber | pdf | PDF text extraction |
| reportlab | pdf | PDF generation |
| pytesseract | pdf | OCR (optional) |
| pdf2image | pdf | PDF to image (optional) |
| defusedxml | docx, pptx | Safe XML parsing |
| markitdown | pptx | Markdown processing |

### B.2 System Packages

| Package | Skills | Purpose |
|---------|--------|---------|
| LibreOffice | xlsx, docx, pptx | Document calculations/conversion |
| pandoc | docx | Document conversion |
| poppler-utils | docx, pdf | PDF processing |
| qpdf | pdf | PDF manipulation |
| pdftk | pdf | PDF toolkit |

### B.3 Node Packages

| Package | Skills | Purpose |
|---------|--------|---------|
| docx | docx | Word document manipulation |
| pptxgenjs | pptx | PowerPoint generation |
| playwright | pptx | Browser automation |
| sharp | pptx | Image processing |

---

## Appendix C: Integration Timeline Estimate

**Assuming serial development:**

- PR #1 (PDF): 2-3 days (includes infrastructure setup)
- PR #2 (XLSX): 1-2 days (pattern established)
- PR #3 (DOCX): 2-3 days (OOXML infrastructure setup)
- PR #4 (PPTX): 1-2 days (leverages DOCX patterns)

**Total: 6-10 days of development time**

**Assuming parallel development (after PR #1):**

- PR #1 (PDF): 2-3 days (sequential, establishes foundation)
- PRs #2-4: 2-3 days (parallel, after PR #1 merged)

**Total: 4-6 days of development time**

**Review/merge time:** 1-2 days per PR

**Overall timeline:** 2-4 weeks calendar time

---

## Appendix D: Reference Links

- **Anthropic Skills Repository**: https://github.com/anthropics/skills/tree/main/document-skills
- **Amplihack Philosophy**: `.claude/context/PHILOSOPHY.md`
- **Amplihack Project Context**: `.claude/context/PROJECT.md`
- **Pre-commit Configuration**: `.pre-commit-config.yaml`

---

**Document Status:** Complete and ready for implementation

**Last Updated:** 2025-11-08

**Author:** Architect Agent (Claude)

**Approved By:** Pending user review
