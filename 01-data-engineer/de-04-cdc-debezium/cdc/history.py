"""Consume Debezium change events for orders and keep every status change.

A mirror table only knows the current status. Analysts asking "how long do orders wait
between paid and shipped?" need the history, which only the change stream still has.

Delivery is at-least-once (offsets are committed after the database commit); the
(order_id, lsn) primary key makes replays harmless.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

import psycopg2
from confluent_kafka import Consumer, KafkaError
from psycopg2.extras import execute_values

TOPIC = "shop.public.orders"
log = logging.getLogger("history")

INSERT_SQL = """
INSERT INTO order_status_events (order_id, lsn, op, status, changed_at)
VALUES %s
ON CONFLICT (order_id, lsn) DO NOTHING
"""


def status_event(message_value: bytes | None) -> tuple | None:
    """Debezium JSON envelope -> (order_id, lsn, op, status, changed_at) or None if nothing to record."""
    if message_value is None:  # tombstone that follows a delete
        return None
    envelope = json.loads(message_value)
    payload = envelope.get("payload", envelope)
    if payload is None:
        return None
    op, before, after, source = payload["op"], payload.get("before"), payload.get("after"), payload["source"]
    lsn = source.get("lsn") or 0  # snapshot rows may carry no LSN; (order_id, 0) is still unique
    commit_time = datetime.fromtimestamp(source["ts_ms"] / 1000, tz=timezone.utc).isoformat()

    if op in ("r", "c"):
        return (after["id"], lsn, op, after["status"], after.get("updated_at") or commit_time)
    if op == "u":
        if before is not None and before.get("status") == after["status"]:
            return None  # a non-status change (e.g. total recalculated)
        return (after["id"], lsn, op, after["status"], after.get("updated_at") or commit_time)
    if op == "d":
        return (before["id"], lsn, op, None, commit_time)
    return None


def write_events(conn, events: list[tuple]) -> None:
    if not events:
        return
    with conn, conn.cursor() as cur:
        execute_values(cur, INSERT_SQL, events, page_size=len(events))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    conn = psycopg2.connect(os.getenv("REPLICA_DSN", "host=localhost port=5437 dbname=replica user=replica password=replica"))
    consumer = Consumer({
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP", "localhost:9094"),
        "group.id": "order-status-history",
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    consumer.subscribe([TOPIC])
    log.info("consuming %s", TOPIC)
    total = 0
    while True:
        messages = consumer.consume(num_messages=1000, timeout=1.0)
        events, consumed = [], 0
        for msg in messages:
            err = msg.error()
            if err is not None:
                if err.code() not in (KafkaError._PARTITION_EOF, KafkaError.UNKNOWN_TOPIC_OR_PART):
                    log.warning("kafka error: %s", err)
                continue
            consumed += 1
            event = status_event(msg.value())
            if event:
                events.append(event)
        if consumed:
            write_events(conn, events)
            consumer.commit(asynchronous=False)
            total += len(events)
            if events:
                log.info("recorded %d status events (%d total)", len(events), total)


if __name__ == "__main__":
    main()
