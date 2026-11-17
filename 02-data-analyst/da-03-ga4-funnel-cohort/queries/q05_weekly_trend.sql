-- Q5. How did traffic and conversion move week by week through the holiday season?
-- Techniques: DATE_TRUNC to ISO weeks, session conversion, LAG for week-over-week change.
WITH events AS (
    SELECT
        DATE_TRUNC(PARSE_DATE('%Y%m%d', event_date), WEEK(MONDAY)) AS week,
        user_pseudo_id,
        CONCAT(user_pseudo_id, '-', CAST((SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS STRING)) AS session_id,
        event_name,
        ecommerce.purchase_revenue_in_usd AS revenue
    FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
    WHERE _TABLE_SUFFIX BETWEEN '20201102' AND '20210131'   -- whole weeks only: Monday 2 Nov to Sunday 31 Jan
),
weekly AS (
    SELECT
        week,
        COUNT(DISTINCT user_pseudo_id)                                  AS users,
        COUNT(DISTINCT session_id)                                      AS sessions,
        COUNT(DISTINCT IF(event_name = 'purchase', session_id, NULL))   AS purchasing_sessions,
        ROUND(SUM(revenue))                                             AS revenue_usd
    FROM events
    GROUP BY week
)
SELECT
    week,
    users,
    sessions,
    purchasing_sessions,
    ROUND(100 * purchasing_sessions / sessions, 2)                     AS session_conversion_pct,
    revenue_usd,
    ROUND(100 * (sessions / LAG(sessions) OVER (ORDER BY week) - 1), 1) AS sessions_wow_pct
FROM weekly
ORDER BY week;
