# Skills Validation Tests

This directory contains validation tests for Claude Code skills following TDD methodology.

## Purpose

Skills are markdown-based capabilities that Claude loads on-demand. These tests validate:

- **File Structure**: All required files exist in correct locations
- **YAML Frontmatter**: Metadata is properly formatted and complete
- **Token Budget**: Skills stay within token limits for efficient loading
- **Content Structure**: Required sections and organization
- **Progressive Disclosure**: SKILL.md references supporting files correctly
- **Examples Quality**: Code examples are complete and working
- **References**: API and technical details are comprehensive
- **Patterns**: Best practices are documented
- **Troubleshooting**: Debugging guidance is provided

## Test Structure

```
tests/skills/
├── README.md                    # This file
├── test_aspire_skill.py        # Aspire skill validation tests
└── TEST_RESULTS.md             # Latest test run results
```

## Running Tests

### Run All Skill Tests

```bash
uv run pytest tests/skills/ -v
```

### Run Specific Skill Tests

```bash
# Aspire skill only
uv run pytest tests/skills/test_aspire_skill.py -v

# Specific test class
uv run pytest tests/skills/test_aspire_skill.py::TestTokenBudget -v

# Specific test method
uv run pytest tests/skills/test_aspire_skill.py::TestTokenBudget::test_skill_under_max_token_budget -v
```

### Run with Different Output Levels

```bash
# Minimal output (just pass/fail)
uv run pytest tests/skills/test_aspire_skill.py -q

# Verbose with short traceback
uv run pytest tests/skills/test_aspire_skill.py -v --tb=short

# Verbose with full traceback
uv run pytest tests/skills/test_aspire_skill.py -v --tb=long

# Show local variables on failure
uv run pytest tests/skills/test_aspire_skill.py -v --tb=long --showlocals
```

### Run Only Failed Tests

```bash
# Re-run only tests that failed last time
uv run pytest tests/skills/test_aspire_skill.py --lf

# Re-run failed tests first, then others
uv run pytest tests/skills/test_aspire_skill.py --ff
```

## Test Categories

### 1. File Structure Tests

Validate that all required files exist:
- `SKILL.md` (main skill file)
- `reference.md` (API reference and technical details)
- `examples.md` (working code examples)
- `patterns.md` (best practices and production patterns)
- `troubleshooting.md` (debugging guidance)

### 2. YAML Frontmatter Tests

Validate metadata in SKILL.md frontmatter:
- `name`: lowercase, kebab-case
- `description`: clear, contains trigger keywords
- `version`: semver format (X.Y.Z)
- `source_urls`: official documentation URLs
- `activation_keywords`: comprehensive coverage
- `token_budget`: declared and accurate

### 3. Token Budget Tests

Enforce token limits using tiktoken:
- **Hard limit**: 2000 tokens maximum
- **Target**: 1800 tokens (leaves buffer for edits)
- **Declared**: Must match target in frontmatter

### 4. Content Structure Tests

Validate required sections:
- Overview (problem statement and solution)
- Quick Start (installation and first steps)
- Core Workflows (common patterns)
- Navigation Guide (when to read supporting files)

### 5. Progressive Disclosure Tests

Validate that SKILL.md:
- References supporting files (not inlines content)
- Uses "Read when you need" pattern
- Keeps supporting files one level deep (no nesting)

### 6. Quality Tests

Validate supporting file quality:
- Examples contain complete code blocks
- References cover core APIs
- Patterns address production concerns
- Troubleshooting covers common issues
- No broken internal links

## TDD Methodology

These tests follow **Test-Driven Development** principles:

1. **Tests written first**: Before skill is complete
2. **Tests fail initially**: Red phase of red-green-refactor
3. **Clear failure messages**: Tell you exactly what's wrong
4. **Objective criteria**: Tests define "done"

### Expected TDD Cycle

```
1. Write tests (define success criteria)
2. Run tests → FAILURES (shows what needs fixing)
3. Fix skill content
4. Run tests → Some pass, some fail
5. Iterate until all tests pass
6. Skill is validated ✅
```

## Token Counting

Token counting uses `tiktoken` with `cl100k_base` encoding (closest to Claude's tokenizer):

```python
import tiktoken

def count_tokens(text: str) -> int:
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))
```

### Why Token Budgets Matter

- Skills load into Claude's context window
- Smaller skills = more room for actual code/context
- Target: 1800 tokens (allows 10% growth before hitting 2000 limit)
- Hard limit: 2000 tokens (absolute maximum)

## Adding Tests for New Skills

To add validation tests for a new skill:

1. **Copy template**:
   ```bash
   cp tests/skills/test_aspire_skill.py tests/skills/test_<skill-name>_skill.py
   ```

2. **Update constants**:
   ```python
   SKILL_DIR = WORKTREE_ROOT / ".claude" / "skills" / "<skill-name>"
   SKILL_FILE = SKILL_DIR / "SKILL.md"
   ```

3. **Customize required files** (if different from standard set):
   ```python
   REQUIRED_FILES = [
       "SKILL.md",
       "reference.md",
       "examples.md",
       "patterns.md",
       "troubleshooting.md",
   ]
   ```

4. **Adjust skill-specific validations** (e.g., activation keywords, key terms)

5. **Run tests** to see what fails, then fix the skill

## Common Issues and Fixes

### Issue: Token Budget Exceeded

**Symptom**: Tests fail with token count > 1800

**Fix**:
1. Move detailed examples to `examples.md`
2. Condense verbose sections
3. Use bullets instead of paragraphs
4. Reference supporting files instead of inlining

### Issue: Missing Section

**Symptom**: Test fails with "Missing '## SectionName' section"

**Fix**: Add the section header to SKILL.md

### Issue: Broken Internal Links

**Symptom**: Test fails with "broken internal links"

**Fix**: Verify all referenced files exist in skill directory

### Issue: Activation Keywords Insufficient

**Symptom**: Test fails with "missing required terms"

**Fix**: Add core skill terms to `activation_keywords` in frontmatter

## Philosophy Alignment

These tests enforce amplihack philosophy:

- **Ruthless Simplicity**: Token budgets force conciseness
- **Modular Design**: Each file has one clear purpose
- **Progressive Disclosure**: Load only what's needed
- **Zero-BS**: No stubs, all tests validate real content
- **Measurable Quality**: Objective metrics (token counts, structure)

## CI Integration

These tests can run in CI:

```yaml
# .github/workflows/validate-skills.yml
- name: Validate Skills
  run: uv run pytest tests/skills/ -v --tb=short
```

## Success Criteria

A skill passes validation when:

- ✅ All 47+ tests pass
- ✅ Token count ≤ 1800 (target) or 2000 (maximum)
- ✅ All required files exist
- ✅ YAML frontmatter is valid
- ✅ Content structure is complete
- ✅ Progressive disclosure is followed
- ✅ Examples and references are comprehensive
- ✅ No broken links

## Questions?

See:
- `TEST_RESULTS.md` for latest test run details
- `test_aspire_skill.py` for complete test implementation
- `~/.amplihack/.claude/skills/` for skill examples
