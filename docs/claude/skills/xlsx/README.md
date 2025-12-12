# XLSX Skill Integration

## Overview

The XLSX skill provides comprehensive spreadsheet creation, editing, and analysis capabilities with support for formulas, formatting, data analysis, and visualization. This skill enables working with Excel files (.xlsx, .xlsm) and other spreadsheet formats (.csv, .tsv) using professional financial modeling standards.

## Integration with Amplihack

This skill integrates seamlessly with the amplihack agentic coding framework, enabling AI agents to:

- Create sophisticated financial models with formulas
- Analyze and visualize data in spreadsheets
- Modify existing spreadsheets while preserving formulas and formatting
- Recalculate formulas with zero-error verification
- Follow industry-standard color coding and formatting conventions

The XLSX skill follows amplihack's brick philosophy: it is a self-contained, independently functional module with clear contracts and comprehensive dependency documentation.

## Key Capabilities

### Spreadsheet Creation

- Build Excel files from scratch using pandas or openpyxl
- Apply professional formatting (colors, fonts, alignment)
- Create dynamic formulas that recalculate automatically
- Support for multiple sheets and workbook organization

### Data Analysis

- Load and analyze data with pandas
- Generate statistics and summaries
- Create visualizations and charts
- Export results to Excel format

### Formula Management

- Insert Excel formulas (not hardcoded values)
- Recalculate formulas using LibreOffice engine
- Zero-error verification (#REF!, #DIV/0!, #VALUE!, etc.)
- Comprehensive error reporting with cell locations

### Financial Modeling Standards

- Industry-standard color coding (blue inputs, black formulas, green links)
- Professional number formatting (currency, percentages, zeros as dashes)
- Assumption cell documentation
- Source attribution for hardcoded values

## Dependencies

See [DEPENDENCIES.md](DEPENDENCIES.md) for complete dependency information including:

- Python packages (pandas, openpyxl)
- System requirements (LibreOffice)
- Installation instructions for macOS, Linux, and Windows
- Verification commands

## Usage

### Basic Example

```python
from openpyxl import Workbook

# Create workbook
wb = Workbook()
sheet = wb.active

# Add data and formulas
sheet['A1'] = 'Revenue'
sheet['B1'] = 1000
sheet['B2'] = '=B1*1.1'  # Use formula, not hardcoded value

wb.save('model.xlsx')
```

### Recalculate Formulas

```bash
python .claude/skills/xlsx/scripts/recalc.py model.xlsx
```

Returns JSON with error details:

```json
{
  "status": "success",
  "total_errors": 0,
  "total_formulas": 15
}
```

## Examples

See [examples/example_usage.md](examples/example_usage.md) for comprehensive examples including:

- Financial modeling (revenue projections, DCF models)
- Data analysis and visualization
- Budget tracking and forecasting
- Dashboard creation
- Multi-sheet workbook management

## Testing

Run the test suite to verify the skill works correctly:

```bash
cd .claude/skills/xlsx
pytest tests/ -v
```

Tests will skip gracefully if dependencies are not installed.

## Known Issues and Limitations

### LibreOffice Required for Formula Recalculation

The recalc.py script requires LibreOffice to calculate formula values. Without LibreOffice:

- Formulas will be inserted correctly
- Formula values will not be calculated
- Excel will recalculate when opened

### File Size Considerations

Very large Excel files (>100MB) may take longer to recalculate. Consider:

- Using write-only mode for large exports
- Breaking large models into multiple workbooks
- Using the timeout parameter: `python recalc.py file.xlsx 60`

### Platform-Specific Notes

**macOS**: LibreOffice installs to `/Applications/LibreOffice.app`. The `soffice` command should be available in PATH.

**Linux**: LibreOffice is typically pre-installed. Use package manager if not available.

**Windows**: The recalc.py script has limited timeout support on Windows. Formula recalculation still works.

## Zero-Error Requirement

All Excel files created with this skill MUST have zero formula errors. The recalc.py script verifies:

- **#REF!** - Invalid cell references
- **#DIV/0!** - Division by zero
- **#VALUE!** - Wrong data type in formula
- **#NAME?** - Unrecognized formula name
- **#NULL!** - Incorrect range operator
- **#NUM!** - Invalid numeric value
- **#N/A** - Value not available

If errors are found, the script reports their locations and counts for correction.

## Best Practices

### Always Use Formulas

Never hardcode calculated values. Use Excel formulas so spreadsheets remain dynamic:

```python
# Wrong
sheet['B10'] = 5000  # Hardcoded sum

# Right
sheet['B10'] = '=SUM(B2:B9)'  # Formula
```

### Follow Color Coding Standards

Unless the user specifies otherwise or an existing template has established conventions:

- **Blue text**: User inputs and scenario assumptions
- **Black text**: All formulas and calculations
- **Green text**: Internal worksheet links
- **Red text**: External file links
- **Yellow background**: Key assumptions requiring attention

### Document Hardcoded Values

If you must hardcode a value, document the source:

```python
sheet['B5'] = 42.5
sheet['C5'] = 'Source: Company 10-K, FY2024, Page 45, Revenue Note'
```

### Verify Before Delivery

Always run recalc.py before considering the Excel file complete:

```bash
python recalc.py output.xlsx
# Check status is "success"
# If errors found, fix and recalculate
```

## Amplihack Philosophy Alignment

This skill demonstrates amplihack's core principles:

**Ruthless Simplicity**: Uses standard libraries (pandas, openpyxl) without unnecessary abstractions.

**Modular Design**: Self-contained skill with clear boundaries. The recalc.py script is a focused, single-purpose tool.

**Zero-BS Implementation**: No placeholders or stubs. Every feature works completely or doesn't exist.

**Regeneratable**: Can be rebuilt from SKILL.md + recalc.py + this README.

## Support

For issues or questions:

1. Check [DEPENDENCIES.md](DEPENDENCIES.md) for installation problems
2. Review [examples/example_usage.md](examples/example_usage.md) for usage patterns
3. Run tests to verify your environment: `pytest tests/`
4. Check [SKILL.md](SKILL.md) for complete skill documentation

## Related Skills

- **PDF Skill**: For PDF manipulation and extraction (planned)
- **DOCX Skill**: For Word document creation (planned)
- **PPTX Skill**: For PowerPoint presentations (planned)

See `.claude/skills/INTEGRATION_STATUS.md` for current integration status.
