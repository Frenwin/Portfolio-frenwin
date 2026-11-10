select
    order_id || '-' || order_item_id       as order_item_key,
    order_id,
    order_item_id::int                     as order_item_number,
    product_id,
    seller_id,
    shipping_limit_date::timestamp         as shipping_limit_at,
    price::numeric(12, 2)                  as price,
    freight_value::numeric(12, 2)          as freight_value
from {{ source('olist', 'order_items') }}
