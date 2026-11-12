import json
from datetime import datetime, timezone

from streaming import transform
from streaming.events import EventFactory, encode

NOW = datetime(2026, 11, 12, 10, 0, 5, tzinfo=timezone.utc)


def kafka_rows(spark, payloads):
    rows = [(p, 0, i, NOW.replace(tzinfo=None)) for i, p in enumerate(payloads)]
    return spark.createDataFrame(rows, "value binary, partition int, offset long, timestamp timestamp")


def test_parse_accepts_valid_and_labels_every_rejection(spark):
    factory = EventFactory(run_id="t", seed=1)
    good = factory.ride(NOW)
    bad_zone = {**factory.ride(NOW), "zone": "Atlantis"}
    zero_fare = {**factory.ride(NOW), "fare_idr": 0}
    far = {**factory.ride(NOW), "distance_km": 250.0}
    no_user = {k: v for k, v in factory.ride(NOW).items() if k != "user_id"}

    df = transform.parse(kafka_rows(spark, [
        encode(good), encode(bad_zone), encode(zero_fare), encode(far), encode(no_user),
        b"not json at all", b'{"event_id": "broken"',
    ]))
    reasons = [r["reject_reason"] for r in df.orderBy("kafka_offset").collect()]
    assert reasons == [
        None, "unknown_zone", "non_positive_fare", "invalid_distance", "missing_field",
        "malformed_json", "malformed_json",
    ]


def test_parse_reads_event_time_in_utc(spark):
    event = EventFactory(run_id="t", seed=1).ride(NOW, delay_s=30)
    row = transform.parse(kafka_rows(spark, [encode(event)])).first()
    assert row["event_ts"] == datetime(2026, 11, 12, 9, 59, 35)
    assert json.loads(row["raw_value"])["event_id"] == row["event_id"]
