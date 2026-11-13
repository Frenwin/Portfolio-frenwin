# ADR-001: Log-based CDC with Debezium, a mirror and a history

**Status:** Accepted · **Date:** 2026-11-13

## Context

Analytics needs the shop's operational data without slowing the shop down, and it needs more than the current state: questions like "how long do orders sit in *paid*?" require every status an order passed through, which the operational table overwrites.

## Options

| Approach | Load on source | Sees deletes | Sees every intermediate change | Latency |
| --- | --- | --- | --- | --- |
| Nightly full export | High, once a day | Only by diffing | No | 24 h |
| Query-based incremental (`WHERE updated_at > :last`) | A query per poll | No | No, only the latest state between polls | Poll interval |
| Triggers writing an audit table | On every write, inside the transaction | Yes | Yes | Low, but slows the application |
| **Log-based CDC (Debezium reading the WAL)** | Reads the log the database writes anyway | Yes | Yes | Seconds |

## Decision

Debezium's PostgreSQL connector reads the write-ahead log through the built-in `pgoutput` plugin and publishes one Kafka topic per table. Two consumers read those topics:

1. **Debezium JDBC sink** keeps a mirror of current state in the replica database (upserts by primary key, deletes applied, new columns added automatically). Configuration only, no code.
2. **`cdc/history.py`** keeps every status change of every order as an SCD Type 2 history, which the mirror cannot.

Details that matter:

- **Least privilege.** Debezium logs in as a role with `REPLICATION` and `SELECT` only; the publication is created by the schema owner, so the connector never needs ownership.
- **`REPLICA IDENTITY FULL` on `orders`.** Update events then include the previous row, so the history consumer can ignore updates that did not change the status.
- **WAL order, not timestamps.** The history is ordered by LSN. Application timestamps and commit timestamps come from different clocks; a test reproduces a delete that would sort before its own insert if ordered by time.
- **Idempotency.** The history key is `(order_id, lsn)` and offsets are committed after the database commit, so a consumer restart re-reads events without duplicating them.

## Consequences

- A replication slot holds WAL until it is consumed; if Debezium is down for long, the source disk grows. Production needs an alert on slot lag (`pg_replication_slots`).
- Adding a column with a `DEFAULT` in PostgreSQL does not rewrite existing rows, so no change events are emitted for them; the replica only learns the value when a row next changes. Backfills need an explicit update.
- The mirror has no foreign keys: rows can briefly arrive out of parent-child order.
