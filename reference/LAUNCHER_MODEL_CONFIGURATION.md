# Launcher Model Configuration

## Default Model Behavior

The amplihack launcher uses `sonnet[1m]` as the default model when launching Claude Code. This provides the optimal balance of performance, extended context window, and cost-effectiveness for most development tasks.

## Model Selection Priority

When the launcher determines which model to use, it follows this strict priority order:

1. **Azure Proxy Configuration** (highest priority)
   - When `--with-proxy-config` is specified with an Azure configuration file
   - Azure proxy settings completely override all other model specifications
   - The proxy determines the model based on its own configuration

2. **--model Flag**
   - Explicitly specified model via command-line flag
   - Example: `amplihack launch --model opus`
   - Overrides environment variable and hardcoded default

3. **AMPLIHACK_DEFAULT_MODEL Environment Variable**
   - Set in your shell environment
   - Example: `export AMPLIHACK_DEFAULT_MODEL=opus`
   - Overrides hardcoded default but not command-line flag

4. **Hardcoded Default** (lowest priority)
   - `sonnet[1m]` is used when no other configuration is present
   - Provides sensible default for most development work

## Usage Examples

### Using the Default Model

```bash
# Uses sonnet[1m] by default
amplihack launch
```

### Override with Command-Line Flag

```bash
# Use Opus model with extended context
amplihack launch --model opus[1m]

# Use Haiku for quick tasks
amplihack launch --model haiku

# Use standard Sonnet without extended context
amplihack launch --model sonnet
```

### Override with Environment Variable

```bash
# Set default model for all amplihack sessions
export AMPLIHACK_DEFAULT_MODEL=opus[1m]

# Now all launches use Opus by default
amplihack launch

# Still can override with flag
amplihack launch --model haiku
```

### Azure Proxy Takes Precedence

```bash
# Azure proxy configuration determines the model
amplihack launch --with-proxy-config ./azure.env --model opus

# In this case:
# - Azure proxy configuration is used
# - The --model flag is effectively ignored
# - Model is determined by Azure deployment configuration
```

## Available Models

| Model        | Context     | Best For                            |
| ------------ | ----------- | ----------------------------------- |
| `sonnet[1m]` | 1M tokens   | Default - most development tasks    |
| `sonnet`     | 200K tokens | Standard development work           |
| `opus[1m]`   | 1M tokens   | Complex architecture, critical code |
| `opus`       | 200K tokens | High-quality reasoning              |
| `haiku`      | 200K tokens | Quick tasks, simple operations      |

## Configuration Persistence

Model selection is **per-session only**. Each time you launch amplihack, the priority hierarchy is evaluated fresh:

- Command-line flags apply to that session only
- Environment variables persist across shell sessions (until unset)
- Hardcoded default is always available as fallback

**To permanently change your default model**, set the environment variable in your shell profile:

```bash
# Add to ~/.bashrc or ~/.zshrc
export AMPLIHACK_DEFAULT_MODEL=opus[1m]

# Reload shell configuration
source ~/.bashrc  # or source ~/.zshrc
```

## Checking Active Model

The active model is displayed in the statusline at the bottom of Claude Code:

```
~/src/amplihack (main → origin) Sonnet[1m] 🎫 234K 💰$1.23 ⏱12m
```

For more information about the statusline, see [STATUSLINE.md](./STATUSLINE.md).

## Troubleshooting

### Model flag not working with Azure proxy

**Problem**: You specify `--model opus` but Azure model is used instead.

**Solution**: This is expected behavior. Azure proxy configuration always takes precedence over model flags. To use a different model with Azure, modify your Azure proxy configuration file.

### Environment variable not being respected

**Problem**: You set `AMPLIHACK_DEFAULT_MODEL` but the default `sonnet[1m]` is still used.

**Solution**:

1. Verify the variable is exported: `echo $AMPLIHACK_DEFAULT_MODEL`
2. Check for command-line flags that override it
3. Ensure you've reloaded your shell after setting it

### Invalid model name

**Problem**: Error when specifying an invalid model name.

**Solution**: Use one of the valid model names listed in the "Available Models" table above. Model names are case-sensitive.

## Related Documentation

- [Proxy Configuration Guide](../PROXY_CONFIG_GUIDE.md) - Azure OpenAI proxy setup
- [Statusline Reference](./STATUSLINE.md) - Session information display
- [Auto Mode](../AUTO_MODE.md) - Autonomous mode with model selection
