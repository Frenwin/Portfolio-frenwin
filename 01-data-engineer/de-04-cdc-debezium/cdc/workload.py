"""Simulated online-shop traffic on the source database.

Every operation is its own transaction, as an application would issue it:
new orders, status changes, cancellations, price changes, customers moving city,
purging cancelled orders (hard delete, cascading to items), and, once, a schema change.
"""

from __future__ import annotations

import random
import time
from collections import Counter
from dataclasses import dataclass, field

from psycopg2.extras import execute_values

NEXT_STATUS = {"pending": "paid", "paid": "packed", "packed": "shipped", "shipped": "delivered"}
OPEN_STATUSES = tuple(NEXT_STATUS)
CITIES = ["Jakarta", "Bandung", "Surabaya", "Medan", "Semarang", "Makassar", "Yogyakarta", "Denpasar", "Palembang", "Balikpapan"]
CATEGORIES = ["electronics", "fashion", "home", "beauty", "groceries", "sports", "books", "toys"]
TIERS = ["basic", "silver", "gold"]

# operation -> weight
OPERATIONS = {
    "new_order": 35,
    "advance_status": 40,
    "cancel_order": 5,
    "change_price": 8,
    "move_customer": 7,
    "purge_cancelled": 5,
}


def next_status(status: str) -> str | None:
    return NEXT_STATUS.get(status)


@dataclass
class Workload:
    seed: int = 11
    counts: Counter = field(default_factory=Counter)
    has_loyalty_tier: bool = False

    def __post_init__(self) -> None:
        self.rng = random.Random(self.seed)

    # ---------- seeding (before CDC starts: captured by the snapshot) ----------
    def seed_data(self, conn, customers: int = 5_000, products: int = 300, orders: int = 20_000) -> None:
        r = self.rng
        with conn, conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM customers")
            if cur.fetchone()[0]:
                return
            execute_values(cur, "INSERT INTO customers (name, email, city) VALUES %s", [
                (f"Customer {i}", f"customer{i}@example.com", r.choice(CITIES)) for i in range(customers)
            ], page_size=1000)
            execute_values(cur, "INSERT INTO products (name, category, price_idr, stock) VALUES %s", [
                (f"Product {i}", r.choice(CATEGORIES), round(r.uniform(15_000, 2_500_000), -2), r.randint(0, 500))
                for i in range(products)
            ], page_size=1000)
            cur.execute("SELECT id, price_idr FROM products")
            prices = dict(cur.fetchall())
            statuses = ["pending", "paid", "packed", "shipped", "delivered", "delivered", "delivered", "cancelled"]
            order_rows = [(r.randint(1, customers), r.choice(statuses), 0) for _ in range(orders)]
            ids = [row[0] for row in execute_values(
                cur, "INSERT INTO orders (customer_id, status, total_idr) VALUES %s RETURNING id",
                order_rows, page_size=1000, fetch=True)]
            items = []
            for order_id in ids:
                for line in range(1, r.randint(1, 4) + 1):
                    pid = r.randint(1, products)
                    items.append((order_id, line, pid, r.randint(1, 3), prices[pid]))
            execute_values(cur, "INSERT INTO order_items (order_id, line_no, product_id, quantity, unit_price_idr) VALUES %s",
                           items, page_size=2000)
            cur.execute("""UPDATE orders o SET total_idr = s.total FROM (
                             SELECT order_id, sum(quantity * unit_price_idr) AS total FROM order_items GROUP BY order_id) s
                           WHERE s.order_id = o.id""")

    # ---------- live traffic (after CDC starts: captured from the WAL) ----------
    def step(self, conn) -> str:
        op = self.rng.choices(list(OPERATIONS), list(OPERATIONS.values()))[0]
        with conn, conn.cursor() as cur:
            done = getattr(self, f"_{op}")(cur)
        self.counts[op if done else f"{op}_skipped"] += 1
        return op

    def add_loyalty_tier(self, conn) -> None:
        """Online schema change on a replicated table."""
        with conn, conn.cursor() as cur:
            cur.execute("ALTER TABLE customers ADD COLUMN IF NOT EXISTS loyalty_tier text")
        self.has_loyalty_tier = True
        self.counts["schema_change"] += 1

    def _random_id(self, cur, table: str, where: str = "TRUE", params: tuple = ()) -> int | None:
        cur.execute(f"SELECT max(id) FROM {table}")
        top = cur.fetchone()[0] or 0
        if not top:
            return None
        start = self.rng.randint(1, top)
        cur.execute(f"SELECT id FROM {table} WHERE id >= %s AND {where} ORDER BY id LIMIT 1", (start, *params))
        row = cur.fetchone()
        if row is None:
            cur.execute(f"SELECT id FROM {table} WHERE {where} ORDER BY id LIMIT 1", params)
            row = cur.fetchone()
        return row[0] if row else None

    def _new_order(self, cur) -> bool:
        customer = self._random_id(cur, "customers")
        cur.execute("INSERT INTO orders (customer_id, status, total_idr) VALUES (%s, 'pending', 0) RETURNING id", (customer,))
        order_id = cur.fetchone()[0]
        for line in range(1, self.rng.randint(1, 4) + 1):
            product = self._random_id(cur, "products")
            cur.execute(
                "INSERT INTO order_items (order_id, line_no, product_id, quantity, unit_price_idr) "
                "SELECT %s, %s, id, %s, price_idr FROM products WHERE id = %s",
                (order_id, line, self.rng.randint(1, 3), product),
            )
        cur.execute("UPDATE orders SET total_idr = (SELECT sum(quantity * unit_price_idr) FROM order_items WHERE order_id = %s) "
                    "WHERE id = %s", (order_id, order_id))
        return True

    def _advance_status(self, cur) -> bool:
        order_id = self._random_id(cur, "orders", "status = ANY(%s)", (list(OPEN_STATUSES),))
        if order_id is None:
            return False
        cur.execute("""UPDATE orders SET status = CASE status
                         WHEN 'pending' THEN 'paid' WHEN 'paid' THEN 'packed'
                         WHEN 'packed' THEN 'shipped' WHEN 'shipped' THEN 'delivered' END,
                       updated_at = now()
                       WHERE id = %s""", (order_id,))
        return True

    def _cancel_order(self, cur) -> bool:
        order_id = self._random_id(cur, "orders", "status IN ('pending', 'paid')")
        if order_id is None:
            return False
        cur.execute("UPDATE orders SET status = 'cancelled', updated_at = now() WHERE id = %s", (order_id,))
        return True

    def _change_price(self, cur) -> bool:
        product = self._random_id(cur, "products")
        cur.execute("UPDATE products SET price_idr = round(price_idr * %s, -2), updated_at = now() WHERE id = %s",
                    (self.rng.uniform(0.85, 1.15), product))
        return True

    def _move_customer(self, cur) -> bool:
        customer = self._random_id(cur, "customers")
        if self.has_loyalty_tier:
            cur.execute("UPDATE customers SET city = %s, loyalty_tier = %s, updated_at = now() WHERE id = %s",
                        (self.rng.choice(CITIES), self.rng.choice(TIERS), customer))
        else:
            cur.execute("UPDATE customers SET city = %s, updated_at = now() WHERE id = %s", (self.rng.choice(CITIES), customer))
        return True

    def _purge_cancelled(self, cur) -> bool:
        order_id = self._random_id(cur, "orders", "status = 'cancelled'")
        if order_id is None:
            return False
        cur.execute("DELETE FROM orders WHERE id = %s", (order_id,))  # items go with it (ON DELETE CASCADE)
        return True

    def run(self, conn, rate_per_s: float, duration_s: float, schema_change_at_s: float | None = None) -> Counter:
        start = time.monotonic()
        next_at = start
        while (elapsed := time.monotonic() - start) < duration_s:
            if schema_change_at_s is not None and not self.has_loyalty_tier and elapsed >= schema_change_at_s:
                self.add_loyalty_tier(conn)
            self.step(conn)
            next_at += 1.0 / rate_per_s
            time.sleep(max(0.0, next_at - time.monotonic()))
        return self.counts
