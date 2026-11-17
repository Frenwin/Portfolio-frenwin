-- Q9. Can the funnel be trusted? How many sessions skip a step or record steps out of order?
-- Techniques: tracking QA with session-level flags, COUNTIF over combinations of missing and present events.
WITH events AS (
    SELECT
        CONCAT(user_pseudo_id, '-', CAST((SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS STRING)) AS session_id,
        event_name,
        event_timestamp AS ts
    FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
    WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
),
s AS (
    SELECT
        session_id,
        MIN(IF(event_name = 'view_item', ts, NULL))      AS t_view,
        MIN(IF(event_name = 'add_to_cart', ts, NULL))    AS t_cart,
        MIN(IF(event_name = 'begin_checkout', ts, NULL)) AS t_checkout,
        MIN(IF(event_name = 'purchase', ts, NULL))       AS t_purchase
    FROM events
    WHERE session_id IS NOT NULL
    GROUP BY session_id
),
u AS (
    SELECT
        user_pseudo_id,
        LOGICAL_OR(event_name = 'add_to_cart') AS has_cart,
        LOGICAL_OR(event_name = 'purchase')    AS bought
    FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
    WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
    GROUP BY user_pseudo_id
)
SELECT check_name, sessions, base, base_description, ROUND(100 * sessions / base, 1) AS pct_of_base
FROM (
    SELECT 'checkout without add_to_cart in the session' AS check_name,
           COUNTIF(t_checkout IS NOT NULL AND t_cart IS NULL) AS sessions,
           COUNTIF(t_checkout IS NOT NULL) AS base, 'sessions with begin_checkout' AS base_description FROM s
    UNION ALL
    SELECT 'add_to_cart without view_item in the session',
           COUNTIF(t_cart IS NOT NULL AND t_view IS NULL), COUNTIF(t_cart IS NOT NULL), 'sessions with add_to_cart' FROM s
    UNION ALL
    SELECT 'add_to_cart recorded before the first view_item',
           COUNTIF(t_cart < t_view), COUNTIF(t_cart IS NOT NULL AND t_view IS NOT NULL), 'sessions with both' FROM s
    UNION ALL
    SELECT 'purchase without begin_checkout in the session',
           COUNTIF(t_purchase IS NOT NULL AND t_checkout IS NULL), COUNTIF(t_purchase IS NOT NULL), 'sessions with purchase' FROM s
    UNION ALL
    SELECT 'buyers who never fired add_to_cart (any session)',
           COUNTIF(bought AND NOT has_cart), COUNTIF(bought), 'buyers' FROM u
)
ORDER BY check_name;
