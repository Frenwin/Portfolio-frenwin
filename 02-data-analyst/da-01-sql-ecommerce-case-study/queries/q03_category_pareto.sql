-- Q3. Which categories drive revenue, and how concentrated is it (Pareto)?
-- Techniques: RANK, share of total with SUM() OVER (), running total for cumulative share.
WITH category AS (
    SELECT p.category_name,
           sum(i.price)               AS revenue,
           count(DISTINCT i.order_id) AS orders
    FROM marts.fct_order_items i
    JOIN marts.dim_products p USING (product_id)
    WHERE i.order_status NOT IN ('canceled', 'unavailable')
      AND i.purchased_at >= '2017-01-01' AND i.purchased_at < '2018-09-01'
    GROUP BY 1
),
-- MATERIALIZED stops the planner pushing the rank filter into this CTE. Without it, PostgreSQL 16.16
-- drops the filter when rank() shares its ordering with a running sum and returns all 74 rows
-- (fixed in 17.x). Reproduction: docs/postgres-16-window-filter.md
ranked AS MATERIALIZED (
    SELECT rank() OVER (ORDER BY revenue DESC)                                   AS category_rank,
           category_name,
           round(revenue)                                                         AS revenue_brl,
           orders,
           round(100 * revenue / sum(revenue) OVER (), 1)                         AS share_pct,
           round(100 * sum(revenue) OVER (ORDER BY revenue DESC ROWS UNBOUNDED PRECEDING)
                     / sum(revenue) OVER (), 1)                                   AS cumulative_pct,
           count(*) OVER ()                                                       AS total_categories
    FROM category
)
SELECT * FROM ranked WHERE category_rank <= 15 ORDER BY category_rank;
