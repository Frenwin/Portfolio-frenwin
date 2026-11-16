-- Q10. When do customers buy? Day of week and time of day.
-- Techniques: join to the date dimension, extract(hour), share within each grain.
WITH orders AS (
    SELECT d.day_name, d.day_of_week, extract(hour FROM o.purchased_at)::int AS hour
    FROM marts.fct_orders o
    JOIN marts.dim_date d ON d.date_key = o.purchase_date_key
    WHERE o.order_status NOT IN ('canceled', 'unavailable')
      AND o.purchased_at >= '2017-01-01' AND o.purchased_at < '2018-09-01'
),
grains AS (
    SELECT 'day of week' AS grain, day_of_week AS sort_key, day_name AS label, count(*) AS orders
    FROM orders GROUP BY day_of_week, day_name
    UNION ALL
    SELECT 'time of day',
           CASE WHEN hour < 6 THEN 1 WHEN hour < 12 THEN 2 WHEN hour < 18 THEN 3 ELSE 4 END,
           CASE WHEN hour < 6 THEN '00-05 night' WHEN hour < 12 THEN '06-11 morning'
                WHEN hour < 18 THEN '12-17 afternoon' ELSE '18-23 evening' END,
           count(*)
    FROM orders GROUP BY 2, 3
)
SELECT grain, label, orders,
       round(100.0 * orders / sum(orders) OVER (PARTITION BY grain), 1) AS share_pct
FROM grains
ORDER BY grain, sort_key;
