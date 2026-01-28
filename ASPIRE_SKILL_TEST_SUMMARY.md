# Aspire Skill Validation Tests - Implementation Summary

## Objective

Created comprehensive TDD validation tests for the Aspire skill following the test specification in GitHub issue #2197.

## What Was Created

### 1. Test File

**Location**: `tests/skills/test_aspire_skill.py`

**Comprehensive validation suite with 47 tests across 10 test classes:**

1. **TestFileStructure** (5 tests)
   - Validates all required files exist in correct location
   - Checks for unexpected files (no cruft)
   - Ensures files are readable and markdown format

2. **TestYAMLFrontmatter** (15 tests)
   - Validates YAML frontmatter structure
   - Checks `name` field (lowercase, kebab-case, equals "aspire")
   - Validates `description` (non-empty, contains trigger keywords)
   - Checks `version` field (semver format)
   - Validates `source_urls` (list, contains official Aspire URLs)
   - Validates `activation_keywords` (includes core terms, sufficient coverage)

3. **TestTokenBudget** (5 tests)
   - Uses tiktoken (cl100k_base encoding) for accurate token counting
   - Enforces maximum budget (2000 tokens)
   - Enforces target budget (1800 tokens for future edit buffer)
   - Validates declared budget matches target
   - Ensures actual tokens within declared budget

4. **TestContentStructure** (8 tests)
   - Validates required sections (Overview, Quick Start, Core Workflows, Navigation Guide)
   - Checks Navigation Guide references all supporting files
   - Validates Overview describes core problem
   - Ensures Quick Start has code examples
   - Confirms Core Workflows has subsections

5. **TestProgressiveDisclosure** (3 tests)
   - Validates "Read when you need" pattern in Navigation Guide
   - Ensures supporting files are referenced, not inlined
   - Checks supporting files don't cross-reference (one level deep)

6. **TestExamples** (4 tests)
   - Validates examples.md exists and contains code blocks
   - Checks for C# code examples (```csharp)
   - Ensures examples are complete (>10 lines, not just snippets)

7. **TestReferences** (2 tests)
   - Validates reference.md exists
   - Checks reference.md covers AppHost API

8. **TestPatterns** (2 tests)
   - Validates patterns.md exists
   - Checks patterns.md covers production topics (deployment, security, performance)

9. **TestTroubleshooting** (2 tests)
   - Validates troubleshooting.md exists
   - Checks troubleshooting.md covers common issues

10. **TestNoInternalBrokenReferences** (1 test)
    - Validates no broken internal markdown links

### 2. Documentation Files

**Location**: `tests/skills/`

- **README.md**: Complete guide for running and understanding skill validation tests
- **TEST_RESULTS.md**: Detailed analysis of current test results and required fixes

### 3. Test Infrastructure

- Created `tests/skills/` directory
- Added `__init__.py` for proper Python package structure
- Integrated with existing pytest configuration

## Test Results

### Current Status

**Total Tests**: 47
**Passing**: 44 (93.6%)
**Failing**: 3 (6.4%)

### Passing Tests ✅

All structural, organizational, and quality tests pass:

- File structure and existence
- YAML frontmatter format and content
- Content structure and organization
- Progressive disclosure patterns
- Examples completeness
- References coverage
- Patterns best practices
- Troubleshooting guidance
- No broken links

### Failing Tests ❌ (As Expected with TDD)

**Token budget violations (3 tests):**

```
Current token count: 2350
Target budget: 1800 tokens
Maximum budget: 2000 tokens

Overage: 550 tokens above target, 350 tokens above maximum
```

**This is correct TDD behavior** - tests fail until the skill meets requirements.

## TDD Approach Validated

The tests follow proper TDD methodology:

1. ✅ **Tests written first** (before skill is complete)
2. ✅ **Tests fail initially** (red phase)
3. ✅ **Clear failure messages** (tell you exactly what to fix)
4. ✅ **Objective criteria** (token counts are measurable)
5. ✅ **Actionable feedback** (tests specify exactly what needs reduction)

## Key Technical Features

### 1. Token Counting

Uses `tiktoken` with `cl100k_base` encoding (closest to Claude's actual tokenizer):

```python
def count_tokens(text: str) -> int:
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))
```

### 2. YAML Parsing

Custom YAML parser for frontmatter (handles simple YAML without external dependencies):

```python
def extract_yaml_frontmatter(content: str) -> dict:
    # Extracts and parses YAML between --- delimiters
    # Handles both key: value and key: [list] formats
```

### 3. Progressive Disclosure Validation

Validates that SKILL.md:
- References supporting files (not inlines)
- Uses "Read when you need" pattern
- Keeps total size < 40% of combined content (proxy for no inlining)

### 4. Content Quality Checks

- Code blocks must be present and complete (>10 lines)
- Sections must exist and contain relevant keywords
- Links must not be broken
- Files must cover expected topics

## Running the Tests

### Basic Usage

```bash
# From worktree root
cd /home/azureuser/src/amplihack/worktrees/feat/issue-2197-aspire-skill

# Run all skill validation tests
uv run pytest tests/skills/test_aspire_skill.py -v

# Run specific test class
uv run pytest tests/skills/test_aspire_skill.py::TestTokenBudget -v

# Run with detailed output
uv run pytest tests/skills/test_aspire_skill.py -v --tb=long
```

### Expected Output

```
============================= test session starts ==============================
collecting ... collected 47 items

tests/skills/test_aspire_skill.py::TestFileStructure::test_skill_directory_exists PASSED
tests/skills/test_aspire_skill.py::TestFileStructure::test_all_required_files_exist PASSED
...
tests/skills/test_aspire_skill.py::TestTokenBudget::test_skill_under_max_token_budget FAILED
tests/skills/test_aspire_skill.py::TestTokenBudget::test_skill_under_target_token_budget FAILED
tests/skills/test_aspire_skill.py::TestTokenBudget::test_actual_tokens_within_declared_budget FAILED
...

========================= 3 failed, 44 passed in 0.58s =========================
```

## What Needs to Happen Next

To make all tests pass, the Aspire skill needs:

1. **Reduce SKILL.md by ~550 tokens** to reach 1800 token target
2. **Strategies**:
   - Move detailed code examples to examples.md
   - Condense Core Workflows section
   - Simplify Common Tasks section
   - Streamline Quick Reference section
3. **Re-run tests** to verify: `uv run pytest tests/skills/test_aspire_skill.py -v`
4. **Iterate** until all 47 tests pass

## Files Created

```
tests/skills/
├── __init__.py                     # Package marker
├── README.md                       # User guide (2.1KB)
├── TEST_RESULTS.md                 # Test analysis (5.8KB)
└── test_aspire_skill.py           # Test implementation (22.5KB)

/home/azureuser/src/amplihack/worktrees/feat/issue-2197-aspire-skill/
└── ASPIRE_SKILL_TEST_SUMMARY.md   # This file
```

## Philosophy Alignment

These tests enforce amplihack philosophy:

- **Ruthless Simplicity**: Token budgets force conciseness
- **Modular Design**: Each file has one clear purpose
- **Progressive Disclosure**: Load only what's needed
- **Zero-BS Implementation**: All tests validate real content, no stubs
- **Measurable Quality**: Objective metrics (token counts, structure)
- **TDD Approach**: Tests define "done" before implementation

## Success Criteria Met

✅ **File Structure Tests**: All required files exist and are valid
✅ **YAML Frontmatter Tests**: Metadata is correctly formatted
❌ **Token Budget Tests**: NEEDS FIX (2350 tokens > 1800 target)
✅ **Content Structure Tests**: All sections present and organized
✅ **Progressive Disclosure Tests**: Pattern correctly followed
✅ **Quality Tests**: Examples, references, patterns, troubleshooting are complete

## Test Coverage

The test suite validates:

1. ✅ **Existence**: All 5 required files exist
2. ✅ **Format**: All files are markdown, readable
3. ✅ **Metadata**: YAML frontmatter is complete and valid
4. ❌ **Token Budget**: 2350 tokens (OVER BUDGET - expected TDD failure)
5. ✅ **Structure**: Required sections present
6. ✅ **Organization**: Navigation Guide references all supporting files
7. ✅ **Quality**: Examples are complete, references comprehensive
8. ✅ **Links**: No broken internal references
9. ✅ **Progressive Disclosure**: Supporting files referenced, not inlined
10. ✅ **Best Practices**: Patterns cover production topics

## Integration with Existing Tests

The skill validation tests integrate seamlessly:

- Use existing pytest configuration (`pytest.ini`)
- Follow existing test patterns (fixtures, assertions)
- Use standard markers (`pytest.mark.unit`)
- Run with existing test infrastructure (`uv run pytest`)

## Next Steps for Issue #2197

1. **Review test results**: See `tests/skills/TEST_RESULTS.md`
2. **Reduce token count**: Bring SKILL.md from 2350 to 1800 tokens
3. **Re-run tests**: Verify all 47 tests pass
4. **Commit**: Add tests to repository for ongoing validation
5. **CI Integration**: Consider adding to CI pipeline

## Documentation References

- Test specification: GitHub Issue #2197
- Test implementation: `tests/skills/test_aspire_skill.py`
- User guide: `tests/skills/README.md`
- Test results: `tests/skills/TEST_RESULTS.md`
- Aspire skill: `.claude/skills/aspire/`

## Conclusion

Successfully created comprehensive TDD validation tests for the Aspire skill. The tests:

- Are thorough (47 tests across 10 categories)
- Follow TDD methodology (tests fail as expected)
- Provide clear, actionable feedback
- Use objective metrics (token counting)
- Enforce amplihack philosophy
- Integrate with existing infrastructure

The 3 failing token budget tests correctly identify that SKILL.md needs to be reduced by ~550 tokens. This is exactly how TDD should work - tests guide the implementation.
