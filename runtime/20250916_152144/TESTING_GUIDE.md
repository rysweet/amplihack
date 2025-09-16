# Testing Guide for /customize Command

## Prerequisites
- Claude Code should be restarted or the commands reloaded
- The command should appear in `/help` output

## Test Cases

### 1. Basic Command Help
```bash
/customize
```
Expected: Should show usage information and available actions

### 2. Show Default Preferences
```bash
/customize show
```
Expected: Display the default USER_PREFERENCES.md content

### 3. Set Verbosity
```bash
/customize set verbosity concise
```
Expected: Success message and preference updated

### 4. Set Invalid Value
```bash
/customize set verbosity invalid
```
Expected: Error message with valid options

### 5. Set Communication Style
```bash
/customize set communication_style casual
```
Expected: Success message

### 6. Set Preferred Languages
```bash
/customize set preferred_languages "python,typescript,rust"
```
Expected: Success message

### 7. Learn from Feedback
```bash
/customize learn "Always use async/await instead of promises"
```
Expected: Feedback captured and added to preferences

### 8. Show Updated Preferences
```bash
/customize show
```
Expected: Display updated preferences with all changes

### 9. Reset Specific Preference
```bash
/customize reset verbosity
```
Expected: Verbosity reset to "balanced"

### 10. Reset All Preferences
```bash
/customize reset
```
Expected: All preferences reset to defaults

## Verification Steps

1. Check that `.claude/context/USER_PREFERENCES.md` exists
2. Verify file updates after each set command
3. Confirm learned patterns accumulate in the file
4. Ensure timestamps are properly recorded

## Integration Testing

After setting preferences, test that:
1. New Claude Code sessions import USER_PREFERENCES.md
2. Agents can access preference values
3. Preferences persist across sessions

## Known Limitations

- Command requires bash shell features
- File edits use Claude Code's @Edit tool syntax
- Preferences apply to future agent invocations, not retroactively

## Troubleshooting

If the command doesn't appear:
1. Restart Claude Code
2. Check `.claude/commands/` directory
3. Verify customize.md file exists

If preferences aren't persisting:
1. Check file permissions on `.claude/context/`
2. Verify USER_PREFERENCES.md isn't corrupted
3. Ensure CLAUDE.md includes the import