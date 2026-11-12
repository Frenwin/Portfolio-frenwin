"""Send simulated ride events to Kafka at a target rate, with injected faults.

Usage:
    python -m streaming.producer --rate 200                 # run until stopped
    python -m streaming.producer --rate 1000 --duration 180 # measured run, writes data/runs/<run_id>.json
"""

from __future__ import annotations

import argparse
import heapq
import json
import logging
import os
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from confluent_kafka import Producer

from streaming.events import BURST_RIDES, Counts, EventFactory, encode
from streaming.kafka_admin import ensure_topic

log = logging.getLogger("producer")
TICK_S = 0.05


def run(rate: float, duration: float, bootstrap: str, topic: str, run_id: str, seed: int, out_dir: Path) -> dict:
    ensure_topic(bootstrap, topic)
    factory = EventFactory(run_id=run_id, seed=seed)
    counts = Counts()
    failures = 0

    def on_delivery(err, _msg):
        nonlocal failures
        if err is not None:
            failures += 1

    producer = Producer({
        "bootstrap.servers": bootstrap,
        "linger.ms": 20,
        "acks": "all",
        "enable.idempotence": True,
        "compression.type": "lz4",
    })

    def send(key: str | None, payload: bytes) -> None:
        while True:
            try:
                producer.produce(topic, key=key, value=payload, on_delivery=on_delivery)
                counts.sent += 1
                return
            except BufferError:
                producer.poll(0.05)

    scheduled: list[tuple[float, int, str, object]] = []  # (due, seq, kind, data)
    seq = 0
    bursts_started: dict[str, int] = {}
    start = time.monotonic()
    started_at = datetime.now(timezone.utc)
    next_tick, carry, last_log = start, 0.0, start

    while True:
        mono = time.monotonic()
        elapsed = mono - start
        if duration and elapsed >= duration:
            break
        now = datetime.now(timezone.utc)

        carry += rate * TICK_S
        n, carry = int(carry), carry - int(carry)
        for _ in range(n):
            kind = factory.pick_kind(elapsed)
            if kind == "malformed":
                send(None, factory.malformed())
                counts.malformed += 1
                continue
            event = factory.ride(now, factory.delay_for(kind))
            payload = encode(event)
            send(event["event_id"], payload)
            counts.unique += 1
            setattr(counts, kind, getattr(counts, kind) + 1)
            if kind == "normal" and factory.rng.random() < factory.mix.duplicate:
                seq += 1
                heapq.heappush(scheduled, (mono + factory.rng.uniform(1, 10), seq, "duplicate", (event["event_id"], payload)))

        # Fraud bursts: start at second 0-10 and 10-30 of each minute so all 6 rides share one minute.
        minute = now.strftime("%Y%m%d%H%M")
        started = bursts_started.get(minute, 0)
        room_left = not duration or elapsed + 20 < duration
        if room_left and started < factory.mix.bursts_per_minute and now.second >= 10 * started and now.second <= 30:
            user = factory.next_burst_user()
            counts.burst_users += 1
            bursts_started[minute] = started + 1
            for i in range(BURST_RIDES):
                seq += 1
                heapq.heappush(scheduled, (mono + i * 3, seq, "burst", user))

        while scheduled and scheduled[0][0] <= mono:
            _, _, kind, data = heapq.heappop(scheduled)
            if kind == "duplicate":
                key, payload = data
                send(key, payload)
                counts.duplicate += 1
            else:
                event = factory.ride(datetime.now(timezone.utc), 0, user_id=data)
                send(event["event_id"], encode(event))
                counts.unique += 1
                counts.burst_rides += 1

        producer.poll(0)
        if mono - last_log >= 10:
            log.info("run %s: %d sent in %.0f s (%.0f/s)", run_id, counts.sent, elapsed, counts.sent / max(elapsed, 1e-9))
            last_log = mono
        next_tick += TICK_S
        time.sleep(max(0.0, next_tick - time.monotonic()))

    # Send what is still scheduled (pending duplicates and burst rides), then wait for delivery.
    for _, _, kind, data in sorted(scheduled):
        if kind == "duplicate":
            send(data[0], data[1])
            counts.duplicate += 1
        else:
            event = factory.ride(datetime.now(timezone.utc), 0, user_id=data)
            send(event["event_id"], encode(event))
            counts.unique += 1
            counts.burst_rides += 1
    producer.flush(30)
    ended_at = datetime.now(timezone.utc)

    seconds = (ended_at - started_at).total_seconds()
    summary = {
        "run_id": run_id,
        "target_rate_per_s": rate,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "seconds": round(seconds, 1),
        "achieved_rate_per_s": round(counts.sent / seconds, 1),
        "delivery_failures": failures,
        "counts": asdict(counts),
        "expected_rides": counts.unique - counts.too_late,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{run_id}.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log.info("summary: %s", json.dumps(summary))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate", type=float, default=200, help="events per second")
    parser.add_argument("--duration", type=float, default=0, help="seconds; 0 = run until stopped")
    parser.add_argument("--run-id", default=datetime.now(timezone.utc).strftime("r%Y%m%d%H%M%S"))
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", type=Path, default=Path("data/runs"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run(
        rate=args.rate,
        duration=args.duration,
        bootstrap=os.getenv("KAFKA_BOOTSTRAP", "localhost:9092"),
        topic=os.getenv("KAFKA_TOPIC", "rides"),
        run_id=args.run_id,
        seed=args.seed,
        out_dir=args.out,
    )


if __name__ == "__main__":
    main()
