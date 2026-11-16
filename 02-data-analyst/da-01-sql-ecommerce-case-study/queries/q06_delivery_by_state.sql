-- Q6. Which states get the slowest and least reliable delivery?
-- Techniques: join to the SCD2 customer dimension (address at purchase time), RANK, HAVING for minimum volume,
-- difference from the average of all states with AVG() OVER ().
WITH delivered AS (
    SELECT c.state, o.days_to_deliver, o.is_delivered_late
    FROM marts.fct_orders o
    JOIN marts.dim_customers c USING (customer_sk)
    WHERE o.order_status = 'delivered' AND o.is_delivered_late IS NOT NULL
      AND o.purchased_at >= '2017-01-01' AND o.purchased_at < '2018-09-01'
),
by_state AS (
    SELECT state,
           count(*)                                      AS orders,
           round(avg(days_to_deliver), 1)                AS avg_days,
           round(100.0 * avg(is_delivered_late::int), 1) AS late_pct
    FROM delivered
    GROUP BY state
    HAVING count(*) >= 300
)
SELECT rank() OVER (ORDER BY late_pct DESC)          AS worst_rank,
       state, orders, avg_days, late_pct,
       round(late_pct - avg(late_pct) OVER (), 1)    AS vs_state_average_pp
FROM by_state
ORDER BY late_pct DESC;
