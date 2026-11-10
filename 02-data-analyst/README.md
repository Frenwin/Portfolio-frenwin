# Week 2 · Data Analyst — Explain what happened

> **Purpose of this week:** prove I can turn clean data into answers a business person can act on: the right metric, a clear chart, and a recommendation with an estimated impact.

[← Week 1 · Data Engineer](../01-data-engineer/) · [Portfolio home](../README.md) · [Next: Week 3 · Data Scientist →](../03-data-scientist/)

## Why this week matters

A warehouse full of correct data is still useless if nobody can read it. Analysts translate data into decisions: they choose which numbers matter, notice when something changes, and explain it in plain language. Good analysis is mostly asking the right question and defining the metric precisely.

## The question this week answers

**"What is happening in the business, and why?"** Each project answers it for a different audience:

| Audience | Project | What they get |
| --- | --- | --- |
| Interviewer or analytics lead | **DA-1** SQL case study | Business questions answered directly in SQL |
| Executives | **DA-2** sales dashboard | A two-page dashboard: overview and drill-down |
| Product team | **DA-3** funnel & cohort | Where users drop off and who comes back |
| Marketing / CRM team | **DA-4** segmentation | Customer segments and which campaign each should get |

## Projects

| # | Project | What it proves | Stack | Status |
| --- | --- | --- | --- | :---: |
| DA-1 | SQL business case study | 10–12 business questions answered with CTEs and window functions | BigQuery SQL | ⬜ |
| DA-2 | Executive sales dashboard | A star-schema model, DAX measures (YoY, YTD, margin) and a clear layout | Power BI, DAX | ⬜ |
| DA-3 | Product funnel & cohort retention | Funnel drop-off and weekly retention on real GA4 event data | BigQuery, GA4 schema | ⬜ |
| DA-4 | Customer segmentation + insight deck | RFM segments, profiles, and a recommendation deck with estimated value | Python, scikit-learn, slides | ⬜ |

## Skills covered

| Skill | Where it is shown |
| --- | --- |
| Advanced SQL (CTEs, window functions) | DA-1, DA-3 |
| Metric definition and KPI design | DA-1, DA-2 |
| BI dashboards and data modeling | DA-2 |
| Product analytics (funnel, cohort, retention) | DA-3 |
| Segmentation and storytelling for stakeholders | DA-4 |

## What this week hands to the next

Clear metric definitions and observed patterns, such as late deliveries and low review scores moving together. Week 3 moves from describing patterns to testing changes, predicting outcomes and measuring what actually causes a result.
