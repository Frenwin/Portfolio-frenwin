"""End-to-end run: seed -> snapshot -> live traffic + schema change -> prove the replica matches.

Usage (inside the compose network):
    python -m cdc.demo --rate 50 --duration 180

Writes docs/results.json and docs/results.md.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import statistics
import threading
import time
from pathlib import Path

import psycopg2

from cdc import connect, verify
from cdc.workload import Workload

log = logging.getLogger("demo")


def dsn(name: str, default: str) -> str:
    return os.getenv(name, default)


def wait_db(conn_str: str, timeout_s: float = 60):
    deadline = time.monotonic() + timeout_s
    while True:
        try:
            return psycopg2.connect(conn_str)
        except psycopg2.OperationalError:
            if time.monotonic() > deadline:
                raise
            time.sleep(1)


def history_check(source, replica) -> dict:
    """Current status per order in the source vs the SCD2 history's current row."""
    with source.cursor() as cur:
        cur.execute("SELECT id, status FROM orders")
        current = dict(cur.fetchall())
    source.rollback()
    with replica.cursor() as cur:
        cur.execute("SELECT order_id, status FROM order_status_history WHERE is_current")
        history = dict(cur.fetchall())
        cur.execute("SELECT count(DISTINCT order_id) FROM order_status_events WHERE op = 'd'")
        deleted = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM order_status_events")
        events = cur.fetchone()[0]
        cur.execute("""SELECT round(avg(n), 2), max(n) FROM (
                         SELECT order_id, count(*) AS n FROM order_status_history GROUP BY order_id) x""")
        avg_states, max_states = cur.fetchone()
    replica.rollback()
    mismatched = sum(1 for oid, status in current.items() if history.get(oid) != status)
    still_open_in_history = sum(1 for oid in history if oid not in current)
    return {
        "orders_in_source": len(current),
        "orders_with_wrong_current_status": mismatched,
        "deleted_orders_still_current_in_history": still_open_in_history,
        "deleted_orders_recorded": deleted,
        "status_events": events,
        "avg_statuses_per_order": float(avg_states or 0),
        "max_statuses_per_order": max_states,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate", type=float, default=50, help="source transactions per second")
    parser.add_argument("--duration", type=float, default=180)
    parser.add_argument("--schema-change-at", type=float, default=60)
    parser.add_argument("--probe-every", type=float, default=2.0)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    src_dsn = dsn("SOURCE_DSN", "host=localhost port=5436 dbname=shop user=shop password=shop")
    rep_dsn = dsn("REPLICA_DSN", "host=localhost port=5437 dbname=replica user=replica password=replica")
    source, replica = wait_db(src_dsn), wait_db(rep_dsn)
    result: dict = {}

    workload = Workload()
    workload.seed_data(source)
    with source, source.cursor() as cur:
        # One probe row before the snapshot, so the replica's probe table exists before lag is measured.
        cur.execute("INSERT INTO cdc_probe DEFAULT VALUES")
        cur.execute("SELECT (SELECT count(*) FROM customers), (SELECT count(*) FROM products), "
                    "(SELECT count(*) FROM orders), (SELECT count(*) FROM order_items)")
        result["seeded_rows"] = dict(zip(["customers", "products", "orders", "order_items"], cur.fetchone()))
    log.info("seeded %s", result["seeded_rows"])

    if "io.debezium.connector.jdbc.JdbcSinkConnector" not in connect.plugins():
        raise SystemExit("JDBC sink connector plugin not found in Kafka Connect")

    t0 = time.monotonic()
    for name in connect.CONNECTORS:
        connect.register(name)
        connect.wait_running(name)
    seconds, _ = verify.wait_until_equal(source, replica)
    result["snapshot_seconds"] = round(time.monotonic() - t0, 1)
    log.info("initial snapshot replicated in %.1f s", result["snapshot_seconds"])

    # Live traffic in a thread; lag probes from the main thread while it runs.
    traffic_conn = wait_db(src_dsn)
    thread = threading.Thread(
        target=workload.run, args=(traffic_conn, args.rate, args.duration, args.schema_change_at), daemon=True
    )
    t_start = time.monotonic()
    thread.start()
    lags = []
    while thread.is_alive():
        lags.append(verify.probe_lag(source, replica))
        time.sleep(args.probe_every)
    thread.join()
    run_seconds = time.monotonic() - t_start
    ops = sum(v for k, v in workload.counts.items() if not k.endswith("_skipped") and k != "schema_change")
    log.info("traffic done: %d operations in %.0f s", ops, run_seconds)

    converge_s, final = verify.wait_until_equal(source, replica)
    result["traffic"] = {
        "seconds": round(run_seconds, 1),
        "transactions": ops,
        "per_second": round(ops / run_seconds, 1),
        "by_type": dict(sorted(workload.counts.items())),
    }
    result["replication_lag_s"] = {
        "probes": len(lags),
        "p50": round(statistics.median(lags), 2),
        "p95": round(sorted(lags)[int(0.95 * (len(lags) - 1))], 2),
        "max": round(max(lags), 2),
    }
    result["converged_after_traffic_s"] = round(converge_s, 1)
    result["final_comparison"] = final
    with replica.cursor() as cur:
        cur.execute("SELECT count(*), count(loyalty_tier) FROM customers")
        rows, with_tier = cur.fetchone()
    replica.rollback()
    result["schema_change"] = {
        "column_added_in_source": "customers.loyalty_tier",
        "column_present_in_replica": verify.has_column(replica, "customers", "loyalty_tier"),
        "replica_rows_with_value": with_tier,
    }

    deadline = time.monotonic() + 60
    while True:
        hist = history_check(source, replica)
        if hist["orders_with_wrong_current_status"] == 0 or time.monotonic() > deadline:
            break
        time.sleep(1)
    result["history"] = hist

    out = Path("docs")
    out.mkdir(exist_ok=True)
    (out / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (out / "results.md").write_text(render(result), encoding="utf-8")
    print(json.dumps(result, indent=2))


def render(r: dict) -> str:
    t, lag, h, sc = r["traffic"], r["replication_lag_s"], r["history"], r["schema_change"]
    rows = [
        f"| `{name}` | {v['source_rows']:,} | {v['replica_rows']:,} | {'identical' if v['equal'] else 'DIFFERENT'} |"
        for name, v in r["final_comparison"].items()
    ]
    by_type = ", ".join(f"{k} {v:,}" for k, v in t["by_type"].items())
    return "\n".join([
        "# Measured run",
        "",
        "Generated by `python -m cdc.demo`, Docker on a laptop.",
        "",
        "## Replica vs source after live traffic",
        "",
        "| Table | Source rows | Replica rows | Row-by-row checksum |",
        "| --- | ---: | ---: | --- |",
        *rows,
        "",
        "## Timings",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Initial snapshot of {sum(r['seeded_rows'].values()):,} rows | {r['snapshot_seconds']} s |",
        f"| Live traffic | {t['transactions']:,} transactions in {t['seconds']} s ({t['per_second']}/s) |",
        f"| Replication lag p50 / p95 / max ({lag['probes']} probes) | {lag['p50']} / {lag['p95']} / {lag['max']} s |",
        f"| Replica identical after traffic stopped | {r['converged_after_traffic_s']} s |",
        "",
        f"Operations: {by_type}.",
        "",
        "## Schema change during traffic",
        "",
        f"`ALTER TABLE customers ADD COLUMN loyalty_tier` ran in the source mid-traffic: column present in replica = "
        f"{sc['column_present_in_replica']}, {sc['replica_rows_with_value']:,} replica rows carry a value.",
        "",
        "## Order status history (SCD2 from the change stream)",
        "",
        f"- {h['status_events']:,} status events recorded; orders passed through up to {h['max_statuses_per_order']} statuses "
        f"(average {h['avg_statuses_per_order']}).",
        f"- Current status in history vs source: {h['orders_with_wrong_current_status']} of {h['orders_in_source']:,} orders differ.",
        f"- {h['deleted_orders_recorded']:,} purged orders kept in history as deletions; "
        f"{h['deleted_orders_still_current_in_history']} still shown as current.",
        "",
    ])


if __name__ == "__main__":
    main()
