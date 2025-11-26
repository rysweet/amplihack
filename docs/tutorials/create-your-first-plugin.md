# Create Your First Plugin

**Learn to create an amplihack plugin in 15 minutes.**

## What You'll Build

By the end of this tutorial, ye'll have:

- A working plugin that greets users
- Understanding of the plugin lifecycle
- Knowledge to create yer own plugins

## Prerequisites

- amplihack installed and working
- Basic Python knowledge
- Text editor

## Step 1: Create Plugin Directory

First, create a directory for yer plugins if it doesn't exist:

```bash
mkdir -p plugins
cd plugins
```

**Expected output:**

```bash
# Directory created (no output if successful)
```

## Step 2: Create Your First Plugin

Create a file named `hello.py`:

```python
# plugins/hello.py
from amplihack.plugins import PluginBase, register_plugin

@register_plugin
class HelloPlugin(PluginBase):
    """Simple greeting plugin."""

    name = "hello"
    description = "Print a friendly greeting"

    def execute(self, args):
        """Execute the hello command."""
        print("Hello, World!")
        return 0
```

**What this does:**

1. **Import required classes**: `PluginBase` and `register_plugin`
2. **Use decorator**: `@register_plugin` automatically registers the plugin
3. **Inherit from PluginBase**: Required for all plugins
4. **Set name**: Used in CLI commands (`amplihack hello`)
5. **Set description**: Shown in help text
6. **Implement execute()**: Main plugin logic, returns exit code

## Step 3: Test Your Plugin

Run yer plugin:

```bash
amplihack hello
```

**Expected output:**

```
Hello, World!
```

**Success!** Ye've created yer first plugin.

## Step 4: Add Arguments

Let's make it more interesting by adding a name argument.

Update `hello.py`:

```python
# plugins/hello.py
from amplihack.plugins import PluginBase, register_plugin

@register_plugin
class HelloPlugin(PluginBase):
    """Simple greeting plugin."""

    name = "hello"
    description = "Print a friendly greeting"

    def execute(self, args):
        """Execute the hello command."""
        # Get name from arguments, default to "World"
        name = getattr(args, 'name', 'World')
        print(f"Hello, {name}!")
        return 0
```

Test with an argument:

```bash
amplihack hello --name Claude
```

**Expected output:**

```
Hello, Claude!
```

## Step 5: Add Error Handling

Good plugins handle errors gracefully. Let's add validation.

Update `hello.py`:

```python
# plugins/hello.py
from amplihack.plugins import PluginBase, register_plugin

@register_plugin
class HelloPlugin(PluginBase):
    """Simple greeting plugin."""

    name = "hello"
    description = "Print a friendly greeting"

    def execute(self, args):
        """Execute the hello command."""
        try:
            # Get name from arguments
            name = getattr(args, 'name', 'World')

            # Validate name
            if not name.strip():
                print("Error: Name cannot be empty")
                return 1

            # Greet
            print(f"Hello, {name}!")
            return 0

        except Exception as e:
            print(f"Error: {e}")
            return 1
```

Test error handling:

```bash
amplihack hello --name ""
```

**Expected output:**

```
Error: Name cannot be empty
```

## Step 6: Add Multiple Greeting Styles

Let's make it fancier with different greeting styles.

Final version of `hello.py`:

```python
# plugins/hello.py
from amplihack.plugins import PluginBase, register_plugin

@register_plugin
class HelloPlugin(PluginBase):
    """Simple greeting plugin with multiple styles."""

    name = "hello"
    description = "Print a friendly greeting"

    def execute(self, args):
        """Execute the hello command."""
        try:
            # Get arguments
            name = getattr(args, 'name', 'World')
            style = getattr(args, 'style', 'normal')

            # Validate name
            if not name.strip():
                print("Error: Name cannot be empty")
                return 1

            # Greet based on style
            if style == 'pirate':
                print(f"Ahoy, {name}! Ye scurvy dog!")
            elif style == 'formal':
                print(f"Good day, {name}. How do you do?")
            elif style == 'excited':
                print(f"HELLO, {name.upper()}!!!")
            else:
                print(f"Hello, {name}!")

            return 0

        except Exception as e:
            print(f"Error: {e}")
            return 1
```

Test different styles:

```bash
amplihack hello --name Claude --style pirate
amplihack hello --name Claude --style formal
amplihack hello --name Claude --style excited
```

**Expected output:**

```
Ahoy, Claude! Ye scurvy dog!
Good day, Claude. How do you do?
HELLO, CLAUDE!!!
```

## What You Learned

Congratulations! Ye now know how to:

1. ✓ Create a plugin file
2. ✓ Use the `@register_plugin` decorator
3. ✓ Implement the `execute()` method
4. ✓ Access command-line arguments
5. ✓ Handle errors gracefully
6. ✓ Return proper exit codes
7. ✓ Test yer plugin

## Next Steps

Now that ye've created yer first plugin, ye can:

- **Read the full guide**: [Plugin System README](../../src/amplihack/plugins/README.md)
- **Explore the API**: [Plugin API Reference](../reference/plugin-api.md)
- **See more examples**: Check `plugins/` directory for real-world examples
- **Create something useful**: Build a plugin for yer workflow

## Common Issues

### Plugin Not Found

If `amplihack hello` says "command not found":

1. Check file is in `plugins/` directory
2. Verify `@register_plugin` decorator is present
3. Ensure plugin inherits from `PluginBase`
4. Check `name` attribute matches command

### Import Error

If ye get `ModuleNotFoundError`:

1. Make sure amplihack is installed: `pip install amplihack`
2. Check import statement: `from amplihack.plugins import ...`
3. Verify ye're in the correct directory

### Execute Method Not Called

If plugin registers but doesn't run:

1. Check method signature: `def execute(self, args):`
2. Ensure method returns an integer
3. Verify no exceptions during import

## Complete Example

Here's the complete, working plugin:

```python
# plugins/hello.py
"""
Hello plugin - demonstrates basic plugin creation.

This plugin shows:
- Plugin registration with @register_plugin
- Argument handling with getattr()
- Error handling with try/except
- Multiple execution paths (styles)
- Proper exit codes
"""
from amplihack.plugins import PluginBase, register_plugin

@register_plugin
class HelloPlugin(PluginBase):
    """Simple greeting plugin with multiple styles."""

    name = "hello"
    description = "Print a friendly greeting"

    def execute(self, args):
        """
        Execute the hello command.

        Args:
            args: Namespace containing:
                - name (str): Name to greet (default: "World")
                - style (str): Greeting style (default: "normal")

        Returns:
            int: Exit code (0 success, 1 error)
        """
        try:
            # Get arguments with defaults
            name = getattr(args, 'name', 'World')
            style = getattr(args, 'style', 'normal')

            # Validate name
            if not name.strip():
                print("Error: Name cannot be empty")
                return 1

            # Greet based on style
            if style == 'pirate':
                print(f"Ahoy, {name}! Ye scurvy dog!")
            elif style == 'formal':
                print(f"Good day, {name}. How do you do?")
            elif style == 'excited':
                print(f"HELLO, {name.upper()}!!!")
            else:
                print(f"Hello, {name}!")

            return 0

        except Exception as e:
            print(f"Error: {e}")
            return 1
```

## Related Tutorials

- [Create a File Processing Plugin](./file-processing-plugin.md) - Learn to work with files
- [Create a Plugin with Configuration](./configurable-plugin.md) - Add configuration files
- [Testing Your Plugins](./testing-plugins.md) - Write tests for plugins

---

**Time to complete**: 15 minutes
**Difficulty**: Beginner
**Last updated**: 2025-11-26
