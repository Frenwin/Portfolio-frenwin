"""Parse and validate raw Kafka records. Pure DataFrame logic, so it is tested on static data."""

from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from streaming.events import ZONES

EVENT_SCHEMA = (
    "event_id string, event_type string, run_id string, event_ts timestamp, produced_at timestamp, "
    "user_id string, driver_id string, zone string, payment_method string, "
    "distance_km double, fare_idr long"
)
EVENT_COLUMNS = [
    "event_id", "run_id", "event_ts", "produced_at", "user_id", "driver_id",
    "zone", "payment_method", "distance_km", "fare_idr",
]
REQUIRED = ["event_ts", "produced_at", "user_id", "driver_id", "zone", "payment_method", "distance_km", "fare_idr", "run_id"]
MAX_DISTANCE_KM = 100


def parse(raw: DataFrame) -> DataFrame:
    """Kafka rows (value, partition, offset, timestamp) -> event columns + reject_reason (null = valid)."""
    value = F.col("value").cast("string")
    parsed = raw.select(
        value.alias("raw_value"),
        F.col("partition").alias("kafka_partition"),
        F.col("offset").alias("kafka_offset"),
        F.col("timestamp").alias("kafka_ts"),
        F.from_json(value, EVENT_SCHEMA).alias("e"),
    ).select("raw_value", "kafka_partition", "kafka_offset", "kafka_ts", "e.*")

    missing = F.lit(False)
    for column in REQUIRED:
        missing = missing | F.col(column).isNull()

    reason = (
        F.when(F.col("event_id").isNull(), "malformed_json")
        .when(missing, "missing_field")
        .when(~F.col("zone").isin(*ZONES), "unknown_zone")
        .when(F.col("fare_idr") <= 0, "non_positive_fare")
        .when((F.col("distance_km") <= 0) | (F.col("distance_km") > MAX_DISTANCE_KM), "invalid_distance")
    )
    return parsed.withColumn("reject_reason", reason)
