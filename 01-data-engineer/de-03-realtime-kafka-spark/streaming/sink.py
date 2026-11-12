"""Idempotent PostgreSQL sinks for Spark foreachBatch.

Spark guarantees each micro-batch is delivered at least once; if a batch is replayed after a
failure, these writes must not double-count. The rides sink does it in one statement:

  1. insert rides ON CONFLICT (event_id) DO NOTHING ... RETURNING only the rows really inserted
  2. add those rows - and only those - to per-minute zone demand and per-user activity
  3. flag a user the moment their rides in one minute reach FRAUD_MIN_RIDES

A replayed batch inserts nothing in step 1, so steps 2 and 3 add nothing either.
"""

from __future__ import annotations

import os

import psycopg2
from psycopg2.extras import execute_values
from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from streaming.events import FRAUD_MIN_RIDES

ISO = "yyyy-MM-dd'T'HH:mm:ss.SSSXXX"

RIDES_SQL = f"""
WITH incoming (event_id, run_id, event_ts, produced_at, batch_id, user_id, driver_id,
               zone, payment_method, distance_km, fare_idr) AS (VALUES %s),
new AS (
    INSERT INTO rides (event_id, run_id, event_ts, produced_at, batch_id, user_id, driver_id,
                       zone, payment_method, distance_km, fare_idr)
    SELECT * FROM incoming
    ON CONFLICT (event_id) DO NOTHING
    RETURNING event_ts, user_id, zone, distance_km, fare_idr
),
zone_upsert AS (
    INSERT INTO zone_demand_1m AS t (window_start, zone, trips, revenue_idr, distance_km)
    SELECT date_trunc('minute', event_ts), zone, count(*), sum(fare_idr), sum(distance_km)
    FROM new GROUP BY 1, 2
    ON CONFLICT (window_start, zone) DO UPDATE SET
        trips       = t.trips + EXCLUDED.trips,
        revenue_idr = t.revenue_idr + EXCLUDED.revenue_idr,
        distance_km = t.distance_km + EXCLUDED.distance_km,
        updated_at  = clock_timestamp()
),
activity_upsert AS (
    INSERT INTO user_activity_1m AS t (window_start, user_id, rides, fare_idr, flagged_at)
    SELECT date_trunc('minute', event_ts), user_id, count(*), sum(fare_idr),
           CASE WHEN count(*) >= {int(FRAUD_MIN_RIDES)} THEN clock_timestamp() END
    FROM new GROUP BY 1, 2
    ON CONFLICT (window_start, user_id) DO UPDATE SET
        rides      = t.rides + EXCLUDED.rides,
        fare_idr   = t.fare_idr + EXCLUDED.fare_idr,
        flagged_at = COALESCE(
            t.flagged_at,
            CASE WHEN t.rides + EXCLUDED.rides >= {int(FRAUD_MIN_RIDES)} THEN clock_timestamp() END
        )
)
SELECT count(*) FROM new
"""
RIDES_TEMPLATE = "(%s, %s, %s::timestamptz, %s::timestamptz, %s::bigint, %s, %s, %s, %s, %s::numeric, %s::integer)"

REJECTED_SQL = """
INSERT INTO rejected_events (kafka_partition, kafka_offset, kafka_ts, reason, raw_value)
VALUES %s
ON CONFLICT (kafka_partition, kafka_offset) DO NOTHING
RETURNING 1
"""

FINAL_SQL = """
INSERT INTO zone_demand_final AS t (window_start, window_end, zone, trips, revenue_idr)
VALUES %s
ON CONFLICT (window_start, zone) DO UPDATE SET
    trips = EXCLUDED.trips, revenue_idr = EXCLUDED.revenue_idr, finalized_at = clock_timestamp()
RETURNING 1
"""


def connect():
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5435")),
        dbname=os.getenv("PGDATABASE", "streaming"),
        user=os.getenv("PGUSER", "streaming"),
        password=os.getenv("PGPASSWORD", "streaming"),
    )


def _record_batch(cur, query: str, batch_id: int, rows_in: int, rows_written: int) -> None:
    cur.execute(
        "INSERT INTO stream_batches (query, batch_id, rows_in, rows_written) VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (query, batch_id) DO NOTHING",
        (query, batch_id, rows_in, rows_written),
    )


def upsert_rides(conn, rows: list[tuple], batch_id: int) -> int:
    """rows: (event_id, run_id, event_ts, produced_at, user_id, driver_id, zone, payment_method, distance_km, fare_idr)."""
    values = [(*r[:4], batch_id, *r[4:]) for r in rows]
    with conn, conn.cursor() as cur:
        inserted = 0
        if values:
            result = execute_values(cur, RIDES_SQL, values, template=RIDES_TEMPLATE, page_size=len(values), fetch=True)
            inserted = sum(r[0] for r in result)
        _record_batch(cur, "rides", batch_id, len(values), inserted)
    return inserted


def insert_rejected(conn, rows: list[tuple], batch_id: int) -> int:
    with conn, conn.cursor() as cur:
        written = 0
        if rows:
            written = len(execute_values(cur, REJECTED_SQL, rows, page_size=len(rows), fetch=True))
        _record_batch(cur, "rejected", batch_id, len(rows), written)
    return written


def upsert_final_windows(conn, rows: list[tuple], batch_id: int) -> int:
    with conn, conn.cursor() as cur:
        written = 0
        if rows:
            written = len(execute_values(cur, FINAL_SQL, rows, page_size=len(rows), fetch=True))
        _record_batch(cur, "zone_demand_final", batch_id, len(rows), written)
    return written


def _collect(df: DataFrame, columns: list) -> list[tuple]:
    return [tuple(r) for r in df.select(*columns).collect()]


def write_rides(df: DataFrame, batch_id: int) -> None:
    rows = _collect(df, [
        "event_id", "run_id",
        F.date_format("event_ts", ISO), F.date_format("produced_at", ISO),
        "user_id", "driver_id", "zone", "payment_method", "distance_km", "fare_idr",
    ])
    conn = connect()
    try:
        upsert_rides(conn, rows, batch_id)
    finally:
        conn.close()


def write_rejected(df: DataFrame, batch_id: int) -> None:
    rows = _collect(df, [
        "kafka_partition", "kafka_offset", F.date_format("kafka_ts", ISO), "reject_reason",
        F.substring("raw_value", 1, 500),
    ])
    conn = connect()
    try:
        insert_rejected(conn, rows, batch_id)
    finally:
        conn.close()


def write_final_windows(df: DataFrame, batch_id: int) -> None:
    rows = _collect(df, [
        F.date_format("window.start", ISO), F.date_format("window.end", ISO), "zone", "trips", "revenue_idr",
    ])
    conn = connect()
    try:
        upsert_final_windows(conn, rows, batch_id)
    finally:
        conn.close()
