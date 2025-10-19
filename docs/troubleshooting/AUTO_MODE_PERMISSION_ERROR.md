# Auto Mode Permission Error - Troubleshooting

## Problem

When running `amplihack claude --auto`, you encounter:
```
option '--permission-mode <mode>' argument 'allow' is invalid
```

## Cause

Bug in `auto_mode.py` line 203 using incorrect Claude SDK argument.

## Solution

**Fixed in PR #948**

Changed from incorrect:
```python
permission_mode="allow"
```

To correct:
```python
dangerously_allow_permissions=True
```

## Verifying the Fix

**Check if you have the fix:**
```bash
git log --oneline | grep "permission argument"
```

If you see commit with "Correct Claude SDK permission argument", you have the fix.

**Test auto mode:**
```bash
amplihack claude --auto -- -p "Create a hello world script"
```

Should work without permission errors.

## Related Issues

- Issue #947: Auto mode fails with invalid permission_mode argument
- PR #948: Fix for the permission argument bug

## Prevention

This was a one-time bug introduced when Claude SDK API changed. The fix ensures we use the correct argument going forward.

---

**Fixed:** 2025-10-19
**PR:** #948
