-- Q9. How do customers pay, and do instalments go with bigger baskets?
-- Techniques: two segmentations stacked with UNION ALL, share within each block, AOV per segment.
WITH orders AS (
    SELECT primary_payment_type, max_installments, items_value
    FROM marts.fct_orders
    WHERE order_status NOT IN ('canceled', 'unavailable') AND primary_payment_type IS NOT NULL
      AND purchased_at >= '2017-01-01' AND purchased_at < '2018-09-01'
),
by_type AS (
    SELECT 'payment type' AS dimension, primary_payment_type AS segment,
           count(*) AS orders, round(avg(items_value), 2) AS aov_brl
    FROM orders GROUP BY primary_payment_type
),
by_instalments AS (
    SELECT 'credit card instalments' AS dimension,
           CASE WHEN max_installments <= 1 THEN '1 (paid in full)'
                WHEN max_installments <= 3 THEN '2-3'
                WHEN max_installments <= 6 THEN '4-6'
                ELSE '7-24' END AS segment,
           count(*) AS orders, round(avg(items_value), 2) AS aov_brl
    FROM orders WHERE primary_payment_type = 'credit_card'
    GROUP BY 2
)
SELECT dimension, segment, orders,
       round(100.0 * orders / sum(orders) OVER (PARTITION BY dimension), 1) AS share_pct,
       aov_brl
FROM (SELECT * FROM by_type UNION ALL SELECT * FROM by_instalments) t
ORDER BY dimension DESC, segment;
