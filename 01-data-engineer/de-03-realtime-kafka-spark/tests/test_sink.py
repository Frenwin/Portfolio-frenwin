from streaming.sink import insert_rejected, upsert_rides


def ride(event_id, user="u1", zone="Sudirman", minute=0, second=0, fare=30000):
    ts = f"2026-11-12T10:{minute:02d}:{second:02d}.000Z"
    return (event_id, "run1", ts, ts, user, "d1", zone, "ewallet", 5.5, fare)


def fetch(conn, sql):
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchall()


def test_replayed_batch_does_not_double_count(pg):
    batch = [ride("e1"), ride("e2", zone="Kemang"), ride("e3")]
    assert upsert_rides(pg, batch, batch_id=1) == 3
    assert upsert_rides(pg, batch, batch_id=1) == 0  # Spark replays the batch after a crash

    assert fetch(pg, "select count(*) from rides") == [(3,)]
    assert fetch(pg, "select zone, trips, revenue_idr from zone_demand_1m order by zone") == [
        ("Kemang", 1, 30000), ("Sudirman", 2, 60000),
    ]
    assert fetch(pg, "select rows_in, rows_written from stream_batches where query = 'rides'") == [(3, 3)]


def test_duplicate_inside_a_batch_and_across_batches_counted_once(pg):
    upsert_rides(pg, [ride("e1"), ride("e2")], batch_id=1)
    upsert_rides(pg, [ride("e2"), ride("e3")], batch_id=2)
    assert fetch(pg, "select trips from zone_demand_1m") == [(3,)]


def test_fraud_flag_set_when_threshold_crossed_across_batches(pg):
    upsert_rides(pg, [ride(f"a{i}", user="burst", second=i) for i in range(3)], batch_id=1)
    assert fetch(pg, "select count(*) from fraud_alerts") == [(0,)]
    upsert_rides(pg, [ride(f"b{i}", user="burst", second=10 + i) for i in range(2)], batch_id=2)
    assert fetch(pg, "select user_id, rides from fraud_alerts") == [("burst", 5)]


def test_rides_in_different_minutes_are_not_combined_for_fraud(pg):
    rides = [ride(f"c{i}", user="u9", minute=i // 3, second=i) for i in range(6)]  # 3 + 3
    upsert_rides(pg, rides, batch_id=1)
    assert fetch(pg, "select count(*) from fraud_alerts") == [(0,)]


def test_rejected_events_are_idempotent_by_kafka_offset(pg):
    rows = [(0, 41, "2026-11-12T10:00:00.000Z", "malformed_json", "not json")]
    assert insert_rejected(pg, rows, batch_id=1) == 1
    assert insert_rejected(pg, rows, batch_id=1) == 0
