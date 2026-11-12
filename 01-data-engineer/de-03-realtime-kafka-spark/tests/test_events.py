import json
from collections import Counter
from datetime import datetime, timezone

from streaming.events import ZONES, EventFactory, encode

NOW = datetime(2026, 11, 12, 10, 0, 5, tzinfo=timezone.utc)


def test_ride_event_is_valid_json_with_plausible_values():
    factory = EventFactory(run_id="t", seed=1)
    event = json.loads(encode(factory.ride(NOW)))
    assert event["zone"] in ZONES
    assert 0.8 <= event["distance_km"] <= 60
    assert event["fare_idr"] > 0 and event["fare_idr"] % 100 == 0
    assert event["event_ts"] == "2026-11-12T10:00:05.000+00:00"


def test_late_events_carry_an_older_event_time():
    factory = EventFactory(run_id="t", seed=1)
    event = factory.ride(NOW, delay_s=60)
    assert event["event_ts"] == "2026-11-12T09:59:05.000+00:00"
    assert event["produced_at"] == "2026-11-12T10:00:05.000+00:00"


def test_fault_mix_matches_configuration():
    factory = EventFactory(run_id="t", seed=3)
    kinds = Counter(factory.pick_kind(elapsed_s=60) for _ in range(200_000))
    assert abs(kinds["malformed"] / 200_000 - 0.003) < 0.001
    assert abs(kinds["too_late"] / 200_000 - 0.005) < 0.001
    assert abs(kinds["late"] / 200_000 - 0.02) < 0.002


def test_no_too_late_events_before_first_watermark():
    factory = EventFactory(run_id="t", seed=3)
    assert "too_late" not in {factory.pick_kind(elapsed_s=5) for _ in range(50_000)}


def test_same_seed_gives_same_events():
    a = EventFactory(run_id="t", seed=9).ride(NOW)
    b = EventFactory(run_id="t", seed=9).ride(NOW)
    assert a == b


def test_runs_with_the_same_seed_never_share_event_ids():
    # Regression: seeded ids collided across runs and the sink discarded real rides as duplicates.
    a, b = EventFactory(run_id="run-a", seed=7), EventFactory(run_id="run-b", seed=7)
    ids_a = {a.ride(NOW)["event_id"] for _ in range(1_000)}
    ids_b = {b.ride(NOW)["event_id"] for _ in range(1_000)}
    assert len(ids_a) == 1_000
    assert not ids_a & ids_b
