# DAX validation

The core measures were run inside Power BI Desktop's own engine (ADOMD.NET against the local Analysis Services instance, after a full refresh) and compared with the numbers computed independently in pandas ([expected-values.md](expected-values.md)). **Every value matches.**

## By fiscal year

| Fiscal year | Measure | DAX in Power BI | pandas | Match |
| --- | --- | ---: | ---: | :---: |
| FY2018 | Total Sales | 23,860,891.17 | 23,860,891.17 | ✓ |
| FY2018 | Gross Margin % | 12.72% | 12.72% | ✓ |
| FY2018 | Orders | 3,198 | 3,198 | ✓ |
| FY2019 | Total Sales | 34,070,108.50 | 34,070,108.50 | ✓ |
| FY2019 | Sales YoY % | 42.79% | 42.79% | ✓ |
| FY2019 | Profit YoY % | 22.14% | 22.14% | ✓ |
| FY2019 | Margin Change pp | −1.84 | −1.84 | ✓ |
| FY2020 | Total Sales | 51,878,274.54 | 51,878,274.54 | ✓ |
| FY2020 | Gross Profit | 5,807,432.52 | 5,807,432.52 | ✓ |
| FY2020 | Orders | 23,519 | 23,519 | ✓ |
| FY2020 | Avg Order Value | 2,205.80 | 2,205.80 | ✓ |
| FY2020 | Sales YoY % | 52.27% | 52.27% | ✓ |
| FY2020 | Profit YoY % | 56.62% | 56.62% | ✓ |
| FY2020 | Margin Change pp | +0.31 | +0.31 | ✓ |

## By channel and fiscal year

| Fiscal year | Channel | Total Sales | Gross Margin % | Orders | Match |
| --- | --- | ---: | ---: | ---: | :---: |
| FY2018 | Internet | 7,572,449.40 | 40.21% | 2,459 | ✓ |
| FY2018 | Reseller | 16,288,441.77 | −0.06% | 739 | ✓ |
| FY2019 | Internet | 6,148,437.98 | 41.55% | 3,483 | ✓ |
| FY2019 | Reseller | 27,921,670.52 | 4.13% | 1,255 | ✓ |
| FY2020 | Internet | 15,637,789.84 | 41.45% | 21,717 | ✓ |
| FY2020 | Reseller | 36,240,484.70 | −1.86% | 1,802 | ✓ |

## All years and diagnostics

| Measure | DAX in Power BI | pandas | Match |
| --- | ---: | ---: | :---: |
| Total Sales | 109,809,274.20 | 109,809,274.20 | ✓ |
| Gross Profit | 12,551,366.25 | 12,551,366.25 | ✓ |
| Orders | 31,455 | 31,455 | ✓ |
| Discount | 527,507.89 | 527,507.89 | ✓ |
| Loss Lines (sum of years) | 21,829 | 21,829 | ✓ |
| Loss Amount | 3,320,274.60 | 3,320,274.60 | ✓ |
| Reseller Share % | 73.26% | 73.3% | ✓ |
| Sales FYTD on 30 Jun 2020 | 51,878,274.54 | FY2020 total | ✓ |
| Top product by profit, FY2020 | Mountain-200 Black, 38: 540,713.70 | same | ✓ |

## How to re-run

With the project open in Power BI Desktop, the engine listens on a local port (`%LOCALAPPDATA%\Microsoft\Power BI Desktop\AnalysisServicesWorkspaces\*\Data\msmdsrv.port.txt`). Any DAX client (DAX Studio, or ADOMD.NET from a script) can run the `EVALUATE` statements at the end of [`model/measures.dax`](../model/measures.dax) against it.
