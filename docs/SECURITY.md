# Security Guide

**Comprehensive security documentation for amplihack ecosystem components**

## Overview

amplihack integrates multiple ecosystem components, including Microsoft-maintained bundles, community-contributed extensions, and third-party API services. This guide provides security best practices, risk assessments, and configuration guidelines.

---

## Security Model

### Trust Levels

amplihack components operate under a three-tier trust model:

| Trust Level | Source               | Examples                                       | Security Posture                                               |
| ----------- | -------------------- | ---------------------------------------------- | -------------------------------------------------------------- |
| **High**    | Microsoft-maintained | lsp-suite, python-dev, ts-dev, notify          | Official maintenance, security reviews, rapid CVE response     |
| **Medium**  | Community-verified   | memory (michaeljabbour), perplexity (colombod) | Community review, limited security guarantees, use at own risk |
| **Low**     | Experimental/Custom  | User-created bundles                           | No security review, caveat emptor                              |

### Security Implications by Trust Level

**High Trust (Microsoft)**

- ✅ Regular security audits
- ✅ CVE tracking and rapid patching
- ✅ HTTPS-only Git URLs with verified ownership
- ✅ Documented data handling practices

**Medium Trust (Community)**

- ⚠️ Community-driven security review
- ⚠️ Slower CVE response times
- ⚠️ Limited security guarantees
- ⚠️ User responsibility for verification

**Low Trust (Experimental)**

- ❌ No security review process
- ❌ Unknown data handling practices
- ❌ Use only in isolated environments
- ❌ Audit before production use

---

## Bundle Security Profiles

### Dev Tools with Integrated LSP (High Trust)

**Bundles**: `python-dev` (includes `lsp-python`), `ts-dev` (includes `lsp-typescript`)

**What's Included**:

- **Code Quality**: Linting (ruff, eslint), formatting (black, prettier), type checking (pyright, tsserver)
- **LSP Intelligence**: Language servers for semantic code navigation, hover documentation, autocomplete
- **Auto-Fix**: One-command fixes for common issues

**Security Characteristics**:

- **Local execution only**: All processing happens on your machine
- **No external network calls**: Code and intelligence data never leaves your system
- **File system access**: Read-only access required for code analysis
- **Memory footprint**: ~50-200MB per language server + quality tools

**Risks**:

- **Low**: Quality tools and LSP servers have file system read access
- **Mitigation**: Use official Microsoft-maintained bundles only

**Configuration Security**:

```yaml
# Language servers and quality tools auto-discover based on project files
# No API keys or secrets required - all local processing
```

**Architecture Note**: LSP capabilities are bundled within dev-tools for simplicity. The `python-dev` bundle includes both ruff/pyright quality checks AND pylsp language intelligence. This integrated approach follows Microsoft's design: all Python development tooling together rather than split across separate bundles.

---

### Community: Memory Bundle (Medium Trust)

**Bundle**: `michaeljabbour/amplifier-bundle-memory`

**⚠️ PRIVACY WARNING: This bundle stores conversation history locally in a Kuzu graph database.**

**Security Characteristics**:

- **Local storage**: `~/.amplifier/memory/kuzu.db`
- **PII storage risk**: Conversations may contain sensitive information
- **No encryption at rest**: Database stored in plaintext
- **No external transmission**: Data stays on your machine

**Risks**:

- **HIGH**: PII exposure if database accessed by unauthorized users
- **MEDIUM**: Backup/sync tools may copy database to cloud storage
- **LOW**: Database corruption from concurrent access

**Mitigation**:

```bash
# 1. Set restrictive file permissions
chmod 600 ~/.amplifier/memory/kuzu.db

# 2. Exclude from cloud backup services
echo "~/.amplifier/memory/" >> ~/.cloudignore

# 3. Add to .gitignore globally
git config --global core.excludesfile ~/.gitignore_global
echo ".amplifier/memory/" >> ~/.gitignore_global

# 4. Regular cleanup of old data
# The memory bundle provides cleanup commands (see PRIVACY.md)
```

**When to Use**:

- ✅ Personal development machines (single-user)
- ✅ Ephemeral development environments
- ❌ Shared workstations
- ❌ Production servers
- ❌ CI/CD environments (unless explicitly configured)

---

### Community: Perplexity Bundle (Medium Trust)

**Bundle**: `colombod/amplifier-bundle-perplexity`

**⚠️ PRIVACY WARNING: This bundle sends queries to Perplexity AI's external API.**

**Security Characteristics**:

- **External API calls**: Queries sent to `https://api.perplexity.ai`
- **API key required**: `PERPLEXITY_API_KEY` environment variable
- **Data transmission**: Research queries leave your machine
- **Third-party processing**: Perplexity AI processes and stores queries

**Risks**:

- **HIGH**: Sensitive code/data exposure if included in research queries
- **MEDIUM**: API key exposure if not properly protected
- **MEDIUM**: Third-party data retention (per Perplexity privacy policy)

**Mitigation**:

```bash
# 1. NEVER hardcode API keys
# BAD:  config: { api_key: "sk-..." }  # pragma: allowlist secret
# GOOD: config: { api_key: "${PERPLEXITY_API_KEY}" }

# 2. Use .env files with restrictive permissions
echo "PERPLEXITY_API_KEY=your-key-here" > .env
chmod 600 .env

# 3. Verify .gitignore excludes secrets
grep -q "^\.env$" .gitignore || echo ".env" >> .gitignore

# 4. Use separate API keys per environment
# Development: PERPLEXITY_API_KEY_DEV
# Production:  PERPLEXITY_API_KEY_PROD
```

**Data Handling**:

- **Query content**: Sent to Perplexity AI
- **Responses**: Cached locally (optional)
- **Retention**: Subject to [Perplexity Privacy Policy](https://www.perplexity.ai/privacy)

**When to Use**:

- ✅ Research on public information
- ✅ Non-sensitive architectural questions
- ❌ Queries containing proprietary code
- ❌ Personal identifiable information (PII)
- ❌ Company confidential data

---

### Notifications Bundle (High Trust, Optional)

**Bundle**: `microsoft/amplifier-bundle-notify`

**Security Characteristics**:

- **Local notifications only**: Desktop notification system
- **No external services**: Uses OS notification APIs
- **No data transmission**: Messages stay on device

**Risks**:

- Low: Notification content visible on screen
- Mitigation: Configure sensitive information filtering

---

## API Key Management

### Best Practices

**1. Never Hardcode Secrets**

❌ **BAD**:

```yaml
providers:
  - module: provider-custom
    config:
      api_key: "sk-1234567890abcdef" # NEVER DO THIS  # pragma: allowlist secret
```

✅ **GOOD**:

```yaml
providers:
  - module: provider-custom
    config:
      api_key: "${CUSTOM_API_KEY}" # Environment variable
```

**2. Use .env Files with Restrictive Permissions**

```bash
# Create .env file
cat > .env <<EOF
PERPLEXITY_API_KEY=your-key-here
CUSTOM_PROVIDER_KEY=another-key
EOF

# Set restrictive permissions (owner read/write only)
chmod 600 .env

# Verify .gitignore excludes it
grep -q "^\.env$" .gitignore || echo ".env" >> .gitignore
```

**3. Use Secret Management Systems (Production)**

For production environments, use proper secret management:

```bash
# Azure Key Vault
export PERPLEXITY_API_KEY=$(az keyvault secret show --name perplexity-key --vault-name my-vault --query value -o tsv)

# AWS Secrets Manager
export PERPLEXITY_API_KEY=$(aws secretsmanager get-secret-value --secret-id perplexity-key --query SecretString --output text)

# HashiCorp Vault
export PERPLEXITY_API_KEY=$(vault kv get -field=api_key secret/perplexity)
```

**4. Rotate Keys Regularly**

```bash
# Set key rotation reminders
echo "Rotate API keys quarterly" >> ~/.amplifier/security-checklist.md

# Use key rotation scripts
# Example: .amplifier/scripts/rotate-keys.sh
```

---

## Data Privacy

### Data Flow by Component

| Component         | Data Collected                     | Storage Location              | External Transmission       | Retention                   |
| ----------------- | ---------------------------------- | ----------------------------- | --------------------------- | --------------------------- |
| **LSP Suite**     | Code structure, symbols            | Memory (RAM only)             | None                        | Session-scoped              |
| **Dev Tools**     | Linting/type errors                | Memory (RAM only)             | None                        | Session-scoped              |
| **Memory Bundle** | Conversation history, code context | `~/.amplifier/memory/kuzu.db` | None                        | Indefinite (manual cleanup) |
| **Perplexity**    | Research queries, responses        | Optional local cache          | **YES** - Perplexity AI API | Per Perplexity policy       |
| **Notify**        | Notification messages              | Memory (transient)            | None                        | Until dismissed             |

### PII Risk Assessment

**High Risk**:

- Memory bundle: Stores full conversation history (may contain PII)
- Perplexity bundle: Queries sent to external API (may contain sensitive data)

**Medium Risk**:

- Dev tools: Error messages may contain sensitive code paths

**Low Risk**:

- LSP suite: Only processes code structure (no content transmission)
- Notify: Transient local notifications

---

## Supply Chain Security

### Git URL Validation

All bundles use HTTPS Git URLs to prevent MITM attacks:

```yaml
# ✅ GOOD: HTTPS with verified repository
- bundle: git+https://github.com/microsoft/amplifier-bundle-lsp@main

# ❌ BAD: SSH (harder to verify, requires key setup)
- bundle: git+ssh://github.com/microsoft/amplifier-bundle-lsp@main

# ❌ BAD: HTTP (no encryption)
- bundle: git+http://github.com/microsoft/amplifier-bundle-lsp@main
```

### Dependency Pinning (Future)

**Current**: Bundles use `@main` for transparency and latest features

**Recommended for Production**: Pin to specific commit hashes

```yaml
# Development (current approach)
- bundle: git+https://github.com/microsoft/amplifier-bundle-lsp@main

# Production (recommended future approach)
- bundle: git+https://github.com/microsoft/amplifier-bundle-lsp@a1b2c3d4e5f6
```

### Bundle Verification

Before using community bundles, review their source:

```bash
# Clone bundle repository for inspection
git clone https://github.com/michaeljabbour/amplifier-bundle-memory

# Review bundle configuration
cat amplifier-bundle-memory/bundle.md

# Check for suspicious patterns
grep -r "eval\|exec\|system\|subprocess" amplifier-bundle-memory/

# Review git history for unusual commits
cd amplifier-bundle-memory && git log --oneline --graph
```

---

## Vulnerability Reporting

### Microsoft Bundles

Report vulnerabilities in Microsoft-maintained bundles:

- **Email**: [secure@microsoft.com](mailto:secure@microsoft.com)
- **GitHub**: [microsoft/amplifier-security](https://github.com/microsoft/amplifier/security)
- **CVE**: Use standard Microsoft vulnerability disclosure process

### Community Bundles

Report vulnerabilities directly to bundle authors:

- **Memory bundle**: [michaeljabbour/amplifier-bundle-memory/issues](https://github.com/michaeljabbour/amplifier-bundle-memory/issues)
- **Perplexity bundle**: [colombod/amplifier-bundle-perplexity/issues](https://github.com/colombod/amplifier-bundle-perplexity/issues)

### amplihack Framework

Report amplihack-specific issues:

- **GitHub Issues**: [rysweet/amplihack/issues](https://github.com/rysweet/amplihack/issues)
- **Security Label**: Use `security` label for sensitive issues
- **Private Disclosure**: Email maintainer for critical vulnerabilities

---

## Security Checklist

### Initial Setup

- [ ] Review trust levels for all bundles
- [ ] Set restrictive permissions on memory database (`chmod 600`)
- [ ] Configure `.env` files for API keys
- [ ] Verify `.gitignore` excludes secrets (`.env`, `*.key`, `*secret*`, `*token*`)
- [ ] Review Perplexity privacy policy if using research bundle
- [ ] Document API key rotation schedule

### Regular Maintenance

- [ ] Audit memory database for PII monthly
- [ ] Rotate API keys quarterly
- [ ] Update bundles to latest versions
- [ ] Review bundle source code for community bundles
- [ ] Check for security advisories on bundle repositories

### Before Production Deployment

- [ ] Pin bundle versions to commit hashes (not `@main`)
- [ ] Use secret management systems (Azure Key Vault, AWS Secrets Manager)
- [ ] Enable audit logging for API key access
- [ ] Configure data retention policies
- [ ] Document incident response procedures

---

## Configuration Examples

### Secure Bundle Configuration

```yaml
# amplifier-bundle/behaviors/community.yaml
bundle:
  name: amplihack-community
  description: "Community bundles with security controls"

includes:
  # Memory bundle - local storage only
  - bundle: git+https://github.com/michaeljabbour/amplifier-bundle-memory@main

  # Perplexity bundle - requires API key
  - bundle: git+https://github.com/colombod/amplifier-bundle-perplexity@main

# Security controls for community bundles
tools:
  - module: tool-memory
    config:
      # Restrict memory storage location
      database_path: "${AMPLIFIER_MEMORY_DB:-~/.amplifier/memory/kuzu.db}"
      # Enable automatic PII filtering (future enhancement)
      enable_pii_filter: true
      # Data retention period (days)
      retention_days: 90

  - module: tool-perplexity
    config:
      # Use environment variable for API key
      api_key: "${PERPLEXITY_API_KEY}"
      # Disable query caching for sensitive projects
      enable_cache: false
      # Rate limiting
      max_queries_per_minute: 10
```

### Secure Environment File

```bash
# .env (chmod 600)
# =================

# Perplexity API (for research bundle)
PERPLEXITY_API_KEY=your-key-here

# Custom memory database location
AMPLIFIER_MEMORY_DB=~/.amplifier/memory/kuzu.db

# Optional: Separate keys per environment
# PERPLEXITY_API_KEY_DEV=dev-key
# PERPLEXITY_API_KEY_PROD=prod-key
```

---

## Frequently Asked Questions

### Is my code safe with LSP bundles?

**Yes**. LSP bundles run language servers locally on your machine. No code is transmitted externally. Language servers only read your code to provide intelligence features (autocomplete, go-to-definition, etc.).

### Does the memory bundle send data to external services?

**No**. The memory bundle stores all data locally in `~/.amplifier/memory/kuzu.db`. However, **the database is not encrypted** and may contain sensitive information from your conversations.

### Can I use amplihack in corporate environments?

**Yes, with precautions**:

- Disable community bundles if your security policy prohibits them
- Use only Microsoft-maintained bundles (High Trust)
- Review and approve all bundles with your security team
- Configure API key management per corporate policy

### How do I opt out of specific bundles?

Edit `amplifier-bundle/bundle.md` and remove unwanted bundle includes:

```yaml
includes:
  # Comment out unwanted bundles
  # - bundle: git+https://github.com/michaeljabbour/amplifier-bundle-memory@main
  - bundle: git+https://github.com/microsoft/amplifier-bundle-lsp@main
```

### What happens if I commit an API key to git?

**Immediate action required**:

1. Rotate the exposed key immediately
2. Rewrite git history to remove the secret
3. Enable git secret scanning (e.g., trufflehog, git-secrets)
4. Add pre-commit hooks to prevent future exposure

---

## Additional Resources

- [PRIVACY.md](./PRIVACY.md) - Detailed data handling disclosure
- [PREREQUISITES.md](./PREREQUISITES.md) - API key setup guide
- [Security Recommendations](./SECURITY_RECOMMENDATIONS.md) - General best practices
- [Perplexity Privacy Policy](https://www.perplexity.ai/privacy) - Third-party data handling

---

**Last Updated**: 2026-02-11
**Version**: 0.8.0
**Maintained By**: amplihack community
