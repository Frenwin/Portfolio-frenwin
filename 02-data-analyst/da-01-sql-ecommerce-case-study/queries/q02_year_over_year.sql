-- Q2. Is the business still growing? Compare Jan-Aug 2018 with Jan-Aug 2017.
-- Techniques: conditional aggregation with FILTER, unpivot with UNION ALL, growth ratio.
WITH by_year AS (
    SELECT extract(year FROM purchased_at)::int  AS year,
           count(*)                              AS orders,
           sum(items_value)                      AS gmv,
           count(DISTINCT customer_unique_id)    AS customers
    FROM marts.fct_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
      AND extract(month FROM purchased_at) BETWEEN 1 AND 8
      AND purchased_at >= '2017-01-01' AND purchased_at < '2018-09-01'
    GROUP BY 1
),
pivoted AS (
    SELECT 'orders' AS metric,
           max(orders) FILTER (WHERE year = 2017)::numeric AS y2017,
           max(orders) FILTER (WHERE year = 2018)::numeric AS y2018
    FROM by_year
    UNION ALL
    SELECT 'customers', max(customers) FILTER (WHERE year = 2017), max(customers) FILTER (WHERE year = 2018)
    FROM by_year
    UNION ALL
    SELECT 'gmv_brl', round(max(gmv) FILTER (WHERE year = 2017)), round(max(gmv) FILTER (WHERE year = 2018))
    FROM by_year
    UNION ALL
    SELECT 'aov_brl', round(max(gmv / orders) FILTER (WHERE year = 2017), 2), round(max(gmv / orders) FILTER (WHERE year = 2018), 2)
    FROM by_year
)
SELECT metric, y2017 AS jan_aug_2017, y2018 AS jan_aug_2018, round(100 * (y2018 / y2017 - 1), 1) AS growth_pct
FROM pivoted;
