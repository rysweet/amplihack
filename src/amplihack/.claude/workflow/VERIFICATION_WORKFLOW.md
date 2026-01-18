# Verification Workflow

For TRIVIAL changes: config edits, doc updates, single-line fixes

## When to Use

- Config file changes (_.yml, _.json, \*.toml)
- Documentation updates
- Presentational changes (CSS, styling)
- Simple fixes < 10 lines

## Workflow Steps (5 total)

### Step 1: Make Change

- [ ] Edit the file(s)
- [ ] Verify syntax (linter, formatter)

### Step 2: Verify Locally

- [ ] Run build command (if applicable)
- [ ] Visual check (if UI change)
- [ ] Test command succeeds (if CLI change)

### Step 3: Commit

- [ ] Commit with descriptive message
- [ ] Push to branch

### Step 4: Create PR

- [ ] Create PR with brief description
- [ ] Link to issue (if exists)

### Step 5: Verify CI

- [ ] CI passes
- [ ] Request review
- [ ] Merge when approved

**Total Time**: 5-10 minutes
**Tests Required**: Verification only (does it build?)
