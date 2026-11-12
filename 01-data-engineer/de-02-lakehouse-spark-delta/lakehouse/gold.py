"""Gold: business-ready aggregates rebuilt from silver on every run."""

from __future__ import annotations

from pyspark.sql import SparkSession
from pyspark.sql import functions as F

from lakehouse.config import Tables

AIRPORT_ZONES = ("JFK Airport", "LaGuardia Airport", "Newark Airport")


def build(spark: SparkSession, tables: Tables) -> dict[str, int]:
    trips = spark.read.format("delta").load(tables.silver_trips)
    card_tip_pct = F.when(
        (F.col("payment_type") == 1) & (F.col("fare_amount") > 0),
        F.col("tip_amount") / F.col("fare_amount") * 100,
    )

    daily_zone_demand = trips.groupBy("pickup_date", "pu_location_id", "pu_borough", "pu_zone").agg(
        F.count("*").alias("trips"),
        F.round(F.sum("total_amount"), 2).alias("revenue"),
        F.round(F.avg("trip_distance"), 2).alias("avg_distance_mi"),
        F.round(F.avg("duration_min"), 2).alias("avg_duration_min"),
        F.round(F.avg(card_tip_pct), 2).alias("avg_card_tip_pct"),
    )

    hourly_demand = trips.groupBy("pickup_date", "pickup_hour").agg(
        F.count("*").alias("trips"),
        F.round(F.sum("trip_distance") / (F.sum("duration_min") / 60), 2).alias("avg_speed_mph"),
        F.round(F.avg("total_amount"), 2).alias("avg_total_amount"),
    )

    daily_kpis = trips.groupBy("pickup_date").agg(
        F.count("*").alias("trips"),
        F.round(F.sum("total_amount"), 2).alias("revenue"),
        F.round(F.avg("duration_min"), 2).alias("avg_duration_min"),
        F.round(F.avg("trip_distance"), 2).alias("avg_distance_mi"),
        F.round(F.avg((F.col("payment_type") == 1).cast("int")) * 100, 2).alias("card_share_pct"),
        F.sum(F.col("pu_zone").isin(*AIRPORT_ZONES).cast("int")).alias("airport_pickups"),
    )

    counts = {}
    for name, df, path in [
        ("daily_zone_demand", daily_zone_demand, tables.gold_daily_zone_demand),
        ("hourly_demand", hourly_demand, tables.gold_hourly_demand),
        ("daily_kpis", daily_kpis, tables.gold_daily_kpis),
    ]:
        df.write.format("delta").mode("overwrite").option("overwriteSchema", "true").save(path)
        counts[name] = spark.read.format("delta").load(path).count()
    return counts
