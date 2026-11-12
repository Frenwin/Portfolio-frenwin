"""Download NYC TLC yellow taxi trip files and the taxi zone lookup into data/landing.

Usage:
    python scripts/download_tlc.py --months 2024-01 2024-02 2024-03
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

BASE = "https://d37ci6vzurychx.cloudfront.net"


def download(url: str, target: Path) -> None:
    if target.exists() and target.stat().st_size > 0:
        print(f"skip  {target.name} (already downloaded)")
        return
    tmp = target.with_suffix(target.suffix + ".part")
    with urllib.request.urlopen(url, timeout=120) as response, tmp.open("wb") as fh:
        while chunk := response.read(1 << 20):
            fh.write(chunk)
    tmp.replace(target)
    print(f"done  {target.name} ({target.stat().st_size / 1e6:.1f} MB)")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", nargs="+", default=["2024-01", "2024-02", "2024-03"])
    parser.add_argument("--out", type=Path, default=Path("data/landing"))
    args = parser.parse_args()

    for month in args.months:
        if not re.fullmatch(r"\d{4}-\d{2}", month):
            print(f"invalid month: {month} (expected YYYY-MM)", file=sys.stderr)
            return 1

    args.out.mkdir(parents=True, exist_ok=True)
    download(f"{BASE}/misc/taxi_zone_lookup.csv", args.out / "taxi_zone_lookup.csv")
    for month in args.months:
        name = f"yellow_tripdata_{month}.parquet"
        download(f"{BASE}/trip-data/{name}", args.out / name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
