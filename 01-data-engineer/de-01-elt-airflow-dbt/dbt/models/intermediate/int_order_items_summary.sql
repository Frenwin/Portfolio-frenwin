select
    order_id,
    count(*)                    as item_count,
    count(distinct product_id)  as distinct_products,
    count(distinct seller_id)   as distinct_sellers,
    sum(price)                  as items_value,
    sum(freight_value)          as freight_value
from {{ ref('stg_olist__order_items') }}
group by order_id
