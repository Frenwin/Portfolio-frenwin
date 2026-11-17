-- Q4. Which acquisition channels bring buyers, not just visitors?
-- Techniques: user-level first-touch attribution (traffic_source), user conversion rate, revenue per user.
WITH users AS (
    SELECT
        user_pseudo_id,
        ANY_VALUE(traffic_source.medium)                   AS first_medium,
        LOGICAL_OR(event_name = 'purchase')                AS bought,
        SUM(IFNULL(ecommerce.purchase_revenue_in_usd, 0))  AS revenue
    FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
    WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
    GROUP BY user_pseudo_id
)
SELECT
    first_medium,
    COUNT(*)                                          AS users,
    ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)  AS share_of_users_pct,
    COUNTIF(bought)                                   AS buyers,
    ROUND(100 * COUNTIF(bought) / COUNT(*), 2)        AS user_conversion_pct,
    ROUND(SUM(revenue))                               AS revenue_usd,
    ROUND(SUM(revenue) / COUNT(*), 2)                 AS revenue_per_user_usd
FROM users
GROUP BY first_medium
ORDER BY users DESC;
