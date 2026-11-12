import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="session")
def spark():
    from pyspark.sql import SparkSession

    session = (
        SparkSession.builder.master("local[1]")
        .appName("stream-tests")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.sql.shuffle.partitions", "1")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )
    yield session
    session.stop()


@pytest.fixture
def pg():
    if os.getenv("RUN_DB_TESTS") != "1":
        pytest.skip("set RUN_DB_TESTS=1 with the schema from postgres/init loaded")
    from streaming.sink import connect

    conn = connect()
    with conn, conn.cursor() as cur:
        cur.execute(
            "TRUNCATE rides, zone_demand_1m, zone_demand_final, user_activity_1m, rejected_events, stream_batches"
        )
    yield conn
    conn.close()
