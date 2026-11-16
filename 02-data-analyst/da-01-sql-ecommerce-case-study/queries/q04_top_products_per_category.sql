-- Q4. What are the 3 best-selling products in each of the 5 largest categories?
-- Techniques: two-level ranking with ROW_NUMBER() OVER (PARTITION BY ...), share within a partition.
WITH sales AS (
    SELECT p.category_name, i.product_id, sum(i.price) AS revenue, count(*) AS units
    FROM marts.fct_order_items i
    JOIN marts.dim_products p USING (product_id)
    WHERE i.order_status NOT IN ('canceled', 'unavailable')
      AND i.purchased_at >= '2017-01-01' AND i.purchased_at < '2018-09-01'
    GROUP BY 1, 2
),
top_categories AS (
    SELECT category_name, sum(revenue) AS category_revenue
    FROM sales GROUP BY 1 ORDER BY 2 DESC LIMIT 5
),
ranked AS (
    SELECT s.*, t.category_revenue,
           row_number() OVER (PARTITION BY s.category_name ORDER BY s.revenue DESC) AS rank_in_category,
           round(100 * s.revenue / t.category_revenue, 1)                           AS share_of_category_pct
    FROM sales s JOIN top_categories t USING (category_name)
)
SELECT category_name, rank_in_category, left(product_id, 8) AS product, units,
       round(revenue) AS revenue_brl, share_of_category_pct
FROM ranked
WHERE rank_in_category <= 3
ORDER BY category_revenue DESC, rank_in_category;
