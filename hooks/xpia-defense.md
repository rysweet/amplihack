---
hook:
  name: xpia-defense
  description: Cross-prompt injection attack defense
  events: ["prompt:submit", "tool:before"]
---

# XPIA Defense Hook

Detects and blocks potential prompt injection attacks in user input and tool outputs.

## Threat Categories

| Category | Pattern | Action |
|----------|---------|--------|
| System Override | "Ignore previous", "New instructions" | Block |
| Role Manipulation | "You are now", "Act as" | Block |
| Command Injection | Shell metacharacters in prompts | Warn |
| Data Exfiltration | Requests for system prompts | Block |

## Threat Tiers

### Tier 1: Critical (Block)
- Direct system prompt override attempts
- Encoded/obfuscated injection attempts
- Multi-language injection attempts

### Tier 2: Suspicious (Warn)
- Unusual character sequences
- Context-switching patterns
- Boundary-testing inputs

### Tier 3: Development (Allow with logging)
- Legitimate prompt engineering discussions
- Security research contexts

## Operating Modes
- **Standard**: Block critical, warn suspicious
- **Strict**: Block critical + suspicious
- **Learning**: Log all, block none (analysis mode)

## Performance Target
- Detection latency: <100ms
- False positive rate: <5%
- Detection rate: >95%
