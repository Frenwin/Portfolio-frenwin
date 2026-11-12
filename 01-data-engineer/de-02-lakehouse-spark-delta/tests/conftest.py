import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("SPARK_DRIVER_MEMORY", "1g")
os.environ.setdefault("SPARK_SHUFFLE_PARTITIONS", "2")

from lakehouse.config import Tables, build_spark  # noqa: E402


@pytest.fixture(scope="session")
def spark(tmp_path_factory):
    root = tmp_path_factory.mktemp("lakehouse")
    session = build_spark("lakehouse-tests", root=str(root))
    yield session
    session.stop()


@pytest.fixture
def tables(tmp_path):
    return Tables(root=str(tmp_path / "lakehouse"))


@pytest.fixture
def landing(tmp_path):
    path = tmp_path / "landing"
    path.mkdir()
    (path / "taxi_zone_lookup.csv").write_text(
        "LocationID,Borough,Zone,service_zone\n"
        "132,Queens,JFK Airport,Airports\n"
        "161,Manhattan,Midtown Center,Yellow Zone\n"
        "236,Manhattan,Upper East Side North,Yellow Zone\n",
        encoding="utf-8",
    )
    return path
