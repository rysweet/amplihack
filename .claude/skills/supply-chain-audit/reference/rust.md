# Rust / Cargo Supply Chain — Dimension 9

## Lock Files and Build Integrity

**High**: `Cargo.lock` not committed (for binary crates — libraries may omit it, but CI
builds for deployment must pin exact versions).
**High**: `cargo install` in CI without `--locked` — resolves latest compatible versions.
**Medium**: `cargo update` present in CI pipeline (should only run in dev workflows).
**High**: `[patch]` or `[replace]` sections in `Cargo.toml` overriding upstream crates
without justification — potential shadow dependency injection.

## Registry Verification

**High**: `[registries]` in `Cargo.toml` or `.cargo/config.toml` pointing to non-crates.io
sources without documentation/justification.
**High**: `cargo install` from git URL without `--rev` or `--tag`:
`cargo install --git https://github.com/org/tool` — mutable reference.
**Medium**: `[source]` replacement redirecting crates.io to a mirror without checksum policy.

## Build Script Risks

**High**: crate dependency with `build.rs` that:

- Opens network connections (`std::net`, `reqwest` in build deps)
- Executes shell commands via `std::process::Command`
- Sets `cargo:rustc-link-search` to paths outside the project

Check `Cargo.toml` `build-dependencies` for crates known to have invasive build scripts.
Flag `links` key in `[package]` — can inject native library search paths.

**Info**: no `cargo vet` or `cargo crev` configuration present.

Fix: add `cargo vet` to enforce supply chain review policy:

```
cargo install cargo-vet
cargo vet init
```
