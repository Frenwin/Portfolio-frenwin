"""Simulated ride-hailing events for Jakarta, with the faults real streams have.

Each emitted message is one of:
  normal     on time (0-2 s delay)
  late       20-90 s old: inside the watermark, must still be counted
  too_late   5-10 min old: beyond the watermark, must be dropped
  duplicate  an exact re-send of an earlier event (producer retry), must be counted once
  malformed  bytes that are not valid JSON, must land in rejected_events
  burst      one user taking 6 rides within 15 s of the same minute, must raise a fraud alert
"""

from __future__ import annotations

import json
import random
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

# Zone name -> relative demand weight
ZONES: dict[str, int] = {
    "Sudirman": 14, "Kuningan": 11, "Menteng": 9, "Senayan": 8, "Kemang": 7,
    "Kebayoran Baru": 7, "Tebet": 6, "Kelapa Gading": 6, "Pantai Indah Kapuk": 5,
    "Grogol": 5, "Cawang": 5, "Pasar Minggu": 4, "Cilandak": 4, "Cengkareng": 3,
    "Kota Tua": 3, "Ancol": 3,
}
PAYMENT_METHODS = {"ewallet": 62, "cash": 23, "card": 15}
EVENT_NAMESPACE = uuid.UUID("6f1c2a52-8d3e-4b7a-9c1d-2e5f8a9b0c3d")
BURST_RIDES = 6
FRAUD_MIN_RIDES = 5


@dataclass
class FaultMix:
    duplicate: float = 0.01
    late: float = 0.02
    too_late: float = 0.005
    malformed: float = 0.003
    bursts_per_minute: int = 2
    warmup_seconds: int = 30  # no too-late events before the first watermark exists


@dataclass
class Counts:
    sent: int = 0
    unique: int = 0
    normal: int = 0
    late: int = 0
    too_late: int = 0
    duplicate: int = 0
    malformed: int = 0
    burst_users: int = 0
    burst_rides: int = 0


@dataclass
class EventFactory:
    run_id: str
    seed: int = 7
    # Large enough that ordinary users almost never reach the fraud threshold by chance:
    # at 1,000 rides/s that is 0.03 rides per user-minute, so P(>= 5) is about 2e-10.
    n_users: int = 2_000_000
    n_drivers: int = 20_000
    mix: FaultMix = field(default_factory=FaultMix)

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)
        self._zones = list(ZONES)
        self._zone_w = list(ZONES.values())
        self._pay = list(PAYMENT_METHODS)
        self._pay_w = list(PAYMENT_METHODS.values())
        self._burst_seq = 0

    def ride(self, now: datetime, delay_s: float = 0.0, user_id: str | None = None) -> dict:
        distance = round(min(max(self.rng.lognormvariate(1.6, 0.6), 0.8), 60.0), 2)
        fare = int(round((8_000 + 3_500 * distance) * self.rng.uniform(0.9, 1.3), -2))
        return {
            # Namespaced by run_id: two runs with the same seed must never produce the same id,
            # or the idempotent sink would treat real rides as duplicates.
            "event_id": str(uuid.uuid5(EVENT_NAMESPACE, f"{self.run_id}:{self.rng.getrandbits(128)}")),
            "event_type": "ride_completed",
            "run_id": self.run_id,
            "event_ts": iso(now - timedelta(seconds=delay_s)),
            "produced_at": iso(now),
            "user_id": user_id or f"u{self.rng.randrange(self.n_users):07d}",
            "driver_id": f"d{self.rng.randrange(self.n_drivers):05d}",
            "zone": self.rng.choices(self._zones, self._zone_w)[0],
            "payment_method": self.rng.choices(self._pay, self._pay_w)[0],
            "distance_km": distance,
            "fare_idr": fare,
        }

    def pick_kind(self, elapsed_s: float) -> str:
        r = self.rng.random()
        m = self.mix
        if r < m.malformed:
            return "malformed"
        r -= m.malformed
        if r < m.too_late and elapsed_s >= m.warmup_seconds:
            return "too_late"
        r -= m.too_late
        if r < m.late:
            return "late"
        return "normal"

    def delay_for(self, kind: str) -> float:
        if kind == "too_late":
            return self.rng.uniform(300, 600)
        if kind == "late":
            return self.rng.uniform(20, 90)
        return self.rng.uniform(0, 2)

    def malformed(self) -> bytes:
        return self.rng.choice([b'{"event_id": "broken"', b"not json at all", b'{"fare_idr": }'])

    def next_burst_user(self) -> str:
        self._burst_seq += 1
        return f"burst-{self.run_id}-{self._burst_seq:04d}"


def iso(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).isoformat(timespec="milliseconds")


def encode(event: dict) -> bytes:
    return json.dumps(event, separators=(",", ":")).encode("utf-8")
