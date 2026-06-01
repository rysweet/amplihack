# ⚠️ This repository is deprecated

**amplihack has been rewritten in Rust.** This Python repository is no longer maintained.

👉 **Use [amplihack-rs](https://github.com/rysweet/amplihack-rs) instead.**

---

## Migrating to amplihack-rs

### Quick upgrade (existing users)

```bash
# 1. Install the Rust binary
curl -sL https://github.com/rysweet/amplihack-rs/releases/latest/download/amplihack-x86_64-unknown-linux-gnu.tar.gz | tar xz
sudo cp amplihack amplihack-hooks /usr/local/bin/

# 2. Re-run install to refresh all framework assets (recipes, skills, hooks)
amplihack install

# 3. Verify
amplihack --version
amplihack doctor
```

> **macOS (Apple Silicon):** replace `x86_64-unknown-linux-gnu` with `aarch64-apple-darwin`
>
> **macOS (Intel):** replace with `x86_64-apple-darwin`

### What changed

| | Python (this repo) | Rust ([amplihack-rs](https://github.com/rysweet/amplihack-rs)) |
|---|---|---|
| **Runtime** | Python 3.11+ / uv | Single static binary — no runtime deps |
| **Recipe runner** | `run_recipe_by_name()` | `amplihack recipe run <recipe>.yaml` |
| **Hooks** | Python scripts (`*.py`) | Native Rust binary (`amplihack-hooks`) |
| **Orchestration** | `orch_helper.py` | `amplihack orch helper` (native Rust) |
| **Performance** | ~2s startup | <50ms startup |
| **Install** | `pip install` / `uv tool install` | `amplihack install` (self-contained) |

### If you have the old Python version installed

```bash
# Remove the old Python installation
pip uninstall amplihack 2>/dev/null
uv tool uninstall amplihack 2>/dev/null

# Remove stale Python source tree (if present)
rm -rf ~/.amplihack/src/

# Install fresh from Rust
curl -sL https://github.com/rysweet/amplihack-rs/releases/latest/download/amplihack-x86_64-unknown-linux-gnu.tar.gz | tar xz
sudo cp amplihack amplihack-hooks /usr/local/bin/
amplihack install
```

### Keeping up to date

```bash
amplihack update
```

This downloads the latest release binary **and** refreshes all framework assets (recipes, skills, hooks) automatically.

---

## Links

- **New repo:** [github.com/rysweet/amplihack-rs](https://github.com/rysweet/amplihack-rs)
- **Releases:** [amplihack-rs/releases](https://github.com/rysweet/amplihack-rs/releases)
- **Documentation:** [rysweet.github.io/amplihack-rs](https://rysweet.github.io/amplihack-rs/) *(coming soon)*
- **Issues:** [amplihack-rs/issues](https://github.com/rysweet/amplihack-rs/issues)

---

<details>
<summary>Original README (archived)</summary>

# amplihack

Development framework for Claude Code, GitHub Copilot CLI, and Microsoft
Amplifier. Adds structured workflows, persistent memory, specialized agents,
goal-seeking capabilities, autonomous execution, and continuous improvement for
systematic software engineering.

**This version is no longer maintained. See [amplihack-rs](https://github.com/rysweet/amplihack-rs).**

</details>
