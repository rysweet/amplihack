---
name: workiq-wsl
description: |
  Access Microsoft 365 data (emails, calendar, files) from WSL via the Windows
  Copilot CLI bridge. Routes queries through powershell.exe to the Windows-native
  Copilot CLI with WorkIQ plugin for M365 Graph API access.
version: 1.0.0
auto_activates:
  - "workiq"
  - "work iq"
  - "emails"
  - "calendar"
  - "meetings"
  - "m365"
  - "microsoft 365"
  - "outlook"
priority: 3
---

# WorkIQ WSL Bridge Skill

Access Microsoft 365 data — emails, calendar, files, Teams — from WSL2 by bridging
to the Windows-native Copilot CLI with the WorkIQ plugin installed.

## Purpose

WSL2 environments cannot natively run the WorkIQ MCP server because it depends on
Windows-native authentication (M365 SSO via browser). This skill solves that by
routing M365 queries through `powershell.exe` to the Windows Copilot CLI, which has
full access to the WorkIQ MCP server and Microsoft Graph API.

This means you can query your emails, check your calendar, search files, and read
Teams messages — all without leaving your WSL terminal session.

## Prerequisites

### 1. WSL2 with a Linux Distribution

You must be running inside WSL2 (not WSL1 or native Linux).

```bash
# Verify WSL2
grep -qi microsoft /proc/version && echo "WSL detected" || echo "Not WSL"
```

### 2. Windows-Native Copilot CLI

Install on the **Windows host** (not inside WSL):

```powershell
# From Windows Terminal or PowerShell
winget install GitHub.Copilot
```

Verify from WSL:

```bash
powershell.exe -NoProfile -Command "copilot --version" 2>&1
```

### 3. GitHub Authentication

Authenticate the Windows Copilot CLI:

```bash
powershell.exe -NoProfile -Command "copilot login" 2>&1
```

### 4. WorkIQ Plugin

Install the WorkIQ plugin in the Windows Copilot CLI:

```bash
powershell.exe -NoProfile -Command "copilot plugin install workiq" 2>&1
```

### 5. M365 Authentication

WorkIQ will prompt for Microsoft SSO on first use. A browser window opens on the
Windows host for sign-in. No extra setup needed — just approve the consent prompt.

## How It Works

```text
WSL Copilot CLI session
     │
     ▼
powershell.exe -NoProfile -Command "copilot -p '...' --allow-all-tools --silent --no-auto-update 2>&1"
     │
     ▼
Windows Copilot CLI (native)
     │
     ▼
WorkIQ MCP Server (npx @microsoft/workiq@latest mcp)
     │
     ▼
Microsoft Graph API → M365 (emails, calendar, files, Teams)
```

Each query spawns a `powershell.exe` process that invokes the Windows Copilot CLI
with a natural-language prompt. The `--allow-all-tools` flag grants the Copilot CLI
permission to call the WorkIQ MCP tool, which queries Microsoft Graph on your behalf.

Key flags:

- `--allow-all-tools` — Lets Copilot use WorkIQ without manual approval
- `--silent` — Suppresses interactive UI elements
- `--no-auto-update` — Prevents update checks that slow down execution
- `2>&1` — Captures both stdout and stderr from the Windows side

## Usage Examples

### Check Today's Meetings

```bash
powershell.exe -NoProfile -Command "copilot -p 'Use the workiq ask_work_iq tool to answer: What meetings do I have today?' --allow-all-tools --silent --no-auto-update 2>&1"
```

### Find Recent Emails from Someone

```bash
powershell.exe -NoProfile -Command "copilot -p 'Use the workiq ask_work_iq tool to find all emails from Dustin Duran. Show me the 5 most recent ones with their subject lines, dates sent, and a brief summary of each email.' --allow-all-tools --silent --no-auto-update 2>&1"
```

### Search for Files

```bash
powershell.exe -NoProfile -Command "copilot -p 'Use the workiq ask_work_iq tool to answer: Find my most recent PowerPoint files in OneDrive and SharePoint.' --allow-all-tools --silent --no-auto-update 2>&1"
```

### Get Email Summaries

```bash
powershell.exe -NoProfile -Command "copilot -p 'Use the workiq ask_work_iq tool to answer: Summarize the most important unread emails in my inbox from the last 24 hours.' --allow-all-tools --silent --no-auto-update 2>&1"
```

### Check This Week's Calendar

```bash
powershell.exe -NoProfile -Command "copilot -p 'Use the workiq ask_work_iq tool to answer: What does my calendar look like for the rest of this week? List all meetings with times and attendees.' --allow-all-tools --silent --no-auto-update 2>&1"
```

## Activation Instructions

This skill activates when the user mentions emails, calendar, meetings, M365,
Microsoft 365, Outlook, or WorkIQ in a WSL environment.

### Detection Logic

When activated, perform these checks in order:

1. **Detect WSL environment:**

   ```bash
   grep -qi microsoft /proc/version
   ```

   If not WSL, fall back to the standard `work-iq` skill (native MCP approach).

2. **Check Windows Copilot is available:**

   ```bash
   powershell.exe -NoProfile -Command "copilot --version" 2>&1
   ```

   If not found, guide user through installation (see Prerequisites §2).

3. **Check WorkIQ plugin is installed:**

   ```bash
   powershell.exe -NoProfile -Command "copilot plugin list" 2>&1 | grep -i workiq
   ```

   If not found, guide user through installation (see Prerequisites §4).

4. **Route the query:** Build the powershell.exe command with the user's natural-language
   question and execute it:

   ```bash
   powershell.exe -NoProfile -Command "copilot -p 'Use the workiq ask_work_iq tool to answer: <USER_QUERY>' --allow-all-tools --silent --no-auto-update 2>&1"
   ```

5. **Parse and present:** Extract the relevant answer from the Copilot CLI output
   and present it cleanly to the user.

### If Prerequisites Are Missing

Guide the user through setup:

```text
It looks like you're in WSL but the Windows Copilot CLI isn't set up for WorkIQ yet.

To set up M365 access from WSL:
1. Install Copilot CLI on Windows: winget install GitHub.Copilot
2. Authenticate: powershell.exe -NoProfile -Command "copilot login"
3. Install WorkIQ: powershell.exe -NoProfile -Command "copilot plugin install workiq"
4. Try your query again — WorkIQ will prompt for M365 sign-in on first use.
```

## Troubleshooting

| Problem                           | Cause                                          | Solution                                                                                                                |
| --------------------------------- | ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `copilot: command not found`      | Copilot CLI not installed on Windows host      | Install via `winget install GitHub.Copilot` from Windows Terminal                                                       |
| `powershell.exe: not found`       | Not running in WSL2 or WSL interop disabled    | Check `cat /proc/sys/fs/binfmt_misc/WSLInterop` exists                                                                  |
| WorkIQ timeout / no response      | M365 auth expired or never completed           | Run the query again — it will re-trigger browser auth                                                                   |
| PowerShell execution policy error | Restrictive execution policy                   | The `-NoProfile` flag avoids this; if persists, run `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` in PowerShell |
| Quote escaping issues             | Nested quotes between bash and PowerShell      | Use double quotes for the outer PowerShell command, single quotes for the inner Copilot prompt                          |
| Garbled output or ANSI codes      | Terminal encoding mismatch                     | Pipe output through `sed 's/\x1b\[[0-9;]*m//g'` to strip ANSI escape codes                                              |
| `GitHub auth required`            | Copilot CLI not authenticated                  | Run `powershell.exe -NoProfile -Command "copilot login"`                                                                |
| Slow responses (30s+)             | Normal — each query boots Copilot + WorkIQ MCP | Expected behavior; first query is slowest due to MCP server startup                                                     |

## Limitations

- **Write actions may require additional permissions** — WorkIQ can query M365 data and draft content. Sending emails, creating documents, and posting Teams messages may require additional M365 admin consent or Graph API permissions. If write operations fail, check your tenant's app permissions for the WorkIQ integration.
- **WSL-only** — Requires a Windows host with Copilot CLI installed. Does not work on native Linux or macOS.
- **No session persistence** — Each query spawns a new Copilot CLI process. There is no conversational memory between queries.
- **Startup latency** — Response time includes Copilot CLI startup + WorkIQ MCP server initialization (~10-30 seconds per query).
- **Output parsing** — Copilot CLI output includes status messages and formatting that must be filtered to extract the actual answer.
- **Auth scope** — Access is limited to what your M365 account has permissions for. Admin consent may be required for some tenants.
- **No streaming** — The full response is returned only after the Windows Copilot CLI process completes.

## Relationship to work-iq Skill

This skill complements the existing `work-iq` skill:

|                     | `work-iq`                    | `workiq-wsl`                                    |
| ------------------- | ---------------------------- | ----------------------------------------------- |
| **Environment**     | Any (native MCP)             | WSL2 only                                       |
| **How it connects** | Direct MCP server connection | Bridge via powershell.exe → Windows Copilot CLI |
| **Auth**            | Browser from current OS      | Browser on Windows host                         |
| **Latency**         | Low (direct MCP)             | Higher (~10-30s per query)                      |
| **Session**         | Persistent MCP connection    | New process per query                           |

Use `work-iq` when running natively. Use `workiq-wsl` when running inside WSL2 and
the native MCP approach is unavailable.

---

**Version:** 1.0.0 | **Updated:** 2025-07-14
