from datetime import datetime as dt

from pyspark.sql import functions as F

from lakehouse import bronze, gold, silver

# Raw TLC column names as published. January uses "Airport_fee" and int passenger_count;
# the test for drift writes the other spelling and a double passenger_count.
RAW_SCHEMA = (
    "VendorID int, tpep_pickup_datetime timestamp, tpep_dropoff_datetime timestamp, "
    "passenger_count {pc}, trip_distance double, RatecodeID double, store_and_fwd_flag string, "
    "PULocationID int, DOLocationID int, payment_type long, fare_amount double, extra double, "
    "mta_tax double, tip_amount double, tolls_amount double, improvement_surcharge double, "
    "total_amount double, congestion_surcharge double, {airport} double"
)


def trip(pickup, dropoff, distance=2.0, fare=12.0, total=16.0, pu=161, do=236, payment=1, tip=2.0):
    return (2, pickup, dropoff, 1, distance, 1.0, "N", pu, do, payment, fare, 1.0, 0.5, tip, 0.0, 1.0, total, 2.5, 0.0)


def write_month(spark, landing, month, rows, pc="int", airport="Airport_fee"):
    path = landing / f"yellow_tripdata_{month}.parquet"
    if pc == "double":
        rows = [(*r[:3], float(r[3]), *r[4:]) for r in rows]
    spark.createDataFrame(rows, RAW_SCHEMA.format(pc=pc, airport=airport)).coalesce(1).write.mode("overwrite").parquet(str(path))
    return path


GOOD = trip(dt(2024, 1, 10, 8, 0), dt(2024, 1, 10, 8, 20))
GOOD_2 = trip(dt(2024, 1, 11, 9, 0), dt(2024, 1, 11, 9, 30), pu=132, distance=17.5, fare=70.0, total=90.0)
DIRTY = [
    trip(dt(2024, 1, 12, 9, 0), dt(2024, 1, 12, 8, 59)),               # dropoff before pickup
    trip(dt(2024, 1, 13, 9, 0), dt(2024, 1, 13, 9, 10), fare=-5.0),    # negative amount (void/refund)
    trip(dt(2009, 1, 1, 0, 5), dt(2009, 1, 1, 0, 15)),                 # stray date outside the file month
    trip(dt(2024, 1, 14, 9, 0), dt(2024, 1, 14, 9, 10), distance=0.0), # zero distance
]


def test_conform_handles_schema_drift(spark, landing):
    a = write_month(spark, landing, "2024-01", [GOOD], pc="int", airport="Airport_fee")
    b = write_month(spark, landing, "2024-02", [GOOD], pc="double", airport="airport_fee")
    left = bronze.conform_trips(spark.read.parquet(str(a)))
    right = bronze.conform_trips(spark.read.parquet(str(b)))
    assert left.schema == right.schema
    assert [f.name for f in left.schema] == [c for c, _ in bronze.TRIP_SCHEMA]
    assert right.first()["airport_fee"] == 0.0


def test_bronze_ingest_is_idempotent(spark, tables, landing):
    write_month(spark, landing, "2024-01", [GOOD, GOOD_2])
    assert bronze.ingest_trips_month(spark, tables, landing, "2024-01") == 2
    assert bronze.ingest_trips_month(spark, tables, landing, "2024-01") == 2


def _load_month(spark, tables, landing, rows):
    write_month(spark, landing, "2024-01", rows)
    bronze.ingest_zones(spark, tables, landing)
    bronze.ingest_trips_month(spark, tables, landing, "2024-01")
    return silver.process_month(spark, tables, "2024-01")


def test_silver_rejects_with_reason_and_removes_duplicates(spark, tables, landing):
    result = _load_month(spark, tables, landing, [GOOD, GOOD, *DIRTY])

    assert (result.read, result.rejected, result.duplicates, result.inserted) == (6, 4, 1, 1)
    reasons = {r["reject_reason"] for r in spark.read.format("delta").load(tables.silver_rejected).collect()}
    assert reasons == {"dropoff_not_after_pickup", "negative_amount", "pickup_outside_file_month", "non_positive_distance"}

    row = spark.read.format("delta").load(tables.silver_trips).first()
    assert (row["pu_zone"], row["do_zone"], row["duration_min"], row["payment_type_name"]) == (
        "Midtown Center", "Upper East Side North", 20.0, "credit_card",
    )


def test_silver_rerun_changes_nothing(spark, tables, landing):
    _load_month(spark, tables, landing, [GOOD, GOOD_2])
    again = silver.process_month(spark, tables, "2024-01")
    assert (again.inserted, again.deleted) == (0, 0)
    assert spark.read.format("delta").load(tables.silver_trips).count() == 2


def test_silver_sync_deletes_trips_removed_from_source(spark, tables, landing):
    _load_month(spark, tables, landing, [GOOD, GOOD_2])
    result = _load_month(spark, tables, landing, [GOOD])  # source corrected: GOOD_2 withdrawn
    assert (result.inserted, result.deleted) == (0, 1)
    assert spark.read.format("delta").load(tables.silver_trips).count() == 1


def test_gold_totals_match_silver(spark, tables, landing):
    _load_month(spark, tables, landing, [GOOD, GOOD_2, *DIRTY])
    counts = gold.build(spark, tables)
    assert counts == {"daily_zone_demand": 2, "hourly_demand": 2, "daily_kpis": 2}

    kpis = spark.read.format("delta").load(tables.gold_daily_kpis)
    totals = kpis.agg(F.sum("trips").alias("trips"), F.sum("revenue").alias("revenue"), F.sum("airport_pickups").alias("airport")).first()
    assert (totals["trips"], totals["revenue"], totals["airport"]) == (2, 106.0, 1)
