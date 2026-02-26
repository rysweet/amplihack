# Tutorial: Using the Power-Steering Re-Enable Prompt

> **Diátaxis Category**: Tutorial (Learning-oriented)
> **Level**: Beginner
> **Time**: 5 minutes

## What You'll Learn

In this tutorial, you'll learn how to work with amplihack's power-steering re-enable prompt that appears when you've temporarily disabled power-steering. You'll understand what the prompt does, how to respond to it, and when to use each option.

## Prerequisites

- amplihack installed and configured
- Basic familiarity with running `amplihack launch` or `amplihack copilot`
- Have previously disabled power-steering at some point

## Background

Power-steering is amplihack's quality verification system that prevents incomplete work. Sometimes you might temporarily disable it (for valid reasons like debugging or experimental work). The re-enable prompt ensures you don't accidentally leave it disabled indefinitely.

## Step 1: Understanding When the Prompt Appears

The prompt only appears when **both** conditions are met:

1. You previously disabled power-steering by creating a `.disabled` file
2. You're starting a new amplihack session

**You'll see**:

````bash
Power-Steering is currently disabled.
Would you like to re-enable it? [Y/n] (30s timeout, defaults to YES):
````

## Step 2: Choosing Your Response

You have three options:

### Option A: Press Enter or Type 'Y' (Recommended)

This re-enables power-steering immediately.

**When to use**:
- You temporarily disabled for debugging and now want quality checks back
- You're starting normal development work
- You want the default safe behavior

**What happens**:
- `.disabled` file is removed
- Power-steering becomes active
- Quality checks will run on session completion

**Try it now**:

````bash
# If you see the prompt, just press Enter
[Y/n]: <press Enter>
````

### Option B: Type 'n' (Temporary Disable)

This keeps power-steering disabled for the current session.

**When to use**:
- You're continuing debugging work
- You're doing experimental development
- You want to explicitly control when to re-enable

**What happens**:
- `.disabled` file stays in place
- Power-steering remains disabled for this session
- Prompt will appear again on next startup

**Try it now**:

````bash
[Y/n]: n
# Power-steering remains disabled
````

### Option C: Wait 30 Seconds (Auto-Enable)

The prompt automatically chooses YES after 30 seconds.

**When to use**:
- You stepped away from keyboard during startup
- You're not sure what to choose (safe default)
- You want the fail-safe behavior

**What happens**:
- Same as pressing Enter or typing 'Y'
- Power-steering is re-enabled automatically
- Countdown shows remaining time

**Try it now**:

````bash
# Just wait and watch the countdown
[Y/n]: (28s remaining...)
[Y/n]: (25s remaining...)
# ... auto-enables at 0s
````

## Step 3: Verifying Your Choice

After responding, verify power-steering status:

**If you enabled** (Y or timeout):

````bash
# Check that .disabled file is gone
ls ~/.amplihack/.claude/runtime/power-steering/.disabled
# Should show: No such file or directory

# Power-steering will run at session end
````

**If you kept disabled** (n):

````bash
# Check that .disabled file still exists
ls ~/.amplihack/.claude/runtime/power-steering/.disabled
# Should show: .disabled file exists

# Power-steering will NOT run at session end
````

## Step 4: Working With Worktrees (Advanced)

If you use git worktrees, the behavior is slightly different:

**Shared state location**:
- The `.disabled` file is stored in the main repo's `.claude/runtime/power-steering/` directory
- All worktrees see the same disabled state
- This is by design to prevent confusion

**Try it** (if you use worktrees):

````bash
# From main repo
cd ~/myproject

# Check shared location
ls .claude/runtime/power-steering/.disabled

# From worktree
cd ~/myproject-worktrees/feature-branch

# Same location - shared state!
ls $(git rev-parse --git-common-dir)/.claude/runtime/power-steering/.disabled
````

## What You Learned

✅ When the re-enable prompt appears (startup after disabling)
✅ How to choose YES (press Enter or 'Y')
✅ How to choose NO (type 'n')
✅ What happens with timeout (auto-enables after 30s)
✅ How to verify your choice worked
✅ How worktrees share disabled state

## Next Steps

- **Explanation**: Learn [why power-steering re-enable exists](../features/power-steering/README.md#auto-re-enable-on-startup)
- **How-To**: Permanently [disable power-steering](../howto/power-steering-disable-permanently.md) if needed
- **Reference**: Check [power-steering API](../reference/power-steering-api.md) for technical details

## Common Questions

**Q: Can I skip the prompt entirely?**

A: Not recommended. The prompt exists to prevent accidental long-term disabling. If you frequently need power-steering disabled, consider customizing your workflow instead.

**Q: What if I press 'n' by mistake?**

A: No problem! Just manually remove the file:

````bash
rm ~/.amplihack/.claude/runtime/power-steering/.disabled
````

**Q: Does this work on Windows?**

A: Yes! The prompt uses cross-platform support (Unix signals + Windows threading).

**Q: Can I change the 30-second timeout?**

A: Not currently. The 30s timeout is hard-coded for safety (fail-open design). If you need more time, choose 'n' and manually re-enable later.

## Troubleshooting

**Prompt doesn't appear**: See [troubleshooting guide](../features/power-steering/README.md#troubleshooting)

**Timeout issues**: The 30s countdown is a safety feature and cannot be extended

**Worktree confusion**: Use the diagnostic command in the [worktree troubleshooting guide](../howto/power-steering-worktree-troubleshooting.md)

---

**Tutorial completed!** You now understand how to work with the power-steering re-enable prompt.
