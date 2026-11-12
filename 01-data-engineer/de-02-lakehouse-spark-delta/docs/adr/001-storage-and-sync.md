# ADR-001: Object storage and the silver sync strategy

**Status:** Accepted · **Date:** 2026-11-12

## Context

The lakehouse must store Delta tables on S3-compatible object storage, run on a laptop with one command, and let any month be re-processed without duplicating or losing trips.

## Decision 1: SeaweedFS as the local S3

MinIO was the planned choice, but its community Docker images are no longer published: `minio/minio` and `quay.io/minio/minio` both refused pulls on 2026-11-12. The options were:

| Option | Verdict |
| --- | --- |
| `bitnamilegacy/minio` | Pulls, but it is a frozen image that receives no fixes |
| LocalStack | Works, but emulates all of AWS and is heavy for one bucket |
| **SeaweedFS** (`chrislusf/seaweedfs:4.52`) | Actively released, single container, S3 API on port 8333 |

Spark talks to it through the standard `s3a://` connector (`hadoop-aws` 3.3.4, path-style access), so the same code would run against AWS S3 by changing four settings.

## Decision 2: Two pruned MERGEs instead of one MERGE with `whenNotMatchedBySource`

Silver must end up equal to the latest source for each month: new trips inserted, withdrawn trips deleted, unchanged trips untouched.

The first version used a single `MERGE … WHEN NOT MATCHED BY SOURCE THEN DELETE`. It was correct, but each month took longer than the last (45 s, 250 s, 418 s for January to March), because a not-matched-by-source clause forces Delta to scan **every** target row, not just the month being loaded.

The current version splits the work so both steps restrict the target to the month's partitions:

1. an insert-only `MERGE` (Delta has an optimised path for it), and
2. an anti-join to find trips that disappeared, followed by a `MERGE … WHEN MATCHED THEN DELETE` on those ids only.

Measured effect is in the README results.

## Consequences

- Re-running a month is a no-op: 0 inserted, 0 deleted.
- Delta's default S3 log store assumes a single writer; concurrent writers to the same table would need a DynamoDB-backed log store, which is out of scope here.
