---
name: Analyze E-commerce Data
description: Systematically analyze e-commerce datasets (Excel/CSV/JSON)
---

## Analyze E-commerce Data

Guidelines for processing and validating e-commerce analytics data.

### Steps

1. **Schema Check**: Verify the column names and data types in the target dataset (e.g., `testdata.xlsx`).
2. **Data Integrity**: Identify missing values or outliers in revenue, order counts, or product IDs.
3. **Analytics Logic**: Implement or verify the aggregation logic (e.g., Daily Revenue, Top Products).
4. **Validation**: Compare results against expected PRD requirements.

### Tips
- Use Python's `pandas` or `openpyxl` for Excel processing.
- Focus on performance when handling large datasets.
