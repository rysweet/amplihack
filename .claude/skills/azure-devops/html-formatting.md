# HTML Formatting Guide

Azure DevOps work items use HTML for descriptions and comments. The format_html tool converts markdown to proper HTML.

## Why HTML?

Azure DevOps displays work item descriptions as HTML. Plain text looks unprofessional and lacks formatting.

## Auto-Formatting

The create_work_item tool automatically converts markdown to HTML:

```bash
python .claude/scenarios/az-devops-tools/create_work_item.py \
  --type "User Story" \
  --title "My Story" \
  --description "# Title

This is **bold** and this is *italic*.

- List item 1
- List item 2"
```

Disable with `--no-format`:

```bash
python .claude/scenarios/az-devops-tools/create_work_item.py \
  --type Task \
  --title "My Task" \
  --description "<p>Already HTML</p>" \
  --no-format
```

## Standalone Formatter

Convert markdown files to HTML:

```bash
# From file
python .claude/scenarios/az-devops-tools/format_html.py story.md

# From stdin
echo "# Title" | python .claude/scenarios/az-devops-tools/format_html.py

# Save to file
python .claude/scenarios/az-devops-tools/format_html.py story.md -o output.html
```

## Supported Markdown

### Headings
**Markdown:** `# H1`, `## H2`, `### H3`
**HTML:** `<h1>H1</h1>`, `<h2>H2</h2>`, `<h3>H3</h3>`

### Bold and Italic
**Markdown:** `**bold**`, `*italic*`, `***bold italic***`
**HTML:** `<strong>bold</strong>`, `<em>italic</em>`, `<strong><em>bold italic</em></strong>`

### Lists
**Markdown:**
```markdown
- Item 1
- Item 2

1. First
2. Second
```

**HTML:**
```html
<ul>
  <li>Item 1</li>
  <li>Item 2</li>
</ul>

<ol>
  <li>First</li>
  <li>Second</li>
</ol>
```

### Code
**Markdown:** `` `inline code` ``
**HTML:** `<code>inline code</code>`

**Markdown:**
````markdown
```python
def hello():
    print("Hello!")
```
````

**HTML:**
```html
<pre><code class="language-python">def hello():
    print("Hello!")
</code></pre>
```

### Links
**Markdown:** `[Link text](https://example.com)`
**HTML:** `<a href="https://example.com">Link text</a>`

## Programmatic Usage

```python
from .claude.scenarios.az_devops_tools.format_html import markdown_to_html

markdown = """
# User Story

As a user, I want to **log in** so I can access my account.

## Acceptance Criteria

- User can enter credentials
- System validates login
- Error shown on failure
"""

html = markdown_to_html(markdown)
print(html)
```

## Best Practices

1. **Use markdown** - Easier to write and maintain
2. **Preview in Azure DevOps** - Check formatting after creation
3. **Keep it simple** - Avoid complex HTML
4. **Use code blocks** - For code snippets and logs
5. **Structure with headings** - Makes descriptions scannable

## Limitations

The formatter supports common markdown only:

- No tables
- No images
- No nested lists
- No HTML entities

For advanced formatting, use raw HTML with `--no-format`.

## See Also

- [@work-items.md] - Work item operations
- [Markdown Guide](https://www.markdownguide.org/)
