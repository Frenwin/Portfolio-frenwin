-- Q7. How much does a late delivery cost in customer satisfaction?
-- Techniques: CASE bucketing, conditional averages, share of total with SUM(COUNT(*)) OVER ().
WITH bucketed AS (
    SELECT CASE
               WHEN delivery_delay_days <= -7 THEN '1. 7+ days early'
               WHEN delivery_delay_days < 0   THEN '2. 1-6 days early'
               WHEN delivery_delay_days = 0   THEN '3. on the estimated day'
               WHEN delivery_delay_days <= 3  THEN '4. 1-3 days late'
               WHEN delivery_delay_days <= 7  THEN '5. 4-7 days late'
               ELSE                                '6. 8+ days late'
           END AS delivery,
           avg_review_score
    FROM marts.fct_orders
    WHERE order_status = 'delivered' AND avg_review_score IS NOT NULL AND delivery_delay_days IS NOT NULL
      AND purchased_at >= '2017-01-01' AND purchased_at < '2018-09-01'
)
SELECT delivery,
       count(*)                                             AS orders,
       round(100.0 * count(*) / sum(count(*)) OVER (), 1)   AS share_pct,
       round(avg(avg_review_score), 2)                      AS avg_review,
       round(100.0 * avg((avg_review_score <= 2)::int), 1)  AS one_or_two_star_pct
FROM bucketed
GROUP BY delivery
ORDER BY delivery;
