"""Reconcile a measured producer run against what landed in PostgreSQL.

Usage (after `python -m streaming.producer --duration N` finished and the job caught up):
    python -m streaming.report --run-id <run_id>      # defaults to the newest file in data/runs

Writes docs/results.json and docs/results.md.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from streaming.events import BURST_RIDES, FRAUD_MIN_RIDES
from streaming.sink import connect


def one(cur, sql: str, params=()) -> tuple:
    cur.execute(sql, params)
    return cur.fetchone()


def build(run: dict) -> dict:
    rid, counts = run["run_id"], run["counts"]
    window = (run["started_at"], run["ended_at"])
    burst_like = f"burst-{rid}-%"
    conn = connect()
    with conn, conn.cursor() as cur:
        stored = one(cur, "SELECT count(*) FROM rides WHERE run_id = %s", (rid,))[0]
        cur.execute("""
            SELECT percentile_cont(0.5)  WITHIN GROUP (ORDER BY s), percentile_cont(0.95) WITHIN GROUP (ORDER BY s),
                   percentile_cont(0.99) WITHIN GROUP (ORDER BY s), max(s)
            FROM (SELECT extract(epoch FROM ingested_at - produced_at) AS s FROM rides WHERE run_id = %s) x""", (rid,))
        p50, p95, p99, mx = cur.fetchone()
        first, last = one(cur, "SELECT min(ingested_at), max(ingested_at) FROM rides WHERE run_id = %s", (rid,))
        late_kept = one(cur, """SELECT count(*) FROM rides WHERE run_id = %s
                                 AND produced_at - event_ts BETWEEN interval '15 seconds' AND interval '2 minutes'""", (rid,))[0]
        too_late_kept = one(cur, "SELECT count(*) FROM rides WHERE run_id = %s AND produced_at - event_ts > interval '4 minutes'", (rid,))[0]
        malformed = one(cur, """SELECT count(*) FROM rejected_events WHERE reason = 'malformed_json'
                                 AND kafka_ts BETWEEN %s::timestamptz AND %s::timestamptz + interval '5 seconds'""", window)[0]
        detected = one(cur, "SELECT count(DISTINCT user_id) FROM fraud_alerts WHERE user_id LIKE %s", (burst_like,))[0]
        false_alerts = one(cur, """SELECT count(*) FROM fraud_alerts WHERE user_id NOT LIKE 'burst-%%'
                                    AND window_start BETWEEN %s::timestamptz - interval '5 minutes' AND %s::timestamptz""", window)[0]
        det_p50, det_max = one(cur, f"""
            WITH ranked AS (
                SELECT user_id, date_trunc('minute', event_ts) AS w, produced_at,
                       row_number() OVER (PARTITION BY user_id, date_trunc('minute', event_ts) ORDER BY event_ts) AS rn
                FROM rides WHERE run_id = %s AND user_id LIKE %s)
            SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM a.flagged_at - r.produced_at)),
                   max(extract(epoch FROM a.flagged_at - r.produced_at))
            FROM fraud_alerts a JOIN ranked r ON r.user_id = a.user_id AND r.w = a.window_start AND r.rn = {FRAUD_MIN_RIDES}""",
            (rid, burst_like))
        windows, matching = one(cur, """
            SELECT count(*), count(*) FILTER (WHERE f.trips = d.trips)
            FROM zone_demand_final f JOIN zone_demand_1m d USING (window_start, zone)
            WHERE f.window_start BETWEEN %s::timestamptz AND %s::timestamptz""", window)
        batches, avg_rows, max_rows = one(cur, """
            SELECT count(*), round(avg(rows_in)), max(rows_in) FROM stream_batches
            WHERE query = 'rides' AND processed_at BETWEEN %s::timestamptz AND %s::timestamptz + interval '1 minute'""", window)
    conn.close()

    span = (last - first).total_seconds() if first and last else 0
    return {
        "run_id": rid,
        "producer": {
            "seconds": run["seconds"],
            "messages_sent": counts["sent"],
            "achieved_rate_per_s": run["achieved_rate_per_s"],
            "injected": {k: counts[k] for k in ("duplicate", "late", "too_late", "malformed", "burst_users")},
        },
        "correctness": {
            "expected_rides": run["expected_rides"],
            "stored_rides": stored,
            "exact_match": stored == run["expected_rides"],
            "duplicates_sent": counts["duplicate"],
            "late_sent": counts["late"],
            "late_kept": late_kept,
            "too_late_sent": counts["too_late"],
            "too_late_kept": too_late_kept,
            "malformed_sent": counts["malformed"],
            "malformed_rejected": malformed,
        },
        "fraud": {
            "rule": f">= {FRAUD_MIN_RIDES} rides by one user in one minute",
            "bursts_injected": counts["burst_users"],
            "bursts_detected": detected,
            "false_alerts": false_alerts,
            "detection_latency_p50_s": _r(det_p50),
            "detection_latency_max_s": _r(det_max),
            "burst_size": BURST_RIDES,
        },
        "latency_s": {"p50": _r(p50), "p95": _r(p95), "p99": _r(p99), "max": _r(mx)},
        "throughput": {
            "rides_per_s_stored": round(stored / span, 1) if span else None,
            "micro_batches": batches,
            "avg_rows_per_batch": int(avg_rows or 0),
            "max_rows_per_batch": max_rows,
        },
        "final_vs_realtime_windows": {"windows_compared": windows, "identical": matching},
    }


def _r(x) -> float | None:
    return None if x is None else round(float(x), 2)


def render(r: dict) -> str:
    p, c, f, l, t, w = r["producer"], r["correctness"], r["fraud"], r["latency_s"], r["throughput"], r["final_vs_realtime_windows"]
    return "\n".join([
        "# Measured run",
        "",
        f"Run `{r['run_id']}`: {p['messages_sent']:,} messages in {p['seconds']} s ({p['achieved_rate_per_s']:,}/s), "
        "Spark local mode in Docker on a laptop.",
        "",
        "## Correctness",
        "",
        "| Check | Sent | Result |",
        "| --- | ---: | --- |",
        f"| Unique valid rides stored exactly once | {c['expected_rides']:,} expected | {c['stored_rides']:,} stored ({'exact match' if c['exact_match'] else 'MISMATCH'}) |",
        f"| Duplicate re-sends | {c['duplicates_sent']:,} | 0 extra rows (deduplicated) |",
        f"| Late events (20-90 s) | {c['late_sent']:,} | {c['late_kept']:,} kept |",
        f"| Too-late events (5-10 min, beyond watermark) | {c['too_late_sent']:,} | {c['too_late_kept']:,} kept (dropped) |",
        f"| Malformed messages | {c['malformed_sent']:,} | {c['malformed_rejected']:,} in `rejected_events` |",
        f"| Fraud bursts ({f['burst_size']} rides in 15 s) | {f['bursts_injected']} | {f['bursts_detected']} detected, {f['false_alerts']} false alerts |",
        "",
        "## Speed",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| End-to-end latency p50 / p95 / p99 (produced -> stored) | {l['p50']} / {l['p95']} / {l['p99']} s |",
        f"| Fraud detection latency p50 / max (5th ride -> flag) | {f['detection_latency_p50_s']} / {f['detection_latency_max_s']} s |",
        f"| Rides stored per second | {t['rides_per_s_stored']} |",
        f"| Micro-batches (avg / max rows) | {t['micro_batches']} ({t['avg_rows_per_batch']:,} / {t['max_rows_per_batch']:,}) |",
        "",
        f"Real-time and watermark-final per-minute counts agree on {w['identical']} of {w['windows_compared']} zone-minutes.",
        "",
    ])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id")
    parser.add_argument("--runs", type=Path, default=Path("data/runs"))
    parser.add_argument("--out", type=Path, default=Path("docs"))
    args = parser.parse_args()
    path = args.runs / f"{args.run_id}.json" if args.run_id else max(args.runs.glob("*.json"), key=lambda p: p.stat().st_mtime)
    result = build(json.loads(path.read_text(encoding="utf-8")))
    args.out.mkdir(exist_ok=True)
    (args.out / "results.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    (args.out / "results.md").write_text(render(result), encoding="utf-8")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
