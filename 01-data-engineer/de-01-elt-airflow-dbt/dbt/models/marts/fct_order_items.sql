-- Grain: one row per item in an order.
-- Incremental: later runs only reprocess orders purchased within `lookback_days`
-- of the latest order already loaded, replacing those rows (delete+insert on the key).
{{
    config(
        materialized='incremental',
        unique_key='order_item_key',
        incremental_strategy='delete+insert',
        on_schema_change='sync_all_columns'
    )
}}

select
    i.order_item_key,
    i.order_id,
    i.order_item_number,
    i.product_id,
    i.seller_id,
    cv.customer_sk,
    to_char(o.purchased_at, 'YYYYMMDD')::int   as purchase_date_key,
    o.purchased_at,
    o.order_status,
    i.shipping_limit_at,
    i.price,
    i.freight_value,
    i.price + i.freight_value                  as item_total
from {{ ref('stg_olist__order_items') }} as i
inner join {{ ref('stg_olist__orders') }} as o
    on o.order_id = i.order_id
inner join {{ ref('int_customer_versions') }} as cv
    on cv.customer_id = o.customer_id

{% if is_incremental() %}
where o.purchased_at >= (
    select max(purchased_at) - interval '{{ var("lookback_days") }} days' from {{ this }}
)
{% endif %}
