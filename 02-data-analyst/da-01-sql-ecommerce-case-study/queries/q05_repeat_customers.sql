-- Q5. How many customers come back, and how long until their second order?
-- Techniques: LEAD to find each customer's next order, ROW_NUMBER, percentile_cont for the median.
WITH orders AS (
    SELECT customer_unique_id, purchased_at,
           lead(purchased_at) OVER (PARTITION BY customer_unique_id ORDER BY purchased_at) AS next_purchase,
           row_number()       OVER (PARTITION BY customer_unique_id ORDER BY purchased_at) AS order_number
    FROM marts.fct_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
      AND purchased_at >= '2017-01-01' AND purchased_at < '2018-09-01'
),
per_customer AS (
    SELECT customer_unique_id, count(*) AS orders FROM orders GROUP BY 1
),
second_orders AS (
    SELECT extract(epoch FROM next_purchase - purchased_at) / 86400 AS days_to_second
    FROM orders
    WHERE order_number = 1 AND next_purchase IS NOT NULL
)
SELECT
    (SELECT count(*) FROM per_customer)                                                         AS customers,
    (SELECT count(*) FROM per_customer WHERE orders >= 2)                                       AS repeat_customers,
    (SELECT round(100.0 * count(*) FILTER (WHERE orders >= 2) / count(*), 2) FROM per_customer)  AS repeat_rate_pct,
    (SELECT round(100.0 * sum(orders) FILTER (WHERE orders >= 2) / sum(orders), 2) FROM per_customer) AS orders_from_repeaters_pct,
    (SELECT round(percentile_cont(0.5) WITHIN GROUP (ORDER BY days_to_second)::numeric, 1) FROM second_orders) AS median_days_to_second_order,
    (SELECT round(100.0 * count(*) FILTER (WHERE days_to_second < 1) / count(*), 1) FROM second_orders)        AS second_order_within_1_day_pct;
