# FORBIDDEN_PATTERNS.md

Shell and git anti-patterns that are forbidden in this codebase.

These patterns mask errors, hide authentication failures, and violate the
fail-fast principle. CI and code review should reject any addition of these
patterns.

---

## 1. Silent failure via `|| true`

```bash
# FORBIDDEN
git push || true
some_command || true
```

**Why forbidden:** Swallows all errors silently. A failing command returns
success, making the pipeline appear healthy when it is not. Failures are
invisible in logs and CI.

**Correct pattern:** Let the command fail loudly, or handle the error
explicitly with a meaningful message and non-zero exit.

---

## 2. Silent push via `|| echo "Push prepared"`

```bash
# FORBIDDEN
git push 2>/dev/null || echo "Push prepared"
```

**Why forbidden:** The echo masks the push failure with a success-looking
message. Callers believe the push succeeded when it may have been rejected,
timed out, or failed due to permissions. The `2>/dev/null` also suppresses the
error output that would reveal the root cause.

**Correct pattern:**

```bash
git pull --rebase 2>/dev/null && git push
```

---

## 3. `2>/dev/null` on push commands

```bash
# FORBIDDEN
git push 2>/dev/null
git push origin HEAD 2>/dev/null
```

**Why forbidden:** Suppresses stderr on the push itself, hiding authentication
failures, permission errors, pre-receive hook rejections, and network errors.
These are critical signals that must surface immediately.

**Acceptable:** `2>/dev/null` on `git pull --rebase` is acceptable because
rebase progress output is noise. The push that follows must not suppress stderr.

---

## 4. `;` before `git push` inside a subshell where a preceding `git commit` could fail

```bash
# FORBIDDEN
(git commit -m "message" && git pull --rebase 2>/dev/null ; git push)
```

**Why forbidden:** The `;` separator is unconditional. If `git commit` or
`git pull --rebase` fails, execution continues to `git push` regardless.
This violates fail-fast: a push after a failed rebase can corrupt the remote
branch or push stale content.

**Correct pattern:**

```bash
(git commit -m "message" && git pull --rebase 2>/dev/null && git push)
```

---

## 5. Any pattern that masks git errors

```bash
# FORBIDDEN — general principle
git <any-command> 2>/dev/null || true
git <any-command> 2>/dev/null || echo "anything"
git <any-command> &>/dev/null
```

**Why forbidden:** Git errors carry critical diagnostic information:
authentication state, remote rejection reasons, merge conflicts, hook
failures. Masking them delays diagnosis and can lead to data loss or
silent divergence between local and remote state.

**Rule of thumb:** If a git command can fail in a way that affects the
integrity of the repository or the CI pipeline, it must fail loudly.

---

## Summary table

| Pattern | Risk | Status |
|---|---|---|
| `git push \|\| true` | Silent push failure | FORBIDDEN |
| `git push 2>/dev/null \|\| echo "..."` | Masked push error | FORBIDDEN |
| `git push 2>/dev/null` | Suppressed auth/permission errors | FORBIDDEN |
| `; git push` after fallible command in subshell | Push despite prior failure | FORBIDDEN |
| `git pull --rebase 2>/dev/null` | Noisy rebase output suppressed | ALLOWED |
| `git push -u origin <branch>` (initial tracking push) | No rebase needed | ALLOWED |
