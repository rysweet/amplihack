---
skill:
  name: pptx
  description: PowerPoint operations - slide creation and manipulation
---

# PowerPoint Operations

## Library: python-pptx

```python
from pptx import Presentation
from pptx.util import Inches, Pt

# Create presentation
prs = Presentation()
slide_layout = prs.slide_layouts[1]  # Title and content
slide = prs.slides.add_slide(slide_layout)

title = slide.shapes.title
title.text = "Slide Title"

body = slide.placeholders[1]
body.text = "Bullet point"

prs.save("presentation.pptx")
```
