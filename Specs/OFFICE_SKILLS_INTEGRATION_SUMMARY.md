# Office Skills Integration - Executive Summary

## Quick Overview

This document summarizes the architecture for integrating Anthropic's four Office document skills (XLSX, DOCX, PPTX, PDF) into amplihack.

**Full Architecture:** See [OFFICE_SKILLS_INTEGRATION_ARCHITECTURE.md](OFFICE_SKILLS_INTEGRATION_ARCHITECTURE.md)

## Key Decisions

### 1. Directory Structure

```
.claude/skills/
├── README.md                    # Root documentation
├── INTEGRATION_STATUS.md        # Status tracking
├── common/                      # Shared components
│   ├── ooxml/                   # OOXML scripts (docx + pptx)
│   └── verification/            # Dependency checking
├── xlsx/                        # Excel skill
├── docx/                        # Word skill
├── pptx/                        # PowerPoint skill
└── pdf/                         # PDF skill
```

**Each skill directory contains:**
- `SKILL.md` (from Anthropic)
- `README.md` (integration notes)
- `DEPENDENCIES.md` (complete dependency list)
- `tests/` (verification tests)
- `examples/` (usage examples)
- `scripts/` (skill-specific scripts)

### 2. Integration Pattern

**What to copy:**
- SKILL.md files verbatim from Anthropic
- Script files (recalc.py, OOXML scripts)

**What to create:**
- README.md (amplihack-specific integration notes)
- DEPENDENCIES.md (complete dependency documentation)
- tests/test_basic.py (verification tests)
- examples/basic_usage.md (usage documentation)

**What to adapt:**
- OOXML scripts → extract to `common/ooxml/`
- Create symlinks from docx/pptx to common OOXML scripts

### 3. Dependency Management

**No automatic installation.** Users choose what to install.

**Three-level documentation:**
1. **Skill-level**: Complete list in `[skill]/DEPENDENCIES.md`
2. **Common-level**: Shared dependencies in `common/dependencies.txt`
3. **Root-level**: Quick start in `.claude/skills/README.md`

**Verification script:** `common/verification/verify_skill.py`
- Checks Python packages
- Checks system commands
- Reports missing dependencies
- Used by tests and manual verification

### 4. Testing Strategy

**Four test levels:**
1. **Load Test**: SKILL.md exists and loads
2. **Dependency Test**: Verify dependencies via script
3. **Basic Functionality Test**: Create/read simple document
4. **Integration Test**: (Future) Test with amplihack agents

**Tests skip gracefully if dependencies missing.**

### 5. Implementation Order

**Recommended order (simplest → most complex):**

1. **PR #1: PDF** (simplest)
   - No external scripts
   - Pure Python libraries
   - Establishes basic pattern
   - Includes infrastructure setup

2. **PR #2: XLSX** (moderate)
   - One script (recalc.py)
   - Tests script handling pattern

3. **PR #3: DOCX** (moderate-complex)
   - Sets up common OOXML infrastructure
   - Establishes symlink pattern

4. **PR #4: PPTX** (most complex)
   - Leverages DOCX patterns
   - Heaviest dependencies

**Rationale:** Build confidence, establish patterns, increase complexity progressively.

### 6. Common Components

**OOXML Scripts (shared by docx + pptx):**
- Extract to `.claude/skills/common/ooxml/`
- Symlink from skill directories
- Single source of truth

**Verification Utilities:**
- `verify_skill.py` checks dependencies
- Used by tests and manual verification
- Consistent experience across skills

**Shared Dependencies:**
- LibreOffice (xlsx, docx, pptx)
- defusedxml (docx, pptx)
- poppler-utils (docx, pdf)

### 7. Pre-Commit Configuration

**No changes required.**

**Rationale:**
- Scripts are external code (Anthropic upstream)
- Tests follow existing project standards
- Can exclude scripts if linting issues arise

## Implementation Checklist

### Per-PR Checklist

**All PRs must include:**
- [ ] SKILL.md from Anthropic
- [ ] README.md with integration notes
- [ ] DEPENDENCIES.md with complete list
- [ ] tests/test_basic.py with verification tests
- [ ] examples/basic_usage.md with usage examples
- [ ] Scripts (if applicable)
- [ ] Update to INTEGRATION_STATUS.md
- [ ] All tests passing (or skipping gracefully)

### PR #1 (PDF) Additional Items

**Infrastructure setup:**
- [ ] Create `.claude/skills/` directory
- [ ] Create root README.md
- [ ] Create INTEGRATION_STATUS.md
- [ ] Create common/ directory structure
- [ ] Create common/verification/verify_skill.py
- [ ] Create common/README.md
- [ ] Create common/dependencies.txt

### PR #3 (DOCX) Additional Items

**OOXML infrastructure:**
- [ ] Create common/ooxml/ directory
- [ ] Copy unpack.py and pack.py
- [ ] Create OOXML README.md
- [ ] Set up symlink from docx/scripts

### PR #4 (PPTX) Additional Items

**OOXML extensions:**
- [ ] Copy rearrange.py, inventory.py, replace.py
- [ ] Set up symlink from pptx/scripts

## Quick Start (After Integration)

### Installing Dependencies

```bash
# Check what's needed for a skill
cd .claude/skills/[skill]
cat DEPENDENCIES.md

# Verify dependencies
python ../common/verification/verify_skill.py [skill]

# Install (example for PDF)
pip install pypdf pdfplumber reportlab
brew install qpdf poppler  # macOS
```

### Using a Skill

```
User: Create an Excel spreadsheet with sales data

Claude: [Automatically uses xlsx skill]
```

### Testing a Skill

```bash
cd .claude/skills/[skill]
pytest tests/ -v
```

## Risk Assessment

### High Priority Risks

| Risk | Mitigation |
|------|------------|
| Dependencies fail on some platforms | Clear documentation, graceful test skipping |
| Symlinks break on Windows | Document Windows setup, consider copies as fallback |
| Skills don't integrate with Claude Code | Follow Anthropic patterns exactly |

### Medium Priority Risks

| Risk | Mitigation |
|------|------------|
| OOXML scripts need modification | Test thoroughly, document changes, maintain upstream compatibility |
| PRs blocked by review delays | Each PR independent, can proceed in parallel |
| Over-engineering the integration | Follow brick philosophy, keep it simple |

## Success Metrics

### Quantitative
- **Integration Completeness**: 4/4 skills integrated (100%)
- **Test Coverage**: >80% passing (or skipping appropriately)
- **Documentation Coverage**: 100% of required docs present
- **Timeline**: 4 PRs in 2-4 weeks

### Qualitative
- **User Experience**: Users can use skills without asking for help
- **Philosophy Compliance**: Follows brick philosophy
- **Maintainability**: Understandable in <30 minutes
- **Robustness**: Graceful degradation for missing dependencies

## Timeline Estimate

**Serial development:**
- PR #1 (PDF): 2-3 days (includes infrastructure)
- PR #2 (XLSX): 1-2 days
- PR #3 (DOCX): 2-3 days (includes OOXML setup)
- PR #4 (PPTX): 1-2 days
- **Total: 6-10 days development + 4-8 days review = 2-4 weeks**

**Parallel development (after PR #1):**
- PR #1 (PDF): 2-3 days (sequential)
- PRs #2-4: 2-3 days (parallel)
- **Total: 4-6 days development + 4-8 days review = 2-3 weeks**

## Next Steps

### Immediate (Start PR #1)

1. Create `.claude/skills/` directory structure
2. Copy PDF SKILL.md from Anthropic repository
3. Create PDF documentation (README, DEPENDENCIES, examples)
4. Create PDF tests
5. Create common infrastructure (verification/)
6. Create root documentation (README, INTEGRATION_STATUS)
7. Submit PR #1

### After PR #1 Merged

1. Start PR #2 (XLSX)
2. Start PR #3 (DOCX) - includes OOXML setup
3. Start PR #4 (PPTX) - after DOCX merged

## Key Contacts

- **Anthropic Skills Repository**: https://github.com/anthropics/skills/tree/main/document-skills
- **Amplihack Repository**: https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding

## Document References

- **Full Architecture**: [OFFICE_SKILLS_INTEGRATION_ARCHITECTURE.md](OFFICE_SKILLS_INTEGRATION_ARCHITECTURE.md)
- **Philosophy**: `.claude/context/PHILOSOPHY.md`
- **Project Context**: `.claude/context/PROJECT.md`

---

**Document Status:** Complete and ready for implementation

**Last Updated:** 2025-11-08

**Next Action:** Begin PR #1 (PDF skill integration)
