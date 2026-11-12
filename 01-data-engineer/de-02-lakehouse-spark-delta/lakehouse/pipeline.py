"""Run the lakehouse end to end: bronze → silver → gold → table maintenance.

Usage:
    python -m lakehouse.pipeline --months 2024-01 2024-02 2024-03
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from dataclasses import asdict
from pathlib import Path

from delta.tables import DeltaTable

from lakehouse import bronze, gold, silver
from lakehouse.config import build_spark, ensure_bucket, tables_from_env

log = logging.getLogger("lakehouse")


def optimize_silver(spark, path: str) -> dict:
    """Compact small files and Z-order by pickup zone, the most common filter after date."""
    before = DeltaTable.forPath(spark, path).detail().select("numFiles", "sizeInBytes").first()
    DeltaTable.forPath(spark, path).optimize().executeZOrderBy("pu_location_id")
    after = DeltaTable.forPath(spark, path).detail().select("numFiles", "sizeInBytes").first()
    return {"files_before": before["numFiles"], "files_after": after["numFiles"], "size_bytes": after["sizeInBytes"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bronze → silver → gold lakehouse pipeline")
    parser.add_argument("--months", nargs="+", default=["2024-01", "2024-02", "2024-03"])
    parser.add_argument("--landing", type=Path, default=Path("data/landing"))
    parser.add_argument("--skip-optimize", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    tables = tables_from_env()
    ensure_bucket(tables.root)
    spark = build_spark("lakehouse-pipeline", tables.root)
    summary: dict = {"root": tables.root, "months": {}, "timings_s": {}}
    started = time.perf_counter()

    t = time.perf_counter()
    summary["zones"] = bronze.ingest_zones(spark, tables, args.landing)
    for month in args.months:
        rows = bronze.ingest_trips_month(spark, tables, args.landing, month)
        summary["months"][month] = {"bronze_rows": rows}
        log.info("bronze %s: %d rows", month, rows)
    summary["timings_s"]["bronze"] = round(time.perf_counter() - t, 1)

    t = time.perf_counter()
    for month in args.months:
        result = silver.process_month(spark, tables, month)
        summary["months"][month].update({k: v for k, v in asdict(result).items() if k != "month"})
        log.info("silver %s: %s", month, result)
    summary["timings_s"]["silver"] = round(time.perf_counter() - t, 1)

    t = time.perf_counter()
    summary["gold"] = gold.build(spark, tables)
    summary["timings_s"]["gold"] = round(time.perf_counter() - t, 1)
    log.info("gold: %s", summary["gold"])

    if not args.skip_optimize:
        t = time.perf_counter()
        summary["optimize_silver"] = optimize_silver(spark, tables.silver_trips)
        summary["timings_s"]["optimize"] = round(time.perf_counter() - t, 1)
        log.info("optimize: %s", summary["optimize_silver"])

    summary["timings_s"]["total"] = round(time.perf_counter() - started, 1)
    print(json.dumps(summary, indent=2))
    spark.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
