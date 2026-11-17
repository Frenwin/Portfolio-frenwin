-- Q1. What does the data cover: period, users, sessions, purchases, revenue?
-- Techniques: wildcard tables with _TABLE_SUFFIX, scalar subquery over UNNEST(event_params) for the GA4 session id.
WITH events AS (
    SELECT
        user_pseudo_id,
        CONCAT(user_pseudo_id, '-', CAST((SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS STRING)) AS session_id,
        event_name,
        PARSE_DATE('%Y%m%d', event_date) AS event_date,
        ecommerce.purchase_revenue_in_usd AS revenue
    FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
    WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
)
SELECT
    MIN(event_date)                          AS first_day,
    MAX(event_date)                          AS last_day,
    COUNT(*)                                 AS events,
    COUNT(DISTINCT user_pseudo_id)           AS users,
    COUNT(DISTINCT session_id)               AS sessions,
    COUNTIF(event_name = 'purchase')         AS purchases,
    ROUND(SUM(revenue))                      AS revenue_usd,
    COUNT(DISTINCT IF(event_name = 'purchase', user_pseudo_id, NULL)) AS buyers
FROM events;
