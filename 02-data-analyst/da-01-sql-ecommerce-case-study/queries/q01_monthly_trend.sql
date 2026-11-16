-- Q1. How did GMV, orders and AOV develop month by month, and how fast did they grow?
-- Techniques: CTE, LAG for month-over-month growth, moving average with a window frame.
WITH monthly AS (
    SELECT date_trunc('month', purchased_at)::date AS month,
           count(*)                                AS orders,
           sum(items_value)                        AS gmv
    FROM marts.fct_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
      AND purchased_at >= '2017-01-01' AND purchased_at < '2018-09-01'
    GROUP BY 1
)
SELECT to_char(month, 'YYYY-MM')                                                  AS month,
       orders,
       round(gmv)                                                                  AS gmv_brl,
       round(gmv / orders, 2)                                                      AS aov_brl,
       round(100 * (gmv / lag(gmv) OVER (ORDER BY month) - 1), 1)                  AS gmv_mom_pct,
       round(avg(gmv) OVER (ORDER BY month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)) AS gmv_3m_avg_brl
FROM monthly
ORDER BY month;
