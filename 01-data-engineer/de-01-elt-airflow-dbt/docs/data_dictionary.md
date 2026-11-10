# Data dictionary — marts

All tables live in the `marts` schema. Money is in BRL; timestamps are kept exactly as provided by Olist.

## fct_orders

Grain: one row per order (99,441 rows).

| Column | Type | Description |
| --- | --- | --- |
| order_id | text | Primary key |
| customer_sk | text | FK to `dim_customers`: the customer's address version at purchase time |
| customer_unique_id | text | The person behind the order |
| purchase_date_key | int | FK to `dim_date` (YYYYMMDD) |
| order_status | text | created, approved, invoiced, processing, shipped, delivered, canceled, unavailable |
| purchased_at, approved_at, delivered_to_carrier_at, delivered_to_customer_at, estimated_delivery_at | timestamp | Order lifecycle |
| item_count, distinct_sellers | int | From order items (0 for orders without items) |
| items_value, freight_value, order_value | numeric | Sum of item prices, freight, and both |
| payment_value, payment_count, primary_payment_type, max_installments | mixed | From payments; primary type = method with the largest amount |
| avg_review_score, latest_review_score, review_count | mixed | From reviews (some orders have several) |
| hours_to_approve, days_to_deliver | numeric | Durations from purchase |
| delivery_delay_days | int | Delivered date minus estimated date (negative = early) |
| is_delivered_late | bool | Delivered after the estimated date; null if not delivered |

## fct_order_items

Grain: one row per item in an order (112,650 rows). Incremental, delete+insert on `order_item_key`.

| Column | Type | Description |
| --- | --- | --- |
| order_item_key | text | Primary key: `order_id-order_item_number` |
| order_id | text | FK to `fct_orders` |
| order_item_number | int | Position of the item in the order |
| product_id / seller_id | text | FKs to `dim_products` / `dim_sellers` |
| customer_sk | text | FK to `dim_customers` |
| purchase_date_key | int | FK to `dim_date` |
| purchased_at, order_status | mixed | Copied from the order for filtering without a join |
| shipping_limit_at | timestamp | Deadline for the seller to hand over to the carrier |
| price, freight_value, item_total | numeric | Item price, freight, and both |

## dim_customers (SCD Type 2)

Grain: one row per address version of a customer (96,355 rows for 96,096 customers).

| Column | Type | Description |
| --- | --- | --- |
| customer_sk | text | Primary key: md5 of `customer_unique_id-version_number` |
| customer_unique_id | text | Natural key of the person |
| version_number | int | 1 = first known address |
| zip_code_prefix, city, state | text | Address for this version |
| latitude, longitude | double | Average location of the zip code (null for 270 versions whose zip is not in the geolocation data) |
| orders_in_version | int | Orders placed at this address |
| valid_from / valid_to | timestamp | First purchase at this address / start of the next version (null = current) |
| is_current | bool | Latest version |

## dim_products

Grain: one row per product (32,951 rows).

| Column | Type | Description |
| --- | --- | --- |
| product_id | text | Primary key |
| category_name | text | English category; Portuguese if untranslated; `unknown` if missing |
| category_name_pt | text | Original Portuguese category |
| name_length, description_length, photos_qty | int | Listing attributes |
| weight_g, length_cm, height_cm, width_cm, volume_cm3 | numeric | Package dimensions |

## dim_sellers

Grain: one row per seller (3,095 rows).

| Column | Type | Description |
| --- | --- | --- |
| seller_id | text | Primary key |
| zip_code_prefix, city, state | text | Seller location |
| latitude, longitude | double | Average location of the zip code |

## dim_date

Grain: one row per day from the first purchase to the last delivery or estimate (800 rows).

| Column | Type | Description |
| --- | --- | --- |
| date_key | int | Primary key, YYYYMMDD |
| date_day | date | Calendar date |
| year, quarter, month, month_name, month_start, week_start | mixed | Calendar attributes (ISO weeks start Monday) |
| day_of_week, day_name, is_weekend | mixed | 1 = Monday … 7 = Sunday |
