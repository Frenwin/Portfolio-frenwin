"""Build a small, referentially consistent sample of the Olist data for CI.

Takes the first N orders by order_id plus every order of customers who changed
address (so the SCD2 logic is exercised), then keeps only the customers, items,
payments, reviews, products, sellers and geolocation points those orders reference.

Usage:
    python scripts/make_sample.py --raw data/raw --out data/sample --orders 400
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

csv.field_size_limit(2**31 - 1)


def read(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader.fieldnames or []), list(reader)


def write(path: Path, header: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{path.name:45s} {len(rows):6d} rows")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=Path("data/raw"))
    parser.add_argument("--out", type=Path, default=Path("data/sample"))
    parser.add_argument("--orders", type=int, default=400)
    parser.add_argument("--movers", type=int, default=25, help="customers with an address change to include")
    parser.add_argument("--points-per-zip", type=int, default=3)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    f = lambda name: args.raw / name  # noqa: E731

    cust_h, customers = read(f("olist_customers_dataset.csv"))
    ord_h, orders = read(f("olist_orders_dataset.csv"))
    customer_by_id = {c["customer_id"]: c for c in customers}

    # customers whose consecutive orders have different addresses
    by_person = defaultdict(list)
    for c in customers:
        by_person[c["customer_unique_id"]].append(c)
    movers = sorted(
        p for p, cs in by_person.items()
        if len({(c["customer_zip_code_prefix"], c["customer_city"], c["customer_state"]) for c in cs}) > 1
    )[: args.movers]
    mover_customer_ids = {c["customer_id"] for p in movers for c in by_person[p]}

    base = {o["order_id"] for o in sorted(orders, key=lambda o: o["order_id"])[: args.orders]}
    keep_orders = [o for o in orders if o["order_id"] in base or o["customer_id"] in mover_customer_ids]
    order_ids = {o["order_id"] for o in keep_orders}
    customer_ids = {o["customer_id"] for o in keep_orders}

    items_h, items = read(f("olist_order_items_dataset.csv"))
    items = [r for r in items if r["order_id"] in order_ids]
    pay_h, payments = read(f("olist_order_payments_dataset.csv"))
    payments = [r for r in payments if r["order_id"] in order_ids]
    rev_h, reviews = read(f("olist_order_reviews_dataset.csv"))
    reviews = [r for r in reviews if r["order_id"] in order_ids]

    product_ids = {r["product_id"] for r in items}
    seller_ids = {r["seller_id"] for r in items}
    prod_h, products = read(f("olist_products_dataset.csv"))
    products = [r for r in products if r["product_id"] in product_ids]
    sell_h, sellers = read(f("olist_sellers_dataset.csv"))
    sellers = [r for r in sellers if r["seller_id"] in seller_ids]
    kept_customers = [customer_by_id[c] for c in sorted(customer_ids)]

    zips = {c["customer_zip_code_prefix"] for c in kept_customers} | {s["seller_zip_code_prefix"] for s in sellers}
    geo_h, geo = read(f("olist_geolocation_dataset.csv"))
    per_zip: dict[str, int] = defaultdict(int)
    geo_kept = []
    for g in geo:
        z = g["geolocation_zip_code_prefix"]
        if z in zips and per_zip[z] < args.points_per_zip:
            per_zip[z] += 1
            geo_kept.append(g)

    tr_h, translations = read(f("product_category_name_translation.csv"))

    write(args.out / "olist_customers_dataset.csv", cust_h, kept_customers)
    write(args.out / "olist_orders_dataset.csv", ord_h, keep_orders)
    write(args.out / "olist_order_items_dataset.csv", items_h, items)
    write(args.out / "olist_order_payments_dataset.csv", pay_h, payments)
    write(args.out / "olist_order_reviews_dataset.csv", rev_h, reviews)
    write(args.out / "olist_products_dataset.csv", prod_h, products)
    write(args.out / "olist_sellers_dataset.csv", sell_h, sellers)
    write(args.out / "olist_geolocation_dataset.csv", geo_h, geo_kept)
    write(args.out / "product_category_name_translation.csv", tr_h, translations)


if __name__ == "__main__":
    main()
