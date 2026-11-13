import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def replica():
    if os.getenv("RUN_DB_TESTS") != "1":
        pytest.skip("set RUN_DB_TESTS=1 with replica-db/init loaded")
    import psycopg2

    conn = psycopg2.connect(os.getenv("TEST_DSN", os.getenv("REPLICA_DSN", "host=localhost port=5437 dbname=replica user=replica password=replica")))
    with conn, conn.cursor() as cur:
        cur.execute("CREATE SCHEMA IF NOT EXISTS cdc_test")
        cur.execute("SET search_path TO cdc_test, public")
        cur.execute("DROP TABLE IF EXISTS cdc_test.order_status_events CASCADE")
        cur.execute("CREATE TABLE cdc_test.order_status_events (LIKE public.order_status_events INCLUDING ALL)")
        cur.execute("""CREATE VIEW cdc_test.order_status_history AS
                       SELECT order_id, status, valid_from, valid_to, valid_to IS NULL AS is_current FROM (
                         SELECT order_id, op, status, changed_at AS valid_from,
                                lead(changed_at) OVER (PARTITION BY order_id ORDER BY lsn, changed_at) AS valid_to
                         FROM cdc_test.order_status_events) e WHERE op <> 'd'""")
    conn.cursor().execute("SET search_path TO cdc_test, public")
    yield conn
    conn.rollback()
    with conn, conn.cursor() as cur:
        cur.execute("DROP SCHEMA cdc_test CASCADE")
    conn.close()
