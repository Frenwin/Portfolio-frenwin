# ADR-001: Stack and loading strategy

**Status:** Accepted · **Date:** 2026-11-10

## Context

The project must run on a laptop with one command, be reproducible by a reviewer without a cloud account, and still use the tools data teams run in production. The source is nine CSV exports (1.55M rows) that arrive as full snapshots.

## Decision

| Concern | Choice | Alternatives considered |
| --- | --- | --- |
| Orchestration | Airflow 2.10.5, LocalExecutor, in Docker Compose | Prefect, Dagster: smaller footprint, but Airflow is the most established orchestrator in data teams |
| Warehouse | PostgreSQL 16 | BigQuery (needs a GCP project), DuckDB (no server, less like production) |
| Transformation | dbt-core 1.12 | Plain SQL scripts: no dependency graph, tests or docs |
| Loading | Truncate + `COPY` inside one transaction, columns as `text` | pandas `to_sql` (row inserts, infers types silently); append-only (not idempotent) |
| dbt runtime | Separate virtualenv inside the Airflow image | Same environment (dependency conflicts), `DockerOperator` (needs the Docker socket) |
| Customer history | SCD2 derived from order history | dbt snapshot (would hold one version on a static export) |

## Consequences

- `docker compose up -d --build` is the only setup step; CI runs the same loader and dbt project against a service container.
- Full reloads are cheap at this size (≈30 s end to end) but would not scale to large sources; that is addressed by the CDC project (DE-4).
- The profile reads connection settings from environment variables, so adding a BigQuery target later does not change the models.
