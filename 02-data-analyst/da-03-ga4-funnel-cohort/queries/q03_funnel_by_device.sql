-- Q3. Does the funnel break differently on mobile and desktop?
-- Techniques: session-level flags with LOGICAL_OR, ANY_VALUE for session attributes, step-to-step rates per segment.
WITH events AS (
    SELECT
        CONCAT(user_pseudo_id, '-', CAST((SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS STRING)) AS session_id,
        event_name,
        device.category AS device
    FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
    WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
),
sessions AS (
    SELECT
        session_id,
        ANY_VALUE(device)                       AS device,
        LOGICAL_OR(event_name = 'view_item')    AS viewed,
        LOGICAL_OR(event_name = 'add_to_cart')  AS carted,
        LOGICAL_OR(event_name = 'begin_checkout') AS checked_out,
        LOGICAL_OR(event_name = 'purchase')     AS purchased
    FROM events
    WHERE session_id IS NOT NULL
    GROUP BY session_id
)
SELECT
    device,
    COUNT(*)                                                        AS sessions,
    ROUND(100 * COUNTIF(viewed) / COUNT(*), 1)                      AS view_item_pct,
    ROUND(100 * SAFE_DIVIDE(COUNTIF(carted), COUNTIF(viewed)), 1)   AS view_to_cart_pct,
    ROUND(100 * SAFE_DIVIDE(COUNTIF(checked_out), COUNTIF(carted)), 1) AS cart_to_checkout_pct,
    ROUND(100 * SAFE_DIVIDE(COUNTIF(purchased), COUNTIF(checked_out)), 1) AS checkout_to_purchase_pct,
    ROUND(100 * COUNTIF(purchased) / COUNT(*), 2)                   AS session_conversion_pct
FROM sessions
GROUP BY device
ORDER BY sessions DESC;
