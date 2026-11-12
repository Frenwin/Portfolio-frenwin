"""Silver: validated, de-duplicated, enriched trips.

* Each row is checked against ``REJECT_RULES``; failures go to ``trips_rejected`` with the
  first rule they broke, so nothing disappears silently.
* ``trip_id`` is a hash of the trip's content, so exact duplicates collapse to one row.
* Rows are synced into silver with a Delta MERGE scoped to the month: new trips are
  inserted, trips that vanished from the source are deleted, unchanged trips are untouched.
  Re-running a month therefore changes nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from delta.tables import DeltaTable
from pyspark.sql import Column, DataFrame, SparkSession
from pyspark.sql import functions as F

from lakehouse.config import Tables

MAX_TRIP_SECONDS = 6 * 3600
MAX_DISTANCE_MILES = 200

# (reason, SQL condition that makes a row invalid); the first match is recorded
REJECT_RULES: list[tuple[str, str]] = [
    ("missing_timestamp", "pickup_ts IS NULL OR dropoff_ts IS NULL"),
    ("pickup_outside_file_month", "date_format(pickup_ts, 'yyyy-MM') <> source_month"),
    ("dropoff_not_after_pickup", "dropoff_ts <= pickup_ts"),
    ("duration_over_6h", f"unix_timestamp(dropoff_ts) - unix_timestamp(pickup_ts) > {MAX_TRIP_SECONDS}"),
    ("non_positive_distance", "trip_distance <= 0"),
    ("distance_over_200_miles", f"trip_distance > {MAX_DISTANCE_MILES}"),
    ("negative_amount", "fare_amount < 0 OR total_amount < 0"),
]

PAYMENT_TYPES = {0: "flex_fare", 1: "credit_card", 2: "cash", 3: "no_charge", 4: "dispute", 5: "unknown", 6: "voided"}

TRIP_ID_COLUMNS = [
    "vendor_id", "pickup_ts", "dropoff_ts", "pu_location_id", "do_location_id",
    "passenger_count", "trip_distance", "payment_type", "fare_amount", "total_amount",
]


@dataclass(frozen=True)
class SilverResult:
    month: str
    read: int
    rejected: int
    duplicates: int
    inserted: int
    deleted: int


def reject_reason() -> Column:
    expr = F.lit(None).cast("string")
    for reason, condition in reversed(REJECT_RULES):
        expr = F.when(F.coalesce(F.expr(condition), F.lit(False)), F.lit(reason)).otherwise(expr)
    return expr


def month_bounds(month: str) -> tuple[str, str]:
    year, mon = map(int, month.split("-"))
    start = date(year, mon, 1)
    end = date(year + (mon == 12), mon % 12 + 1, 1)
    return start.isoformat(), end.isoformat()


def enrich(valid: DataFrame, zones: DataFrame) -> DataFrame:
    pu = zones.select(
        F.col("location_id").alias("pu_location_id"),
        F.col("borough").alias("pu_borough"),
        F.col("zone").alias("pu_zone"),
    )
    do = zones.select(
        F.col("location_id").alias("do_location_id"),
        F.col("borough").alias("do_borough"),
        F.col("zone").alias("do_zone"),
    )
    payment_name = F.create_map([F.lit(x) for kv in PAYMENT_TYPES.items() for x in kv])
    return (
        valid.join(F.broadcast(pu), "pu_location_id", "left")
        .join(F.broadcast(do), "do_location_id", "left")
        .select(
            F.sha2(F.concat_ws("|", *[F.coalesce(F.col(c).cast("string"), F.lit("")) for c in TRIP_ID_COLUMNS]), 256).alias("trip_id"),
            "vendor_id",
            "pickup_ts",
            "dropoff_ts",
            F.to_date("pickup_ts").alias("pickup_date"),
            F.hour("pickup_ts").alias("pickup_hour"),
            F.round((F.unix_timestamp("dropoff_ts") - F.unix_timestamp("pickup_ts")) / 60.0, 2).alias("duration_min"),
            "passenger_count",
            "trip_distance",
            "pu_location_id", "pu_borough", "pu_zone",
            "do_location_id", "do_borough", "do_zone",
            "payment_type",
            F.coalesce(payment_name[F.col("payment_type")], F.lit("unknown")).alias("payment_type_name"),
            "fare_amount", "tip_amount", "tolls_amount", "total_amount",
            "congestion_surcharge", "airport_fee",
            "source_month",
            F.current_timestamp().alias("_processed_at"),
        )
    )


def process_month(spark: SparkSession, tables: Tables, month: str) -> SilverResult:
    bronze = (
        spark.read.format("delta").load(tables.bronze_trips)
        .where(F.col("source_month") == month)
        .withColumn("reject_reason", reject_reason())
    ).cache()
    zones = spark.read.format("delta").load(tables.bronze_zones)

    rejected = bronze.where(F.col("reject_reason").isNotNull()).withColumn("_processed_at", F.current_timestamp())
    (
        rejected.write.format("delta")
        .mode("overwrite")
        .option("replaceWhere", f"source_month = '{month}'")
        .partitionBy("source_month")
        .save(tables.silver_rejected)
    )

    valid = enrich(bronze.where(F.col("reject_reason").isNull()).drop("reject_reason"), zones)
    deduped = valid.dropDuplicates(["trip_id"]).cache()
    read, n_rejected, n_valid, n_unique = bronze.count(), rejected.count(), valid.count(), deduped.count()

    start, end = month_bounds(month)
    in_month = f"t.pickup_date >= '{start}' AND t.pickup_date < '{end}'"

    if not DeltaTable.isDeltaTable(spark, tables.silver_trips):
        deduped.write.format("delta").partitionBy("pickup_date").save(tables.silver_trips)
        inserted, deleted = n_unique, 0
    else:
        inserted, deleted = _sync_month(spark, tables.silver_trips, deduped, in_month)

    bronze.unpersist()
    deduped.unpersist()
    return SilverResult(month, read, n_rejected, n_valid - n_unique, inserted, deleted)


def _sync_month(spark: SparkSession, path: str, source: DataFrame, in_month: str) -> tuple[int, int]:
    """Make silver's rows for one month equal to `source`, touching only that month's partitions.

    A single MERGE with whenNotMatchedBySourceDelete would be simpler, but Delta then has to
    scan the whole target table, so each month gets slower as the table grows. Two MERGEs whose
    conditions both restrict the target to the month let Delta prune every other partition.
    """
    table = DeltaTable.forPath(spark, path)

    # 1. Insert-only MERGE: new trips in, existing trips untouched.
    table.alias("t").merge(source.alias("s"), f"t.trip_id = s.trip_id AND {in_month}").whenNotMatchedInsertAll().execute()
    inserted = _last_metric(table, "numTargetRowsInserted")

    # 2. Trips that are in silver for this month but no longer in the source.
    month_rows = spark.read.format("delta").load(path).alias("t").where(in_month).select("trip_id")
    stale = month_rows.join(source.select("trip_id"), "trip_id", "left_anti").cache()
    deleted = 0
    if stale.count():
        table.alias("t").merge(stale.alias("s"), f"t.trip_id = s.trip_id AND {in_month}").whenMatchedDelete().execute()
        deleted = _last_metric(table, "numTargetRowsDeleted")
    stale.unpersist()
    return inserted, deleted


def _last_metric(table: DeltaTable, name: str) -> int:
    metrics = table.history(1).select("operationMetrics").first()["operationMetrics"]
    return int(metrics.get(name, 0))
