-- Q11. Who pays the most for shipping relative to what they buy?
-- Techniques: ratio of sums (not an average of ratios), join to the SCD2 dimension, RANK over an expression.
WITH items AS (
    SELECT c.state, i.price, i.freight_value
    FROM marts.fct_order_items i
    JOIN marts.dim_customers c USING (customer_sk)
    WHERE i.order_status NOT IN ('canceled', 'unavailable')
      AND i.purchased_at >= '2017-01-01' AND i.purchased_at < '2018-09-01'
)
SELECT rank() OVER (ORDER BY sum(freight_value) / sum(price) DESC) AS burden_rank,
       state,
       count(*)                                          AS items,
       round(avg(price), 2)                              AS avg_item_price_brl,
       round(avg(freight_value), 2)                      AS avg_freight_brl,
       round(100 * sum(freight_value) / sum(price), 1)   AS freight_share_pct
FROM items
GROUP BY state
HAVING count(*) >= 300
ORDER BY burden_rank;
