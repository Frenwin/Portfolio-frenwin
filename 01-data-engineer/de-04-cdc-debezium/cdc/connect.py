"""Register Debezium connectors with the Kafka Connect REST API (idempotent PUT)."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

CONNECTORS = ("shop-source", "replica-sink")


def _request(method: str, path: str, body: dict | None = None) -> dict:
    url = os.getenv("CONNECT_URL", "http://localhost:8083") + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    return json.loads(raw) if raw else {}


def register(name: str, config_dir: Path = Path("connectors")) -> None:
    """Create or update a connector; PUT on /config makes re-running safe."""
    config = json.loads((config_dir / f"{name}.json").read_text(encoding="utf-8"))
    _request("PUT", f"/connectors/{name}/config", config)


def wait_running(name: str, timeout_s: float = 120) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            status = _request("GET", f"/connectors/{name}/status")
            tasks = status.get("tasks", [])
            if status["connector"]["state"] == "RUNNING" and tasks and all(t["state"] == "RUNNING" for t in tasks):
                return
            failed = [t for t in tasks if t["state"] == "FAILED"]
            if failed:
                raise RuntimeError(f"{name} failed: {failed[0].get('trace', '')[:2000]}")
        except urllib.error.HTTPError:
            pass
        time.sleep(1)
    raise TimeoutError(f"{name} not RUNNING after {timeout_s} s")


def plugins() -> list[str]:
    return [p["class"] for p in _request("GET", "/connector-plugins")]


def main() -> None:
    for name in CONNECTORS:
        register(name)
        wait_running(name)
        print(f"{name}: RUNNING")


if __name__ == "__main__":
    main()
