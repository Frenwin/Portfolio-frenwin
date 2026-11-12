"""Bronze: land source files in Delta with a stable schema and lineage columns.

TLC files drift between months (``Airport_fee`` vs ``airport_fee``, ``passenger_count``
as int or double). Bronze applies one schema contract so every month lands in the same
table; nothing is filtered or fixed here.
"""

from __future__ import annotations

from pathlib import Path

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from lakehouse.config import Tables

# Canonical bronze schema: (column, Spark type)
TRIP_SCHEMA: list[tuple[str, str]] = [
    ("vendor_id", "int"),
    ("pickup_ts", "timestamp"),
    ("dropoff_ts", "timestamp"),
    ("passenger_count", "int"),
    ("trip_distance", "double"),
    ("rate_code_id", "int"),
    ("store_and_fwd_flag", "string"),
    ("pu_location_id", "int"),
    ("do_location_id", "int"),
    ("payment_type", "int"),
    ("fare_amount", "double"),
    ("extra", "double"),
    ("mta_tax", "double"),
    ("tip_amount", "double"),
    ("tolls_amount", "double"),
    ("improvement_surcharge", "double"),
    ("total_amount", "double"),
    ("congestion_surcharge", "double"),
    ("airport_fee", "double"),
]

# Source names (lower-cased) that differ from the canonical names
RENAMES = {
    "vendorid": "vendor_id",
    "tpep_pickup_datetime": "pickup_ts",
    "tpep_dropoff_datetime": "dropoff_ts",
    "ratecodeid": "rate_code_id",
    "pulocationid": "pu_location_id",
    "dolocationid": "do_location_id",
}


def conform_trips(df: DataFrame) -> DataFrame:
    """Rename, add missing columns as null and cast to the canonical schema."""
    for name in df.columns:
        canonical = RENAMES.get(name.lower(), name.lower())
        if canonical != name:
            df = df.withColumnRenamed(name, canonical)
    present = set(df.columns)
    return df.select(
        [
            (F.col(c) if c in present else F.lit(None)).cast(t).alias(c)
            for c, t in TRIP_SCHEMA
        ]
    )


def ingest_trips_month(spark: SparkSession, tables: Tables, landing: Path, month: str) -> int:
    """Replace the bronze partition for one source month. Re-running is idempotent."""
    source = landing / f"yellow_tripdata_{month}.parquet"
    if not source.exists():
        raise FileNotFoundError(f"{source} not found. Run scripts/download_tlc.py first.")

    df = (
        conform_trips(spark.read.parquet(str(source)))
        .withColumn("source_month", F.lit(month))
        .withColumn("_source_file", F.lit(source.name))
        .withColumn("_ingested_at", F.current_timestamp())
    )
    (
        df.write.format("delta")
        .mode("overwrite")
        .option("replaceWhere", f"source_month = '{month}'")
        .partitionBy("source_month")
        .save(tables.bronze_trips)
    )
    return spark.read.format("delta").load(tables.bronze_trips).where(F.col("source_month") == month).count()


def ingest_zones(spark: SparkSession, tables: Tables, landing: Path) -> int:
    source = landing / "taxi_zone_lookup.csv"
    df = (
        spark.read.option("header", True).csv(str(source))
        .select(
            F.col("LocationID").cast("int").alias("location_id"),
            F.col("Borough").alias("borough"),
            F.col("Zone").alias("zone"),
            F.col("service_zone"),
        )
    )
    df.write.format("delta").mode("overwrite").save(tables.bronze_zones)
    return df.count()
