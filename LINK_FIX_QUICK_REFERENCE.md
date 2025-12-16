# Link Fix Quick Reference

**One-page guide for fixing broken documentation links**

---

## Pattern Recognition Chart

```
┌─────────────────────────────────────────────────────────────────┐
│                     BROKEN LINK PATTERNS                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Pattern 1: DIRECTORY LINKS          (~15 occurrences)          │
│  ────────────────────────────────────────────────────────        │
│  Broken:  [Link](directory/)                                    │
│  Fixed:   [Link](directory/README.md)                           │
│           [Link](directory/index.md)                            │
│  Impact:  HIGH - Batch fixable with sed                         │
│                                                                  │
│  Pattern 2: RELATIVE PATHS           (~30 occurrences)          │
│  ────────────────────────────────────────────────────────        │
│  Broken:  [Link](../../other/section.md)                        │
│  Fixed:   [Link](/docs/other/section.md)                        │
│           Remove and rely on nav sidebar                        │
│  Impact:  MEDIUM - Requires review per link                     │
│                                                                  │
│  Pattern 3: MISSING FILES            (~10-20 occurrences)       │
│  ────────────────────────────────────────────────────────        │
│  Broken:  [Link](non-existent.md)                               │
│  Fixed:   Remove dead link                                      │
│           Create placeholder page                               │
│           Update to correct path                                │
│  Impact:  LOW - Manual review required                          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5-Minute Fix Guide

### Step 1: Run the Quick Wins (2 minutes)

```bash
cd /home/azureuser/src/amplihack

# Fix DDD directory links (15 broken links → 0)
sed -i 's|\](core_concepts/)|](core_concepts/README.md)|g' docs/document_driven_development/*.md
sed -i 's|\](phases/)|](phases/README.md)|g' docs/document_driven_development/*.md
sed -i 's|\](reference/)|](reference/README.md)|g' docs/document_driven_development/*.md

# Verify changes
git diff docs/document_driven_development/
```

### Step 2: Get Full Report (1 minute)

```bash
# Run link checker
python .github/scripts/link_checker.py

# Read results
cat broken_links_report.md
```

### Step 3: Triage Remaining Issues (2 minutes)

```bash
# Find cross-boundary links
grep -r "\](\\.\\.\/" docs/ | wc -l

# Find missing files
grep -rho "\]([^)]*\.md)" docs/ | sed 's/.*](//' | sed 's/).*//' | \
    while read f; do [ ! -f "docs/$f" ] && echo "MISSING: $f"; done
```

---

## Decision Tree

```
                    Found Broken Link
                           |
                           v
              ┌────────────┴────────────┐
              │                         │
         Ends with /               Has ../ path
              │                         │
              v                         v
    ┌─────────┴─────────┐      ┌───────┴───────┐
    │                   │      │               │
index.md exists?   README.md?  Same section?  Cross-section?
    │                   │      │               │
    v                   v      v               v
Add index.md      Add README   Keep & fix    Site-relative
or /README.md     to link      relative      or remove
```

---

## Batch Fix Commands

### Fix #1: DDD Directory Links
```bash
# What: Add README.md to directory-only links
# Where: docs/document_driven_development/
# Impact: Fixes ~15 links
sed -i 's|\](core_concepts/)|](core_concepts/README.md)|g' docs/document_driven_development/*.md
sed -i 's|\](phases/)|](phases/README.md)|g' docs/document_driven_development/*.md
sed -i 's|\](reference/)|](reference/README.md)|g' docs/document_driven_development/*.md
```

### Fix #2: Create Index Files (Alternative)
```bash
# What: Create index.md as symlinks to README.md
# Where: docs/document_driven_development/subdirs/
# Impact: Allows directory/ links to work
cd docs/document_driven_development
for dir in core_concepts phases reference; do
    ln -s README.md "$dir/index.md"
done
```

### Fix #3: Find All Directory Links
```bash
# What: Identify all directory-only links
# Output: List for manual review
grep -rE "\]\([^)]+/\)" docs/ | grep -v "http"
```

---

## Standards Cheat Sheet

### DO ✅

```markdown
[Guide](user-guide.md)                    # Same directory
[API](api/reference.md)                   # Subdirectory with file
[Config](/.claude/context/CONFIG.md)      # Site-absolute for cross-section
[Section](#heading)                       # Anchor in current page
[Doc](other.md#section)                   # Anchor in other page
```

### DON'T ❌

```markdown
[Guide](guides/)                          # Directory without file
[Doc](../../../other.md)                  # Deep relative paths
[File](/home/user/docs/file.md)           # Absolute filesystem paths
```

### MAYBE (Review Required) ⚠️

```markdown
[Doc](../sibling/file.md)                 # Relative within section - OK
[Doc](../../other-section/file.md)        # Cross-section - prefer site-relative
```

---

## File Naming Conventions

```
directory/
├── index.md          # MkDocs landing page (auto-indexed)
│                     # Use when: Want MkDocs to auto-resolve dir/
│
├── README.md         # GitHub-friendly intro
│                     # Use when: Want GitHub preview + explicit links
│                     # Link as: [Text](directory/README.md)
│
├── overview.md       # Conceptual introduction
├── guide.md          # How-to guide
├── reference.md      # API/command reference
└── subsection/
    └── index.md      # Subsection landing
```

**Recommendation**: Choose one pattern project-wide:
- **Pattern A**: All `index.md` (MkDocs native, allows `dir/` links)
- **Pattern B**: All `README.md` (GitHub-friendly, explicit links required)
- **Pattern C**: Hybrid with symlinks (both work, maintenance overhead)

---

## Testing Your Fixes

```bash
# 1. Run link checker
python .github/scripts/link_checker.py

# 2. Build docs locally
mkdocs build --strict

# 3. Preview site
mkdocs serve
# Visit http://localhost:8000 and click all links

# 4. Check specific file
python .github/scripts/link_checker.py 2>&1 | \
    grep "docs/your-file.md"
```

---

## Common Errors & Solutions

### Error: "File not found: core_concepts/"
```markdown
# Broken
[Link](core_concepts/)

# Fix Option 1: Add README.md
[Link](core_concepts/README.md)

# Fix Option 2: Add index.md
[Link](core_concepts/index.md)

# Fix Option 3: Link to specific page
[Link](core_concepts/retcon_writing.md)
```

### Error: "File not found: ../../Specs/..."
```markdown
# Broken
[Architecture](../../Specs/ARCHITECTURE.md)

# Fix Option 1: Site-relative path
[Architecture](/Specs/ARCHITECTURE.md)

# Fix Option 2: Add to mkdocs.yml nav
# Then remove inline link, rely on navigation

# Fix Option 3: Copy content to docs/
# If it should be in published docs
```

### Error: "Anchor not found: #section-name"
```markdown
# Common cause: Heading format difference

# Markdown heading
## Section Name

# Generates anchor
#section-name

# Link must match (case, spaces, special chars)
[Link](#section-name)  ✅
[Link](#Section-Name)  ❌
[Link](#section_name)  ❌
```

---

## Verification Checklist

After fixing links:

- [ ] Run `python .github/scripts/link_checker.py`
- [ ] Check `broken_links_report.md` shows 0 broken links
- [ ] Run `mkdocs build --strict` without errors
- [ ] Preview site with `mkdocs serve` and spot-check navigation
- [ ] Commit changes with descriptive message
- [ ] CI docs workflow passes on PR

---

## Need Help?

1. **Pattern not listed?** Check `DOCUMENTATION_LINK_PATTERNS_ANALYSIS.md`
2. **Unsure about fix?** Test locally with `mkdocs serve`
3. **Complex issue?** Run full link checker and analyze report
4. **Prevention?** Review standards in analysis document

---

**Quick Reference Version**: 1.0
**Last Updated**: 2025-12-02
**Companion Document**: DOCUMENTATION_LINK_PATTERNS_ANALYSIS.md
