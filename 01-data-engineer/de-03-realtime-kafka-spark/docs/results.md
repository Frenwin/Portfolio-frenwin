# Measured run

Run `bench2`: 181,810 messages in 192.2 s (946.1/s), Spark local mode in Docker on a laptop.

## Correctness

| Check | Sent | Result |
| --- | ---: | --- |
| Unique valid rides stored exactly once | 178,736 expected | 178,736 stored (exact match) |
| Duplicate re-sends | 1,762 | 0 extra rows (deduplicated) |
| Late events (20-90 s) | 3,771 | 3,771 kept |
| Too-late events (5-10 min, beyond watermark) | 754 | 0 kept (dropped) |
| Malformed messages | 558 | 558 in `rejected_events` |
| Fraud bursts (6 rides in 15 s) | 8 | 8 detected, 0 false alerts |

## Speed

| Metric | Value |
| --- | ---: |
| End-to-end latency p50 / p95 / p99 (produced -> stored) | 4.05 / 6.36 / 7.57 s |
| Fraud detection latency p50 / max (5th ride -> flag) | 3.64 / 5.39 s |
| Rides stored per second | 939.2 |
| Micro-batches (avg / max rows) | 49 (3,694 / 4,987) |

Real-time and watermark-final per-minute counts agree on 48 of 48 zone-minutes.
