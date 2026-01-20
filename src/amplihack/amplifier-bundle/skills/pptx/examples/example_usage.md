# PPTX Skill Usage Examples

This document provides practical examples of using the PPTX skill in Claude Code conversations. The PPTX skill enables comprehensive PowerPoint manipulation including creation, editing, and analysis.

## Table of Contents

1. [Creating Presentations from Scratch](#creating-presentations-from-scratch)
2. [Using Templates](#using-templates)
3. [Editing Existing Presentations](#editing-existing-presentations)
4. [Analyzing Presentations](#analyzing-presentations)
5. [Design and Styling](#design-and-styling)
6. [Charts and Data](#charts-and-data)
7. [Template Workflows](#template-workflows)
8. [Visual Validation](#visual-validation)
9. [Conversion and Export](#conversion-and-export)
10. [Advanced Techniques](#advanced-techniques)

---

## 1. Creating Presentations from Scratch

### Example 1.1: Simple Presentation with Custom Design

**User**: Create a 5-slide presentation about renewable energy with a modern green color palette

**Claude**:

```
I'll create a presentation using the Sage & Terracotta palette which complements the renewable energy theme:
- Sage (#87A96B) - main color
- Terracotta (#E07A5F) - accent
- Cream (#F4F1DE) - background
- Charcoal (#2C2C2C) - text

Slides:
1. Title: "The Future of Renewable Energy"
2. Overview: Types of renewable energy sources
3. Benefits: Environmental and economic advantages
4. Challenges: Current obstacles and solutions
5. Conclusion: Path forward

[Creates HTML slides with custom styling, converts to PPTX using html2pptx]
```

### Example 1.2: Data-Driven Presentation with Charts

**User**: Create a quarterly sales presentation with charts showing revenue trends

**Claude**:

```
I'll create a presentation with two-column layouts for charts:
- Classic Blue palette for professional appearance
- Charts in one column, key insights in the other
- Data visualization with horizontal bar charts

[Generates slides with placeholder divs for charts, then uses PptxGenJS to add actual chart data]
```

---

## 2. Using Templates

### Example 2.1: Create Presentation from Corporate Template

**User**: Use this template.pptx to create a 10-slide investor pitch

**Claude**:

```
Workflow:
1. Extract template text and create thumbnail grid
2. Analyze template inventory (73 slides with various layouts)
3. Select appropriate slides for pitch structure:
   - Slide 0: Title/Cover
   - Slide 34: Title and body (for overview)
   - Slide 45: Two-column with image placeholder
   - Slide 50: Quote layout
   - Slide 54: Closing slide

4. Rearrange slides: python scripts/rearrange.py template.pptx working.pptx 0,34,34,45,45,45,50,34,34,54
5. Extract text inventory
6. Generate replacement text preserving formatting
7. Apply replacements with replace.py

[Executes template workflow with appropriate content]
```

### Example 2.2: Duplicate and Customize Template Slides

**User**: Take slides 5-8 from template.pptx and create 12 slides by duplicating the pattern

**Claude**:

```
Using rearrange.py to duplicate and reorder:

python scripts/rearrange.py template.pptx output.pptx 5,6,7,8,5,6,7,8,5,6,7,8

This creates 12 slides by repeating the 5-8 pattern three times.

[Then applies custom text replacement for each duplicated set]
```

---

## 3. Editing Existing Presentations

### Example 3.1: Update Speaker Notes

**User**: Add speaker notes to slides 2, 3, and 5 in presentation.pptx

**Claude**:

```
Using OOXML workflow:
1. Unpack: python ooxml/scripts/unpack.py presentation.pptx workspace/
2. Edit notesSlides/notesSlide2.xml, notesSlide3.xml, notesSlide5.xml
3. Add <a:t> elements with speaker note content
4. Validate: python ooxml/scripts/validate.py workspace/ --original presentation.pptx
5. Pack: python ooxml/scripts/pack.py workspace/ presentation-with-notes.pptx

[Performs XML editing with proper OOXML structure]
```

### Example 3.2: Modify Slide Layouts

**User**: Change slide 4 from single-column to two-column layout

**Claude**:

```
OOXML approach:
1. Unpack presentation
2. Read ppt/slides/slide4.xml
3. Modify shape positions and dimensions:
   - Split content into two <p:sp> elements
   - Adjust <a:off> (position) and <a:ext> (size) for each shape
4. Validate changes
5. Repack presentation

[Applies precise XML modifications]
```

---

## 4. Analyzing Presentations

### Example 4.1: Extract Text Content

**User**: Extract all text from this presentation to markdown

**Claude**:

```bash
python -m markitdown presentation.pptx > content.md
```

Result: Clean markdown with slide structure preserved, perfect for analysis or documentation.

### Example 4.2: Analyze Design and Typography

**User**: What fonts and colors are used in this template?

**Claude**:

```
I'll analyze the design:
1. Unpack presentation
2. Read ppt/theme/theme1.xml for color scheme
3. Examine ppt/slides/slide1.xml for actual font usage
4. Use grep to find all color and font references

Findings:
- Primary font: Montserrat
- Body font: Open Sans
- Color scheme:
  - Dark Blue (#1C2833) - headers
  - Gray (#708090) - body text
  - Accent: Coral (#FF6B6B)
```

---

## 5. Design and Styling

### Example 5.1: Choose Appropriate Color Palette

**User**: Create a presentation for a tech startup - suggest a color palette

**Claude**:

```
For a tech startup, I recommend the "Deep Purple & Emerald" palette:
- Purple (#B165FB) - innovation and creativity
- Dark Blue (#181B24) - professional and tech-focused
- Emerald (#40695B) - growth and success
- White (#FFFFFF) - clean and modern

This palette conveys: innovation, professionalism, and forward-thinking.

Alternative: "Vibrant Orange" (#F96D00, #F2F2F2, #222831) for more energy.

[Creates presentation with selected palette]
```

### Example 5.2: Apply Visual Hierarchy

**User**: Make the titles really stand out in this presentation

**Claude**:

```
I'll apply strong visual hierarchy:
- Title slides: 72pt bold headers with 11pt body (extreme size contrast)
- Section headers: All-caps with wide letter spacing
- Body text: 14pt regular weight
- Accent elements: Thick 5pt underlines beneath headers
- Color contrast: Dark text on light backgrounds (WCAG AA compliant)

[Implements hierarchy in HTML templates]
```

---

## 6. Charts and Data

### Example 6.1: Create Presentation with Multiple Chart Types

**User**: Create slides with bar chart, line chart, and pie chart showing sales data

**Claude**:

```
Using two-column layouts (PREFERRED for charts):
- Header spanning full width
- Left column: Key insights (40% width)
- Right column: Chart (60% width)

Chart styling:
- Monochrome with single accent color
- Minimal gridlines
- Data labels on elements
- No legends (direct labeling)

[Creates placeholder divs in HTML, then adds charts with PptxGenJS API]
```

### Example 6.2: Data Visualization Best Practices

**User**: Show quarterly metrics in an impactful way

**Claude**:

```
I'll use oversized numbers for key metrics:
- 125pt font size for main numbers
- Small 18pt labels underneath
- Horizontal bar charts for comparisons
- Color-coded performance indicators (green/red)
- Full-slide layout for maximum impact

[Implements data visualization principles]
```

---

## 7. Template Workflows

### Example 7.1: Complete Template-Based Workflow

**User**: Create a project status report using corporate-template.pptx

**Claude**:

```
Complete workflow:

Step 1: Extract and analyze
  python -m markitdown corporate-template.pptx > template-content.md
  python scripts/thumbnail.py corporate-template.pptx

Step 2: Create inventory
  [Analyzes 73 slides, identifies:
   - Slide 0: Title
   - Slide 12: Status overview layout
   - Slide 25: Milestone timeline
   - Slide 40: Risk assessment
   - Slide 68: Next steps]

Step 3: Rearrange
  python scripts/rearrange.py corporate-template.pptx working.pptx 0,12,25,25,40,68

Step 4: Extract inventory
  python scripts/inventory.py working.pptx inventory.json

Step 5: Generate replacement text
  [Creates replacement-text.json with:
   - Proper paragraph formatting
   - Bold titles
   - Bullet lists (bullet: true, level: 0)
   - Centered headers
   - Theme colors]

Step 6: Apply replacements
  python scripts/replace.py working.pptx replacement-text.json final.pptx

[Produces final presentation with consistent branding]
```

### Example 7.2: Handle Template with Image Placeholders

**User**: Use template slide 15 which has image placeholders

**Claude**:

```
Slide 15 has 3 image placeholder shapes.

Approach:
1. Use rearrange.py to duplicate slide 15
2. Extract inventory showing OBJECT placeholder types
3. In replacement JSON:
   - Keep image placeholder shapes empty (no paragraphs field)
   - They'll be cleared but structure preserved
   - Manually insert images after using python-pptx or OOXML

Note: Template workflow focuses on text replacement.
For images, post-process with python-pptx or manual insertion.
```

---

## 8. Visual Validation

### Example 8.1: Generate and Review Thumbnails

**User**: Create thumbnails of this 50-slide presentation for quick review

**Claude**:

```bash
python scripts/thumbnail.py presentation.pptx review --cols 5
```

Output:

- review-1.jpg: Slides 0-29 (5×6 grid)
- review-2.jpg: Slides 30-49 (4×5 grid)

Review thumbnails for:

- Text cutoff at slide edges
- Overlap between elements
- Positioning issues
- Contrast problems
- Consistent styling

### Example 8.2: Fix Visual Issues After Validation

**User**: The thumbnail shows text cutoff on slides 3 and 7

**Claude**:

```
I'll fix the layout issues:

Slide 3: Header bar cutting off title
- Increase top margin from 0.5" to 0.8"
- Reduce title font size from 44pt to 36pt

Slide 7: Bullet list too long
- Split into two slides
- Or reduce font size from 18pt to 16pt
- Increase line spacing

[Regenerates HTML and converts to PPTX]
[Creates new thumbnails to verify fixes]
```

---

## 9. Conversion and Export

### Example 9.1: Convert Presentation to PDF

**User**: Convert presentation.pptx to PDF

**Claude**:

```bash
soffice --headless --convert-to pdf presentation.pptx
```

Result: presentation.pdf with all slides preserved

### Example 9.2: Convert Slides to Individual Images

**User**: Export each slide as a high-resolution image

**Claude**:

```bash
# First convert to PDF
soffice --headless --convert-to pdf presentation.pptx

# Then convert PDF pages to images (150 DPI)
pdftoppm -jpeg -r 150 presentation.pdf slide
```

Result: slide-1.jpg, slide-2.jpg, slide-3.jpg, etc.

---

## 10. Advanced Techniques

### Example 10.1: Combine Multiple Templates

**User**: Use title slide from template-A.pptx and content slides from template-B.pptx

**Claude**:

```
Multi-template workflow:

1. Extract slide 0 from template-A:
   python scripts/rearrange.py template-A.pptx title.pptx 0

2. Extract slides 5,6,7 from template-B:
   python scripts/rearrange.py template-B.pptx content.pptx 5,6,7

3. Manually combine using OOXML or python-pptx:
   - Unpack both presentations
   - Copy slide XML files from content/ to title/
   - Update presentation.xml with new slide references
   - Pack combined presentation

[Performs OOXML merging]
```

### Example 10.2: Batch Process Multiple Presentations

**User**: Apply the same text replacements to 10 different presentations

**Claude**:

```bash
for file in *.pptx; do
  echo "Processing $file"
  python scripts/inventory.py "$file" "inventory-${file}.json"
  # Create custom replacement JSON for each
  python scripts/replace.py "$file" "replacement-${file}.json" "updated-${file}"
done
```

Enables bulk updates while preserving each presentation's unique formatting.

### Example 10.3: Extract and Analyze Slide Layouts

**User**: Show me all unique slide layouts in this template

**Claude**:

```
Analysis workflow:
1. Unpack template
2. Read ppt/presentation.xml for layout references
3. List all slideLayouts in ppt/slideLayouts/
4. For each layout, extract:
   - Layout name
   - Placeholder types and positions
   - Master slide reference

Result:
- Title Slide (1 title, 1 subtitle)
- Title and Content (1 title, 1 body)
- Two Content (1 title, 2 content areas)
- Comparison (1 title, 2 columns)
- Title Only (1 title, full blank area)
- Blank (no placeholders)
- Content with Caption (1 body, 1 caption)
- Picture with Caption (1 picture, 1 caption)
- Section Header (1 title, 1 text)

[Creates layout reference document]
```

---

## Tips and Best Practices

### Design Tips

1. **Content-First Design**: Analyze subject matter before choosing colors
2. **Limit Palette**: Use 3-5 colors maximum for consistency
3. **Web-Safe Fonts**: Stick to Arial, Helvetica, Georgia, Times New Roman, etc.
4. **Contrast**: Ensure WCAG AA compliance (4.5:1 for body text)
5. **Hierarchy**: Use size, weight, and color to guide attention

### Layout Tips

1. **Two-Column for Charts**: Never stack charts below text vertically
2. **White Space**: Don't fill every inch - negative space improves readability
3. **Alignment**: Use consistent margins and alignment patterns
4. **Grid Systems**: Consider 3×3 or 4×4 modular grids for complex layouts

### Template Workflow Tips

1. **Always Create Thumbnails**: Visual reference prevents errors
2. **Verify Indices**: Slides are 0-indexed (first slide = 0)
3. **Check Inventory**: Confirm shapes exist before referencing in replacement JSON
4. **Preserve Formatting**: Copy paragraph properties from inventory
5. **Test Small**: Try workflow on 2-3 slides before full presentation

### Validation Tips

1. **Immediate Validation**: Validate after every OOXML edit
2. **Visual Inspection**: Always review thumbnails after generation
3. **Check Overflow**: Watch for text overflow warnings from replace.py
4. **Test on Device**: Preview on actual presentation device if possible

---

## Common Patterns

### Pattern 1: Professional Corporate Presentation

```
Structure: Title → Agenda → 3-5 Content Slides → Conclusion
Colors: Classic Blue or Charcoal & Red
Fonts: Arial or Helvetica
Layouts: Two-column for content, full-slide for data
```

### Pattern 2: Creative Pitch Deck

```
Structure: Hook → Problem → Solution → Product → Traction → Ask
Colors: Bold Red or Pink & Purple
Fonts: Mixed (Impact for headers, Arial for body)
Layouts: Full-bleed images, asymmetric columns
```

### Pattern 3: Data-Heavy Report

```
Structure: Executive Summary → Detailed Metrics → Analysis → Recommendations
Colors: Monochrome with single accent
Fonts: Monospace (Courier New) for numbers
Layouts: Charts in right column, insights in left
```

---

## Troubleshooting Common Issues

### Issue: Text Cutoff in Thumbnails

**Solution**: Increase margins in HTML, reduce font sizes, or split content across slides

### Issue: Template Slide Index Out of Range

**Solution**: Remember 0-indexing. Template with 73 slides has indices 0-72

### Issue: Shape Not Found in Inventory

**Solution**: Check shape names exactly match inventory.json. Shapes are "shape-0", "shape-1", etc.

### Issue: Overflow Warnings from replace.py

**Solution**: Shorten text, reduce font size, or choose shape with larger dimensions

### Issue: Formatting Lost After Replacement

**Solution**: Ensure replacement JSON includes all paragraph properties (bold, alignment, etc.)

---

## Additional Resources

- [SKILL.md](../SKILL.md) - Complete skill documentation
- [DEPENDENCIES.md](../DEPENDENCIES.md) - Installation guide
- [README.md](../README.md) - Integration overview
- [Anthropic PPTX Skill](https://github.com/anthropics/skills/tree/main/document-skills/pptx)

---

**Last Updated**: 2025-11-08
**Maintained By**: amplihack project
