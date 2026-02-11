---
name: SIMPLIFIED_WORKFLOW
version: 1.0.0
description: Documentation-optimized workflow with same quality gates as DEFAULT_WORKFLOW but docs-specific steps
steps: 16
applies_to:
  - Documentation-only changes
  - README updates
  - Tutorial writing
  - How-to guides
  - Reference documentation
phases:
  - requirements-clarification
  - design
  - writing
  - validation
  - review
  - merge
success_criteria:
  - "All steps completed"
  - "Examples verified runnable"
  - "Links validated"
  - "Markdown linting passed"
  - "PR is mergeable"
  - "Philosophy compliant"
philosophy_alignment:
  - principle: Ruthless Simplicity
    application: Every sentence must earn its place
  - principle: Zero-BS Implementation
    application: No placeholder examples or "coming soon" sections
  - principle: Modular Design
    application: Each section stands alone when appropriate
customizable: true
---

# SIMPLIFIED_WORKFLOW - Documentation Changes

**This is NOT a shortcut** - it's a docs-optimized workflow that maintains the same quality rigor as DEFAULT_WORKFLOW but removes code-specific steps.

## When to Use This Workflow

Use SIMPLIFIED_WORKFLOW for documentation-only changes:
- ✅ README updates
- ✅ Tutorial writing
- ✅ How-to guides
- ✅ Reference documentation
- ✅ API documentation
- ✅ Inline code documentation improvements

## When NOT to Use (Use DEFAULT_WORKFLOW Instead)

- ❌ Code changes (even with docs)
- ❌ API design
- ❌ Any file containing executable code
- ❌ Configuration changes that affect runtime behavior

---

## Step 0: Workflow Preparation (MANDATORY)

**Purpose**: Prevent step skipping and completion bias

**Actions**:
- [ ] Read entire workflow file (16 steps: 0-15)
- [ ] Understand this is docs-optimized, NOT fewer quality gates
- [ ] Proceed to Step 1

---

## Step 1: Prepare the Workspace

**Purpose**: Start with clean, up-to-date environment

**Actions**:
- [ ] Check git status: `git status` (no unstashed changes)
- [ ] Fetch latest: `git fetch`
- [ ] Verify on main branch: `git branch --show-current`

---

## Step 2: Clarify Documentation Requirements

**Purpose**: Define clear documentation goals

**Actions**:
- [ ] Identify target audience (developers, users, operators)
- [ ] Define documentation type (tutorial, how-to, reference, explanation - Diataxis framework)
- [ ] Document success criteria: What should readers be able to do after reading?
- [ ] Identify examples that need to be included
- [ ] Note: Use prompt-writer agent if requirements unclear

---

## Step 3: Create Issue/Work Item

**Purpose**: Track documentation work formally

**GitHub**:
```bash
gh issue create \
  --title "docs: Add getting started tutorial" \
  --body "Create tutorial for new users..." \
  --label documentation,enhancement
```

**Azure DevOps**:
```bash
az boards work-item create \
  --title "docs: Add getting started tutorial" \
  --type "User Story" \
  --description "Create tutorial..."
```

**Actions**:
- [ ] Create issue with clear description
- [ ] Add documentation label
- [ ] Note issue number for branch name

---

## Step 4: Setup Worktree and Branch

**Purpose**: Isolated development environment

**Actions**:
- [ ] Create worktree:
  ```bash
  git worktree add ./worktrees/docs-issue-{N}-{description} -b docs/issue-{N}-{description}
  ```
- [ ] Push to remote:
  ```bash
  cd ./worktrees/docs-issue-{N}-{description}
  git push -u origin docs/issue-{N}-{description}
  ```
- [ ] Switch to worktree: `cd ./worktrees/docs-issue-{N}-{description}`

---

## Step 5: Research and Design - Documentation Structure

**Purpose**: Plan documentation architecture before writing

**Actions**:
- [ ] Review existing documentation structure
- [ ] Identify where new docs fit (docs/, README, inline comments)
- [ ] Plan document outline (headings, sections, flow)
- [ ] Identify code examples needed (must be tested later)
- [ ] Plan diagram requirements (if any)
- [ ] Review style guide and conventions
- [ ] Identify cross-references and links needed

**Quality Gate**: Document outline approved before writing

---

## Step 6: Write Documentation

**Purpose**: Create comprehensive documentation following standards

**Standards**:
- [ ] Follow Diataxis framework (tutorial/how-to/reference/explanation)
- [ ] Place docs in `docs/` directory (not root)
- [ ] Link from appropriate entry points
- [ ] Use consistent terminology
- [ ] Include table of contents for long docs
- [ ] Add frontmatter metadata where applicable

**Actions**:
- [ ] Write clear, concise explanations
- [ ] Include runnable code examples (test in Step 7)
- [ ] Add cross-references and internal links
- [ ] Include prerequisites and setup instructions
- [ ] Add diagrams if helpful (mermaid format)

---

## Step 7: Verify Examples Are Runnable (MANDATORY)

**Purpose**: Ensure all code examples actually work (replaces TDD for docs)

**Actions**:
- [ ] Extract all code examples from documentation
- [ ] Test each example in clean environment
- [ ] Verify commands produce expected output
- [ ] Test copy-paste usability (no hidden characters)
- [ ] Verify dependencies are documented
- [ ] Test on target platform(s)

**Testing Checklist**:
```bash
# Example testing script
for example in docs/examples/*.sh; do
  bash -n "$example" && echo "✓ $example syntax valid"
  bash "$example" && echo "✓ $example runs successfully"
done
```

**Quality Gate**: Every code example must be tested

---

## Step 8: Markdown Linting and Link Validation (MANDATORY)

**Purpose**: Ensure technical correctness (replaces compilation/type checking)

**Actions**:
- [ ] Run markdown linter:
  ```bash
  markdownlint **/*.md || remark-lint **/*.md
  ```
- [ ] Validate all internal links (no broken references)
- [ ] Validate all external links:
  ```bash
  markdown-link-check **/*.md
  ```
- [ ] Check frontmatter syntax
- [ ] Verify code fence language tags
- [ ] Check heading hierarchy (no skipped levels: H1 → H3)
- [ ] Validate mermaid diagram syntax if present

**Quality Gate**: Zero linting errors, zero broken links

---

## Step 9: Refactor and Simplify (MANDATORY)

**Purpose**: Ruthless simplification of documentation

**Actions**:
- [ ] Remove unnecessary explanations
- [ ] Eliminate redundant examples
- [ ] Simplify complex sentences
- [ ] Remove jargon where possible
- [ ] Ensure single responsibility per section
- [ ] Verify no TODOs or placeholders remain (Zero-BS Implementation)
- [ ] Check reading level appropriate for audience

**Philosophy Check**:
- Every sentence must earn its place
- No "coming soon" or placeholder content
- Each section stands alone when possible

---

## Step 10: Review Pass Before Commit (MANDATORY)

**Purpose**: Comprehensive quality check before committing

**Actions**:
- [ ] Check documentation clarity and accuracy
- [ ] Verify examples are practical and realistic
- [ ] Check tone and style consistency
- [ ] Verify no placeholder content ("TODO", "TBD", "coming soon")
- [ ] Review for accessibility (alt text, clear language)

**PR Cleanliness Check**:
- [ ] Review staged changes: all related to issue?
- [ ] Remove temporary files (scratch_*.md, notes_*.txt)
- [ ] Remove point-in-time analysis docs
- [ ] Check for debugging comments or draft notes
- [ ] Verify .gitignore updated if new file types added

---

## Step 11: Incorporate Review Feedback

**Purpose**: Address pre-commit review findings

**Actions**:
- [ ] Address identified issues
- [ ] Update examples if needed
- [ ] Revise structure if issues identified
- [ ] Re-verify examples after changes

---

## Step 12: Commit and Push

**Purpose**: Save changes to git history

**Actions**:
- [ ] Stage all changes: `git add docs/`
- [ ] Write detailed commit message:
  ```bash
  git commit -m "docs: Add getting started tutorial (#123)

  - Create step-by-step setup guide
  - Add code examples for common tasks
  - Include troubleshooting section
  - Verify all examples tested"
  ```
- [ ] Reference issue number in commit
- [ ] Push to remote: `git push`

**Commit Format**: `docs: <description> (#<issue-number>)`

---

## Step 13: Open Pull Request as Draft

**Purpose**: Enable early review and CI checks

**GitHub**:
```bash
gh pr create --draft \
  --title "docs: Add getting started tutorial (#123)" \
  --body "## Documentation Changes

**Type**: Tutorial
**Target Audience**: New users

### Changes Made
- Added: docs/tutorials/getting-started.md
- Examples verified: Setup, basic usage, troubleshooting
- Links validated: All internal and external links checked

### Testing Results
All code examples tested in clean environment:
1. Installation example: ✅ Tested on Ubuntu 22.04
2. Basic usage example: ✅ Tested with sample data
3. Troubleshooting commands: ✅ All commands verified

### Checklist
- [x] Examples are runnable
- [x] Links validated (internal and external)
- [x] Markdown linting passed
- [x] Follows Diataxis framework
- [x] Placed in docs/ directory
- [x] Cross-referenced from README"
```

**Azure DevOps**:
```bash
az repos pr create \
  --title "docs: Add getting started tutorial (#123)" \
  --description "Documentation changes..." \
  --draft true
```

---

## Step 14: Review & Implement Feedback (MANDATORY - DO NOT SKIP)

**Purpose**: PR review and feedback implementation

⚠️ **MANDATORY - DO NOT SKIP** ⚠️

**Review Actions**:
- [ ] Review documentation accuracy and clarity
- [ ] Verify philosophy compliance
- [ ] Ensure examples tested and documented in PR
- [ ] Check for any technical errors

**Feedback Implementation**:
- [ ] Address each review comment
- [ ] Push updates to PR: `git push`
- [ ] Respond to review comments
- [ ] Ensure all validations still pass
- [ ] Request re-review if needed

**Quality Gate**: All review feedback addressed or explicitly discussed

---

## Step 15: Ensure PR is Mergeable (TASK COMPLETION POINT)

**Purpose**: Final verification before merge

**Philosophy Compliance Check**:
- [ ] Verify ruthless simplicity achieved
- [ ] Confirm zero-BS implementation (no placeholders)
- [ ] Verify documentation completeness

**Final Cleanup**:
- [ ] Review all changes for cleanliness
- [ ] Remove any temporary documentation artifacts
- [ ] Eliminate unnecessary complexity
- [ ] Ensure zero dead content or stubs
- [ ] Commit and push any cleanup changes if needed

**Convert PR to Ready**:
```bash
# GitHub
gh pr ready

# Azure DevOps
az repos pr update --id <pr_number> --draft false
```

**Verify Mergeable**:
- [ ] Verify all CI checks passing
- [ ] Resolve any merge conflicts
- [ ] Verify all review comments addressed
- [ ] Confirm PR is approved
- [ ] Close issue: `gh issue close 123` or `az boards work-item update --id 123 --state Closed`

**Quality Gate**: PR is approved, checks pass, ready to merge

---

## Success Criteria

Documentation changes are complete when:

1. ✅ All 16 steps completed sequentially
2. ✅ All code examples tested and working
3. ✅ All links validated (internal and external)
4. ✅ Markdown linting passes
5. ✅ PR approved by reviewers
6. ✅ CI checks pass
7. ✅ Philosophy compliance verified
8. ✅ PR is merged
9. ✅ Issue is closed

---

## Key Differences from DEFAULT_WORKFLOW

**Removed Steps** (code-specific):
- Step 7: TDD - Write Tests First (replaced with Step 7: Verify Examples)
- Step 5b: API Design (not applicable to docs)
- Step 5c: Database Design (not applicable to docs)
- Step 12: Code Compilation/Type Checking (replaced with Step 8: Markdown Linting)
- Multiple sub-steps for code quality (proportionality, outside-in testing)

**Adapted Steps** (docs-specific):
- Step 2: Clarify docs requirements (audience, type, examples)
- Step 5: Docs structure design (outline, examples, diagrams)
- Step 7: Verify examples runnable (replaces TDD)
- Step 8: Markdown linting + link validation (replaces compilation/type checking)

**Same Rigor, Different Focus**:
- ✅ Still has workspace prep (Step 1)
- ✅ Still has worktree isolation (Step 4)
- ✅ Still has multiple review passes (Steps 10, 14)
- ✅ Still has cleanup pass (Step 9)
- ✅ Still has philosophy check (Step 15)
- ✅ Still has mandatory testing (Step 7: example verification)

---

**This workflow maintains the same quality standards as DEFAULT_WORKFLOW while being optimized for documentation work.**
