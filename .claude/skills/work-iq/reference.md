# Work IQ Technical Reference

Complete technical documentation for Microsoft Work IQ MCP server integration.

## Installation Methods

### Method 1: NPX (Recommended)

Run on-demand without installation:

```bash
npx -y @microsoft/workiq mcp
```

### Method 2: Global Install

```bash
npm install -g @microsoft/workiq
workiq version
```

### Method 3: Via MCP Manager

Using amplihack's mcp-manager skill:

```bash
cd .claude/scenarios
python3 -m mcp-manager.cli add workiq npx -- -y @microsoft/workiq mcp
```

## MCP Configuration

### Basic Configuration

Add to `.mcp.json`:

```json
{
  "mcpServers": {
    "workiq": {
      "command": "npx",
      "args": ["-y", "@microsoft/workiq", "mcp"]
    }
  }
}
```

### With Specific Tenant

```json
{
  "mcpServers": {
    "workiq": {
      "command": "npx",
      "args": ["-y", "@microsoft/workiq", "mcp"],
      "env": {
        "WORKIQ_TENANT_ID": "your-tenant-id"
      }
    }
  }
}
```

### VS Code Integration

Add to VS Code MCP settings:

```json
{
  "mcp.servers": {
    "workiq": {
      "command": "npx",
      "args": ["-y", "@microsoft/workiq", "mcp"]
    }
  }
}
```

## Authentication

### OAuth Flow

1. **First Query** - Triggers authentication
2. **Browser Opens** - Sign in to Microsoft 365
3. **Grant Permissions** - Accept requested permissions
4. **Token Cached** - Subsequent queries use cached credentials

### Admin Consent

Enterprise deployments may require tenant administrator consent:

1. **User Attempts Access** - Consent dialog appears
2. **Admin Reviews** - Evaluates permission request
3. **Consent Granted** - Admin approves via Entra admin center
4. **Access Enabled** - All users can authenticate

**Admin Consent URL:**

```
https://entra.microsoft.com/ → Enterprise applications → WorkIQ → Permissions → Grant admin consent
```

### Required Permissions

| Permission                | Type      | Purpose                |
| ------------------------- | --------- | ---------------------- |
| `Mail.Read`               | Delegated | Read email messages    |
| `Calendars.Read`          | Delegated | Access calendar events |
| `ChannelMessage.Read.All` | Delegated | Read Teams messages    |
| `Files.Read.All`          | Delegated | Search documents       |
| `People.Read`             | Delegated | Find people info       |

### Clear Credentials

```bash
# Remove cached tokens - platform specific locations:
# Windows: %LOCALAPPDATA%\Microsoft\WorkIQ
# macOS: ~/Library/Application Support/Microsoft/WorkIQ
# Linux: ~/.config/Microsoft/WorkIQ
```

## CLI Command Reference

### workiq accept-eula

Accept the End User License Agreement. **Required before first use.**

```bash
workiq accept-eula
# or
npx @microsoft/workiq accept-eula
```

### workiq ask

Query M365 data interactively or with a specific question.

```bash
# Interactive mode
workiq ask

# Direct question
workiq ask -q "What meetings do I have tomorrow?"

# Specific tenant
workiq ask -t "your-tenant-id" -q "Show my emails"
```

### workiq mcp

Start MCP stdio server for agent communication.

```bash
workiq mcp
# Runs as daemon, invoked by MCP runtime
```

### workiq version

Display version information.

```bash
workiq version
```

## Query Patterns

### Date Ranges

| Syntax       | Interpretation   |
| ------------ | ---------------- |
| "today"      | Current day      |
| "yesterday"  | Previous day     |
| "this week"  | Current week     |
| "last week"  | Previous 7 days  |
| "last month" | Previous 30 days |

### Query Types

| Data Type | Example Query                                    |
| --------- | ------------------------------------------------ |
| Email     | "What did John say about the proposal?"          |
| Calendar  | "What's on my calendar tomorrow?"                |
| Teams     | "Messages in Engineering channel about deadline" |
| Documents | "Find my recent PowerPoint presentations"        |
| People    | "Who is working on Project Alpha?"               |

## Troubleshooting

### EULA Not Accepted

```
Error: EULA not accepted
```

**Solution:**

```bash
npx @microsoft/workiq accept-eula
```

### Authentication Failed

```
Error: Authentication failed
```

**Solutions:**

1. Clear cached credentials (see locations above)
2. Verify M365 account is active
3. Check network connectivity
4. Try re-authenticating

### Admin Consent Required

```
Error: Admin consent required for this application
```

**Solutions:**

1. Contact M365 tenant administrator
2. Request application consent
3. Admin grants via Entra admin center

### WSL Browser Issues

```
Error: Unable to open browser for authentication
```

**Solution:**

```bash
sudo apt install xdg-utils
sudo apt install wslu
```

### Rate Limiting

```
Error: Rate limit exceeded
```

**Solution:**

- Wait for cooldown period (usually 60 seconds)
- Reduce query frequency
- Use more specific queries

## Security Considerations

### Data Access

- Queries scoped to YOUR M365 account
- Respects M365 permissions
- No data sent to third parties (except Microsoft)

### Token Storage

- Platform-standard secure storage:
  - Windows: Credential Manager
  - macOS: Keychain
  - Linux: Secret Service API

### Best Practices

- Review permissions before granting consent
- Use least-privilege principle
- Revoke access when no longer needed
- Regular access reviews for enterprise

---

**Last Updated:** 2026-01-23
