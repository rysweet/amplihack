# Privacy Policy

**Data handling disclosure for amplihack ecosystem components**

## Overview

This privacy policy describes how data is collected, stored, processed, and transmitted by amplihack and its integrated ecosystem components. amplihack prioritizes user privacy by default, with most processing happening locally on your machine.

**Last Updated**: 2026-02-11
**Effective Date**: 2026-02-11
**Version**: 0.8.0

---

## Quick Summary

| Component             | Data Collected                    | Stored Locally            | Sent Externally | Encryption      |
| --------------------- | --------------------------------- | ------------------------- | --------------- | --------------- |
| **Core amplihack**    | Session metadata, command history | ✅ Yes                    | ❌ No           | ❌ Plaintext    |
| **LSP Suite**         | Code structure, AST               | ✅ RAM only               | ❌ No           | N/A (transient) |
| **Dev Tools**         | Linting/type errors               | ✅ RAM only               | ❌ No           | N/A (transient) |
| **Memory Bundle**     | Full conversation history         | ✅ `~/.amplifier/memory/` | ❌ No           | ❌ Plaintext    |
| **Perplexity Bundle** | Research queries                  | ⚠️ Optional cache         | ✅ **YES**      | TLS in transit  |
| **Notifications**     | Message content                   | ✅ RAM (transient)        | ❌ No           | N/A (transient) |

---

## Data Collection

### Core amplihack Framework

**What We Collect**:

- Command invocation history (which agents/workflows executed)
- Session duration and token usage statistics
- Error logs and stack traces (local only)
- User preferences (stored in `~/.amplihack/.claude/USER_PREFERENCES.md`)

**Purpose**: Improve user experience, debug issues, track usage patterns

**Storage Location**: `~/.amplihack/.claude/logs/`

**Retention Period**: 30 days (automatic cleanup via log rotation)

**User Control**: Disable logging via `AMPLIHACK_DISABLE_LOGS=1`

---

### Dev Tools with Integrated LSP (python-dev, ts-dev)

**What We Collect**:

- **Code Quality Data**: Linting errors, type checking results, formatting violations, code quality metrics
- **LSP Intelligence Data**: Source code AST, symbol definitions/references, type information, import graphs

**Purpose**:

- Provide code quality checks and automated fixes
- Enable code intelligence features (autocomplete, go-to-definition, hover, find references)

**Storage Location**: Memory (RAM) only - **no persistent storage**

**Retention Period**: Session-scoped (cleared when dev tools/language servers stop)

**Data Transmission**: **None** - all processing is local

**User Control**: Disable dev tools (and their integrated LSP) by not including dev-tools bundles

**Architecture Note**: The `python-dev` bundle includes both ruff/pyright quality tools AND pylsp language intelligence. Similarly, `ts-dev` includes eslint/prettier AND typescript-language-server. This integrated approach means you get both code quality AND code intelligence from a single bundle.

---

### Memory Bundle (michaeljabbour/amplifier-bundle-memory)

⚠️ **PRIVACY IMPACT: HIGH** - This bundle stores full conversation history locally.

**What We Collect**:

- Complete conversation transcripts
- User messages and assistant responses
- Code snippets shared in conversations
- Metadata: timestamps, session IDs, agent names
- Knowledge graph relationships between concepts

**Purpose**:

- Persistent memory across sessions
- Context recall for long-running projects
- Knowledge graph navigation

**Storage Location**: `~/.amplifier/memory/kuzu.db` (Kuzu graph database)

**Retention Period**: **Indefinite** (manual cleanup required)

**Encryption**: ❌ **Not encrypted at rest**

**Data Transmission**: ❌ **None** - stays local

**Personal Information Risk**:

- **HIGH**: Conversations may contain:
  - Personal identifiable information (PII)
  - Company confidential data
  - API keys or passwords (if accidentally shared)
  - Proprietary code or algorithms

**User Control**:

```bash
# View memory database location
ls -lh ~/.amplifier/memory/kuzu.db

# Check database size
du -sh ~/.amplifier/memory/

# Delete all memory data
rm -rf ~/.amplifier/memory/

# Set restrictive permissions
chmod 600 ~/.amplifier/memory/kuzu.db

# Exclude from backups
echo "~/.amplifier/memory/" >> ~/.rsync-exclude
```

**Data Subject Rights**:

- **Access**: Query database via memory bundle commands
- **Rectification**: Edit or delete specific memories
- **Erasure**: Delete entire database with `rm -rf ~/.amplifier/memory/`
- **Portability**: Database stored in Kuzu format (exportable to JSON/CSV)

---

### Perplexity Bundle (colombod/amplifier-bundle-perplexity)

⚠️ **PRIVACY IMPACT: HIGH** - This bundle sends queries to external API.

**What We Collect**:

- Research queries you submit
- Context provided with queries
- API responses (if caching enabled)

**Purpose**: Deep research using Perplexity AI's search capabilities

**Storage Location**:

- Local cache: `~/.amplifier/perplexity-cache/` (optional)
- External: Perplexity AI servers

**Retention Period**:

- Local cache: 7 days (configurable)
- Perplexity AI: Per their [privacy policy](https://www.perplexity.ai/privacy)

**Data Transmission**: ✅ **YES** - Queries sent to `https://api.perplexity.ai`

**Encryption**: TLS 1.3 in transit

**Third-Party Processor**: Perplexity AI, Inc.

**Personal Information Risk**:

- **HIGH** if queries contain:
  - Proprietary code snippets
  - Company confidential information
  - Personal data or PII
  - Security-sensitive details

**Data Shared with Perplexity AI**:

- Query text
- Context snippets (if provided)
- API key (for authentication)
- Timestamp of request
- Your IP address (standard HTTP headers)

**Perplexity AI Data Usage**:

- Per [Perplexity Privacy Policy](https://www.perplexity.ai/privacy):
  - Query data used to provide service
  - May be used for model training (opt-out available)
  - Stored for service improvement
  - Subject to Perplexity data retention policies

**User Control**:

```bash
# Disable Perplexity bundle entirely
# Remove from amplifier-bundle/bundle.md includes

# Use without caching (no local storage)
export PERPLEXITY_ENABLE_CACHE=false

# Clear local cache
rm -rf ~/.amplifier/perplexity-cache/

# Opt out of Perplexity data usage
# Contact Perplexity AI per their privacy policy
```

**When NOT to Use**:

- ❌ Queries containing proprietary code
- ❌ Company confidential information
- ❌ Personal identifiable information
- ❌ Security-sensitive details
- ❌ Regulated data (HIPAA, GDPR protected data)

**Safe Use Cases**:

- ✅ Public documentation research
- ✅ Open-source library comparisons
- ✅ General programming concepts
- ✅ Non-sensitive architectural questions

---

### Notifications Bundle (microsoft/amplifier-bundle-notify)

**What We Collect**:

- Notification message content
- Notification metadata (title, timestamp, priority)

**Purpose**: Desktop notifications for workflow events

**Storage Location**: Operating system notification system (RAM, transient)

**Retention Period**: Until user dismisses notification (typically seconds to minutes)

**Data Transmission**: **None** - uses OS-native notification APIs

**Privacy Considerations**:

- Notifications may be visible to others viewing your screen
- Some OS logging may capture notification text
- Notification history may be accessible via OS notification center

**User Control**: Disable notifications by not including notify bundle

---

## Data Storage

### Storage Locations

```
~/.amplihack/
├── .claude/
│   ├── logs/               # Command logs (30-day retention)
│   ├── USER_PREFERENCES.md # User settings
│   └── context/            # Context files (read-only)
│
~/.amplifier/
├── memory/
│   ├── kuzu.db            # Memory bundle database (CONTAINS CONVERSATIONS)
│   └── backups/           # Automatic backups (if enabled)
│
├── perplexity-cache/      # Optional query cache (7-day retention)
│   └── queries/
│
└── lsp/                   # LSP server configs (no conversation data)
    ├── python/
    ├── typescript/
    └── rust/
```

### File Permissions

**Recommended permissions** to protect sensitive data:

```bash
# Memory database (contains conversations)
chmod 600 ~/.amplifier/memory/kuzu.db

# User preferences (may contain API keys)
chmod 600 ~/.amplihack/.claude/USER_PREFERENCES.md

# Perplexity cache (contains query history)
chmod 600 ~/.amplifier/perplexity-cache/

# Log files (contain command history)
chmod 600 ~/.amplihack/.claude/logs/*
```

### Backup Considerations

**Risk**: Backup services may expose sensitive data

**Mitigation**:

```bash
# Exclude from Time Machine (macOS)
tmutil addexclusion ~/.amplifier/memory/

# Exclude from rsync backups
echo "~/.amplifier/memory/" >> ~/.rsync-exclude

# Exclude from cloud sync (Dropbox, OneDrive, etc.)
# Add to respective service's ignore patterns
```

---

## Data Transmission

### Local Processing (No Transmission)

These components **never** transmit data externally:

- ✅ Core amplihack framework
- ✅ LSP suite (all languages)
- ✅ Dev tools (python-dev, ts-dev)
- ✅ Memory bundle
- ✅ Notifications bundle

**All processing happens on your local machine.**

### External Transmission

Only **one** component transmits data externally:

#### Perplexity Bundle

**Endpoint**: `https://api.perplexity.ai/chat/completions`

**Data Sent**:

```json
{
  "model": "sonar",
  "messages": [
    {
      "role": "user",
      "content": "Your research query here"
    }
  ]
}
```

**Transport Security**:

- TLS 1.3 encryption
- Certificate pinning (recommended)
- No fallback to unencrypted HTTP

**Headers Sent**:

- `Authorization: Bearer ${PERPLEXITY_API_KEY}`
- `Content-Type: application/json`
- `User-Agent: amplihack/0.8.0`

**IP Address Exposure**: Your IP address is visible to Perplexity AI (standard for all HTTP requests)

**DNS Leakage**: Queries may expose which domains/topics you're researching

---

## Third-Party Processors

### Perplexity AI, Inc.

**Role**: Research query processing

**Data Processed**: Research queries submitted via perplexity bundle

**Privacy Policy**: https://www.perplexity.ai/privacy

**Location**: United States (check their privacy policy for data center locations)

**Data Retention**: Per Perplexity privacy policy

**User Rights**:

- Right to access data
- Right to deletion (contact Perplexity)
- Right to opt-out of data usage for training

**Contact**:

- Privacy inquiries: [privacy@perplexity.ai](mailto:privacy@perplexity.ai)
- Privacy policy: https://www.perplexity.ai/privacy

---

## User Rights

### Right to Access

**Memory Bundle Data**:

```bash
# View conversation history
# (Memory bundle provides query commands)

# Export to JSON
# (Memory bundle provides export functionality)
```

**Log Data**:

```bash
# View command logs
cat ~/.amplihack/.claude/logs/amplihack.log

# View specific session
grep "session-id" ~/.amplihack/.claude/logs/amplihack.log
```

### Right to Rectification

**Edit Stored Data**:

```bash
# Edit user preferences
vim ~/.amplihack/.claude/USER_PREFERENCES.md

# Memory bundle provides commands to update specific memories
```

### Right to Erasure

**Delete All Data**:

```bash
# Delete conversation history
rm -rf ~/.amplifier/memory/

# Delete logs
rm -rf ~/.amplihack/.claude/logs/

# Delete cache
rm -rf ~/.amplifier/perplexity-cache/

# Delete preferences (resets to defaults)
rm ~/.amplihack/.claude/USER_PREFERENCES.md
```

**Delete Specific Data**:

```bash
# Memory bundle provides granular deletion
# (e.g., delete memories from specific date range, containing specific keywords)
```

### Right to Data Portability

**Export Formats**:

- Memory database: Kuzu native format (exportable to JSON/CSV)
- Logs: Plain text
- Preferences: Markdown

**Export Commands**:

```bash
# Memory bundle provides export to standard formats
# (JSON, CSV, markdown)
```

### Right to Object

Users can opt out of specific data collection:

```bash
# Disable logging
export AMPLIHACK_DISABLE_LOGS=1

# Disable memory bundle
# (Remove from bundle configuration)

# Disable perplexity bundle
# (Remove from bundle configuration)

# Disable notifications
# (Remove from bundle configuration)
```

---

## Data Security

### Encryption

**At Rest**:

- ❌ Memory database: **Not encrypted** (plaintext Kuzu database)
- ❌ Logs: **Not encrypted** (plaintext files)
- ❌ Cache: **Not encrypted** (plaintext JSON)

**In Transit**:

- ✅ Perplexity API: TLS 1.3
- N/A for local-only components

**User-Managed Encryption**:

Users can enable filesystem-level encryption:

```bash
# macOS: FileVault
# Encrypts entire home directory including ~/.amplifier/

# Linux: LUKS/dm-crypt
# Encrypt partition containing ~/.amplifier/

# Per-directory encryption (macOS)
# Use encrypted disk images for sensitive directories
```

### Access Control

**File System Permissions**:

```bash
# Recommended permissions
chmod 700 ~/.amplihack/
chmod 700 ~/.amplifier/
chmod 600 ~/.amplifier/memory/kuzu.db
chmod 600 ~/.amplihack/.claude/logs/*
```

**API Key Protection**:

```bash
# Never hardcode in configuration
# Use environment variables
export PERPLEXITY_API_KEY="your-key"  # pragma: allowlist secret

# Or .env files with restrictive permissions
echo "PERPLEXITY_API_KEY=your-key" > .env
chmod 600 .env
```

---

## Children's Privacy

amplihack is not directed at children under 13 (or 16 in the EU). We do not knowingly collect personal information from children. If you are a parent or guardian and believe your child has provided data through amplihack, contact the maintainers.

---

## International Data Transfers

### Local Components

All local components (LSP, dev tools, memory bundle) **never** transfer data internationally. Data stays on your machine.

### Perplexity Bundle

When using the Perplexity bundle:

- Data may be transferred to United States (Perplexity AI servers)
- Subject to U.S. data protection laws
- May be subject to CLOUD Act or similar regulations
- Users in the EU: Data transfer may not have adequacy decision

**EU/EEA Users**: Review Perplexity AI's GDPR compliance documentation before use.

---

## Compliance

### GDPR (EU Users)

**Legal Basis for Processing**:

- Legitimate interest (core framework features)
- Consent (optional bundles like Perplexity)

**Data Controller**:

- For local data: You (the user)
- For Perplexity data: Perplexity AI, Inc.

**Data Protection Officer**: N/A (amplihack is open-source software, not a service)

**Rights**:

- Access, rectification, erasure (see User Rights section)
- Data portability (export commands available)
- Object to processing (disable specific bundles)

### CCPA (California Users)

**Do Not Sell**: amplihack does not sell user data

**Categories of Personal Information**: Conversation history (if memory bundle enabled)

**Disclosure**: Only to Perplexity AI (if perplexity bundle enabled)

**Rights**: Access, deletion, opt-out (see User Rights section)

---

## Changes to This Policy

**Notification**: Updates will be announced via:

- GitHub releases: https://github.com/rysweet/amplihack/releases
- Documentation site: https://rysweet.github.io/amplihack/PRIVACY/
- In-app notifications (if opted in)

**Material Changes**: Will be highlighted with 30-day notice period

**Version History**: Available at https://github.com/rysweet/amplihack/commits/main/docs/PRIVACY.md

---

## Contact Information

### amplihack Framework

**Issue Tracker**: https://github.com/rysweet/amplihack/issues

**Privacy Concerns**: Label issue with `privacy` tag

**Security Issues**: See [SECURITY.md](./SECURITY.md) for vulnerability reporting

### Microsoft Bundles

**Security/Privacy**: [secure@microsoft.com](mailto:secure@microsoft.com)

**GitHub**: https://github.com/microsoft/amplifier/issues

### Community Bundles

**Memory Bundle**: https://github.com/michaeljabbour/amplifier-bundle-memory/issues

**Perplexity Bundle**: https://github.com/colombod/amplifier-bundle-perplexity/issues

---

## Frequently Asked Questions

### Does amplihack send my code to external servers?

**No**, with one exception:

- LSP suite, dev tools, memory bundle: **All local processing**
- Perplexity bundle: **Only if you explicitly use it** for research queries

### Can I use amplihack without any data leaving my machine?

**Yes**. Simply don't include the Perplexity bundle. All other components are local-only.

### Is my conversation history encrypted?

**No**. The memory bundle stores conversations in plaintext. Use filesystem-level encryption (FileVault, LUKS) if you need encryption.

### What happens if I use amplihack on a company laptop?

- Your employer may have access to files in `~/.amplihack/` and `~/.amplifier/`
- Memory database may be subject to corporate backup policies
- Perplexity queries may be logged by corporate proxies/firewalls
- **Recommendation**: Review with your security team before using memory or perplexity bundles

### How do I completely remove all amplihack data?

```bash
# Delete all configuration and data
rm -rf ~/.amplihack/
rm -rf ~/.amplifier/

# Uninstall package
pip uninstall amplihack
```

### Can I use amplihack with HIPAA/PII data?

**Not recommended**:

- Memory bundle stores data unencrypted
- Perplexity bundle sends queries externally
- No business associate agreements (BAAs) in place

**If you must**:

- Disable memory bundle
- Disable perplexity bundle
- Use only local-only components (LSP, dev tools)
- Enable full-disk encryption
- Document as part of your privacy impact assessment

---

## Additional Resources

- [SECURITY.md](./SECURITY.md) - Security best practices
- [PREREQUISITES.md](./PREREQUISITES.md) - API key management
- [Perplexity Privacy Policy](https://www.perplexity.ai/privacy) - Third-party data handling

---

**Effective Date**: 2026-02-11
**Version**: 0.8.0
**Last Updated**: 2026-02-11
