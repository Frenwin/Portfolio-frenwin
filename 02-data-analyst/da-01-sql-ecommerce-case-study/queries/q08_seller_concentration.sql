-- Q8. How dependent is the marketplace on its largest sellers?
-- Techniques: NTILE deciles, nested aggregate inside a window (SUM(SUM(...)) OVER), cumulative share.
WITH seller_gmv AS (
    SELECT seller_id, sum(price) AS gmv
    FROM marts.fct_order_items
    WHERE order_status NOT IN ('canceled', 'unavailable')
      AND purchased_at >= '2017-01-01' AND purchased_at < '2018-09-01'
    GROUP BY seller_id
),
deciles AS (
    SELECT seller_id, gmv, ntile(10) OVER (ORDER BY gmv DESC) AS decile FROM seller_gmv
)
SELECT decile,
       count(*)                                                                       AS sellers,
       round(sum(gmv))                                                                AS gmv_brl,
       round(100 * sum(gmv) / sum(sum(gmv)) OVER (), 1)                               AS share_pct,
       round(100 * sum(sum(gmv)) OVER (ORDER BY decile) / sum(sum(gmv)) OVER (), 1)   AS cumulative_pct,
       round(avg(gmv))                                                                AS avg_gmv_per_seller_brl
FROM deciles
GROUP BY decile
ORDER BY decile;
