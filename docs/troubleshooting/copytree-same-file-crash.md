# Copytree Same-File Crash

> [Home](../index.md) > [Troubleshooting](README.md) > Copytree Same-File Crash

## Symptoms

When `AMPLIHACK_HOME` is set to the amplihack source tree itself (or to a
path that resolves to the same directory via symlinks), `copytree_manifest()`
crashes with:

```
shutil.SameFileError: '/home/user/src/amplihack/bin' and '/home/user/src/amplihack/bin' are the same file
```

This typically happens during:

- Local development with `AMPLIHACK_HOME=.`
- Symlinked installs where source and staging directory converge
- CI pipelines that reuse the checkout as the install target

## Root Cause

`copytree_manifest()` in `install.py` iterates over `ESSENTIAL_DIRS` and
copies each from the source tree into the destination. When source and
destination resolve to the same filesystem path, `shutil.copytree()` detects
the overlap and raises `SameFileError`.

## Fix

An `os.path.samefile()` guard now runs before each `shutil.copytree()` call.
If source and target resolve to the same inode, the copy is silently skipped
with a warning:

```
  ⚠️  Skipping bin: source and target are the same path
```

The guard:

- **Resolves symlinks** — `os.path.samefile()` compares real device/inode
  pairs, so symlinked paths that converge are correctly detected.
- **Fails open** — If `samefile()` raises `OSError` or `ValueError` (e.g.,
  on platforms where it is unsupported), the guard is bypassed and the normal
  copy proceeds.
- **Has no side effects** — It is a read-only stat check with no filesystem
  mutations.

## Verifying the Fix

```bash
# Reproduce the original crash (before fix):
AMPLIHACK_HOME=$(pwd) python -c "from amplihack.install import copytree_manifest; copytree_manifest('.', '.')"
# Expected (after fix): prints skip warnings, exits cleanly

# Run the regression tests:
pytest tests/unit/test_copytree_samefile.py -v
```

## Equivalent Rust Guard

The Rust CLI (`amplihack-rs`) has an identical guard in every
`copy_dir_recursive` function. It uses `std::fs::canonicalize()` to resolve
both paths and compares the results:

```rust
if let (Ok(canon_src), Ok(canon_dst)) = (source.canonicalize(), dest.canonicalize()) {
    if canon_src == canon_dst {
        // skip copy, log warning
        return Ok(());
    }
}
```

The Rust guard appears in:

| Crate               | File                             | Function              |
| -------------------- | -------------------------------- | --------------------- |
| `amplihack-cli`      | `src/auto_stager.rs`             | `copy_dir_recursive`  |
| `amplihack-launcher` | `src/auto_stager.rs`             | `copy_dir_recursive`  |
| `amplihack-context`  | `src/migration.rs`               | `copy_dir_recursive`  |
| `amplihack-cli`      | `src/commands/mode/migration.rs` | `copy_dir_recursive`  |

## Related

- [Issue #4296](https://github.com/rysweet/amplihack/issues/4296) — Original bug report
- [PR #4297](https://github.com/rysweet/amplihack/pull/4297) — Python fix
- [PR #201](https://github.com/rysweet/amplihack-rs/pull/201) — Rust fix
- [Interactive Installation](../INTERACTIVE_INSTALLATION.md) — Installation system overview
