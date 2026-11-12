# ADR-001: Exactly-once results on an at-least-once stream

**Status:** Accepted · **Date:** 2026-11-12

## Context

Spark Structured Streaming with a checkpoint replays a micro-batch if the job crashes after writing but before committing the offset. The producer also re-sends events on retry. Either way the same ride can arrive more than once, and a dashboard that counts it twice is wrong.

## Decision

Make every write idempotent and derive aggregates only from rows that were really new.

| Layer | Mechanism |
| --- | --- |
| Spark | `withWatermark("event_ts", "2 minutes")` + `dropDuplicatesWithinWatermark("event_id")` removes re-sends inside the watermark and drops events older than it |
| Rides table | `INSERT … ON CONFLICT (event_id) DO NOTHING RETURNING …` |
| Aggregates | Per-minute zone demand and per-user activity are incremented from the `RETURNING` rows in the same statement, so a replayed batch adds nothing |
| Rejected events | Keyed by Kafka `(partition, offset)` |
| Final windows | Spark emits each window once after the watermark passes (append mode); the upsert overwrites, so a replay rewrites the same value |

Fraud detection is a threshold on the per-user, per-minute counter: the moment it reaches 5, `flagged_at` is set once and never moved.

## Alternatives considered

- **Spark-only running totals in update mode.** Spark would emit changed totals every batch, but writing them still needs an idempotent upsert on replay, and the fraud flag would depend on Spark state that is lost if the checkpoint is reset. Keeping the counters next to the rides they were derived from makes them auditable with one SQL query. Spark is still used for the final per-minute windows (append mode), where it fits best.
- **Kafka transactions end to end.** Would need a transactional sink; PostgreSQL via `foreachBatch` is not one.

## Consequences

- The real-time table shows a minute as soon as its first rides land; the final table shows it only after the watermark (about 2-3 minutes later), but never changes afterwards. The report checks that both agree.
- `user_activity_1m` grows with every user-minute; production would expire rows older than an hour.
