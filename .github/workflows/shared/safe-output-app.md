# Safe Output Application Guidelines

## What are Safe Outputs?

Safe outputs are the ONLY mechanism for workflows to make changes in strict mode. They provide:

- **Controlled write operations**: Issues, PRs, comments, labels
- **Rate limiting**: Max operations per run
- **Expiration**: Auto-close stale items
- **Grouping**: Prevent issue tracker flooding

## Common Safe Output Patterns

### Creating Issues

```yaml
safe-outputs:
  create-issue:
    max: 10
    expires: 2d
    title-prefix: "[automation] "
    labels: [automated, needs-review]
```

### Creating Pull Requests

```yaml
safe-outputs:
  create-pull-request:
    max: 1
    title-prefix: "[automation] "
    labels: [automated]
    reviewers: [copilot]
```

### Adding Comments

```yaml
safe-outputs:
  add-comment:
    max: 5
    target: "*"
```

### Adding Labels

```yaml
safe-outputs:
  add-labels:
    max: 1
    allowed: [bug, feature, enhancement]
```

## Best Practices

1. **Set appropriate limits**: Don't flood the issue tracker
2. **Use expiration**: Clean up stale automation artifacts
3. **Group related items**: Use grouping to consolidate when possible
4. **Prefix titles**: Make automation-generated items easily identifiable
5. **Apply labels**: Help with filtering and organization
