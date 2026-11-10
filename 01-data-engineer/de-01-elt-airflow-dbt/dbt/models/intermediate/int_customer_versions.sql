-- Olist issues a new customer_id for every order, all pointing to one customer_unique_id.
-- Ordering those records by purchase time gives the person's address history:
-- a new version starts whenever zip code, city or state differs from the previous order.
with customer_orders as (
    select
        c.customer_id,
        c.customer_unique_id,
        c.zip_code_prefix,
        c.city,
        c.state,
        o.purchased_at
    from {{ ref('stg_olist__customers') }} as c
    inner join {{ ref('stg_olist__orders') }} as o
        on o.customer_id = c.customer_id
),

flagged as (
    select
        *,
        case
            when lag(zip_code_prefix || '|' || city || '|' || state) over w
                 is not distinct from (zip_code_prefix || '|' || city || '|' || state)
            then 0
            else 1
        end as starts_new_version
    from customer_orders
    window w as (partition by customer_unique_id order by purchased_at, customer_id)
),

versioned as (
    select
        *,
        sum(starts_new_version) over (
            partition by customer_unique_id
            order by purchased_at, customer_id
            rows between unbounded preceding and current row
        ) as version_number
    from flagged
)

select
    customer_id,
    customer_unique_id,
    version_number,
    md5(customer_unique_id || '-' || version_number) as customer_sk,
    zip_code_prefix,
    city,
    state,
    purchased_at
from versioned
