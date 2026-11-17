-- Q8. Which popular products get looked at but rarely added to the cart?
-- Techniques: UNNEST(items) for item-level events, HAVING for a minimum-traffic threshold, ratio ranking.
WITH item_events AS (
    SELECT event_name, item.item_name AS item_name, item.item_category AS category
    FROM `bigquery-public-data.ga4_obfuscated_sample_ecommerce.events_*`, UNNEST(items) AS item
    WHERE _TABLE_SUFFIX BETWEEN '20201101' AND '20210131'
      AND event_name IN ('view_item', 'add_to_cart')
      AND item.item_name NOT IN ('(not set)', '')
),
per_item AS (
    SELECT
        item_name,
        ANY_VALUE(category)                    AS category,
        COUNTIF(event_name = 'view_item')      AS views,
        COUNTIF(event_name = 'add_to_cart')    AS adds_to_cart
    FROM item_events
    GROUP BY item_name
    HAVING views >= 2000
)
SELECT
    item_name,
    category,
    views,
    adds_to_cart,
    ROUND(100 * adds_to_cart / views, 1)                                   AS view_to_cart_pct,
    ROUND(100 * SUM(adds_to_cart) OVER () / SUM(views) OVER (), 1)         AS average_pct_for_these_items,
    RANK() OVER (ORDER BY adds_to_cart / views)                            AS weakest_rank
FROM per_item
ORDER BY view_to_cart_pct
LIMIT 15;
