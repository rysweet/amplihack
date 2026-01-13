# File Organization Guidelines

Guidelines fer organizing files in the amplihack repository. Followin' these keeps the root directory clean and makes documentation discoverable.

## Directory Structure

### Root Directory (/)

Keep the root directory minimal and focused on essential project files:

**Essential files only:**

- `README.md` - Project overview and quick start
- `CLAUDE.md` - Framework configuration and workflow selection
- `pyproject.toml` - Python package configuration
- `Makefile` - Build and scenario tool commands
- `LICENSE` - Project license
- `.gitignore` - Git ignore patterns

**Avoid placin' in root:**

- Test results or validation reports
- Evaluation summaries or analysis documents
- Legacy build files (like `setup.py` when using `pyproject.toml`)
- Documentation that belongs in `docs/`

### Documentation (docs/)

All documentation goes in the `docs/` directory, organized by type:

```
docs/
├── contributing/       # Contribution guidelines
│   └── file-organization.md  # This file
├── memory/            # Memory system documentation
│   └── evaluation-summary.md  # Memory evaluation results
├── testing/           # Testing documentation
│   └── gh-pages-link-validation.txt  # Link validation results
├── howto/             # Task-oriented guides
├── tutorials/         # Learning-oriented guides
├── reference/         # Information-oriented docs
└── concepts/          # Understanding-oriented docs
```

**See the [Eight Rules of Good Documentation](.claude/skills/documentation-writing/reference.md) fer complete guidelines.**

### Archive (archive/)

Legacy files that be superseded but may be needed fer reference:

```
archive/
└── legacy/
    ├── setup.py       # Superseded by pyproject.toml
    └── README.md      # Explains why files be archived
```

## File Movement Examples

### Recent Cleanup (Issue #1913)

These files were moved from root to organized locations:

| Original Location              | New Location                                | Reason                       |
| ------------------------------ | ------------------------------------------- | ---------------------------- |
| `EVALUATION_SUMMARY.md`        | `docs/memory/evaluation-summary.md`         | Memory system documentation  |
| `gh_pages_link_validation.txt` | `docs/testing/gh-pages-link-validation.txt` | Testing results              |
| `setup.py`                     | `archive/legacy/setup.py`                   | Superseded by pyproject.toml |

### When to Move Files

Move files when they:

- Clutter the root directory
- Belong to a specific documentation category
- Are superseded by newer approaches
- Are testing/validation results rather than source code

### When to Keep Files in Root

Keep files in root only when they:

- Are essential fer project setup (README, LICENSE, pyproject.toml)
- Configure the development environment (CLAUDE.md, Makefile)
- Are required by tools (pyproject.toml, .gitignore)

## Preventive Guidance

### Before Creating a New File

Ask these questions:

1. **Is this documentation?** → Place in `docs/` subdirectory
2. **Is this a test result?** → Place in `docs/testing/` or don't commit
3. **Is this superseded?** → Archive it in `archive/legacy/`
4. **Is this essential configuration?** → Root is acceptable
5. **Is this temporary?** → Don't commit to main

### File Type Decision Tree

```
New File?
├─ Documentation → docs/{category}/
├─ Test Result → docs/testing/ (or CI only)
├─ Legacy File → archive/legacy/
├─ Configuration → Root (if essential)
└─ Temporary → .gitignore
```

## Integration with Other Systems

### Cleanup Agent Gap

**Known Gap (Issue #1913):** The cleanup agent focuses on code quality (dead code, complexity) but doesn't enforce documentation organization. This was discovered during root cleanup and be documented fer future consideration - no immediate action needed.

**Future Enhancement Opportunity**: If root organization becomes a recurring issue, consider extending cleanup agent to suggest documentation moves. Not implemented yet - trust in emergence.

### Link Checkers

When movin' files:

- Update all internal links
- Run link validation before committing
- Use `make check-broken-links` to verify

## References

- [Eight Rules of Good Documentation](.claude/skills/documentation-writing/reference.md)
- [Documentation Guidelines](../DOCUMENTATION_GUIDELINES.md)
- [Legacy Files Archive](../../archive/legacy/README.md)

---

**Last Updated:** 2026-01-12
