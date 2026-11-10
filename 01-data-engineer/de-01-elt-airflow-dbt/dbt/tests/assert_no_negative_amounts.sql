-- Prices, freight and payments can be zero (vouchers) but never negative.
select order_item_key as record_key, 'order_item' as record_type
from {{ ref('fct_order_items') }}
where price < 0 or freight_value < 0

union all

select order_id, 'order'
from {{ ref('fct_orders') }}
where items_value < 0 or freight_value < 0 or payment_value < 0
