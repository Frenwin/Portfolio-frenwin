from cdc.verify import checksum_sql


def test_checksum_query_is_ordered_and_null_safe():
    sql = checksum_sql("orders", "id", ["id", "status"])
    assert "ORDER BY id" in sql
    assert "coalesce((status)::text, '<null>')" in sql


def test_checksum_detects_a_single_changed_value(replica):
    with replica, replica.cursor() as cur:
        cur.execute("CREATE TABLE cdc_test.a (id int PRIMARY KEY, price numeric(12,2), note text)")
        cur.execute("CREATE TABLE cdc_test.b (id int PRIMARY KEY, price numeric, note text)")  # looser type, as a sink may create
        cur.execute("INSERT INTO cdc_test.a VALUES (1, 10.50, NULL), (2, 99.00, 'x')")
        cur.execute("INSERT INTO cdc_test.b VALUES (1, 10.5, NULL), (2, 99, 'x')")
    cols = ["id", "price::numeric(12,2)", "note"]

    def checksum(table):
        with replica.cursor() as cur:
            cur.execute(checksum_sql(f"cdc_test.{table}", "id", cols))
            return cur.fetchone()

    assert checksum("a") == checksum("b")  # same data, different column types
    with replica, replica.cursor() as cur:
        cur.execute("UPDATE cdc_test.b SET note = 'y' WHERE id = 2")
    assert checksum("a") != checksum("b")
