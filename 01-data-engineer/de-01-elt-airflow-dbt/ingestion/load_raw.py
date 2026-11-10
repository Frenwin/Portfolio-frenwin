"""Load Olist CSV files into the ``raw`` schema of the warehouse.

Each CSV becomes one table of ``text`` columns plus two audit columns
(``_loaded_at``, ``_source_file``). A load runs in a single transaction:

* table missing or columns changed -> drop (cascade) and recreate
* table unchanged                  -> truncate
* then ``COPY`` the file and check the row count against the file

so re-running a load is idempotent and a failed load leaves the previous data intact.
Typing happens downstream in dbt staging models.

Usage:
    python -m ingestion.load_raw --data-dir data/raw
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg2
from psycopg2 import sql

log = logging.getLogger(__name__)

# Review messages can be long; 2**31 - 1 also fits a C long on Windows.
csv.field_size_limit(2**31 - 1)

_IDENTIFIER = re.compile(r"[a-z_][a-z0-9_]*")
_AUDIT_COLUMNS = ("_loaded_at", "_source_file")


@dataclass(frozen=True)
class LoadResult:
    table: str
    rows_loaded: int


def table_name_for(path: Path) -> str:
    """``olist_orders_dataset.csv`` -> ``orders``."""
    name = path.stem.lower()
    name = re.sub(r"^olist_", "", name)
    name = re.sub(r"_dataset$", "", name)
    _check_identifier(name, path)
    return name


def read_header(path: Path) -> list[str]:
    """Column names from the first line, with any UTF-8 BOM removed."""
    with path.open(encoding="utf-8-sig", newline="") as fh:
        header = next(csv.reader(fh), None)
    if not header:
        raise ValueError(f"{path.name}: file is empty")
    columns = [c.strip().lower() for c in header]
    for column in columns:
        _check_identifier(column, path)
    if len(set(columns)) != len(columns):
        raise ValueError(f"{path.name}: duplicate column names {columns}")
    return columns


def count_records(path: Path) -> int:
    """Number of CSV records excluding the header (quoted newlines count once)."""
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.reader(fh)
        next(reader, None)
        return sum(1 for _ in reader)


def load_table(conn, path: Path, schema: str = "raw") -> LoadResult:
    """Replace ``schema.<table>`` with the contents of ``path`` in one transaction."""
    _check_identifier(schema, path)
    table = table_name_for(path)
    columns = read_header(path)
    expected_rows = count_records(path)
    target = sql.Identifier(schema, table)

    with conn:  # commits on success, rolls back on any exception
        with conn.cursor() as cur:
            cur.execute(sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(sql.Identifier(schema)))
            existing = _existing_columns(cur, schema, table)

            if existing == columns:
                cur.execute(sql.SQL("TRUNCATE {}").format(target))
            else:
                if existing:
                    log.warning("%s.%s: columns changed, recreating table", schema, table)
                cur.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(target))
                cur.execute(
                    sql.SQL(
                        "CREATE TABLE {} ({}, _loaded_at timestamptz NOT NULL DEFAULT now(), "
                        "_source_file text NOT NULL)"
                    ).format(
                        target,
                        sql.SQL(", ").join(sql.SQL("{} text").format(sql.Identifier(c)) for c in columns),
                    )
                )

            cur.execute(
                sql.SQL("ALTER TABLE {} ALTER COLUMN _source_file SET DEFAULT {}").format(
                    target, sql.Literal(path.name)
                )
            )
            copy = sql.SQL("COPY {} ({}) FROM STDIN WITH (FORMAT csv, HEADER true, ENCODING 'UTF8')").format(
                target, sql.SQL(", ").join(map(sql.Identifier, columns))
            )
            with path.open("rb") as fh:
                cur.copy_expert(copy.as_string(conn), fh)
            rows_loaded = cur.rowcount

            if rows_loaded != expected_rows:
                raise ValueError(
                    f"{schema}.{table}: loaded {rows_loaded} rows but {path.name} has {expected_rows}"
                )

    log.info("%s.%s: loaded %d rows from %s", schema, table, rows_loaded, path.name)
    return LoadResult(table=table, rows_loaded=rows_loaded)


def connect_from_env():
    return psycopg2.connect(
        host=os.getenv("WAREHOUSE_HOST", "localhost"),
        port=int(os.getenv("WAREHOUSE_PORT", "5434")),
        dbname=os.getenv("WAREHOUSE_DB", "warehouse"),
        user=os.getenv("WAREHOUSE_USER", "warehouse"),
        password=os.getenv("WAREHOUSE_PASSWORD", "warehouse"),
    )


def _existing_columns(cur, schema: str, table: str) -> list[str]:
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
        """,
        (schema, table),
    )
    return [row[0] for row in cur.fetchall() if row[0] not in _AUDIT_COLUMNS]


def _check_identifier(name: str, path: Path) -> None:
    if not _IDENTIFIER.fullmatch(name):
        raise ValueError(f"{path.name}: '{name}' is not a safe SQL identifier")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--schema", default="raw")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    files = sorted(args.data_dir.glob("*.csv"))
    if not files:
        log.error("No CSV files found in %s", args.data_dir)
        return 1

    conn = connect_from_env()
    try:
        for path in files:
            load_table(conn, path, args.schema)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
