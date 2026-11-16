"""Generate the Power BI project (PBIP): semantic model in TMDL + report in PBIR.

Everything Power BI needs is written as text, so the dashboard is reproducible and diffable:
    python tools/build_pbip.py
Then open "AdventureWorks Sales Dashboard.pbip" in Power BI Desktop and press Refresh.

Measures are read from model/measures.dax, so the DAX lives in one place.
"""

from __future__ import annotations

import json
import re
import shutil
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "AdventureWorks Sales Dashboard"
MODEL_DIR = ROOT / f"{NAME}.SemanticModel"
REPORT_DIR = ROOT / f"{NAME}.Report"
WORKBOOK = ROOT / "data" / "AdventureWorks Sales.xlsx"
BASE_THEME = "Fluent2-CY26SU10"
THEME_SOURCE = Path(r"C:\Program Files\Microsoft Power BI Desktop\bin\WebView2Resources\minerva\sharedresources\BaseThemes") / f"{BASE_THEME}.json"

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric"
V_REPORT, V_PAGE, V_VISUAL = "3.3.0", "2.1.0", "2.10.0"
NS = uuid.UUID("0d4c5f0e-2a8b-4c43-9d6c-6a1f2b7e9c11")  # stable ids across rebuilds

# ----------------------------------------------------------------------------- model
# table -> (Excel table name, [(column, tmdl dataType, M type, hidden)])
TABLES: dict[str, tuple[str, list[tuple[str, str, str, bool]]]] = {
    "Sales": ("Sales", [
        ("SalesOrderLineKey", "int64", "Int64.Type", True),
        ("ResellerKey", "int64", "Int64.Type", True),
        ("CustomerKey", "int64", "Int64.Type", True),
        ("ProductKey", "int64", "Int64.Type", True),
        ("OrderDateKey", "int64", "Int64.Type", True),
        ("DueDateKey", "int64", "Int64.Type", True),
        ("ShipDateKey", "int64", "Int64.Type", True),
        ("SalesTerritoryKey", "int64", "Int64.Type", True),
        ("Order Quantity", "int64", "Int64.Type", False),
        ("Unit Price", "double", "type number", False),
        ("Extended Amount", "double", "type number", False),
        ("Unit Price Discount Pct", "double", "type number", True),
        ("Product Standard Cost", "double", "type number", False),
        ("Total Product Cost", "double", "type number", False),
        ("Sales Amount", "double", "type number", False),
    ]),
    "Date": ("Date", [
        ("DateKey", "int64", "Int64.Type", True),
        ("Date", "dateTime", "type date", False),
        ("Fiscal Year", "string", "type text", False),
        ("Fiscal Quarter", "string", "type text", False),
        ("Month", "string", "type text", False),
        ("Full Date", "string", "type text", True),
        ("MonthKey", "int64", "Int64.Type", True),
        ("Month Start", "dateTime", "computed", False),  # added in Power Query for a continuous month axis
    ]),
    "Product": ("Product", [
        ("ProductKey", "int64", "Int64.Type", True),
        ("SKU", "string", "type text", False),
        ("Product", "string", "type text", False),
        ("Standard Cost", "double", "type number", False),
        ("Color", "string", "type text", False),
        ("List Price", "double", "type number", False),
        ("Model", "string", "type text", False),
        ("Subcategory", "string", "type text", False),
        ("Category", "string", "type text", False),
    ]),
    "Customer": ("Customer", [
        ("CustomerKey", "int64", "Int64.Type", True),
        ("Customer ID", "string", "type text", False),
        ("Customer", "string", "type text", False),
        ("City", "string", "type text", False),
        ("State-Province", "string", "type text", False),
        ("Country-Region", "string", "type text", False),
        ("Postal Code", "string", "type text", False),
    ]),
    "Reseller": ("Reseller", [
        ("ResellerKey", "int64", "Int64.Type", True),
        ("Reseller ID", "string", "type text", False),
        ("Business Type", "string", "type text", False),
        ("Reseller", "string", "type text", False),
        ("City", "string", "type text", False),
        ("State-Province", "string", "type text", False),
        ("Country-Region", "string", "type text", False),
        ("Postal Code", "string", "type text", False),
    ]),
    "SalesTerritory": ("SalesTerritory", [
        ("SalesTerritoryKey", "int64", "Int64.Type", True),
        ("Region", "string", "type text", False),
        ("Country", "string", "type text", False),
        ("Group", "string", "type text", False),
    ]),
    "SalesOrder": ("SalesOrder", [
        ("Channel", "string", "type text", False),
        ("SalesOrderLineKey", "int64", "Int64.Type", True),
        ("Sales Order", "string", "type text", False),
        ("Sales Order Line", "string", "type text", False),
    ]),
}

RELATIONSHIPS = [
    ("Sales", "OrderDateKey", "Date", "DateKey"),
    ("Sales", "ProductKey", "Product", "ProductKey"),
    ("Sales", "CustomerKey", "Customer", "CustomerKey"),
    ("Sales", "ResellerKey", "Reseller", "ResellerKey"),
    ("Sales", "SalesTerritoryKey", "SalesTerritory", "SalesTerritoryKey"),
    ("Sales", "SalesOrderLineKey", "SalesOrder", "SalesOrderLineKey"),
]

FORMATS = {
    "currency": r"\$#,0",
    "currency2": r"\$#,0.00",
    "percent": "0.0%",
    "pp": "+0.0;-0.0;0.0",
    "whole": "#,0",
}
MEASURE_FORMAT = {
    "Total Sales": "currency", "Total Cost": "currency", "Gross Profit": "currency", "Discount": "currency",
    "Total Sales PY": "currency", "Gross Profit PY": "currency", "Sales FYTD": "currency", "Sales PY FYTD": "currency",
    "Loss Amount": "currency", "Avg Order Value": "currency2",
    "Gross Margin %": "percent", "Gross Margin PY": "percent", "Sales YoY %": "percent", "Profit YoY %": "percent",
    "Reseller Share %": "percent", "Margin Change pp": "pp",
    "Orders": "whole", "Units": "whole", "Loss Lines": "whole", "Profit Rank": "whole",
    "Gross Profit Top 10": "currency",
    "KPI Sales": "currency", "KPI Sales PY": "currency", "KPI Profit": "currency", "KPI Profit PY": "currency",
    "KPI Margin": "percent", "KPI Margin PY": "percent", "KPI Orders": "whole", "KPI Orders PY": "whole",
    "KPI AOV": "currency2", "KPI AOV PY": "currency2",
    # text and colour measures (KPI Period, KPI * Delta, * Color) carry no format string
}


def q(name: str) -> str:
    """TMDL name quoting: quote anything that is not a plain identifier."""
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else "'" + name.replace("'", "''") + "'"


def tag(*parts: str) -> str:
    return str(uuid.uuid5(NS, "/".join(parts)))


def parse_measures() -> list[tuple[str, str, str]]:
    """(name, folder, expression) from model/measures.dax, in file order."""
    text = (ROOT / "model" / "measures.dax").read_text(encoding="utf-8")
    body = re.split(r"(?m)^DEFINE\s*$", text, maxsplit=1)[1]
    body = re.split(r"(?m)^EVALUATE\b", body, maxsplit=1)[0]
    measures, folder, current = [], "Measures", None
    for line in body.splitlines():
        header = re.match(r"\s*// -+ (.+?) -+\s*$", line)
        start = re.match(r"\s*MEASURE Sales\[(.+?)\] =\s*$", line)
        if header:
            folder = header.group(1).split(" (")[0]
            current = None
        elif start:
            current = [start.group(1), folder, []]
            measures.append(current)
        elif current is not None and line.strip():
            current[2].append(line.strip() if not line.strip().startswith("//") else line.strip())
    out = []
    for name, folder, lines in measures:
        # keep the original relative indentation of continuation lines
        out.append((name, folder, lines))
    return [(n, f, "\n".join(l)) for n, f, l in out]


def m_query(table: str, excel_name: str, columns) -> str:
    types = ", ".join(f'{{"{c}", {m}}}' for c, _, m, _ in columns if m != "computed")
    lines = [
        "let",
        "    Source = Excel.Workbook(File.Contents(SourceFile), null, true),",
        f'    Data = Source{{[Item="{excel_name}",Kind="Table"]}}[Data],',
        f"    Typed = Table.TransformColumnTypes(Data, {{{types}}})" + ("," if table == "Date" else ""),
    ]
    if table == "Date":
        # The sample's date table runs a year past the last sale; stop at the end of FY2020.
        lines.append("    Trimmed = Table.SelectRows(Typed, each [Date] <= #date(2020, 6, 30)),")
        lines.append('    WithMonthStart = Table.AddColumn(Trimmed, "Month Start", each Date.StartOfMonth([Date]), type date)')
        lines += ["in", "    WithMonthStart"]
    else:
        lines += ["in", "    Typed"]
    return "\n".join(lines)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def build_model() -> int:
    if MODEL_DIR.exists():
        shutil.rmtree(MODEL_DIR)
    d = MODEL_DIR / "definition"
    write(MODEL_DIR / "definition.pbism", json.dumps({
        "$schema": f"{SCHEMA}/item/semanticModel/definitionProperties/1.0.0/schema.json",
        "version": "4.0",
        "settings": {},
    }, indent=2))
    write(d / "database.tmdl", "database\n\tcompatibilityLevel: 1600\n")
    order = ["SourceFile", *TABLES]
    model = [
        "model Model",
        "\tculture: en-US",
        "\tdefaultPowerBIDataSourceVersion: powerBI_V3",
        "\tsourceQueryCulture: en-US",
        "\tdataAccessOptions",
        "\t\tlegacyRedirects",
        "\t\treturnErrorValuesAsNull",
        "",
        f"annotation PBI_QueryOrder = {json.dumps(order)}",
        "",
        "annotation __PBI_TimeIntelligenceEnabled = 0",
        "",
        *[f"ref table {q(t)}" for t in TABLES],
        "",
    ]
    write(d / "model.tmdl", "\n".join(model))
    workbook = str(WORKBOOK)
    write(d / "expressions.tmdl", "\n".join([
        f'expression SourceFile = "{workbook}" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]',
        f"\tlineageTag: {tag('expr', 'SourceFile')}",
        "",
        "\tannotation PBI_ResultType = Text",
        "",
    ]))

    measures = parse_measures()
    for table, (excel, columns) in TABLES.items():
        lines = [f"table {q(table)}", f"\tlineageTag: {tag('table', table)}"]
        if table == "Date":
            lines.append("\tdataCategory: Time")
        lines.append("")
        if table == "Sales":
            for name, folder, expr in measures:
                lines.append(f"\tmeasure {q(name)} =")
                lines += [f"\t\t\t{e}" for e in expr.splitlines()]
                if name in MEASURE_FORMAT:
                    lines.append(f"\t\tformatString: {FORMATS[MEASURE_FORMAT[name]]}")
                lines.append(f"\t\tdisplayFolder: {folder}")
                lines.append(f"\t\tlineageTag: {tag('measure', name)}")
                lines.append("")
        for col, dtype, _, hidden in columns:
            lines.append(f"\tcolumn {q(col)}")
            lines.append(f"\t\tdataType: {dtype}")
            if hidden:
                lines.append("\t\tisHidden")
            if table == "Date" and col == "Date":
                lines.append("\t\tisKey")
                lines.append("\t\tformatString: yyyy-mm-dd")
            if table == "Date" and col == "Month":
                lines.append("\t\tsortByColumn: MonthKey")
            if table == "Date" and col == "Month Start":
                lines.append("\t\tformatString: mmm yyyy")
            lines.append(f"\t\tlineageTag: {tag('column', table, col)}")
            lines.append("\t\tsummarizeBy: none")
            lines.append(f"\t\tsourceColumn: {col}")
            lines.append("")
        lines.append(f"\tpartition {q(table)} = m")
        lines.append("\t\tmode: import")
        lines.append("\t\tsource =")
        lines += [f"\t\t\t\t{l}" for l in m_query(table, excel, columns).splitlines()]
        lines.append("")
        write(d / "tables" / f"{table}.tmdl", "\n".join(lines))

    rel = []
    for f_table, f_col, t_table, t_col in RELATIONSHIPS:
        rel += [
            f"relationship {tag('rel', f_table, f_col)}",
            f"\tfromColumn: {q(f_table)}.{q(f_col)}",
            f"\ttoColumn: {q(t_table)}.{q(t_col)}",
            "",
        ]
    write(d / "relationships.tmdl", "\n".join(rel))
    return len(measures)


# ----------------------------------------------------------------------------- report
THEME_FILE = ROOT / "theme" / "AdventureWorksExecutive.json"
CUSTOM_THEME = "AdventureWorksExecutive.json"

BLUE, ORANGE, GREY, RED, INK, MUTED = "#2A78D6", "#EB6834", "#9CA3AF", "#B91C1C", "#111827", "#6B7280"


def measure(name: str) -> dict:
    return {"Measure": {"Expression": {"SourceRef": {"Entity": "Sales"}}, "Property": name}}


def column(table: str, name: str) -> dict:
    return {"Column": {"Expression": {"SourceRef": {"Entity": table}}, "Property": name}}


def ref(field: dict) -> str:
    kind = "Measure" if "Measure" in field else "Column"
    return f'{field[kind]["Expression"]["SourceRef"]["Entity"]}.{field[kind]["Property"]}'


def projection(field) -> dict:
    """field, or (field, display name shown in the visual)."""
    field, display = field if isinstance(field, tuple) else (field, None)
    kind = "Measure" if "Measure" in field else "Column"
    p = {"field": field, "queryRef": ref(field), "nativeQueryRef": field[kind]["Property"]}
    if display:
        p["displayName"] = display
    return p


def whole(n: int) -> dict:
    """Integer literal (e.g. label precision)."""
    return {"expr": {"Literal": {"Value": f"{n}L"}}}


def lit(value) -> dict:
    if isinstance(value, bool):
        return {"expr": {"Literal": {"Value": "true" if value else "false"}}}
    if isinstance(value, (int, float)):
        return {"expr": {"Literal": {"Value": f"{value}D"}}}
    return {"expr": {"Literal": {"Value": "'" + str(value).replace("'", "''") + "'"}}}


def solid(hex_color: str) -> dict:
    return {"solid": {"color": lit(hex_color)}}


def solid_from(measure_name: str) -> dict:
    """Colour taken from a measure that returns a hex code (format by field value)."""
    return {"solid": {"color": {"expr": measure(measure_name)}}}


def every_value(metadata: str | None = None) -> dict:
    sel: dict = {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}
    if metadata:
        sel["metadata"] = metadata
    return sel


def series_is(field: dict, value: str) -> dict:
    return {"data": [{"scopeId": {"Comparison": {"ComparisonKind": 0, "Left": field, "Right": {"Literal": {"Value": f"'{value}'"}}}}}]}


M = measure
FY, CHANNEL, MONTH_START = column("Date", "Fiscal Year"), column("SalesOrder", "Channel"), column("Date", "Month Start")


class Visual:
    def __init__(self, name, vtype, x, y, w, h, roles=None, title=None, subtitle=None, sort=None, objects=None,
                 container=None, title_color=None, title_size=None, subtitle_measure=None, subtitle_color_measure=None):
        self.name, self.vtype, self.pos = name, vtype, (x, y, w, h)
        self.roles, self.title, self.subtitle, self.sort = roles or {}, title, subtitle, sort
        self.objects, self.container = objects, container or {}
        self.title_color, self.title_size = title_color, title_size
        self.subtitle_measure, self.subtitle_color_measure = subtitle_measure, subtitle_color_measure

    def to_json(self, z: int) -> dict:
        x, y, w, h = self.pos
        v: dict = {"visualType": self.vtype}
        if self.roles:
            v["query"] = {"queryState": {r: {"projections": [projection(f) for f in fs]} for r, fs in self.roles.items()}}
            if self.sort:
                field, direction = self.sort
                v["query"]["sortDefinition"] = {"sort": [{"field": field, "direction": direction}], "isDefaultSort": False}
        if self.objects:
            v["objects"] = self.objects
        vco = dict(self.container)
        if self.title is not None:
            props = {"show": lit(True), "text": lit(self.title)}
            if self.title_color:
                props["fontColor"] = solid(self.title_color)
            if self.title_size:
                props["fontSize"] = lit(self.title_size)
            vco["title"] = [{"properties": props}]
        if self.subtitle or self.subtitle_measure:
            props = {"show": lit(True), "fontSize": lit(9)}
            props["text"] = {"expr": measure(self.subtitle_measure)} if self.subtitle_measure else lit(self.subtitle)
            props["fontColor"] = solid_from(self.subtitle_color_measure) if self.subtitle_color_measure else solid(MUTED)
            vco["subTitle"] = [{"properties": props}]
        if vco:
            v["visualContainerObjects"] = vco
        v["drillFilterOtherVisuals"] = True
        return {
            "$schema": f"{SCHEMA}/item/report/definition/visualContainer/{V_VISUAL}/schema.json",
            "name": self.name,
            "position": {"x": x, "y": y, "z": z, "width": w, "height": h, "tabOrder": z},
            "visual": v,
        }


NO_FRAME = {"background": [{"properties": {"show": lit(False)}}], "border": [{"properties": {"show": lit(False)}}],
            "title": [{"properties": {"show": lit(False)}}]}


def header(name: str, title: str, subtitle: str) -> Visual:
    paragraphs = [
        {"textRuns": [{"value": title, "textStyle": {"fontWeight": "bold", "fontSize": "16pt", "color": INK}}]},
        {"textRuns": [{"value": subtitle, "textStyle": {"fontSize": "10pt", "color": "#4B5563"}}]},
    ]
    return Visual(name, "textbox", 16, 4, 700, 74, objects={"general": [{"properties": {"paragraphs": paragraphs}}]},
                  container=NO_FRAME)


def slicer(name: str, field: dict, x: int) -> Visual:
    return Visual(name, "slicer", x, 10, 180, 64, {"Values": [field]},
                  objects={"data": [{"properties": {"mode": lit("Dropdown")}}]})


def kpi(name: str, label: str, value: str, x: int, units: int | None = None, precision: int = 1) -> Visual:
    """KPI tile: label, coloured delta vs prior year (subtitle), value with one decimal in its display unit."""
    labels = {"labelPrecision": whole(precision)}
    if units is not None:
        labels["labelDisplayUnits"] = lit(units)
    return Visual(name, "card", x, 86, 240, 104, {"Values": [M(value)]}, title=label, title_color=MUTED, title_size=10,
                  subtitle_measure=f"{value} Delta", subtitle_color_measure=f"{value} Color",
                  objects={"labels": [{"properties": labels}]})


def labels_on() -> dict:
    return {"labels": [{"properties": {"show": lit(True)}}]}


PAGES = [
    ("overview", "Executive overview", [
        header("header", "AdventureWorks · Sales performance",
               "Growth is real, profit is not: resellers bring 73% of sales at a margin near zero"),
        Visual("period", "card", 724, 16, 168, 56, {"Values": [M("KPI Period")]},
               objects={"labels": [{"properties": {"fontSize": lit(12), "color": solid(MUTED)}}]}, container=NO_FRAME),
        slicer("fy_slicer", FY, 900),
        slicer("channel_slicer", CHANNEL, 1088),
        kpi("kpi_sales", "Sales", "KPI Sales", 16),
        kpi("kpi_profit", "Gross profit", "KPI Profit", 268),
        kpi("kpi_margin", "Gross margin", "KPI Margin", 520),
        kpi("kpi_orders", "Orders", "KPI Orders", 772, units=1, precision=0),
        kpi("kpi_aov", "Average order value", "KPI AOV", 1024, units=1, precision=0),
        Visual("sales_trend", "lineChart", 16, 202, 736, 242,
               {"Category": [MONTH_START], "Y": [(M("Total Sales"), "Sales"), (M("Total Sales PY"), "Prior year")]},
               title="Monthly sales vs prior year", subtitle="FY2020 sales grew 52%, led by the Internet channel",
               sort=(MONTH_START, "Ascending"),
               objects={
                   "categoryAxis": [{"properties": {"axisType": lit("Scalar")}}],
                   "dataPoint": [{"properties": {"fill": solid(BLUE)}, "selector": {"metadata": "Sales.Total Sales"}},
                                 {"properties": {"fill": solid(GREY)}, "selector": {"metadata": "Sales.Total Sales PY"}}],
                   "lineStyles": [{"properties": {"strokeWidth": lit(3)}, "selector": {"metadata": "Sales.Total Sales"}},
                                  {"properties": {"strokeWidth": lit(2), "lineStyle": lit("dashed")},
                                   "selector": {"metadata": "Sales.Total Sales PY"}}],
                   "legend": [{"properties": {"show": lit(True)}}],
               }),
        Visual("fy_table", "tableEx", 764, 202, 500, 242,
               {"Values": [(FY, "FY"), (M("Total Sales"), "Sales"), (M("Sales YoY %"), "YoY"),
                           (M("Gross Margin %"), "Margin"), (M("Margin Change pp"), "Δ margin pp"), (M("Orders"), "Orders")]},
               title="Fiscal years at a glance", subtitle="Green: better than the prior year · red: worse",
               sort=(FY, "Ascending"),
               objects={
                   "values": [
                       {"properties": {"fontColor": solid_from("Growth Color")}, "selector": every_value("Sales.Sales YoY %")},
                       {"properties": {"fontColor": solid_from("Change Color")}, "selector": every_value("Sales.Margin Change pp")},
                   ],
                   "total": [{"properties": {"totals": lit(False)}}],
               }),
        Visual("margin_by_channel", "clusteredColumnChart", 16, 456, 616, 252,
               {"Category": [FY], "Series": [CHANNEL], "Y": [M("Gross Margin %")]},
               title="Gross margin by channel", subtitle="Internet earns about 41% every year; resellers, 73% of sales, earn close to zero",
               sort=(FY, "Ascending"),
               objects={
                   "dataPoint": [{"properties": {"fill": solid(BLUE)}, "selector": series_is(CHANNEL, "Internet")},
                                 {"properties": {"fill": solid(ORANGE)}, "selector": series_is(CHANNEL, "Reseller")}],
                   **labels_on(),
                   "legend": [{"properties": {"show": lit(True)}}],
               }),
        Visual("margin_by_country", "clusteredBarChart", 648, 456, 616, 252,
               {"Category": [column("SalesTerritory", "Country")], "Y": [M("Gross Margin %")], "Tooltips": [M("Reseller Share %")]},
               title="Gross margin by country",
               subtitle="Orange: more than half of sales through resellers. Margin follows the channel mix",
               sort=(M("Gross Margin %"), "Descending"),
               objects={"dataPoint": [{"properties": {"fill": solid_from("Channel Mix Color")}, "selector": every_value()}],
                        **labels_on()}),
    ]),
    ("drilldown", "Where the margin goes", [
        header("header2", "Where the margin goes",
               "21,829 order lines were sold below cost, all of them to resellers"),
        slicer("fy_slicer2", FY, 900),
        slicer("category_slicer", column("Product", "Category"), 1088),
        Visual("subcategory_table", "tableEx", 16, 86, 736, 338,
               {"Values": [(column("Product", "Category"), "Category"), (column("Product", "Subcategory"), "Subcategory"),
                           (M("Total Sales"), "Sales"), (M("Gross Profit"), "Gross profit"),
                           (M("Gross Margin %"), "Margin"), (M("Reseller Share %"), "Via resellers")]},
               title="Subcategories ranked by gross margin",
               subtitle="Red: sold at a loss. Jerseys, touring frames and caps lose money; bikes earn 11%",
               sort=(M("Gross Margin %"), "Ascending"),
               objects={
                   "values": [{"properties": {"fontColor": solid_from("Margin Color")}, "selector": every_value("Sales.Gross Margin %")},
                              {"properties": {"fontColor": solid_from("Margin Color")}, "selector": every_value("Sales.Gross Profit")}],
                   "total": [{"properties": {"totals": lit(False)}}],
               }),
        Visual("top_products", "clusteredBarChart", 764, 86, 500, 338,
               {"Category": [column("Product", "Product")], "Y": [(M("Gross Profit Top 10"), "Gross profit")]},
               title="Top 10 products by gross profit", subtitle="Mountain-200 and Road-150 bikes lead",
               sort=(M("Gross Profit Top 10"), "Descending"),
               objects={"dataPoint": [{"properties": {"fill": solid(BLUE)}}],
                        "labels": [{"properties": {"show": lit(True), "fontSize": lit(9)}}],
                        "valueAxis": [{"properties": {"show": lit(False)}}],
                        "categoryAxis": [{"properties": {"fontSize": lit(9)}}]}),
        Visual("subcategory_scatter", "scatterChart", 16, 436, 736, 272,
               {"Category": [column("Product", "Subcategory")], "X": [(M("Total Sales"), "Sales")],
                "Y": [(M("Gross Margin %"), "Gross margin")], "Size": [M("Units")]},
               title="Subcategories: sales vs gross margin",
               subtitle="Orange: sold at a loss · bubble size = units · the biggest sellers sit at low margins",
               objects={"dataPoint": [{"properties": {"fill": solid_from("Margin Point Color")}, "selector": every_value()}]}),
        Visual("loss_lines", "card", 764, 436, 500, 96, {"Values": [M("Loss Lines")]},
               title="Order lines sold below cost (all of them to resellers)", title_color=MUTED, title_size=10,
               objects={"labels": [{"properties": {"color": solid(RED), "labelDisplayUnits": lit(1), "labelPrecision": whole(0)}}]}),
        Visual("loss_by_reseller_type", "clusteredBarChart", 764, 544, 500, 164,
               {"Category": [column("Reseller", "Business Type")], "Y": [(M("Loss Amount"), "Loss")]},
               title="Loss on below-cost lines by reseller type", subtitle="Every reseller type loses money on some lines",
               sort=(M("Loss Amount"), "Descending"),
               objects={"dataPoint": [{"properties": {"fill": solid(ORANGE)}}], **labels_on(),
                        "valueAxis": [{"properties": {"show": lit(False)}}]}),
    ]),
]


def build_report() -> int:
    if REPORT_DIR.exists():
        shutil.rmtree(REPORT_DIR)
    d = REPORT_DIR / "definition"
    write(REPORT_DIR / "definition.pbir", json.dumps({
        "$schema": f"{SCHEMA}/item/report/definitionProperties/2.0.0/schema.json",
        "version": "4.0",
        "datasetReference": {"byPath": {"path": f"../{NAME}.SemanticModel"}},
    }, indent=2))
    write(d / "version.json", json.dumps({
        "$schema": f"{SCHEMA}/item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"}, indent=2))
    version_at_import = {"visual": V_VISUAL, "page": V_PAGE, "report": V_REPORT}
    write(d / "report.json", json.dumps({
        "$schema": f"{SCHEMA}/item/report/definition/report/{V_REPORT}/schema.json",
        "themeCollection": {
            "baseTheme": {"name": BASE_THEME, "reportVersionAtImport": version_at_import, "type": "SharedResources"},
            "customTheme": {"name": CUSTOM_THEME, "reportVersionAtImport": version_at_import, "type": "RegisteredResources"},
        },
        "resourcePackages": [
            {"name": "SharedResources", "type": "SharedResources", "items": [
                {"name": BASE_THEME, "path": f"BaseThemes/{BASE_THEME}.json", "type": "BaseTheme"}]},
            {"name": "RegisteredResources", "type": "RegisteredResources", "items": [
                {"name": CUSTOM_THEME, "path": CUSTOM_THEME, "type": "CustomTheme"}]},
        ],
    }, indent=2))
    static = REPORT_DIR / "StaticResources"
    (static / "SharedResources" / "BaseThemes").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(THEME_SOURCE, static / "SharedResources" / "BaseThemes" / f"{BASE_THEME}.json")
    (static / "RegisteredResources").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(THEME_FILE, static / "RegisteredResources" / CUSTOM_THEME)

    write(d / "pages" / "pages.json", json.dumps({
        "$schema": f"{SCHEMA}/item/report/definition/pagesMetadata/1.0.0/schema.json",
        "pageOrder": [p[0] for p in PAGES],
        "activePageName": PAGES[0][0],
    }, indent=2))
    count = 0
    for page_name, display, visuals in PAGES:
        write(d / "pages" / page_name / "page.json", json.dumps({
            "$schema": f"{SCHEMA}/item/report/definition/page/{V_PAGE}/schema.json",
            "name": page_name, "displayName": display, "displayOption": "FitToPage", "height": 720, "width": 1280,
        }, indent=2))
        for z, vis in enumerate(visuals):
            write(d / "pages" / page_name / "visuals" / vis.name / "visual.json",
                  json.dumps(vis.to_json(z * 1000), indent=2, ensure_ascii=False))
            count += 1
    write(ROOT / f"{NAME}.pbip", json.dumps({
        "$schema": f"{SCHEMA}/pbip/pbipProperties/1.0.0/schema.json",
        "version": "1.0",
        "artifacts": [{"report": {"path": f"{NAME}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    }, indent=2))
    return count


if __name__ == "__main__":
    n_measures = build_model()
    n_visuals = build_report()
    print(f"semantic model: {len(TABLES)} tables, {len(RELATIONSHIPS)} relationships, {n_measures} measures")
    print(f"report: {len(PAGES)} pages, {n_visuals} visuals, theme {CUSTOM_THEME}")
