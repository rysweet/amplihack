# Python Data Visualization Guidelines

## Required Libraries

Use these standard data visualization libraries:

```python
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
```

## Chart Quality Standards

### Figure Settings

- DPI: 300 minimum for production charts
- Figure size: 12x7 inches (standard)
- Style: seaborn-v0_8 or seaborn default

### Chart Elements

- **Title**: Clear, descriptive
- **Axes labels**: Units specified
- **Legend**: Positioned appropriately
- **Grid**: Optional, subtle if used
- **Colors**: Use colorblind-friendly palettes

## Common Chart Types

### Line Charts (Trends)

```python
plt.figure(figsize=(12, 7), dpi=300)
sns.set_style("whitegrid")
plt.plot(dates, values, marker='o')
plt.title("Metric Trend Over Time")
plt.xlabel("Date")
plt.ylabel("Count")
plt.savefig("trend.png", dpi=300, bbox_inches='tight')
```

### Bar Charts (Comparisons)

```python
plt.figure(figsize=(12, 7), dpi=300)
sns.barplot(x=categories, y=values)
plt.title("Category Comparison")
plt.xticks(rotation=45, ha='right')
plt.savefig("comparison.png", dpi=300, bbox_inches='tight')
```

## Data Preparation

Always prepare data in pandas DataFrames for consistent handling and easy manipulation.
