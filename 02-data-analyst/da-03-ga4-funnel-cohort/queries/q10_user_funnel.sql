-- Q10. The purchase funnel per user, across sessions (the headline funnel).
-- Techniques: user-level closed funnel on first-occurrence timestamps across sessions, built only from reliably
-- tracked steps; add_to_cart is excluded because 34% of buyers never fire it (see Q9).
WITH firsts AS (
    SELECT
        user_pseudo_id,
        MIN(IF(event_name = 'view_item', event_timestamp, NULL))        AS t_view,
        MIN(IF(event_name = 'add_to_cart', event_timestamp, NULL))      AS t_cart,
        MIN(IF(event_name = 'begin_checkout', event_timestamp, NULL))   AS t_checkout,
        MIN(IF(event_name = 'add_payment_info', event_timestamp, NULL)) AS t_payment,
        MIN(IF(event_name = 'purchase', event_timestamp, NULL))         AS t_purchase
    FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
    WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
    GROUP BY user_pseudo_id
),
agg AS (
    SELECT
        COUNT(*)                                                                             AS users,
        COUNTIF(t_view IS NOT NULL)                                                          AS viewed,
        COUNTIF(t_checkout >= t_view)                                                        AS checked_out,
        COUNTIF(t_checkout >= t_view AND t_payment >= t_checkout)                            AS paid_info,
        COUNTIF(t_checkout >= t_view AND t_payment >= t_checkout AND t_purchase >= t_payment) AS purchased,
        COUNTIF(t_cart >= t_view)                                                            AS carted_info
    FROM firsts
)
SELECT
    s.step,
    s.n                                          AS users,
    ROUND(100 * s.n / agg.users, 2)              AS pct_of_all_users,
    ROUND(100 * SAFE_DIVIDE(s.n, s.prev), 1)     AS pct_of_previous_step
FROM agg, UNNEST([
    STRUCT('1. Visited' AS step, agg.users AS n, agg.users AS prev),
    STRUCT('2. Viewed a product', agg.viewed, agg.users),
    STRUCT('3. Began checkout', agg.checked_out, agg.viewed),
    STRUCT('4. Added payment info', agg.paid_info, agg.checked_out),
    STRUCT('5. Purchased', agg.purchased, agg.paid_info),
    STRUCT('(info) Added to cart after viewing', agg.carted_info, agg.viewed)
]) AS s
ORDER BY s.step;
