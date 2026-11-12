"""Spark Structured Streaming job: Kafka -> validate -> watermark + dedup -> PostgreSQL.

Three queries share one parsed stream:
  rides              deduplicated valid events, written every trigger (real-time view)
  rejected           malformed or invalid events, kept with their reason
  zone_demand_final  per-minute demand emitted once the watermark closes each window
"""

from __future__ import annotations

import logging
import os

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from streaming import sink, transform
from streaming.kafka_admin import ensure_topic

KAFKA_PACKAGE = "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.3"
WATERMARK = os.getenv("WATERMARK", "2 minutes")
TRIGGER = os.getenv("TRIGGER", "5 seconds")
MAX_OFFSETS_PER_TRIGGER = int(os.getenv("MAX_OFFSETS_PER_TRIGGER", "50000"))

log = logging.getLogger("spark_job")


def build_spark() -> SparkSession:
    spark = (
        SparkSession.builder.appName("ride-stream")
        .master(os.getenv("SPARK_MASTER", "local[*]"))
        .config("spark.jars.packages", KAFKA_PACKAGE)
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", os.getenv("SPARK_SHUFFLE_PARTITIONS", "8"))
        .config("spark.driver.memory", os.getenv("SPARK_DRIVER_MEMORY", "2g"))
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    return spark


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("py4j").setLevel(logging.WARNING)  # otherwise every foreachBatch callback is logged
    bootstrap = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
    topic = os.getenv("KAFKA_TOPIC", "rides")
    checkpoints = os.getenv("CHECKPOINT_DIR", "data/checkpoints")
    ensure_topic(bootstrap, topic)
    spark = build_spark()

    raw = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", bootstrap)
        .option("subscribe", topic)
        .option("startingOffsets", "earliest")
        .option("maxOffsetsPerTrigger", MAX_OFFSETS_PER_TRIGGER)
        .option("failOnDataLoss", "false")
        .load()
    )
    parsed = transform.parse(raw)

    valid = parsed.where(F.col("reject_reason").isNull()).select(*transform.EVENT_COLUMNS)
    deduped = valid.withWatermark("event_ts", WATERMARK).dropDuplicatesWithinWatermark(["event_id"])
    rejected = parsed.where(F.col("reject_reason").isNotNull())

    final_windows = (
        deduped.groupBy(F.window("event_ts", "1 minute"), "zone")
        .agg(F.count("*").alias("trips"), F.sum("fare_idr").alias("revenue_idr"))
    )

    def start(df, name, writer, mode="append"):
        return (
            df.writeStream.queryName(name)
            .outputMode(mode)
            .foreachBatch(writer)
            .option("checkpointLocation", f"{checkpoints}/{name}")
            .trigger(processingTime=TRIGGER)
            .start()
        )

    start(deduped, "rides", sink.write_rides)
    start(rejected, "rejected", sink.write_rejected)
    start(final_windows, "zone_demand_final", sink.write_final_windows)
    log.info("streaming from %s/%s, watermark %s, trigger %s", bootstrap, topic, WATERMARK, TRIGGER)
    spark.streams.awaitAnyTermination()


if __name__ == "__main__":
    main()
