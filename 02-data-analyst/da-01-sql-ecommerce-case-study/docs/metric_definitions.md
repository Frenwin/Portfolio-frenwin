# Metric definitions

Every query in this case study uses these definitions. Source: the `marts` schema built in [DE-1](../../../01-data-engineer/de-01-elt-airflow-dbt/).

| Metric | Definition | SQL |
| --- | --- | --- |
| **Analysis window** | Orders purchased 2017-01-01 to 2018-08-31 (20 full months). 2016 and Sep–Oct 2018 hold under 350 orders in total and are collection artefacts, not business trends. | `purchased_at >= '2017-01-01' AND purchased_at < '2018-09-01'` |
| **Valid order** | Any order not cancelled and not marked unavailable | `order_status NOT IN ('canceled', 'unavailable')` |
| **GMV** (gross merchandise value) | Sum of item prices of valid orders, excluding freight | `sum(items_value)` or `sum(price)` |
| **Order value** | Item prices plus freight | `items_value + freight_value` |
| **AOV** (average order value) | GMV ÷ valid orders | `sum(items_value) / count(*)` |
| **Customer** | A person, identified by `customer_unique_id` (Olist issues a new `customer_id` per order) | `customer_unique_id` |
| **Repeat customer** | Customer with 2 or more valid orders in the window | `count(*) >= 2` |
| **Late delivery** | Delivered on a later calendar day than the estimate given at purchase | `is_delivered_late` |
| **Delivery days** | Days from purchase to delivery to the customer | `days_to_deliver` |
| **Review score** | Average score (1–5) of the reviews attached to an order | `avg_review_score` |
| **Freight share** | Freight ÷ item price for the same items | `sum(freight_value) / sum(price)` |

Money is in Brazilian reais (BRL). Timestamps are as recorded by Olist.
