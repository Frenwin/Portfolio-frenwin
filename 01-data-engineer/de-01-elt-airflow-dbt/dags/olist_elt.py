"""
### Olist ELT

1. **load_file** — one mapped task per CSV in `data/raw`, loaded into `raw.<table>` (idempotent, atomic).
2. **summarize** — logs row counts per table.
3. **dbt_source_freshness** — fails if any raw table was not loaded in the last 48 hours.
4. **dbt_build** — runs and tests staging → intermediate → marts in dependency order.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

from airflow.decorators import dag, task
from airflow.operators.bash import BashOperator

DATA_DIR = Path(os.environ.get("OLIST_DATA_DIR", "/opt/airflow/data/raw"))
DBT_DIR = os.environ.get("DBT_PROJECT_DIR", "/opt/airflow/dbt")
DBT = f"{os.environ.get('DBT_BIN', 'dbt')} --no-use-colors"
DBT_ARGS = f"--project-dir {DBT_DIR} --profiles-dir {DBT_DIR}"

log = logging.getLogger(__name__)


@dag(
    dag_id="olist_elt",
    schedule="@daily",
    start_date=datetime(2026, 11, 1),
    catchup=False,
    max_active_runs=1,
    default_args={"owner": "frenwin", "retries": 2, "retry_delay": timedelta(minutes=1)},
    tags=["olist", "elt", "dbt"],
    doc_md=__doc__,
)
def olist_elt():
    @task
    def list_source_files() -> list[str]:
        files = sorted(str(p) for p in DATA_DIR.glob("*.csv"))
        if not files:
            raise FileNotFoundError(f"No CSV files in {DATA_DIR}. See README: Get the data.")
        return files

    @task
    def load_file(path: str) -> dict:
        from ingestion.load_raw import connect_from_env, load_table

        conn = connect_from_env()
        try:
            result = load_table(conn, Path(path))
        finally:
            conn.close()
        return {"table": result.table, "rows": result.rows_loaded}

    @task
    def summarize(results: list[dict]) -> int:
        total = 0
        for r in sorted(results, key=lambda r: r["table"]):
            log.info("raw.%-36s %10d rows", r["table"], r["rows"])
            total += r["rows"]
        log.info("total %d rows across %d tables", total, len(results))
        return total

    freshness = BashOperator(
        task_id="dbt_source_freshness",
        bash_command=f"{DBT} source freshness {DBT_ARGS}",
    )
    build = BashOperator(
        task_id="dbt_build",
        bash_command=f"{DBT} build {DBT_ARGS}",
        retries=0,  # a failed dbt test is a data problem, not a transient one
    )

    loaded = load_file.expand(path=list_source_files())
    summarize(loaded) >> freshness >> build


olist_elt()
