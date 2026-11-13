import json

from cdc.history import status_event, write_events
from cdc.workload import NEXT_STATUS, next_status


def envelope(op, before=None, after=None, lsn=1000, ts_ms=1_763_000_000_000):
    """Debezium JSON as produced by Kafka Connect's JsonConverter with schemas enabled."""
    return json.dumps({
        "schema": {"type": "struct"},
        "payload": {"op": op, "before": before, "after": after, "source": {"lsn": lsn, "ts_ms": ts_ms}},
    }).encode()


def order(status, updated_at="2026-11-13T03:00:00.000000Z", id_=7):
    return {"id": id_, "customer_id": 1, "status": status, "updated_at": updated_at}


def test_snapshot_and_insert_record_the_status():
    assert status_event(envelope("r", after=order("paid"))) == (7, 1000, "r", "paid", "2026-11-13T03:00:00.000000Z")
    assert status_event(envelope("c", after=order("pending")))[3] == "pending"


def test_update_recorded_only_when_status_changes():
    changed = envelope("u", before=order("paid"), after=order("packed", "2026-11-13T03:05:00.000000Z"), lsn=2000)
    assert status_event(changed) == (7, 2000, "u", "packed", "2026-11-13T03:05:00.000000Z")
    total_only = envelope("u", before=order("paid"), after=order("paid"), lsn=2001)
    assert status_event(total_only) is None


def test_delete_and_tombstone():
    deleted = status_event(envelope("d", before=order("cancelled"), lsn=3000))
    assert deleted[:4] == (7, 3000, "d", None)
    assert status_event(None) is None


def test_snapshot_rows_without_lsn_still_get_a_key():
    assert status_event(envelope("r", after=order("paid"), lsn=None))[1] == 0


def test_status_machine_only_moves_forward():
    assert [next_status(s) for s in NEXT_STATUS] == ["paid", "packed", "shipped", "delivered"]
    assert next_status("delivered") is None and next_status("cancelled") is None


def test_replayed_events_do_not_duplicate_history(replica):
    events = [
        status_event(envelope("c", after=order("pending", "2026-11-13T03:00:00Z"), lsn=10)),
        status_event(envelope("u", before=order("pending"), after=order("paid", "2026-11-13T03:02:00Z"), lsn=20)),
        status_event(envelope("u", before=order("paid"), after=order("packed", "2026-11-13T03:09:00Z"), lsn=30)),
    ]
    write_events(replica, events)
    write_events(replica, events)  # consumer crashed before committing offsets and re-read them
    with replica.cursor() as cur:
        cur.execute("SELECT status, valid_to IS NULL FROM order_status_history ORDER BY valid_from")
        assert cur.fetchall() == [("pending", False), ("paid", False), ("packed", True)]
        cur.execute("SELECT extract(epoch FROM valid_to - valid_from) FROM order_status_history WHERE status = 'paid'")
        assert float(cur.fetchone()[0]) == 420.0  # 7 minutes in 'paid'


def test_deleted_order_has_no_current_status(replica):
    # The delete's commit time is earlier than the app's updated_at (clock skew): order must follow the WAL.
    write_events(replica, [
        status_event(envelope("c", after=order("cancelled", "2026-11-13T03:00:00Z"), lsn=10)),
        status_event(envelope("d", before=order("cancelled"), lsn=20, ts_ms=1_794_538_000_000)),
    ])
    with replica.cursor() as cur:
        cur.execute("SELECT count(*) FROM order_status_history WHERE is_current")
        assert cur.fetchone()[0] == 0
