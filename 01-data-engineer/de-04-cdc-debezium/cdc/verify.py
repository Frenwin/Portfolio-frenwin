"""Prove the replica equals the source, and measure how far behind it is."""

from __future__ import annotations

import time

EPOCH_US = "(extract(epoch FROM {c}) * 1000000)::bigint"

# table -> (order key, columns compared). Values are normalised so type differences
# between source and replica (e.g. numeric scale, timestamp precision) cannot hide or fake a mismatch.
TABLES: dict[str, tuple[str, list[str]]] = {
    "customers": ("id", ["id", "name", "email", "city", EPOCH_US.format(c="updated_at")]),
    "products": ("id", ["id", "name", "category", "price_idr::numeric(12,2)", "stock", EPOCH_US.format(c="updated_at")]),
    "orders": ("id", ["id", "customer_id", "status", "total_idr::numeric(14,2)",
                      EPOCH_US.format(c="created_at"), EPOCH_US.format(c="updated_at")]),
    "order_items": ("order_id, line_no", ["order_id", "line_no", "product_id", "quantity", "unit_price_idr::numeric(12,2)"]),
}


def has_column(conn, table: str, column: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s", (table, column))
        return cur.fetchone() is not None


def checksum_sql(table: str, key: str, columns: list[str]) -> str:
    row = " || '~' || ".join(f"coalesce(({c})::text, '<null>')" for c in columns)
    return f"SELECT count(*), md5(coalesce(string_agg({row}, '|' ORDER BY {key}), '')) FROM {table}"


def checksums(conn, tables: dict = TABLES, extra_customer_columns: tuple[str, ...] = ()) -> dict[str, tuple[int, str]]:
    result = {}
    conn.rollback()
    with conn.cursor() as cur:
        for table, (key, columns) in tables.items():
            cols = columns + list(extra_customer_columns) if table == "customers" else columns
            cur.execute(checksum_sql(table, key, cols))
            result[table] = cur.fetchone()
    conn.rollback()
    return result


def compare(source, replica) -> dict[str, dict]:
    extra = ("loyalty_tier",) if has_column(source, "customers", "loyalty_tier") else ()
    try:
        s, r = checksums(source, extra_customer_columns=extra), checksums(replica, extra_customer_columns=extra)
    except Exception as exc:  # e.g. a replica table or column not created yet: report why, keep waiting
        source.rollback()
        replica.rollback()
        reason = str(exc).splitlines()[0]
        return {t: {"source_rows": None, "replica_rows": None, "equal": False, "error": reason} for t in TABLES}
    return {t: {"source_rows": s[t][0], "replica_rows": r[t][0], "equal": s[t] == r[t]} for t in TABLES}


def wait_until_equal(source, replica, timeout_s: float = 300, poll_s: float = 0.5) -> tuple[float, dict]:
    start = time.monotonic()
    while True:
        result = compare(source, replica)
        if all(v["equal"] for v in result.values()):
            return time.monotonic() - start, result
        if time.monotonic() - start > timeout_s:
            raise TimeoutError(f"replica did not converge in {timeout_s} s: {result}")
        time.sleep(poll_s)


def probe_lag(source, replica, timeout_s: float = 60) -> float:
    """Insert a row in the source and time how long until it is readable in the replica."""
    with source, source.cursor() as cur:
        cur.execute("INSERT INTO cdc_probe DEFAULT VALUES RETURNING id")
        probe_id = cur.fetchone()[0]
    start = time.monotonic()
    while time.monotonic() - start < timeout_s:
        with replica, replica.cursor() as cur:
            cur.execute("SELECT 1 FROM cdc_probe WHERE id = %s", (probe_id,))
            if cur.fetchone():
                return time.monotonic() - start
        time.sleep(0.02)
    raise TimeoutError(f"probe {probe_id} not replicated in {timeout_s} s")
