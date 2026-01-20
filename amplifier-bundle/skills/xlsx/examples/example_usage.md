# XLSX Skill Usage Examples

This document provides 10 comprehensive examples demonstrating the XLSX skill's capabilities, from basic spreadsheet creation to advanced financial modeling.

## Example 1: Basic Spreadsheet Creation

**Task**: Create a simple expense tracker with totals.

**User Request**: "Create an Excel file tracking my monthly expenses with categories and totals."

**Implementation**:

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

wb = Workbook()
sheet = wb.active
sheet.title = "Expenses"

# Headers
sheet['A1'] = 'Category'
sheet['B1'] = 'Amount'
sheet['A1'].font = Font(bold=True)
sheet['B1'].font = Font(bold=True)

# Data
expenses = [
    ('Rent', 1200),
    ('Groceries', 400),
    ('Utilities', 150),
    ('Transportation', 200)
]

row = 2
for category, amount in expenses:
    sheet[f'A{row}'] = category
    sheet[f'B{row}'] = amount
    row += 1

# Total row with formula
sheet[f'A{row}'] = 'Total'
sheet[f'B{row}'] = f'=SUM(B2:B{row-1})'  # Formula, not hardcoded
sheet[f'A{row}'].font = Font(bold=True)
sheet[f'B{row}'].font = Font(bold=True)

wb.save('expenses.xlsx')
```

**Recalculate formulas**:

```bash
python .claude/skills/xlsx/scripts/recalc.py expenses.xlsx
```

**Result**: Excel file with expense categories and a SUM formula for total expenses.

---

## Example 2: Revenue Projection Model

**Task**: Create a 5-year revenue projection with growth rates.

**User Request**: "Build a financial model showing revenue growth over 5 years with 15% annual growth."

**Implementation**:

```python
from openpyxl import Workbook
from openpyxl.styles import Font

wb = Workbook()
sheet = wb.active
sheet.title = "Revenue Projection"

# Headers
sheet['A1'] = 'Metric'
years = ['2024', '2025', '2026', '2027', '2028']
for idx, year in enumerate(years, start=2):
    sheet.cell(1, idx, year)
    sheet.cell(1, idx).font = Font(bold=True)

# Assumptions section
sheet['A2'] = 'Assumptions'
sheet['A2'].font = Font(bold=True, color='0000FF')  # Blue for inputs

sheet['A3'] = 'Base Revenue'
sheet['B3'] = 1000000  # Base revenue
sheet['B3'].font = Font(color='0000FF')  # Blue for input

sheet['A4'] = 'Growth Rate'
sheet['B4'] = 0.15  # 15% growth
sheet['B4'].font = Font(color='0000FF')
sheet['B4'].number_format = '0.0%'

# Revenue projection with formulas
sheet['A6'] = 'Revenue'
sheet['A6'].font = Font(bold=True)

# Year 1 references assumption
sheet['B6'] = '=$B$3'  # Reference base revenue
sheet['B6'].font = Font(color='000000')  # Black for formula

# Years 2-5 with growth formula
for col in range(3, 7):  # Columns C through F
    prev_col = chr(ord('A') + col - 2)
    sheet.cell(6, col, f'={prev_col}6*(1+$B$4)')  # Growth formula
    sheet.cell(6, col).font = Font(color='000000')
    sheet.cell(6, col).number_format = '$#,##0'

# Format all revenue cells as currency
for col in range(2, 7):
    sheet.cell(6, col).number_format = '$#,##0'

wb.save('revenue_projection.xlsx')
```

**Recalculate**:

```bash
python .claude/skills/xlsx/scripts/recalc.py revenue_projection.xlsx
```

**Result**: Professional financial model with blue inputs, black formulas, and currency formatting.

---

## Example 3: Data Analysis with pandas

**Task**: Analyze sales data and create summary statistics.

**User Request**: "Load sales data from CSV and create an Excel report with statistics."

**Implementation**:

```python
import pandas as pd

# Sample data (in practice, load from CSV)
data = {
    'Product': ['Widget A', 'Widget B', 'Widget C'] * 12,
    'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'] * 3,
    'Sales': [5000, 5200, 4800, 5500, 6000, 6200,
              6500, 6100, 5900, 6300, 6700, 7000,
              3000, 3100, 2900, 3200, 3400, 3500,
              3600, 3300, 3200, 3500, 3700, 3800]
}

df = pd.DataFrame(data)

# Calculate summary statistics
summary = df.groupby('Product')['Sales'].agg([
    ('Total Sales', 'sum'),
    ('Average', 'mean'),
    ('Min', 'min'),
    ('Max', 'max')
]).reset_index()

# Create Excel file with multiple sheets
with pd.ExcelWriter('sales_analysis.xlsx', engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='Raw Data', index=False)
    summary.to_excel(writer, sheet_name='Summary', index=False)

print("Sales analysis created: sales_analysis.xlsx")
```

**Result**: Multi-sheet Excel workbook with raw data and summary statistics.

---

## Example 4: Financial Model with Color Coding

**Task**: Create an income statement with proper color coding standards.

**User Request**: "Build an income statement following financial modeling best practices."

**Implementation**:

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

wb = Workbook()
sheet = wb.active
sheet.title = "Income Statement"

# Color definitions
BLUE = Font(color='0000FF')      # Inputs
BLACK = Font(color='000000')     # Formulas
GREEN = Font(color='008000')     # Internal links
YELLOW_BG = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')

# Headers
sheet['A1'] = 'Income Statement'
sheet['A1'].font = Font(bold=True, size=14)
sheet['A2'] = '($000s)'
sheet['B2'] = '2024'

# Assumptions (Blue inputs)
sheet['A4'] = 'Assumptions'
sheet['A4'].font = Font(bold=True)
sheet['A5'] = 'Revenue Growth'
sheet['B5'] = 0.12
sheet['B5'].font = BLUE
sheet['B5'].number_format = '0.0%'
sheet['B5'].fill = YELLOW_BG  # Key assumption

sheet['A6'] = 'COGS %'
sheet['B6'] = 0.40
sheet['B6'].font = BLUE
sheet['B6'].number_format = '0.0%'

sheet['A7'] = 'OpEx %'
sheet['B7'] = 0.25
sheet['B7'].font = BLUE
sheet['B7'].number_format = '0.0%'

# Income Statement (Black formulas)
sheet['A9'] = 'Revenue'
sheet['B9'] = 10000  # Base revenue (could be blue input)
sheet['B9'].font = BLUE
sheet['B9'].number_format = '$#,##0'

sheet['A10'] = 'COGS'
sheet['B10'] = '=-B9*$B$6'  # Formula
sheet['B10'].font = BLACK
sheet['B10'].number_format = '$#,##0;($#,##0);-'

sheet['A11'] = 'Gross Profit'
sheet['B11'] = '=B9+B10'  # COGS is negative
sheet['B11'].font = BLACK
sheet['B11'].number_format = '$#,##0'

sheet['A12'] = 'Operating Expenses'
sheet['B12'] = '=-B9*$B$7'
sheet['B12'].font = BLACK
sheet['B12'].number_format = '$#,##0;($#,##0);-'

sheet['A13'] = 'EBITDA'
sheet['B13'].font = Font(bold=True)
sheet['B13'] = '=B11+B12'
sheet['B13'].font = BLACK
sheet['B13'].number_format = '$#,##0'

# Column width
sheet.column_dimensions['A'].width = 25
sheet.column_dimensions['B'].width = 15

wb.save('income_statement.xlsx')
```

**Recalculate**:

```bash
python .claude/skills/xlsx/scripts/recalc.py income_statement.xlsx
```

**Result**: Professional income statement with proper color coding (blue inputs, black formulas, yellow highlighting for key assumptions).

---

## Example 5: Multi-Year Budget Model

**Task**: Create a detailed budget with multiple categories over 3 years.

**User Request**: "Build a budget model for my business with quarterly breakdown for 3 years."

**Implementation**:

```python
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment

wb = Workbook()
sheet = wb.active
sheet.title = "Budget Model"

# Headers
sheet['A1'] = 'Budget Model 2024-2026'
sheet['A1'].font = Font(bold=True, size=14)

# Time periods
periods = ['Q1 2024', 'Q2 2024', 'Q3 2024', 'Q4 2024',
           'Q1 2025', 'Q2 2025', 'Q3 2025', 'Q4 2025',
           'Q1 2026', 'Q2 2026', 'Q3 2026', 'Q4 2026']

sheet['A3'] = 'Category'
for idx, period in enumerate(periods, start=2):
    cell = sheet.cell(3, idx, period)
    cell.font = Font(bold=True)
    cell.alignment = Alignment(horizontal='center')

# Budget categories with formulas
categories = {
    'Revenue': 100000,
    'Cost of Sales': -40000,
    'Salaries': -30000,
    'Rent': -5000,
    'Marketing': -8000,
    'Utilities': -2000
}

row = 4
for category, base_amount in categories.items():
    sheet.cell(row, 1, category)
    sheet.cell(row, 1).font = Font(bold=category == 'Revenue')

    # Q1 2024 - base value
    sheet.cell(row, 2, base_amount)
    sheet.cell(row, 2).font = Font(color='0000FF')  # Blue input
    sheet.cell(row, 2).number_format = '$#,##0;($#,##0);-'

    # Subsequent quarters - growth formula (2% per quarter)
    for col in range(3, 14):
        prev_col = chr(ord('A') + col - 2)
        sheet.cell(row, col, f'={prev_col}{row}*1.02')  # 2% growth
        sheet.cell(row, col).font = Font(color='000000')  # Black formula
        sheet.cell(row, col).number_format = '$#,##0;($#,##0);-'

    row += 1

# Net Income row
sheet.cell(row, 1, 'Net Income')
sheet.cell(row, 1).font = Font(bold=True)
for col in range(2, 14):
    col_letter = chr(ord('A') + col - 1)
    sheet.cell(row, col, f'=SUM({col_letter}4:{col_letter}{row-1})')
    sheet.cell(row, col).font = Font(bold=True, color='000000')
    sheet.cell(row, col).number_format = '$#,##0'

# Set column widths
sheet.column_dimensions['A'].width = 20
for col in range(2, 14):
    sheet.column_dimensions[chr(ord('A') + col - 1)].width = 12

wb.save('budget_model.xlsx')
```

**Recalculate**:

```bash
python .claude/skills/xlsx/scripts/recalc.py budget_model.xlsx
```

**Result**: Comprehensive budget model with quarterly projections and automatic totals.

---

## Example 6: DCF Valuation Model

**Task**: Build a discounted cash flow valuation model.

**User Request**: "Create a DCF model to value a company with 5-year projections."

**Implementation**:

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

wb = Workbook()
sheet = wb.active
sheet.title = "DCF Model"

BLUE = Font(color='0000FF')
BLACK = Font(color='000000')
YELLOW = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')

# Title
sheet['A1'] = 'DCF Valuation Model'
sheet['A1'].font = Font(bold=True, size=14)

# Years
years = ['2024', '2025', '2026', '2027', '2028']
sheet['A3'] = 'Year'
for idx, year in enumerate(years, start=2):
    sheet.cell(3, idx, year)
    sheet.cell(3, idx).font = Font(bold=True)

# Assumptions
sheet['A5'] = 'Assumptions'
sheet['A5'].font = Font(bold=True)

sheet['A6'] = 'Base FCF'
sheet['B6'] = 5000000
sheet['B6'].font = BLUE
sheet['B6'].fill = YELLOW
sheet['B6'].number_format = '$#,##0'

sheet['A7'] = 'Growth Rate'
sheet['B7'] = 0.10
sheet['B7'].font = BLUE
sheet['B7'].fill = YELLOW
sheet['B7'].number_format = '0.0%'

sheet['A8'] = 'Terminal Growth'
sheet['B8'] = 0.03
sheet['B8'].font = BLUE
sheet['B8'].fill = YELLOW
sheet['B8'].number_format = '0.0%'

sheet['A9'] = 'Discount Rate (WACC)'
sheet['B9'] = 0.12
sheet['B9'].font = BLUE
sheet['B9'].fill = YELLOW
sheet['B9'].number_format = '0.0%'

# Free Cash Flow Projections
sheet['A11'] = 'Free Cash Flow'
sheet['A11'].font = Font(bold=True)

# Year 1
sheet['B11'] = '=$B$6'
sheet['B11'].font = BLACK
sheet['B11'].number_format = '$#,##0'

# Years 2-5
for col in range(3, 7):
    prev_col = chr(ord('A') + col - 2)
    sheet.cell(11, col, f'={prev_col}11*(1+$B$7)')
    sheet.cell(11, col).font = BLACK
    sheet.cell(11, col).number_format = '$#,##0'

# Discount factors
sheet['A12'] = 'Discount Factor'
for col in range(2, 7):
    year_num = col - 1
    sheet.cell(12, col, f'=1/((1+$B$9)^{year_num})')
    sheet.cell(12, col).font = BLACK
    sheet.cell(12, col).number_format = '0.000'

# Present Value of FCF
sheet['A13'] = 'PV of FCF'
for col in range(2, 7):
    col_letter = chr(ord('A') + col - 1)
    sheet.cell(13, col, f'={col_letter}11*{col_letter}12')
    sheet.cell(13, col).font = BLACK
    sheet.cell(13, col).number_format = '$#,##0'

# Terminal Value
sheet['A15'] = 'Terminal Value'
sheet['F15'] = '=F11*(1+$B$8)/($B$9-$B$8)'
sheet['F15'].font = BLACK
sheet['F15'].number_format = '$#,##0'

sheet['A16'] = 'PV of Terminal Value'
sheet['F16'] = '=F15*F12'
sheet['F16'].font = BLACK
sheet['F16'].number_format = '$#,##0'

# Enterprise Value
sheet['A18'] = 'Enterprise Value'
sheet['A18'].font = Font(bold=True)
sheet['B18'] = '=SUM(B13:F13)+F16'
sheet['B18'].font = Font(bold=True, color='000000')
sheet['B18'].number_format = '$#,##0'

# Column widths
sheet.column_dimensions['A'].width = 25
for col in 'BCDEFG':
    sheet.column_dimensions[col].width = 15

wb.save('dcf_model.xlsx')
```

**Recalculate**:

```bash
python .claude/skills/xlsx/scripts/recalc.py dcf_model.xlsx
```

**Result**: Professional DCF valuation model with discounted cash flows and terminal value calculation.

---

## Example 7: Dashboard with Multiple Metrics

**Task**: Create an executive dashboard with KPIs.

**User Request**: "Build a dashboard showing key business metrics with visual formatting."

**Implementation**:

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

wb = Workbook()
sheet = wb.active
sheet.title = "Executive Dashboard"

# Styling
TITLE_FONT = Font(bold=True, size=16, color='FFFFFF')
TITLE_FILL = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
HEADER_FONT = Font(bold=True, size=12)
METRIC_FONT = Font(size=20, bold=True, color='2F5597')
BORDER = Border(
    left=Side(style='thin'),
    right=Side(style='thin'),
    top=Side(style='thin'),
    bottom=Side(style='thin')
)

# Title
sheet.merge_cells('A1:F1')
sheet['A1'] = 'Executive Dashboard - Q4 2024'
sheet['A1'].font = TITLE_FONT
sheet['A1'].fill = TITLE_FILL
sheet['A1'].alignment = Alignment(horizontal='center', vertical='center')
sheet.row_dimensions[1].height = 30

# KPI Section 1: Revenue
sheet.merge_cells('A3:B3')
sheet['A3'] = 'Total Revenue'
sheet['A3'].font = HEADER_FONT
sheet['A3'].border = BORDER

sheet.merge_cells('A4:B4')
sheet['A4'] = '=B10'  # Links to data below
sheet['A4'].font = METRIC_FONT
sheet['A4'].number_format = '$#,##0'
sheet['A4'].alignment = Alignment(horizontal='center')
sheet['A4'].border = BORDER

# KPI Section 2: Profit Margin
sheet.merge_cells('D3:E3')
sheet['D3'] = 'Profit Margin'
sheet['D3'].font = HEADER_FONT
sheet['D3'].border = BORDER

sheet.merge_cells('D4:E4')
sheet['D4'] = '=B12/B10'  # Profit / Revenue
sheet['D4'].font = METRIC_FONT
sheet['D4'].number_format = '0.0%'
sheet['D4'].alignment = Alignment(horizontal='center')
sheet['D4'].border = BORDER

# Data section (hidden below dashboard)
sheet['A9'] = 'Underlying Data'
sheet['A9'].font = Font(bold=True, italic=True)

sheet['A10'] = 'Revenue'
sheet['B10'] = 2500000
sheet['B10'].font = Font(color='0000FF')
sheet['B10'].number_format = '$#,##0'

sheet['A11'] = 'Expenses'
sheet['B11'] = 1800000
sheet['B11'].font = Font(color='0000FF')
sheet['B11'].number_format = '$#,##0'

sheet['A12'] = 'Profit'
sheet['B12'] = '=B10-B11'
sheet['B12'].font = Font(color='000000')
sheet['B12'].number_format = '$#,##0'

# Column widths
sheet.column_dimensions['A'].width = 15
sheet.column_dimensions['B'].width = 15
sheet.column_dimensions['D'].width = 15
sheet.column_dimensions['E'].width = 15

wb.save('dashboard.xlsx')
```

**Recalculate**:

```bash
python .claude/skills/xlsx/scripts/recalc.py dashboard.xlsx
```

**Result**: Professional executive dashboard with formatted KPI displays and underlying data.

---

## Example 8: Data Import and Transformation

**Task**: Load messy data, clean it, and export to Excel.

**User Request**: "Clean this sales data and create a professional Excel report."

**Implementation**:

```python
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font

# Sample messy data
raw_data = {
    'customer_name': ['  John Doe', 'Jane Smith  ', 'Bob Jones', None, 'Alice Brown'],
    'order_date': ['2024-01-15', '2024-01-20', 'invalid', '2024-02-01', '2024-02-15'],
    'amount': ['1000', '1500.50', 'invalid', '2000', '750.25']
}

df = pd.DataFrame(raw_data)

# Clean data
df['customer_name'] = df['customer_name'].str.strip()  # Remove whitespace
df = df.dropna(subset=['customer_name'])  # Remove null customers
df['order_date'] = pd.to_datetime(df['order_date'], errors='coerce')  # Parse dates
df = df.dropna(subset=['order_date'])  # Remove invalid dates
df['amount'] = pd.to_numeric(df['amount'], errors='coerce')  # Parse amounts
df = df.dropna(subset=['amount'])  # Remove invalid amounts

# Calculate summary
summary = {
    'Total Orders': len(df),
    'Total Revenue': df['amount'].sum(),
    'Average Order': df['amount'].mean()
}

# Export to Excel with pandas
with pd.ExcelWriter('sales_report.xlsx', engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='Clean Data', index=False)

    # Summary sheet
    summary_df = pd.DataFrame(list(summary.items()), columns=['Metric', 'Value'])
    summary_df.to_excel(writer, sheet_name='Summary', index=False)

# Post-process with openpyxl for formatting
wb = load_workbook('sales_report.xlsx')

# Format Summary sheet
summary_sheet = wb['Summary']
summary_sheet['A1'].font = Font(bold=True)
summary_sheet['B1'].font = Font(bold=True)
summary_sheet['B2'].number_format = '0'
summary_sheet['B3'].number_format = '$#,##0.00'
summary_sheet['B4'].number_format = '$#,##0.00'

wb.save('sales_report.xlsx')
```

**Result**: Clean data and formatted summary report in Excel.

---

## Example 9: Formula Error Detection

**Task**: Create a spreadsheet with formulas and verify zero errors.

**User Request**: "Build a spreadsheet and make sure all formulas calculate correctly."

**Implementation**:

```python
from openpyxl import Workbook
import subprocess
import json

wb = Workbook()
sheet = wb.active

# Create some formulas
sheet['A1'] = 'Value 1'
sheet['B1'] = 100
sheet['A2'] = 'Value 2'
sheet['B2'] = 200
sheet['A3'] = 'Total'
sheet['B3'] = '=SUM(B1:B2)'

sheet['A5'] = 'Average'
sheet['B5'] = '=AVERAGE(B1:B2)'

sheet['A7'] = 'Percentage'
sheet['B7'] = '=B1/B3'
sheet['B7'].number_format = '0.0%'

wb.save('formulas_test.xlsx')

# Recalculate and verify
result = subprocess.run(
    ['python', '.claude/skills/xlsx/scripts/recalc.py', 'formulas_test.xlsx'],
    capture_output=True,
    text=True
)

# Parse result
verification = json.loads(result.stdout)

if verification['status'] == 'success':
    print(f"✓ Success! All {verification['total_formulas']} formulas calculated correctly.")
else:
    print(f"✗ Found {verification['total_errors']} errors:")
    for error_type, details in verification['error_summary'].items():
        print(f"  {error_type}: {details['count']} errors")
        for location in details['locations']:
            print(f"    - {location}")
```

**Result**: Spreadsheet with verified formulas and detailed error reporting if any issues found.

---

## Example 10: Multi-Sheet Financial Model

**Task**: Create a comprehensive financial model with multiple linked sheets.

**User Request**: "Build a complete financial model with separate sheets for assumptions, income statement, balance sheet, and cash flow."

**Implementation**:

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

wb = Workbook()

# Remove default sheet
wb.remove(wb.active)

# Sheet 1: Assumptions
assumptions = wb.create_sheet("Assumptions")
assumptions['A1'] = 'Model Assumptions'
assumptions['A1'].font = Font(bold=True, size=14)

assumptions['A3'] = 'Revenue Growth'
assumptions['B3'] = 0.15
assumptions['B3'].font = Font(color='0000FF')
assumptions['B3'].fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')
assumptions['B3'].number_format = '0.0%'

assumptions['A4'] = 'Gross Margin'
assumptions['B4'] = 0.65
assumptions['B4'].font = Font(color='0000FF')
assumptions['B4'].fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')
assumptions['B4'].number_format = '0.0%'

assumptions['A5'] = 'Tax Rate'
assumptions['B5'] = 0.21
assumptions['B5'].font = Font(color='0000FF')
assumptions['B5'].fill = PatternFill(start_color='FFFF00', end_color='FFFF00', fill_type='solid')
assumptions['B5'].number_format = '0.0%'

# Sheet 2: Income Statement
income = wb.create_sheet("Income Statement")
income['A1'] = 'Income Statement'
income['A1'].font = Font(bold=True, size=14)

years = ['2024', '2025', '2026']
income['A3'] = 'Year'
for idx, year in enumerate(years, start=2):
    income.cell(3, idx, year)
    income.cell(3, idx).font = Font(bold=True)

# Revenue
income['A5'] = 'Revenue'
income['B5'] = 1000000
income['B5'].font = Font(color='0000FF')
income['B5'].number_format = '$#,##0'

# Years 2-3 with growth from assumptions sheet
income['C5'] = '=B5*(1+Assumptions!$B$3)'  # Links to assumptions (green)
income['C5'].font = Font(color='008000')
income['C5'].number_format = '$#,##0'

income['D5'] = '=C5*(1+Assumptions!$B$3)'
income['D5'].font = Font(color='008000')
income['D5'].number_format = '$#,##0'

# COGS
income['A6'] = 'COGS'
for col in range(2, 5):
    col_letter = chr(ord('A') + col - 1)
    income.cell(6, col, f'=-{col_letter}5*(1-Assumptions!$B$4)')
    income.cell(6, col).font = Font(color='008000')  # Green for cross-sheet
    income.cell(6, col).number_format = '$#,##0;($#,##0);-'

# Gross Profit
income['A7'] = 'Gross Profit'
for col in range(2, 5):
    col_letter = chr(ord('A') + col - 1)
    income.cell(7, col, f'={col_letter}5+{col_letter}6')
    income.cell(7, col).font = Font(color='000000')
    income.cell(7, col).number_format = '$#,##0'

# Sheet 3: Balance Sheet
balance = wb.create_sheet("Balance Sheet")
balance['A1'] = 'Balance Sheet'
balance['A1'].font = Font(bold=True, size=14)

balance['A3'] = 'Year'
for idx, year in enumerate(years, start=2):
    balance.cell(3, idx, year)
    balance.cell(3, idx).font = Font(bold=True)

# Assets
balance['A5'] = 'Assets'
balance['A5'].font = Font(bold=True)

balance['A6'] = 'Cash'
for col in range(2, 5):
    col_letter = chr(ord('A') + col - 1)
    # Link to income statement profit * 0.3 (simplified)
    balance.cell(6, col, f"='Income Statement'!{col_letter}7*0.3")
    balance.cell(6, col).font = Font(color='008000')  # Green for cross-sheet
    balance.cell(6, col).number_format = '$#,##0'

# Sheet 4: Cash Flow
cashflow = wb.create_sheet("Cash Flow")
cashflow['A1'] = 'Cash Flow Statement'
cashflow['A1'].font = Font(bold=True, size=14)

cashflow['A3'] = 'Year'
for idx, year in enumerate(years, start=2):
    cashflow.cell(3, idx, year)
    cashflow.cell(3, idx).font = Font(bold=True)

# Operating Cash Flow (links to Income Statement)
cashflow['A5'] = 'Operating Cash Flow'
for col in range(2, 5):
    col_letter = chr(ord('A') + col - 1)
    cashflow.cell(5, col, f"='Income Statement'!{col_letter}7")
    cashflow.cell(5, col).font = Font(color='008000')
    cashflow.cell(5, col).number_format = '$#,##0'

wb.save('integrated_model.xlsx')
```

**Recalculate**:

```bash
python .claude/skills/xlsx/scripts/recalc.py integrated_model.xlsx
```

**Result**: Comprehensive multi-sheet financial model with proper linking (green color for cross-sheet references) and integration between statements.

---

## Best Practices Demonstrated

These examples demonstrate:

1. **Formula Usage**: Always use formulas, never hardcoded calculations
2. **Color Coding**: Blue for inputs, black for formulas, green for links
3. **Zero Errors**: Always run recalc.py to verify
4. **Professional Formatting**: Currency, percentages, alignment
5. **Multi-Sheet Integration**: Linking data across worksheets
6. **Documentation**: Clear labels and assumption sections
7. **Data Validation**: Clean and verify data before export
8. **Comprehensive Models**: Build complete financial models
9. **pandas Integration**: Use pandas for data analysis
10. **Error Detection**: Automated verification of formula correctness

## Running Examples

To run any example:

1. Copy the code to a Python file (e.g., `example_1.py`)
2. Run: `python example_1.py`
3. Recalculate formulas: `python .claude/skills/xlsx/scripts/recalc.py output.xlsx`
4. Verify zero errors in the JSON output
5. Open the Excel file to see results

## Additional Resources

- **SKILL.md**: Complete skill documentation
- **DEPENDENCIES.md**: Installation instructions
- **README.md**: Integration overview
- **tests/**: Test examples for verification
