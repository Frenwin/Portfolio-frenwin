-- Q2. Where do sessions drop out on the way to a purchase?
-- Techniques: closed funnel (each step must happen after the previous one in the same session),
-- MIN(IF(...)) for first-occurrence timestamps, UNNEST of an array of STRUCTs to unpivot.
WITH events AS (
    SELECT
        CONCAT(user_pseudo_id, '-', CAST((SELECT value.int_value FROM UNNEST(event_params) WHERE key = 'ga_session_id') AS STRING)) AS session_id,
        event_name,
        event_timestamp AS ts
    FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`
    WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
),
firsts AS (
    SELECT
        session_id,
        MIN(IF(event_name = 'view_item', ts, NULL))        AS t_view,
        MIN(IF(event_name = 'add_to_cart', ts, NULL))      AS t_cart,
        MIN(IF(event_name = 'begin_checkout', ts, NULL))   AS t_checkout,
        MIN(IF(event_name = 'add_payment_info', ts, NULL)) AS t_payment,
        MIN(IF(event_name = 'purchase', ts, NULL))         AS t_purchase
    FROM events
    WHERE session_id IS NOT NULL
    GROUP BY session_id
),
reached AS (
    SELECT
        t_view IS NOT NULL                                             AS viewed,
        t_view IS NOT NULL AND t_cart >= t_view                        AS carted,
        t_view IS NOT NULL AND t_cart >= t_view AND t_checkout >= t_cart AS checked_out,
        t_view IS NOT NULL AND t_cart >= t_view AND t_checkout >= t_cart AND t_payment >= t_checkout AS paid_info,
        t_view IS NOT NULL AND t_cart >= t_view AND t_checkout >= t_cart AND t_payment >= t_checkout
            AND t_purchase >= t_payment                                AS purchased
    FROM firsts
),
agg AS (
    SELECT COUNT(*) AS sessions, COUNTIF(viewed) AS viewed, COUNTIF(carted) AS carted,
           COUNTIF(checked_out) AS checked_out, COUNTIF(paid_info) AS paid_info, COUNTIF(purchased) AS purchased
    FROM reached
)
SELECT
    s.step,
    s.n                                                   AS sessions,
    ROUND(100 * s.n / agg.sessions, 2)                    AS pct_of_all_sessions,
    ROUND(100 * SAFE_DIVIDE(s.n, s.prev), 1)              AS pct_of_previous_step
FROM agg, UNNEST([
    STRUCT('1. Session' AS step, agg.sessions AS n, agg.sessions AS prev),
    STRUCT('2. View item', agg.viewed, agg.sessions),
    STRUCT('3. Add to cart', agg.carted, agg.viewed),
    STRUCT('4. Begin checkout', agg.checked_out, agg.carted),
    STRUCT('5. Add payment info', agg.paid_info, agg.checked_out),
    STRUCT('6. Purchase', agg.purchased, agg.paid_info)
]) AS s
ORDER BY s.step;
