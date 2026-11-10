import os
from pathlib import Path

import pytest

from ingestion.load_raw import count_records, load_table, read_header, table_name_for


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("olist_orders_dataset.csv", "orders"),
        ("olist_order_items_dataset.csv", "order_items"),
        ("product_category_name_translation.csv", "product_category_name_translation"),
    ],
)
def test_table_name_for(filename, expected):
    assert table_name_for(Path(filename)) == expected


def test_table_name_rejects_unsafe_identifier():
    with pytest.raises(ValueError):
        table_name_for(Path("orders; drop table x.csv"))


def test_read_header_strips_bom_and_lowercases(tmp_path):
    path = tmp_path / "t.csv"
    path.write_bytes("﻿Product_Category_Name,english\nbeleza,beauty\n".encode("utf-8"))
    assert read_header(path) == ["product_category_name", "english"]


def test_read_header_rejects_duplicate_columns(tmp_path):
    path = tmp_path / "t.csv"
    path.write_text("a,a\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_header(path)


def test_count_records_counts_quoted_newlines_once(tmp_path):
    path = tmp_path / "t.csv"
    path.write_text('id,message\n1,"line one\nline two"\n2,plain\n', encoding="utf-8")
    assert count_records(path) == 2


requires_db = pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1", reason="set RUN_DB_TESTS=1 with a reachable warehouse"
)


@requires_db
def test_load_is_idempotent_and_replaces_data(tmp_path):
    from ingestion.load_raw import connect_from_env

    path = tmp_path / "olist_widgets_dataset.csv"
    path.write_text('widget_id,note\n1,"multi\nline"\n2,\n', encoding="utf-8")
    conn = connect_from_env()
    try:
        assert load_table(conn, path, schema="test_raw").rows_loaded == 2
        assert load_table(conn, path, schema="test_raw").rows_loaded == 2  # rerun: same result

        path.write_text("widget_id,note\n3,x\n", encoding="utf-8")
        assert load_table(conn, path, schema="test_raw").rows_loaded == 1  # replaced, not appended

        with conn.cursor() as cur:
            cur.execute("select widget_id, _source_file from test_raw.widgets")
            assert cur.fetchall() == [("3", "olist_widgets_dataset.csv")]
            cur.execute("drop schema test_raw cascade")
        conn.commit()
    finally:
        conn.close()
