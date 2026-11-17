-- Q7. How long from first visit to first purchase, and do buyers buy again?
-- Techniques: per-user MIN timestamps, TIMESTAMP_DIFF, APPROX_QUANTILES for the median, bucketed distribution.
WITH users AS (
    SELECT
        user_pseudo_id,
        MIN(IF(event_name = 'first_visit', event_timestamp, NULL)) AS t_first_visit,
        MIN(IF(event_name = 'purchase', event_timestamp, NULL))    AS t_first_purchase,
        COUNT(DISTINCT IF(event_name = 'purchase', ecommerce.transaction_id, NULL)) AS purchases
    FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
    WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
    GROUP BY user_pseudo_id
),
buyers AS (
    SELECT
        purchases,
        TIMESTAMP_DIFF(TIMESTAMP_MICROS(t_first_purchase), TIMESTAMP_MICROS(t_first_visit), MINUTE) / 60.0 AS hours_to_buy
    FROM users
    WHERE t_first_purchase IS NOT NULL AND t_first_visit IS NOT NULL AND t_first_purchase >= t_first_visit
)
SELECT
    CASE
        WHEN hours_to_buy < 1   THEN '1. within 1 hour'
        WHEN hours_to_buy < 24  THEN '2. 1-24 hours'
        WHEN hours_to_buy < 168 THEN '3. 1-7 days'
        ELSE                         '4. more than 7 days'
    END                                                          AS time_to_first_purchase,
    COUNT(*)                                                     AS buyers,
    ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)             AS share_pct,
    ROUND(100 * COUNTIF(purchases >= 2) / COUNT(*), 1)           AS repeat_buyer_pct,
    (SELECT ROUND(APPROX_QUANTILES(hours_to_buy, 2)[OFFSET(1)], 1) FROM buyers) AS median_hours_all_buyers
FROM buyers
GROUP BY time_to_first_purchase
ORDER BY time_to_first_purchase;
