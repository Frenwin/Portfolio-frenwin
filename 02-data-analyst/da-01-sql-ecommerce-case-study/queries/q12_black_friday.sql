-- Q12. What did Black Friday 2017 (24 Nov) do to volume and to delivery reliability?
-- Techniques: period labelling with CASE, per-day rates, ratio to a baseline computed in a separate CTE.
WITH periods AS (
    SELECT CASE
               WHEN purchased_at::date BETWEEN '2017-10-01' AND '2017-11-16' THEN '1. baseline (1 Oct - 16 Nov)'
               WHEN purchased_at::date BETWEEN '2017-11-17' AND '2017-11-23' THEN '2. week before Black Friday'
               WHEN purchased_at::date = '2017-11-24'                         THEN '3. Black Friday (24 Nov)'
               WHEN purchased_at::date BETWEEN '2017-11-25' AND '2017-12-03' THEN '4. next 9 days'
               WHEN purchased_at::date BETWEEN '2017-12-04' AND '2017-12-31' THEN '5. rest of December'
           END AS period,
           purchased_at::date AS day, is_delivered_late, days_to_deliver
    FROM marts.fct_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
      AND purchased_at >= '2017-10-01' AND purchased_at < '2018-01-01'
),
baseline AS (
    SELECT count(*)::numeric / count(DISTINCT day) AS orders_per_day
    FROM periods WHERE period LIKE '1.%'
)
SELECT period,
       count(DISTINCT day)                                                                AS days,
       round(count(*)::numeric / count(DISTINCT day))                                     AS orders_per_day,
       round(count(*)::numeric / count(DISTINCT day) / (SELECT orders_per_day FROM baseline), 1) AS x_baseline,
       round(100.0 * avg(is_delivered_late::int), 1)                                      AS late_pct,
       round(avg(days_to_deliver), 1)                                                     AS avg_delivery_days
FROM periods
WHERE period IS NOT NULL
GROUP BY period
ORDER BY period;
