# Build guide

## Quick path (about 2 minutes)

The whole dashboard (model, relationships, 20 measures, both pages) is generated as a Power BI Project:

```powershell
python tools/build_pbip.py          # writes the .pbip, .SemanticModel and .Report folders
```

1. Open `AdventureWorks Sales Dashboard.pbip` in Power BI Desktop.
2. If the workbook is not at the path in the `SourceFile` parameter, change it: **Transform data → Manage parameters → SourceFile**.
3. **Home → Refresh** (about 10 seconds).
4. Check the numbers against [dax-validation.md](dax-validation.md).

The manual path below builds the same thing by hand; it is kept for learning Power BI step by step.

## Manual path (about 60–90 minutes)

## 1. Load the data (10 min)

1. Download the data if `data/AdventureWorks Sales.xlsx` is missing:
   ```powershell
   curl.exe -L -o "data/AdventureWorks Sales.xlsx" "https://raw.githubusercontent.com/microsoft/powerbi-desktop-samples/main/AdventureWorks%20Sales%20Sample/AdventureWorks%20Sales.xlsx"
   ```
2. Power BI Desktop → **Get data → Excel workbook** → pick the file.
3. In the Navigator tick the **7 tables** (table icon, not the `*_data` sheets): `Customer`, `Date`, `Product`, `Reseller`, `Sales`, `SalesOrder`, `SalesTerritory`.
4. Click **Transform data** and set two types:
   - `Date[Date]` → **Date**
   - `Sales[ShipDateKey]` → **Whole number** (it has 2,113 blanks for unshipped lines; that is expected)
5. **Close & Apply**.

## 2. Model (10 min)

Open **Model view**. Power BI auto-detects most relationships; make the set exactly this (all single direction, many-to-one, from `Sales`):

| From (many) | To (one) | Active |
| --- | --- | --- |
| `Sales[OrderDateKey]` | `Date[DateKey]` | **Yes** (create it: names differ, so it is not auto-detected) |
| `Sales[ProductKey]` | `Product[ProductKey]` | Yes |
| `Sales[CustomerKey]` | `Customer[CustomerKey]` | Yes |
| `Sales[ResellerKey]` | `Reseller[ResellerKey]` | Yes |
| `Sales[SalesTerritoryKey]` | `SalesTerritory[SalesTerritoryKey]` | Yes |
| `Sales[SalesOrderLineKey]` | `SalesOrder[SalesOrderLineKey]` | Yes. If detected as one-to-one / both directions, change it to **Many to one, Single** |

Then:

1. Select the `Date` table → **Table tools → Mark as date table** → column `Date`.
2. `Date[Month]` → **Sort by column** → `MonthKey` (otherwise months sort alphabetically).
3. Hide the key columns in report view (right-click → Hide): every `*Key` column in `Sales`, and `DateKey`, `MonthKey`.

## 3. Measures (10 min)

1. Open **DAX query view** (left rail, fourth icon).
2. Paste the whole of [`model/measures.dax`](../model/measures.dax) and press **Run**.
3. Compare the two result grids with [`expected-values.md`](expected-values.md). FY2019 must show Total Sales 34,070,108.50, Gross Margin 10.88%, Orders 4,738. If anything differs, stop and fix the model before building visuals.
4. Click **Update model: Add 20 new measures** (the link just above `DEFINE`).
5. In Model view, set formats (select the measure → Measure tools):

| Measures | Format |
| --- | --- |
| Total Sales, Total Cost, Gross Profit, Discount, Total Sales PY, Gross Profit PY, Sales FYTD, Sales PY FYTD, Loss Amount, Avg Order Value | Currency, 0 decimals |
| Gross Margin %, Gross Margin PY, Sales YoY %, Profit YoY %, Reseller Share % | Percentage, 1 decimal |
| Margin Change pp | Decimal, 1 decimal, suffix " pp" (custom format `0.0" pp"`) |
| Orders, Units, Loss Lines, Profit Rank | Whole number, thousands separator |

6. Optional but tidy: put measures in display folders `Revenue`, `Volume`, `Time intelligence`, `Diagnostics` (matching the comments in the file).

## 4. Report pages (40–60 min)

Build the two pages described in [`dashboard-spec.md`](dashboard-spec.md). Tips:

- Page size 16:9 (1280 × 720). Turn on **View → Gridlines** and **Snap to grid**.
- Add a **page-level filter** `Date[Fiscal Year]` *is not* `FY2021` on both pages (the date table runs a year past the sales).
- Use the **Card (new)** visual for KPIs: main value = the measure, reference label = its YoY measure.
- Write each visual title as the finding, not the field list (the spec gives every title).
- Conditional formatting on `Gross Margin %` in tables: rules, red below 0, default otherwise.

## 5. Publish to the repo (10 min)

1. **File → Save as** `AdventureWorks Sales Dashboard.pbix` in this folder.
2. **File → Export → Export to PDF** → `docs/dashboard.pdf`.
3. Take one screenshot per page → `docs/page-1-overview.png`, `docs/page-2-drilldown.png`.
4. Tell Claude; it will check the screenshots against the expected values and finish the README.
