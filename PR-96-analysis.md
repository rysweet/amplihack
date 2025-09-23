# PR #96 Analysis and Hook Configuration Solution

## What PR #96 Actually Does

PR #96 makes a simple change:

- Removes all hook definitions from the amplihack project's
  `.claude/settings.json`
- Adds CI fix for PYTHONPATH to make tests pass

This prevents the amplihack repository itself from interfering with global hook
installation.

## What PR #96 DOESN'T Solve

**The fundamental problem remains:** When users have their own projects with
`.claude/settings.json` that contain hooks, those project hooks completely
override the global amplihack hooks due to Claude Code's last-wins merge
strategy.

### Scenario Analysis

1. **✅ New user, fresh install**
   - Amplihack hooks installed to `~/.claude/settings.json`
   - No project hooks to interfere
   - **Works perfectly**

2. **✅ User working in amplihack repository**
   - After PR #96, no hooks in project settings
   - Global hooks work properly
   - **Works perfectly**

3. **❌ User with their own project that has hooks**
   - Project's `.claude/settings.json` has hooks
   - Project hooks completely override global amplihack hooks
   - Amplihack functionality lost in that project
   - **FAILS - This is the unsolved problem**

## The Real Problem

Claude Code uses a **last-wins merge strategy** for settings:

```
Final settings = global settings + project settings (overwrites)
```

If a project has ANY hooks defined, it completely replaces ALL global hooks.

## Possible Solutions

### Option 1: Documentation Only (Simplest)

- Document that users must manually merge hooks in their project settings
- Provide clear examples of how to include amplihack hooks
- **Pros:** Simple, no code needed
- **Cons:** Manual process, error-prone

### Option 2: Hook Merge Tool

- Create a CLI tool that helps users merge hooks
- `amplihack merge-hooks` would update project settings
- **Pros:** Automated, reliable
- **Cons:** Another tool to maintain

### Option 3: Install Script Enhancement

- Detect project settings during install
- Warn users about conflicts
- Offer to merge hooks automatically
- **Pros:** Proactive, catches issues early
- **Cons:** Complex logic in install.sh

### Option 4: Request Claude Code Change

- Ask Anthropic to change merge strategy to append hooks instead of replace
- **Pros:** Solves root cause
- **Cons:** Out of our control, may take time

## Recommended Approach

Given our philosophy of **ruthless simplicity**, I recommend:

1. **Merge PR #96** - It fixes the CI and cleans up our own project
2. **Create clear documentation** (Option 1) - Show users how to manually add
   amplihack hooks to their project settings
3. **File feature request** with Claude Code team for better hook merging
   (Option 4)

## Example Documentation for Users

````markdown
## If Your Project Has Hooks

If your project has a `.claude/settings.json` with hooks, you need to manually
add amplihack hooks:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          // Your existing project hooks here
          {
            "type": "command",
            "command": "/Users/YOU/.claude/tools/amplihack/hooks/session_start.py",
            "timeout": 10000
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          // Your existing project hooks here
          {
            "type": "command",
            "command": "/Users/YOU/.claude/tools/amplihack/hooks/stop.py",
            "timeout": 30000
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          // Your existing project hooks here
          {
            "type": "command",
            "command": "/Users/YOU/.claude/tools/amplihack/hooks/post_tool_use.py"
          }
        ]
      }
    ]
  }
}
```
````

```

## Conclusion

PR #96 is a good incremental improvement that:
- Fixes CI tests
- Cleans up the amplihack project itself
- Removes unnecessary complexity

But it doesn't solve the fundamental issue of project hooks overriding global hooks. That requires either:
- User education and manual configuration
- A change to Claude Code's merge behavior
- A more complex hook management system (which we rejected for violating simplicity)

The pragmatic solution is to merge PR #96 and document the limitation clearly.
```
