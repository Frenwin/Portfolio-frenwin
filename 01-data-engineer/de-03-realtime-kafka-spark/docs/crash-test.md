# Crash test

The Spark job was killed with `docker kill` (no graceful shutdown) 60 s into a 600 events/s run, kept down for 18 s (04:12:39 to 04:12:57 UTC), then restarted from its checkpoint. Any micro-batch not yet committed when it died is re-run on restart, so the sink has to absorb rows it may already have written.

## Correctness

| Check | Sent | Result |
| --- | ---: | --- |
| Unique valid rides stored exactly once | 89,342 expected | 89,342 stored (exact match) |
| Duplicate re-sends | 886 | 0 extra rows (deduplicated) |
| Late events (20-90 s) | 1,878 | 1,878 kept |
| Too-late events (5-10 min, beyond watermark) | 396 | 0 kept (dropped) |
| Malformed messages | 286 | 286 in `rejected_events` |
| Fraud bursts (6 rides in 15 s) | 4 | 4 detected, 0 false alerts |

## Speed

| Metric | Value |
| --- | ---: |
| End-to-end latency p50 / p95 / p99 (produced -> stored) | 4.82 / 37.16 / 43.17 s |
| Fraud detection latency p50 / max (5th ride -> flag) | 3.15 / 9.95 s |
| Rides stored per second | 575.1 |
| Micro-batches (avg / max rows) | 34 (2,690 / 19,177) |

Real-time and watermark-final per-minute counts agree on 48 of 48 zone-minutes.

The p95/p99 latency and the 19,177-row batch reflect the 18 s outage and the catch-up afterwards, not steady state; see [results.md](results.md) for the steady-state run.
