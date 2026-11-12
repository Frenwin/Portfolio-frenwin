# Week 1 · Data Engineer — Make data reliable

> **Purpose of this week:** prove I can build the foundation everything else depends on. Before anyone can analyse, predict or build AI, data has to arrive on time, in the right shape, and be correct.

[← Portfolio home](../README.md) · [Next: Week 2 · Data Analyst →](../02-data-analyst/)

## Why this week comes first

Every later week reads from data. If a pipeline double-counts orders or silently drops rows, the dashboard in Week 2 is wrong, the experiment in Week 3 draws the wrong conclusion, and the AI in Week 4 answers from bad facts. Data engineering is the part nobody sees when it works and everybody feels when it breaks.

## The question this week answers

**"Is the data correct, complete and on time?"** Each project answers it for a different way that data moves:

| Data arrives… | Project | Example in industry |
| --- | --- | --- |
| as daily files or exports | **DE-1** batch ELT | nightly sales exports loaded into a warehouse |
| as very large files | **DE-2** lakehouse | years of trip or transaction history |
| as a continuous stream of events | **DE-3** streaming | ride requests, payments, clicks |
| as changes inside a live database | **DE-4** change data capture | copying an app's database without slowing it down |

## Projects

| # | Project | What it proves | Stack | Status |
| --- | --- | --- | --- | :---: |
| DE-1 | [**Batch ELT to a star-schema warehouse**](de-01-elt-airflow-dbt/) | An orchestrated, idempotent pipeline with 70 data tests, an SCD2 dimension and CI | Airflow, dbt, PostgreSQL, Docker, GitHub Actions | ✅ |
| DE-2 | [**Lakehouse with bronze/silver/gold layers**](de-02-lakehouse-spark-delta/) | 9.5M taxi trips validated, de-duplicated and partitioned on S3 storage; idempotent month re-loads, time travel | PySpark, Delta Lake, SeaweedFS (S3) | ✅ |
| DE-3 | [**Real-time ride event streaming**](de-03-realtime-kafka-spark/) | Exactly-once results from a faulty stream: duplicates, late events, malformed messages, fraud alerts in seconds | Kafka, Spark Structured Streaming, PostgreSQL, Grafana | ✅ |
| DE-4 | Change Data Capture | Inserts, updates and deletes replicated from an operational database | PostgreSQL, Debezium, Kafka Connect | ⬜ |

## Skills covered

| Skill | Where it is shown |
| --- | --- |
| Orchestration and scheduling | DE-1 |
| Dimensional modeling (star schema, SCD Type 2) | DE-1 |
| Data quality testing and freshness checks | DE-1, DE-3 |
| Idempotent and incremental loading | DE-1, DE-2 |
| Distributed processing and lakehouse formats | DE-2, DE-3 |
| Streaming and change data capture | DE-3, DE-4 |
| Docker, CI/CD, reproducible setup | all |

## What this week hands to the next

The Olist warehouse from DE-1 (`marts.fct_orders`, `dim_customers`, …) is clean, tested and documented, so Week 2 can start analysing instead of cleaning.
