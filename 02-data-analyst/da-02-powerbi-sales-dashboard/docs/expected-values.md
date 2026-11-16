# Expected values

Computed with pandas straight from the workbook by `analysis/expected_values.py`, independently of Power BI. Every card and table in the dashboard must show these numbers; if a DAX measure disagrees, the measure is wrong.

## By fiscal year (July-June)

| Fiscal Year | Total Sales | Gross Profit | Gross Margin % | Orders | Avg Order Value | Units | Sales YoY % | Profit YoY % | Margin change pp |
|---|---|---|---|---|---|---|---|---|---|
| FY2018 | 23,860,891.17 | 3,035,933.57 | 12.72 | 3,198 | 7,461.19 | 24,349 |  |  |  |
| FY2019 | 34,070,108.50 | 3,708,000.16 | 10.88 | 4,738 | 7,190.82 | 83,339 | 42.79 | 22.14 | -1.84 |
| FY2020 | 51,878,274.54 | 5,807,432.52 | 11.19 | 23,519 | 2,205.80 | 167,088 | 52.27 | 56.62 | 0.31 |

## All years

| Total Sales | Gross Profit | Gross Margin % | Orders | Avg Order Value | Units | Discount |
|---|---|---|---|---|---|---|
| 109,809,274.20 | 12,551,366.25 | 11.43 | 31,455 | 3,491.00 | 274,776 | 527,507.89 |

## By channel and fiscal year

| Fiscal Year | Channel | Total Sales | Gross Profit | Gross Margin % | Orders | Avg Order Value | Units |
|---|---|---|---|---|---|---|---|
| FY2018 | Internet | 7,572,449.40 | 3,045,168.62 | 40.21 | 2,459 | 3,079.48 | 2,459 |
| FY2018 | Reseller | 16,288,441.77 | -9,235.05 | -0.06 | 739 | 22,041.19 | 21,890 |
| FY2019 | Internet | 6,148,437.98 | 2,554,555.40 | 41.55 | 3,483 | 1,765.27 | 4,380 |
| FY2019 | Reseller | 27,921,670.52 | 1,153,444.77 | 4.13 | 1,255 | 22,248.34 | 78,959 |
| FY2020 | Internet | 15,637,789.84 | 6,481,159.63 | 41.45 | 21,717 | 720.07 | 53,559 |
| FY2020 | Reseller | 36,240,484.70 | -673,727.11 | -1.86 | 1,802 | 20,111.26 | 113,529 |

## By category (all years)

| Category | Total Sales | Gross Profit | Gross Margin % | Orders | Avg Order Value | Units |
|---|---|---|---|---|---|---|
| Bikes | 94,620,526.21 | 10,515,096.61 | 11.11 | 18,358 | 5,154.18 | 90,220 |
| Components | 11,799,076.66 | 1,032,966.48 | 8.75 | 2,646 | 4,459.21 | 49,027 |
| Clothing | 2,117,613.45 | 368,836.00 | 17.42 | 9,871 | 214.53 | 73,598 |
| Accessories | 1,272,057.89 | 634,467.16 | 49.88 | 19,523 | 65.16 | 61,931 |

## By country (all years)

| Country | Total Sales | Gross Profit | Gross Margin % | Orders |
|---|---|---|---|---|
| United States | 62,997,590.72 | 4,444,138.59 | 7.05 | 12,041 |
| Canada | 16,355,770.46 | 1,008,148.59 | 6.16 | 4,067 |
| Australia | 10,655,335.96 | 3,577,134.19 | 33.57 | 6,843 |
| United Kingdom | 7,670,721.04 | 1,396,872.69 | 18.21 | 3,219 |
| France | 7,251,555.65 | 1,048,955.12 | 14.47 | 2,672 |
| Germany | 4,878,300.38 | 1,076,117.07 | 22.06 | 2,613 |

## Top 10 products by gross profit, FY2020

| Rank | Product | Total Sales | Gross Profit |
|---|---|---|---|
| 1 | Mountain-200 Black, 38 | 2,525,104.06 | 540,713.70 |
| 2 | Mountain-200 Black, 42 | 2,219,585.58 | 533,166.77 |
| 3 | Mountain-200 Silver, 38 | 2,079,781.95 | 510,413.77 |
| 4 | Mountain-200 Black, 46 | 1,888,678.54 | 493,971.38 |
| 5 | Mountain-200 Silver, 46 | 1,871,448.70 | 493,189.07 |
| 6 | Mountain-200 Silver, 42 | 1,863,508.07 | 476,389.10 |
| 7 | Touring-1000 Blue, 54 | 731,432.68 | 126,802.01 |
| 8 | Road-350-W Yellow, 44 | 680,396.00 | 108,830.72 |
| 9 | Touring-1000 Blue, 50 | 1,057,096.64 | 104,210.57 |
| 10 | Touring-1000 Blue, 46 | 1,572,649.15 | 96,639.00 |

## Subcategories sold at a loss (all years)

| Category | Subcategory | Total Sales | Gross Profit | Gross Margin % |
|---|---|---|---|---|
| Clothing | Jerseys | 752,259.39 | -92,921.27 | -12.35 |
| Components | Touring Frames | 1,642,327.69 | -5,573.41 | -0.34 |
| Clothing | Caps | 51,229.45 | -1,203.20 | -2.35 |

## Order lines sold below cost

21,829 lines (18.0%) lost a total of 3,320,274.60; by channel: {'Internet': 0, 'Reseller': 21829}.
