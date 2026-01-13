---
skill:
  name: xlsx
  description: Excel document operations - creation and manipulation
---

# Excel Operations

## Libraries
- **openpyxl**: Full Excel support
- **pandas**: Data analysis with Excel I/O
- **xlsxwriter**: Write-only, advanced formatting

## Common Operations

```python
import pandas as pd
from openpyxl import Workbook

# Read Excel
df = pd.read_excel("data.xlsx", sheet_name="Sheet1")

# Write Excel with pandas
df.to_excel("output.xlsx", index=False)

# Create with openpyxl
wb = Workbook()
ws = wb.active
ws["A1"] = "Header"
wb.save("workbook.xlsx")
```
