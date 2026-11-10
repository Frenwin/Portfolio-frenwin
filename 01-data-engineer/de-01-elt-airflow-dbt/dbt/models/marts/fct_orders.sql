-- Grain: one row per order (accumulating snapshot of the order lifecycle).
select
    o.order_id,
    cv.customer_sk,
    cv.customer_unique_id,
    to_char(o.purchased_at, 'YYYYMMDD')::int                      as purchase_date_key,
    o.order_status,

    o.purchased_at,
    o.approved_at,
    o.delivered_to_carrier_at,
    o.delivered_to_customer_at,
    o.estimated_delivery_at,

    coalesce(i.item_count, 0)                                     as item_count,
    coalesce(i.distinct_sellers, 0)                               as distinct_sellers,
    coalesce(i.items_value, 0)                                    as items_value,
    coalesce(i.freight_value, 0)                                  as freight_value,
    coalesce(i.items_value, 0) + coalesce(i.freight_value, 0)     as order_value,

    p.payment_value,
    p.payment_count,
    p.primary_payment_type,
    p.max_installments,

    r.avg_review_score,
    r.latest_review_score,
    coalesce(r.review_count, 0)                                   as review_count,

    round(extract(epoch from o.approved_at - o.purchased_at) / 3600.0, 2)                as hours_to_approve,
    round(extract(epoch from o.delivered_to_customer_at - o.purchased_at) / 86400.0, 2) as days_to_deliver,
    o.delivered_to_customer_at::date - o.estimated_delivery_at::date                    as delivery_delay_days,
    case
        when o.delivered_to_customer_at is null then null
        else o.delivered_to_customer_at::date > o.estimated_delivery_at::date
    end                                                           as is_delivered_late
from {{ ref('stg_olist__orders') }} as o
inner join {{ ref('int_customer_versions') }} as cv
    on cv.customer_id = o.customer_id
left join {{ ref('int_order_items_summary') }} as i
    on i.order_id = o.order_id
left join {{ ref('int_order_payments_summary') }} as p
    on p.order_id = o.order_id
left join {{ ref('int_order_reviews_summary') }} as r
    on r.order_id = o.order_id
