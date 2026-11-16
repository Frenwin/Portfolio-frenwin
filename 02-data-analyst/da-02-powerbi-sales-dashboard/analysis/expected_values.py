"""Compute every dashboard number independently of Power BI, to check the DAX measures against.

Usage:
    python analysis/expected_values.py     # writes docs/expected-values.md and docs/expected-values.json
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "data" / "AdventureWorks Sales.xlsx"


def load() -> pd.DataFrame:
    x = pd.read_excel(WORKBOOK, sheet_name=None)
    s = (
        x["Sales_data"]
        .merge(x["Date_data"][["DateKey", "Date", "Fiscal Year"]], left_on="OrderDateKey", right_on="DateKey")
        .merge(x["Sales Order_data"][["SalesOrderLineKey", "Channel", "Sales Order"]], on="SalesOrderLineKey")
        .merge(x["Product_data"][["ProductKey", "Product", "Subcategory", "Category"]], on="ProductKey")
        .merge(x["Sales Territory_data"][["SalesTerritoryKey", "Country", "Group"]], on="SalesTerritoryKey")
    )
    s["Profit"] = s["Sales Amount"] - s["Total Product Cost"]
    s["Discount"] = s["Extended Amount"] - s["Sales Amount"]
    return s


def kpis(df: pd.DataFrame) -> dict:
    sales, cost = df["Sales Amount"].sum(), df["Total Product Cost"].sum()
    orders = df["Sales Order"].nunique()
    return {
        "Total Sales": round(sales, 2),
        "Total Cost": round(cost, 2),
        "Gross Profit": round(sales - cost, 2),
        "Gross Margin %": round(100 * (sales - cost) / sales, 2),
        "Orders": orders,
        "Units": int(df["Order Quantity"].sum()),
        "Avg Order Value": round(sales / orders, 2),
        "Discount": round(df["Discount"].sum(), 2),
    }


def table(rows: list[dict], columns: list[str]) -> str:
    out = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    for r in rows:
        cells = []
        for c in columns:
            v = r.get(c, "")
            cells.append(f"{v:,.2f}" if isinstance(v, float) else (f"{v:,}" if isinstance(v, int) else str(v)))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def main() -> None:
    s = load()
    result: dict = {}
    years = sorted(s["Fiscal Year"].unique())

    by_year = []
    prev = None
    for fy in years:
        k = kpis(s[s["Fiscal Year"] == fy])
        k["Fiscal Year"] = fy
        if prev:
            k["Sales YoY %"] = round(100 * (k["Total Sales"] / prev["Total Sales"] - 1), 2)
            k["Profit YoY %"] = round(100 * (k["Gross Profit"] / prev["Gross Profit"] - 1), 2)
            k["Margin change pp"] = round(k["Gross Margin %"] - prev["Gross Margin %"], 2)
        by_year.append(k)
        prev = k
    result["by_fiscal_year"] = by_year
    result["all_years"] = kpis(s)

    result["by_channel_year"] = [
        {"Fiscal Year": fy, "Channel": ch, **kpis(g)} for (fy, ch), g in s.groupby(["Fiscal Year", "Channel"])
    ]
    result["by_category"] = sorted(
        [{"Category": c, **kpis(g)} for c, g in s.groupby("Category")], key=lambda r: -r["Total Sales"]
    )
    result["by_country"] = sorted(
        [{"Country": c, **kpis(g)} for c, g in s.groupby("Country")], key=lambda r: -r["Total Sales"]
    )
    latest = s[s["Fiscal Year"] == years[-1]]
    prod = latest.groupby("Product").agg(sales=("Sales Amount", "sum"), profit=("Profit", "sum")).reset_index()
    result["top_products_by_profit_latest_fy"] = [
        {"Rank": i + 1, "Product": r.Product, "Total Sales": round(r.sales, 2), "Gross Profit": round(r.profit, 2)}
        for i, r in enumerate(prod.sort_values("profit", ascending=False).head(10).itertuples())
    ]
    sub = s.groupby(["Category", "Subcategory"]).agg(sales=("Sales Amount", "sum"), profit=("Profit", "sum")).reset_index()
    sub["margin"] = 100 * sub.profit / sub.sales
    result["loss_making_subcategories"] = [
        {"Category": r.Category, "Subcategory": r.Subcategory, "Total Sales": round(r.sales, 2),
         "Gross Profit": round(r.profit, 2), "Gross Margin %": round(r.margin, 2)}
        for r in sub[sub.profit < 0].sort_values("profit").itertuples()
    ]
    lines = s.assign(loss=s["Profit"] < 0)
    result["lines_sold_below_cost"] = {
        "lines": int(lines.loss.sum()),
        "share_of_lines_pct": round(100 * lines.loss.mean(), 2),
        "by_channel": {ch: int(g.loss.sum()) for ch, g in lines.groupby("Channel")},
        "loss_amount": round(-lines.loc[lines.loss, "Profit"].sum(), 2),
    }

    (ROOT / "docs").mkdir(exist_ok=True)
    (ROOT / "docs" / "expected-values.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    kpi_cols = ["Total Sales", "Gross Profit", "Gross Margin %", "Orders", "Avg Order Value", "Units"]
    md = [
        "# Expected values",
        "",
        "Computed with pandas straight from the workbook by `analysis/expected_values.py`, independently of Power BI. "
        "Every card and table in the dashboard must show these numbers; if a DAX measure disagrees, the measure is wrong.",
        "",
        "## By fiscal year (July-June)",
        "",
        table(by_year, ["Fiscal Year", *kpi_cols, "Sales YoY %", "Profit YoY %", "Margin change pp"]),
        "",
        "## All years",
        "",
        table([result["all_years"]], [*kpi_cols, "Discount"]),
        "",
        "## By channel and fiscal year",
        "",
        table(result["by_channel_year"], ["Fiscal Year", "Channel", *kpi_cols]),
        "",
        "## By category (all years)",
        "",
        table(result["by_category"], ["Category", *kpi_cols]),
        "",
        "## By country (all years)",
        "",
        table(result["by_country"], ["Country", "Total Sales", "Gross Profit", "Gross Margin %", "Orders"]),
        "",
        f"## Top 10 products by gross profit, {years[-1]}",
        "",
        table(result["top_products_by_profit_latest_fy"], ["Rank", "Product", "Total Sales", "Gross Profit"]),
        "",
        "## Subcategories sold at a loss (all years)",
        "",
        table(result["loss_making_subcategories"], ["Category", "Subcategory", "Total Sales", "Gross Profit", "Gross Margin %"]),
        "",
        "## Order lines sold below cost",
        "",
        f"{result['lines_sold_below_cost']['lines']:,} lines ({result['lines_sold_below_cost']['share_of_lines_pct']}%) "
        f"lost a total of {result['lines_sold_below_cost']['loss_amount']:,.2f}; by channel: "
        f"{result['lines_sold_below_cost']['by_channel']}.",
        "",
    ]
    (ROOT / "docs" / "expected-values.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
