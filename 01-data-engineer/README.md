# Week 1 — Data Engineer (16–22 Nov 2026)

Pipelines that move, model, and validate data the way production teams do: batch ELT, lakehouse, streaming, and CDC.

| # | Date | Project | Stack | Status |
| --- | --- | --- | --- | --- |
| DE-1 | 10 Nov | [`de-01-elt-airflow-dbt`](de-01-elt-airflow-dbt/) — Batch ELT into a tested star schema with an SCD2 customer dimension | Airflow, dbt, PostgreSQL, Docker, GitHub Actions | Done |
| DE-2 | 18 Nov | `de-02-lakehouse-spark-delta` — Bronze/silver/gold lakehouse on NYC taxi data | PySpark, Delta Lake, MinIO | Planned |
| DE-3 | 19–20 Nov | `de-03-realtime-kafka-spark` — Real-time event aggregation with alerting | Kafka, Spark Structured Streaming, PostgreSQL, Grafana | Planned |
| DE-4 | 21 Nov | `de-04-cdc-debezium` — Replicate inserts, updates and deletes from an OLTP database | PostgreSQL, Debezium, Kafka Connect | Planned |

Details for each project: [ROADMAP.md — Minggu 1](../ROADMAP.md#3-minggu-1--data-engineer-1622-nov).
